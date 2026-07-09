/**
 * Dashboard charts and live status polling
 */
const DashboardApp = {
  charts: {},

  init() {
    const dataEl = document.getElementById("dashboard-chart-data");
    if (!dataEl) return;
    const data = JSON.parse(dataEl.textContent);
    this.initCharts(data);
    this.pollLiveStatus();
    setInterval(() => this.pollLiveStatus(), 5000);
  },

  initCharts(data) {
    const defaults = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
    };

    this.charts.weekly = new Chart(document.getElementById("chartWeekly"), {
      type: "bar",
      data: {
        labels: data.weekly.labels,
        datasets: [{ label: "Present", data: data.weekly.values, backgroundColor: "#2563eb", borderRadius: 6 }],
      },
      options: { ...defaults, scales: { y: { beginAtZero: true } } },
    });

    this.charts.monthly = new Chart(document.getElementById("chartMonthly"), {
      type: "line",
      data: {
        labels: data.monthly.labels,
        datasets: [{ label: "Attendance", data: data.monthly.values, borderColor: "#16a34a", backgroundColor: "rgba(22,163,74,0.1)", fill: true, tension: 0.4 }],
      },
      options: defaults,
    });

    this.charts.course = new Chart(document.getElementById("chartCourse"), {
      type: "doughnut",
      data: {
        labels: data.by_course.labels,
        datasets: [{ data: data.by_course.values, backgroundColor: ["#2563eb", "#16a34a", "#d97706", "#dc2626", "#0891b2", "#7c3aed"] }],
      },
      options: { responsive: true, plugins: { legend: { position: "bottom" } } },
    });

    this.charts.confidence = new Chart(document.getElementById("chartConfidence"), {
      type: "bar",
      data: {
        labels: data.confidence.labels,
        datasets: [{ data: data.confidence.values, backgroundColor: ["#dc2626", "#d97706", "#16a34a"], borderRadius: 6 }],
      },
      options: defaults,
    });

    this.charts.trends = new Chart(document.getElementById("chartTrends"), {
      type: "line",
      data: {
        labels: data.trends.labels,
        datasets: [
          { label: "Present", data: data.trends.present, borderColor: "#16a34a", tension: 0.3 },
          { label: "Absent", data: data.trends.absent, borderColor: "#dc2626", tension: 0.3 },
        ],
      },
      options: { responsive: true, plugins: { legend: { position: "top" } } },
    });
  },

  async pollLiveStatus() {
    try {
      const res = await fetch("/api/session/status/");
      const data = await res.json();
      const detected = document.getElementById("dashStudentsDetected");
      const frames = document.getElementById("dashFramesProcessed");
      const timer = document.getElementById("dashSessionTimer");
      if (detected) detected.textContent = data.students_detected ?? 0;
      if (frames) frames.textContent = data.frames_processed ?? 0;
      if (timer && data.active && data.started_at) {
        const elapsed = Math.floor((Date.now() - new Date(data.started_at).getTime()) / 1000);
        const m = String(Math.floor(elapsed / 60)).padStart(2, "0");
        const s = String(elapsed % 60).padStart(2, "0");
        timer.textContent = `${m}:${s}`;
      }
    } catch (e) { /* silent */ }
  },
};

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("chartWeekly")) DashboardApp.init();
});

window.DashboardApp = DashboardApp;
