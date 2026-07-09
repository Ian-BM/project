/**
 * Modal and confirmation dialog system
 */
const ModalManager = {
  overlay: null,

  init() {
    this.overlay = document.getElementById("modalOverlay");
    if (!this.overlay) return;

    this.overlay.querySelectorAll("[data-modal-close]").forEach((btn) => {
      btn.addEventListener("click", () => this.close());
    });

    this.overlay.addEventListener("click", (e) => {
      if (e.target === this.overlay) this.close();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.overlay.classList.contains("is-open")) {
        this.close();
      }
    });
  },

  open(options = {}) {
    if (!this.overlay) return;

    const title = this.overlay.querySelector("[data-modal-title]");
    const body = this.overlay.querySelector("[data-modal-body]");
    const confirmBtn = this.overlay.querySelector("[data-modal-confirm]");

    if (title) title.textContent = options.title || "Confirm";
    if (body) body.innerHTML = options.body || "";
    if (confirmBtn) {
      confirmBtn.textContent = options.confirmText || "Confirm";
      confirmBtn.className = `btn ${options.confirmClass || "btn-primary"}`;
      confirmBtn.onclick = () => {
        if (options.onConfirm) options.onConfirm();
        this.close();
      };
    }

    this.overlay.classList.add("is-open");
    document.body.style.overflow = "hidden";
  },

  close() {
    if (!this.overlay) return;
    this.overlay.classList.remove("is-open");
    document.body.style.overflow = "";
  },

  confirm(title, body, onConfirm) {
    this.open({ title, body, onConfirm, confirmText: "Confirm", confirmClass: "btn-danger" });
  },
};

window.ModalManager = ModalManager;
