import csv
import json
from datetime import datetime, timedelta
from io import BytesIO, StringIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from attendance.models import (
    AttendanceSummary,
    Detection,
    Module,
    PerformanceRecord,
    Programme,
    ReportLog,
    Session,
    Student,
)
from attendance.services.academic import (
    create_notification,
    session_attendance_percent,
    session_avg_confidence,
    student_attendance_percent,
    student_avg_confidence,
)


def _apply_filters(qs, request, student_field="student", session_prefix="session"):
    programme = request.GET.get("programme")
    module = request.GET.get("module")
    teacher = request.GET.get("teacher")
    student = request.GET.get("student")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    semester = request.GET.get("semester")
    academic_year = request.GET.get("academic_year")

    if programme:
        qs = qs.filter(**{f"{session_prefix}__module__programme_id": programme})
    if module:
        qs = qs.filter(**{f"{session_prefix}__module_id": module})
    if teacher:
        qs = qs.filter(**{f"{session_prefix}__teacher_id": teacher})
    if student:
        qs = qs.filter(**{f"{student_field}_id": student})
    if date_from:
        qs = qs.filter(**{f"{session_prefix}__date__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{session_prefix}__date__lte": date_to})
    if semester:
        qs = qs.filter(**{f"{session_prefix}__module__semester__icontains": semester})
    if academic_year:
        qs = qs.filter(**{f"{session_prefix}__module__academic_year__icontains": academic_year})
    return qs


def _filter_context(request):
    return {
        "programmes": Programme.objects.all(),
        "modules": Module.objects.all(),
        "teachers": User.objects.filter(sessions__isnull=False).distinct(),
        "students": Student.objects.all()[:200],
        "filters": request.GET,
    }


@login_required
def reports_hub(request):
    return render(
        request,
        "attendance/reports/hub.html",
        {
            **_filter_context(request),
            "recent_reports": ReportLog.objects.filter(generated_by=request.user)[:10],
            "report_types": ReportLog.REPORT_CHOICES,
        },
    )


@login_required
def report_view(request, report_type):
    valid = dict(ReportLog.REPORT_CHOICES)
    if report_type not in valid:
        messages.error(request, "Unknown report type.")
        return redirect("reports_hub")

    rows = []
    title = valid[report_type]

    if report_type == "attendance":
        qs = _apply_filters(
            AttendanceSummary.objects.select_related("student", "session", "session__module"),
            request,
        )
        for s in qs.order_by("-session__date")[:500]:
            rows.append(
                {
                    "Student": s.student.name,
                    "Session": s.session_id,
                    "Module": s.session.module.code if s.session.module else "—",
                    "Date": s.session.date,
                    "Status": s.status,
                    "Confidence": round(s.confidence_score * 100, 1),
                }
            )
    elif report_type == "session":
        qs = Session.objects.select_related("module", "teacher")
        if request.GET.get("module"):
            qs = qs.filter(module_id=request.GET["module"])
        if request.GET.get("teacher"):
            qs = qs.filter(teacher_id=request.GET["teacher"])
        for s in qs.order_by("-start_time")[:200]:
            rows.append(
                {
                    "Session": s.id,
                    "Name": s.name or f"Session {s.id}",
                    "Module": s.module.code if s.module else "—",
                    "Teacher": s.teacher.get_full_name() or s.teacher.username,
                    "Date": s.date,
                    "Status": s.get_status_display(),
                    "Attendance %": session_attendance_percent(s),
                    "Confidence %": session_avg_confidence(s),
                    "Frames": s.total_frames,
                }
            )
    elif report_type == "student":
        for student in Student.objects.select_related("profile")[:200]:
            rows.append(
                {
                    "Student": student.name,
                    "Registration": getattr(getattr(student, "profile", None), "registration_number", ""),
                    "Programme": getattr(
                        getattr(getattr(student, "profile", None), "programme", None), "code", "—"
                    ),
                    "Attendance %": student_attendance_percent(student),
                    "Confidence %": student_avg_confidence(student),
                    "Risk": getattr(getattr(student, "profile", None), "risk_level", "—"),
                }
            )
    elif report_type == "module":
        for module in Module.objects.select_related("programme", "teacher"):
            summaries = AttendanceSummary.objects.filter(session__module=module)
            avg = summaries.aggregate(a=Avg("confidence_score"))["a"] or 0
            present = summaries.filter(status__in=["Present", "Partial"]).count()
            total = summaries.count() or 1
            rows.append(
                {
                    "Code": module.code,
                    "Name": module.name,
                    "Programme": module.programme.code if module.programme else "—",
                    "Teacher": (module.teacher.get_full_name() or module.teacher.username)
                    if module.teacher
                    else "—",
                    "Attendance %": round(present / total * 100, 1),
                    "Confidence %": round(float(avg) * 100, 1),
                }
            )
    elif report_type == "programme":
        for programme in Programme.objects.all():
            summaries = AttendanceSummary.objects.filter(session__module__programme=programme)
            avg = summaries.aggregate(a=Avg("confidence_score"))["a"] or 0
            present = summaries.filter(status__in=["Present", "Partial"]).count()
            total = summaries.count() or 1
            rows.append(
                {
                    "Code": programme.code,
                    "Name": programme.name,
                    "Students": programme.students.count(),
                    "Modules": programme.modules.count(),
                    "Attendance %": round(present / total * 100, 1),
                    "Confidence %": round(float(avg) * 100, 1),
                }
            )
    elif report_type == "teacher":
        for teacher in User.objects.filter(sessions__isnull=False).distinct():
            sessions = Session.objects.filter(teacher=teacher)
            summaries = AttendanceSummary.objects.filter(session__teacher=teacher)
            avg = summaries.aggregate(a=Avg("confidence_score"))["a"] or 0
            rows.append(
                {
                    "Teacher": teacher.get_full_name() or teacher.username,
                    "Sessions": sessions.count(),
                    "Modules": Module.objects.filter(teacher=teacher).count(),
                    "Avg Confidence %": round(float(avg) * 100, 1),
                }
            )
    elif report_type == "recognition":
        for d in Detection.objects.select_related("student", "session").order_by("-timestamp")[:500]:
            rows.append(
                {
                    "Student": d.student.name,
                    "Session": d.session_id,
                    "Timestamp": d.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
    elif report_type == "confidence":
        qs = _apply_filters(
            AttendanceSummary.objects.select_related("student", "session"), request
        )
        for s in qs.order_by("-confidence_score")[:500]:
            rows.append(
                {
                    "Student": s.student.name,
                    "Session": s.session_id,
                    "Confidence %": round(s.confidence_score * 100, 1),
                    "Status": s.status,
                }
            )

    export = request.GET.get("export")
    if export == "csv":
        return _export_csv(title, rows)
    if export == "excel":
        return _export_excel(title, rows)

    is_print = request.GET.get("print") == "1" or getattr(request, "_report_print", False)
    if not is_print:
        ReportLog.objects.create(
            report_type=report_type,
            generated_by=request.user,
            filters=dict(request.GET.items()),
        )
        create_notification(
            request.user,
            "Report Generated",
            f"{title} was generated.",
            link=f"/reports/{report_type}/",
        )

    template = "attendance/reports/print.html" if is_print else "attendance/reports/view.html"
    return render(
        request,
        template,
        {
            "title": title,
            "report_type": report_type,
            "rows": rows,
            "columns": list(rows[0].keys()) if rows else [],
            **_filter_context(request),
        },
    )


def _export_csv(title, rows):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{title.replace(" ", "_").lower()}.csv"'
    writer = csv.writer(response)
    if rows:
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow(row.values())
    return response


def _export_excel(title, rows):
    # Lightweight TSV that opens in Excel without extra dependencies
    response = HttpResponse(content_type="application/vnd.ms-excel")
    response["Content-Disposition"] = f'attachment; filename="{title.replace(" ", "_").lower()}.xls"'
    if rows:
        headers = "\t".join(str(k) for k in rows[0].keys())
        lines = [headers]
        for row in rows:
            lines.append("\t".join(str(v) for v in row.values()))
        response.write("\n".join(lines))
    return response


@login_required
def report_print(request, report_type):
    """Print-friendly report (browser Print / Save as PDF)."""
    request._report_print = True
    return report_view(request, report_type)
