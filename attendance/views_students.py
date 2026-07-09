import csv
import json
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from attendance.forms import StudentEditForm, StudentForm, StudentImageForm
from attendance.models import (
    AttendanceSummary,
    Course,
    Department,
    Detection,
    Enrollment,
    Student,
    StudentImage,
    StudentProfile,
)
from attendance.services.dashboard_stats import student_attendance_percent
from attendance.services.dataset import copy_image_to_dataset, encoding_update_instructions, validate_student_image


def _student_list_queryset(request):
    qs = Student.objects.select_related("profile", "profile__department").prefetch_related("enrollments__course")
    q = request.GET.get("q", "").strip()
    department = request.GET.get("department", "")
    course = request.GET.get("course", "")
    status = request.GET.get("status", "")
    risk = request.GET.get("risk", "")

    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(profile__registration_number__icontains=q)
            | Q(profile__email__icontains=q)
        )
    if department:
        qs = qs.filter(profile__department_id=department)
    if course:
        qs = qs.filter(enrollments__course_id=course)
    if status:
        qs = qs.filter(profile__status=status)
    if risk:
        qs = qs.filter(profile__risk_level=risk)
    return qs.distinct().order_by("name")


def _student_row(student):
    profile = getattr(student, "profile", None)
    enrollment = student.enrollments.select_related("course").first()
    return {
        "student": student,
        "profile": profile,
        "course": enrollment.course if enrollment else None,
        "attendance_percent": student_attendance_percent(student),
        "recognition_status": profile.recognition_status if profile else "pending",
        "risk_level": profile.risk_level if profile else "low",
        "grade": profile.average_grade if profile else None,
        "registration": profile.registration_number if profile else "—",
        "department": profile.department if profile else None,
        "photo": student.images.filter(is_primary=True).first() or student.images.first(),
    }


@login_required
def student_list(request):
    queryset = _student_list_queryset(request)
    paginator = Paginator(queryset, 12)
    page = paginator.get_page(request.GET.get("page"))

    rows = [_student_row(s) for s in page.object_list]

    return render(
        request,
        "attendance/students/list.html",
        {
            "page_obj": page,
            "rows": rows,
            "departments": Department.objects.all(),
            "courses": Course.objects.all(),
            "filters": request.GET,
            "total_count": queryset.count(),
        },
    )


@login_required
def student_create(request):
    encoding_msg = request.session.pop("encoding_instructions", None)
    if request.method == "POST":
        form = StudentForm(request.POST, request.FILES)
        photos = request.FILES.getlist("photos")
        if form.is_valid():
            name = form.cleaned_data["name"]
            student = Student.objects.create(name=name)
            profile = StudentProfile.objects.create(
                student=student,
                registration_number=form.cleaned_data["registration_number"],
                email=form.cleaned_data.get("email", ""),
                phone=form.cleaned_data.get("phone", ""),
                department=form.cleaned_data.get("department"),
                status=form.cleaned_data["status"],
                teacher=request.user,
                recognition_status=StudentProfile.RECOG_PENDING,
            )
            course = form.cleaned_data.get("course")
            if course:
                Enrollment.objects.get_or_create(student=student, course=course)

            saved_count = 0
            for i, photo in enumerate(photos):
                try:
                    validate_student_image(photo)
                    img = StudentImage.objects.create(
                        student=student, image=photo, is_primary=(i == 0)
                    )
                    copy_image_to_dataset(name, img.image.path, Path(img.image.name).name)
                    saved_count += 1
                except Exception as exc:
                    messages.warning(request, f"Could not save image {photo.name}: {exc}")

            if saved_count:
                profile.recognition_status = StudentProfile.RECOG_PENDING
                profile.save(update_fields=["recognition_status"])
                request.session["encoding_instructions"] = encoding_update_instructions()

            messages.success(request, f"Student {name} created successfully.")
            return redirect("student_detail", pk=student.pk)
    else:
        form = StudentForm()

    return render(
        request,
        "attendance/students/form.html",
        {"form": form, "is_edit": False, "encoding_msg": encoding_msg},
    )


@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student.objects.prefetch_related("images", "enrollments__course"), pk=pk)
    profile = getattr(student, "profile", None)
    if not profile:
        profile = StudentProfile.objects.create(
            student=student,
            registration_number=f"REG-{student.pk:04d}",
            teacher=request.user,
        )

    summaries = AttendanceSummary.objects.filter(student=student).select_related("session").order_by("-session__end_time")[:20]
    detections = Detection.objects.filter(student=student).select_related("session").order_by("-timestamp")[:20]
    enrollments = Enrollment.objects.filter(student=student).select_related("course")

    encoding_msg = request.session.pop("encoding_instructions", None)

    return render(
        request,
        "attendance/students/detail.html",
        {
            "student": student,
            "profile": profile,
            "summaries": summaries,
            "detections": detections,
            "enrollments": enrollments,
            "attendance_percent": student_attendance_percent(student),
            "encoding_msg": encoding_msg,
        },
    )


@login_required
def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    profile = get_object_or_404(StudentProfile, student=student)

    if request.method == "POST":
        form = StudentEditForm(request.POST, instance=profile)
        if form.is_valid():
            new_name = form.cleaned_data["name"].strip()
            if new_name.lower() != student.name.lower():
                if Student.objects.filter(name__iexact=new_name).exclude(pk=student.pk).exists():
                    form.add_error("name", "A student with this name already exists.")
                else:
                    student.name = new_name
                    student.save(update_fields=["name"])
            form.save()
            messages.success(request, "Student updated successfully.")
            return redirect("student_detail", pk=student.pk)
    else:
        form = StudentEditForm(instance=profile)

    return render(
        request,
        "attendance/students/form_edit.html",
        {"form": form, "student": student, "profile": profile},
    )


@login_required
@require_POST
def student_upload_images(request, pk):
    student = get_object_or_404(Student, pk=pk)
    photos = request.FILES.getlist("photos")
    saved = 0
    for photo in photos:
        try:
            validate_student_image(photo)
            img = StudentImage.objects.create(student=student, image=photo)
            copy_image_to_dataset(student.name, img.image.path, Path(img.image.name).name)
            saved += 1
        except Exception as exc:
            messages.warning(request, str(exc))

    if saved:
        if hasattr(student, "profile"):
            student.profile.recognition_status = StudentProfile.RECOG_PENDING
            student.profile.save(update_fields=["recognition_status"])
        request.session["encoding_instructions"] = encoding_update_instructions()
        messages.success(request, f"{saved} image(s) uploaded. Run face encoding to update recognition.")
    return redirect("student_detail", pk=pk)


@login_required
def student_export(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="students.csv"'
    writer = csv.writer(response)
    writer.writerow(["Name", "Registration", "Email", "Department", "Course", "Attendance %", "Risk", "Status"])
    for student in Student.objects.select_related("profile").prefetch_related("enrollments__course"):
        profile = getattr(student, "profile", None)
        course = student.enrollments.select_related("course").first()
        writer.writerow([
            student.name,
            profile.registration_number if profile else "",
            profile.email if profile else "",
            profile.department.name if profile and profile.department else "",
            course.course.code if course else "",
            student_attendance_percent(student),
            profile.risk_level if profile else "",
            profile.status if profile else "",
        ])
    return response


@login_required
@require_GET
def api_search(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})

    students = Student.objects.filter(
        Q(name__icontains=q) | Q(profile__registration_number__icontains=q)
    )[:8]
    courses = Course.objects.filter(Q(name__icontains=q) | Q(code__icontains=q))[:8]

    results = []
    for s in students:
        results.append({"type": "student", "label": s.name, "url": f"/students/{s.pk}/", "icon": "user"})
    for c in courses:
        results.append({"type": "course", "label": f"{c.code} — {c.name}", "url": f"/courses/{c.pk}/", "icon": "book-open"})
    return JsonResponse({"results": results})
