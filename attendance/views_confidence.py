from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import render

from attendance.models import AttendanceSummary, Module, Programme, Session, Student
from attendance.services.academic import (
    build_ai_insights,
    student_avg_confidence,
)


@login_required
def confidence_dashboard(request):
    summaries = AttendanceSummary.objects.select_related("student", "session", "session__module")
    avg = summaries.aggregate(a=Avg("confidence_score"))["a"] or 0
    avg_pct = round(float(avg) * 100, 1)

    buckets = {"0-40": 0, "40-75": 0, "75-100": 0}
    for s in summaries.iterator():
        pct = s.confidence_score * 100
        if pct < 40:
            buckets["0-40"] += 1
        elif pct < 75:
            buckets["40-75"] += 1
        else:
            buckets["75-100"] += 1

    # Detection ratio / time coverage / recency are components of stored confidence;
    # expose approximate breakdown from recent sessions
    recent = list(summaries.order_by("-session__end_time")[:50])
    student_history = []
    for student in Student.objects.all()[:30]:
        conf = student_avg_confidence(student)
        if conf:
            student_history.append({"student": student, "confidence": conf})
    student_history.sort(key=lambda x: x["confidence"])

    module_conf = []
    for module in Module.objects.all()[:15]:
        a = AttendanceSummary.objects.filter(session__module=module).aggregate(
            a=Avg("confidence_score")
        )["a"]
        if a is not None:
            module_conf.append({"module": module, "confidence": round(float(a) * 100, 1)})

    programme_conf = []
    for programme in Programme.objects.all()[:15]:
        a = AttendanceSummary.objects.filter(session__module__programme=programme).aggregate(
            a=Avg("confidence_score")
        )["a"]
        if a is not None:
            programme_conf.append(
                {"programme": programme, "confidence": round(float(a) * 100, 1)}
            )

    session_conf = []
    for session in Session.objects.filter(is_active=False).order_by("-end_time")[:15]:
        a = AttendanceSummary.objects.filter(session=session).aggregate(a=Avg("confidence_score"))["a"]
        session_conf.append(
            {
                "session": session,
                "confidence": round(float(a or 0) * 100, 1),
                "frames": session.total_frames,
            }
        )

    insights = [i for i in build_ai_insights() if i["category"] in ("confidence", "session", "system")]

    low_alerts = [h for h in student_history if h["confidence"] < 40][:10]
    failures = [s for s in session_conf if s["confidence"] < 30 and s["frames"] > 3]

    chart_data = {
        "distribution": {"labels": list(buckets.keys()), "values": list(buckets.values())},
        "timeline": {
            "labels": [f"#{s['session'].id}" for s in reversed(session_conf)],
            "values": [s["confidence"] for s in reversed(session_conf)],
        },
    }

    return render(
        request,
        "attendance/confidence/dashboard.html",
        {
            "overall_confidence": avg_pct,
            "detection_ratio": round(buckets["75-100"] / max(sum(buckets.values()), 1) * 100, 1),
            "time_coverage": round(buckets["40-75"] / max(sum(buckets.values()), 1) * 100, 1),
            "recency_score": round(avg_pct * 0.2, 1),
            "buckets": buckets,
            "student_history": student_history[:15],
            "module_conf": module_conf,
            "programme_conf": programme_conf,
            "session_conf": session_conf,
            "insights": insights,
            "low_alerts": low_alerts,
            "failures": failures,
            "chart_data": chart_data,
            "recommendations": insights[:8],
        },
    )
