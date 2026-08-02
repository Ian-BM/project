"""
Canonical date/time formatting for Univera.

All UI timestamps should go through these helpers so every page
displays the same Africa/Dar_es_Salaam local time and format:

  Date:      02 Aug 2026
  Time:      14:35
  DateTime:  02 Aug 2026 • 14:35
"""

from datetime import date, datetime, time

from django.utils import timezone

DATE_FMT = "%d %b %Y"
TIME_FMT = "%H:%M"
DATETIME_SEP = " • "


def local_now():
    """Current timezone-aware datetime in the active Django timezone."""
    return timezone.localtime(timezone.now())


def to_local(value):
    """Convert a datetime to the active timezone; leave date/time as-is."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            # Treat naive values as UTC (Django default storage) then localize
            value = timezone.make_aware(value, timezone.utc)
        return timezone.localtime(value)
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
    """Format a datetime as DD MMM YYYY • HH:MM."""
    if value is None or value == "":
        return "—"
    value = to_local(value)
    if isinstance(value, datetime):
        return f"{value.strftime(DATE_FMT)}{DATETIME_SEP}{value.strftime(TIME_FMT)}"
    if isinstance(value, date):
        return value.strftime(DATE_FMT)
    return str(value)
