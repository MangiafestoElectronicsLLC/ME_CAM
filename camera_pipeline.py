import os
import time
import cv2
from loguru import logger
from datetime import datetime, timedelta

from config_manager import get_config
from ai_person_detector import PersonDetector
from motion_detector import MotionDetector
from smart_motion_filter import SmartMotionFilter


class CameraPipeline:
    def __init__(self, stop_event, preview_only=False):
        self.stop_event = stop_event
        self.preview_only = preview_only

        cfg = get_config()
        self.storage_cfg = cfg["storage"]
        self.det_cfg = cfg["detection"]

        self.person_detector = PersonDetector("models/person_detection.tflite")
        self.motion_detector = MotionDetector(
            min_area=self.det_cfg.get("min_motion_area", 500)
        )
        self.smart_filter = SmartMotionFilter()

        self.recordings_dir = self.storage_cfg["recordings_dir"]
        os.makedirs(self.recordings_dir, exist_ok=True)

        self._last_motion_clip = None

        self.camera_index = 0
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            logger.warning("[CAMERA] Could not open /dev/video0")

    def run(self):
        logger.info("[PIPELINE] Camera pipeline started.")
        self._cleanup_old_recordings()

        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = None
        recording = False
        last_motion_time = None
        motion_timeout = 5  # seconds after last detection to stop recording

        while not self.stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.2)
                continue

            motion_mask = self.motion_detector.detect(frame)
            motion_detected = self.smart_filter.is_motion_significant(motion_mask)

            person_present = False
            if self.det_cfg.get("person_only", True) and self.person_detector.enabled:
                person_present = self.person_detector.has_person(
                    frame, threshold=self.det_cfg.get("sensitivity", 0.6)
                )
            else:
                person_present = motion_detected

            event_trigger = motion_detected and person_present

            if event_trigger and not recording and not self.preview_only:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                clip_path = os.path.join(self.recordings_dir, f"motion_{timestamp}.avi")
                h, w = frame.shape[:2]
                out = cv2.VideoWriter(clip_path, fourcc, 10.0, (w, h))
                recording = True
                last_motion_time = time.time()
                self._last_motion_clip = clip_path
                logger.info(f"[RECORD] Started motion recording: {clip_path}")

            if recording and out is not None:
                out.write(frame)
                if event_trigger:
                    last_motion_time = time.time()
                elif time.time() - last_motion_time > motion_timeout:
                    logger.info("[RECORD] Stopping motion recording.")
                    out.release()
                    out = None
                    recording = False

            if self.preview_only:
                break

        if self.cap:
            self.cap.release()
        if out:
            out.release()
        logger.info("[PIPELINE] Camera pipeline stopped.")

    def _cleanup_old_recordings(self):
        retention_days = self.storage_cfg.get("retention_days", 7)
        cutoff = datetime.now() - timedelta(days=retention_days)
        for fname in os.listdir(self.recordings_dir):
            fpath = os.path.join(self.recordings_dir, fname)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                if mtime < cutoff:
                    os.remove(fpath)
                    logger.info(f"[CLEANUP] Removed old recording: {fpath}")
            except Exception as e:
                logger.warning(f"[CLEANUP] Error removing {fpath}: {e}")

    def get_last_motion_clip(self):
        return self._last_motion_clip
