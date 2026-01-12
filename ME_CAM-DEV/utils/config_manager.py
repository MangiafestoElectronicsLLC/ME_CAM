import json
import os
from threading import Lock

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
}

_config_cache = None
_config_lock = Lock()


def _ensure_config_file():
    global _config_cache
    if not os.path.exists(CONFIG_PATH):
        logger.info(f"[CONFIG] Creating default config at {CONFIG_PATH}")
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(_default_config, f, indent=2)
        _config_cache = _default_config.copy()
    else:
        if _config_cache is None:
            with open(CONFIG_PATH, "r") as f:
                try:
                    data = json.load(f)
                except Exception:
                    logger.warning("[CONFIG] Failed to load config.json, resetting to defaults")
                    data = _default_config.copy()
            # Merge defaults with existing
            merged = _default_config.copy()
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
