# Safe additive migration — preserve Course/Enrollment tables, rename in ORM state only

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("attendance", "0006_phase2_models"),
    ]

    operations = [
        # ORM rename only — tables stay attendance_course / attendance_enrollment
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameModel(old_name="Course", new_name="Module"),
                migrations.AlterModelTable(name="module", table="attendance_course"),
                migrations.AlterModelOptions(name="module", options={"ordering": ["name"]}),
                migrations.AlterField(
                    model_name="module",
                    name="department",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="modules",
                        to="attendance.department",
                    ),
                ),
                migrations.AlterField(
                    model_name="module",
                    name="teacher",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="modules",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                migrations.RenameModel(old_name="Enrollment", new_name="ModuleEnrollment"),
                migrations.AlterModelTable(name="moduleenrollment", table="attendance_enrollment"),
                migrations.AlterModelOptions(name="moduleenrollment", options={"ordering": ["-enrolled_at"]}),
                migrations.RenameField(model_name="moduleenrollment", old_name="course", new_name="module"),
                migrations.AlterField(
                    model_name="moduleenrollment",
                    name="module",
                    field=models.ForeignKey(
                        db_column="course_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="enrollments",
                        to="attendance.module",
                    ),
                ),
                migrations.AlterField(
                    model_name="moduleenrollment",
                    name="student",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="module_enrollments",
                        to="attendance.student",
                    ),
                ),
                migrations.AlterUniqueTogether(
                    name="moduleenrollment",
                    unique_together={("student", "module")},
                ),
                migrations.RenameField(model_name="session", old_name="course", new_name="module"),
                migrations.AlterField(
                    model_name="session",
                    name="module",
                    field=models.ForeignKey(
                        blank=True,
                        db_column="course_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sessions",
                        to="attendance.module",
                    ),
                ),
                migrations.AlterField(
                    model_name="session",
                    name="teacher",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                migrations.AlterModelOptions(name="session", options={"ordering": ["-start_time"]}),
            ],
            database_operations=[],
        ),

        # Additive Session fields
        migrations.AddField(model_name="session", name="is_paused", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="session", name="name", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="session", name="notes", field=models.TextField(blank=True)),
        migrations.AddField(model_name="session", name="room", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="session", name="scheduled_end", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="session", name="scheduled_start", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(
            model_name="session",
            name="status",
            field=models.CharField(
                choices=[
                    ("upcoming", "Upcoming"),
                    ("active", "Active"),
                    ("paused", "Paused"),
                    ("completed", "Completed"),
                    ("cancelled", "Cancelled"),
                ],
                default="active",
                max_length=20,
            ),
        ),

        # Programme
        migrations.CreateModel(
            name="Programme",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("code", models.CharField(max_length=50, unique=True)),
                ("duration_years", models.PositiveIntegerField(default=4)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "department",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="programmes",
                        to="attendance.department",
                    ),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddField(
            model_name="module",
            name="programme",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="modules",
                to="attendance.programme",
            ),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="programme",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="students",
                to="attendance.programme",
            ),
        ),
        migrations.CreateModel(
            name="ProgrammeEnrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enrolled_at", models.DateTimeField(auto_now_add=True)),
                (
                    "programme",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="enrollments",
                        to="attendance.programme",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="programme_enrollments",
                        to="attendance.student",
                    ),
                ),
            ],
            options={"ordering": ["-enrolled_at"], "unique_together": {("student", "programme")}},
        ),
        migrations.CreateModel(
            name="Assessment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                (
                    "assessment_type",
                    models.CharField(
                        choices=[
                            ("cat", "CAT"),
                            ("assignment", "Assignment"),
                            ("exam", "Exam"),
                            ("project", "Project"),
                            ("quiz", "Quiz"),
                        ],
                        default="cat",
                        max_length=20,
                    ),
                ),
                ("max_marks", models.DecimalField(decimal_places=2, default=100, max_digits=6)),
                ("semester", models.CharField(blank=True, max_length=50)),
                ("academic_year", models.CharField(blank=True, max_length=20)),
                ("date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "module",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assessments",
                        to="attendance.module",
                    ),
                ),
                (
                    "teacher",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assessments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="PerformanceRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("marks", models.DecimalField(decimal_places=2, max_digits=6)),
                ("remarks", models.TextField(blank=True)),
                ("recorded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "assessment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="records",
                        to="attendance.assessment",
                    ),
                ),
                (
                    "recorded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="recorded_performances",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="performance_records",
                        to="attendance.student",
                    ),
                ),
            ],
            options={"ordering": ["-recorded_at"], "unique_together": {("student", "assessment")}},
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("message", models.TextField()),
                (
                    "notification_type",
                    models.CharField(
                        choices=[
                            ("info", "Info"),
                            ("warning", "Warning"),
                            ("danger", "Danger"),
                            ("success", "Success"),
                        ],
                        default="info",
                        max_length=20,
                    ),
                ),
                ("is_read", models.BooleanField(default=False)),
                ("link", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ReportLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "report_type",
                    models.CharField(
                        choices=[
                            ("attendance", "Attendance Report"),
                            ("programme", "Programme Report"),
                            ("module", "Module Report"),
                            ("teacher", "Teacher Report"),
                            ("student", "Student Report"),
                            ("session", "Session Report"),
                            ("recognition", "Recognition Report"),
                            ("confidence", "Confidence Report"),
                        ],
                        max_length=30,
                    ),
                ),
                ("filters", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "generated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="UnknownFace",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tracking_id", models.PositiveIntegerField(default=0)),
                ("confidence", models.FloatField(default=0.0)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("snapshot", models.ImageField(blank=True, null=True, upload_to="unknown/%Y/%m/")),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="unknown_faces",
                        to="attendance.session",
                    ),
                ),
            ],
            options={"ordering": ["-timestamp"]},
        ),
        migrations.RunSQL(
            sql=(
                "UPDATE attendance_session SET status='completed' WHERE is_active=0;"
                "UPDATE attendance_session SET status='active' WHERE is_active=1;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
