"""
AnalyticsDedupeService (E6.3) - Event deduplication and bot classification.

Handles duplicate event detection and user agent classification.

Spec refs: E6.3, TA-0039, TA-0040
Test assertions:
- TA-0039: Duplicate events are detected and filtered
- TA-0040: Bot classification based on user agent patterns

Key behaviors:
- Dedupe within configurable TTL window (default 10s)
- Classify user agents as bot/real/unknown
- Exclude bot traffic from real counts
- Privacy-preserving (no raw UA storage)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Protocol

# --- Enums ---


class UAClass(str, Enum):
    """User agent classification."""

    BOT = "bot"
    REAL = "real"
    UNKNOWN = "unknown"


# --- Configuration ---


@dataclass(frozen=True)
class DedupeConfig:
    """Deduplication configuration."""

    enabled: bool = True
    ttl_seconds: int = 10

    # Bot classification
    treat_unknown_as: str = "real"
    exclude_bots_from_counts: bool = True

    # Bot detection patterns (common bot user agent substrings)
    bot_patterns: tuple[str, ...] = (
        "bot",
        "crawler",
        "spider",
        "scraper",
        "wget",
        "curl",
        "python-requests",
        "go-http-client",
        "java/",
        "libwww",
        "httpclient",
        "ahrefsbot",
        "bingbot",
        "googlebot",
        "yandexbot",
        "baiduspider",
        "duckduckbot",
        "slurp",
        "facebookexternalhit",
        "linkedinbot",
        "twitterbot",
        "applebot",
        "semrushbot",
        "mj12bot",
        "dotbot",
        "petalbot",
        "bytespider",
        "gptbot",
        "claudebot",
        "anthropic",
    )

    # Real browser patterns (must match for "real" classification)
    real_browser_patterns: tuple[str, ...] = (
        "mozilla/5.0",
        "chrome/",
        "firefox/",
        "safari/",
        "edge/",
        "opera/",
        "msie",
        "trident/",
    )


DEFAULT_CONFIG = DedupeConfig()


# --- Dedupe Key Generation ---


def generate_dedupe_key(
    event_type: str,
    path: str | None = None,
    content_id: str | None = None,
    asset_id: str | None = None,
    timestamp_bucket: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """
    Generate a dedupe key for an event.

    Key is based on event characteristics within a time bucket.
    Does NOT include any PII (IP, cookies, etc.).
    """
    parts = [
        event_type or "",
        path or "",
        content_id or "",
        asset_id or "",
        timestamp_bucket or "",
    ]

    if extra:
        for key in sorted(extra.keys()):
            parts.append(f"{key}:{extra[key]}")

    key_string = "|".join(parts)
    return hashlib.sha256(key_string.encode()).hexdigest()[:32]


def get_timestamp_bucket(
    timestamp: datetime,
    bucket_seconds: int = 10,
) -> str:
    """
    Get a timestamp bucket for deduplication.

    Events in the same bucket are candidates for deduplication.
    """
    epoch = timestamp.timestamp()
    bucket = int(epoch // bucket_seconds) * bucket_seconds
    return str(bucket)


# --- Bot Classification ---


def classify_user_agent(
    user_agent: str | None,
    config: DedupeConfig = DEFAULT_CONFIG,
) -> UAClass:
    """
    Classify a user agent string (TA-0040).

    Returns BOT, REAL, or UNKNOWN based on patterns.
    """
    if not user_agent:
        return UAClass.UNKNOWN

    ua_lower = user_agent.lower()

    # Check for bot patterns first (they take priority)
    for pattern in config.bot_patterns:
        if pattern in ua_lower:
            return UAClass.BOT

    # Check for real browser patterns
    for pattern in config.real_browser_patterns:
        if pattern in ua_lower:
            return UAClass.REAL

    return UAClass.UNKNOWN


def is_bot(ua_class: UAClass, config: DedupeConfig = DEFAULT_CONFIG) -> bool:
    """Check if UA class should be treated as a bot."""
    if ua_class == UAClass.BOT:
        return True
    if ua_class == UAClass.UNKNOWN and config.treat_unknown_as == "bot":
        return True
    return False


def should_count(ua_class: UAClass, config: DedupeConfig = DEFAULT_CONFIG) -> bool:
    """Check if event should be counted in real metrics."""
    if not config.exclude_bots_from_counts:
        return True
    return not is_bot(ua_class, config)


# --- Dedupe Store Protocol ---


class DedupeStorePort(Protocol):
    """Dedupe store interface."""

    def exists(self, key: str) -> bool:
        """Check if key exists (not expired)."""
        ...

    def add(self, key: str, ttl_seconds: int) -> bool:
        """Add key with TTL. Returns True if added (new), False if exists."""
        ...

    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count removed."""
        ...


# --- In-Memory Dedupe Store ---


class InMemoryDedupeStore:
    """In-memory dedupe store for testing/dev."""

    def __init__(self) -> None:
        self._entries: dict[str, datetime] = {}

    def exists(self, key: str) -> bool:
        """Check if key exists and not expired."""
        if key not in self._entries:
            return False

        expires_at = self._entries[key]
        if datetime.now(UTC) > expires_at:
            del self._entries[key]
            return False

        return True

    def add(self, key: str, ttl_seconds: int) -> bool:
        """Add key with TTL. Returns True if new."""
        if self.exists(key):
            return False

        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        self._entries[key] = expires_at
        return True

    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        now = datetime.now(UTC)
        expired = [k for k, v in self._entries.items() if now > v]
        for key in expired:
            del self._entries[key]
        return len(expired)

    def clear(self) -> None:
        """Clear all entries (for testing)."""
        self._entries.clear()


# --- Dedupe Result ---


@dataclass
class DedupeResult:
    """Result of dedupe check."""

    is_duplicate: bool
    dedupe_key: str
    ua_class: UAClass
    should_count: bool


# --- Dedupe Service ---


class DedupeService:
    """
    Deduplication service (E6.3).

    Detects duplicate events and classifies user agents.
    """

    def __init__(
        self,
        store: DedupeStorePort | None = None,
        config: DedupeConfig | None = None,
    ) -> None:
        """Initialize service."""
        self._store = store or InMemoryDedupeStore()
        self._config = config or DEFAULT_CONFIG

    def check_and_record(
        self,
        event_type: str,
        timestamp: datetime,
        user_agent: str | None = None,
        path: str | None = None,
        content_id: str | None = None,
        asset_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> DedupeResult:
        """
        Check if event is duplicate and record it (TA-0039).

        Returns DedupeResult with duplicate status and classification.
        """
        # Classify user agent
        ua_class = classify_user_agent(user_agent, self._config)

        # Generate dedupe key
        bucket = get_timestamp_bucket(timestamp, self._config.ttl_seconds)
        key = generate_dedupe_key(
            event_type=event_type,
            path=path,
            content_id=content_id,
            asset_id=asset_id,
            timestamp_bucket=bucket,
            extra=extra,
        )

        # Check for duplicate
        is_duplicate = False
        if self._config.enabled:
            # add() returns True if new, False if exists
            is_new = self._store.add(key, self._config.ttl_seconds)
            is_duplicate = not is_new

        return DedupeResult(
            is_duplicate=is_duplicate,
            dedupe_key=key,
            ua_class=ua_class,
            should_count=should_count(ua_class, self._config),
        )

    def classify(self, user_agent: str | None) -> UAClass:
        """Classify a user agent (TA-0040)."""
        return classify_user_agent(user_agent, self._config)

    def should_count(self, ua_class: UAClass) -> bool:
        """Check if UA class should be counted."""
        return should_count(ua_class, self._config)

    def cleanup(self) -> int:
        """Cleanup expired dedupe entries."""
        return self._store.cleanup_expired()


# --- Factory ---


def create_dedupe_service(
    store: DedupeStorePort | None = None,
    config: DedupeConfig | None = None,
) -> DedupeService:
    """Create a DedupeService."""
    return DedupeService(store=store, config=config)
