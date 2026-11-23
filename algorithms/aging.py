"""
Aging Algorithm — OS Concept Implementation
Demonstrates: Starvation Prevention via Dynamic Priority Boosting
"""

import time
from typing import List
from models.patient import Patient


class AgingManager:
    """
    Implements the Aging algorithm for starvation prevention.
    
    OS Concept:
    In priority scheduling, low-priority processes may never execute
    if high-priority processes keep arriving (starvation).
    
    Solution: Gradually increase the priority of waiting processes
    over time so they eventually get scheduled.
    
    Real-world OS Example:
    - Linux completely fair scheduler (CFS) uses similar techniques
    - Windows uses priority boosting for foreground threads
    - Multilevel Feedback Queue: processes promoted to higher queues
    """

    def __init__(self, aging_rate: float = 0.15, interval_seconds: float = 15.0,
                 starvation_threshold: float = 120.0):
        """
        Args:
            aging_rate:            Priority improvement per aging tick
            interval_seconds:      Seconds between aging applications
            starvation_threshold:  Seconds after which starvation is flagged
        """
        self.aging_rate            = aging_rate
        self.interval_seconds      = interval_seconds
        self.starvation_threshold  = starvation_threshold
        self.last_tick             = time.time()
        self.total_ticks           = 0
        self.priority_changes      = []   # Audit log of aging events

    def tick(self, ready_queue: List[Patient]) -> List[dict]:
        """
        Apply one aging tick to all patients in the ready queue.
        
        Returns list of aging events (for UI notification):
        Each event: {patient_id, name, old_priority, new_priority, starving}
        """
        events = []
        now    = time.time()

        for patient in ready_queue:
            # Update waiting time
            patient.waiting_time = now - patient.arrival_time
            old_p = patient.effective_priority

            # Apply aging
            delta = patient.apply_aging(self.aging_rate)
            new_p = patient.effective_priority

            is_starving = patient.waiting_time >= self.starvation_threshold

            if delta > 0.001:   # Only log meaningful changes
                event = {
                    "patient_id":    patient.patient_id,
                    "name":          patient.name,
                    "old_priority":  round(old_p, 2),
                    "new_priority":  round(new_p, 2),
                    "delta":         round(delta, 3),
                    "waiting_time":  round(patient.waiting_time, 1),
                    "is_starving":   is_starving,
                    "timestamp":     time.strftime("%H:%M:%S"),
                }
                events.append(event)
                self.priority_changes.append(event)

        self.last_tick   = now
        self.total_ticks += 1
        return events

    def should_tick(self) -> bool:
        """Check if enough time has passed for the next aging tick."""
        return (time.time() - self.last_tick) >= self.interval_seconds

    def get_audit_log(self) -> List[dict]:
        """Return the last 100 aging events for the report view."""
        return self.priority_changes[-100:]

    def reset(self):
        self.last_tick    = time.time()
        self.total_ticks  = 0
        self.priority_changes.clear()


def explain_aging() -> str:
    """Return a human-readable explanation of the aging algorithm."""
    return """
    AGING ALGORITHM — Starvation Prevention
    =========================================
    Problem:
      In pure priority scheduling, low-severity patients (like those
      with minor ailments) may NEVER be treated if critical patients
      keep arriving. This is called STARVATION.
    
    Solution (Aging):
      Every {interval} seconds, we reduce the effective_priority of
      all waiting patients by {rate}. Since lower number = higher
      urgency, waiting patients gradually become more urgent.
    
    Example:
      Patient Sara (Fever, severity=4) arrives.
      Critical patients keep arriving.
      
      t=0:    Sara's priority = 4.0
      t=15s:  Sara's priority = 3.85  (after 1 aging tick)
      t=30s:  Sara's priority = 3.70
      t=120s: Sara's priority = 2.80  (now equivalent to High!)
      t=240s: Sara's priority = 1.60  (nearly Critical!)
    
    This guarantees Sara will eventually be treated — no starvation!
    """.format(interval=15, rate=0.15)
