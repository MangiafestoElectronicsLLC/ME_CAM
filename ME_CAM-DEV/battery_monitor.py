import subprocess
from utils.logger import get_logger
from config_manager import get_config

logger = get_logger("battery_monitor")


class BatteryMonitor:
    def __init__(self, enabled: bool = False, low_threshold_percent: int = 20):
        self.enabled = enabled
        self.low_threshold_percent = low_threshold_percent

    def _vcgencmd_throttled(self):
        try:
            out = subprocess.check_output(["vcgencmd", "get_throttled"], text=True).strip()
            # Example: 'throttled=0x50000'
            if "=" in out:
                _, hexval = out.split("=", 1)
                val = int(hexval, 16)
                return val
        except Exception as e:
            logger.debug(f"vcgencmd not available or failed: {e}")
        return 0

    def get_status(self):
        if not self.enabled:
            return {"enabled": False, "percent": None, "is_low": False, "external_power": None}

        cfg = get_config()
        percent_override = cfg.get("battery_percent_override")

        throttled = self._vcgencmd_throttled()
        undervolt_now = bool(throttled & 0x1)
        undervolt_ever = bool(throttled & 0x10000)

        # With generic USB power banks, exact % isn't available without a HAT/ADC.
        # If user provides override in config, use it; otherwise None.
        percent = None
        if isinstance(percent_override, (int, float)):
            percent = int(percent_override)

        is_low = undervolt_now or (percent is not None and percent <= self.low_threshold_percent)
        external_power = not undervolt_now  # heuristic: if no undervolt, likely adequate external power

        return {
            "enabled": True,
            "percent": percent,
            "is_low": is_low,
            "external_power": external_power,
            "undervolt_ever": undervolt_ever
        }
