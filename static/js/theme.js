/**
 * Theme management — light/dark mode with localStorage persistence
 */
const ThemeManager = {
  STORAGE_KEY: "univera-theme",

  init() {
    const saved = localStorage.getItem(this.STORAGE_KEY);
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const theme = saved || (prefersDark ? "dark" : "light");
    this.setTheme(theme, false);

    document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
      btn.addEventListener("click", () => this.toggle());
    });
  },

  getTheme() {
    return document.documentElement.getAttribute("data-theme") || "light";
  },

  setTheme(theme, save = true) {
    document.documentElement.setAttribute("data-theme", theme);
    if (save) {
      localStorage.setItem(this.STORAGE_KEY, theme);
    }
    this.updateToggleIcons(theme);
  },

  toggle() {
    const next = this.getTheme() === "dark" ? "light" : "dark";
    this.setTheme(next);
  },

  updateToggleIcons(theme) {
    document.querySelectorAll("[data-theme-icon-light]").forEach((el) => {
      el.classList.toggle("hidden", theme === "dark");
    });
    document.querySelectorAll("[data-theme-icon-dark]").forEach((el) => {
      el.classList.toggle("hidden", theme === "light");
    });
  },
};

window.ThemeManager = ThemeManager;
