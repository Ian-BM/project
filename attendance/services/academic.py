"""Shared academic helpers for Programme / Module / Session analytics."""

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from attendance.models import (
    Assessment,
    AttendanceSummary,
    Detection,
    Module,
    ModuleEnrollment,
    Notification,
    PerformanceRecord,
    Programme,
    Session,
    Student,
    StudentProfile,
)


def student_attendance_percent(student):
    summaries = AttendanceSummary.objects.filter(student=student, session__status=Session.STATUS_COMPLETED)
    # Also include legacy completed sessions (is_active=False)
    if summaries.count() == 0:
        summaries = AttendanceSummary.objects.filter(student=student, session__is_active=False)
    total = summaries.count()
    if total == 0:
        return 0.0
    present = summaries.filter(
        status__in=[AttendanceSummary.STATUS_PRESENT, AttendanceSummary.STATUS_PARTIAL]
    ).count()
    return round((present / total) * 100, 1)


def student_avg_confidence(student):
    avg = AttendanceSummary.objects.filter(student=student).aggregate(a=Avg("confidence_score"))["a"]
    return round(float(avg or 0) * 100, 1)


def student_avg_performance(student):
    records = PerformanceRecord.objects.filter(student=student).select_related("assessment")
    if not records.exists():
        profile = getattr(student, "profile", None)
        if profile and profile.average_grade is not None:
            return float(profile.average_grade)
        return None
    total = 0.0
    for r in records:
        total += r.percentage
    return round(total / records.count(), 1)


def session_attendance_percent(session):
    summaries = AttendanceSummary.objects.filter(session=session)
    total = summaries.count()
    if total == 0:
        # Fall back to detections vs enrolled
        enrolled = ModuleEnrollment.objects.filter(module=session.module).count() if session.module else 0
        detected = Detection.objects.filter(session=session).values("student_id").distinct().count()
        if enrolled:
            return round(min(detected / enrolled * 100, 100), 1)
        return 0.0
    present = summaries.filter(
        status__in=[AttendanceSummary.STATUS_PRESENT, AttendanceSummary.STATUS_PARTIAL]
    ).count()
    return round(present / total * 100, 1)


def session_avg_confidence(session):
    avg = AttendanceSummary.objects.filter(session=session).aggregate(a=Avg("confidence_score"))["a"]
    return round(float(avg or 0) * 100, 1)


def session_recognition_percent(session):
    frames = max(session.total_frames or 0, 1)
    detections = Detection.objects.filter(session=session).count()
    return round(min(detections / frames * 100, 100), 1)


def module_stats(module):
    sessions = Session.objects.filter(module=module, is_active=False)
    summaries = AttendanceSummary.objects.filter(session__module=module)
    present = summaries.filter(
        status__in=[AttendanceSummary.STATUS_PRESENT, AttendanceSummary.STATUS_PARTIAL]
    ).count()
    total = summaries.count()
    avg_conf = summaries.aggregate(a=Avg("confidence_score"))["a"] or 0
    records = PerformanceRecord.objects.filter(assessment__module=module)
    avg_marks = None
    if records.exists():
        avg_marks = round(sum(r.percentage for r in records) / records.count(), 1)
        pass_rate = round(sum(1 for r in records if r.passed) / records.count() * 100, 1)
    else:
        pass_rate = None
    return {
        "students": ModuleEnrollment.objects.filter(module=module).count(),
        "attendance_percent": round(present / total * 100, 1) if total else 0,
        "recognition_percent": round(float(avg_conf) * 100, 1),
        "avg_marks": avg_marks,
        "pass_rate": pass_rate,
        "sessions": sessions.count(),
    }


def programme_stats(programme):
    modules = Module.objects.filter(programme=programme)
    students = StudentProfile.objects.filter(programme=programme).count()
    summaries = AttendanceSummary.objects.filter(session__module__programme=programme)
    present = summaries.filter(
        status__in=[AttendanceSummary.STATUS_PRESENT, AttendanceSummary.STATUS_PARTIAL]
    ).count()
    total = summaries.count()
    avg_conf = summaries.aggregate(a=Avg("confidence_score"))["a"] or 0
    records = PerformanceRecord.objects.filter(assessment__module__programme=programme)
    avg_perf = None
    if records.exists():
        avg_perf = round(sum(r.percentage for r in records) / records.count(), 1)
    return {
        "students": students,
        "modules": modules.count(),
        "attendance_percent": round(present / total * 100, 1) if total else 0,
        "recognition_percent": round(float(avg_conf) * 100, 1),
        "avg_performance": avg_perf,
        "confidence_average": round(float(avg_conf) * 100, 1),
    }


def create_notification(user, title, message, ntype=Notification.TYPE_INFO, link=""):
    return Notification.objects.create(
        user=user, title=title, message=message, notification_type=ntype, link=link
    )


def sync_session_status(session):
    """Keep is_active / status / is_paused consistent."""
    if session.status == Session.STATUS_CANCELLED:
        session.is_active = False
        session.is_paused = False
    elif session.status == Session.STATUS_COMPLETED:
        session.is_active = False
        session.is_paused = False
    elif session.status == Session.STATUS_PAUSED:
        session.is_active = True
        session.is_paused = True
    elif session.status == Session.STATUS_ACTIVE:
        session.is_active = True
        session.is_paused = False
    elif session.status == Session.STATUS_UPCOMING:
        session.is_active = False
        session.is_paused = False
    session.save(update_fields=["status", "is_active", "is_paused"])


def build_ai_insights(user=None):
    insights = []

    # Low attendance students
    for profile in StudentProfile.objects.select_related("student")[:200]:
        att = student_attendance_percent(profile.student)
        if att and att < 50:
            insights.append({
                "type": "warning",
                "category": "attendance",
                "title": "Low attendance",
                "message": f"{profile.student.name} has only {att}% attendance.",
                "link": f"/students/{profile.student_id}/",
            })
        conf = student_avg_confidence(profile.student)
        if conf and conf < 40:
            insights.append({
                "type": "danger",
                "category": "confidence",
                "title": "Low recognition confidence",
                "message": f"{profile.student.name} averages {conf}% recognition confidence.",
                "link": f"/students/{profile.student_id}/",
            })

    for module in Module.objects.all()[:50]:
        stats = module_stats(module)
        if stats["attendance_percent"] and stats["attendance_percent"] < 50:
            insights.append({
                "type": "warning",
                "category": "module",
                "title": "Module needs attention",
                "message": f"{module.code} attendance is {stats['attendance_percent']}%.",
                "link": f"/modules/{module.pk}/",
            })

    for session in Session.objects.filter(is_active=False).order_by("-end_time")[:20]:
        rec = session_recognition_percent(session)
        if session.total_frames > 5 and rec < 20:
            insights.append({
                "type": "danger",
                "category": "session",
                "title": "Poor recognition quality",
                "message": f"Session #{session.id} recognition rate was {rec}%.",
                "link": f"/sessions/{session.pk}/",
            })

    if not insights:
        insights.append({
            "type": "info",
            "category": "system",
            "title": "All clear",
            "message": "No critical academic or recognition anomalies detected.",
            "link": "/dashboard/",
        })
    return insights[:30]


def leaderboard_data():
    students = list(Student.objects.select_related("profile")[:100])
    ranked = []
    for s in students:
        ranked.append({
            "student": s,
            "attendance": student_attendance_percent(s),
            "confidence": student_avg_confidence(s),
        })
    return {
        "highest_attendance": sorted(ranked, key=lambda x: x["attendance"], reverse=True)[:5],
        "lowest_attendance": sorted(ranked, key=lambda x: x["attendance"])[:5],
        "best_recognition": sorted(ranked, key=lambda x: x["confidence"], reverse=True)[:5],
        "lowest_confidence": sorted([r for r in ranked if r["confidence"] > 0], key=lambda x: x["confidence"])[:5],
        "best_modules": [
            {"module": m, **module_stats(m)} for m in Module.objects.all()[:20]
        ],
        "best_programmes": [
            {"programme": p, **programme_stats(p)} for p in Programme.objects.all()[:20]
        ],
    }
