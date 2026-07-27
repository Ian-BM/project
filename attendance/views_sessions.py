import csv
import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from attendance.forms import SessionForm
from attendance.models import (
    AttendanceSummary,
    Detection,
    Module,
    Notification,
    Session,
    UnknownFace,
)
from attendance.services.academic import (
    create_notification,
    session_attendance_percent,
    session_avg_confidence,
    session_recognition_percent,
    sync_session_status,
)
from attendance.views import _compute_summary_for_session, _active_session


def _session_queryset(request):
    qs = Session.objects.select_related("teacher", "module", "module__programme")
    if not request.user.is_superuser:
        qs = qs.filter(teacher=request.user)
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    module = request.GET.get("module", "")
    programme = request.GET.get("programme", "")
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(room__icontains=q)
            | Q(module__code__icontains=q)
            | Q(module__name__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)
    if module:
        qs = qs.filter(module_id=module)
    if programme:
        qs = qs.filter(module__programme_id=programme)
    sort = request.GET.get("sort", "-start_time")
    allowed = {"start_time", "-start_time", "date", "-date", "status", "-status", "name", "-name"}
    if sort not in allowed:
        sort = "-start_time"
    return qs.order_by(sort)


@login_required
def session_list(request):
    queryset = _session_queryset(request)
    paginator = Paginator(queryset, 15)
    page = paginator.get_page(request.GET.get("page"))
    rows = []
    for s in page.object_list:
        duration = s.duration_seconds
        hours = int(duration // 3600)
        mins = int((duration % 3600) // 60)
        rows.append(
            {
                "session": s,
                "attendance_percent": session_attendance_percent(s),
                "recognition_percent": session_recognition_percent(s),
                "confidence_percent": session_avg_confidence(s),
                "duration": f"{hours:02d}:{mins:02d}",
                "programme": s.programme,
            }
        )
    return render(
        request,
        "attendance/sessions/list.html",
        {
            "page_obj": page,
            "rows": rows,
            "modules": Module.objects.all(),
            "filters": request.GET,
            "status_choices": Session.STATUS_CHOICES,
            "counts": {
                "upcoming": Session.objects.filter(status=Session.STATUS_UPCOMING).count(),
                "active": Session.objects.filter(status=Session.STATUS_ACTIVE).count(),
                "completed": Session.objects.filter(status=Session.STATUS_COMPLETED).count(),
                "cancelled": Session.objects.filter(status=Session.STATUS_CANCELLED).count(),
            },
        },
    )


@login_required
def session_create(request):
    if request.method == "POST":
        form = SessionForm(request.POST, user=request.user)
        if form.is_valid():
            session = form.save(commit=False)
            session.teacher = request.user
            if not session.name and session.module:
                session.name = f"{session.module.code} Session"
            if session.status == Session.STATUS_UPCOMING:
                session.is_active = False
            elif session.status == Session.STATUS_ACTIVE:
                session.is_active = True
                session.start_time = timezone.now()
            session.save()
            messages.success(request, "Session created.")
            return redirect("session_detail", pk=session.pk)
    else:
        form = SessionForm(
            user=request.user,
            initial={
                "date": timezone.now().date(),
                "start_time": timezone.now(),
                "status": Session.STATUS_UPCOMING,
            },
        )
    return render(request, "attendance/sessions/form.html", {"form": form, "is_edit": False})


@login_required
def session_detail(request, pk):
    session = get_object_or_404(
        Session.objects.select_related("teacher", "module", "module__programme"), pk=pk
    )
    summaries = AttendanceSummary.objects.filter(session=session).select_related("student")
    detections = Detection.objects.filter(session=session).select_related("student").order_by("timestamp")
    unknown = UnknownFace.objects.filter(session=session)[:50]
    timeline = [
        {"time": d.timestamp, "student": d.student.name, "type": "recognition"}
        for d in detections[:100]
    ]
    return render(
        request,
        "attendance/sessions/detail.html",
        {
            "session": session,
            "summaries": summaries,
            "detections": detections[:50],
            "unknown_faces": unknown,
            "timeline": timeline,
            "attendance_percent": session_attendance_percent(session),
            "recognition_percent": session_recognition_percent(session),
            "confidence_percent": session_avg_confidence(session),
            "avg_confidence_chart": [
                float(v) for v in summaries.values_list("confidence_score", flat=True)
            ],
            "status_counts": {
                "Present": summaries.filter(status="Present").count(),
                "Partial": summaries.filter(status="Partial").count(),
                "Absent": summaries.filter(status="Absent").count(),
            },
        },
    )


@login_required
def session_live(request, pk):
    session = get_object_or_404(Session, pk=pk)
    return redirect(f"/?session_id={session.pk}")


@login_required
@require_POST
def session_start(request, pk):
    session = get_object_or_404(Session, pk=pk, teacher=request.user)
    # End any other active session for this teacher
    for other in Session.objects.filter(teacher=request.user, is_active=True).exclude(pk=pk):
        other.status = Session.STATUS_COMPLETED
        other.is_active = False
        other.end_time = timezone.now()
        other.save()
        _compute_summary_for_session(other)

    session.status = Session.STATUS_ACTIVE
    session.is_active = True
    session.is_paused = False
    if not session.start_time:
        session.start_time = timezone.now()
    session.save()
    create_notification(
        request.user,
        "Session Started",
        f"Session #{session.id} is now live.",
        Notification.TYPE_SUCCESS,
        f"/sessions/{session.pk}/",
    )
    messages.success(request, "Session started.")
    return redirect("index")


@login_required
@require_POST
def session_pause(request, pk):
    session = get_object_or_404(Session, pk=pk, teacher=request.user)
    session.status = Session.STATUS_PAUSED
    session.is_paused = True
    session.is_active = True
    session.save(update_fields=["status", "is_paused", "is_active"])
    messages.info(request, "Session paused.")
    return redirect("session_detail", pk=pk)


@login_required
@require_POST
def session_resume(request, pk):
    session = get_object_or_404(Session, pk=pk, teacher=request.user)
    session.status = Session.STATUS_ACTIVE
    session.is_paused = False
    session.is_active = True
    session.save(update_fields=["status", "is_paused", "is_active"])
    messages.success(request, "Session resumed.")
    return redirect("index")


@login_required
@require_POST
def session_end(request, pk):
    session = get_object_or_404(Session, pk=pk, teacher=request.user)
    session.status = Session.STATUS_COMPLETED
    session.is_active = False
    session.is_paused = False
    session.end_time = timezone.now()
    session.save()
    _compute_summary_for_session(session)
    create_notification(
        request.user,
        "Session Completed",
        f"Session #{session.id} ended. Attendance summary computed.",
        Notification.TYPE_SUCCESS,
        f"/sessions/{session.pk}/",
    )
    messages.success(request, "Session ended and attendance computed.")
    return redirect("session_detail", pk=pk)


@login_required
@require_POST
def session_cancel(request, pk):
    session = get_object_or_404(Session, pk=pk, teacher=request.user)
    session.status = Session.STATUS_CANCELLED
    session.is_active = False
    session.is_paused = False
    session.save(update_fields=["status", "is_active", "is_paused"])
    messages.warning(request, "Session cancelled.")
    return redirect("session_list")


@login_required
def session_export(request, pk):
    session = get_object_or_404(Session, pk=pk)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="session_{pk}.csv"'
    writer = csv.writer(response)
    writer.writerow(["Student", "Status", "Confidence", "Detections"])
    for summary in AttendanceSummary.objects.filter(session=session).select_related("student"):
        det_count = Detection.objects.filter(session=session, student=summary.student).count()
        writer.writerow(
            [summary.student.name, summary.status, summary.confidence_score, det_count]
        )
    return response


@login_required
def session_print(request, pk):
    session = get_object_or_404(
        Session.objects.select_related("teacher", "module", "module__programme"), pk=pk
    )
    summaries = AttendanceSummary.objects.filter(session=session).select_related("student")
    return render(
        request,
        "attendance/sessions/print.html",
        {
            "session": session,
            "summaries": summaries,
            "attendance_percent": session_attendance_percent(session),
            "confidence_percent": session_avg_confidence(session),
        },
    )
