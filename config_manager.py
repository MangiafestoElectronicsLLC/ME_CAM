import json
import os
import hashlib
from typing import Any, Dict
from utils.logger import get_logger

logger = get_logger("config_manager")

CONFIG_DIR = "config"
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, "config_default.json")


def _ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config() -> Dict[str, Any]:
    _ensure_config_dir()
    if not os.path.exists(CONFIG_PATH):
        logger.info("Config not found, creating from default.")
        reset_to_default()
    with open(CONFIG_PATH, "r") as f:
        data = json.load(f)
    return data


def save_config(config: Dict[str, Any]) -> None:
    _ensure_config_dir()
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)
    logger.info("Config saved.")


def reset_to_default() -> None:
    _ensure_config_dir()
    if not os.path.exists(DEFAULT_CONFIG_PATH):
        raise FileNotFoundError("Default config file missing.")
    with open(DEFAULT_CONFIG_PATH, "r") as f:
        default = json.load(f)
    with open(CONFIG_PATH, "w") as f:
        json.dump(default, f, indent=4)
    logger.info("Config reset to default.")


def export_config(export_path: str) -> None:
    config = load_config()
    with open(export_path, "w") as f:
        json.dump(config, f, indent=4)
    logger.info(f"Config exported to {export_path}")


def import_config(import_path: str) -> None:
    with open(import_path, "r") as f:
        config = json.load(f)
    save_config(config)
    logger.info(f"Config imported from {import_path}")


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def set_dashboard_pin(pin: str) -> None:
    config = load_config()
    config["dashboard_pin_hash"] = hash_pin(pin)
    save_config(config)


def verify_dashboard_pin(pin: str) -> bool:
    config = load_config()
    stored = config.get("dashboard_pin_hash", "")
    if not stored:
        return False
    return stored == hash_pin(pin)
