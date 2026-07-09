/**
 * Live clock in top navigation
 */
const ClockManager = {
  init() {
    const el = document.getElementById("topbarClock");
    if (!el) return;

    const update = () => {
      const now = new Date();
      el.textContent = now.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    };

    update();
    setInterval(update, 1000);
  },
};

window.ClockManager = ClockManager;
