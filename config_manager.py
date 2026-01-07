import json
import os
from threading import RLock

CONFIG_PATH = "config/config.json"
DEFAULT_CONFIG_PATH = "config/config_default.json"

_lock = RLock()
_config_cache = None


def _load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def get_config():
    global _config_cache
    with _lock:
        if _config_cache is None:
            os.makedirs("config", exist_ok=True)
            if not os.path.exists(CONFIG_PATH):
                default = _load_json(DEFAULT_CONFIG_PATH)
                with open(CONFIG_PATH, "w") as f:
                    json.dump(default, f, indent=2)
                _config_cache = default
            else:
                _config_cache = _load_json(CONFIG_PATH)
        return _config_cache


def save_config(new_config: dict):
    global _config_cache
    with _lock:
        os.makedirs("config", exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(new_config, f, indent=2)
        _config_cache = new_config


def update_config(updates: dict):
    cfg = get_config()
    cfg.update(updates)
    save_config(cfg)


def is_first_run():
    cfg = get_config()
    return not cfg.get("first_run_completed", False)


def mark_first_run_complete():
    cfg = get_config()
    cfg["first_run_completed"] = True
    save_config(cfg)
