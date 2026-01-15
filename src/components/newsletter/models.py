"""
Newsletter component models (C10).

Data models for newsletter subscription management.

Spec refs: E16.1, E16.2, E16.3
State machine: SM3 (Subscriber: pending → confirmed → unsubscribed)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

# --- State Machine SM3 ---


class SubscriberStatus(Enum):
    """
    Newsletter subscriber status (SM3).

    State transitions:
    - pending → confirmed (via confirmation link)
    - confirmed → unsubscribed (via unsubscribe link)
    - pending → (deleted) (if never confirmed)
    """

    PENDING = "pending"  # Awaiting email confirmation
    CONFIRMED = "confirmed"  # Email confirmed, active subscriber
    UNSUBSCRIBED = "unsubscribed"  # User unsubscribed


# Valid state transitions
VALID_TRANSITIONS: dict[SubscriberStatus, set[SubscriberStatus]] = {
    SubscriberStatus.PENDING: {SubscriberStatus.CONFIRMED},
    SubscriberStatus.CONFIRMED: {SubscriberStatus.UNSUBSCRIBED},
    SubscriberStatus.UNSUBSCRIBED: set(),  # Terminal state
}


def can_transition(from_status: SubscriberStatus, to_status: SubscriberStatus) -> bool:
    """Check if state transition is valid according to SM3."""
    return to_status in VALID_TRANSITIONS.get(from_status, set())


# --- Entity ---


@dataclass
class NewsletterSubscriber:
    """
    Newsletter subscriber entity (E9).

    Stores subscription state and tokens for double opt-in flow.
    """

    id: UUID
    email: str
    status: SubscriberStatus = SubscriberStatus.PENDING
    confirmation_token: str | None = None  # One-time confirmation token
    unsubscribe_token: str | None = None  # Permanent unsubscribe token
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    confirmed_at: datetime | None = None
    unsubscribed_at: datetime | None = None


# --- Input Models ---


@dataclass(frozen=True)
class ValidateEmailInput:
    """Input for email validation."""

    email: str
    check_disposable: bool = True  # Check against disposable email domains


@dataclass(frozen=True)
class SubscribeInput:
    """Input for new subscription."""

    email: str
    ip_address: str | None = None  # For rate limiting
    source: str | None = None  # e.g., "homepage", "article_footer"


@dataclass(frozen=True)
class ConfirmInput:
    """Input for confirming subscription."""

    token: str


@dataclass(frozen=True)
class UnsubscribeInput:
    """Input for unsubscribing."""

    token: str


@dataclass(frozen=True)
class GenerateTokenInput:
    """Input for token generation."""

    purpose: str  # "confirmation" or "unsubscribe"
    length: int = 32  # Token length in bytes (URL-safe encoded)


# --- Output Models ---


@dataclass(frozen=True)
class ValidationError:
    """Validation error detail."""

    code: str
    message: str
    field: str | None = None


@dataclass(frozen=True)
class ValidateEmailOutput:
    """Output from email validation."""

    is_valid: bool
    normalized_email: str | None = None  # Lowercase, trimmed
    errors: list[ValidationError] = field(default_factory=list)
    is_disposable: bool = False


@dataclass(frozen=True)
class GenerateTokenOutput:
    """Output from token generation."""

    token: str
    expires_at: datetime | None = None


@dataclass(frozen=True)
class SubscribeOutput:
    """Output from subscription attempt."""

    success: bool
    subscriber_id: UUID | None = None
    needs_confirmation: bool = True  # Always true for new subscriptions
    errors: list[ValidationError] = field(default_factory=list)
    already_subscribed: bool = False  # True if email already confirmed


@dataclass(frozen=True)
class ConfirmOutput:
    """Output from confirmation attempt."""

    success: bool
    subscriber_id: UUID | None = None
    errors: list[ValidationError] = field(default_factory=list)
    already_confirmed: bool = False  # Idempotent success


@dataclass(frozen=True)
class UnsubscribeOutput:
    """Output from unsubscribe attempt."""

    success: bool
    errors: list[ValidationError] = field(default_factory=list)
    already_unsubscribed: bool = False  # Idempotent success


# --- Token Validation ---


@dataclass(frozen=True)
class ValidateTokenInput:
    """Input for token validation."""

    token: str
    max_age_hours: int = 48  # Default 48 hours for confirmation tokens


@dataclass(frozen=True)
class ValidateTokenOutput:
    """Output from token validation."""

    is_valid: bool
    is_expired: bool = False
    subscriber_id: UUID | None = None
    errors: list[ValidationError] = field(default_factory=list)


# --- Configuration ---


@dataclass(frozen=True)
class NewsletterConfig:
    """Newsletter service configuration."""

    confirmation_token_expiry_hours: int = 48
    rate_limit_per_ip_per_hour: int = 10
    site_name: str = "Little Research Lab"
    base_url: str = "https://littleresearchlab.com"
    confirmation_path: str = "/newsletter/confirm"
    unsubscribe_path: str = "/newsletter/unsubscribe"


# --- Error Types ---


class NewsletterError(Exception):
    """Base newsletter error."""

    pass


class EmailValidationError(NewsletterError):
    """Email validation failed."""

    def __init__(self, email: str, reason: str) -> None:
        self.email = email
        self.reason = reason
        super().__init__(f"Invalid email '{email}': {reason}")


class TokenError(NewsletterError):
    """Token validation failed."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Token error: {reason}")


class TokenExpiredError(TokenError):
    """Token has expired."""

    def __init__(self) -> None:
        super().__init__("Token has expired")


class TokenNotFoundError(TokenError):
    """Token not found."""

    def __init__(self) -> None:
        super().__init__("Token not found")


class SubscriptionError(NewsletterError):
    """Subscription operation failed."""

    def __init__(self, email: str, reason: str) -> None:
        self.email = email
        self.reason = reason
        super().__init__(f"Subscription error for '{email}': {reason}")


class RateLimitError(NewsletterError):
    """Rate limit exceeded."""

    def __init__(self, ip_address: str, retry_after_seconds: int = 3600) -> None:
        self.ip_address = ip_address
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded for {ip_address}")
