"""
Dev Email Adapter (P7 Implementation).

Logs emails to console instead of sending.
Used for local development and testing.

Spec refs: E16.5, TA-0088, TA-0089, D-0013
Test assertions:
- TA-0088: DevEmailAdapter logs without sending
- TA-0089: Implements EmailPort interface

Production uses real email providers (SMTP/SendGrid/SES);
this provides safe testing without sending actual emails.

Key behaviors:
- Logs email details to console/file
- Returns SKIPPED status (not SENT)
- Stores emails in memory for test assertions
- Supports configurable verbosity
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from src.core.ports.email import (
    EmailMessage,
    EmailResult,
    EmailStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class SentEmail:
    """Record of a logged email for test assertions."""

    id: str
    recipient: str
    subject: str
    body_html: str
    body_text: str
    sender: str | None
    logged_at: datetime


@dataclass
class DevEmailAdapter:
    """
    Dev email adapter that logs instead of sending (TA-0088).

    For local development and testing. Emails are logged to
    console and stored in memory for test assertions.

    Implements EmailPort protocol (TA-0089).
    """

    # In-memory storage for test assertions
    sent_emails: list[SentEmail] = field(default_factory=list)

    # Configuration
    log_level: int = logging.INFO
    log_body: bool = True  # Whether to log body content
    body_preview_length: int = 100  # Max chars of body to log

    def send_email(
        self,
        recipient: str,
        subject: str,
        body_html: str,
        body_text: str | None = None,
    ) -> EmailResult:
        """
        Log an email instead of sending (TA-0088).

        Args:
            recipient: Email address of recipient
            subject: Email subject line
            body_html: HTML body content
            body_text: Plain text body (optional)

        Returns:
            EmailResult with SKIPPED status
        """
        message_id = f"dev-{uuid4().hex[:12]}"
        now = datetime.now(UTC)

        # Store for test assertions
        sent_email = SentEmail(
            id=message_id,
            recipient=recipient,
            subject=subject,
            body_html=body_html,
            body_text=body_text or "",
            sender=None,
            logged_at=now,
        )
        self.sent_emails.append(sent_email)

        # Log the email
        self._log_email(
            recipient=recipient,
            subject=subject,
            body_html=body_html,
            message_id=message_id,
        )

        return EmailResult(
            status=EmailStatus.SKIPPED,
            message_id=message_id,
            recipient=recipient,
            error="Dev mode - email logged, not sent",
        )

    def send(self, message: EmailMessage) -> EmailResult:
        """
        Log a structured email message (TA-0088).

        Args:
            message: Complete email message

        Returns:
            EmailResult with SKIPPED status
        """
        message_id = f"dev-{uuid4().hex[:12]}"
        now = datetime.now(UTC)

        sender_str = str(message.sender) if message.sender else None

        # Store for test assertions
        sent_email = SentEmail(
            id=message_id,
            recipient=str(message.recipient),
            subject=message.subject,
            body_html=message.body_html,
            body_text=message.body_text,
            sender=sender_str,
            logged_at=now,
        )
        self.sent_emails.append(sent_email)

        # Log the email
        self._log_email(
            recipient=str(message.recipient),
            subject=message.subject,
            body_html=message.body_html,
            message_id=message_id,
            sender=sender_str,
        )

        return EmailResult(
            status=EmailStatus.SKIPPED,
            message_id=message_id,
            recipient=str(message.recipient),
            error="Dev mode - email logged, not sent",
        )

    def _log_email(
        self,
        recipient: str,
        subject: str,
        body_html: str,
        message_id: str,
        sender: str | None = None,
    ) -> None:
        """Log email details to console."""
        # Build log message
        parts = [
            f"EMAIL (dev): To={recipient}",
            f"Subject={subject}",
        ]

        if sender:
            parts.append(f"From={sender}")

        if self.log_body and body_html:
            # Truncate body for logging
            preview = body_html[:self.body_preview_length]
            if len(body_html) > self.body_preview_length:
                preview += "..."
            parts.append(f"Body={preview}")

        parts.append(f"MessageID={message_id}")

        log_message = ", ".join(parts)
        logger.log(self.log_level, log_message)

    # --- Test Helper Methods ---

    def get_last_email(self) -> SentEmail | None:
        """Get the most recently logged email."""
        return self.sent_emails[-1] if self.sent_emails else None

    def get_emails_to(self, recipient: str) -> list[SentEmail]:
        """Get all emails logged to a specific recipient."""
        return [e for e in self.sent_emails if e.recipient == recipient]

    def get_emails_with_subject(self, subject_contains: str) -> list[SentEmail]:
        """Get all emails with a subject containing the given text."""
        return [e for e in self.sent_emails if subject_contains in e.subject]

    def clear(self) -> None:
        """Clear all stored emails (for test isolation)."""
        self.sent_emails.clear()

    @property
    def email_count(self) -> int:
        """Get the number of logged emails."""
        return len(self.sent_emails)


# --- Factory Function ---


def create_dev_email_adapter(
    log_level: int = logging.INFO,
    log_body: bool = True,
    body_preview_length: int = 100,
) -> DevEmailAdapter:
    """
    Create a dev email adapter.

    Args:
        log_level: Logging level for email logs
        log_body: Whether to log body content
        body_preview_length: Max chars of body to preview

    Returns:
        Configured DevEmailAdapter
    """
    return DevEmailAdapter(
        log_level=log_level,
        log_body=log_body,
        body_preview_length=body_preview_length,
    )
