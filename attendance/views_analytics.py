from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import render
from django.utils import timezone

from attendance.models import (
    AttendanceSummary,
    Detection,
    Module,
    Notification,
    PerformanceRecord,
    Programme,
    Session,
    Student,
)
from attendance.services.academic import build_ai_insights, leaderboard_data


@login_required
def analytics_dashboard(request):
    today = timezone.now().date()

    weekly_labels, weekly_att, weekly_conf = [], [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        weekly_labels.append(day.strftime("%a"))
        day_sessions = Session.objects.filter(date=day, is_active=False)
        summaries = AttendanceSummary.objects.filter(session__in=day_sessions)
        present = summaries.filter(status__in=["Present", "Partial"]).count()
        weekly_att.append(present)
        avg = summaries.aggregate(a=Avg("confidence_score"))["a"] or 0
        weekly_conf.append(round(float(avg) * 100, 1))

    programme_labels, programme_values = [], []
    for p in Programme.objects.all()[:8]:
        programme_labels.append(p.code)
        programme_values.append(
            AttendanceSummary.objects.filter(
                session__module__programme=p, status__in=["Present", "Partial"]
            ).count()
        )

    module_labels, module_values = [], []
    for m in Module.objects.all()[:8]:
        module_labels.append(m.code)
        module_values.append(Session.objects.filter(module=m).count())

    # Attendance heatmap-style matrix (weekday x hour bucket simplified)
    heatmap = []
    for dow in range(7):
        row = []
        for hour_bucket in range(4):  # morning/afternoon/evening/night
            count = Detection.objects.filter(
                timestamp__week_day=((dow + 1) % 7) + 1  # Django week_day: Sun=1
            ).count()  # simplified aggregate
            row.append(min(count, 20))
        heatmap.append(row)

    # Performance correlation sample
    correlation = []
    for student in Student.objects.all()[:40]:
        from attendance.services.academic import (
            student_attendance_percent,
            student_avg_performance,
        )

        att = student_attendance_percent(student)
        perf = student_avg_performance(student)
        if perf is not None:
            correlation.append({"name": student.name, "attendance": att, "performance": perf})

    leaders = leaderboard_data()
    # Sort best modules/programmes by attendance
    leaders["best_modules"] = sorted(
        leaders["best_modules"], key=lambda x: x["attendance_percent"], reverse=True
    )[:5]
    leaders["best_programmes"] = sorted(
        leaders["best_programmes"], key=lambda x: x["attendance_percent"], reverse=True
    )[:5]

    unread = Notification.objects.filter(user=request.user, is_read=False).count()

    chart_data = {
        "attendance_trends": {"labels": weekly_labels, "values": weekly_att},
        "confidence_trends": {"labels": weekly_labels, "values": weekly_conf},
        "recognition_trends": {
            "labels": weekly_labels,
            "values": [
                Detection.objects.filter(timestamp__date=today - timedelta(days=i)).count()
                for i in range(6, -1, -1)
            ],
        },
        "programmes": {"labels": programme_labels, "values": programme_values},
        "modules": {"labels": module_labels, "values": module_values},
    }

    return render(
        request,
        "attendance/analytics/dashboard.html",
        {
            "chart_data": chart_data,
            "leaders": leaders,
            "insights": build_ai_insights()[:10],
            "correlation": correlation,
            "heatmap": heatmap,
            "kpis": {
                "students": Student.objects.count(),
                "programmes": Programme.objects.count(),
                "modules": Module.objects.count(),
                "sessions": Session.objects.count(),
                "detections": Detection.objects.count(),
                "unread_notifications": unread,
            },
        },
    )


@login_required
def notifications_list(request):
    notes = Notification.objects.filter(user=request.user)
    if request.GET.get("mark") == "read":
        notes.filter(is_read=False).update(is_read=True)
    return render(
        request,
        "attendance/notifications/list.html",
        {"notifications": notes[:50]},
    )


@login_required
def notification_mark_read(request, pk):
    from django.shortcuts import redirect

    Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    return redirect("notifications_list")
