import os
import cv2
import time
from threading import Event
from typing import Optional

from config_manager import load_config
from motion_detector import MotionDetector
from smart_motion_filter import SmartMotionFilter
from ai_person_detector import PersonDetector
from face_recognition_whitelist import FaceWhitelist
from battery_monitor import BatteryMonitor
from cloud.email_notifier import EmailNotifier
from cloud.gdrive_uploader import GDriveUploader
from utils.logger import get_logger

logger = get_logger("camera_pipeline")


class CameraPipeline:
    def __init__(self, stop_event: Event):
        self.stop_event = stop_event
        self.config = load_config()

        cam_cfg = self.config["camera"]
        self.cap = cv2.VideoCapture(cam_cfg["source"])
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_cfg["resolution"][0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_cfg["resolution"][1])
        self.cap.set(cv2.CAP_PROP_FPS, cam_cfg["fps"])

        mot_cfg = self.config["motion"]
        self.motion_detector = MotionDetector(
            sensitivity=mot_cfg["sensitivity"],
            min_area=mot_cfg["min_area"],
        )
        self.motion_filter = SmartMotionFilter()

        ai_cfg = self.config["ai"]
        self.person_detector = PersonDetector(
            model_path=ai_cfg["tflite_model_path"],
            enabled=ai_cfg["person_detection_enabled"],
        )
        self.face_whitelist = FaceWhitelist(enabled=ai_cfg["face_whitelist_enabled"])

        bat_cfg = self.config["battery"]
        self.battery_monitor = BatteryMonitor(
            enabled=bat_cfg["enabled"],
            low_threshold_percent=bat_cfg["low_threshold_percent"],
        )

        alert_cfg = self.config["alerts"]
        self.email_notifier = EmailNotifier(enabled=alert_cfg["email_enabled"])
        self.gdrive_uploader = GDriveUploader(enabled=alert_cfg["gdrive_enabled"])

        self.recordings_dir = self.config["storage"]["recordings_dir"]
        os.makedirs(self.recordings_dir, exist_ok=True)

        self.current_writer: Optional[cv2.VideoWriter] = None
        self.recording = False

    def get_battery_status(self):
        return self.battery_monitor.get_status()

    def _start_recording(self, frame):
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.recordings_dir, f"event_{ts}.mp4")

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        h, w = frame.shape[:2]
        fps = self.config["camera"]["fps"]
        self.current_writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
        self.recording = True
        logger.info(f"Recording started: {path}")
        return path

    def _stop_recording(self):
        if self.current_writer:
            self.current_writer.release()
        self.current_writer = None
        self.recording = False
        logger.info("Recording stopped.")

    def run(self):
        if not self.cap.isOpened():
            logger.error("Camera failed to open.")
            return

        last_path = None

        while not self.stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                logger.error("Failed to read frame from camera.")
                time.sleep(1)
                continue

            if self.motion_detector.detect(frame):
                if self.motion_filter.register_motion():
                    if self.person_detector.is_person_present(frame) and \
                       self.face_whitelist.is_face_whitelisted(frame):

                        if not self.recording:
                            last_path = self._start_recording(frame)
                        if self.current_writer:
                            self.current_writer.write(frame)
                    else:
                        logger.info("Motion not confirmed by AI filters.")
                elif self.recording and self.current_writer:
                    self.current_writer.write(frame)
            else:
                if self.recording:
                    self._stop_recording()
                    if last_path:
                        self.email_notifier.send_alert(
                            "ME Camera Event",
                            f"New event recorded: {last_path}",
                        )
                        self.gdrive_uploader.upload_file(last_path)

            time.sleep(0.01)

        if self.recording:
            self._stop_recording()
        self.cap.release()
