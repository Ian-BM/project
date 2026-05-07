from django.contrib.auth.models import User
from django.db import models


class Student(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


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
