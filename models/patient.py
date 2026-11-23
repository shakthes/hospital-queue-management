"""
Patient Model - Represents a Process in OS terminology
Each patient = One process waiting to be scheduled (treated)
"""

import time
from datetime import datetime


class Patient:
    """
    Represents a patient (analogous to a Process in OS).
    
    OS Concepts:
    - Patient ID       → Process ID (PID)
    - Severity Level   → Initial Priority
    - Arrival Time     → Process Arrival Time
    - Waiting Time     → Time spent in Ready Queue
    - Effective Priority → Dynamic priority (after Aging)
    - Status           → Process State (Ready / Running / Terminated)
    """

    # Process States
    STATE_WAITING    = "waiting"      # Ready Queue
    STATE_TREATMENT  = "treatment"    # Running (CPU Burst)
    STATE_COMPLETED  = "completed"    # Terminated
    STATE_REGISTERED = "registered"   # Just arrived (new)

    # Severity-to-Priority Mapping
    SEVERITY_MAP = {
        1: "Critical",
        2: "High",
        3: "Medium",
        4: "Low"
    }

    SEVERITY_COLORS = {
        1: "#FF3B30",   # Red
        2: "#FF9500",   # Orange
        3: "#FFCC00",   # Yellow
        4: "#34C759"    # Green
    }

    _id_counter = 1  # Auto-increment PID (simulated by class variable)

    def __init__(self, name: str, age: int, disease: str, severity: int):
        self.patient_id    = f"P{Patient._id_counter:03d}"
        Patient._id_counter += 1

        self.name          = name
        self.age           = age
        self.disease       = disease
        self.severity      = severity            # Base priority (1=Critical … 4=Low)
        self.arrival_time  = time.time()         # Unix timestamp (Arrival Time)
        self.arrival_dt    = datetime.now()      # Human-readable

        self.waiting_time  = 0.0                 # Seconds waited in ready queue
        self.treatment_time= 0.0                 # Seconds spent in treatment
        self.start_time    = None                # When treatment began
        self.end_time      = None                # When treatment ended

        # Effective (dynamic) priority = severity + aging_boost
        # Lower number = higher priority (like OS priority values)
        self.effective_priority = float(severity)
        self.aging_boost        = 0.0            # Accumulated aging reduction

        self.status        = self.STATE_WAITING
        self.doctor_id     = None                # Which doctor/resource assigned

        # For Gantt Chart
        self.gantt_start   = None
        self.gantt_end     = None

    def apply_aging(self, aging_rate: float = 0.1):
        """
        Aging Algorithm: Reduce effective priority over time.
        This prevents starvation of low-priority patients.
        
        OS Concept: Same as aging in multilevel feedback queue —
        a process that waits too long gets bumped up to a higher queue.
        """
        # Minimum effective priority is 0.5 (can never exceed Critical)
        old_priority = self.effective_priority
        self.aging_boost += aging_rate
        self.effective_priority = max(0.5, self.severity - self.aging_boost)
        return old_priority - self.effective_priority   # delta (how much improved)

    def update_waiting_time(self):
        """Recalculate waiting time since arrival (or since last check)."""
        if self.status == self.STATE_WAITING:
            self.waiting_time = time.time() - self.arrival_time

    def start_treatment(self, doctor_id: str):
        """Mark patient as being treated — analogous to dispatch by CPU scheduler."""
        self.status      = self.STATE_TREATMENT
        self.doctor_id   = doctor_id
        self.start_time  = time.time()
        self.waiting_time = self.start_time - self.arrival_time  # Final wait time
        self.gantt_start = self.start_time

    def complete_treatment(self):
        """Mark patient as treated — analogous to process termination."""
        self.status          = self.STATE_COMPLETED
        self.end_time        = time.time()
        self.treatment_time  = self.end_time - self.start_time
        self.gantt_end       = self.end_time

    def to_dict(self) -> dict:
        """Serialize to dictionary (for JSON/DB storage)."""
        return {
            "patient_id":          self.patient_id,
            "name":                self.name,
            "age":                 self.age,
            "disease":             self.disease,
            "severity":            self.severity,
            "severity_label":      self.SEVERITY_MAP.get(self.severity, "Unknown"),
            "severity_color":      self.SEVERITY_COLORS.get(self.severity, "#888"),
            "arrival_time":        self.arrival_dt.strftime("%H:%M:%S"),
            "waiting_time":        round(self.waiting_time, 1),
            "treatment_time":      round(self.treatment_time, 1),
            "effective_priority":  round(self.effective_priority, 2),
            "aging_boost":         round(self.aging_boost, 2),
            "status":              self.status,
            "doctor_id":           self.doctor_id,
            "gantt_start":         self.gantt_start,
            "gantt_end":           self.gantt_end,
        }

    def __repr__(self):
        return (f"Patient({self.patient_id}, {self.name}, "
                f"severity={self.severity}, eff={self.effective_priority:.2f}, "
                f"status={self.status})")
