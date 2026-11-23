"""
Flask Web Application — Hospital Patient Queue Management System
Entry point: main.py
"""

from flask import Flask, render_template, request, jsonify, Response
import json
import time
import threading

from models.queue_manager import QueueManager

app = Flask(__name__)
app.config["SECRET_KEY"] = "hospital_os_2024"

# Global queue manager (singleton — shared state)
qm = QueueManager()
qm.start()

# Server-Sent Events (SSE) — Real-time push to browser
_sse_clients = []
_sse_lock    = threading.Lock()


def _broadcast():
    """Push updated snapshot to all connected SSE clients."""
    data = json.dumps(qm.snapshot())
    with _sse_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait(data)
            except Exception:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)


qm.on_update = _broadcast


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/register", methods=["POST"])
def register_patient():
    data = request.get_json(force=True)
    try:
        name     = data["name"].strip()
        age      = int(data["age"])
        disease  = data["disease"].strip()
        severity = int(data["severity"])

        if not name or not disease:
            return jsonify({"error": "Name and disease are required"}), 400
        if severity not in (1, 2, 3, 4):
            return jsonify({"error": "Severity must be 1–4"}), 400

        patient = qm.register_patient(name, age, disease, severity)
        return jsonify({"success": True, "patient": patient.to_dict()})

    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/snapshot")
def snapshot():
    return jsonify(qm.snapshot())


@app.route("/api/stats")
def stats():
    return jsonify(qm.get_stats())


@app.route("/api/complete/<patient_id>", methods=["POST"])
def complete_patient(patient_id):
    """Manually complete a patient's treatment (for demo/testing)."""
    with qm._queue_lock:
        for doc_id, patient in list(qm.in_treatment.items()):
            if patient.patient_id == patient_id:
                doctor = qm._get_doctor_by_id(doc_id)
                if doctor:
                    doctor.release()
                    qm.semaphore.signal()
                patient.complete_treatment()
                qm.completed.append(patient)
                qm.total_treated += 1
                qm.total_waiting_time += patient.waiting_time
                qm.gantt_records.append({
                    "patient_id": patient.patient_id,
                    "name":       patient.name,
                    "doctor":     doctor.name if doctor else doc_id,
                    "start":      patient.gantt_start,
                    "end":        patient.gantt_end,
                    "severity":   patient.severity,
                    "color":      patient.SEVERITY_COLORS.get(patient.severity, "#888"),
                })
                del qm.in_treatment[doc_id]
                _broadcast()
                return jsonify({"success": True})
    return jsonify({"error": "Patient not found in treatment"}), 404


@app.route("/api/load_sample", methods=["POST"])
def load_sample():
    """Load the 5 sample patients from the project spec."""
    samples = [
        {"name": "John",  "age": 45, "disease": "Heart Attack",  "severity": 1},
        {"name": "Sara",  "age": 25, "disease": "Fever",          "severity": 4},
        {"name": "Mike",  "age": 60, "disease": "Stroke",         "severity": 1},
        {"name": "Priya", "age": 30, "disease": "Fracture",       "severity": 2},
        {"name": "Tom",   "age": 50, "disease": "Appendicitis",   "severity": 3},
    ]
    added = []
    for s in samples:
        p = qm.register_patient(s["name"], s["age"], s["disease"], s["severity"])
        added.append(p.to_dict())
    return jsonify({"success": True, "patients": added})


@app.route("/api/reset", methods=["POST"])
def reset_system():
    """Reset the entire system for a fresh demo."""
    global qm
    qm.stop()
    time.sleep(0.5)
    from models.patient import Patient
    Patient._id_counter = 1
    qm = QueueManager()
    qm.on_update = _broadcast
    qm.start()
    _broadcast()
    return jsonify({"success": True})


@app.route("/stream")
def stream():
    """Server-Sent Events stream for real-time UI updates."""
    import queue as _queue

    client_q = _queue.Queue(maxsize=20)
    with _sse_lock:
        _sse_clients.append(client_q)

    def generate():
        # Send initial snapshot
        yield f"data: {json.dumps(qm.snapshot())}\n\n"
        while True:
            try:
                data = client_q.get(timeout=30)
                yield f"data: {data}\n\n"
            except Exception:
                # Heartbeat to keep connection alive
                yield ": heartbeat\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    print("=" * 60)
    print("  🏥 Hospital Patient Queue Management System")
    print("  OS Concepts: Priority Scheduling + Aging + Semaphores")
    print("=" * 60)
    print("  Open: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=False, threaded=True, port=5000)
