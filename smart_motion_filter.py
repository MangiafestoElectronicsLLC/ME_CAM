from collections import deque
import time


class SmartMotionFilter:
    def __init__(self, window_seconds: float = 5.0, min_events: int = 2):
        self.window_seconds = window_seconds
        self.min_events = min_events
        self.events = deque()

    def register_motion(self) -> bool:
        now = time.time()
        self.events.append(now)

        while self.events and now - self.events[0] > self.window_seconds:
            self.events.popleft()

        return len(self.events) >= self.min_events
