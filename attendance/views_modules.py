from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from attendance.forms import ModuleForm
from attendance.models import AttendanceSummary, Department, Module, ModuleEnrollment, Programme, Session, Student
from attendance.services.academic import module_stats, student_attendance_percent


def _module_queryset(request):
    qs = Module.objects.select_related("department", "teacher", "programme").annotate(
        student_count=Count("enrollments", distinct=True)
    )
    q = request.GET.get("q", "").strip()
    department = request.GET.get("department", "")
    programme = request.GET.get("programme", "")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
    if department:
        qs = qs.filter(department_id=department)
    if programme:
        qs = qs.filter(programme_id=programme)
    return qs.order_by("name")


@login_required
def module_list(request):
    queryset = _module_queryset(request)
    paginator = Paginator(queryset, 12)
    page = paginator.get_page(request.GET.get("page"))
    rows = []
    for module in page.object_list:
        stats = module_stats(module)
        rows.append({"module": module, "students": module.student_count, **stats})
    return render(
        request,
        "attendance/modules/list.html",
        {
            "page_obj": page,
            "rows": rows,
            "departments": Department.objects.all(),
            "programmes": Programme.objects.all(),
            "filters": request.GET,
        },
    )


@login_required
def module_create(request):
    if request.method == "POST":
        form = ModuleForm(request.POST, user=request.user)
        if form.is_valid():
            module = form.save(commit=False)
            if not module.teacher_id:
                module.teacher = request.user
            module.save()
            messages.success(request, f"Module {module.code} created.")
            return redirect("module_detail", pk=module.pk)
    else:
        form = ModuleForm(user=request.user, initial={"teacher": request.user})
    return render(request, "attendance/modules/form.html", {"form": form, "is_edit": False})


@login_required
def module_detail(request, pk):
    module = get_object_or_404(
        Module.objects.select_related("department", "teacher", "programme"), pk=pk
    )
    enrollments = ModuleEnrollment.objects.filter(module=module).select_related(
        "student", "student__profile"
    )
    sessions = Session.objects.filter(module=module).order_by("-start_time")[:10]
    student_rows = [
        {
            "student": e.student,
            "profile": getattr(e.student, "profile", None),
            "attendance_percent": student_attendance_percent(e.student),
        }
        for e in enrollments
    ]
    stats = module_stats(module)
    from attendance.models import PerformanceRecord

    records = list(
        PerformanceRecord.objects.filter(assessment__module=module).select_related("student")
    )
    ranked = sorted(records, key=lambda r: r.percentage, reverse=True)
    performers = {
        "highest": ranked[0] if ranked else None,
        "lowest": ranked[-1] if ranked else None,
    }
    return render(
        request,
        "attendance/modules/detail.html",
        {
            "module": module,
            "student_rows": student_rows,
            "sessions": sessions,
            "sessions_count": Session.objects.filter(module=module).count(),
            "enrollment_count": enrollments.count(),
            "stats": stats,
            "avg_confidence": stats["recognition_percent"],
            "performers": performers,
        },
    )


@login_required
def module_edit(request, pk):
    module = get_object_or_404(Module, pk=pk)
    if request.method == "POST":
        form = ModuleForm(request.POST, instance=module, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Module updated.")
            return redirect("module_detail", pk=module.pk)
    else:
        form = ModuleForm(instance=module, user=request.user)
    return render(
        request, "attendance/modules/form.html", {"form": form, "is_edit": True, "module": module}
    )


@login_required
@require_POST
def module_delete(request, pk):
    module = get_object_or_404(Module, pk=pk)
    code = module.code
    module.delete()
    messages.success(request, f"Module {code} deleted.")
    return redirect("module_list")


@login_required
def module_enroll(request, pk):
    module = get_object_or_404(Module, pk=pk)
    enrolled_ids = set(
        ModuleEnrollment.objects.filter(module=module).values_list("student_id", flat=True)
    )
    available = Student.objects.exclude(pk__in=enrolled_ids).order_by("name")
    if request.method == "POST":
        student_ids = request.POST.getlist("students")
        added = 0
        for sid in student_ids:
            _, created = ModuleEnrollment.objects.get_or_create(student_id=sid, module=module)
            if created:
                added += 1
        messages.success(request, f"{added} student(s) enrolled in {module.code}.")
        return redirect("module_detail", pk=module.pk)
    return render(
        request,
        "attendance/modules/enroll.html",
        {"module": module, "available_students": available},
    )


@login_required
@require_POST
def module_unenroll(request, pk, student_id):
    module = get_object_or_404(Module, pk=pk)
    ModuleEnrollment.objects.filter(module=module, student_id=student_id).delete()
    messages.success(request, "Student removed from module.")
    return redirect("module_detail", pk=pk)


# Backwards-compatible aliases for old URL names during transition
course_list = module_list
course_create = module_create
course_detail = module_detail
course_edit = module_edit
course_delete = module_delete
course_enroll = module_enroll
course_unenroll = module_unenroll
