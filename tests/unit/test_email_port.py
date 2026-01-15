"""
TA-0089: Email port interface tests.

Verifies the EmailPort protocol and related data classes work correctly.
"""

from __future__ import annotations

from typing import Protocol

import pytest

from src.core.ports.email import (
    DEFAULT_CONFIRMATION_SUBJECT,
    EMAIL_PLACEHOLDERS,
    EmailAddress,
    EmailConfigPort,
    EmailError,
    EmailMessage,
    EmailPort,
    EmailRateLimitError,
    EmailResult,
    EmailSendError,
    EmailStatus,
    EmailValidationError,
)

# --- Protocol Tests (TA-0089) ---


class TestEmailPortProtocol:
    """TA-0089: Verify EmailPort is a proper Protocol."""

    def test_email_port_is_protocol(self) -> None:
        """EmailPort inherits from Protocol."""
        assert issubclass(EmailPort, Protocol)

    def test_email_config_port_is_protocol(self) -> None:
        """EmailConfigPort inherits from Protocol."""
        assert issubclass(EmailConfigPort, Protocol)

    def test_email_port_has_send_email_method(self) -> None:
        """EmailPort defines send_email method."""
        assert hasattr(EmailPort, "send_email")

    def test_email_port_has_send_method(self) -> None:
        """EmailPort defines send method with EmailMessage."""
        assert hasattr(EmailPort, "send")


# --- EmailAddress Tests ---


class TestEmailAddress:
    """Test EmailAddress data class."""

    def test_email_address_simple(self) -> None:
        """Simple email address without name."""
        addr = EmailAddress("user@example.com")
        assert addr.email == "user@example.com"
        assert addr.name is None
        assert str(addr) == "user@example.com"

    def test_email_address_with_name(self) -> None:
        """Email address with display name."""
        addr = EmailAddress("user@example.com", "John Doe")
        assert addr.email == "user@example.com"
        assert addr.name == "John Doe"
        assert str(addr) == '"John Doe" <user@example.com>'

    def test_email_address_with_quotes_in_name(self) -> None:
        """Email address escapes quotes in name."""
        addr = EmailAddress("user@example.com", 'John "Johnny" Doe')
        formatted = str(addr)
        assert '\\"' in formatted
        assert "user@example.com" in formatted

    def test_email_address_is_frozen(self) -> None:
        """EmailAddress is immutable."""
        addr = EmailAddress("user@example.com")
        with pytest.raises(AttributeError):  # FrozenInstanceError is a subclass
            addr.email = "other@example.com"  # type: ignore[misc]


# --- EmailMessage Tests ---


class TestEmailMessage:
    """Test EmailMessage data class."""

    def test_email_message_minimal(self) -> None:
        """Minimal email message with required fields."""
        msg = EmailMessage(
            recipient=EmailAddress("user@example.com"),
            subject="Test Subject",
            body_html="<p>Hello</p>",
            body_text="Hello",
        )
        assert msg.recipient.email == "user@example.com"
        assert msg.subject == "Test Subject"
        assert msg.body_html == "<p>Hello</p>"
        assert msg.body_text == "Hello"
        assert msg.sender is None
        assert msg.reply_to is None

    def test_email_message_with_sender(self) -> None:
        """Email message with explicit sender."""
        msg = EmailMessage(
            recipient=EmailAddress("user@example.com"),
            subject="Test",
            body_html="<p>Hello</p>",
            body_text="Hello",
            sender=EmailAddress("noreply@site.com", "Site Name"),
        )
        assert msg.sender is not None
        assert msg.sender.email == "noreply@site.com"

    def test_email_message_with_reply_to(self) -> None:
        """Email message with reply-to address."""
        msg = EmailMessage(
            recipient=EmailAddress("user@example.com"),
            subject="Test",
            body_html="<p>Hello</p>",
            body_text="Hello",
            reply_to=EmailAddress("support@site.com"),
        )
        assert msg.reply_to is not None
        assert msg.reply_to.email == "support@site.com"

    def test_email_message_with_headers(self) -> None:
        """Email message with custom headers."""
        msg = EmailMessage(
            recipient=EmailAddress("user@example.com"),
            subject="Test",
            body_html="<p>Hello</p>",
            body_text="Hello",
            headers={"X-Custom": "value"},
        )
        assert msg.headers["X-Custom"] == "value"

    def test_email_message_requires_recipient(self) -> None:
        """Email message requires valid recipient."""
        with pytest.raises(ValueError, match="Recipient email is required"):
            EmailMessage(
                recipient=EmailAddress(""),  # Empty email
                subject="Test",
                body_html="<p>Hello</p>",
                body_text="Hello",
            )

    def test_email_message_requires_subject(self) -> None:
        """Email message requires subject."""
        with pytest.raises(ValueError, match="Subject is required"):
            EmailMessage(
                recipient=EmailAddress("user@example.com"),
                subject="",  # Empty subject
                body_html="<p>Hello</p>",
                body_text="Hello",
            )

    def test_email_message_requires_body(self) -> None:
        """Email message requires at least one body."""
        with pytest.raises(ValueError, match="body_html or body_text"):
            EmailMessage(
                recipient=EmailAddress("user@example.com"),
                subject="Test",
                body_html="",
                body_text="",
            )

    def test_email_message_html_only_valid(self) -> None:
        """Email message with only HTML body is valid."""
        msg = EmailMessage(
            recipient=EmailAddress("user@example.com"),
            subject="Test",
            body_html="<p>Hello</p>",
            body_text="",  # Empty is OK if HTML provided
        )
        # Validation passes only if body_html is not empty
        assert msg.body_html == "<p>Hello</p>"


# --- EmailResult Tests ---


class TestEmailResult:
    """Test EmailResult data class and factory methods."""

    def test_email_result_success_factory(self) -> None:
        """EmailResult.success() creates successful result."""
        result = EmailResult.success("user@example.com", message_id="msg-123")
        assert result.status == EmailStatus.SENT
        assert result.recipient == "user@example.com"
        assert result.message_id == "msg-123"
        assert result.error is None
        assert result.sent_at is not None

    def test_email_result_skipped_factory(self) -> None:
        """EmailResult.skipped() creates skipped result."""
        result = EmailResult.skipped("user@example.com", "Dev mode")
        assert result.status == EmailStatus.SKIPPED
        assert result.recipient == "user@example.com"
        assert result.error == "Dev mode"
        assert result.message_id is None

    def test_email_result_failed_factory(self) -> None:
        """EmailResult.failed() creates failed result."""
        result = EmailResult.failed("user@example.com", "SMTP timeout")
        assert result.status == EmailStatus.FAILED
        assert result.recipient == "user@example.com"
        assert result.error == "SMTP timeout"
        assert result.message_id is None


# --- EmailStatus Tests ---


class TestEmailStatus:
    """Test EmailStatus enum."""

    def test_email_status_values(self) -> None:
        """EmailStatus has expected values."""
        assert EmailStatus.SENT.value == "sent"
        assert EmailStatus.QUEUED.value == "queued"
        assert EmailStatus.FAILED.value == "failed"
        assert EmailStatus.SKIPPED.value == "skipped"


# --- Error Types Tests ---


class TestEmailErrors:
    """Test email error classes."""

    def test_email_error_base(self) -> None:
        """EmailError is base exception."""
        err = EmailError("Test error")
        assert isinstance(err, Exception)
        assert str(err) == "Test error"

    def test_email_validation_error(self) -> None:
        """EmailValidationError includes field info."""
        err = EmailValidationError("Invalid format", field="recipient")
        assert err.field == "recipient"
        assert "Invalid format" in str(err)

    def test_email_send_error(self) -> None:
        """EmailSendError includes recipient and retriability."""
        err = EmailSendError("user@example.com", "Connection refused", retriable=True)
        assert err.recipient == "user@example.com"
        assert err.error == "Connection refused"
        assert err.retriable is True
        assert "user@example.com" in str(err)

    def test_email_send_error_non_retriable(self) -> None:
        """EmailSendError can be non-retriable."""
        err = EmailSendError("bad@example.com", "Invalid address", retriable=False)
        assert err.retriable is False

    def test_email_rate_limit_error(self) -> None:
        """EmailRateLimitError includes retry info."""
        err = EmailRateLimitError("user@example.com", retry_after_seconds=300)
        assert err.recipient == "user@example.com"
        assert err.retry_after_seconds == 300
        assert "300" in str(err)


# --- Constants Tests ---


class TestEmailConstants:
    """Test email-related constants."""

    def test_email_placeholders_defined(self) -> None:
        """EMAIL_PLACEHOLDERS has expected keys."""
        assert "site_name" in EMAIL_PLACEHOLDERS
        assert "subscriber_email" in EMAIL_PLACEHOLDERS
        assert "confirmation_url" in EMAIL_PLACEHOLDERS
        assert "unsubscribe_url" in EMAIL_PLACEHOLDERS

    def test_default_confirmation_subject(self) -> None:
        """DEFAULT_CONFIRMATION_SUBJECT uses placeholders."""
        assert "{{site_name}}" in DEFAULT_CONFIRMATION_SUBJECT


# --- Mock Adapter Tests ---


class TestMockEmailAdapter:
    """Test that a mock adapter can implement EmailPort."""

    def test_mock_adapter_implements_protocol(self) -> None:
        """A simple mock can implement EmailPort."""

        class MockEmailAdapter:
            """Mock email adapter for testing."""

            def __init__(self) -> None:
                self.sent_emails: list[EmailMessage] = []

            def send_email(
                self,
                recipient: str,
                subject: str,
                body_html: str,
                body_text: str | None = None,
            ) -> EmailResult:
                return EmailResult.skipped(recipient, "Mock adapter")

            def send(self, message: EmailMessage) -> EmailResult:
                self.sent_emails.append(message)
                return EmailResult.skipped(message.recipient.email, "Mock adapter")

        adapter = MockEmailAdapter()

        # Test send_email
        result = adapter.send_email(
            recipient="user@example.com",
            subject="Test",
            body_html="<p>Hello</p>",
        )
        assert result.status == EmailStatus.SKIPPED

        # Test send
        msg = EmailMessage(
            recipient=EmailAddress("user@example.com"),
            subject="Test",
            body_html="<p>Hello</p>",
            body_text="Hello",
        )
        result = adapter.send(msg)
        assert result.status == EmailStatus.SKIPPED
        assert len(adapter.sent_emails) == 1
