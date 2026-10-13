"""
QueueWise AI — Simulation and Optimizer Pydantic Schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from pydantic import BaseModel, Field


class ScenarioInfo(BaseModel):
    """Metadata describing a challenge scenario."""
    key: str
    code: str
    title: str
    title_ur: str
    category: str
    badge_color: str
    description: str
    description_ur: str
    duration_seconds: int
    arrival_rate_per_minute: float
    active_counters_count: int
    priority_ratio: float
    no_show_rate: float
    service_duration_multiplier: float
    target_sla_seconds: int
    expected_outcome: str


class SimulationRunCreate(BaseModel):
    """Request payload to initiate a simulation run."""
    name: Optional[str] = Field(None, description="Human-friendly label for this run")
    scenario_key: Optional[str] = Field("scenario_a", description="Preset scenario key (scenario_a..scenario_f)")
    random_seed: int = Field(42, description="RNG seed for deterministic replay")
    duration_seconds: Optional[int] = Field(1800, description="Simulation duration in seconds")
    arrival_rate_per_minute: Optional[float] = Field(None, description="Override arrival rate")
    active_counters_count: Optional[int] = Field(None, description="Override counter count")
    priority_ratio: Optional[float] = Field(None, description="Override priority ratio (0.0 to 1.0)")
    no_show_rate: Optional[float] = Field(None, description="Override no-show rate (0.0 to 1.0)")
    service_duration_multiplier: Optional[float] = Field(None, description="Override service duration multiplier")
    target_sla_seconds: Optional[int] = Field(None, description="Target SLA maximum wait threshold")
    custom_counter_assignments: Optional[Dict[str, List[str]]] = Field(
        None, description="Direct counter service mapping, e.g. {'Counter 1': ['GEN', 'DOC']}"
    )


class EstimateVsActualPoint(BaseModel):
    """Comparison sample point for estimator accuracy."""
    token_number: str
    service_code: str
    priority: int
    estimated_wait_seconds: int
    actual_wait_seconds: int
    error_seconds: int
    accuracy_pct: float


class EstimateVsActualAnalysis(BaseModel):
    """Overall estimator accuracy metrics."""
    mean_absolute_error_seconds: int
    overall_accuracy_pct: float
    sample_points: List[EstimateVsActualPoint]


class KPIMetrics(BaseModel):
    """Core key performance indicators from the simulation."""
    avg_wait_seconds: int
    median_wait_seconds: int
    p95_wait_seconds: int
    max_wait_seconds: int
    avg_service_seconds: int
    avg_priority_wait_seconds: int
    avg_standard_wait_seconds: int
    counter_utilization_pct: float
    sla_breach_count: int
    sla_breach_pct: float
    throughput_per_hour: float


class CounterPerformance(BaseModel):
    """Metrics for an individual counter."""
    counter_name: str
    supported_services: List[str]
    tokens_served: int
    busy_time_seconds: int
    utilization_pct: float


class ServicePerformance(BaseModel):
    """Metrics for a service category."""
    name: str
    total_issued: int
    completed: int
    skipped: int
    unserved: int
    avg_wait_seconds: int
    max_wait_seconds: int


class SimulationRunResponse(BaseModel):
    """Complete simulation run response with telemetry."""
    id: Optional[uuid.UUID] = None
    name: str
    scenario_key: str
    scenario_title: str
    scenario_title_ur: str
    random_seed: int
    duration_seconds: int
    total_tokens_issued: int
    completed_tokens: int
    skipped_tokens: int
    unserved_waiting_tokens: int
    kpi_metrics: KPIMetrics
    estimate_vs_actual: EstimateVsActualAnalysis
    counters: List[CounterPerformance]
    service_breakdown: Dict[str, ServicePerformance]
    parameters: Dict[str, Any]
    created_at: Optional[datetime] = None


class ServiceDemandSpec(BaseModel):
    """Demand profile for a service in optimization requests."""
    code: str
    name: str
    arrival_rate_per_min: float = 1.0
    avg_duration_seconds: float = 180.0
    current_counters: int = 1


class OptimizerRequest(BaseModel):
    """Payload to request optimal counter allocation."""
    total_counters: int = Field(3, description="Available pool of counters")
    target_sla_seconds: float = Field(600.0, description="Target SLA threshold in seconds")
    services: Optional[List[ServiceDemandSpec]] = Field(
        None, description="Optional service demand list (defaults to system services if omitted)"
    )


class ServiceOptimizationResult(BaseModel):
    """Optimization allocation and expected outcome for a service."""
    service_code: str
    service_name: str
    current_counters: int
    recommended_counters: int
    offered_load_erlangs: float
    current_utilization_pct: float
    recommended_utilization_pct: float
    current_wait_seconds: int
    recommended_wait_seconds: int
    wait_reduction_seconds: int


class OptimizerResponse(BaseModel):
    """Output recommendation from the Counter Optimizer."""
    total_available_counters: int
    target_sla_seconds: float
    current_avg_wait_seconds: int
    recommended_avg_wait_seconds: int
    wait_reduction_pct: float
    current_sla_compliance_pct: float
    recommended_sla_compliance_pct: float
    services: List[ServiceOptimizationResult]
    actionable_recommendations: List[str]
    actionable_recommendations_ur: List[str]
