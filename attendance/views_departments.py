"""Department management views — full CRUD in the application UI."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from attendance.forms import DepartmentForm
from attendance.models import (
    AttendanceSummary,
    Department,
    Module,
    Programme,
    Session,
    StudentProfile,
)
from attendance.services.academic import student_attendance_percent


def _department_stats(department):
    programmes = Programme.objects.filter(department=department)
    modules = Module.objects.filter(department=department)
    lecturers = (
        User.objects.filter(modules__department=department).distinct().count()
        or User.objects.filter(modules__programme__department=department).distinct().count()
    )
    students = StudentProfile.objects.filter(
        Q(department=department) | Q(programme__department=department)
    ).distinct().count()
    summaries = AttendanceSummary.objects.filter(
        Q(session__module__department=department)
        | Q(session__module__programme__department=department)
    )
    present = summaries.filter(
        status__in=[AttendanceSummary.STATUS_PRESENT, AttendanceSummary.STATUS_PARTIAL]
    ).count()
    total = summaries.count()
    return {
        "programmes": programmes.count(),
        "modules": modules.count(),
        "lecturers": lecturers,
        "students": students,
        "attendance_percent": round(present / total * 100, 1) if total else 0,
    }


@login_required
def department_list(request):
    qs = Department.objects.select_related("head_of_department").all()
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    sort = request.GET.get("sort", "name")
    allowed = {"name", "-name", "code", "-code", "created_at", "-created_at"}
    if sort not in allowed:
        sort = "name"
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(description__icontains=q))
    if status:
        qs = qs.filter(status=status)

    paginator = Paginator(qs.order_by(sort), 12)
    page = paginator.get_page(request.GET.get("page"))
    rows = [{"department": d, **_department_stats(d)} for d in page.object_list]
    return render(
        request,
        "attendance/departments/list.html",
        {
            "page_obj": page,
            "rows": rows,
            "filters": request.GET,
            "status_choices": Department.STATUS_CHOICES,
        },
    )


@login_required
def department_create(request):
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            department = form.save()
            messages.success(request, f"Department {department.code} created.")
            return redirect("department_detail", pk=department.pk)
    else:
        form = DepartmentForm()
    return render(
        request, "attendance/departments/form.html", {"form": form, "is_edit": False}
    )


@login_required
def department_detail(request, pk):
    department = get_object_or_404(
        Department.objects.select_related("head_of_department"), pk=pk
    )
    programmes = Programme.objects.filter(department=department)
    modules = Module.objects.filter(
        Q(department=department) | Q(programme__department=department)
    ).select_related("teacher", "programme").distinct()
    lecturers = User.objects.filter(modules__in=modules).distinct()
    students = StudentProfile.objects.filter(
        Q(department=department) | Q(programme__department=department)
    ).select_related("student", "programme").distinct()
    stats = _department_stats(department)
    recent_sessions = (
        Session.objects.filter(
            Q(module__department=department) | Q(module__programme__department=department)
        )
        .select_related("module", "teacher")
        .order_by("-start_time")[:8]
    )
    student_rows = [
        {
            "student": p.student,
            "profile": p,
            "attendance_percent": student_attendance_percent(p.student),
        }
        for p in students[:50]
    ]
    return render(
        request,
        "attendance/departments/detail.html",
        {
            "department": department,
            "programmes": programmes,
            "modules": modules[:30],
            "lecturers": lecturers,
            "student_rows": student_rows,
            "stats": stats,
            "recent_sessions": recent_sessions,
        },
    )


@login_required
def department_edit(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated.")
            return redirect("department_detail", pk=department.pk)
    else:
        form = DepartmentForm(instance=department)
    return render(
        request,
        "attendance/departments/form.html",
        {"form": form, "is_edit": True, "department": department},
    )


@login_required
@require_POST
def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)
    programmes = Programme.objects.filter(department=department).count()
    modules = Module.objects.filter(department=department).count()
    if programmes or modules:
        messages.error(
            request,
            f"Cannot delete {department.code}: it has {programmes} programme(s) and "
            f"{modules} module(s). Reassign or remove them first.",
        )
        return redirect("department_detail", pk=pk)
    code = department.code
    department.delete()
    messages.success(request, f"Department {code} deleted.")
    return redirect("department_list")


@login_required
@require_GET
def api_programmes_by_department(request):
    """JSON list of programmes for cascading Module / Student forms."""
    department_id = request.GET.get("department")
    qs = Programme.objects.filter(status=Programme.STATUS_ACTIVE).order_by("name")
    if department_id:
        qs = qs.filter(department_id=department_id)
    else:
        qs = qs.none()
    data = [{"id": p.id, "code": p.code, "name": p.name} for p in qs]
    return JsonResponse({"programmes": data})
