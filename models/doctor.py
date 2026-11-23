"""
Doctor Model - Represents a CPU/Resource in OS terminology
Each doctor = One CPU that can run one process at a time (Mutex)
"""

import time
from datetime import datetime


class Doctor:
    """
    Represents a doctor (analogous to a CPU/Resource in OS).
    
    OS Concepts:
    - Doctor ID     → CPU ID
    - is_available  → CPU idle/busy state
    - Semaphore     → Controls access to doctor resource
    - Mutex Lock    → Prevents two patients from being assigned same doctor
    """

    SPECIALIZATIONS = {
        "Dr. Sharma":   "Cardiology",
        "Dr. Patel":    "Neurology",
        "Dr. Gupta":    "General Medicine",
        "Dr. Reddy":    "Orthopedics",
        "Dr. Mehta":    "Emergency",
    }

    def __init__(self, doctor_id: str, name: str, specialization: str = "General"):
        self.doctor_id      = doctor_id
        self.name           = name
        self.specialization = specialization

        # Semaphore/Mutex state
        self.is_available   = True       # Semaphore value (0=busy, 1=free)
        self._lock          = False      # Mutex flag (True = locked)

        # Current patient being treated
        self.current_patient_id = None
        self.treatment_start    = None

        # Statistics
        self.total_patients_treated = 0
        self.total_busy_time        = 0.0
        self.idle_since             = time.time()

    def acquire(self, patient_id: str) -> bool:
        """
        Semaphore wait() / P() operation — acquire the doctor resource.
        Returns True if acquired, False if already locked (busy).
        
        OS Concept: Mutex lock — only one process (patient) can hold
        the resource (doctor) at a time.
        """
        if self._lock:               # Already locked → busy
            return False
        # --- Critical Section Enter ---
        self._lock              = True
        self.is_available       = False
        self.current_patient_id = patient_id
        self.treatment_start    = time.time()
        # --- Critical Section End ---
        return True

    def release(self) -> float:
        """
        Semaphore signal() / V() operation — release the doctor resource.
        Returns time the doctor was busy with this patient.
        
        OS Concept: Mutex unlock — resource becomes available again.
        """
        if not self._lock:
            return 0.0
        busy_duration = time.time() - (self.treatment_start or time.time())
        # --- Critical Section Enter ---
        self._lock              = False
        self.is_available       = True
        self.current_patient_id = None
        self.treatment_start    = None
        self.total_patients_treated += 1
        self.total_busy_time        += busy_duration
        self.idle_since             = time.time()
        # --- Critical Section End ---
        return busy_duration

    @property
    def utilization(self) -> float:
        """CPU utilization percentage — analogous to OS CPU usage metric."""
        total = self.total_busy_time + (time.time() - self.idle_since)
        return (self.total_busy_time / total * 100) if total > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "doctor_id":        self.doctor_id,
            "name":             self.name,
            "specialization":   self.specialization,
            "is_available":     self.is_available,
            "current_patient":  self.current_patient_id,
            "patients_treated": self.total_patients_treated,
            "utilization":      round(self.utilization, 1),
            "busy_time":        round(self.total_busy_time, 1),
        }

    def __repr__(self):
        status = "FREE" if self.is_available else f"TREATING {self.current_patient_id}"
        return f"Doctor({self.name}, {status})"
