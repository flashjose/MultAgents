from __future__ import annotations

from collections import defaultdict
from threading import Lock
from time import monotonic, sleep
from urllib.parse import urlparse


class HostRateLimiter:
    def __init__(self, min_interval_seconds: float) -> None:
        self.min_interval_seconds = min_interval_seconds
        self._last_request_at: dict[str, float] = defaultdict(float)
        self._lock = Lock()

    def wait_for_slot(self, url: str) -> None:
        host = urlparse(url).netloc or "default"
        with self._lock:
            now = monotonic()
            elapsed = now - self._last_request_at[host]
            wait_seconds = max(0.0, self.min_interval_seconds - elapsed)
            if wait_seconds:
                sleep(wait_seconds)
            self._last_request_at[host] = monotonic()
