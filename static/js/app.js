/**
 * Application bootstrap — initializes all UI modules
 */
document.addEventListener("DOMContentLoaded", () => {
  if (window.ThemeManager) ThemeManager.init();
  if (window.SidebarManager) SidebarManager.init();
  if (window.DropdownManager) DropdownManager.init();
  if (window.SearchManager) SearchManager.init();
  if (window.ToastManager) ToastManager.init();
  if (window.ModalManager) ModalManager.init();
  if (window.ClockManager) ClockManager.init();
  if (window.LiveSessionBadge) LiveSessionBadge.init();

  if (window.lucide) {
    lucide.createIcons();
  }

  if (document.getElementById("video") && window.AttendanceApp) {
    AttendanceApp.init();
  }

  const djangoMessages = document.querySelectorAll("[data-django-message]");
  djangoMessages.forEach((el) => {
    const type = el.dataset.djangoMessage || "info";
    const text = el.textContent.trim();
    if (text && window.ToastManager) {
      ToastManager.show(type, type.charAt(0).toUpperCase() + type.slice(1), text);
    }
    el.remove();
  });
});
