# 🏥 Hospital Patient Queue Management System

> **A Mini Project demonstrating Operating System Concepts**  
> Priority Scheduling · Aging · Semaphores · Mutex Lock · Multi-threading · Gantt Chart

---

## 📌 Problem Statement

Hospitals treat hundreds of patients daily with varying levels of medical urgency. Without a systematic approach, patients may be treated in arrival order (FCFS), which can be fatal for critical patients. This project simulates an intelligent queue management system using **OS scheduling algorithms** to ensure the most critical patients are always treated first, while also preventing low-priority patients from starving indefinitely.

---

## 🖥️ OS Concepts Implemented

| OS Concept | Hospital Analogy | Implementation |
|---|---|---|
| **Priority Scheduling** | Severe patients treated first | `effective_priority` field, sorted ready queue |
| **Aging Algorithm** | Long-waiting patients get priority boost | `apply_aging()` runs every 15 seconds |
| **Counting Semaphore** | Doctor pool (resource pool) | `Semaphore` class in `algorithms/semaphore.py` |
| **Mutex Lock** | One patient per doctor | `doctor.acquire()` / `doctor.release()` |
| **Multi-threading** | Multiple doctors treating simultaneously | Python `threading.Thread` (daemon threads) |
| **FCFS Tie-breaking** | Same severity → first arrival first | Secondary sort key: `arrival_time` |
| **Gantt Chart** | Treatment timeline visualization | Rendered in browser from `gantt_records` |
| **Starvation Prevention** | Low-priority patients never ignored | Aging reduces `effective_priority` over time |

---

## 🏗️ Project Structure

```
hospital_queue_system/
│
├── main.py                       # Flask entry point
├── requirements.txt              # Python dependencies (Flask only)
│
├── models/
│   ├── patient.py                # Patient class (= Process)
│   ├── doctor.py                 # Doctor class (= CPU/Resource)
│   └── queue_manager.py          # Scheduler, Semaphore, threads
│
├── algorithms/
│   ├── priority_scheduler.py     # Scheduling algorithm helpers
│   ├── aging.py                  # Aging algorithm
│   └── semaphore.py              # Semaphore & Mutex implementations
│
├── templates/
│   └── index.html                # Main dashboard (single-page app)
│
└── static/
    ├── css/style.css             # Dark-theme professional UI
    └── js/app.js                 # SSE-driven real-time frontend
```

---

## ⚙️ Algorithm Explanation

### 1. Priority Scheduling

```
Sort Key: (effective_priority ASC, arrival_time ASC)
```

- Each patient has a **base severity**: Critical=1, High=2, Medium=3, Low=4  
- Lower number = higher urgency (treated first)
- The scheduler always picks the patient with the smallest `effective_priority`
- If two patients have the same effective priority → **FCFS** (earlier arrival first)

### 2. Aging Algorithm (Starvation Prevention)

```python
effective_priority = max(0.5,  severity  -  aging_boost)
                            # base      minus accumulated boost
```

Every **15 seconds**, all waiting patients get an aging tick:
- `aging_boost += 0.15` per tick
- Priority improves continuously — a Low (4) patient reaches Critical-equivalent (~1) after ~200 seconds

**Example (Sara, Fever, severity=4):**
```
t=0s   → priority = 4.00  (Low)
t=15s  → priority = 3.85
t=30s  → priority = 3.70
t=120s → priority = 2.80  ≈ High
t=200s → priority = 1.50  ≈ near Critical
```

### 3. Semaphore (Counting)

```python
# Doctor pool with 5 slots
semaphore = Semaphore(count=5)

# When assigning a doctor (P operation):
semaphore.wait()   # count → 4

# When doctor finishes (V operation):
semaphore.signal() # count → 5
```

The semaphore prevents more patients from being assigned than there are doctors.

### 4. Mutex Lock

```python
doctor.acquire(patient_id)   # Lock the doctor to this patient
# ... treatment happens ...
doctor.release()              # Unlock — doctor available again
```

The `_lock` flag ensures no two patients can be assigned to the same doctor simultaneously (mutual exclusion).

### 5. Multi-threading

Three concurrent threads run:
1. **Main Thread** — Flask web server (handles HTTP requests)
2. **Scheduler Thread** — dispatches patients to doctors every 1 second
3. **Aging Thread** — applies aging to waiting patients every 15 seconds

---

## 🚀 Setup & Run

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Navigate to project folder
cd hospital_queue_system

# Install dependencies (only Flask needed!)
pip install -r requirements.txt

# Run the application
python main.py
```

### Open in Browser
```
http://127.0.0.1:5000
```

---

## 🎮 How to Demo

1. **Start the app** and open `http://127.0.0.1:5000`
2. Click **"Load Sample Data"** to load the 5 test patients
3. Watch the **Ready Queue** auto-sort by priority (Critical first)
4. Observe doctors being assigned (Semaphore counter updates)
5. Watch the **Gantt Chart** build as patients complete treatment
6. Wait 15–30 seconds and see **Aging** boost Sara's priority
7. Click **"Add Patient"** to register a new patient manually
8. Use **"✓ Done"** button to manually complete a patient's treatment

---

## 📊 Sample Test Data & Expected Output

| Patient | Age | Disease | Severity | Initial Queue Position |
|---|---|---|---|---|
| John | 45 | Heart Attack | 🔴 Critical (1) | 1st |
| Mike | 60 | Stroke | 🔴 Critical (1) | 2nd (FCFS tie-break) |
| Priya | 30 | Fracture | 🟠 High (2) | 3rd |
| Tom | 50 | Appendicitis | 🟡 Medium (3) | 4th |
| Sara | 25 | Fever | 🟢 Low (4) | 5th |

**After aging (Sara's priority improves over time):**
```
Treatment Order: John → Mike → Priya → Tom → Sara
                 (Sara eventually moves up due to Aging)
```

---

## 📐 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Main dashboard |
| POST | `/api/register` | Register new patient |
| POST | `/api/load_sample` | Load 5 sample patients |
| GET | `/api/snapshot` | Current system state (JSON) |
| GET | `/api/stats` | Statistics only |
| POST | `/api/complete/<id>` | Manually complete treatment |
| POST | `/api/reset` | Reset entire system |
| GET | `/stream` | SSE real-time event stream |

---

## 🎨 UI Features

- **Dark professional theme** with real-time updates via Server-Sent Events
- **Priority bar** for each waiting patient (visual urgency indicator)
- **Semaphore dots** showing available/busy doctor slots
- **Aging indicator** (↑ value) showing priority boost amount
- **Color-coded** severity badges (Red/Orange/Yellow/Green)
- **Live Gantt chart** building as patients complete treatment
- **Alert system** for critical arrivals and starvation warnings
- **Keyboard shortcut**: Press `N` to open the patient registration form

---

## 📝 Conclusion

This project successfully demonstrates how **Operating System scheduling concepts** directly map to real-world resource allocation problems. The hospital queue system shows:

- **Priority Scheduling** solves the problem of treating urgent patients first
- **Aging** prevents the theoretical problem of starvation in pure priority scheduling
- **Semaphores** provide a clean, OS-inspired way to manage a pool of shared resources
- **Mutex Locks** ensure data consistency when multiple threads modify shared state
- **Multi-threading** enables true parallel treatment by multiple doctors (CPUs)

The implementation in Python with Flask demonstrates that OS concepts are not just academic — they are directly applicable to building real production systems.

---

*Built for OS Mini Project — Demonstrating: Priority Scheduling, Aging, Semaphores, Mutex, Multi-threading*
"# hospital-queue-management" 
