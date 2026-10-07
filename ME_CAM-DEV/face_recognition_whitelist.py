import os
import threading

from utils.logger import get_logger

logger = get_logger("face_whitelist")

try:
    import face_recognition
except ImportError:
    face_recognition = None
    logger.warning("face_recognition library not available.")


class FaceWhitelist:
    def __init__(self, known_images_dir: str = None, enabled: bool = False, tolerance: float = 0.5):
        self.known_images_dir = known_images_dir or os.path.join(os.path.dirname(__file__), "faces", "whitelist")
        self.tolerance = tolerance
        self.available = face_recognition is not None
        self.enabled = enabled and face_recognition is not None
        self.known_encodings = []
        self.known_names = []
        self._lock = threading.RLock()
        if self.enabled:
            self._load_whitelist(known_images_dir)

    def _load_whitelist(self, dir_path: str):
        dir_path = dir_path or self.known_images_dir
        os.makedirs(dir_path, exist_ok=True)
        encodings = []
        names = []

        for fname in sorted(os.listdir(dir_path)):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            path = os.path.join(dir_path, fname)
            try:
                img = face_recognition.load_image_file(path)
                encs = face_recognition.face_encodings(img)
            except Exception as exc:
                logger.warning(f"Could not load whitelist image {fname}: {exc}")
                continue
            if encs:
                encodings.append(encs[0])
                names.append(os.path.splitext(fname)[0])
        with self._lock:
            self.known_encodings = encodings
            self.known_names = names
        logger.info(f"Loaded {len(encodings)} whitelisted faces.")

    def reload(self):
        if self.enabled:
            self._load_whitelist(self.known_images_dir)

    def set_enabled(self, enabled: bool):
        self.enabled = bool(enabled and self.available)
        if self.enabled and not self.known_encodings:
            self._load_whitelist(self.known_images_dir)

    def recognize(self, frame):
        if not self.enabled:
            return []
        import cv2

        with self._lock:
            known_encodings = list(self.known_encodings)
            known_names = list(self.known_names)
        if not known_encodings:
            return []

        height, width = frame.shape[:2]
        if width > 640:
            frame = cv2.resize(frame, (640, max(1, int(height * 640 / width))))
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb, model="hog")
        encodings = face_recognition.face_encodings(rgb, locations)
        recognized = []
        for encoding in encodings:
            distances = face_recognition.face_distance(known_encodings, encoding)
            if len(distances) == 0:
                continue
            best_match = int(distances.argmin())
            name = known_names[best_match]
            if distances[best_match] <= self.tolerance and name not in recognized:
                recognized.append(name)
        return recognized

    def is_face_whitelisted(self, frame) -> bool:
        if not self.enabled:
            return True
        return bool(self.recognize(frame))
