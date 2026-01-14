from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Protocol

from src.rules.models import RateLimitRules


class TimePort(Protocol):
    """Protocol for time operations (enables testing with deterministic time)."""

    def now(self) -> datetime:
        """Return current UTC time."""
        ...


class SystemTimeAdapter:
    """Production time adapter using system clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class RateLimiter:
    def __init__(
        self,
        rules: RateLimitRules,
        time_port: TimePort | None = None,
    ):
        self.rules = rules
        self._time = time_port if time_port is not None else SystemTimeAdapter()
        self._history: dict[str, list[datetime]] = {}
        self._lock = Lock()

    def _cleanup(self, key: str, window: int) -> None:
        now = self._time.now()
        cutoff = now - timedelta(seconds=window)
        if key in self._history:
            self._history[key] = [t for t in self._history[key] if t > cutoff]
            if not self._history[key]:
                del self._history[key]

    def allow_request(self, key: str, window: int, limit: int) -> bool:
        """
        Check if request is allowed.
        If allowed, records the attempt and returns True.
        If denied, returns False.
        """
        if limit <= 0:
            return False

        with self._lock:
            self._cleanup(key, window)
            current_count = len(self._history.get(key, []))

            if current_count >= limit:
                return False

            if key not in self._history:
                self._history[key] = []
            self._history[key].append(self._time.now())
            return True

    def check_login(self, ip: str) -> bool:
        cfg = self.rules.login
        limit = cfg.max_attempts if cfg.max_attempts is not None else 5

        return self.allow_request(f"login:{ip}", cfg.window_seconds, limit)

    def check_upload(self, user_id: str) -> bool:
        cfg = self.rules.upload
        limit = cfg.max_requests if cfg.max_requests is not None else 100

        return self.allow_request(f"upload:{user_id}", cfg.window_seconds, limit)
