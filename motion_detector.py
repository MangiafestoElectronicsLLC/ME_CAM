import cv2
import numpy as np
from utils.logger import get_logger

logger = get_logger("motion_detector")


class MotionDetector:
    def __init__(self, sensitivity: float = 0.5, min_area: int = 500):
        self.sensitivity = sensitivity
        self.min_area = min_area
        self.prev_gray = None

    def detect(self, frame) -> bool:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_gray is None:
            self.prev_gray = gray
            return False

        frame_delta = cv2.absdiff(self.prev_gray, gray)
        thresh_value = int(30 * (1.0 - self.sensitivity) + 5)
        _, thresh = cv2.threshold(frame_delta, thresh_value, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(
            thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        self.prev_gray = gray

        for c in contours:
            if cv2.contourArea(c) >= self.min_area:
                logger.info("Motion detected.")
                return True
        return False
