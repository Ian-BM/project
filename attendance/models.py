from django.contrib.auth.models import User
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    recognition_status = models.CharField(max_length=20, choices=RECOG_CHOICES, default=RECOG_PENDING)
    risk_level = models.CharField(max_length=20, choices=RISK_CHOICES, default=RISK_LOW)
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
    def primary_course(self):
        enrollment = self.student.enrollments.select_related("course").first()
        return enrollment.course if enrollment else None


class StudentImage(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="students/%Y/%m/")
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "-uploaded_at"]

    def __str__(self):
        return f"Image for {self.student.name}"


class Course(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="courses"
    )
    semester = models.CharField(max_length=50, blank=True)
    academic_year = models.CharField(max_length=20, blank=True)
    credits = models.PositiveIntegerField(default=3)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="courses")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.student.name} → {self.course.code}"


class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendances")
    date = models.DateField()
    time = models.TimeField()

    class Meta:
        unique_together = ("student", "date")

    def __str__(self):
        return f"{self.student.name} - {self.date} {self.time}"


class Session(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name="sessions")
    date = models.DateField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    total_frames = models.IntegerField(default=0)

    def __str__(self):
        return f"Session {self.id} ({'Active' if self.is_active else 'Closed'})"


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
