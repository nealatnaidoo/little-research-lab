"""
Settings component port definitions.

Spec refs: E1.1
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.core.entities import SiteSettings


class SettingsRepoPort(Protocol):
    """Repository interface for settings."""

    def get(self) -> SiteSettings | None:
        """Get current settings, or None if not configured."""
        ...

    def save(self, settings: SiteSettings) -> SiteSettings:
        """Save or update settings (upsert)."""
        ...


class CacheInvalidatorPort(Protocol):
    """Cache invalidation hook for R6 compliance."""

    def invalidate_settings(self) -> None:
        """Invalidate cached settings across SSR."""
        ...


class TimePort(Protocol):
    """Port for time operations."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...
