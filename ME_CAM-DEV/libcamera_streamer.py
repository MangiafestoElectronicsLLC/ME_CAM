import subprocess
import threading
import time
from typing import Generator, Optional

class LibcameraMJPEGStreamer:
    """
    Wraps libcamera-vid to provide an MJPEG frame generator.

    Uses a subprocess:
      libcamera-vid -t 0 --inline --codec mjpeg --width W --height H --framerate FPS -o -

    Then parses the MJPEG stream and yields frames suitable for Flask MJPEG endpoints.
    """

    def __init__(self, width: int = 1536, height: int = 864, fps: int = 15):
        self.width = width
        self.height = height
        self.fps = fps

        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._running = False

    def _build_command(self):
        return [
            "libcamera-vid",
            "-t", "0",
            "--inline",
            "--codec", "mjpeg",
            "--width", str(self.width),
            "--height", str(self.height),
            "--framerate", str(self.fps),
            "-o", "-"
        ]

    def _reader_loop(self):
        """
        Reads from libcamera-vid stdout, accumulates MJPEG frames.
        """
        if not self._process or not self._process.stdout:
            return

        SOI = b"\xff\xd8"  # Start Of Image
        EOI = b"\xff\xd9"  # End Of Image

        while self._running:
            chunk = self._process.stdout.read(1024)
            if not chunk:
                break

            with self._lock:
                self._buffer.extend(chunk)
                # Try to extract complete JPEGs
                while True:
                    start = self._buffer.find(SOI)
                    if start == -1:
                        # no start marker yet
                        self._buffer.clear()
                        break
                    end = self._buffer.find(EOI, start + 2)
                    if end == -1:
                        # no end marker yet, keep data
                        if start > 0:
                            # discard leading garbage
                            del self._buffer[:start]
                        break
                    # We found a full JPEG
                    frame = self._buffer[start:end+2]
                    # Remove this frame from buffer
                    del self._buffer[:end+2]
                    # Store latest frame in a dedicated attribute
                    self._latest_frame = frame

        # Clean up if process exits
        self.stop()

    def start(self):
        """
        Starts libcamera-vid and reader thread if not already running.
        """
        if self._running:
            return

        self._running = True
        cmd = self._build_command()
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0
        )
        self._latest_frame: Optional[bytes] = None
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """
        Stops the reader thread and libcamera-vid process.
        """
        self._running = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=2)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
        self._process = None
        self._thread = None

    def restart(self, width: Optional[int] = None, height: Optional[int] = None, fps: Optional[int] = None):
        """
        Restart with new resolution/fps if provided.
        """
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height
        if fps is not None:
            self.fps = fps

        self.stop()
        time.sleep(0.5)
        self.start()

    def frames(self) -> Generator[bytes, None, None]:
        """
        Generator that yields the latest MJPEG frame.
        If no frame is yet available, it waits briefly.
        """
        self.start()
        while True:
            frame = getattr(self, "_latest_frame", None)
            if frame:
                yield frame
            else:
                time.sleep(0.05)
