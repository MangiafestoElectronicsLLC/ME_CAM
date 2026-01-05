from typing import List
from utils.logger import get_logger

logger = get_logger("face_whitelist")

try:
    import face_recognition
except ImportError:
    face_recognition = None
    logger.warning("face_recognition library not available.")


class FaceWhitelist:
    def __init__(self, known_images_dir: str = "faces/whitelist", enabled: bool = False):
        self.enabled = enabled and face_recognition is not None
        self.known_encodings = []
        if self.enabled:
            self._load_whitelist(known_images_dir)

    def _load_whitelist(self, dir_path: str):
        import os

        for fname in os.listdir(dir_path):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            path = os.path.join(dir_path, fname)
            img = face_recognition.load_image_file(path)
            encs = face_recognition.face_encodings(img)
            if encs:
                self.known_encodings.append(encs[0])
        logger.info(f"Loaded {len(self.known_encodings)} whitelisted faces.")

    def is_face_whitelisted(self, frame) -> bool:
        if not self.enabled:
            return True

        rgb = frame[:, :, ::-1]
        encs = face_recognition.face_encodings(rgb)
        if not encs:
            return False
        for enc in encs:
            matches = face_recognition.compare_faces(self.known_encodings, enc)
            if any(matches):
                return True
        return False
