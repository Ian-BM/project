from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Department(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    head_of_department = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Programme(models.Model):
    """Academic degree / programme a student belongs to (e.g. BSc Computer Science)."""

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="programmes"
    )
    duration_years = models.PositiveIntegerField(default=4)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class Student(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_SUSPENDED = "suspended"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
        (STATUS_SUSPENDED, "Suspended"),
    ]

    RECOG_ENCODED = "encoded"
    RECOG_PENDING = "pending"
    RECOG_FAILED = "failed"
    RECOG_CHOICES = [
        (RECOG_ENCODED, "Encoded"),
        (RECOG_PENDING, "Pending"),
        (RECOG_FAILED, "Failed"),
    ]

    RISK_LOW = "low"
    RISK_MEDIUM = "medium"
    RISK_HIGH = "high"
    RISK_CHOICES = [
        (RISK_LOW, "Low"),
        (RISK_MEDIUM, "Medium"),
        (RISK_HIGH, "High"),
    ]

    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="profile")
    registration_number = models.CharField(max_length=50, unique=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="students"
    )
    programme = models.ForeignKey(
        Programme, on_delete=models.SET_NULL, null=True, blank=True, related_name="students"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    year_of_study = models.PositiveIntegerField(null=True, blank=True)
    recognition_status = models.CharField(max_length=20, choices=RECOG_CHOICES, default=RECOG_PENDING)
    risk_level = models.CharField(max_length=20, choices=RISK_CHOICES, default=RISK_LOW)
    # Kept for legacy data; not used by the UI after Performance module removal
    average_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    teacher = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_students"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["student__name"]

    def __str__(self):
        return self.student.name

    @property
    def primary_module(self):
        enrollment = self.student.module_enrollments.select_related("module").first()
        return enrollment.module if enrollment else None

    # Backwards-compatible alias used by older templates/services
    @property
    def primary_course(self):
        return self.primary_module


class StudentImage(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="students/%Y/%m/")
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "-uploaded_at"]

    def __str__(self):
        return f"Image for {self.student.name}"


class Module(models.Model):
    """Individual subject taught by a lecturer (formerly Course)."""

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    programme = models.ForeignKey(
        Programme, on_delete=models.SET_NULL, null=True, blank=True, related_name="modules"
    )
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="modules"
    )
    semester = models.CharField(max_length=50, blank=True)
    academic_year = models.CharField(max_length=20, blank=True)
    credits = models.PositiveIntegerField(default=3)
    teacher = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="modules"
    )
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        db_table = "attendance_course"

    def __str__(self):
        return f"{self.code} — {self.name}"


# Backwards-compatible alias so existing imports of Course keep working during transition
Course = Module


class ProgrammeEnrollment(models.Model):
    """Student belongs to a Programme."""

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="programme_enrollments")
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "programme")
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.student.name} → {self.programme.code}"


class ModuleEnrollment(models.Model):
    """Student roster for a Module (subject)."""

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="module_enrollments")
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="enrollments",
        db_column="course_id",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "module")
        ordering = ["-enrolled_at"]
        db_table = "attendance_enrollment"

    def __str__(self):
        return f"{self.student.name} → {self.module.code}"

    @property
    def course(self):
        return self.module


# Backwards-compatible alias for existing imports
Enrollment = ModuleEnrollment


class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendances")
    date = models.DateField()
    time = models.TimeField()

    class Meta:
        unique_together = ("student", "date")

    def __str__(self):
        return f"{self.student.name} - {self.date} {self.time}"


class Session(models.Model):
    STATUS_UPCOMING = "upcoming"
    STATUS_ACTIVE = "active"
    STATUS_PAUSED = "paused"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_UPCOMING, "Upcoming"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAUSED, "Paused"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    module = models.ForeignKey(
        Module, on_delete=models.SET_NULL, null=True, blank=True, related_name="sessions",
        db_column="course_id",
    )
    name = models.CharField(max_length=255, blank=True)
    room = models.CharField(max_length=100, blank=True)
    date = models.DateField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_paused = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    total_frames = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_time"]

    def __str__(self):
        label = self.name or f"Session {self.id}"
        return f"{label} ({self.get_status_display()})"

    @property
    def course(self):
        """Backwards-compatible alias."""
        return self.module

    @course.setter
    def course(self, value):
        self.module = value

    @property
    def duration_seconds(self):
        end = self.end_time or timezone.now()
        if not self.start_time:
            return 0
        return max((end - self.start_time).total_seconds(), 0)

    @property
    def programme(self):
        return self.module.programme if self.module else None


class Detection(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="detections")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="detections")
    timestamp = models.DateTimeField()

    def __str__(self):
        return f"{self.student.name} @ {self.timestamp}"


class AttendanceSummary(models.Model):
    STATUS_PRESENT = "Present"
    STATUS_PARTIAL = "Partial"
    STATUS_ABSENT = "Absent"
    STATUS_CHOICES = [
        (STATUS_PRESENT, STATUS_PRESENT),
        (STATUS_PARTIAL, STATUS_PARTIAL),
        (STATUS_ABSENT, STATUS_ABSENT),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance_summaries")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="attendance_summaries")
    confidence_score = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ("student", "session")

    def __str__(self):
        return f"{self.student.name} - {self.status} ({self.confidence_score:.2f})"


class UnknownFace(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="unknown_faces")
    tracking_id = models.PositiveIntegerField(default=0)
    confidence = models.FloatField(default=0.0)
    timestamp = models.DateTimeField(auto_now_add=True)
    snapshot = models.ImageField(upload_to="unknown/%Y/%m/", blank=True, null=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"Unknown #{self.tracking_id} @ session {self.session_id}"


class Assessment(models.Model):
    TYPE_CAT = "cat"
    TYPE_ASSIGNMENT = "assignment"
    TYPE_EXAM = "exam"
    TYPE_PROJECT = "project"
    TYPE_QUIZ = "quiz"
    TYPE_CHOICES = [
        (TYPE_CAT, "CAT"),
        (TYPE_ASSIGNMENT, "Assignment"),
        (TYPE_EXAM, "Exam"),
        (TYPE_PROJECT, "Project"),
        (TYPE_QUIZ, "Quiz"),
    ]

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="assessments")
    title = models.CharField(max_length=255)
    assessment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_CAT)
    max_marks = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    semester = models.CharField(max_length=50, blank=True)
    academic_year = models.CharField(max_length=20, blank=True)
    date = models.DateField(null=True, blank=True)
    teacher = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assessments"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.module.code})"


class PerformanceRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="performance_records")
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="records")
    marks = models.DecimalField(max_digits=6, decimal_places=2)
    remarks = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="recorded_performances"
    )

    class Meta:
        unique_together = ("student", "assessment")
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.student.name} — {self.assessment.title}: {self.marks}"

    @property
    def percentage(self):
        if not self.assessment.max_marks:
            return 0.0
        return round(float(self.marks) / float(self.assessment.max_marks) * 100, 1)

    @property
    def passed(self):
        return self.percentage >= 40.0


class Notification(models.Model):
    TYPE_INFO = "info"
    TYPE_WARNING = "warning"
    TYPE_DANGER = "danger"
    TYPE_SUCCESS = "success"
    TYPE_CHOICES = [
        (TYPE_INFO, "Info"),
        (TYPE_WARNING, "Warning"),
        (TYPE_DANGER, "Danger"),
        (TYPE_SUCCESS, "Success"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_INFO)
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ReportLog(models.Model):
    REPORT_ATTENDANCE = "attendance"
    REPORT_PROGRAMME = "programme"
    REPORT_MODULE = "module"
    REPORT_TEACHER = "teacher"
    REPORT_LECTURER = "teacher"  # alias — report_type value stays "teacher" for DB compat
    REPORT_STUDENT = "student"
    REPORT_SESSION = "session"
    REPORT_RECOGNITION = "recognition"
    REPORT_CONFIDENCE = "confidence"
    REPORT_CHOICES = [
        (REPORT_ATTENDANCE, "Attendance Report"),
        (REPORT_PROGRAMME, "Programme Report"),
        (REPORT_MODULE, "Module Report"),
        (REPORT_TEACHER, "Lecturer Report"),
        (REPORT_STUDENT, "Student Report"),
        (REPORT_SESSION, "Session Report"),
        (REPORT_RECOGNITION, "Recognition Report"),
        (REPORT_CONFIDENCE, "Confidence Report"),
    ]

    report_type = models.CharField(max_length=30, choices=REPORT_CHOICES)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="reports")
    filters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_report_type_display()} @ {self.created_at:%Y-%m-%d %H:%M}"
