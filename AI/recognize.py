import pickle
from pathlib import Path

import face_recognition
import numpy as np


AI_DIR = Path(__file__).resolve().parent
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


def recognize_faces(image_path):
    known_encodings, known_names = _load_embeddings()
    if not known_encodings:
        return []

    image = face_recognition.load_image_file(image_path)
    face_locations = face_recognition.face_locations(image)
    if not face_locations:
        return []

    face_encodings = face_recognition.face_encodings(image, face_locations)
    detected_names = []

    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(
            known_encodings,
            face_encoding,
            tolerance=TOLERANCE,
        )
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)

        name = "Unknown"
        if len(face_distances) > 0:
            best_match_index = int(np.argmin(face_distances))
            if matches[best_match_index]:
                name = known_names[best_match_index]

        detected_names.append(name)

    return detected_names
