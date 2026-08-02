"""
Canonical date/time formatting for Univera.

Storage (USE_TZ=True): UTC via timezone.now().
Display: East Africa Time (EAT) = Africa/Dar_es_Salaam (UTC+3).

IMPORTANT:
  django.utils.dateformat.format() uses the datetime's own wall-clock fields.
  Formatting a UTC datetime WITHOUT astimezone() first produces UTC labels
  (e.g. 21:20 when EAT is 00:20). Always convert with to_local() first.
"""

from datetime import date, datetime, time, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.utils import timezone

# East Africa Time — same zone as the navbar clock
DISPLAY_TZ_NAME = "Africa/Dar_es_Salaam"
DISPLAY_TZ_LABEL = "EAT"
DISPLAY_TZ = ZoneInfo(DISPLAY_TZ_NAME)
UTC = dt_timezone.utc

_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def local_now():
    """Current time in East Africa Time (matches navbar clock source)."""
    return timezone.now().astimezone(DISPLAY_TZ)


def to_local(value):
    """
    Convert any datetime to Africa/Dar_es_Salaam (EAT).

    Uses datetime.astimezone() — not Django dateformat — so UTC cannot leak
    into displayed hour/minute/second fields.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            # SQLite/USE_TZ: naive values are UTC
            value = value.replace(tzinfo=UTC)
        return value.astimezone(DISPLAY_TZ)
    return value


def _fmt_eat_datetime(eat_dt: datetime) -> str:
    """Format an EAT-aware datetime as 'Aug 03, 00:20:29'."""
    return (
        f"{_MONTHS[eat_dt.month - 1]} {eat_dt.day:02d}, "
        f"{eat_dt.hour:02d}:{eat_dt.minute:02d}:{eat_dt.second:02d}"
    )


def _fmt_eat_date(eat_date: date) -> str:
    return f"{_MONTHS[eat_date.month - 1]} {eat_date.day:02d}, {eat_date.year}"


def fmt_date(value):
    """MMM DD, YYYY in EAT — e.g. Aug 03, 2026."""
    if value is None or value == "":
        return "—"
    value = to_local(value)
    if isinstance(value, datetime):
        return _fmt_eat_date(value.date())
    if isinstance(value, date):
        return _fmt_eat_date(value)
    return str(value)


def fmt_time(value):
    """HH:MM:SS in EAT — e.g. 00:20:29."""
    if value is None or value == "":
        return "—"
    value = to_local(value)
    if isinstance(value, datetime):
        return f"{value.hour:02d}:{value.minute:02d}:{value.second:02d}"
    if isinstance(value, time):
        return f"{value.hour:02d}:{value.minute:02d}:{value.second:02d}"
    return str(value)


def fmt_datetime(value):
    """
    Lecturer-facing datetime in East Africa Time.

    UTC 21:20:08 → "Aug 03, 00:20:08"
    Never formats UTC wall-clock fields directly.
    """
    if value is None or value == "":
        return "—"
    value = to_local(value)
    if isinstance(value, datetime):
        return _fmt_eat_datetime(value)
    if isinstance(value, date):
        return _fmt_eat_date(value)
    return str(value)
