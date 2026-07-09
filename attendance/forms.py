from django import forms
from django.contrib.auth.models import User

from attendance.models import Course, Department, Enrollment, Student, StudentProfile
from attendance.services.dataset import validate_student_image


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Department name"}),
            "code": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. CS"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "name", "code", "department", "semester", "academic_year",
            "credits", "teacher", "description",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "code": forms.TextInput(attrs={"class": "form-input"}),
            "department": forms.Select(attrs={"class": "form-select"}),
            "semester": forms.TextInput(attrs={"class": "form-input", "placeholder": "Fall 2026"}),
            "academic_year": forms.TextInput(attrs={"class": "form-input", "placeholder": "2025-2026"}),
            "credits": forms.NumberInput(attrs={"class": "form-input", "min": 1}),
            "teacher": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["teacher"].initial = user.pk
        self.fields["department"].queryset = Department.objects.all()

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        qs = Course.objects.filter(code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A course with this code already exists.")
        return code


class StudentForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Full name"}),
    )
    registration_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "REG-2026-001"}),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "student@university.edu"}),
    )
    phone = forms.CharField(
        required=False,
        max_length=30,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "+1 555 0000"}),
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
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


class StudentEditForm(forms.ModelForm):
    name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={"class": "form-input"}))

    class Meta:
        model = StudentProfile
        fields = [
            "registration_number", "email", "phone", "department",
            "status", "risk_level", "average_grade", "notes",
        ]
        widgets = {
            "registration_number": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(attrs={"class": "form-input"}),
            "phone": forms.TextInput(attrs={"class": "form-input"}),
            "department": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "risk_level": forms.Select(attrs={"class": "form-select"}),
            "average_grade": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.student_id:
            self.fields["name"].initial = self.instance.student.name

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
        widget=forms.FileInput(attrs={"class": "form-input", "accept": "image/jpeg,image/png,image/jpg"}),
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
