import threading
import time
from threading import Event
from utils.logger import get_logger
from camera_pipeline import CameraPipeline

logger = get_logger("watchdog")


class CameraWatchdog:
    def __init__(self):
        self.stop_event = Event()
        self.thread = None

    def _run_pipeline(self):
        pipeline = CameraPipeline(self.stop_event)
        pipeline.run()

    def start(self):
        logger.info("Starting camera pipeline.")
        self.thread = threading.Thread(target=self._run_pipeline, daemon=True)
        self.thread.start()

    def stop(self):
        logger.info("Stopping camera pipeline.")
        self.stop_event.set()
        if self.thread:
            self.thread.join()

    def status(self):
        """Return pipeline status"""
        return {
            "active": self.thread and self.thread.is_alive(),
            "timestamp": time.time()
        }

    def supervise(self):
        self.start()
        while not self.stop_event.is_set():
            if not self.thread.is_alive():
                logger.warning("Camera pipeline crashed, restarting.")
                self.stop_event.clear()
                self.start()
            time.sleep(5)
