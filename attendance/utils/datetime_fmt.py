"""
Canonical date/time formatting for Univera.

Always display Africa/Dar_es_Salaam wall time (never raw UTC), using:

  Date:      02 Aug 2026
  Time:      14:35
  DateTime:  02 Aug 2026 • 14:35
"""

from datetime import date, datetime, time, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.utils import timezone

# Single source of truth for display — do not rely on ambient Django activate()
DISPLAY_TZ = ZoneInfo("Africa/Dar_es_Salaam")
UTC = dt_timezone.utc

DATE_FMT = "%d %b %Y"
TIME_FMT = "%H:%M"
DATETIME_SEP = " • "


def local_now():
    """Current timezone-aware datetime in Africa/Dar_es_Salaam."""
    return timezone.now().astimezone(DISPLAY_TZ)


def to_local(value):
    """
    Convert any datetime to Africa/Dar_es_Salaam for display.

    DB values are stored in UTC (USE_TZ=True). Naive values are treated as UTC.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            value = value.replace(tzinfo=UTC)
        return value.astimezone(DISPLAY_TZ)
    return value


def fmt_date(value):
    """Format a date or datetime as DD MMM YYYY."""
    if value is None or value == "":
        return "—"
    value = to_local(value)
    if isinstance(value, datetime):
        return value.strftime(DATE_FMT)
    if isinstance(value, date):
        return value.strftime(DATE_FMT)
    return str(value)


def fmt_time(value):
    """Format a time or datetime as HH:MM (24-hour)."""
    if value is None or value == "":
        return "—"
    value = to_local(value)
    if isinstance(value, datetime):
        return value.strftime(TIME_FMT)
    if isinstance(value, time):
        return value.strftime(TIME_FMT)
    return str(value)


def fmt_datetime(value):
    """Format a datetime as DD MMM YYYY • HH:MM in Dar es Salaam."""
    if value is None or value == "":
        return "—"
    value = to_local(value)
    if isinstance(value, datetime):
        return f"{value.strftime(DATE_FMT)}{DATETIME_SEP}{value.strftime(TIME_FMT)}"
    if isinstance(value, date):
        return value.strftime(DATE_FMT)
    return str(value)
