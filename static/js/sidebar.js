/**
 * Sidebar navigation — mobile toggle, overlay, placeholder links
 */
const SidebarManager = {
  init() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    const hamburger = document.getElementById("sidebarToggle");

    if (hamburger && sidebar) {
      hamburger.addEventListener("click", () => this.toggle(sidebar, overlay));
    }

    if (overlay && sidebar) {
      overlay.addEventListener("click", () => this.close(sidebar, overlay));
    }

    document.querySelectorAll(".sidebar-nav-item--placeholder").forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        if (window.ToastManager) {
          window.ToastManager.show("info", "Coming Soon", "This module will be available in a future release.");
        }
        this.close(sidebar, overlay);
      });
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 768 && sidebar && overlay) {
        this.close(sidebar, overlay);
      }
    });
  },

  toggle(sidebar, overlay) {
    const isOpen = sidebar.classList.toggle("is-open");
    if (overlay) {
      overlay.classList.toggle("is-visible", isOpen);
    }
  },

  close(sidebar, overlay) {
    if (sidebar) sidebar.classList.remove("is-open");
    if (overlay) overlay.classList.remove("is-visible");
  },
};

window.SidebarManager = SidebarManager;
