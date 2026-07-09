from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from attendance.forms import CourseForm, EnrollmentForm
from attendance.models import AttendanceSummary, Course, Department, Enrollment, Session, Student
from attendance.services.dashboard_stats import student_attendance_percent


def _course_queryset(request):
    qs = Course.objects.select_related("department", "teacher").annotate(
        student_count=Count("enrollments", distinct=True)
    )
    q = request.GET.get("q", "").strip()
    department = request.GET.get("department", "")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
    if department:
        qs = qs.filter(department_id=department)
    return qs.order_by("name")


@login_required
def course_list(request):
    queryset = _course_queryset(request)
    paginator = Paginator(queryset, 12)
    page = paginator.get_page(request.GET.get("page"))

    rows = []
    for course in page.object_list:
        sessions = Session.objects.filter(course=course, is_active=False)
        summaries = AttendanceSummary.objects.filter(session__in=sessions)
        avg_conf = summaries.aggregate(avg=Avg("confidence_score"))["avg"] or 0
        present = summaries.filter(
            status__in=[AttendanceSummary.STATUS_PRESENT, AttendanceSummary.STATUS_PARTIAL]
        ).count()
        total_summaries = summaries.count()
        att_pct = round((present / total_summaries) * 100, 1) if total_summaries else 0
        rows.append({
            "course": course,
            "students": course.student_count,
            "attendance_percent": att_pct,
            "recognition_percent": round(float(avg_conf) * 100, 1),
        })

    return render(
        request,
        "attendance/courses/list.html",
        {
            "page_obj": page,
            "rows": rows,
            "departments": Department.objects.all(),
            "filters": request.GET,
        },
    )


@login_required
def course_create(request):
    if request.method == "POST":
        form = CourseForm(request.POST, user=request.user)
        if form.is_valid():
            course = form.save(commit=False)
            if not course.teacher_id:
                course.teacher = request.user
            course.save()
            messages.success(request, f"Course {course.code} created.")
            return redirect("course_detail", pk=course.pk)
    else:
        form = CourseForm(user=request.user, initial={"teacher": request.user})
    return render(request, "attendance/courses/form.html", {"form": form, "is_edit": False})


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course.objects.select_related("department", "teacher"), pk=pk)
    enrollments = Enrollment.objects.filter(course=course).select_related("student", "student__profile")
    sessions = Session.objects.filter(course=course).order_by("-start_time")[:10]

    student_rows = []
    for enr in enrollments:
        student = enr.student
        student_rows.append({
            "student": student,
            "profile": getattr(student, "profile", None),
            "attendance_percent": student_attendance_percent(student),
        })

    sessions_count = Session.objects.filter(course=course).count()
    summaries = AttendanceSummary.objects.filter(session__course=course)
    avg_conf = summaries.aggregate(avg=Avg("confidence_score"))["avg"] or 0

    return render(
        request,
        "attendance/courses/detail.html",
        {
            "course": course,
            "student_rows": student_rows,
            "sessions": sessions,
            "sessions_count": sessions_count,
            "enrollment_count": enrollments.count(),
            "avg_confidence": round(float(avg_conf) * 100, 1),
        },
    )


@login_required
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Course updated.")
            return redirect("course_detail", pk=course.pk)
    else:
        form = CourseForm(instance=course, user=request.user)
    return render(request, "attendance/courses/form.html", {"form": form, "is_edit": True, "course": course})


@login_required
@require_POST
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    code = course.code
    course.delete()
    messages.success(request, f"Course {code} deleted.")
    return redirect("course_list")


@login_required
def course_enroll(request, pk):
    course = get_object_or_404(Course, pk=pk)
    enrolled_ids = set(Enrollment.objects.filter(course=course).values_list("student_id", flat=True))
    available = Student.objects.exclude(pk__in=enrolled_ids).order_by("name")

    if request.method == "POST":
        student_ids = request.POST.getlist("students")
        added = 0
        for sid in student_ids:
            _, created = Enrollment.objects.get_or_create(student_id=sid, course=course)
            if created:
                added += 1
        messages.success(request, f"{added} student(s) enrolled in {course.code}.")
        return redirect("course_detail", pk=course.pk)

    return render(
        request,
        "attendance/courses/enroll.html",
        {"course": course, "available_students": available},
    )


@login_required
@require_POST
def course_unenroll(request, pk, student_id):
    course = get_object_or_404(Course, pk=pk)
    Enrollment.objects.filter(course=course, student_id=student_id).delete()
    messages.success(request, "Student removed from course.")
    return redirect("course_detail", pk=pk)
