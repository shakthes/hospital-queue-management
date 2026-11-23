/**
 * Hospital Queue Management System — Frontend JavaScript
 * Real-time dashboard using Server-Sent Events (SSE)
 *
 * OS Concepts demonstrated in UI:
 * - Ready Queue visualization
 * - Priority Scheduler animation
 * - Semaphore counter
 * - Aging indicator
 * - Gantt chart (CPU Burst timeline)
 */

"use strict";

// ============================================================
// STATE
// ============================================================
let lastSnapshot = null;
let alertsDismissed = false;
const TREATMENT_DURATION = 20;   // seconds (must match backend)

// ============================================================
// CLOCK
// ============================================================
function updateClock() {
  const now = new Date();
  document.getElementById("liveClock").textContent = now.toLocaleTimeString("en-IN");
}
setInterval(updateClock, 1000);
updateClock();

// ============================================================
// SERVER-SENT EVENTS — Real-time updates
// ============================================================
function connectSSE() {
  const evtSource = new EventSource("/stream");

  evtSource.onmessage = (e) => {
    try {
      const snap = JSON.parse(e.data);
      lastSnapshot = snap;
      renderDashboard(snap);
    } catch (err) {
      console.error("SSE parse error:", err);
    }
  };

  evtSource.onerror = () => {
    console.warn("SSE connection lost, retrying...");
    evtSource.close();
    setTimeout(connectSSE, 3000);
  };
}
connectSSE();

// ============================================================
// RENDER DASHBOARD
// ============================================================
function renderDashboard(snap) {
  renderStats(snap.stats);
  renderQueue(snap.ready_queue);
  renderTreatment(snap.in_treatment, snap.doctors);
  renderDoctors(snap.doctors, snap.in_treatment);
  renderAlerts(snap.alerts);
  renderCompleted(snap.completed);
  renderGantt(snap.gantt);
  updateSemaphore(snap.stats);
}

// ---- Stats ----
function renderStats(stats) {
  setText("numWaiting",    stats.total_waiting);
  setText("numTreatment",  stats.total_treatment);
  setText("numCompleted",  stats.total_completed);
  setText("avgWait",       stats.avg_waiting_time + "s");
  setText("throughput",    stats.throughput.toFixed(1));
  setText("semValue",      stats.doctors_free);
  setText("semBadge",      stats.semaphore_value);
}

// ---- Ready Queue ----
function renderQueue(queue) {
  const tbody = document.getElementById("queueBody");
  if (!queue || queue.length === 0) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="9">No patients waiting. Click "Add Patient" or "Load Sample Data".</td></tr>`;
    return;
  }

  tbody.innerHTML = queue.map((p, idx) => {
    const wait     = p.waiting_time;
    const waitClass= wait > 120 ? "wait-critical" : wait > 60 ? "wait-warning" : "wait-time";
    const waitStr  = formatSeconds(wait);
    const aging    = p.aging_boost > 0 ? `<span class="aging-up">↑${p.aging_boost.toFixed(2)}</span>` : "—";

    // Priority bar: effective_priority 0.5→4, invert for fill width
    const fillPct  = Math.round(((4 - p.effective_priority) / 3.5) * 100);
    const barColor = getSevColor(p.severity);

    return `
      <tr>
        <td>${idx + 1}</td>
        <td><code>${p.patient_id}</code></td>
        <td><strong>${p.name}</strong></td>
        <td>${p.age}</td>
        <td>${p.disease}</td>
        <td><span class="sev-badge sev-${p.severity}">${p.severity_label}</span></td>
        <td>
          <div class="priority-bar">
            <div class="pbar"><div class="pbar-fill" style="width:${fillPct}%;background:${barColor}"></div></div>
            <span class="priority-num">${p.effective_priority.toFixed(2)}</span>
          </div>
        </td>
        <td class="${waitClass}">${waitStr}</td>
        <td>${aging}</td>
      </tr>`;
  }).join("");
}

// ---- In Treatment ----
function renderTreatment(treatment, doctors) {
  const container = document.getElementById("treatmentCards");
  const entries   = Object.entries(treatment || {});

  if (entries.length === 0) {
    container.innerHTML = `<p class="empty-msg">No patients currently in treatment.</p>`;
    return;
  }

  container.innerHTML = entries.map(([docId, p]) => {
    const doctor   = doctors.find(d => d.doctor_id === docId);
    const docName  = doctor ? doctor.name : docId;
    const elapsed  = p.treatment_time || 0;   // from backend
    const progPct  = Math.min(100, Math.round((elapsed / TREATMENT_DURATION) * 100));

    return `
      <div class="treatment-card">
        <button class="btn-complete" onclick="completePatient('${p.patient_id}')">✓ Done</button>
        <div class="tc-header">
          <div>
            <div class="tc-name">${p.name}</div>
            <div class="tc-pid"><code>${p.patient_id}</code></div>
          </div>
          <span class="sev-badge sev-${p.severity}">${p.severity_label}</span>
        </div>
        <div class="tc-info">
          <span>Age: <strong>${p.age}</strong></span>
          <span>Wait: <strong>${formatSeconds(p.waiting_time)}</strong></span>
          <span colspan="2">Disease: <strong>${p.disease}</strong></span>
        </div>
        <div class="tc-doctor">
          <i class="fa fa-user-doctor"></i> ${docName}
          <span style="color:var(--text-muted)">(${doctor ? doctor.specialization : ""})</span>
        </div>
        <div class="tc-progress">
          <div class="tc-prog-bar">
            <div class="tc-prog-fill" style="width:${progPct}%"></div>
          </div>
        </div>
      </div>`;
  }).join("");
}

// ---- Doctor Panel ----
function renderDoctors(doctors, treatment) {
  const container = document.getElementById("doctorCards");
  container.innerHTML = doctors.map(d => {
    const isFree   = d.is_available;
    const patient  = !isFree ? treatment[d.doctor_id] : null;
    const patName  = patient ? patient.name : "—";
    const utilStr  = d.utilization.toFixed(0) + "%";

    return `
      <div class="doctor-row">
        <div class="dr-status-dot ${isFree ? 'dr-free' : 'dr-busy'}"></div>
        <div class="dr-info">
          <div class="dr-name">${d.name}</div>
          <div class="dr-spec">${d.specialization} · Treated: ${d.patients_treated} · Util: ${utilStr}</div>
          ${!isFree ? `<div style="font-size:11px;color:var(--accent-orange);margin-top:2px;">Treating: <strong>${patName}</strong></div>` : ''}
        </div>
        <span class="dr-badge ${isFree ? 'free' : 'busy'}">${isFree ? 'FREE' : 'BUSY'}</span>
      </div>`;
  }).join("");
}

// ---- Alerts ----
function renderAlerts(alerts) {
  const container = document.getElementById("alertsList");
  if (!alerts || alerts.length === 0) {
    container.innerHTML = `<p class="empty-msg">No alerts yet.</p>`;
    return;
  }
  container.innerHTML = alerts.map(a => `
    <div class="alert-item ${a.type}">
      <span style="flex:1">${a.message}</span>
      <span class="alert-time">${a.timestamp}</span>
    </div>`).join("");

  // Flash the alert banner for critical alerts
  const critical = alerts.find(a => a.type === "critical");
  if (critical) showAlertBanner(critical.message, "critical");
}

// ---- Completed Table ----
function renderCompleted(completed) {
  const tbody = document.getElementById("completedBody");
  if (!completed || completed.length === 0) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="6">No completed patients yet.</td></tr>`;
    return;
  }
  tbody.innerHTML = completed.map(p => `
    <tr>
      <td><code>${p.patient_id}</code></td>
      <td>${p.name}</td>
      <td><span class="sev-badge sev-${p.severity}">${p.severity_label}</span></td>
      <td>${formatSeconds(p.waiting_time)}</td>
      <td>${formatSeconds(p.treatment_time)}</td>
      <td>${p.doctor_id || "—"}</td>
    </tr>`).join("");
}

// ---- Gantt Chart ----
function renderGantt(records) {
  const container = document.getElementById("ganttContainer");
  if (!records || records.length === 0) {
    container.innerHTML = `<p class="empty-msg">Gantt chart will appear after first patient is treated.</p>`;
    return;
  }

  // Find time range
  const minT = Math.min(...records.map(r => r.start));
  const maxT = Math.max(...records.map(r => r.end || r.start + TREATMENT_DURATION));
  const span = Math.max(maxT - minT, 1);

  // Build rows
  const rows = records.map(r => {
    const leftPct  = ((r.start - minT) / span) * 100;
    const widthPct = (((r.end || r.start + TREATMENT_DURATION) - r.start) / span) * 100;
    const label    = `${r.patient_id} (${r.name}) — ${r.doctor}`;

    return `
      <div class="gantt-row">
        <div class="gantt-label" title="${r.name}">${r.patient_id}</div>
        <div class="gantt-track">
          <div class="gantt-bar"
               style="left:${leftPct.toFixed(1)}%;width:${Math.max(widthPct,2).toFixed(1)}%;background:${r.color};"
               title="${label}">
            ${r.name}
          </div>
        </div>
      </div>`;
  }).join("");

  container.innerHTML = `<div class="gantt-chart">${rows}</div>`;
}

// ---- Semaphore Visual ----
function updateSemaphore(stats) {
  const indicator = document.getElementById("semIndicator");
  const val = stats.semaphore_value;
  const total = 5;
  const dots = Array.from({length: total}, (_, i) =>
    `<span style="font-size:14px;color:${i < val ? 'var(--accent-green)' : 'var(--accent-red)'}">●</span>`
  ).join("");
  indicator.innerHTML = `🚦 Semaphore: ${dots} <strong>${val}</strong>/${total}`;
}

// ============================================================
// PATIENT REGISTRATION MODAL
// ============================================================
function openRegisterModal() {
  document.getElementById("registerModal").classList.remove("hidden");
  document.getElementById("f_name").focus();
}
function closeRegisterModal() {
  document.getElementById("registerModal").classList.add("hidden");
  document.getElementById("registerForm").reset();
}

async function submitPatient(e) {
  e.preventDefault();
  const name     = document.getElementById("f_name").value.trim();
  const age      = parseInt(document.getElementById("f_age").value);
  const disease  = document.getElementById("f_disease").value.trim();
  const sevRadio = document.querySelector('input[name="severity"]:checked');
  if (!sevRadio) { showToast("Please select a severity level.", "error"); return; }
  const severity = parseInt(sevRadio.value);

  try {
    const res  = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, age, disease, severity })
    });
    const data = await res.json();
    if (data.error) { showToast("Error: " + data.error, "error"); return; }

    closeRegisterModal();
    showToast(`✅ ${name} registered as ${data.patient.patient_id}`, "success");
  } catch (err) {
    showToast("Network error: " + err.message, "error");
  }
}

// ============================================================
// SAMPLE DATA
// ============================================================
async function loadSample() {
  try {
    const res  = await fetch("/api/load_sample", { method: "POST" });
    const data = await res.json();
    showToast(`✅ Loaded ${data.patients.length} sample patients!`, "success");
  } catch (err) {
    showToast("Error loading sample data", "error");
  }
}

// ============================================================
// COMPLETE PATIENT (manual)
// ============================================================
async function completePatient(patientId) {
  try {
    const res  = await fetch(`/api/complete/${patientId}`, { method: "POST" });
    const data = await res.json();
    if (data.success) showToast(`✅ Patient ${patientId} marked as treated.`, "success");
    else showToast(data.error, "error");
  } catch (err) {
    showToast("Error: " + err.message, "error");
  }
}

// ============================================================
// RESET SYSTEM
// ============================================================
async function resetSystem() {
  if (!confirm("Reset the entire system? All patient data will be cleared.")) return;
  try {
    await fetch("/api/reset", { method: "POST" });
    showToast("🔄 System reset successfully.", "info");
  } catch (err) {
    showToast("Error: " + err.message, "error");
  }
}

// ============================================================
// ALERTS
// ============================================================
function clearAlerts() {
  document.getElementById("alertsList").innerHTML = `<p class="empty-msg">No alerts yet.</p>`;
}

function showAlertBanner(msg, type) {
  const banner = document.getElementById("alertBanner");
  banner.textContent = msg;
  banner.className   = `alert-banner ${type}`;
  banner.classList.remove("hidden");
  setTimeout(() => banner.classList.add("hidden"), 5000);
}

// ============================================================
// UTILS
// ============================================================
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function formatSeconds(secs) {
  if (!secs || secs < 0) return "0s";
  const s = Math.floor(secs);
  if (s < 60)  return `${s}s`;
  if (s < 3600) return `${Math.floor(s/60)}m ${s%60}s`;
  return `${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m`;
}

function getSevColor(severity) {
  const map = { 1: "#ff3b30", 2: "#ff9500", 3: "#ffcc00", 4: "#34c759" };
  return map[severity] || "#888";
}

function showToast(msg, type = "info") {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.style.borderColor = type === "success" ? "var(--accent-green)"
    : type === "error" ? "var(--accent-red)" : "var(--accent-blue)";
  toast.classList.remove("hidden");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.add("hidden"), 3500);
}

// Close modal on backdrop click
document.getElementById("registerModal").addEventListener("click", (e) => {
  if (e.target === e.currentTarget) closeRegisterModal();
});

// Keyboard shortcuts
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeRegisterModal();
  if (e.key === "n" && !e.target.matches("input")) openRegisterModal();
});
