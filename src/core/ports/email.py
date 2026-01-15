"""
Email Adapter Interface (P7).

Protocol-based interface for sending transactional emails.
Used by NewsletterService for confirmation and notification emails.

Spec refs: E16.5, TA-0088, TA-0089
Test assertions:
- TA-0088: DevEmailAdapter logs without sending
- TA-0089: EmailPort interface defines send_email method

Key requirements:
- Send transactional emails (confirmation, unsubscribe)
- Support HTML and plain text body
- Stateless send operation
- Production adapter deferred (DevEmailAdapter for MVP per D-0013)

Implementation strategies:
1. DevEmailAdapter: Logs emails to console (dev/test)
2. SMTPEmailAdapter: Sends via SMTP (future)
3. SendGridAdapter: Sends via SendGrid API (future)
4. SESAdapter: Sends via AWS SES (future)

All strategies implement the same EmailPort interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Protocol


class EmailStatus(Enum):
    """Email send result status."""

    SENT = "sent"
    QUEUED = "queued"  # Async send (not delivered yet)
    FAILED = "failed"
    SKIPPED = "skipped"  # Dev adapter or dry-run


@dataclass(frozen=True)
class EmailAddress:
    """
    Email address with optional display name.

    Examples:
        EmailAddress("user@example.com")
        EmailAddress("user@example.com", "John Doe")
    """

    email: str
    name: str | None = None

    def __str__(self) -> str:
        """Format as RFC 5322 address."""
        if self.name:
            # Escape quotes in name
            safe_name = self.name.replace('"', '\\"')
            return f'"{safe_name}" <{self.email}>'
        return self.email


@dataclass(frozen=True)
class EmailMessage:
    """
    Email message to be sent.

    Supports both HTML and plain text body for maximum compatibility.
    """

    recipient: EmailAddress
    subject: str
    body_html: str
    body_text: str
    sender: EmailAddress | None = None  # None = use default sender
    reply_to: EmailAddress | None = None
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate email message."""
        if not self.recipient.email:
            raise ValueError("Recipient email is required")
        if not self.subject:
            raise ValueError("Subject is required")
        if not self.body_html and not self.body_text:
            raise ValueError("At least one of body_html or body_text is required")


@dataclass
class EmailResult:
    """Result of an email send attempt."""

    status: EmailStatus
    message_id: str | None = None  # Provider's message ID
    error: str | None = None
    sent_at: datetime | None = None
    recipient: str = ""

    @classmethod
    def success(cls, recipient: str, message_id: str | None = None) -> EmailResult:
        """Create a successful send result."""
        return cls(
            status=EmailStatus.SENT,
            message_id=message_id,
            recipient=recipient,
            sent_at=datetime.now(UTC),
        )

    @classmethod
    def skipped(cls, recipient: str, reason: str = "Dev mode") -> EmailResult:
        """Create a skipped result (dev adapter)."""
        return cls(
            status=EmailStatus.SKIPPED,
            recipient=recipient,
            error=reason,
        )

    @classmethod
    def failed(cls, recipient: str, error: str) -> EmailResult:
        """Create a failed result."""
        return cls(
            status=EmailStatus.FAILED,
            recipient=recipient,
            error=error,
        )


class EmailPort(Protocol):
    """
    Email sending interface (TA-0089).

    Implementations:
    - DevEmailAdapter: Logs to console (dev/test)
    - SMTPEmailAdapter: Sends via SMTP (future)
    - SendGridAdapter: Sends via SendGrid (future)
    """

    def send_email(
        self,
        recipient: str,
        subject: str,
        body_html: str,
        body_text: str | None = None,
    ) -> EmailResult:
        """
        Send a transactional email.

        Args:
            recipient: Email address of recipient
            subject: Email subject line
            body_html: HTML body content
            body_text: Plain text body (optional, fallback)

        Returns:
            EmailResult with send outcome

        Notes:
            - Must not raise exceptions; return failed status instead
            - TA-0088: DevEmailAdapter logs but doesn't send
        """
        ...

    def send(self, message: EmailMessage) -> EmailResult:
        """
        Send an email message with full options.

        Args:
            message: Complete email message with all options

        Returns:
            EmailResult with send outcome
        """
        ...


class EmailConfigPort(Protocol):
    """
    Email configuration interface.

    Provides email sending configuration (sender, SMTP settings, etc.).
    """

    @property
    def default_sender(self) -> EmailAddress:
        """Get the default sender address."""
        ...

    @property
    def is_enabled(self) -> bool:
        """Check if email sending is enabled."""
        ...


# --- Error Types ---


class EmailError(Exception):
    """Base exception for email-related errors."""

    pass


class EmailValidationError(EmailError):
    """Invalid email address or message format."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class EmailSendError(EmailError):
    """Failed to send email."""

    def __init__(self, recipient: str, error: str, retriable: bool = True) -> None:
        self.recipient = recipient
        self.error = error
        self.retriable = retriable
        super().__init__(f"Failed to send email to {recipient}: {error}")


class EmailRateLimitError(EmailError):
    """Email rate limit exceeded."""

    def __init__(self, recipient: str, retry_after_seconds: int = 60) -> None:
        self.recipient = recipient
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded for {recipient}, retry after {retry_after_seconds}s")


# --- Constants ---


# Common email template placeholders
EMAIL_PLACEHOLDERS = {
    "site_name": "{{site_name}}",
    "subscriber_email": "{{subscriber_email}}",
    "confirmation_url": "{{confirmation_url}}",
    "unsubscribe_url": "{{unsubscribe_url}}",
}

# Default confirmation email subject
DEFAULT_CONFIRMATION_SUBJECT = "Confirm your subscription to {{site_name}}"

# Default unsubscribe success subject
DEFAULT_UNSUBSCRIBE_SUBJECT = "You've been unsubscribed from {{site_name}}"
