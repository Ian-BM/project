/**
 * Live session badge — reads session state from sessionStorage
 */
const LiveSessionBadge = {
  STORAGE_KEY: "univera-live-session",

  init() {
    this.badge = document.getElementById("liveSessionBadge");
    this.update();

    window.addEventListener("storage", () => this.update());
    setInterval(() => this.update(), 2000);
  },

  setActive(sessionId) {
    sessionStorage.setItem(this.STORAGE_KEY, JSON.stringify({ active: true, id: sessionId }));
    this.update();
  },

  setInactive() {
    sessionStorage.removeItem(this.STORAGE_KEY);
    this.update();
  },

  update() {
    if (!this.badge) return;
    try {
      const data = JSON.parse(sessionStorage.getItem(this.STORAGE_KEY) || "null");
      if (data && data.active) {
        this.badge.classList.add("is-active");
        const label = this.badge.querySelector("[data-live-session-label]");
        if (label) label.textContent = `Live Session #${data.id}`;
      } else {
        this.badge.classList.remove("is-active");
      }
    } catch {
      this.badge.classList.remove("is-active");
    }
  },
};

window.LiveSessionBadge = LiveSessionBadge;
