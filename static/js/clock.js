/**
 * Live clock synchronized to Django server time.
 * Always renders East Africa Time (EAT / Africa/Dar_es_Salaam):
 *   Aug 02, 23:14:24
 * Same timezone + format as Recognition History and other modules.
 */
const ClockManager = {
  TZ: "Africa/Dar_es_Salaam",
  LABEL: "EAT",
  _offsetMs: 0,

  init() {
    const el = document.getElementById("topbarClock");
    if (!el) return;

    const tz = el.getAttribute("data-timezone");
    if (tz) this.TZ = tz;

    const iso = el.getAttribute("data-server-now");
    if (iso) {
      const serverMs = Date.parse(iso);
      if (!Number.isNaN(serverMs)) {
        this._offsetMs = serverMs - Date.now();
      }
    }

    const update = () => {
      const now = new Date(Date.now() + this._offsetMs);
      el.textContent = this.formatDateTime(now);
      el.setAttribute("datetime", now.toISOString());
      el.setAttribute("title", `${el.textContent} (${this.LABEL})`);
    };

    update();
    setInterval(update, 1000);
  },

  formatDateTime(d) {
    const dateParts = new Intl.DateTimeFormat("en-US", {
      timeZone: this.TZ,
      day: "2-digit",
      month: "short",
    }).formatToParts(d);

    const timeParts = new Intl.DateTimeFormat("en-GB", {
      timeZone: this.TZ,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
      hourCycle: "h23",
    }).formatToParts(d);

    const get = (parts, type) => (parts.find((p) => p.type === type) || {}).value || "";
    const day = get(dateParts, "day");
    const month = get(dateParts, "month");
    let hour = get(timeParts, "hour");
    const minute = get(timeParts, "minute");
    const second = get(timeParts, "second");
    if (hour === "24") hour = "00";

    return `${month} ${day}, ${hour}:${minute}:${second}`;
  },
};

window.ClockManager = ClockManager;
