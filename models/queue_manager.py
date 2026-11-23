"""
Queue Manager - The OS Scheduler
Implements Priority Scheduling with Aging + FCFS tie-breaking
"""

import threading
import time
import logging
from typing import List, Optional, Dict
from models.patient import Patient
from models.doctor import Doctor

logger = logging.getLogger(__name__)


class Semaphore:
    """
    Custom Semaphore implementation — OS Concept.
    
    Controls access to a pool of resources (doctors).
    - wait()   / P() → Decrement count; block if 0
    - signal() / V() → Increment count; wake a waiting thread
    """

    def __init__(self, count: int):
        self._count     = count          # Number of available resources
        self._mutex     = threading.Lock()
        self._condition = threading.Condition(self._mutex)

    def wait(self, timeout: float = 0) -> bool:
        """P() — acquire one resource unit. Returns False if none available within timeout."""
        with self._condition:
            if self._count <= 0 and timeout == 0:
                return False
            deadline = time.time() + timeout if timeout > 0 else None
            while self._count <= 0:
                remaining = deadline - time.time() if deadline else None
                if remaining is not None and remaining <= 0:
                    return False
                self._condition.wait(timeout=remaining)
            self._count -= 1
            return True

    def signal(self):
        """V() — release one resource unit and notify waiting threads."""
        with self._condition:
            self._count += 1
            self._condition.notify()

    @property
    def value(self) -> int:
        return self._count


class QueueManager:
    """
    Central scheduler for the hospital queue system.
    
    OS Scheduling Algorithm: Priority Scheduling + Aging + FCFS
    
    Data Structures:
    - ready_queue      → List of waiting patients (Ready Queue)
    - in_treatment     → Dict of patient_id → doctor assignment (Running)
    - completed        → List of treated patients (Terminated)
    - doctors          → Pool of available doctors (CPUs)
    - semaphore        → Controls doctor resource access
    """

    AGING_INTERVAL   = 15    # seconds between aging ticks
    AGING_RATE       = 0.15  # priority improvement per tick
    STARVATION_LIMIT = 120   # seconds before starvation warning
    DEFAULT_TREATMENT_DURATION = 20  # seconds per patient (simulation speed)

    def __init__(self):
        self.ready_queue : List[Patient] = []
        self.in_treatment: Dict[str, Patient] = {}   # doctor_id → patient
        self.completed   : List[Patient] = []

        self.doctors: List[Doctor] = [
            Doctor("D001", "Dr. Sharma",  "Cardiology"),
            Doctor("D002", "Dr. Patel",   "Neurology"),
            Doctor("D003", "Dr. Gupta",   "General Medicine"),
            Doctor("D004", "Dr. Reddy",   "Orthopedics"),
            Doctor("D005", "Dr. Mehta",   "Emergency"),
        ]
        self.num_doctors = len(self.doctors)
        self.semaphore   = Semaphore(self.num_doctors)  # Semaphore = doctor count

        # Mutex for queue access (critical section protection)
        self._queue_lock = threading.Lock()

        # Statistics
        self.total_treated        = 0
        self.total_waiting_time   = 0.0
        self.start_time           = time.time()

        # Alerts
        self.alerts: List[dict] = []

        # Gantt chart records
        self.gantt_records: List[dict] = []

        # Event callbacks (for Flask SSE / UI update)
        self.on_update = None

        # Background threads
        self._aging_thread    = threading.Thread(target=self._aging_loop,    daemon=True)
        self._scheduler_thread= threading.Thread(target=self._scheduler_loop,daemon=True)
        self._running         = True

    def start(self):
        """Start background aging and scheduling threads."""
        self._aging_thread.start()
        self._scheduler_thread.start()
        logger.info("QueueManager started.")

    def stop(self):
        self._running = False

    # -------------------------------------------------------------------------
    # Patient Registration
    # -------------------------------------------------------------------------

    def register_patient(self, name: str, age: int, disease: str, severity: int) -> Patient:
        """
        Add a new patient to the ready queue.
        OS analogy: A new process arrives and enters the Ready Queue.
        """
        patient = Patient(name, age, disease, severity)
        with self._queue_lock:   # Mutex-protected critical section
            self.ready_queue.append(patient)
            self._sort_queue()

        # Critical patient alert
        if severity == 1:
            self._add_alert("critical", f"🚨 CRITICAL patient {patient.name} ({patient.patient_id}) has arrived!")

        logger.info(f"Registered: {patient}")
        self._notify()
        return patient

    # -------------------------------------------------------------------------
    # Scheduling
    # -------------------------------------------------------------------------

    def _scheduler_loop(self):
        """
        Continuously tries to dispatch patients to available doctors.
        OS analogy: The CPU Scheduler loop — picks the highest-priority
        ready process and dispatches it to an idle CPU.
        """
        while self._running:
            self._dispatch()
            self._check_completions()
            time.sleep(1)

    def _dispatch(self):
        """
        Priority Scheduler + Semaphore Resource Allocation.
        
        Algorithm:
        1. Sort ready queue by effective_priority (ascending = higher priority)
        2. FCFS tie-break: same priority → earlier arrival first
        3. For each available doctor (semaphore > 0), assign next patient
        4. Mutex: doctor.acquire() ensures no double-booking
        """
        with self._queue_lock:
            if not self.ready_queue:
                return

            # Find an available doctor (Semaphore check)
            available_doctor = self._get_available_doctor()
            if available_doctor is None:
                # All doctors busy — resource exhaustion alert
                if len(self.ready_queue) > 0:
                    self._add_alert("resource", "⚠️ All doctors are currently busy! Patients waiting...")
                return

            # Pick highest-priority patient (Priority Scheduler)
            patient = self.ready_queue[0]  # Already sorted

            # Semaphore P() — acquire the resource
            acquired = self.semaphore.wait(timeout=0)
            if not acquired:
                return

            # Mutex Lock — assign patient to doctor (atomic operation)
            if not available_doctor.acquire(patient.patient_id):
                self.semaphore.signal()   # Return semaphore token
                return

            # Dispatch: move patient from ready queue to treatment
            self.ready_queue.remove(patient)
            patient.start_treatment(available_doctor.doctor_id)
            self.in_treatment[available_doctor.doctor_id] = patient

            self._add_alert("info",
                f"✅ {patient.name} ({patient.patient_id}) assigned to {available_doctor.name}")
            logger.info(f"Dispatched {patient} → {available_doctor}")

        self._notify()

    def _check_completions(self):
        """
        Simulate treatment completion after DEFAULT_TREATMENT_DURATION seconds.
        OS analogy: Process finishes CPU burst → moves to Terminated state.
        """
        completed_this_tick = []
        with self._queue_lock:
            for doc_id, patient in list(self.in_treatment.items()):
                elapsed = time.time() - patient.start_time
                if elapsed >= self.DEFAULT_TREATMENT_DURATION:
                    # Find doctor
                    doctor = self._get_doctor_by_id(doc_id)
                    if doctor:
                        busy_time = doctor.release()   # Semaphore V()
                        self.semaphore.signal()

                    patient.complete_treatment()
                    self.completed.append(patient)
                    self.total_treated += 1
                    self.total_waiting_time += patient.waiting_time

                    # Gantt record
                    self.gantt_records.append({
                        "patient_id":   patient.patient_id,
                        "name":         patient.name,
                        "doctor":       doctor.name if doctor else doc_id,
                        "start":        patient.gantt_start,
                        "end":          patient.gantt_end,
                        "severity":     patient.severity,
                        "color":        patient.SEVERITY_COLORS.get(patient.severity, "#888"),
                    })

                    completed_this_tick.append(doc_id)
                    self._add_alert("success",
                        f"🏥 {patient.name} ({patient.patient_id}) treatment completed!")

            for doc_id in completed_this_tick:
                del self.in_treatment[doc_id]

        if completed_this_tick:
            self._notify()

    def _sort_queue(self):
        """
        Priority Queue sort:
        Primary: effective_priority ascending (lower = higher priority)
        Secondary: arrival_time ascending (FCFS tie-break)
        """
        self.ready_queue.sort(key=lambda p: (p.effective_priority, p.arrival_time))

    # -------------------------------------------------------------------------
    # Aging Algorithm
    # -------------------------------------------------------------------------

    def _aging_loop(self):
        """
        Background thread that applies aging every AGING_INTERVAL seconds.
        
        OS Concept: Multilevel Feedback Queue aging — processes that wait
        too long are promoted to higher-priority queues.
        """
        while self._running:
            time.sleep(self.AGING_INTERVAL)
            self._apply_aging()

    def _apply_aging(self):
        """Apply aging to all waiting patients."""
        with self._queue_lock:
            for patient in self.ready_queue:
                patient.update_waiting_time()
                delta = patient.apply_aging(self.AGING_RATE)

                if delta > 0.01:   # Meaningful improvement
                    logger.info(f"Aging applied to {patient}: priority improved by {delta:.2f}")

                # Starvation warning
                if patient.waiting_time >= self.STARVATION_LIMIT:
                    self._add_alert("starvation",
                        f"⏰ Starvation warning: {patient.name} ({patient.patient_id}) "
                        f"has been waiting {int(patient.waiting_time)}s!")

            self._sort_queue()

        self._notify()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_available_doctor(self) -> Optional[Doctor]:
        for doc in self.doctors:
            if doc.is_available:
                return doc
        return None

    def _get_doctor_by_id(self, doctor_id: str) -> Optional[Doctor]:
        for doc in self.doctors:
            if doc.doctor_id == doctor_id:
                return doc
        return None

    def _add_alert(self, alert_type: str, message: str):
        self.alerts.append({
            "type":      alert_type,
            "message":   message,
            "timestamp": time.strftime("%H:%M:%S"),
        })
        # Keep only last 50 alerts
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]

    def _notify(self):
        if self.on_update:
            try:
                self.on_update()
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Statistics / Reporting
    # -------------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Compute real-time statistics for the dashboard."""
        elapsed_hours = max((time.time() - self.start_time) / 3600, 0.0001)
        throughput    = self.total_treated / elapsed_hours

        avg_wait = (self.total_waiting_time / self.total_treated
                    if self.total_treated > 0 else 0.0)

        # Update waiting times for all queued patients
        with self._queue_lock:
            for p in self.ready_queue:
                p.update_waiting_time()

        return {
            "total_registered": len(self.ready_queue) + len(self.in_treatment) + len(self.completed),
            "total_waiting":    len(self.ready_queue),
            "total_treatment":  len(self.in_treatment),
            "total_completed":  len(self.completed),
            "avg_waiting_time": round(avg_wait, 1),
            "throughput":       round(throughput, 2),
            "semaphore_value":  self.semaphore.value,
            "doctors_free":     sum(1 for d in self.doctors if d.is_available),
            "doctors_busy":     sum(1 for d in self.doctors if not d.is_available),
        }

    def snapshot(self) -> dict:
        """Full state snapshot for the UI."""
        with self._queue_lock:
            waiting   = [p.to_dict() for p in self.ready_queue]
            treatment = {did: p.to_dict() for did, p in self.in_treatment.items()}
            done      = [p.to_dict() for p in reversed(self.completed[-20:])]

        return {
            "ready_queue":   waiting,
            "in_treatment":  treatment,
            "completed":     done,
            "doctors":       [d.to_dict() for d in self.doctors],
            "alerts":        list(reversed(self.alerts[-10:])),
            "gantt":         self.gantt_records[-30:],
            "stats":         self.get_stats(),
        }
