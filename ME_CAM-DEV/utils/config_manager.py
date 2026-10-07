import json
import os
from threading import Lock

from hardware_profile import get_camera_profile
from utils.logger import get_logger

logger = get_logger("config_manager")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "config.json")
CONFIG_PATH = os.path.abspath(CONFIG_PATH)

_default_config = {
    "device_name": "ME_CAM",
    "admin_email": "",
    "motion_sensitivity": 0.5,
    "stream_resolution": "1536x864",
    "stream_fps": 15,
    "face_recognition_enabled": False,
}

_config_cache = None
_config_lock = Lock()


def _get_default_config():
    defaults = _default_config.copy()
    profile = get_camera_profile()
    defaults["stream_resolution"] = profile["resolution"]
    defaults["stream_fps"] = profile["fps"]
    defaults["face_recognition_enabled"] = profile["face_recognition"]
    return defaults


def _ensure_config_file():
    global _config_cache
    if not os.path.exists(CONFIG_PATH):
        logger.info(f"[CONFIG] Creating default config at {CONFIG_PATH}")
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        defaults = _get_default_config()
        with open(CONFIG_PATH, "w") as f:
            json.dump(defaults, f, indent=2)
        _config_cache = defaults
    else:
        if _config_cache is None:
            with open(CONFIG_PATH, "r") as f:
                try:
                    data = json.load(f)
                except Exception:
                    logger.warning("[CONFIG] Failed to load config.json, resetting to defaults")
                    data = _get_default_config()
            # Merge defaults with existing
            merged = _get_default_config()
            merged.update(data)
            _config_cache = merged


def get_config():
    with _config_lock:
        _ensure_config_file()
        return _config_cache.copy()


def save_config(new_config: dict):
    with _config_lock:
        _ensure_config_file()
        merged = _config_cache.copy()
        merged.update(new_config)

        # Ensure required keys exist
        for k, v in _default_config.items():
            merged.setdefault(k, v)

        with open(CONFIG_PATH, "w") as f:
            json.dump(merged, f, indent=2)

        _config_cache.update(merged)
        logger.info("[CONFIG] Configuration saved.")
