"""Template filters for East Africa Time (EAT) display."""

from django import template

from attendance.utils.datetime_fmt import fmt_date as _fmt_date
from attendance.utils.datetime_fmt import fmt_datetime as _fmt_datetime
from attendance.utils.datetime_fmt import fmt_time as _fmt_time

register = template.Library()


@register.filter(name="fmt_date")
def fmt_date(value):
    """EAT date — e.g. Aug 03, 2026"""
    return _fmt_date(value)


@register.filter(name="fmt_time")
def fmt_time(value):
    """EAT time — e.g. 00:20:29"""
    return _fmt_time(value)


@register.filter(name="fmt_datetime")
def fmt_datetime(value):
    """
    EAT datetime — e.g. Aug 03, 00:20:29

    Always converts UTC → Africa/Dar_es_Salaam before formatting.
    """
    return _fmt_datetime(value)
