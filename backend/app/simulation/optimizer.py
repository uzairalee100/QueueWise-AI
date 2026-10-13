"""
QueueWise AI — Counter Allocation Optimizer

Deterministic optimization engine using multi-server queue theory (M/M/c & Erlang approximation)
to recommend optimal counter allocation across service categories.
Eliminates queue bottlenecks, balances counter utilization, and minimizes citizen wait times.
"""
from typing import Dict, Any, List, Optional
import math


class CounterOptimizer:
    """Intelligent, deterministic counter allocation optimizer."""

    @staticmethod
    def calculate_offered_load(arrival_rate_per_min: float, avg_duration_seconds: float) -> float:
        """
        Calculate offered load (traffic intensity in Erlangs):
        a = lambda / mu = (arrivals/sec) * (avg_duration_seconds)
        """
        arrivals_per_second = max(0.001, arrival_rate_per_min / 60.0)
        return arrivals_per_second * avg_duration_seconds

    @classmethod
    def estimate_wait_seconds(
        cls,
        offered_load: float,
        num_counters: int,
        avg_duration_seconds: float,
        time_horizon_seconds: float = 1800.0,
    ) -> float:
        """
        Estimate expected waiting time in queue given offered load and counter count.
        Uses M/M/c approximation when utilization < 1, and fluid bottleneck backlog when >= 1.
        """
        if num_counters <= 0:
            return time_horizon_seconds  # Maximum wait / stalled

        utilization = offered_load / float(num_counters)

        if utilization >= 0.99:
            # Overloaded/bottlenecked queue: backlog accumulates
            # More counters drain the queue faster, proportionally reducing wait times
            unserved_fraction = max(0.05, 1.0 - (float(num_counters) / max(0.01, offered_load)))
            accumulated_wait = (unserved_fraction * (time_horizon_seconds / 2.0)) + (avg_duration_seconds / float(num_counters))
            return max(avg_duration_seconds, accumulated_wait)

        # Stable queue approximation: Sakasegawa formula / M/M/c wait
        power = max(1.0, math.sqrt(2.0 * (num_counters + 1.0)) - 1.0)
        p_factor = math.pow(utilization, power)
        w_q = (p_factor / (num_counters * (1.0 - utilization))) * avg_duration_seconds
        return max(5.0, w_q)

    @classmethod
    def optimize_allocation(
        cls,
        services: List[Dict[str, Any]],
        total_counters: int,
        target_sla_seconds: float = 600.0,
        time_horizon_seconds: float = 1800.0,
    ) -> Dict[str, Any]:
        """
        Compute optimal counter allocation across services.

        Args:
            services: List of dicts, each with:
                - code: str (e.g. "GEN")
                - name: str (e.g. "General Inquiries")
                - arrival_rate_per_min: float
                - avg_duration_seconds: float
                - current_counters: int
            total_counters: Total number of physical counters available
            target_sla_seconds: Target maximum wait time for SLA compliance (default 600s / 10m)
            time_horizon_seconds: Operating window duration (default 1800s / 30m)

        Returns:
            Dict containing current vs recommended allocations, predicted wait reductions,
            utilization rates, and actionable staff recommendations.
        """
        if not services:
            return {"error": "No services provided"}

        num_services = len(services)
        effective_total_counters = max(num_services, total_counters)

        # 1. Compute current metrics
        service_loads = {}
        for s in services:
            code = s["code"]
            arr = float(s.get("arrival_rate_per_min", 1.0))
            dur = float(s.get("avg_duration_seconds", 180.0))
            load = cls.calculate_offered_load(arr, dur)
            service_loads[code] = {
                "service": s,
                "offered_load": load,
                "arrival_rate": arr,
                "duration": dur,
                "current_counters": max(1, int(s.get("current_counters", 1))),
            }

        # 2. Greedy optimization algorithm:
        # Start by giving at least 1 counter to every service
        allocation = {code: 1 for code in service_loads}
        remaining_counters = effective_total_counters - num_services

        # Prioritize services that need counters to not be bottlenecked (load > counters)
        for code, data in service_loads.items():
            needed_for_stability = int(math.ceil(data["offered_load"]))
            if needed_for_stability > allocation[code] and remaining_counters > 0:
                add = min(needed_for_stability - allocation[code], remaining_counters)
                allocation[code] += add
                remaining_counters -= add

        # Distribute remaining counters to achieve maximum marginal wait reduction
        while remaining_counters > 0:
            best_code = None
            max_reduction = -1.0

            for code, data in service_loads.items():
                c_now = allocation[code]
                wait_now = cls.estimate_wait_seconds(
                    data["offered_load"], c_now, data["duration"], time_horizon_seconds
                )
                wait_next = cls.estimate_wait_seconds(
                    data["offered_load"], c_now + 1, data["duration"], time_horizon_seconds
                )
                # Weighted by arrival rate so services with more people get priority
                marginal_benefit = (wait_now - wait_next) * data["arrival_rate"]
                if marginal_benefit > max_reduction:
                    max_reduction = marginal_benefit
                    best_code = code

            if best_code is not None and max_reduction > 0:
                allocation[best_code] += 1
                remaining_counters -= 1
            else:
                # If marginal benefit is flat, distribute evenly to highest load
                highest_load_code = max(service_loads.keys(), key=lambda k: service_loads[k]["offered_load"])
                allocation[highest_load_code] += 1
                remaining_counters -= 1

        # 3. Calculate before vs after statistics
        current_total_wait_weighted = 0.0
        optimized_total_wait_weighted = 0.0
        total_arrivals = sum(d["arrival_rate"] for d in service_loads.values())

        per_service_results = []
        actionable_steps_en = []
        actionable_steps_ur = []

        current_sla_compliant = 0.0
        optimized_sla_compliant = 0.0

        for code, data in service_loads.items():
            s_name = data["service"].get("name", code)
            curr_c = data["current_counters"]
            rec_c = allocation[code]

            curr_wait = cls.estimate_wait_seconds(
                data["offered_load"], curr_c, data["duration"], time_horizon_seconds
            )
            opt_wait = cls.estimate_wait_seconds(
                data["offered_load"], rec_c, data["duration"], time_horizon_seconds
            )

            curr_util = min(150.0, round((data["offered_load"] / float(curr_c)) * 100.0, 1))
            opt_util = min(100.0, round((data["offered_load"] / float(rec_c)) * 100.0, 1))

            current_total_wait_weighted += curr_wait * data["arrival_rate"]
            optimized_total_wait_weighted += opt_wait * data["arrival_rate"]

            # SLA compliance estimate
            if curr_wait <= target_sla_seconds:
                current_sla_compliant += data["arrival_rate"]
            else:
                current_sla_compliant += data["arrival_rate"] * max(0.1, target_sla_seconds / curr_wait)

            if opt_wait <= target_sla_seconds:
                optimized_sla_compliant += data["arrival_rate"]
            else:
                optimized_sla_compliant += data["arrival_rate"] * max(0.1, target_sla_seconds / opt_wait)

            diff = rec_c - curr_c
            if diff > 0:
                actionable_steps_en.append(
                    f"Assign +{diff} additional counter(s) to {s_name} ({code}) to clear bottleneck (utilization drops from {curr_util}% to {opt_util}%)."
                )
                actionable_steps_ur.append(
                    f"{s_name} ({code}) کے لیے +{diff} اضافی کاؤنٹر مختص کریں تاکہ قطار کا بوجھ ختم ہو سکے۔"
                )
            elif diff < 0:
                actionable_steps_en.append(
                    f"Reassign {-diff} counter(s) from {s_name} ({code}) — demand is low and counters are underutilized ({curr_util}%)."
                )
                actionable_steps_ur.append(
                    f"{s_name} ({code}) سے {-diff} کاؤنٹر دوسرے شعبے میں منتقل کریں کیونکہ یہاں بوجھ کم ہے۔"
                )

            per_service_results.append({
                "service_code": code,
                "service_name": s_name,
                "current_counters": curr_c,
                "recommended_counters": rec_c,
                "offered_load_erlangs": round(data["offered_load"], 2),
                "current_utilization_pct": curr_util,
                "recommended_utilization_pct": opt_util,
                "current_wait_seconds": round(curr_wait),
                "recommended_wait_seconds": round(opt_wait),
                "wait_reduction_seconds": max(0, round(curr_wait - opt_wait)),
            })

        curr_avg_wait = (
            round(current_total_wait_weighted / max(0.01, total_arrivals))
            if total_arrivals > 0
            else 0
        )
        opt_avg_wait = (
            round(optimized_total_wait_weighted / max(0.01, total_arrivals))
            if total_arrivals > 0
            else 0
        )

        reduction_pct = 0.0
        if curr_avg_wait > 0:
            reduction_pct = round(((curr_avg_wait - opt_avg_wait) / float(curr_avg_wait)) * 100.0, 1)

        curr_sla_pct = round((current_sla_compliant / max(0.01, total_arrivals)) * 100.0, 1)
        opt_sla_pct = round((optimized_sla_compliant / max(0.01, total_arrivals)) * 100.0, 1)

        if not actionable_steps_en:
            actionable_steps_en.append("Current counter allocation is already optimal for current load.")
            actionable_steps_ur.append("موجودہ کاؤنٹر کی ترتیب موجودہ بوجھ کے لیے پہلے سے ہی بہترین ہے۔")

        return {
            "total_available_counters": effective_total_counters,
            "target_sla_seconds": target_sla_seconds,
            "current_avg_wait_seconds": curr_avg_wait,
            "recommended_avg_wait_seconds": opt_avg_wait,
            "wait_reduction_pct": max(0.0, reduction_pct),
            "current_sla_compliance_pct": min(100.0, curr_sla_pct),
            "recommended_sla_compliance_pct": min(100.0, opt_sla_pct),
            "services": per_service_results,
            "actionable_recommendations": actionable_steps_en,
            "actionable_recommendations_ur": actionable_steps_ur,
        }
