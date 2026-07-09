import pickle
from pathlib import Path

import face_recognition
import numpy as np
from django.conf import settings

AI_DIR = Path(settings.BASE_DIR) / "AI"
EMBEDDINGS_PATH = AI_DIR / "embeddings.pkl"
TOLERANCE = 0.5


def _load_embeddings():
    if not EMBEDDINGS_PATH.exists():
        raise FileNotFoundError(
            f"Embeddings file not found: {EMBEDDINGS_PATH}. Run 'python AI/encode_faces.py' first."
        )
    with EMBEDDINGS_PATH.open("rb") as file:
        data = pickle.load(file)
    return data.get("encodings", []), data.get("names", [])


def recognize_faces_detailed(image_path):
    """
    Returns per-face detection details for the attendance UI.
    Uses the same matching logic as AI/recognize.py without modifying that module.
    """
    known_encodings, known_names = _load_embeddings()
    image = face_recognition.load_image_file(image_path)
    face_locations = face_recognition.face_locations(image)
    if not face_locations:
        return []

    face_encodings = face_recognition.face_encodings(image, face_locations)
    results = []

    for index, (face_encoding, location) in enumerate(zip(face_encodings, face_locations), start=1):
        top, right, bottom, left = location
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=TOLERANCE)
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)

        name = "Unknown"
        confidence = 0.0
        state = "unknown"

        if len(face_distances) > 0:
            best_match_index = int(np.argmin(face_distances))
            distance = float(face_distances[best_match_index])
            confidence = round(max(0.0, 1.0 - distance), 4)
            if matches[best_match_index]:
                name = known_names[best_match_index]
                state = "recognized"
            else:
                state = "unknown"

        results.append(
            {
                "tracking_id": index,
                "name": name,
                "confidence": confidence,
                "confidence_percent": round(confidence * 100, 1),
                "state": state,
                "box": {"top": top, "right": right, "bottom": bottom, "left": left},
            }
        )

    return results
