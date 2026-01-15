"""
Unit tests for DevEmailAdapter (TA-0088, TA-0089).

Tests verify:
- TA-0088: DevEmailAdapter logs without sending
- TA-0089: Implements EmailPort interface correctly

Tests cover:
1. Basic send_email functionality
2. Structured send() with EmailMessage
3. Status is SKIPPED (not SENT)
4. Email storage for test assertions
5. Test helper methods
"""

import logging
from datetime import UTC, datetime

import pytest

from src.adapters.dev_email import (
    DevEmailAdapter,
    SentEmail,
    create_dev_email_adapter,
)
from src.core.ports.email import (
    EmailAddress,
    EmailMessage,
    EmailResult,
    EmailStatus,
)


class TestDevEmailAdapterSendEmail:
    """Tests for send_email method (TA-0088)."""

    def test_send_email_returns_skipped_status(self) -> None:
        """TA-0088: Dev adapter returns SKIPPED, not SENT."""
        adapter = DevEmailAdapter()

        result = adapter.send_email(
            recipient="user@example.com",
            subject="Test Subject",
            body_html="<p>Test body</p>",
        )

        assert result.status == EmailStatus.SKIPPED

    def test_send_email_includes_message_id(self) -> None:
        """Result includes a message ID for tracking."""
        adapter = DevEmailAdapter()

        result = adapter.send_email(
            recipient="user@example.com",
            subject="Test",
            body_html="<p>Test</p>",
        )

        assert result.message_id is not None
        assert result.message_id.startswith("dev-")

    def test_send_email_includes_recipient(self) -> None:
        """Result includes recipient for verification."""
        adapter = DevEmailAdapter()

        result = adapter.send_email(
            recipient="user@example.com",
            subject="Test",
            body_html="<p>Test</p>",
        )

        assert result.recipient == "user@example.com"

    def test_send_email_includes_dev_mode_error(self) -> None:
        """Result includes dev mode explanation."""
        adapter = DevEmailAdapter()

        result = adapter.send_email(
            recipient="user@example.com",
            subject="Test",
            body_html="<p>Test</p>",
        )

        assert result.error is not None
        assert "dev" in result.error.lower() or "logged" in result.error.lower()

    def test_send_email_stores_email(self) -> None:
        """TA-0088: Email is stored for test assertions."""
        adapter = DevEmailAdapter()

        adapter.send_email(
            recipient="user@example.com",
            subject="Test Subject",
            body_html="<p>HTML body</p>",
            body_text="Text body",
        )

        assert len(adapter.sent_emails) == 1
        email = adapter.sent_emails[0]
        assert email.recipient == "user@example.com"
        assert email.subject == "Test Subject"
        assert email.body_html == "<p>HTML body</p>"
        assert email.body_text == "Text body"

    def test_send_email_without_body_text(self) -> None:
        """Handle optional body_text parameter."""
        adapter = DevEmailAdapter()

        adapter.send_email(
            recipient="user@example.com",
            subject="Test",
            body_html="<p>HTML only</p>",
        )

        email = adapter.get_last_email()
        assert email is not None
        assert email.body_text == ""


class TestDevEmailAdapterSend:
    """Tests for send() method with EmailMessage (TA-0089)."""

    def test_send_returns_skipped_status(self) -> None:
        """TA-0088: Structured send also returns SKIPPED."""
        adapter = DevEmailAdapter()
        message = EmailMessage(
            recipient=EmailAddress("user@example.com"),
            subject="Test",
            body_html="<p>Test</p>",
            body_text="Test",
        )

        result = adapter.send(message)

        assert result.status == EmailStatus.SKIPPED

    def test_send_stores_recipient_formatted(self) -> None:
        """Recipient is stored with proper formatting."""
        adapter = DevEmailAdapter()
        message = EmailMessage(
            recipient=EmailAddress("user@example.com", "John Doe"),
            subject="Test",
            body_html="<p>Test</p>",
            body_text="Test",
        )

        adapter.send(message)

        email = adapter.get_last_email()
        assert email is not None
        assert "user@example.com" in email.recipient
        assert "John Doe" in email.recipient

    def test_send_stores_sender(self) -> None:
        """Sender is stored when provided."""
        adapter = DevEmailAdapter()
        message = EmailMessage(
            recipient=EmailAddress("user@example.com"),
            sender=EmailAddress("admin@site.com", "Site Admin"),
            subject="Test",
            body_html="<p>Test</p>",
            body_text="Test",
        )

        adapter.send(message)

        email = adapter.get_last_email()
        assert email is not None
        assert email.sender is not None
        assert "admin@site.com" in email.sender

    def test_send_without_sender(self) -> None:
        """Handle missing sender gracefully."""
        adapter = DevEmailAdapter()
        message = EmailMessage(
            recipient=EmailAddress("user@example.com"),
            subject="Test",
            body_html="<p>Test</p>",
            body_text="Test",
        )

        adapter.send(message)

        email = adapter.get_last_email()
        assert email is not None
        assert email.sender is None


class TestDevEmailAdapterStorage:
    """Tests for email storage and retrieval."""

    def test_multiple_emails_stored(self) -> None:
        """Multiple emails are stored in order."""
        adapter = DevEmailAdapter()

        adapter.send_email("a@example.com", "First", "<p>1</p>")
        adapter.send_email("b@example.com", "Second", "<p>2</p>")
        adapter.send_email("c@example.com", "Third", "<p>3</p>")

        assert len(adapter.sent_emails) == 3
        assert adapter.sent_emails[0].subject == "First"
        assert adapter.sent_emails[2].subject == "Third"

    def test_get_last_email(self) -> None:
        """get_last_email returns most recent."""
        adapter = DevEmailAdapter()

        adapter.send_email("a@example.com", "First", "<p>1</p>")
        adapter.send_email("b@example.com", "Last", "<p>2</p>")

        last = adapter.get_last_email()
        assert last is not None
        assert last.subject == "Last"

    def test_get_last_email_empty(self) -> None:
        """get_last_email returns None when empty."""
        adapter = DevEmailAdapter()
        assert adapter.get_last_email() is None

    def test_get_emails_to_recipient(self) -> None:
        """Filter emails by recipient."""
        adapter = DevEmailAdapter()

        adapter.send_email("target@example.com", "For target 1", "<p>1</p>")
        adapter.send_email("other@example.com", "For other", "<p>2</p>")
        adapter.send_email("target@example.com", "For target 2", "<p>3</p>")

        target_emails = adapter.get_emails_to("target@example.com")
        assert len(target_emails) == 2
        assert all("target" in e.subject.lower() for e in target_emails)

    def test_get_emails_with_subject(self) -> None:
        """Filter emails by subject content."""
        adapter = DevEmailAdapter()

        adapter.send_email("a@example.com", "Confirm subscription", "<p>1</p>")
        adapter.send_email("b@example.com", "Welcome", "<p>2</p>")
        adapter.send_email("c@example.com", "Please confirm", "<p>3</p>")

        confirm_emails = adapter.get_emails_with_subject("onfirm")
        assert len(confirm_emails) == 2

    def test_clear_emails(self) -> None:
        """Clear removes all stored emails."""
        adapter = DevEmailAdapter()

        adapter.send_email("a@example.com", "Test", "<p>1</p>")
        adapter.send_email("b@example.com", "Test", "<p>2</p>")
        assert adapter.email_count == 2

        adapter.clear()

        assert adapter.email_count == 0
        assert adapter.get_last_email() is None

    def test_email_count_property(self) -> None:
        """email_count returns correct count."""
        adapter = DevEmailAdapter()

        assert adapter.email_count == 0
        adapter.send_email("a@example.com", "Test", "<p>1</p>")
        assert adapter.email_count == 1
        adapter.send_email("b@example.com", "Test", "<p>2</p>")
        assert adapter.email_count == 2


class TestDevEmailAdapterLogging:
    """Tests for logging functionality."""

    def test_logs_email_at_configured_level(self, caplog: pytest.LogCaptureFixture) -> None:
        """Email is logged at configured level."""
        adapter = DevEmailAdapter(log_level=logging.WARNING)

        with caplog.at_level(logging.WARNING):
            adapter.send_email(
                recipient="user@example.com",
                subject="Test Subject",
                body_html="<p>Test body</p>",
            )

        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.WARNING
        assert "user@example.com" in caplog.records[0].message
        assert "Test Subject" in caplog.records[0].message

    def test_logs_body_preview(self, caplog: pytest.LogCaptureFixture) -> None:
        """Body is logged with truncation."""
        adapter = DevEmailAdapter(log_body=True, body_preview_length=20)
        long_body = "<p>" + "x" * 100 + "</p>"

        with caplog.at_level(logging.INFO):
            adapter.send_email(
                recipient="user@example.com",
                subject="Test",
                body_html=long_body,
            )

        assert "..." in caplog.records[0].message

    def test_logs_without_body(self, caplog: pytest.LogCaptureFixture) -> None:
        """Body logging can be disabled."""
        adapter = DevEmailAdapter(log_body=False)

        with caplog.at_level(logging.INFO):
            adapter.send_email(
                recipient="user@example.com",
                subject="Test",
                body_html="<p>Secret content</p>",
            )

        assert "Secret content" not in caplog.records[0].message


class TestDevEmailAdapterFactory:
    """Tests for factory function."""

    def test_create_dev_email_adapter_defaults(self) -> None:
        """Factory creates adapter with defaults."""
        adapter = create_dev_email_adapter()

        assert isinstance(adapter, DevEmailAdapter)
        assert adapter.log_level == logging.INFO
        assert adapter.log_body is True
        assert adapter.body_preview_length == 100

    def test_create_dev_email_adapter_custom(self) -> None:
        """Factory creates adapter with custom settings."""
        adapter = create_dev_email_adapter(
            log_level=logging.DEBUG,
            log_body=False,
            body_preview_length=50,
        )

        assert adapter.log_level == logging.DEBUG
        assert adapter.log_body is False
        assert adapter.body_preview_length == 50


class TestEmailPortProtocolCompliance:
    """Tests verifying EmailPort protocol compliance (TA-0089)."""

    def test_implements_send_email_method(self) -> None:
        """Adapter has send_email method."""
        adapter = DevEmailAdapter()
        assert hasattr(adapter, "send_email")
        assert callable(adapter.send_email)

    def test_implements_send_method(self) -> None:
        """Adapter has send method."""
        adapter = DevEmailAdapter()
        assert hasattr(adapter, "send")
        assert callable(adapter.send)

    def test_send_email_returns_email_result(self) -> None:
        """send_email returns EmailResult."""
        adapter = DevEmailAdapter()

        result = adapter.send_email(
            recipient="user@example.com",
            subject="Test",
            body_html="<p>Test</p>",
        )

        assert isinstance(result, EmailResult)

    def test_send_returns_email_result(self) -> None:
        """send returns EmailResult."""
        adapter = DevEmailAdapter()
        message = EmailMessage(
            recipient=EmailAddress("user@example.com"),
            subject="Test",
            body_html="<p>Test</p>",
            body_text="Test",
        )

        result = adapter.send(message)

        assert isinstance(result, EmailResult)


class TestSentEmailDataclass:
    """Tests for SentEmail dataclass."""

    def test_sent_email_fields(self) -> None:
        """SentEmail has all required fields."""
        now = datetime.now(UTC)
        email = SentEmail(
            id="test-123",
            recipient="user@example.com",
            subject="Test",
            body_html="<p>HTML</p>",
            body_text="Text",
            sender="admin@site.com",
            logged_at=now,
        )

        assert email.id == "test-123"
        assert email.recipient == "user@example.com"
        assert email.subject == "Test"
        assert email.body_html == "<p>HTML</p>"
        assert email.body_text == "Text"
        assert email.sender == "admin@site.com"
        assert email.logged_at == now
