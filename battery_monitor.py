from utils.logger import get_logger

logger = get_logger("battery_monitor")


class BatteryMonitor:
    def __init__(self, enabled: bool = False, low_threshold_percent: int = 20):
        self.enabled = enabled
        self.low_threshold_percent = low_threshold_percent

    def get_status(self):
        if not self.enabled:
            return {"enabled": False, "percent": None, "is_low": False}

        # TODO: implement real hardware read
        # For now, stub:
        percent = 76
        is_low = percent <= self.low_threshold_percent
        return {"enabled": True, "percent": percent, "is_low": is_low}
