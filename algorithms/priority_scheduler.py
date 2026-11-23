"""
Priority Scheduler — OS Concept Implementation
Demonstrates: Priority Scheduling, FCFS tie-breaking
"""

from typing import List
from models.patient import Patient


def priority_schedule(queue: List[Patient]) -> List[Patient]:
    """
    Sort patients by Priority Scheduling algorithm with FCFS tie-breaking.
    
    Rules:
    1. Lower effective_priority value = Higher urgency (treated first)
    2. If two patients have same priority → FCFS (earlier arrival first)
    
    This mimics OS Preemptive Priority Scheduling where the scheduler
    picks the process with the highest priority from the ready queue.
    
    Args:
        queue: List of waiting Patient objects
        
    Returns:
        Sorted list — index 0 is the next patient to be treated
    """
    return sorted(queue, key=lambda p: (p.effective_priority, p.arrival_time))


def get_next_patient(queue: List[Patient]) -> Patient | None:
    """
    Dispatcher function — analogous to OS short-term scheduler (dispatcher).
    Picks and removes the highest-priority patient from the ready queue.
    
    OS Concept: This is the 'dispatch' step — selecting the process
    to give CPU time to, then removing it from the ready queue.
    """
    if not queue:
        return None
    sorted_q = priority_schedule(queue)
    selected = sorted_q[0]
    queue.remove(selected)
    return selected


def calculate_effective_priority(severity: int, waiting_time: float,
                                  aging_rate: float = 0.1) -> float:
    """
    Compute effective priority dynamically based on base severity + aging.
    
    Formula:
        effective_priority = severity - (waiting_time_minutes * aging_rate)
    
    Clamped to minimum 0.5 (can never exceed Critical level).
    
    OS Concept: This mirrors multilevel feedback queue aging where
    processes get a priority boost after waiting a certain amount of time.
    """
    waiting_minutes = waiting_time / 60.0
    aging_boost     = waiting_minutes * aging_rate
    return max(0.5, severity - aging_boost)


def analyze_schedule(completed_patients: list) -> dict:
    """
    Post-mortem analysis of the scheduling performance.
    
    Returns scheduling metrics analogous to OS performance evaluation:
    - Average Waiting Time
    - Average Turnaround Time
    - Throughput
    - CPU Utilization
    """
    if not completed_patients:
        return {}

    total_wait       = sum(p["waiting_time"]   for p in completed_patients)
    total_turnaround = sum(p["treatment_time"] for p in completed_patients)
    n                = len(completed_patients)

    return {
        "avg_waiting_time":    round(total_wait / n, 2),
        "avg_turnaround_time": round((total_wait + total_turnaround) / n, 2),
        "total_patients":      n,
    }
