"""
Canonical date/time formatting for Univera.

Storage (USE_TZ=True): UTC in the database via timezone.now().
Display: always Africa/Dar_es_Salaam wall time via Django timezone.localtime().

Recognition / lecturer-facing format (example):
  Aug 02, 23:14:24
"""

from datetime import date, datetime, time, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.utils import timezone
from django.utils.dateformat import format as dj_format

# Explicit display zone — matches navbar clock and middleware activation
DISPLAY_TZ_NAME = "Africa/Dar_es_Salaam"
DISPLAY_TZ = ZoneInfo(DISPLAY_TZ_NAME)
UTC = dt_timezone.utc

# Django dateformat codes (English, locale-stable)
DATE_DJ = "M d, Y"          # Aug 02, 2026
TIME_DJ = "H:i:s"           # 23:14:24
DATETIME_DJ = "M d, H:i:s"  # Aug 02, 23:14:24


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
    """Format a date or datetime as MMM DD, YYYY — e.g. Aug 02, 2026."""
    if value is None or value == "":
        return "—"
    value = to_local(value)
    if isinstance(value, datetime):
        return dj_format(value, DATE_DJ)
    if isinstance(value, date):
        return dj_format(value, DATE_DJ)
    return str(value)


def fmt_time(value):
    """Format a time or datetime as HH:MM:SS (24-hour, Dar es Salaam)."""
    if value is None or value == "":
        return "—"
    value = to_local(value)
    if isinstance(value, datetime):
        return dj_format(value, TIME_DJ)
    if isinstance(value, time):
        return value.strftime("%H:%M:%S")
    return str(value)


def fmt_datetime(value):
    """
    Format a datetime as local Tanzania time for lecturers.

    Example: recognition at 23:14:24 Dar → "Aug 02, 23:14:24"
    Never returns raw UTC clock time.
    """
    if value is None or value == "":
        return "—"
    value = to_local(value)
    if isinstance(value, datetime):
        return dj_format(value, DATETIME_DJ)
    if isinstance(value, date):
        return dj_format(value, DATE_DJ)
    return str(value)
