"""
QueueWise AI — Preset Challenge Simulation Scenarios (A–F)

Standardized demand, operational, and stress-testing scenarios
designed for evaluation in hackathons and real-world testing.
"""
from typing import Dict, Any, List

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "scenario_a": {
        "key": "scenario_a",
        "code": "A",
        "title": "Baseline Operations",
        "title_ur": "معمول کے مطابق سروس (بیس لائن)",
        "category": "Baseline",
        "badge_color": "emerald",
        "description": "Steady, predictable citizen arrival rate with balanced service durations and all 3 service counters operational.",
        "description_ur": "شہریوں کی باقاعدہ آمد، معیاری دورانیہ اور تمام کاؤنٹرز فعال۔",
        "duration_seconds": 1800,  # 30 min simulation window
        "arrival_rate_per_minute": 1.2,
        "active_counters_count": 3,
        "priority_ratio": 0.10,  # 10% senior / emergency
        "no_show_rate": 0.05,    # 5% no-show
        "service_duration_multiplier": 1.0,
        "target_sla_seconds": 600,  # 10 minute SLA target
        "counter_assignments": {
            "Counter 1": ["GEN"],
            "Counter 2": ["DOC"],
            "Counter 3": ["CASH"],
        },
        "expected_outcome": "Low wait times (< 5 min), high SLA compliance (> 95%), balanced counter utilization (~60-70%).",
    },
    "scenario_b": {
        "key": "scenario_b",
        "code": "B",
        "title": "Morning Demand Surge",
        "title_ur": "صبح کے اوقات میں رش کا دباؤ",
        "category": "Demand Spike",
        "badge_color": "amber",
        "description": "Sudden 3.5x spike in citizen arrivals during the opening rush hour, causing rapid queue accumulation.",
        "description_ur": "صبح کے آغاز پر اچانک 3.5 گنا زیادہ شہریوں کی آمد سے قطاروں میں اضافہ۔",
        "duration_seconds": 1800,
        "arrival_rate_per_minute": 4.0,  # 4 citizens per min (surging)
        "active_counters_count": 3,
        "priority_ratio": 0.10,
        "no_show_rate": 0.05,
        "service_duration_multiplier": 1.0,
        "target_sla_seconds": 600,
        "counter_assignments": {
            "Counter 1": ["GEN"],
            "Counter 2": ["DOC"],
            "Counter 3": ["CASH"],
        },
        "expected_outcome": "Queue depth surges, average wait time spikes (> 15 min), significant SLA breaches occur without optimization.",
    },
    "scenario_c": {
        "key": "scenario_c",
        "code": "C",
        "title": "Staff Shortage & Counter Outage",
        "title_ur": "عملے کی کمی اور کاؤنٹر کی بندش",
        "category": "Operational Stress",
        "badge_color": "rose",
        "description": "Unexpected 66% counter capacity reduction (2 out of 3 counters closed) due to emergency staff absence or system terminal downtime.",
        "description_ur": "عملے کی غیر حاضری کے باعث 3 میں سے 2 کاؤنٹرز بند، سروس کی صلاحیت کم۔",
        "duration_seconds": 1800,
        "arrival_rate_per_minute": 1.5,
        "active_counters_count": 1,  # Only 1 counter handling all services
        "priority_ratio": 0.10,
        "no_show_rate": 0.05,
        "service_duration_multiplier": 1.0,
        "target_sla_seconds": 600,
        "counter_assignments": {
            "Counter 1": ["GEN", "DOC", "CASH"],
        },
        "expected_outcome": "Severe bottleneck on the single counter, wait times climb linearly, wait estimator flags queue stall.",
    },
    "scenario_d": {
        "key": "scenario_d",
        "code": "D",
        "title": "Complex Documentation Cases",
        "title_ur": "پیچیدہ کیسز اور سروس میں تاخیر",
        "category": "Service Inflation",
        "badge_color": "purple",
        "description": "Average service duration inflates by 2.5x due to complex verification paperwork, biometric retries, or regulatory audits.",
        "description_ur": "دستاویزات کی تصدیق اور بائیو میٹرک مسائل کی وجہ سے سروس کا وقت 2.5 گنا بڑھ گیا۔",
        "duration_seconds": 1800,
        "arrival_rate_per_minute": 1.2,
        "active_counters_count": 3,
        "priority_ratio": 0.10,
        "no_show_rate": 0.05,
        "service_duration_multiplier": 2.5,  # 2.5x longer service durations
        "target_sla_seconds": 900,
        "counter_assignments": {
            "Counter 1": ["GEN"],
            "Counter 2": ["DOC"],
            "Counter 3": ["CASH"],
        },
        "expected_outcome": "Counters continuously occupied at 95%+ utilization, service throughput drops by 60%.",
    },
    "scenario_e": {
        "key": "scenario_e",
        "code": "E",
        "title": "High Citizen No-Show Rate",
        "title_ur": "غیر حاضر شہریوں کا زیادہ تناسب",
        "category": "Queue Churn",
        "badge_color": "sky",
        "description": "35% of called citizens abandon the queue or fail to show up, testing the system's rapid skipping and recovery mechanisms.",
        "description_ur": "35 فیصد شہری کال کرنے پر حاضر نہیں ہوتے، اسکیپ اور ری کال کے نظام کا امتحان۔",
        "duration_seconds": 1800,
        "arrival_rate_per_minute": 2.2,
        "active_counters_count": 3,
        "priority_ratio": 0.10,
        "no_show_rate": 0.35,  # 35% no show
        "service_duration_multiplier": 1.0,
        "target_sla_seconds": 600,
        "counter_assignments": {
            "Counter 1": ["GEN"],
            "Counter 2": ["DOC"],
            "Counter 3": ["CASH"],
        },
        "expected_outcome": "High skip rate, apparent queue drops faster than expected, actual wait time for present citizens is much shorter than initial estimates.",
    },
    "scenario_f": {
        "key": "scenario_f",
        "code": "F",
        "title": "Priority & Vulnerable Influx",
        "title_ur": "خصوصی اور بزرگ شہریوں کا بہاؤ",
        "category": "Triage & Priority",
        "badge_color": "indigo",
        "description": "40% of arriving citizens require priority treatment (senior citizens, pregnant mothers, differently-abled, medical emergencies).",
        "description_ur": "40 فیصد بزرگ، معذور یا ہنگامی کیسز، جنہیں عام قطار پر ترجیح دی جاتی ہے۔",
        "duration_seconds": 1800,
        "arrival_rate_per_minute": 1.8,
        "active_counters_count": 3,
        "priority_ratio": 0.40,  # 40% priority
        "no_show_rate": 0.05,
        "service_duration_multiplier": 1.0,
        "target_sla_seconds": 600,
        "counter_assignments": {
            "Counter 1": ["GEN"],
            "Counter 2": ["DOC"],
            "Counter 3": ["CASH"],
        },
        "expected_outcome": "Priority citizens experience virtually zero wait (< 2 min), while standard FIFO tokens experience pre-emption and longer delays.",
    },
}


def get_all_scenarios() -> List[Dict[str, Any]]:
    """Return all preset scenario definitions as a list."""
    return list(SCENARIOS.values())


def get_scenario(key: str) -> Dict[str, Any]:
    """Retrieve a scenario definition by key."""
    if key not in SCENARIOS:
        raise KeyError(f"Scenario '{key}' not found. Available scenarios: {list(SCENARIOS.keys())}")
    return SCENARIOS[key]
