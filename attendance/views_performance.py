from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404, redirect, render

from attendance.forms import AssessmentForm, PerformanceRecordForm
from attendance.models import (
    Assessment,
    AttendanceSummary,
    Module,
    PerformanceRecord,
    Programme,
    Student,
)
from attendance.services.academic import (
    build_ai_insights,
    student_attendance_percent,
    student_avg_confidence,
    student_avg_performance,
)


@login_required
def performance_dashboard(request):
    records = PerformanceRecord.objects.select_related(
        "student", "assessment", "assessment__module", "assessment__module__programme"
    )
    module_id = request.GET.get("module")
    programme_id = request.GET.get("programme")
    if module_id:
        records = records.filter(assessment__module_id=module_id)
    if programme_id:
        records = records.filter(assessment__module__programme_id=programme_id)

    paginator = Paginator(records.order_by("-recorded_at"), 20)
    page = paginator.get_page(request.GET.get("page"))

    avg = None
    all_recs = list(records[:500])
    if all_recs:
        avg = round(sum(r.percentage for r in all_recs) / len(all_recs), 1)
        pass_rate = round(sum(1 for r in all_recs if r.passed) / len(all_recs) * 100, 1)
    else:
        pass_rate = None

    return render(
        request,
        "attendance/performance/dashboard.html",
        {
            "page_obj": page,
            "modules": Module.objects.all(),
            "programmes": Programme.objects.all(),
            "filters": request.GET,
            "avg_performance": avg,
            "pass_rate": pass_rate,
            "assessment_count": Assessment.objects.count(),
            "insights": [i for i in build_ai_insights() if i["category"] in ("attendance", "module")][:5],
        },
    )


@login_required
def assessment_list(request):
    qs = Assessment.objects.select_related("module", "teacher").all()
    module_id = request.GET.get("module")
    if module_id:
        qs = qs.filter(module_id=module_id)
    paginator = Paginator(qs.order_by("-created_at"), 15)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "attendance/performance/assessments.html",
        {"page_obj": page, "modules": Module.objects.all(), "filters": request.GET},
    )


@login_required
def assessment_create(request):
    if request.method == "POST":
        form = AssessmentForm(request.POST, user=request.user)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.teacher = request.user
            assessment.save()
            messages.success(request, "Assessment created.")
            return redirect("assessment_detail", pk=assessment.pk)
    else:
        form = AssessmentForm(user=request.user)
    return render(request, "attendance/performance/assessment_form.html", {"form": form})


@login_required
def assessment_detail(request, pk):
    assessment = get_object_or_404(
        Assessment.objects.select_related("module", "teacher"), pk=pk
    )
    records = PerformanceRecord.objects.filter(assessment=assessment).select_related("student")
    if request.method == "POST":
        form = PerformanceRecordForm(request.POST)
        if form.is_valid():
            rec = form.save(commit=False)
            rec.assessment = assessment
            rec.recorded_by = request.user
            rec.save()
            # Update student average_grade
            avg = student_avg_performance(rec.student)
            if avg is not None and hasattr(rec.student, "profile"):
                rec.student.profile.average_grade = avg
                rec.student.profile.save(update_fields=["average_grade"])
            messages.success(request, "Marks recorded.")
            return redirect("assessment_detail", pk=pk)
    else:
        form = PerformanceRecordForm()
        form.fields["student"].queryset = Student.objects.filter(
            module_enrollments__module=assessment.module
        ).distinct()
        if not form.fields["student"].queryset.exists():
            form.fields["student"].queryset = Student.objects.all()

    avg = None
    if records.exists():
        avg = round(sum(r.percentage for r in records) / records.count(), 1)

    return render(
        request,
        "attendance/performance/assessment_detail.html",
        {"assessment": assessment, "records": records, "form": form, "avg": avg},
    )


@login_required
def student_performance(request, pk):
    student = get_object_or_404(Student, pk=pk)
    records = PerformanceRecord.objects.filter(student=student).select_related(
        "assessment", "assessment__module"
    )
    summaries = AttendanceSummary.objects.filter(student=student).select_related("session")
    att = student_attendance_percent(student)
    conf = student_avg_confidence(student)
    perf = student_avg_performance(student)
    return render(
        request,
        "attendance/performance/student.html",
        {
            "student": student,
            "records": records,
            "summaries": summaries[:20],
            "attendance_percent": att,
            "confidence_percent": conf,
            "performance_avg": perf,
            "correlation": {
                "attendance": att,
                "performance": perf or 0,
                "confidence": conf,
            },
        },
    )
