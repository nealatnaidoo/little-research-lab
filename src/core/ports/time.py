"""
v3 Time/Timezone Adapter Interface (P3).

Protocol-based interface for time operations.
Provides DST-safe time handling for Europe/London timezone.

Spec refs: P3, E5, TA-0027
Test assertions: TA-0027 (DST boundary cases)

Key requirements:
- Scheduling uses Europe/London timezone for display
- Storage uses UTC for all timestamps
- DST transitions must be handled correctly
- Scheduled content must never publish early (G3)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol


class TimePort(Protocol):
    """
    Time/Timezone adapter interface.

    All internal timestamps are stored in UTC.
    Display timezone is configurable (default: Europe/London).
    """

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...

    def now_local(self) -> datetime:
        """Get current time in display timezone."""
        ...

    def to_utc(self, local_dt: datetime) -> datetime:
        """
        Convert local time to UTC.

        Handles DST ambiguity by preferring standard time (later offset).

        Args:
            local_dt: Datetime in local timezone (naive or aware)

        Returns:
            Datetime in UTC (timezone-aware)
        """
        ...

    def to_local(self, utc_dt: datetime) -> datetime:
        """
        Convert UTC to local time.

        Args:
            utc_dt: Datetime in UTC (naive treated as UTC)

        Returns:
            Datetime in local timezone (timezone-aware)
        """
        ...

    def format_local(self, utc_dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
        """
        Format UTC datetime in local timezone.

        Args:
            utc_dt: Datetime in UTC
            fmt: strftime format string

        Returns:
            Formatted datetime string in local timezone
        """
        ...

    def parse_local(self, date_str: str, fmt: str = "%Y-%m-%d %H:%M") -> datetime:
        """
        Parse datetime string as local time and convert to UTC.

        Args:
            date_str: Datetime string in local timezone
            fmt: strftime format string

        Returns:
            Datetime in UTC (timezone-aware)
        """
        ...

    def is_future(self, utc_dt: datetime, grace_seconds: int = 0) -> bool:
        """
        Check if datetime is in the future (with optional grace period).

        Used for scheduling validation (G2).

        Args:
            utc_dt: Datetime to check (UTC)
            grace_seconds: Allow this many seconds in the past

        Returns:
            True if datetime is in the future (or within grace period)
        """
        ...

    def is_past_or_now(self, utc_dt: datetime) -> bool:
        """
        Check if datetime is at or before now.

        Used for publish job execution (G3 - never publish early).

        Args:
            utc_dt: Datetime to check (UTC)

        Returns:
            True if datetime is at or before current time
        """
        ...

    @property
    def timezone_name(self) -> str:
        """Get the display timezone name (e.g., 'Europe/London')."""
        ...

    def get_dst_info(self, utc_dt: datetime) -> tuple[bool, timedelta]:
        """
        Get DST information for a datetime.

        Args:
            utc_dt: Datetime in UTC

        Returns:
            Tuple of (is_dst, utc_offset)
        """
        ...
