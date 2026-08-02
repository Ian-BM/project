from django.contrib import admin

from .models import (
    Assessment,
    Attendance,
    AttendanceSummary,
    Department,
    Detection,
    Module,
    ModuleEnrollment,
    Notification,
    PerformanceRecord,
    Programme,
    ProgrammeEnrollment,
    ReportLog,
    Session,
    Student,
    StudentImage,
    StudentProfile,
    UnknownFace,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "head_of_department", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "code")


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "department", "duration_years", "status", "created_at")
    list_filter = ("department", "status")
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
        "student", "registration_number", "programme", "department", "year_of_study", "status",
        "recognition_status", "risk_level",
    )
    list_filter = ("status", "recognition_status", "risk_level", "department", "programme")
    search_fields = ("student__name", "registration_number", "email")


@admin.register(StudentImage)
class StudentImageAdmin(admin.ModelAdmin):
    list_display = ("student", "is_primary", "uploaded_at")
    list_filter = ("is_primary",)


class ModuleEnrollmentInline(admin.TabularInline):
    model = ModuleEnrollment
    extra = 1


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "programme", "department", "teacher", "semester", "credits", "status")
    list_filter = ("programme", "department", "semester", "academic_year", "status")
    search_fields = ("name", "code")
    inlines = [ModuleEnrollmentInline]


@admin.register(ModuleEnrollment)
class ModuleEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "module", "enrolled_at")
    list_filter = ("module",)
    search_fields = ("student__name", "module__code")


@admin.register(ProgrammeEnrollment)
class ProgrammeEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "programme", "enrolled_at")
    list_filter = ("programme",)
    search_fields = ("student__name", "programme__code")


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "teacher", "module", "date", "status", "is_active", "total_frames", "room")
    list_filter = ("status", "is_active", "date", "teacher", "module")
    search_fields = ("name", "teacher__username", "room", "module__code")


@admin.register(Detection)
class DetectionAdmin(admin.ModelAdmin):
    list_display = ("student", "session", "timestamp_local")
    list_filter = ("session",)
    search_fields = ("student__name",)

    @admin.display(description="Timestamp", ordering="timestamp")
    def timestamp_local(self, obj):
        from attendance.utils.datetime_fmt import fmt_datetime

        return fmt_datetime(obj.timestamp)


@admin.register(AttendanceSummary)
class AttendanceSummaryAdmin(admin.ModelAdmin):
    list_display = ("student", "session", "status", "confidence_score")
    list_filter = ("status",)
    search_fields = ("student__name",)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "date", "time")


@admin.register(UnknownFace)
class UnknownFaceAdmin(admin.ModelAdmin):
    list_display = ("session", "tracking_id", "confidence", "timestamp_local")
    list_filter = ("session",)

    @admin.display(description="Timestamp", ordering="timestamp")
    def timestamp_local(self, obj):
        from attendance.utils.datetime_fmt import fmt_datetime

        return fmt_datetime(obj.timestamp)


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "assessment_type", "max_marks", "semester", "academic_year", "date")
    list_filter = ("assessment_type", "semester", "academic_year", "module")
    search_fields = ("title", "module__code")


@admin.register(PerformanceRecord)
class PerformanceRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "assessment", "marks", "recorded_at", "recorded_by")
    list_filter = ("assessment__module", "assessment__assessment_type")
    search_fields = ("student__name", "assessment__title")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("title", "message", "user__username")


@admin.register(ReportLog)
class ReportLogAdmin(admin.ModelAdmin):
    list_display = ("report_type", "generated_by", "created_at")
    list_filter = ("report_type",)
