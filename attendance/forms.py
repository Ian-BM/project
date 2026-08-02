from django import forms
from django.contrib.auth.models import User

from attendance.models import (
    Department,
    Module,
    Programme,
    Session,
    Student,
    StudentProfile,
)
from attendance.services.dataset import validate_student_image


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "description", "head_of_department", "status"]
        labels = {
            "head_of_department": "Head of Department",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Department name"}),
            "code": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. CS"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "head_of_department": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["head_of_department"].queryset = User.objects.filter(is_active=True).order_by(
            "first_name", "username"
        )
        self.fields["head_of_department"].required = False
        self.fields["head_of_department"].empty_label = "— Optional —"

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        qs = Department.objects.filter(code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A department with this code already exists.")
        return code


class ProgrammeForm(forms.ModelForm):
    class Meta:
        model = Programme
        fields = ["name", "code", "department", "duration_years", "description", "status"]
        labels = {
            "duration_years": "Duration (years)",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Bachelor of Computer Science"}
            ),
            "code": forms.TextInput(attrs={"class": "form-input", "placeholder": "BSC-CS"}),
            "department": forms.Select(attrs={"class": "form-select"}),
            "duration_years": forms.NumberInput(attrs={"class": "form-input", "min": 1}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        qs = Programme.objects.filter(code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A programme with this code already exists.")
        return code


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = [
            "department",
            "programme",
            "name",
            "code",
            "teacher",
            "semester",
            "academic_year",
            "credits",
            "description",
            "status",
        ]
        labels = {
            "teacher": "Assigned Lecturer",
            "credits": "Credits (optional)",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Database Systems"}),
            "code": forms.TextInput(attrs={"class": "form-input", "placeholder": "CS301"}),
            "programme": forms.Select(attrs={"class": "form-select", "id": "id_programme"}),
            "department": forms.Select(attrs={"class": "form-select", "id": "id_department"}),
            "semester": forms.TextInput(attrs={"class": "form-input", "placeholder": "Semester 1"}),
            "academic_year": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "2025-2026"}
            ),
            "credits": forms.NumberInput(attrs={"class": "form-input", "min": 1}),
            "teacher": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["credits"].required = False
        self.fields["teacher"].label = "Assigned Lecturer"
        self.fields["teacher"].empty_label = "— Select lecturer —"
        self.fields["teacher"].queryset = User.objects.filter(is_active=True).order_by(
            "first_name", "username"
        )
        if user:
            self.fields["teacher"].initial = user.pk

        self.fields["department"].queryset = Department.objects.filter(
            status=Department.STATUS_ACTIVE
        ).order_by("name")
        # Cascade: filter programmes by selected department when posted or editing
        dept_id = None
        if self.data.get("department"):
            dept_id = self.data.get("department")
        elif self.instance and self.instance.department_id:
            dept_id = self.instance.department_id
        if dept_id:
            self.fields["programme"].queryset = Programme.objects.filter(
                department_id=dept_id, status=Programme.STATUS_ACTIVE
            ).order_by("name")
        else:
            self.fields["programme"].queryset = Programme.objects.none()

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        qs = Module.objects.filter(code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A module with this code already exists.")
        return code

    def clean(self):
        cleaned = super().clean()
        department = cleaned.get("department")
        programme = cleaned.get("programme")
        if department and programme and programme.department_id != department.id:
            self.add_error("programme", "Programme must belong to the selected department.")
        return cleaned


# Backwards-compatible alias
CourseForm = ModuleForm


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = [
            "name",
            "module",
            "room",
            "date",
            "start_time",
            "scheduled_start",
            "scheduled_end",
            "status",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "module": forms.Select(attrs={"class": "form-select"}),
            "room": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Lab A / Room 12"}
            ),
            "date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "start_time": forms.DateTimeInput(
                attrs={"class": "form-input", "type": "datetime-local"}
            ),
            "scheduled_start": forms.DateTimeInput(
                attrs={"class": "form-input", "type": "datetime-local"}
            ),
            "scheduled_end": forms.DateTimeInput(
                attrs={"class": "form-input", "type": "datetime-local"}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["module"].queryset = Module.objects.all().order_by("code")


class StudentForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        label="Student Name",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Full name"}),
    )
    registration_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "REG-2026-001"}),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={"class": "form-input", "placeholder": "student@university.edu"}
        ),
    )
    phone = forms.CharField(
        required=False,
        max_length=30,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "+1 555 0000"}),
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_department"}),
    )
    programme = forms.ModelChoiceField(
        queryset=Programme.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_programme"}),
        help_text="Academic programme the student belongs to.",
    )
    year_of_study = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(attrs={"class": "form-input", "placeholder": "e.g. 1"}),
    )
    status = forms.ChoiceField(
        choices=StudentProfile.STATUS_CHOICES,
        initial=StudentProfile.STATUS_ACTIVE,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-input", "rows": 3}),
    )
    photos = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-input", "multiple": False}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(
            status=Department.STATUS_ACTIVE
        ).order_by("name")
        dept_id = None
        if self.data.get("department"):
            dept_id = self.data.get("department")
        if dept_id:
            self.fields["programme"].queryset = Programme.objects.filter(
                department_id=dept_id, status=Programme.STATUS_ACTIVE
            ).order_by("name")
        else:
            self.fields["programme"].queryset = Programme.objects.filter(
                status=Programme.STATUS_ACTIVE
            ).order_by("name")

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if Student.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError("A student with this name already exists.")
        return name

    def clean_registration_number(self):
        reg = self.cleaned_data["registration_number"].strip()
        if StudentProfile.objects.filter(registration_number__iexact=reg).exists():
            raise forms.ValidationError("This registration number is already in use.")
        return reg

    def clean(self):
        cleaned = super().clean()
        department = cleaned.get("department")
        programme = cleaned.get("programme")
        if department and programme and programme.department_id != department.id:
            self.add_error("programme", "Programme must belong to the selected department.")
        return cleaned


class StudentEditForm(forms.ModelForm):
    name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={"class": "form-input"}))

    class Meta:
        model = StudentProfile
        fields = [
            "registration_number",
            "email",
            "phone",
            "department",
            "programme",
            "year_of_study",
            "status",
            "risk_level",
            "notes",
        ]
        widgets = {
            "registration_number": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(attrs={"class": "form-input"}),
            "phone": forms.TextInput(attrs={"class": "form-input"}),
            "department": forms.Select(attrs={"class": "form-select", "id": "id_department"}),
            "programme": forms.Select(attrs={"class": "form-select", "id": "id_programme"}),
            "year_of_study": forms.NumberInput(attrs={"class": "form-input", "min": 1}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "risk_level": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.student_id:
            self.fields["name"].initial = self.instance.student.name
        dept_id = None
        if self.data.get("department"):
            dept_id = self.data.get("department")
        elif self.instance and self.instance.department_id:
            dept_id = self.instance.department_id
        if dept_id:
            self.fields["programme"].queryset = Programme.objects.filter(
                department_id=dept_id
            ).order_by("name")

    def clean_registration_number(self):
        reg = self.cleaned_data["registration_number"].strip()
        qs = StudentProfile.objects.filter(registration_number__iexact=reg)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This registration number is already in use.")
        return reg


class StudentImageForm(forms.Form):
    photos = forms.FileField(
        widget=forms.FileInput(
            attrs={"class": "form-input", "accept": "image/jpeg,image/png,image/jpg"}
        ),
    )

    def clean_photos(self):
        upload = self.cleaned_data["photos"]
        validate_student_image(upload)
        return upload


class EnrollmentForm(forms.Form):
    students = forms.ModelMultipleChoiceField(
        queryset=Student.objects.all().order_by("name"),
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 10}),
    )
