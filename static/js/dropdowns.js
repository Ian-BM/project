/**
 * Dropdown menus — notifications, profile, click-outside close
 */
const DropdownManager = {
  init() {
    document.querySelectorAll("[data-dropdown-toggle]").forEach((toggle) => {
      const targetId = toggle.getAttribute("data-dropdown-toggle");
      const menu = document.getElementById(targetId);
      if (!menu) return;

      toggle.addEventListener("click", (e) => {
        e.stopPropagation();
        const isOpen = menu.classList.contains("is-open");
        this.closeAll();
        if (!isOpen) {
          menu.classList.add("is-open");
          toggle.setAttribute("aria-expanded", "true");
        }
      });
    });

    document.addEventListener("click", () => this.closeAll());

    document.querySelectorAll(".dropdown-menu").forEach((menu) => {
      menu.addEventListener("click", (e) => e.stopPropagation());
    });
  },

  closeAll() {
    document.querySelectorAll(".dropdown-menu.is-open").forEach((menu) => {
      menu.classList.remove("is-open");
    });
    document.querySelectorAll("[data-dropdown-toggle]").forEach((toggle) => {
      toggle.setAttribute("aria-expanded", "false");
    });
  },
};

window.DropdownManager = DropdownManager;
