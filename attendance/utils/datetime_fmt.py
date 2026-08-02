"""
Canonical date/time formatting for Univera.

Storage (USE_TZ=True): UTC in the database via timezone.now().
Display: always Africa/Dar_es_Salaam wall time via Django timezone.localtime().

Formats:
  Date:      02 Aug 2026
  Time:      14:35:27
  DateTime:  02 Aug 2026 • 14:35:27
"""

from datetime import date, datetime, time, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.utils import timezone

# Explicit display zone — matches navbar clock and middleware activation
DISPLAY_TZ_NAME = "Africa/Dar_es_Salaam"
DISPLAY_TZ = ZoneInfo(DISPLAY_TZ_NAME)
UTC = dt_timezone.utc

DATE_FMT = "%d %b %Y"
TIME_FMT = "%H:%M:%S"
DATETIME_SEP = " • "


def local_now():
    """Current timezone-aware datetime in Africa/Dar_es_Salaam."""
    return timezone.localtime(timezone.now(), DISPLAY_TZ)


def to_local(value):
    """
    Convert any datetime to Africa/Dar_es_Salaam for display.

    With USE_TZ=True, DB values are UTC. Naive values are treated as UTC
    (Django's SQLite convention when USE_TZ is enabled).
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            value = timezone.make_aware(value, UTC)
        return timezone.localtime(value, DISPLAY_TZ)
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
    """Format a time or datetime as HH:MM:SS (24-hour, Dar es Salaam)."""
    if value is None or value == "":
        return "—"
    value = to_local(value)
    if isinstance(value, datetime):
        return value.strftime(TIME_FMT)
    if isinstance(value, time):
        return value.strftime(TIME_FMT)
    return str(value)


def fmt_datetime(value):
    """Format a datetime as DD MMM YYYY • HH:MM:SS in Dar es Salaam."""
    if value is None or value == "":
        return "—"
    value = to_local(value)
    if isinstance(value, datetime):
        return f"{value.strftime(DATE_FMT)}{DATETIME_SEP}{value.strftime(TIME_FMT)}"
    if isinstance(value, date):
        return value.strftime(DATE_FMT)
    return str(value)
