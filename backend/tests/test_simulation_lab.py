"""
QueueWise AI — Simulation Lab & Counter Optimizer Test Suite

Verifies:
  1. Preset Scenarios (A through F) definitions and metadata
  2. Discrete-Event Simulation Engine determinism, seeding, and execution
  3. Dynamic wait time estimate vs actual comparison accuracy
  4. Counter Allocation Optimizer (M/M/c algorithm, bottleneck detection, wait reduction)
  5. Simulation REST API endpoints (/scenarios, /runs, /runs/{id}, /optimizer/recommend)
  6. Data isolation between simulated runs and live citizen queues
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.main import app
from app.simulation.scenarios import get_all_scenarios, get_scenario, SCENARIOS
from app.simulation.engine import SimulationEngine
from app.simulation.optimizer import CounterOptimizer
from app.models.token import Token
from app.models.enums import TokenStatus


class TestSimulationScenarios:
    """Verifies scenario specifications and definitions."""

    def test_all_six_preset_scenarios_exist(self):
        """All challenge scenarios A through F must be registered."""
        scenarios = get_all_scenarios()
        assert len(scenarios) >= 6
        codes = [s["code"] for s in scenarios]
        assert set(["A", "B", "C", "D", "E", "F"]).issubset(set(codes))

    def test_scenario_required_attributes(self):
        """Every scenario must include all operational parameters and bilingual text."""
        required_fields = [
            "key", "code", "title", "title_ur", "category",
            "duration_seconds", "arrival_rate_per_minute",
            "active_counters_count", "priority_ratio", "no_show_rate",
            "service_duration_multiplier", "target_sla_seconds",
        ]
        for key, s in SCENARIOS.items():
            for field in required_fields:
                assert field in s, f"Scenario '{key}' missing required field '{field}'"
            assert s["duration_seconds"] > 0
            assert s["arrival_rate_per_minute"] > 0
            assert 0.0 <= s["priority_ratio"] <= 1.0
            assert 0.0 <= s["no_show_rate"] <= 1.0


class TestSimulationEngineExecution:
    """Verifies the core simulation engine mechanics."""

    def test_scenario_a_baseline_execution(self):
        """Scenario A (Baseline) executes cleanly with low wait and balanced metrics."""
        results = SimulationEngine.run_simulation(scenario_key="scenario_a", seed=42)
        assert results["scenario_key"] == "scenario_a"
        assert results["total_tokens_issued"] > 0
        assert results["completed_tokens"] > 0
        assert results["kpi_metrics"]["avg_wait_seconds"] >= 0
        assert results["kpi_metrics"]["counter_utilization_pct"] > 0
        # Baseline should have good throughput
        assert results["kpi_metrics"]["throughput_per_hour"] > 0

    def test_scenario_b_demand_surge_causes_queue_backlog(self):
        """Scenario B (Surge) generates higher arrival volume and queue depth than Baseline."""
        res_a = SimulationEngine.run_simulation(scenario_key="scenario_a", seed=100)
        res_b = SimulationEngine.run_simulation(scenario_key="scenario_b", seed=100)

        assert res_b["total_tokens_issued"] > res_a["total_tokens_issued"]
        assert (
            res_b["kpi_metrics"]["avg_wait_seconds"] > res_a["kpi_metrics"]["avg_wait_seconds"]
            or res_b["unserved_waiting_tokens"] > res_a["unserved_waiting_tokens"]
        )

    def test_scenario_c_counter_outage_bottleneck(self):
        """Scenario C (Staff Shortage, 1 counter) creates severe bottleneck and high counter utilization."""
        res_c = SimulationEngine.run_simulation(scenario_key="scenario_c", seed=42)
        assert len(res_c["counters"]) == 1
        # The single counter should be heavily utilized
        assert res_c["counters"][0]["utilization_pct"] >= 70.0

    def test_scenario_e_high_no_show_generates_skips(self):
        """Scenario E (35% no show) results in significantly more skipped tokens than Baseline (5%)."""
        res_a = SimulationEngine.run_simulation(scenario_key="scenario_a", seed=42)
        res_e = SimulationEngine.run_simulation(scenario_key="scenario_e", seed=42)

        assert res_e["skipped_tokens"] > res_a["skipped_tokens"]
        assert res_e["skipped_tokens"] > 0

    def test_scenario_f_priority_triage_reduces_priority_wait(self):
        """Scenario F demonstrates that priority tokens wait significantly less than standard tokens."""
        res_f = SimulationEngine.run_simulation(scenario_key="scenario_f", seed=42)
        kpis = res_f["kpi_metrics"]
        assert kpis["avg_priority_wait_seconds"] < kpis["avg_standard_wait_seconds"]

    def test_simulation_determinism_with_seed(self):
        """Running the simulation twice with identical seed MUST yield 100% identical telemetry."""
        run1 = SimulationEngine.run_simulation(scenario_key="scenario_a", seed=999)
        run2 = SimulationEngine.run_simulation(scenario_key="scenario_a", seed=999)

        assert run1["total_tokens_issued"] == run2["total_tokens_issued"]
        assert run1["completed_tokens"] == run2["completed_tokens"]
        assert run1["kpi_metrics"]["avg_wait_seconds"] == run2["kpi_metrics"]["avg_wait_seconds"]
        assert run1["kpi_metrics"]["max_wait_seconds"] == run2["kpi_metrics"]["max_wait_seconds"]
        assert (
            run1["estimate_vs_actual"]["mean_absolute_error_seconds"]
            == run2["estimate_vs_actual"]["mean_absolute_error_seconds"]
        )

    def test_estimate_vs_actual_comparison_metrics(self):
        """Verifies estimate-vs-actual error tracking and sample comparison points."""
        res = SimulationEngine.run_simulation(scenario_key="scenario_a", seed=42)
        eva = res["estimate_vs_actual"]

        assert "mean_absolute_error_seconds" in eva
        assert "overall_accuracy_pct" in eva
        assert eva["overall_accuracy_pct"] >= 0.0
        assert len(eva["sample_points"]) > 0

        # Verify point structure
        pt = eva["sample_points"][0]
        assert "token_number" in pt
        assert "estimated_wait_seconds" in pt
        assert "actual_wait_seconds" in pt
        assert "error_seconds" in pt


class TestCounterOptimizer:
    """Verifies counter allocation recommendations and queue theory optimizations."""

    def test_optimizer_detects_bottleneck_and_reallocates(self):
        """
        When GEN has 4.0 arrivals/min and CASH has 0.2 arrivals/min with 1 counter each,
        optimizer must allocate more counters to GEN and reduce overall average wait.
        """
        services = [
            {"code": "GEN", "name": "General Inquiries", "arrival_rate_per_min": 4.0, "avg_duration_seconds": 180, "current_counters": 1},
            {"code": "DOC", "name": "Documentation", "arrival_rate_per_min": 0.8, "avg_duration_seconds": 180, "current_counters": 1},
            {"code": "CASH", "name": "Cashier", "arrival_rate_per_min": 0.2, "avg_duration_seconds": 120, "current_counters": 1},
        ]
        result = CounterOptimizer.optimize_allocation(
            services=services,
            total_counters=4,
            target_sla_seconds=600.0,
        )

        assert "recommended_avg_wait_seconds" in result
        assert result["recommended_avg_wait_seconds"] < result["current_avg_wait_seconds"]
        assert result["wait_reduction_pct"] > 0.0

        # GEN must receive the extra counter(s)
        gen_result = next(s for s in result["services"] if s["service_code"] == "GEN")
        assert gen_result["recommended_counters"] > gen_result["current_counters"]
        assert len(result["actionable_recommendations"]) > 0

    def test_optimizer_maintains_minimum_one_counter_per_service(self):
        """All active services must have at least 1 counter assigned."""
        services = [
            {"code": "GEN", "name": "General Inquiries", "arrival_rate_per_min": 2.0, "avg_duration_seconds": 180, "current_counters": 1},
            {"code": "DOC", "name": "Documentation", "arrival_rate_per_min": 1.0, "avg_duration_seconds": 180, "current_counters": 1},
        ]
        result = CounterOptimizer.optimize_allocation(services=services, total_counters=3)
        for s in result["services"]:
            assert s["recommended_counters"] >= 1


class TestSimulationAPIEndpoints:
    """Integration tests for Simulation REST endpoints."""

    @pytest.mark.anyio
    async def test_get_scenarios_endpoint(self, client: AsyncClient):
        """GET /api/v1/simulation/scenarios returns preset scenarios."""
        resp = await client.get("/api/v1/simulation/scenarios")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 6
        assert any(s["code"] == "A" for s in data)

    @pytest.mark.anyio
    async def test_get_single_scenario_endpoint(self, client: AsyncClient):
        """GET /api/v1/simulation/scenarios/scenario_a returns Scenario A details."""
        resp = await client.get("/api/v1/simulation/scenarios/scenario_a")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "A"
        assert "Baseline" in data["category"]

    @pytest.mark.anyio
    async def test_get_unknown_scenario_returns_404(self, client: AsyncClient):
        """GET /api/v1/simulation/scenarios/nonexistent returns 404."""
        resp = await client.get("/api/v1/simulation/scenarios/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_create_and_persist_simulation_run_via_api(self, client: AsyncClient):
        """POST /api/v1/simulation/runs executes simulation and returns complete telemetry."""
        payload = {
            "name": "Integration Test Run",
            "scenario_key": "scenario_a",
            "random_seed": 77,
            "duration_seconds": 600,
        }
        resp = await client.post("/api/v1/simulation/runs", json=payload)
        assert resp.status_code == 201
        data = resp.json()

        assert data["name"] == "Integration Test Run"
        assert data["random_seed"] == 77
        assert data["total_tokens_issued"] > 0
        assert "kpi_metrics" in data
        assert "estimate_vs_actual" in data
        assert "counters" in data
        assert data["id"] is not None

        # Verify it can be retrieved via GET /runs/{id}
        run_id = data["id"]
        get_resp = await client.get(f"/api/v1/simulation/runs/{run_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == run_id

    @pytest.mark.anyio
    async def test_optimizer_recommend_endpoint(self, client: AsyncClient):
        """POST /api/v1/simulation/optimizer/recommend returns allocation recommendations."""
        payload = {
            "total_counters": 4,
            "target_sla_seconds": 600.0,
            "services": [
                {"code": "GEN", "name": "General Inquiries", "arrival_rate_per_min": 3.0, "avg_duration_seconds": 180, "current_counters": 1},
                {"code": "DOC", "name": "Documentation", "arrival_rate_per_min": 0.5, "avg_duration_seconds": 180, "current_counters": 1},
            ],
        }
        resp = await client.post("/api/v1/simulation/optimizer/recommend", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert "wait_reduction_pct" in data
        assert len(data["services"]) == 2
        assert len(data["actionable_recommendations"]) > 0

    @pytest.mark.anyio
    async def test_simulation_does_not_pollute_live_queue(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Simulation execution must be strictly isolated.
        Tokens generated in simulation must NOT appear in live queue queries (session_id='default').
        """
        # Count live waiting tokens before
        stmt_before = select(Token).where(
            Token.session_id == "default",
            Token.status == TokenStatus.WAITING,
        )
        res_before = await db_session.execute(stmt_before)
        live_tokens_before = len(res_before.scalars().all())

        # Execute simulation run
        payload = {
            "scenario_key": "scenario_b",
            "random_seed": 42,
            "duration_seconds": 600,
        }
        resp = await client.post("/api/v1/simulation/runs", json=payload)
        assert resp.status_code == 201

        # Count live waiting tokens after
        res_after = await db_session.execute(stmt_before)
        live_tokens_after = len(res_after.scalars().all())

        assert live_tokens_after == live_tokens_before
