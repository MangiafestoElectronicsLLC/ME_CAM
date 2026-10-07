import threading
import time
from typing import Generator, Optional

import cv2
import numpy as np

from utils.logger import get_logger
from utils.config_manager import get_config
from motion_detector import MotionDetector
from libcamera_streamer import LibcameraMJPEGStreamer
from hardware_profile import get_camera_profile
from face_recognition_whitelist import FaceWhitelist

logger = get_logger("camera_pipeline")


class CameraPipeline:
    """
    High-level camera pipeline that wires together:
    - Libcamera MJPEG streamer
    - Motion detector
    - Configuration (resolution, fps)
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._streamer: Optional[LibcameraMJPEGStreamer] = None
        self._motion_detector = MotionDetector()
        profile = get_camera_profile()
        config = get_config()
        self._face_recognition_supported = profile["face_recognition"]
        self._face_recognizer = FaceWhitelist(
            enabled=self._face_recognition_supported and config.get("face_recognition_enabled", self._face_recognition_supported)
        )
        self._face_status_lock = threading.Lock()
        self._last_face_check = 0.0
        self._recognized_faces = []
        self._running = False

        self._load_stream_config()

    def _load_stream_config(self):
        config = get_config()
        profile = get_camera_profile()
        resolution = config.get("stream_resolution", profile["resolution"])
        fps = int(config.get("stream_fps", profile["fps"]))
        fps = max(5, min(fps, profile["max_fps"]))

        try:
            width_str, height_str = resolution.lower().split("x")
            width = int(width_str)
            height = int(height_str)
        except Exception:
            logger.warning("[PIPELINE] Invalid resolution in config, falling back to 1536x864")
            width, height = 1536, 864

        self._width = width
        self._height = height
        self._fps = fps
        logger.info(f"[PIPELINE] Using resolution {width}x{height} at {fps} fps")

    def _ensure_streamer(self):
        if self._streamer is None:
            self._streamer = LibcameraMJPEGStreamer(
                width=self._width,
                height=self._height,
                fps=self._fps,
            )
            self._streamer.start()

    def update_stream_settings(self):
        """
        Called when config is changed via /config in the web UI.
        """
        with self._lock:
            self._load_stream_config()
            if self._streamer:
                logger.info("[PIPELINE] Restarting streamer with new resolution/fps")
                self._streamer.restart(
                    width=self._width,
                    height=self._height,
                    fps=self._fps,
                )

    def run(self):
        """
        Optional background pipeline work (e.g., motion detection on frames).
        You can expand this later if you want motion detection to run in the background.
        """
        logger.info("[PIPELINE] Camera pipeline started.")
        self._running = True
        self._ensure_streamer()

        # Example: background loop that could run motion detection, etc.
        while self._running:
            time.sleep(0.5)

    def stop(self):
        self._running = False
        if self._streamer:
            self._streamer.stop()

    def update_face_recognition(self, enabled):
        self._face_recognizer.set_enabled(self._face_recognition_supported and enabled)
        with self._face_status_lock:
            self._recognized_faces = []

    def reload_face_whitelist(self):
        self._face_recognizer.reload()

    def face_status(self):
        return {
            "supported": self._face_recognition_supported,
            "available": self._face_recognizer.available,
            "enabled": self._face_recognizer.enabled,
            "known_faces": len(self._face_recognizer.known_names),
            "recognized": self._recognized_faces[:],
        }

    def _recognize_stream_frame(self, jpeg_frame):
        if not self._face_recognizer.enabled:
            return
        now = time.monotonic()
        with self._face_status_lock:
            if now - self._last_face_check < 1.5:
                return
            self._last_face_check = now
        try:
            encoded = np.frombuffer(jpeg_frame, dtype=np.uint8)
            frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
            recognized = self._face_recognizer.recognize(frame) if frame is not None else []
        except Exception as exc:
            logger.warning(f"[FACE] Recognition failed: {exc}")
            recognized = []
        with self._face_status_lock:
            self._recognized_faces = recognized

    def mjpeg_frames(self) -> Generator[bytes, None, None]:
        """
        Frame generator used by Flask MJPEG endpoint.
        """
        self._ensure_streamer()
        if not self._streamer:
            logger.warning("[PIPELINE] Streamer not available, no frames will be produced.")
            while True:
                time.sleep(0.5)
                yield b""

        for frame in self._streamer.frames():
            self._recognize_stream_frame(frame)
            yield frame
