"""
QueueWise AI — Simulation Lab & Counter Optimizer API Endpoints

Provides REST endpoints for:
- Retrieving preset challenge scenarios (A–F)
- Executing deterministic discrete-event simulations
- Querying past simulation telemetry and estimate accuracy
- Calculating optimal counter allocation recommendations
"""
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.service_category import ServiceCategory
from app.models.simulation_run import SimulationRun
from app.models.enums import SimulationStatus
from app.simulation.scenarios import get_all_scenarios, get_scenario
from app.simulation.engine import SimulationEngine
from app.simulation.optimizer import CounterOptimizer
from app.schemas.simulation import (
    ScenarioInfo,
    SimulationRunCreate,
    SimulationRunResponse,
    OptimizerRequest,
    OptimizerResponse,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/scenarios", response_model=List[ScenarioInfo], summary="List preset challenge scenarios")
async def list_scenarios():
    """
    Returns the 6 preset challenge scenarios (A through F)
    with their operational parameters and target characteristics.
    """
    return get_all_scenarios()


@router.get("/scenarios/{scenario_key}", response_model=ScenarioInfo, summary="Get single scenario details")
async def get_single_scenario(scenario_key: str):
    """
    Retrieve definition of a specific challenge scenario.
    """
    try:
        return get_scenario(scenario_key)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_key}' not found.",
        )


@router.post(
    "/runs",
    response_model=SimulationRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute and persist a simulation run",
)
async def create_and_run_simulation(
    payload: SimulationRunCreate,
    persist: bool = Query(True, description="Whether to persist run in database"),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes a discrete-event queue simulation deterministically.
    Calculates wait times, counter utilization, SLA compliance,
    and estimate-vs-actual comparison accuracy.
    """
    # Fetch real services from DB for realistic defaults
    stmt = select(ServiceCategory).where(ServiceCategory.is_active == True)
    res = await db.execute(stmt)
    services_db = res.scalars().all()

    service_specs = None
    if services_db:
        service_specs = [
            {
                "code": s.code,
                "name": s.name,
                "duration": s.default_duration_seconds,
                "weight": 1.0,
            }
            for s in services_db
        ]

    # Build custom overrides from payload
    custom_config = {}
    if payload.duration_seconds is not None:
        custom_config["duration_seconds"] = payload.duration_seconds
    if payload.arrival_rate_per_minute is not None:
        custom_config["arrival_rate_per_minute"] = payload.arrival_rate_per_minute
    if payload.active_counters_count is not None:
        custom_config["active_counters_count"] = payload.active_counters_count
    if payload.priority_ratio is not None:
        custom_config["priority_ratio"] = payload.priority_ratio
    if payload.no_show_rate is not None:
        custom_config["no_show_rate"] = payload.no_show_rate
    if payload.service_duration_multiplier is not None:
        custom_config["service_duration_multiplier"] = payload.service_duration_multiplier
    if payload.target_sla_seconds is not None:
        custom_config["target_sla_seconds"] = payload.target_sla_seconds
    if payload.custom_counter_assignments:
        custom_config["counter_assignments"] = payload.custom_counter_assignments

    # Execute simulation
    try:
        sim_results = SimulationEngine.run_simulation(
            scenario_key=payload.scenario_key,
            custom_config=custom_config,
            seed=payload.random_seed,
            service_categories=service_specs,
        )
    except Exception as e:
        logger.error("simulation_execution_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}",
        )

    run_name = payload.name or f"{sim_results['scenario_title']} (Seed {payload.random_seed})"
    run_id = None
    created_at = None

    if persist:
        sim_run = await SimulationEngine.persist_simulation_run(
            session=db,
            name=run_name,
            scenario_key=payload.scenario_key,
            config=custom_config,
            seed=payload.random_seed,
            results=sim_results,
        )
        await db.commit()
        run_id = sim_run.id
        created_at = sim_run.created_at

    return SimulationRunResponse(
        id=run_id,
        name=run_name,
        scenario_key=sim_results["scenario_key"],
        scenario_title=sim_results["scenario_title"],
        scenario_title_ur=sim_results["scenario_title_ur"],
        random_seed=sim_results["random_seed"],
        duration_seconds=sim_results["duration_seconds"],
        total_tokens_issued=sim_results["total_tokens_issued"],
        completed_tokens=sim_results["completed_tokens"],
        skipped_tokens=sim_results["skipped_tokens"],
        unserved_waiting_tokens=sim_results["unserved_waiting_tokens"],
        kpi_metrics=sim_results["kpi_metrics"],
        estimate_vs_actual=sim_results["estimate_vs_actual"],
        counters=sim_results["counters"],
        service_breakdown=sim_results["service_breakdown"],
        parameters=sim_results["parameters"],
        created_at=created_at,
    )


@router.get("/runs", response_model=List[SimulationRunResponse], summary="List persisted simulation runs")
async def list_simulation_runs(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve history of completed simulation runs ordered by newest first.
    """
    stmt = (
        select(SimulationRun)
        .where(SimulationRun.status == SimulationStatus.COMPLETED)
        .order_by(desc(SimulationRun.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    runs = result.scalars().all()

    response = []
    for r in runs:
        cfg = r.scenario_config or {}
        res = cfg.get("results", {})
        if not res:
            continue
        response.append(
            SimulationRunResponse(
                id=r.id,
                name=r.name or "Simulation Run",
                scenario_key=res.get("scenario_key", "custom"),
                scenario_title=res.get("scenario_title", r.name or "Simulation"),
                scenario_title_ur=res.get("scenario_title_ur", "سمولیشن"),
                random_seed=r.random_seed,
                duration_seconds=res.get("duration_seconds", 1800),
                total_tokens_issued=res.get("total_tokens_issued", 0),
                completed_tokens=res.get("completed_tokens", 0),
                skipped_tokens=res.get("skipped_tokens", 0),
                unserved_waiting_tokens=res.get("unserved_waiting_tokens", 0),
                kpi_metrics=res.get("kpi_metrics", {}),
                estimate_vs_actual=res.get("estimate_vs_actual", {}),
                counters=res.get("counters", []),
                service_breakdown=res.get("service_breakdown", {}),
                parameters=res.get("parameters", {}),
                created_at=r.created_at,
            )
        )
    return response


@router.get("/runs/{run_id}", response_model=SimulationRunResponse, summary="Get single simulation run by ID")
async def get_simulation_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieve telemetry details of a specific simulation run.
    """
    sim_run = await db.get(SimulationRun, run_id)
    if not sim_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run with ID {run_id} not found.",
        )
    cfg = sim_run.scenario_config or {}
    res = cfg.get("results", {})
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation run has no results payload.",
        )

    return SimulationRunResponse(
        id=sim_run.id,
        name=sim_run.name or "Simulation Run",
        scenario_key=res.get("scenario_key", "custom"),
        scenario_title=res.get("scenario_title", sim_run.name or "Simulation"),
        scenario_title_ur=res.get("scenario_title_ur", "سمولیشن"),
        random_seed=sim_run.random_seed,
        duration_seconds=res.get("duration_seconds", 1800),
        total_tokens_issued=res.get("total_tokens_issued", 0),
        completed_tokens=res.get("completed_tokens", 0),
        skipped_tokens=res.get("skipped_tokens", 0),
        unserved_waiting_tokens=res.get("unserved_waiting_tokens", 0),
        kpi_metrics=res.get("kpi_metrics", {}),
        estimate_vs_actual=res.get("estimate_vs_actual", {}),
        counters=res.get("counters", []),
        service_breakdown=res.get("service_breakdown", {}),
        parameters=res.get("parameters", {}),
        created_at=sim_run.created_at,
    )


@router.post(
    "/optimizer/recommend",
    response_model=OptimizerResponse,
    summary="Compute optimal counter allocation recommendations",
)
async def recommend_counter_allocation(
    payload: OptimizerRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Calculates deterministic counter allocation recommendations using M/M/c queue theory.
    Identifies bottlenecks, calculates expected wait reductions, and suggests staff reassignments.
    """
    services_to_optimize = []

    if payload.services:
        for s in payload.services:
            services_to_optimize.append({
                "code": s.code,
                "name": s.name,
                "arrival_rate_per_min": s.arrival_rate_per_min,
                "avg_duration_seconds": s.avg_duration_seconds,
                "current_counters": s.current_counters,
            })
    else:
        # Default: pull active services from database
        stmt = select(ServiceCategory).where(ServiceCategory.is_active == True)
        res = await db.execute(stmt)
        services_db = res.scalars().all()
        if not services_db:
            services_to_optimize = [
                {"code": "GEN", "name": "General Inquiries", "arrival_rate_per_min": 1.5, "avg_duration_seconds": 180, "current_counters": 1},
                {"code": "DOC", "name": "Document Verification", "arrival_rate_per_min": 1.0, "avg_duration_seconds": 240, "current_counters": 1},
                {"code": "CASH", "name": "Cash & Fee Payments", "arrival_rate_per_min": 0.5, "avg_duration_seconds": 150, "current_counters": 1},
            ]
        else:
            for s in services_db:
                services_to_optimize.append({
                    "code": s.code,
                    "name": s.name,
                    "arrival_rate_per_min": 1.2,
                    "avg_duration_seconds": float(s.default_duration_seconds),
                    "current_counters": 1,
                })

    optimization_result = CounterOptimizer.optimize_allocation(
        services=services_to_optimize,
        total_counters=payload.total_counters,
        target_sla_seconds=payload.target_sla_seconds,
    )

    return OptimizerResponse(**optimization_result)
