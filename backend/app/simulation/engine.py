"""
QueueWise AI — Discrete-Event Queue Simulation Engine

Fast, deterministic multi-server queue simulation model.
Supports reproducible random seeds, preset challenge scenarios (A–F),
custom parameter variations, dynamic wait time estimate tracking,
and estimate-vs-actual error analysis.
"""
import uuid
import random
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.service_category import ServiceCategory
from app.models.simulation_run import SimulationRun
from app.models.token import Token
from app.models.enums import SimulationStatus, TokenStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


class VirtualToken:
    """In-memory token representation during discrete-event simulation."""

    def __init__(
        self,
        token_id: int,
        display_number: str,
        service_code: str,
        service_id: uuid.UUID,
        arrival_time: float,
        priority: int,
        estimated_wait_seconds: int,
    ):
        self.token_id = token_id
        self.display_number = display_number
        self.service_code = service_code
        self.service_id = service_id
        self.arrival_time = arrival_time
        self.priority = priority
        self.estimated_wait_seconds = estimated_wait_seconds

        self.called_time: Optional[float] = None
        self.completed_time: Optional[float] = None
        self.actual_wait_seconds: Optional[int] = None
        self.actual_service_seconds: Optional[int] = None
        self.status: str = "WAITING"
        self.assigned_counter: Optional[str] = None


class VirtualCounter:
    """In-memory service counter representation during simulation."""

    def __init__(self, name: str, supported_services: List[str]):
        self.name = name
        self.supported_services = set(supported_services)
        self.busy_until: float = 0.0
        self.total_busy_time: float = 0.0
        self.tokens_served_count: int = 0
        self.is_active: bool = True


class SimulationEngine:
    """
    Deterministic queue simulator executing isolated demand scenarios.
    """

    @classmethod
    def run_simulation(
        cls,
        scenario_key: Optional[str] = None,
        custom_config: Optional[Dict[str, Any]] = None,
        seed: int = 42,
        service_categories: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Execute an isolated discrete-event simulation run.

        Args:
            scenario_key: Preset scenario key ('scenario_a' .. 'scenario_f')
            custom_config: Optional parameter overrides (duration, arrival_rate, counters, etc.)
            seed: Pseudo-random generator seed for 100% determinism
            service_categories: List of available service category specs

        Returns:
            Dictionary containing comprehensive execution telemetry and metrics.
        """
        rng = random.Random(seed)

        # 1. Resolve configuration from preset or defaults
        from app.simulation.scenarios import SCENARIOS

        base_config = {}
        if scenario_key and scenario_key in SCENARIOS:
            base_config = dict(SCENARIOS[scenario_key])

        # Merge custom overrides
        config = {**base_config, **(custom_config or {})}

        duration_seconds = float(config.get("duration_seconds", 1800.0))
        arrival_rate_per_min = float(config.get("arrival_rate_per_minute", 1.5))
        priority_ratio = float(config.get("priority_ratio", 0.10))
        no_show_rate = float(config.get("no_show_rate", 0.05))
        duration_multiplier = float(config.get("service_duration_multiplier", 1.0))
        target_sla_seconds = float(config.get("target_sla_seconds", 600.0))

        # Default standard services if not supplied
        if not service_categories:
            service_categories = [
                {"code": "GEN", "name": "General Inquiries", "duration": 180, "weight": 0.45},
                {"code": "DOC", "name": "Document Verification", "duration": 240, "weight": 0.35},
                {"code": "CASH", "name": "Cash & Fee Payments", "duration": 150, "weight": 0.20},
            ]

        services_by_code = {s["code"]: s for s in service_categories}

        # 2. Configure counters
        counter_assignments = config.get("counter_assignments")
        counters: List[VirtualCounter] = []

        if counter_assignments:
            for c_name, supported in counter_assignments.items():
                counters.append(VirtualCounter(name=c_name, supported_services=supported))
        else:
            # Generate default counters based on active_counters_count
            num_counters = int(config.get("active_counters_count", 3))
            all_codes = list(services_by_code.keys())
            for i in range(num_counters):
                # Distribute services or give each counter all services if single counter
                if num_counters == 1:
                    supp = all_codes
                else:
                    supp = [all_codes[i % len(all_codes)]]
                counters.append(VirtualCounter(name=f"Counter {i+1}", supported_services=supp))

        # 3. Generate arrivals using Poisson process (exponential inter-arrival times)
        lambda_rate = max(0.001, arrival_rate_per_min / 60.0)  # arrivals per second
        current_time = 0.0
        all_tokens: List[VirtualToken] = []
        token_counter = 1

        service_weights = [s.get("weight", 1.0) for s in service_categories]
        service_choices = [s["code"] for s in service_categories]

        # Tracking waiting queues per service: list of VirtualTokens
        waiting_queues: Dict[str, List[VirtualToken]] = {code: [] for code in services_by_code}

        # Estimate helper: counts active counters supporting a service
        def get_active_counters_for(code: str) -> int:
            return sum(1 for c in counters if c.is_active and code in c.supported_services)

        while current_time < duration_seconds:
            # Exponential inter-arrival time: -ln(U) / lambda
            inter_arrival = -math.log(rng.random()) / lambda_rate
            current_time += inter_arrival
            if current_time >= duration_seconds:
                break

            # Pick service category
            chosen_code = rng.choices(service_choices, weights=service_weights, k=1)[0]
            chosen_service = services_by_code[chosen_code]

            # Priority determination
            is_priority = 1 if rng.random() < priority_ratio else 0

            # Dynamic Wait Estimation at moment of arrival:
            # formula: ((Position Ahead + 1) * Avg Duration) / max(1, Active Counters)
            q_len = len(waiting_queues[chosen_code])
            active_c = max(1, get_active_counters_for(chosen_code))
            avg_dur = chosen_service.get("duration", 180) * duration_multiplier
            est_wait = max(1, round(((q_len + 1) * avg_dur) / active_c))

            v_token = VirtualToken(
                token_id=token_counter,
                display_number=f"{chosen_code}-{token_counter:03d}",
                service_code=chosen_code,
                service_id=uuid.uuid4(),
                arrival_time=current_time,
                priority=is_priority,
                estimated_wait_seconds=est_wait,
            )
            token_counter += 1
            all_tokens.append(v_token)

        # 4. Discrete-event simulation execution
        # Event loop stepping through time until all arrivals are handled or max time reached
        sim_time = 0.0
        max_sim_time = duration_seconds + 3600.0  # Allow draining queue after arrival cutoff

        # Sort tokens by arrival time
        arrival_queue = list(all_tokens)
        arrival_idx = 0
        total_arrivals = len(arrival_queue)

        completed_tokens: List[VirtualToken] = []
        skipped_tokens: List[VirtualToken] = []

        while sim_time < max_sim_time:
            # Advance time to next significant event:
            # Candidates: next arrival OR next counter becoming free
            next_arrival_time = (
                arrival_queue[arrival_idx].arrival_time
                if arrival_idx < total_arrivals
                else float("inf")
            )
            next_counter_time = min(
                (c.busy_until for c in counters if c.busy_until > sim_time),
                default=float("inf"),
            )

            next_event_time = min(next_arrival_time, next_counter_time)
            if next_event_time == float("inf"):
                # No more arrivals and no counters busy
                break

            sim_time = max(sim_time, next_event_time)

            # Process all arrivals up to current sim_time
            while arrival_idx < total_arrivals and arrival_queue[arrival_idx].arrival_time <= sim_time:
                arrived = arrival_queue[arrival_idx]
                # Insert into waiting queue maintaining priority (priority DESC, arrival_time ASC)
                q = waiting_queues[arrived.service_code]
                inserted = False
                for idx, t in enumerate(q):
                    if arrived.priority > t.priority:
                        q.insert(idx, arrived)
                        inserted = True
                        break
                if not inserted:
                    q.append(arrived)
                arrival_idx += 1

            # Dispatch available counters to eligible waiting tokens
            counters_dispatched = False
            for counter in counters:
                if counter.busy_until <= sim_time:
                    # Find highest priority waiting token matching counter's supported services
                    best_token = None
                    best_service_code = None

                    for code in counter.supported_services:
                        if code in waiting_queues and len(waiting_queues[code]) > 0:
                            cand = waiting_queues[code][0]
                            if best_token is None:
                                best_token = cand
                                best_service_code = code
                            elif cand.priority > best_token.priority:
                                best_token = cand
                                best_service_code = code
                            elif cand.priority == best_token.priority and cand.arrival_time < best_token.arrival_time:
                                best_token = cand
                                best_service_code = code

                    if best_token and best_service_code:
                        # Pop token from queue
                        waiting_queues[best_service_code].remove(best_token)
                        best_token.called_time = sim_time
                        best_token.assigned_counter = counter.name
                        best_token.actual_wait_seconds = max(0, round(best_token.called_time - best_token.arrival_time))

                        # Check no-show probability
                        is_no_show = rng.random() < no_show_rate
                        if is_no_show:
                            best_token.status = "SKIPPED"
                            hold_time = 25.0  # 25 seconds call timeout before skip
                            counter.busy_until = sim_time + hold_time
                            counter.total_busy_time += hold_time
                            best_token.completed_time = sim_time + hold_time
                            skipped_tokens.append(best_token)
                        else:
                            best_token.status = "COMPLETED"
                            base_dur = services_by_code[best_service_code].get("duration", 180) * duration_multiplier
                            # Add Gaussian variation to service duration (mean, std = 0.2*mean)
                            serv_dur = max(30.0, rng.gauss(base_dur, 0.20 * base_dur))
                            best_token.actual_service_seconds = round(serv_dur)
                            counter.busy_until = sim_time + serv_dur
                            counter.total_busy_time += serv_dur
                            counter.tokens_served_count += 1
                            best_token.completed_time = sim_time + serv_dur
                            completed_tokens.append(best_token)

                        counters_dispatched = True

            # If no counter was dispatched and no arrivals left, check if any queue remains
            if not counters_dispatched and arrival_idx >= total_arrivals:
                remaining_in_queues = sum(len(q) for q in waiting_queues.values())
                if remaining_in_queues == 0:
                    break

        # 5. Compile comprehensive telemetry
        effective_sim_duration = max(duration_seconds, sim_time)

        all_processed = completed_tokens + skipped_tokens
        wait_times = [t.actual_wait_seconds for t in all_processed if t.actual_wait_seconds is not None]
        service_times = [t.actual_service_seconds for t in completed_tokens if t.actual_service_seconds is not None]

        priority_waits = [t.actual_wait_seconds for t in all_processed if t.priority == 1 and t.actual_wait_seconds is not None]
        standard_waits = [t.actual_wait_seconds for t in all_processed if t.priority == 0 and t.actual_wait_seconds is not None]

        avg_wait = round(sum(wait_times) / len(wait_times)) if wait_times else 0
        sorted_waits = sorted(wait_times) if wait_times else [0]
        median_wait = sorted_waits[len(sorted_waits) // 2]
        p95_idx = int(math.ceil(0.95 * len(sorted_waits))) - 1
        p95_wait = sorted_waits[min(p95_idx, len(sorted_waits) - 1)]
        max_wait = max(wait_times) if wait_times else 0

        avg_priority_wait = round(sum(priority_waits) / len(priority_waits)) if priority_waits else 0
        avg_standard_wait = round(sum(standard_waits) / len(standard_waits)) if standard_waits else 0
        avg_service_time = round(sum(service_times) / len(service_times)) if service_times else 0

        # Counter utilization
        counter_stats = []
        total_util_pct = 0.0
        for c in counters:
            util_pct = min(100.0, round((c.total_busy_time / effective_sim_duration) * 100.0, 1))
            total_util_pct += util_pct
            counter_stats.append({
                "counter_name": c.name,
                "supported_services": list(c.supported_services),
                "tokens_served": c.tokens_served_count,
                "busy_time_seconds": round(c.total_busy_time),
                "utilization_pct": util_pct,
            })
        avg_counter_utilization = round(total_util_pct / max(1, len(counters)), 1)

        # SLA Breaches
        sla_breaches = sum(1 for w in wait_times if w > target_sla_seconds)
        sla_breach_pct = round((sla_breaches / max(1, len(wait_times))) * 100.0, 1)

        # Throughput per hour
        sim_hours = effective_sim_duration / 3600.0
        throughput_per_hour = round(len(completed_tokens) / max(0.1, sim_hours), 1)

        # Unserved waiting tokens
        unserved_count = sum(len(q) for q in waiting_queues.values())

        # 6. Estimate vs Actual Comparison Analysis
        comparison_points = []
        abs_errors = []
        pct_errors = []

        # Sample up to 20 representative tokens across run
        sample_step = max(1, len(all_processed) // 20)
        for i, t in enumerate(all_processed):
            if t.actual_wait_seconds is not None:
                err = abs(t.actual_wait_seconds - t.estimated_wait_seconds)
                abs_errors.append(err)
                pct_err = err / max(1.0, float(t.actual_wait_seconds))
                pct_errors.append(min(1.0, pct_err))

                if i % sample_step == 0 and len(comparison_points) < 20:
                    comparison_points.append({
                        "token_number": t.display_number,
                        "service_code": t.service_code,
                        "priority": t.priority,
                        "estimated_wait_seconds": t.estimated_wait_seconds,
                        "actual_wait_seconds": t.actual_wait_seconds,
                        "error_seconds": t.actual_wait_seconds - t.estimated_wait_seconds,
                        "accuracy_pct": max(0.0, round((1.0 - min(1.0, pct_err)) * 100.0, 1)),
                    })

        mean_abs_error = round(sum(abs_errors) / len(abs_errors)) if abs_errors else 0
        overall_accuracy_pct = (
            round((1.0 - (sum(pct_errors) / len(pct_errors))) * 100.0, 1)
            if pct_errors
            else 100.0
        )

        # Per-service breakdown
        service_breakdown = {}
        for s in service_categories:
            code = s["code"]
            s_tokens = [t for t in all_processed if t.service_code == code]
            s_waits = [t.actual_wait_seconds for t in s_tokens if t.actual_wait_seconds is not None]
            service_breakdown[code] = {
                "name": s["name"],
                "total_issued": sum(1 for t in all_tokens if t.service_code == code),
                "completed": sum(1 for t in completed_tokens if t.service_code == code),
                "skipped": sum(1 for t in skipped_tokens if t.service_code == code),
                "unserved": len(waiting_queues.get(code, [])),
                "avg_wait_seconds": round(sum(s_waits) / len(s_waits)) if s_waits else 0,
                "max_wait_seconds": max(s_waits) if s_waits else 0,
            }

        return {
            "scenario_key": scenario_key or "custom",
            "scenario_title": config.get("title", "Custom Scenario"),
            "scenario_title_ur": config.get("title_ur", "اپنی مرضی کا منظرنامہ"),
            "random_seed": seed,
            "duration_seconds": round(effective_sim_duration),
            "total_tokens_issued": len(all_tokens),
            "completed_tokens": len(completed_tokens),
            "skipped_tokens": len(skipped_tokens),
            "unserved_waiting_tokens": unserved_count,
            "kpi_metrics": {
                "avg_wait_seconds": avg_wait,
                "median_wait_seconds": median_wait,
                "p95_wait_seconds": p95_wait,
                "max_wait_seconds": max_wait,
                "avg_service_seconds": avg_service_time,
                "avg_priority_wait_seconds": avg_priority_wait,
                "avg_standard_wait_seconds": avg_standard_wait,
                "counter_utilization_pct": avg_counter_utilization,
                "sla_breach_count": sla_breaches,
                "sla_breach_pct": sla_breach_pct,
                "throughput_per_hour": throughput_per_hour,
            },
            "estimate_vs_actual": {
                "mean_absolute_error_seconds": mean_abs_error,
                "overall_accuracy_pct": overall_accuracy_pct,
                "sample_points": comparison_points,
            },
            "counters": counter_stats,
            "service_breakdown": service_breakdown,
            "parameters": {
                "arrival_rate_per_min": arrival_rate_per_min,
                "priority_ratio": priority_ratio,
                "no_show_rate": no_show_rate,
                "service_duration_multiplier": duration_multiplier,
                "target_sla_seconds": target_sla_seconds,
                "active_counters_count": len(counters),
            },
        }

    @classmethod
    async def persist_simulation_run(
        cls,
        session: AsyncSession,
        name: str,
        scenario_key: Optional[str],
        config: Dict[str, Any],
        seed: int,
        results: Dict[str, Any],
    ) -> SimulationRun:
        """
        Persist a completed simulation run in the database with results.
        """
        now = datetime.now(timezone.utc)
        sim_run = SimulationRun(
            name=name,
            scenario_config={
                "scenario_key": scenario_key,
                "config": config,
                "results": results,
            },
            random_seed=seed,
            status=SimulationStatus.COMPLETED,
            started_at=now,
            ended_at=now,
        )
        session.add(sim_run)
        await session.flush()
        return sim_run
