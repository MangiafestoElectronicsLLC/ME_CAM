import subprocess
import time
from loguru import logger
import os

class LibcameraStreamer:
    """Stream video using libcamera (native Raspberry Pi camera support)."""
    
    def __init__(self):
        self.jpeg_dir = "/tmp/libcamera_frames"
        os.makedirs(self.jpeg_dir, exist_ok=True)
    
    def get_single_frame_jpeg(self):
        """Capture single JPEG frame - more reliable than video streaming."""
        try:
            output_path = f"{self.jpeg_dir}/frame.jpg"
            cmd = [
                "libcamera-still",
                "--width", "640",
                "--height", "480",
                "-o", output_path,
                "--nopreview",
                "-t", "500"  # Timeout in ms
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=3)
            if result.returncode == 0 and os.path.exists(output_path):
                with open(output_path, 'rb') as f:
                    jpeg_data = f.read()
                return jpeg_data
            else:
                logger.warning(f"[CAMERA] libcamera-still failed: {result.stderr.decode()}")
                return None
        except subprocess.TimeoutExpired:
            logger.warning("[CAMERA] libcamera-still timeout")
            return None
        except Exception as e:
            logger.warning(f"[CAMERA] Frame capture error: {e}")
            return None

def is_libcamera_available():
    """Check if libcamera is available."""
    try:
        result = subprocess.run(["which", "libcamera-still"], capture_output=True)
        return result.returncode == 0
    except:
        return False

