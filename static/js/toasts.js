/**
 * Toast notification system
 */
const ToastManager = {
  container: null,
  icons: {
    success: "check-circle",
    error: "x-circle",
    warning: "alert-triangle",
    info: "info",
  },

  init() {
    this.container = document.getElementById("toastContainer");
    if (!this.container) {
      this.container = document.createElement("div");
      this.container.id = "toastContainer";
      this.container.className = "toast-container";
      this.container.setAttribute("aria-live", "polite");
      document.body.appendChild(this.container);
    }
  },

  show(type, title, message, duration = 5000) {
    if (!this.container) this.init();

    const toast = document.createElement("div");
    toast.className = `toast toast--${type}`;
    toast.innerHTML = `
      <span class="toast-icon"><i data-lucide="${this.icons[type] || "info"}"></i></span>
      <div class="toast-content">
        <div class="toast-title">${this.escape(title)}</div>
        ${message ? `<div class="toast-message">${this.escape(message)}</div>` : ""}
      </div>
      <button class="toast-close" aria-label="Dismiss">
        <i data-lucide="x"></i>
      </button>
    `;

    this.container.appendChild(toast);

    if (window.lucide) {
      window.lucide.createIcons({ nodes: [toast] });
    }

    const close = () => {
      toast.classList.add("is-leaving");
      setTimeout(() => toast.remove(), 200);
    };

    toast.querySelector(".toast-close").addEventListener("click", close);

    if (duration > 0) {
      setTimeout(close, duration);
    }

    return toast;
  },

  escape(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  },
};

window.ToastManager = ToastManager;
