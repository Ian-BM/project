import pickle
from pathlib import Path

import face_recognition


BASE_DIR = Path(__file__).resolve().parent.parent
AI_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET_DIR = AI_DIR / "dataset"
FALLBACK_DATASET_DIR = BASE_DIR / "dataset"
EMBEDDINGS_PATH = AI_DIR / "embeddings.pkl"


def get_dataset_dirs():
    dirs = []
    for dataset_dir in (DEFAULT_DATASET_DIR, FALLBACK_DATASET_DIR):
        if dataset_dir.exists() and dataset_dir.is_dir():
            dirs.append(dataset_dir)
    return dirs


def main():
    dataset_dirs = get_dataset_dirs()
    if not dataset_dirs:
        print(
            "[ERROR] No dataset directory found. Checked: "
            f"{DEFAULT_DATASET_DIR} and {FALLBACK_DATASET_DIR}"
        )
        return

    known_encodings = []
    known_names = []
    total_images = 0
    encoded_images = 0

    print("[INFO] Loading dataset directories:")
    for dataset_dir in dataset_dirs:
        print(f"[INFO] - {dataset_dir}")

    # Merge person folders by name across dataset directories.
    person_dirs_by_name = {}
    for dataset_dir in dataset_dirs:
        for person_dir in dataset_dir.iterdir():
            if not person_dir.is_dir():
                continue
            person_dirs_by_name.setdefault(person_dir.name, []).append(person_dir)

    for person_name in sorted(person_dirs_by_name.keys()):
        print(f"[INFO] Processing person: {person_name}")
        image_paths = []
        for person_dir in person_dirs_by_name[person_name]:
            for image_path in sorted(person_dir.iterdir()):
                if image_path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                    image_paths.append(image_path)

        unique_paths = []
        seen_paths = set()
        for image_path in image_paths:
            resolved = str(image_path.resolve())
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            unique_paths.append(image_path)

        for image_path in unique_paths:
            total_images += 1
            print(f"[INFO] Encoding image: {image_path}")

            try:
                image = face_recognition.load_image_file(str(image_path))
                face_locations = face_recognition.face_locations(image)

                if not face_locations:
                    print(f"[WARN] No face found in: {image_path.name}, skipping.")
                    continue

                encodings = face_recognition.face_encodings(image, face_locations)
                if not encodings:
                    print(f"[WARN] Face encoding failed for: {image_path.name}, skipping.")
                    continue

                known_encodings.append(encodings[0])
                known_names.append(person_name)
                encoded_images += 1
            except Exception as exc:
                print(f"[WARN] Failed to process {image_path}: {exc}")

    data = {"encodings": known_encodings, "names": known_names}
    with EMBEDDINGS_PATH.open("wb") as file:
        pickle.dump(data, file)

    print("[INFO] Embeddings saved successfully.")
    print(f"[INFO] Output: {EMBEDDINGS_PATH}")
    print(f"[INFO] Total images: {total_images}")
    print(f"[INFO] Successfully encoded: {encoded_images}")


if __name__ == "__main__":
    main()
