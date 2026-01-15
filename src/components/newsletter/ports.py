"""
Newsletter component ports (C10).

Protocol interfaces for newsletter service dependencies.

Spec refs: E16.1, E16.2, E16.3
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.components.newsletter.models import NewsletterSubscriber, SubscriberStatus


class NewsletterRepoPort(Protocol):
    """
    Newsletter subscriber repository interface.

    Abstracts data persistence for newsletter subscribers.
    """

    def get_by_id(self, subscriber_id: UUID) -> NewsletterSubscriber | None:
        """Get subscriber by ID."""
        ...

    def get_by_email(self, email: str) -> NewsletterSubscriber | None:
        """Get subscriber by email address."""
        ...

    def get_by_confirmation_token(self, token: str) -> NewsletterSubscriber | None:
        """Get subscriber by confirmation token."""
        ...

    def get_by_unsubscribe_token(self, token: str) -> NewsletterSubscriber | None:
        """Get subscriber by unsubscribe token."""
        ...

    def save(self, subscriber: NewsletterSubscriber) -> NewsletterSubscriber:
        """Save or update subscriber."""
        ...

    def delete(self, subscriber_id: UUID) -> bool:
        """Delete subscriber by ID (GDPR)."""
        ...

    def list_by_status(
        self,
        status: SubscriberStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NewsletterSubscriber]:
        """List subscribers by status."""
        ...

    def count_by_status(self, status: SubscriberStatus) -> int:
        """Count subscribers by status."""
        ...


class DisposableEmailCheckerPort(Protocol):
    """
    Disposable email checker interface.

    Checks if an email domain is known to be disposable.
    """

    def is_disposable(self, email: str) -> bool:
        """
        Check if email domain is disposable.

        Args:
            email: Email address to check

        Returns:
            True if domain is disposable (temporary email service)
        """
        ...


class RateLimiterPort(Protocol):
    """
    Rate limiter interface for subscription attempts.

    Tracks and limits subscription attempts per IP address.
    """

    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check if rate limit is exceeded.

        Args:
            key: Rate limit key (e.g., IP address)
            limit: Maximum attempts in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_attempts)
        """
        ...

    def record_attempt(self, key: str) -> None:
        """Record an attempt for rate limiting."""
        ...


class NewsletterRulesPort(Protocol):
    """
    Newsletter rules provider interface.

    Provides configuration from rules.yaml.
    """

    @property
    def confirmation_token_expiry_hours(self) -> int:
        """Token expiry time in hours."""
        ...

    @property
    def rate_limit_per_ip_per_hour(self) -> int:
        """Max subscription attempts per IP per hour."""
        ...

    @property
    def disposable_email_domains(self) -> set[str]:
        """Set of known disposable email domains."""
        ...


class NewsletterEmailSenderPort(Protocol):
    """
    Email sender interface for newsletter operations.

    Sends confirmation and notification emails.
    """

    def send_confirmation_email(
        self,
        recipient_email: str,
        confirmation_url: str,
        site_name: str,
    ) -> bool:
        """
        Send double opt-in confirmation email.

        Args:
            recipient_email: Email to send to
            confirmation_url: Full URL for confirmation
            site_name: Site name for email template

        Returns:
            True if email sent successfully
        """
        ...

    def send_welcome_email(
        self,
        recipient_email: str,
        unsubscribe_url: str,
        site_name: str,
    ) -> bool:
        """
        Send welcome email after confirmation.

        Args:
            recipient_email: Email to send to
            unsubscribe_url: Full URL for unsubscribe
            site_name: Site name for email template

        Returns:
            True if email sent successfully
        """
        ...
