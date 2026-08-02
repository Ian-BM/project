from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from attendance.utils.datetime_fmt import fmt_datetime, fmt_time

from attendance.models import (
    AttendanceSummary,
    Course,
    Department,
    Detection,
    Enrollment,
    Module,
    ModuleEnrollment,
    Programme,
    Session,
    Student,
    StudentProfile,
)
from attendance.utils.datetime_fmt import fmt_datetime, fmt_time


def _teacher_sessions(user):
    return Session.objects.filter(teacher=user)


def _today_sessions(user):
    today = timezone.localdate()
    return _teacher_sessions(user).filter(date=today)


def _latest_session(user):
    return (
        _teacher_sessions(user)
        .filter(is_active=False, end_time__isnull=False)
        .order_by("-end_time")
        .first()
    )


def _active_session(user):
    return _teacher_sessions(user).filter(is_active=True).order_by("-start_time").first()


def student_attendance_percent(student):
    summaries = AttendanceSummary.objects.filter(
        student=student, session__is_active=False
    )
    total = summaries.count()
    if total == 0:
        return 0.0
    present = summaries.filter(
        status__in=[AttendanceSummary.STATUS_PRESENT, AttendanceSummary.STATUS_PARTIAL]
    ).count()
    return round((present / total) * 100, 1)


def build_dashboard_context(user):
    today = timezone.localdate()
    sessions = _teacher_sessions(user)
    active = _active_session(user)
    latest = _latest_session(user)
    today_sess = _today_sessions(user)

    total_students = Student.objects.count()
    courses_count = Module.objects.filter(Q(teacher=user) | Q(teacher__isnull=True)).count()
    programmes_count = Programme.objects.count()
    departments_count = Department.objects.count()
    from django.contrib.auth.models import User

    lecturers_count = (
        User.objects.filter(Q(modules__isnull=False) | Q(sessions__isnull=False))
        .distinct()
        .count()
    )
    active_sessions = sessions.filter(is_active=True).count()

    today_summaries = AttendanceSummary.objects.filter(session__in=today_sess.filter(is_active=False))
    present_today = today_summaries.filter(
        status__in=[AttendanceSummary.STATUS_PRESENT, AttendanceSummary.STATUS_PARTIAL]
    ).values("student_id").distinct().count()
    absent_today = max(total_students - present_today, 0)

    if total_students > 0:
        attendance_rate = round((present_today / total_students) * 100, 1)
    else:
        attendance_rate = 0.0

    avg_confidence = (
        AttendanceSummary.objects.filter(session__teacher=user)
        .aggregate(avg=Avg("confidence_score"))["avg"]
        or 0.0
    )
    avg_confidence_pct = round(float(avg_confidence) * 100, 1)

    total_frames = sessions.aggregate(total=Sum("total_frames"))["total"] or 0
    total_detections = Detection.objects.filter(session__teacher=user).count()
    if total_frames > 0:
        recognition_accuracy = round(min((total_detections / max(total_frames, 1)) * 100, 100), 1)
    else:
        recognition_accuracy = 0.0

    kpis = {
        "total_students": total_students,
        "present_today": present_today,
        "absent_today": absent_today,
        "attendance_rate": attendance_rate,
        "recognition_accuracy": recognition_accuracy,
        "average_confidence": avg_confidence_pct,
        "courses": courses_count,
        "modules": courses_count,
        "programmes": programmes_count,
        "departments": departments_count,
        "lecturers": lecturers_count,
        "active_sessions": active_sessions,
    }

    live_status = {
        "has_active": bool(active),
        "session_id": active.id if active else None,
        "teacher_name": user.get_full_name() or user.username,
        "lecturer_name": user.get_full_name() or user.username,
        "course_name": active.module.name if active and active.module else "—",
        "course_code": active.module.code if active and active.module else "",
        "module_name": active.module.name if active and active.module else "—",
        "module_code": active.module.code if active and active.module else "",
        "programme_name": (
            active.module.programme.name
            if active and active.module and active.module.programme
            else "—"
        ),
        "frames_processed": active.total_frames if active else 0,
        "students_detected": (
            Detection.objects.filter(session=active).values("student_id").distinct().count()
            if active
            else 0
        ),
        "started_at": active.start_time.isoformat() if active else None,
    }

    recent_sessions = list(
        sessions.filter(is_active=False).select_related("module").order_by("-end_time")[:5]
    )
    recent_detections = list(
        Detection.objects.filter(session__teacher=user)
        .select_related("student", "session")
        .order_by("-timestamp")[:8]
    )
    recent_summaries = list(
        AttendanceSummary.objects.filter(session__teacher=user)
        .select_related("student", "session")
        .order_by("-session__end_time")[:8]
    )

    alerts = _build_alerts(user, total_students, present_today, avg_confidence_pct)

    return {
        "kpis": kpis,
        "live_status": live_status,
        "recent_sessions": recent_sessions,
        "recent_detections": recent_detections,
        "recent_summaries": recent_summaries,
        "alerts": alerts,
        "chart_data": build_chart_data(user),
    }


def _build_alerts(user, total_students, present_today, avg_confidence):
    alerts = []
    if total_students > 0 and present_today < total_students * 0.5:
        alerts.append(
            {
                "type": "warning",
                "title": "Low Attendance",
                "message": f"Only {present_today} of {total_students} students present today.",
            }
        )
    if avg_confidence < 50 and avg_confidence > 0:
        alerts.append(
            {
                "type": "danger",
                "title": "Low Recognition Confidence",
                "message": f"Average confidence is {avg_confidence}%. Consider re-encoding faces.",
            }
        )
    at_risk = StudentProfile.objects.filter(risk_level=StudentProfile.RISK_HIGH).count()
    if at_risk:
        alerts.append(
            {
                "type": "warning",
                "title": "Students At Risk",
                "message": f"{at_risk} student(s) flagged as high risk.",
            }
        )
    if not alerts:
        alerts.append(
            {
                "type": "info",
                "title": "System Normal",
                "message": "All systems operating normally.",
            }
        )
    return alerts


def build_chart_data(user):
    today = timezone.localdate()
    weekly_labels = []
    weekly_values = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        weekly_labels.append(day.strftime("%a"))
        day_sessions = Session.objects.filter(teacher=user, date=day, is_active=False)
        summaries = AttendanceSummary.objects.filter(
            session__in=day_sessions,
            status__in=[AttendanceSummary.STATUS_PRESENT, AttendanceSummary.STATUS_PARTIAL],
        ).values("student_id").distinct().count()
        weekly_values.append(summaries)

    monthly_labels = []
    monthly_values = []
    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
        label = month_start.strftime("%b")
        monthly_labels.append(label)
        month_sessions = Session.objects.filter(
            teacher=user, date__year=month_start.year, date__month=month_start.month, is_active=False
        )
        count = AttendanceSummary.objects.filter(
            session__in=month_sessions,
            status__in=[AttendanceSummary.STATUS_PRESENT, AttendanceSummary.STATUS_PARTIAL],
        ).count()
        monthly_values.append(count)

    course_labels = []
    course_values = []
    for course in Module.objects.filter(teacher=user)[:6]:
        course_labels.append(course.code)
        enrolled = ModuleEnrollment.objects.filter(module=course).count()
        course_values.append(enrolled)

    if not course_labels:
        course_labels = ["No courses"]
        course_values = [0]

    confidence_buckets = {"0-40": 0, "40-75": 0, "75-100": 0}
    for summary in AttendanceSummary.objects.filter(session__teacher=user):
        pct = summary.confidence_score * 100
        if pct < 40:
            confidence_buckets["0-40"] += 1
        elif pct < 75:
            confidence_buckets["40-75"] += 1
        else:
            confidence_buckets["75-100"] += 1

    trend_labels = weekly_labels
    trend_present = weekly_values
    trend_absent = [max(Student.objects.count() - v, 0) for v in weekly_values]

    return {
        "weekly": {"labels": weekly_labels, "values": weekly_values},
        "monthly": {"labels": monthly_labels, "values": monthly_values},
        "by_course": {"labels": course_labels, "values": course_values},
        "confidence": {
            "labels": list(confidence_buckets.keys()),
            "values": list(confidence_buckets.values()),
        },
        "trends": {
            "labels": trend_labels,
            "present": trend_present,
            "absent": trend_absent,
        },
    }


def get_live_attendance_rows(session):
    if not session:
        return []

    students_seen = {}
    detections = Detection.objects.filter(session=session).select_related("student").order_by("timestamp")

    for det in detections:
        sid = det.student_id
        if sid not in students_seen:
            students_seen[sid] = {
                "name": det.student.name,
                "first_seen": det.timestamp,
                "last_seen": det.timestamp,
                "count": 1,
            }
        else:
            students_seen[sid]["last_seen"] = det.timestamp
            students_seen[sid]["count"] += 1

    rows = []
    for sid, data in students_seen.items():
        summary = AttendanceSummary.objects.filter(student_id=sid, session=session).first()
        confidence = summary.confidence_score if summary else 0.0
        status = summary.status if summary else "In Progress"
        att_pct = student_attendance_percent(Student.objects.get(pk=sid))
        rows.append(
            {
                "student_id": sid,
                "name": data["name"],
                "recognition_time": fmt_datetime(data["last_seen"]),
                "first_seen": fmt_datetime(data["first_seen"]),
                "last_seen": fmt_datetime(data["last_seen"]),
                "confidence": round(confidence, 4),
                "confidence_percent": round(confidence * 100, 1),
                "status": status,
                "attendance_percent": att_pct,
                "state": "recognized" if data["count"] >= 3 else "processing",
                "detection_count": data["count"],
            }
        )
    return sorted(rows, key=lambda r: r["name"])
