/**
 * AI Attendance — Phase 3 flagship experience
 * Preserves all original backend API integration.
 */
const AttendanceApp = {
  sessionActive: false,
  sessionPaused: false,
  captureIntervalId: null,
  liveTableIntervalId: null,
  sessionTimerIntervalId: null,
  sessionStartTime: null,
  modelsLoaded: false,
  displaySize: null,
  lastFaces: [],
  frameCount: 0,
  lastFrameTime: performance.now(),
  captureIntervalMs: 5000,
  totalRecognized: 0,
  totalAttempts: 0,

  init() {
    this.video = document.getElementById("video");
    this.canvas = document.getElementById("canvas");
    this.overlayCanvas = document.getElementById("overlayCanvas");
    this.startSessionBtn = document.getElementById("startSessionBtn");
    this.pauseSessionBtn = document.getElementById("pauseSessionBtn");
    this.endSessionBtn = document.getElementById("endSessionBtn");
    this.captureBtn = document.getElementById("captureBtn");
    this.statusEl = document.getElementById("status");
    this.sessionStatusEl = document.getElementById("sessionStatus");
    this.studentsEl = document.getElementById("students");
    this.studentsEmpty = document.getElementById("studentsEmpty");
    this.unknownFacesEl = document.getElementById("unknownFaces");
    this.courseSelect = document.getElementById("courseSelect");
    this.cameraFeedback = document.getElementById("cameraFeedback");
    this.recognitionBadge = document.getElementById("recognitionStateBadge");

    if (!this.video) return;

    this.captureBtn?.addEventListener("click", () => this.captureAttendance());
    this.startSessionBtn?.addEventListener("click", () => this.startSession());
    this.pauseSessionBtn?.addEventListener("click", () => this.togglePause());
    this.endSessionBtn?.addEventListener("click", () => this.endSession());

    this.startCamera();
    this.loadModels();
    this.liveTableIntervalId = setInterval(() => this.refreshLiveTable(), 3000);
  },

  async loadModels() {
    try {
      this.setFeedback("Loading face detection models...");
      await faceapi.nets.tinyFaceDetector.loadFromUri("/static/models/");
      this.modelsLoaded = true;
      this.setFeedback("Face detection ready");
      this.setRecognitionState("Ready");
      if (this.video.videoWidth) this.renderLoop();
    } catch (e) {
      this.setFeedback("Failed to load models");
      this.setRecognitionState("Error");
    }
  },

  async startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 } });
      this.video.srcObject = stream;
      this.video.addEventListener("play", () => {
        this.overlayCanvas.width = this.video.videoWidth;
        this.overlayCanvas.height = this.video.videoHeight;
        this.displaySize = { width: this.video.videoWidth, height: this.video.videoHeight };
        this.setFeedback("Camera active");
        this.setRecognitionState("Camera Online");
        if (this.modelsLoaded) this.renderLoop();
      });
      this.setStatus("Camera ready.");
    } catch (e) {
      this.setStatus("Camera offline.");
      this.setFeedback("Camera Offline");
      this.setRecognitionState("Camera Offline");
      this.captureBtn.disabled = true;
    }
  },

  renderLoop() {
    this.frameCount++;
    const now = performance.now();
    if (now - this.lastFrameTime >= 1000) {
      const fps = Math.round((this.frameCount * 1000) / (now - this.lastFrameTime));
      const fpsEl = document.getElementById("fpsCounter");
      if (fpsEl) fpsEl.textContent = `FPS: ${fps}`;
      this.frameCount = 0;
      this.lastFrameTime = now;
    }
    this.drawOverlay();
    requestAnimationFrame(() => this.renderLoop());
  },

  drawOverlay() {
    const ctx = this.overlayCanvas.getContext("2d");
    ctx.clearRect(0, 0, this.overlayCanvas.width, this.overlayCanvas.height);
    if (!this.lastFaces.length) return;

    const scaleX = this.overlayCanvas.width / (this.lastImageWidth || this.overlayCanvas.width);
    const scaleY = this.overlayCanvas.height / (this.lastImageHeight || this.overlayCanvas.height);

    this.lastFaces.forEach((face) => {
      const { top, right, bottom, left } = face.box;
      const x = left * scaleX;
      const y = top * scaleY;
      const w = (right - left) * scaleX;
      const h = (bottom - top) * scaleY;

      let color = "#d97706";
      if (face.state === "recognized") color = "#16a34a";
      if (face.state === "unknown") color = "#dc2626";
      if (face.state === "processing") color = "#d97706";

      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.strokeRect(x, y, w, h);

      const label = face.name === "Unknown"
        ? `Unknown (${face.confidence_percent}%)`
        : `${face.name} (${face.confidence_percent}%)`;
      ctx.fillStyle = color;
      ctx.fillRect(x, y - 22, ctx.measureText(label).width + 12, 22);
      ctx.fillStyle = "#fff";
      ctx.font = "bold 12px Inter, sans-serif";
      ctx.fillText(label, x + 6, y - 7);
    });

    const detBadge = document.getElementById("detectionCountBadge");
    if (detBadge) detBadge.textContent = `Detections: ${this.lastFaces.length}`;
  },

  setStatus(text) { if (this.statusEl) this.statusEl.textContent = text; },
  setFeedback(text) { if (this.cameraFeedback) this.cameraFeedback.textContent = text; },
  setRecognitionState(text) {
    if (this.recognitionBadge) {
      this.recognitionBadge.textContent = text;
      this.recognitionBadge.className = "badge " + (
        text.includes("Recognized") ? "badge-success" :
        text.includes("Unknown") ? "badge-warning" :
        text.includes("Offline") || text.includes("Error") ? "badge-danger" : "badge-neutral"
      );
    }
  },

  toggleStudentsEmpty(show) {
    if (this.studentsEmpty) this.studentsEmpty.style.display = show ? "flex" : "none";
  },

  async captureAttendance() {
    if (!this.video.videoWidth || this.sessionPaused) return;
    if (!this.sessionActive) {
      this.setStatus("No active session.");
      return;
    }

    this.captureBtn.disabled = true;
    this.setStatus("Recognizing...");
    this.setFeedback("Recognizing...");
    this.setRecognitionState("Processing");

    const maxWidth = 640;
    const scale = Math.min(1, maxWidth / this.video.videoWidth);
    this.canvas.width = Math.floor(this.video.videoWidth * scale);
    this.canvas.height = Math.floor(this.video.videoHeight * scale);
    const ctx = this.canvas.getContext("2d");
    ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
    const image = this.canvas.toDataURL("image/jpeg", 0.6);

    try {
      const response = await fetch("/recognize/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Request failed.");

      this.totalAttempts++;
      this.lastFaces = data.faces || [];
      this.lastImageWidth = data.image_width || this.canvas.width;
      this.lastImageHeight = data.image_height || this.canvas.height;

      const students = data.students || [];
      const unknownCount = data.unknown_count || 0;

      if (students.length) {
        this.totalRecognized++;
        this.setStatus("Recognized");
        this.setFeedback("Recognized");
        this.setRecognitionState("Recognized");
      } else if (unknownCount) {
        this.setStatus("Unknown face detected");
        this.setFeedback("Unknown Face");
        this.setRecognitionState("Unknown Face");
      } else {
        this.setStatus("No faces detected");
        this.setFeedback("Detection Lost");
        this.setRecognitionState("Detection Lost");
        this.lastFaces = [];
      }

      this.studentsEl.innerHTML = "";
      this.unknownFacesEl.innerHTML = "";
      this.toggleStudentsEmpty(students.length === 0 && unknownCount === 0);

      students.forEach((name) => {
        const li = document.createElement("li");
        li.textContent = name;
        this.studentsEl.appendChild(li);
      });

      (data.faces || []).filter((f) => f.name === "Unknown").forEach((f) => {
        const div = document.createElement("div");
        div.className = "unknown-face-chip";
        div.textContent = `Unknown #${f.tracking_id} (${f.confidence_percent}%)`;
        this.unknownFacesEl.appendChild(div);
      });

      const framesEl = document.getElementById("framesProcessed");
      if (framesEl) framesEl.textContent = data.frames_processed || 0;
      const unknownEl = document.getElementById("unknownFacesCount");
      if (unknownEl) unknownEl.textContent = unknownCount;
      const presentEl = document.getElementById("studentsPresentCount");
      if (presentEl) presentEl.textContent = students.length;
      const accEl = document.getElementById("recognitionAccuracy");
      if (accEl && this.totalAttempts) {
        accEl.textContent = `${Math.round((this.totalRecognized / this.totalAttempts) * 100)}%`;
      }
      if (data.faces?.length) {
        const avg = data.faces.reduce((s, f) => s + f.confidence, 0) / data.faces.length;
        const avgEl = document.getElementById("avgConfidence");
        if (avgEl) avgEl.textContent = `${Math.round(avg * 100)}%`;
      }

      this.refreshLiveTable();
    } catch (error) {
      this.setStatus(`Error: ${error.message}`);
      this.setFeedback("Recognition Failed");
      this.setRecognitionState("Error");
      window.ToastManager?.show("error", "Recognition Failed", error.message);
    } finally {
      this.captureBtn.disabled = false;
    }
  },

  async startSession() {
    try {
      const courseId = this.courseSelect?.value || null;
      const response = await fetch("/start-session/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ course_id: courseId }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Unable to start session.");

      this.sessionActive = true;
      this.sessionPaused = false;
      this.sessionStartTime = Date.now();
      this.sessionStatusEl.textContent = `Active #${data.session_id}`;
      this.startSessionBtn.disabled = true;
      this.endSessionBtn.disabled = false;
      this.pauseSessionBtn.disabled = false;

      window.LiveSessionBadge?.setActive(data.session_id);
      window.ToastManager?.show("success", "Session Started", `Session #${data.session_id} active.`);

      this.startSessionTimer();
      if (this.captureIntervalId) clearInterval(this.captureIntervalId);
      this.captureIntervalId = setInterval(() => this.captureAttendance(), this.captureIntervalMs);
      this.captureAttendance();
    } catch (error) {
      window.ToastManager?.show("error", "Session Error", error.message);
    }
  },

  togglePause() {
    this.sessionPaused = !this.sessionPaused;
    if (this.sessionPaused) {
      if (this.captureIntervalId) { clearInterval(this.captureIntervalId); this.captureIntervalId = null; }
      this.pauseSessionBtn.innerHTML = '<i data-lucide="play"></i> Resume Session';
      this.sessionStatusEl.textContent = "Paused";
      this.setFeedback("Paused");
      window.lucide?.createIcons();
    } else {
      this.pauseSessionBtn.innerHTML = '<i data-lucide="pause"></i> Pause Session';
      this.sessionStatusEl.textContent = "Active";
      this.captureIntervalId = setInterval(() => this.captureAttendance(), this.captureIntervalMs);
      window.lucide?.createIcons();
    }
  },

  startSessionTimer() {
    if (this.sessionTimerIntervalId) clearInterval(this.sessionTimerIntervalId);
    this.sessionTimerIntervalId = setInterval(() => {
      if (!this.sessionStartTime) return;
      const elapsed = Math.floor((Date.now() - this.sessionStartTime) / 1000);
      const h = String(Math.floor(elapsed / 3600)).padStart(2, "0");
      const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
      const s = String(elapsed % 60).padStart(2, "0");
      const el = document.getElementById("sessionTimer");
      if (el) el.textContent = `${h}:${m}:${s}`;
    }, 1000);
  },

  async endSession() {
    try {
      const response = await fetch("/end-session/", { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Unable to end session.");

      this.sessionActive = false;
      this.sessionPaused = false;
      this.sessionStatusEl.textContent = "Stopped";
      this.startSessionBtn.disabled = false;
      this.endSessionBtn.disabled = true;
      this.pauseSessionBtn.disabled = true;
      if (this.captureIntervalId) { clearInterval(this.captureIntervalId); this.captureIntervalId = null; }
      if (this.sessionTimerIntervalId) { clearInterval(this.sessionTimerIntervalId); this.sessionTimerIntervalId = null; }

      window.LiveSessionBadge?.setInactive();
      window.ToastManager?.show("success", "Session Ended", "Attendance summary computed.");
      this.refreshLiveTable();
    } catch (error) {
      window.ToastManager?.show("error", "Session Error", error.message);
    }
  },

  async refreshLiveTable() {
    try {
      const res = await fetch("/api/attendance/live/");
      const data = await res.json();
      const tbody = document.getElementById("liveAttendanceBody");
      if (!tbody) return;
      if (!data.rows?.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-muted" style="text-align:center;padding:2rem;">No attendance records yet.</td></tr>';
        return;
      }
      tbody.innerHTML = data.rows.map((r) => `
        <tr>
          <td><span class="font-medium">${r.name}</span></td>
          <td>${r.recognition_time}</td>
          <td>${r.confidence_percent}%</td>
          <td><span class="status-chip status-chip--${(r.status || '').toLowerCase()}">${r.status}</span></td>
          <td>${r.attendance_percent}%</td>
          <td><span class="badge badge-${r.state === 'recognized' ? 'success' : 'warning'}">${r.state}</span></td>
        </tr>
      `).join("");
    } catch (e) { /* silent */ }
  },
};

window.AttendanceApp = AttendanceApp;
