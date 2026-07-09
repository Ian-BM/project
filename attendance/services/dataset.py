import os
import shutil
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def validate_student_image(upload: UploadedFile):
    ext = Path(upload.name).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError("Only JPG, JPEG, and PNG images are allowed.")
    if upload.size > MAX_IMAGE_SIZE:
        raise ValidationError("Image must be smaller than 5 MB.")


def dataset_dir_for_student(student_name: str) -> Path:
    base = Path(settings.BASE_DIR) / "dataset"
    base.mkdir(parents=True, exist_ok=True)
    folder = base / student_name.strip().lower()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def copy_image_to_dataset(student_name: str, source_path, filename: str) -> Path:
    dest_dir = dataset_dir_for_student(student_name)
    dest = dest_dir / filename
    shutil.copy2(str(source_path), dest)
    return dest


def save_upload_to_dataset(student_name: str, upload: UploadedFile) -> Path:
    validate_student_image(upload)
    dest_dir = dataset_dir_for_student(student_name)
    ext = Path(upload.name).suffix.lower()
    dest = dest_dir / f"{student_name.lower()}_{upload.name}"
    if dest.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        dest = dest.with_suffix(ext)
    with dest.open("wb") as f:
        for chunk in upload.chunks():
            f.write(chunk)
    return dest


def encoding_update_instructions() -> str:
    return (
        "Student photos saved to dataset folder. To update face recognition embeddings, run:\n"
        "python AI/encode_faces.py\n"
        "This will NOT overwrite automatically — run manually when ready."
    )
