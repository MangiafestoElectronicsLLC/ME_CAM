import threading
import time
from typing import Generator, Optional

from utils.logger import get_logger
from utils.config_manager import get_config
from motion_detector import MotionDetector
from libcamera_streamer import LibcameraMJPEGStreamer

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
        self._running = False

        self._load_stream_config()

    def _load_stream_config(self):
        config = get_config()
        resolution = config.get("stream_resolution", "1536x864")
        fps = int(config.get("stream_fps", 15))

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
            # Optionally run motion detection here on the JPEG frame if needed
            # self._motion_detector.process_frame(...)
            yield frame
