from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    Attendance,
    AttendanceSummary,
    Course,
    Department,
    Detection,
    Enrollment,
    Session,
    Student,
    StudentImage,
    StudentProfile,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "created_at")
    search_fields = ("name", "code")


class StudentImageInline(admin.TabularInline):
    model = StudentImage
    extra = 0


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("name", "id")
    search_fields = ("name",)
    inlines = [StudentImageInline]


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "student", "registration_number", "department", "status",
        "recognition_status", "risk_level", "average_grade",
    )
    list_filter = ("status", "recognition_status", "risk_level", "department")
    search_fields = ("student__name", "registration_number", "email")


@admin.register(StudentImage)
class StudentImageAdmin(admin.ModelAdmin):
    list_display = ("student", "is_primary", "uploaded_at")
    list_filter = ("is_primary",)


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "department", "teacher", "semester", "credits")
    list_filter = ("department", "semester", "academic_year")
    search_fields = ("name", "code")
    inlines = [EnrollmentInline]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "enrolled_at")
    list_filter = ("course",)
    search_fields = ("student__name", "course__code")


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("id", "teacher", "course", "date", "is_active", "total_frames")
    list_filter = ("is_active", "date", "teacher")
    search_fields = ("teacher__username",)


@admin.register(Detection)
class DetectionAdmin(admin.ModelAdmin):
    list_display = ("student", "session", "timestamp")
    list_filter = ("session",)


@admin.register(AttendanceSummary)
class AttendanceSummaryAdmin(admin.ModelAdmin):
    list_display = ("student", "session", "status", "confidence_score")
    list_filter = ("status",)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "date", "time")
