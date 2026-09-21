import time
import threading
from typing import Dict, List, Tuple
from fastapi import Request

from app.core.config import (
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_AUTH_PER_MINUTE,
    RATE_LIMIT_INFERENCE_PER_MINUTE,
    RATE_LIMIT_DEFAULT_PER_MINUTE,
)


class InMemoryRateLimiter:
    """
    Lightweight, low-memory sliding-window rate limiter.
    Uses pure Python collections with periodic garbage collection
    to maintain minimal RAM usage (~512 MB target environment).
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Mapping: (client_ip, category) -> list of request timestamps (float)
        self._hits: Dict[Tuple[str, str], List[float]] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 300.0  # Clean every 5 minutes

    def _cleanup_stale_records(self, now: float) -> None:
        """
        Removes entries older than 60 seconds to prevent memory leak.
        """
        stale_cutoff = now - 60.0
        keys_to_delete = []
        for key, timestamps in self._hits.items():
            fresh_timestamps = [t for t in timestamps if t > stale_cutoff]
            if fresh_timestamps:
                self._hits[key] = fresh_timestamps
            else:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del self._hits[key]
        self._last_cleanup = now

    def is_allowed(self, client_ip: str, category: str) -> Tuple[bool, int]:
        """
        Checks if the request from client_ip for category is within limits.
        Returns (is_allowed: bool, retry_after_seconds: int).
        """
        if not RATE_LIMIT_ENABLED:
            return True, 0

        # Resolve limit for category
        if category == "auth":
            limit = RATE_LIMIT_AUTH_PER_MINUTE
        elif category == "inference":
            limit = RATE_LIMIT_INFERENCE_PER_MINUTE
        else:
            limit = RATE_LIMIT_DEFAULT_PER_MINUTE

        if limit <= 0:
            return True, 0

        now = time.time()
        window_start = now - 60.0
        key = (client_ip, category)

        with self._lock:
            # Periodic cleanup
            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup_stale_records(now)

            timestamps = self._hits.get(key, [])
            # Filter timestamps within the 60s sliding window
            valid_timestamps = [t for t in timestamps if t > window_start]

            if len(valid_timestamps) >= limit:
                # Calculate retry-after as the remaining time on the oldest hit in the window
                oldest = valid_timestamps[0]
                retry_after = max(1, int(60.0 - (now - oldest)))
                self._hits[key] = valid_timestamps
                return False, retry_after

            # Add current hit
            valid_timestamps.append(now)
            self._hits[key] = valid_timestamps
            return True, 0

    @staticmethod
    def get_category_for_path(path: str) -> str:
        """
        Categorizes request path to determine rate limit tier.
        """
        if path.startswith("/api/auth"):
            return "auth"
        elif path.startswith("/api/v1/inference") or path.startswith("/api/scans"):
            return "inference"
        return "default"


rate_limiter = InMemoryRateLimiter()
