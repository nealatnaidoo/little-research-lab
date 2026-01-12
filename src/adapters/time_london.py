"""
Europe/London Time Adapter (P3 Implementation).

Implements the TimePort interface for Europe/London timezone.
Provides DST-safe time handling for scheduling.

Spec refs: P3, E5, TA-0027
Test assertions: TA-0027 (DST boundary cases)

Key behaviors:
- now_utc: Returns current UTC time
- to_utc: Converts Europe/London time to UTC (DST-aware)
- to_local: Converts UTC to Europe/London time
- DST transitions handled correctly
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Python < 3.9 fallback
    from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]


class LondonTimeAdapter:
    """
    Time adapter for Europe/London timezone.

    Handles BST (British Summer Time) / GMT transitions correctly.
    """

    def __init__(self, tz_name: str = "Europe/London") -> None:
        """
        Initialize with specified timezone.

        Args:
            tz_name: IANA timezone name (default: Europe/London)
        """
        self._tz_name = tz_name
        self._tz = ZoneInfo(tz_name)
        self._utc = UTC

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        return datetime.now(self._utc)

    def now_local(self) -> datetime:
        """Get current time in Europe/London."""
        return datetime.now(self._tz)

    def to_utc(self, local_dt: datetime) -> datetime:
        """
        Convert Europe/London time to UTC.

        If local_dt is naive, it's assumed to be in Europe/London.
        If local_dt is aware, it's converted to UTC.

        For DST-ambiguous times (when clocks go back), prefers standard time
        (the later occurrence, which has the smaller UTC offset).
        """
        if local_dt.tzinfo is None:
            # Naive datetime - assume Europe/London
            # For ambiguous times, fold=1 selects the standard time (later)
            local_dt = local_dt.replace(tzinfo=self._tz)

        return local_dt.astimezone(self._utc)

    def to_local(self, utc_dt: datetime) -> datetime:
        """
        Convert UTC to Europe/London time.

        If utc_dt is naive, it's assumed to be UTC.
        """
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=self._utc)

        return utc_dt.astimezone(self._tz)

    def format_local(self, utc_dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
        """Format UTC datetime in Europe/London timezone."""
        local_dt = self.to_local(utc_dt)
        return local_dt.strftime(fmt)

    def parse_local(self, date_str: str, fmt: str = "%Y-%m-%d %H:%M") -> datetime:
        """
        Parse datetime string as Europe/London time and convert to UTC.

        For DST-ambiguous times, prefers standard time (later occurrence).
        """
        # Parse as naive
        naive_dt = datetime.strptime(date_str, fmt)
        # Localize to Europe/London (fold=1 for standard time preference)
        local_dt = naive_dt.replace(tzinfo=self._tz, fold=1)
        return local_dt.astimezone(self._utc)

    def is_future(self, utc_dt: datetime, grace_seconds: int = 0) -> bool:
        """
        Check if datetime is in the future (with optional grace period).

        Used for scheduling validation (G2: publish_at must be in future).

        Args:
            utc_dt: Datetime to check (UTC)
            grace_seconds: Allow this many seconds in the past (default 0)

        Returns:
            True if datetime is more than grace_seconds in the past
        """
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=self._utc)

        now = self.now_utc()
        threshold = now - timedelta(seconds=grace_seconds)
        return utc_dt > threshold

    def is_past_or_now(self, utc_dt: datetime) -> bool:
        """
        Check if datetime is at or before now.

        Used for publish job execution (G3: never publish early).

        Args:
            utc_dt: Datetime to check (UTC)

        Returns:
            True if datetime is at or before current time
        """
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=self._utc)

        return utc_dt <= self.now_utc()

    @property
    def timezone_name(self) -> str:
        """Get the display timezone name."""
        return self._tz_name

    def get_dst_info(self, utc_dt: datetime) -> tuple[bool, timedelta]:
        """
        Get DST information for a datetime.

        Returns:
            Tuple of (is_dst, utc_offset)
            - is_dst: True if datetime is during daylight saving time
            - utc_offset: Offset from UTC (positive for east of UTC)
        """
        local_dt = self.to_local(utc_dt)
        offset = local_dt.utcoffset() or timedelta(0)

        # Europe/London: UTC+0 in winter (GMT), UTC+1 in summer (BST)
        is_dst = offset > timedelta(0)
        return is_dst, offset


class FrozenTimeAdapter:
    """
    Time adapter that returns a fixed time.

    Useful for deterministic testing.
    """

    def __init__(
        self,
        frozen_utc: datetime,
        tz_name: str = "Europe/London",
    ) -> None:
        """
        Initialize with frozen time.

        Args:
            frozen_utc: The UTC time to return from now_utc()
            tz_name: IANA timezone name for local conversions
        """
        self._frozen_utc = frozen_utc.replace(tzinfo=UTC)
        self._tz_name = tz_name
        self._tz = ZoneInfo(tz_name)
        self._utc = UTC

    def now_utc(self) -> datetime:
        """Get frozen UTC time."""
        return self._frozen_utc

    def now_local(self) -> datetime:
        """Get frozen time in local timezone."""
        return self._frozen_utc.astimezone(self._tz)

    def to_utc(self, local_dt: datetime) -> datetime:
        """Convert local time to UTC."""
        if local_dt.tzinfo is None:
            local_dt = local_dt.replace(tzinfo=self._tz)
        return local_dt.astimezone(self._utc)

    def to_local(self, utc_dt: datetime) -> datetime:
        """Convert UTC to local time."""
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=self._utc)
        return utc_dt.astimezone(self._tz)

    def format_local(self, utc_dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
        """Format UTC datetime in local timezone."""
        return self.to_local(utc_dt).strftime(fmt)

    def parse_local(self, date_str: str, fmt: str = "%Y-%m-%d %H:%M") -> datetime:
        """Parse datetime string as local time and convert to UTC."""
        naive_dt = datetime.strptime(date_str, fmt)
        local_dt = naive_dt.replace(tzinfo=self._tz, fold=1)
        return local_dt.astimezone(self._utc)

    def is_future(self, utc_dt: datetime, grace_seconds: int = 0) -> bool:
        """Check if datetime is in the future."""
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=self._utc)
        threshold = self._frozen_utc - timedelta(seconds=grace_seconds)
        return utc_dt > threshold

    def is_past_or_now(self, utc_dt: datetime) -> bool:
        """Check if datetime is at or before frozen time."""
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=self._utc)
        return utc_dt <= self._frozen_utc

    @property
    def timezone_name(self) -> str:
        """Get the display timezone name."""
        return self._tz_name

    def get_dst_info(self, utc_dt: datetime) -> tuple[bool, timedelta]:
        """Get DST information for a datetime."""
        local_dt = self.to_local(utc_dt)
        offset = local_dt.utcoffset() or timedelta(0)
        is_dst = offset > timedelta(0)
        return is_dst, offset

    def advance(self, delta: timedelta) -> None:
        """Advance frozen time by delta (for testing)."""
        self._frozen_utc = self._frozen_utc + delta


def create_time_adapter(tz_name: str = "Europe/London") -> LondonTimeAdapter:
    """Factory function to create a time adapter."""
    return LondonTimeAdapter(tz_name)
