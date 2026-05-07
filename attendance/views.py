import base64
import json
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import AttendanceSummary, Detection, Session, Student


@login_required
def index(request):
    return render(request, "attendance/index.html")


@login_required
def dashboard(request):
    latest_session = Session.objects.filter(is_active=False, teacher=request.user).order_by("-end_time").first()
    students = Student.objects.all().order_by("name")
    rows = []

    for student in students:
        summary = None
        detection_count = 0
        if latest_session:
            summary = AttendanceSummary.objects.filter(
                student=student, session=latest_session
            ).first()
            detection_count = Detection.objects.filter(
                student=student, session=latest_session
            ).count()

        rows.append(
            {
                "name": student.name,
                "status": summary.status if summary else AttendanceSummary.STATUS_ABSENT,
                "confidence_score": round(summary.confidence_score, 4) if summary else 0.0,
                "detection_count": detection_count,
                "confidence_percent": round((summary.confidence_score if summary else 0.0) * 100, 2),
            }
        )

    context = {
        "rows": rows,
        "total_students": students.count(),
        "has_session": bool(latest_session),
        "session_id": latest_session.id if latest_session else None,
    }
    return render(request, "attendance/dashboard.html", context)


def register_view(request):
    error = ""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        if not name or not email or not password:
            error = "Name, email, and password are required."
        elif User.objects.filter(email=email).exists():
            error = "Email already exists."
        else:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=name,
            )
            login(request, user)
            return redirect("dashboard")

    return render(request, "attendance/register.html", {"error": error})


def login_view(request):
    error = ""
    next_url = request.POST.get("next") or request.GET.get("next") or ""

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        next_url = request.POST.get("next") or request.GET.get("next") or ""
        user = User.objects.filter(email=email).first()

        if user:
            auth_user = authenticate(request, username=user.username, password=password)
            if auth_user:
                login(request, auth_user)
                return redirect(next_url or "dashboard")

        error = "Invalid email or password."

    return render(request, "attendance/login.html", {"error": error, "next": next_url})


def logout_view(request):
    logout(request)
    return redirect("login")


@csrf_exempt
@login_required
@require_POST
def recognize_view(request):
    active_session = Session.objects.filter(is_active=True, teacher=request.user).order_by("-start_time").first()
    if not active_session:
        return JsonResponse({"students": []})
    Session.objects.filter(id=active_session.id).update(total_frames=F("total_frames") + 1)
    active_session.refresh_from_db(fields=["total_frames"])

    try:
        payload = json.loads(request.body.decode("utf-8"))
        image_data = payload.get("image", "")
        if not image_data:
            return JsonResponse({"error": "No image provided.", "students": []}, status=400)

        if "," in image_data:
            image_data = image_data.split(",", 1)[1]

        image_bytes = base64.b64decode(image_data)

        media_dir = Path(settings.MEDIA_ROOT)
        media_dir.mkdir(parents=True, exist_ok=True)
        temp_image_path = media_dir / "temp.jpg"
        temp_image_path.write_bytes(image_bytes)

        from AI.recognize import recognize_faces

        detected_names = recognize_faces(str(temp_image_path))
    except FileNotFoundError as exc:
        return JsonResponse({"error": str(exc), "students": []}, status=500)
    except Exception as exc:
        return JsonResponse({"error": f"Recognition failed: {exc}", "students": []}, status=500)

    seen_names = set()
    now = timezone.now()
    for name in set(detected_names):
        if name == "Unknown":
            continue

        student, _ = Student.objects.get_or_create(name=name)
        last_detection = (
            Detection.objects.filter(student=student, session=active_session)
            .order_by("-timestamp")
            .first()
        )
        if last_detection and (now - last_detection.timestamp).total_seconds() < 3:
            continue

        Detection.objects.create(student=student, session=active_session, timestamp=now)
        seen_names.add(student.name)

    return JsonResponse({"students": sorted(seen_names)})


def _compute_summary_for_session(session):
    if not session.end_time:
        return

    session_duration_seconds = max((session.end_time - session.start_time).total_seconds(), 1.0)
    total_frames = max(1, session.total_frames)

    student_ids = (
        Detection.objects.filter(session=session)
        .values_list("student_id", flat=True)
        .distinct()
    )

    for student_id in student_ids:
        detections = Detection.objects.filter(session=session, student_id=student_id).order_by("timestamp")
        detection_count = detections.count()
        if detection_count == 0:
            continue

        if detection_count < 3:
            AttendanceSummary.objects.update_or_create(
                student_id=student_id,
                session=session,
                defaults={
                    "confidence_score": 0.0,
                    "status": AttendanceSummary.STATUS_ABSENT,
                },
            )
            continue

        first_seen = detections.first().timestamp
        last_seen = detections.last().timestamp
        presence_duration_seconds = max((last_seen - first_seen).total_seconds(), 0.0)

        # Confidence uses frequency, temporal spread, and recency within session.
        detection_ratio = min(detection_count / total_frames, 1.0)
        time_coverage = min(presence_duration_seconds / session_duration_seconds, 1.0)
        recency = min(
            max((last_seen - session.start_time).total_seconds() / session_duration_seconds, 0.0),
            1.0,
        )

        confidence = (detection_ratio * 0.5) + (time_coverage * 0.3) + (recency * 0.2)
        confidence = min(max(confidence, 0.0), 1.0)
        if confidence >= 0.75:
            status = AttendanceSummary.STATUS_PRESENT
        elif confidence >= 0.4:
            status = AttendanceSummary.STATUS_PARTIAL
        else:
            status = AttendanceSummary.STATUS_ABSENT

        # Anti-cheating: require visibility in at least 2 of 3 time segments.
        segment_length = session_duration_seconds / 3
        seen_segments = set()
        for detection in detections:
            elapsed = max((detection.timestamp - session.start_time).total_seconds(), 0.0)
            index = min(int(elapsed // segment_length) if segment_length > 0 else 0, 2)
            seen_segments.add(index)

        if len(seen_segments) < 2:
            if status == AttendanceSummary.STATUS_PRESENT:
                status = AttendanceSummary.STATUS_PARTIAL
            elif status == AttendanceSummary.STATUS_PARTIAL:
                status = AttendanceSummary.STATUS_ABSENT

        AttendanceSummary.objects.update_or_create(
            student_id=student_id,
            session=session,
            defaults={
                "confidence_score": round(confidence, 4),
                "status": status,
            },
        )


@csrf_exempt
@login_required
@require_POST
def start_session_view(request):
    active_session = Session.objects.filter(is_active=True, teacher=request.user).order_by("-start_time").first()
    if active_session:
        return JsonResponse(
            {
                "session_id": active_session.id,
                "is_active": True,
                "message": "Resuming existing active session.",
            }
        )

    now = timezone.now()
    session = Session.objects.create(
        teacher=request.user,
        date=now.date(),
        start_time=now,
        is_active=True,
    )
    return JsonResponse({"session_id": session.id, "is_active": True})


@csrf_exempt
@login_required
@require_POST
def end_session_view(request):
    session = Session.objects.filter(is_active=True, teacher=request.user).order_by("-start_time").first()
    if not session:
        return JsonResponse({"error": "No active session found."}, status=400)

    session.is_active = False
    session.end_time = timezone.now()
    session.save(update_fields=["is_active", "end_time"])

    _compute_summary_for_session(session)

    return JsonResponse({"session_id": session.id, "is_active": False})
