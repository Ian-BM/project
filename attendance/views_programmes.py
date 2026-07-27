from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from attendance.forms import ProgrammeForm
from attendance.models import Department, Module, Programme, ProgrammeEnrollment, Student, StudentProfile
from attendance.services.academic import programme_stats, student_attendance_percent


@login_required
def programme_list(request):
    qs = Programme.objects.select_related("department").all()
    q = request.GET.get("q", "").strip()
    department = request.GET.get("department", "")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
    if department:
        qs = qs.filter(department_id=department)
    paginator = Paginator(qs.order_by("name"), 12)
    page = paginator.get_page(request.GET.get("page"))
    rows = [{"programme": p, **programme_stats(p)} for p in page.object_list]
    return render(
        request,
        "attendance/programmes/list.html",
        {
            "page_obj": page,
            "rows": rows,
            "departments": Department.objects.all(),
            "filters": request.GET,
        },
    )


@login_required
def programme_create(request):
    if request.method == "POST":
        form = ProgrammeForm(request.POST)
        if form.is_valid():
            programme = form.save()
            messages.success(request, f"Programme {programme.code} created.")
            return redirect("programme_detail", pk=programme.pk)
    else:
        form = ProgrammeForm()
    return render(request, "attendance/programmes/form.html", {"form": form, "is_edit": False})


@login_required
def programme_detail(request, pk):
    programme = get_object_or_404(Programme.objects.select_related("department"), pk=pk)
    modules = Module.objects.filter(programme=programme).select_related("teacher")
    students = StudentProfile.objects.filter(programme=programme).select_related("student")
    stats = programme_stats(programme)
    student_rows = [
        {
            "student": p.student,
            "profile": p,
            "attendance_percent": student_attendance_percent(p.student),
        }
        for p in students
    ]
    return render(
        request,
        "attendance/programmes/detail.html",
        {
            "programme": programme,
            "modules": modules,
            "student_rows": student_rows,
            "stats": stats,
        },
    )


@login_required
def programme_edit(request, pk):
    programme = get_object_or_404(Programme, pk=pk)
    if request.method == "POST":
        form = ProgrammeForm(request.POST, instance=programme)
        if form.is_valid():
            form.save()
            messages.success(request, "Programme updated.")
            return redirect("programme_detail", pk=programme.pk)
    else:
        form = ProgrammeForm(instance=programme)
    return render(
        request,
        "attendance/programmes/form.html",
        {"form": form, "is_edit": True, "programme": programme},
    )


@login_required
@require_POST
def programme_delete(request, pk):
    programme = get_object_or_404(Programme, pk=pk)
    code = programme.code
    programme.delete()
    messages.success(request, f"Programme {code} deleted.")
    return redirect("programme_list")


@login_required
def programme_enroll(request, pk):
    programme = get_object_or_404(Programme, pk=pk)
    enrolled_ids = set(
        ProgrammeEnrollment.objects.filter(programme=programme).values_list("student_id", flat=True)
    )
    # Also students with profile.programme set
    profile_ids = set(
        StudentProfile.objects.filter(programme=programme).values_list("student_id", flat=True)
    )
    enrolled_ids |= profile_ids
    available = Student.objects.exclude(pk__in=enrolled_ids).order_by("name")
    if request.method == "POST":
        student_ids = request.POST.getlist("students")
        added = 0
        for sid in student_ids:
            _, created = ProgrammeEnrollment.objects.get_or_create(
                student_id=sid, programme=programme
            )
            StudentProfile.objects.filter(student_id=sid).update(programme=programme)
            if created:
                added += 1
        messages.success(request, f"{added} student(s) enrolled in {programme.code}.")
        return redirect("programme_detail", pk=programme.pk)
    return render(
        request,
        "attendance/programmes/enroll.html",
        {"programme": programme, "available_students": available},
    )
