"""Shared template context: single source of truth for current server time."""

from attendance.utils.datetime_fmt import fmt_date, fmt_datetime, fmt_time, local_now


def server_time(request):
    now = local_now()
    return {
        "server_now": now,
        "server_now_iso": now.isoformat(),
        "server_date_display": fmt_date(now),
        "server_time_display": fmt_time(now),
        "server_datetime_display": fmt_datetime(now),
    }
