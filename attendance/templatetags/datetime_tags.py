"""Template filters for consistent date/time display."""

from django import template

from attendance.utils.datetime_fmt import fmt_date as _fmt_date
from attendance.utils.datetime_fmt import fmt_datetime as _fmt_datetime
from attendance.utils.datetime_fmt import fmt_time as _fmt_time

register = template.Library()


@register.filter(name="fmt_date")
def fmt_date(value):
    """DD MMM YYYY — e.g. 02 Aug 2026"""
    return _fmt_date(value)


@register.filter(name="fmt_time")
def fmt_time(value):
    """HH:MM:SS (24h, Dar es Salaam) — e.g. 14:35:27"""
    return _fmt_time(value)


@register.filter(name="fmt_datetime")
def fmt_datetime(value):
    """DD MMM YYYY • HH:MM:SS (Dar es Salaam) — e.g. 02 Aug 2026 • 14:35:27"""
    return _fmt_datetime(value)
