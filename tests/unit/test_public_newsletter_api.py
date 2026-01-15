"""
Unit tests for public newsletter API endpoints.

Spec refs: E16.1, E16.2, E16.3
Test assertions: TA-0074 to TA-0083
"""

import sqlite3
from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.adapters.dev_email import DevEmailAdapter
from src.adapters.sqlite_db import SQLiteNewsletterSubscriberRepo
from src.api.deps import (
    InMemoryRateLimiter,
    NewsletterEmailSender,
    get_email_adapter,
    get_newsletter_email_sender,
    get_newsletter_repo,
    get_rate_limiter,
)
from src.api.main import app
from src.components.newsletter.models import (
    NewsletterConfig,
    NewsletterSubscriber,
    SubscriberStatus,
)

# --- Test Fixtures ---


@pytest.fixture
def test_db_path(tmp_path) -> str:
    """Create test database with newsletter schema."""
    db_path = str(tmp_path / "test.db")

    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE newsletter_subscribers (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL CHECK(status IN ('pending', 'confirmed', 'unsubscribed')),
            confirmation_token TEXT,
            unsubscribe_token TEXT,
            created_at DATETIME NOT NULL,
            confirmed_at DATETIME,
            unsubscribed_at DATETIME
        )
    """)
    conn.execute(
        "CREATE INDEX idx_newsletter_email ON newsletter_subscribers(email)"
    )
    conn.execute(
        """CREATE INDEX idx_newsletter_confirmation_token
        ON newsletter_subscribers(confirmation_token)"""
    )
    conn.execute(
        "CREATE INDEX idx_newsletter_unsubscribe_token ON newsletter_subscribers(unsubscribe_token)"
    )
    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def test_repo(test_db_path: str) -> SQLiteNewsletterSubscriberRepo:
    """Create test repository."""
    return SQLiteNewsletterSubscriberRepo(test_db_path)


@pytest.fixture
def test_email_adapter() -> DevEmailAdapter:
    """Create test email adapter."""
    return DevEmailAdapter()


@pytest.fixture
def test_email_sender(test_email_adapter: DevEmailAdapter) -> NewsletterEmailSender:
    """Create test email sender."""
    return NewsletterEmailSender(test_email_adapter)


@pytest.fixture
def test_rate_limiter() -> InMemoryRateLimiter:
    """Create test rate limiter."""
    return InMemoryRateLimiter()


@pytest.fixture
def test_config() -> NewsletterConfig:
    """Create test configuration."""
    return NewsletterConfig(
        base_url="http://test.local",
        site_name="Test Site",
        confirmation_path="/newsletter/confirm",
        unsubscribe_path="/newsletter/unsubscribe",
        confirmation_token_expiry_hours=48,
        rate_limit_per_ip_per_hour=10,
    )


@pytest.fixture
def client(
    test_repo: SQLiteNewsletterSubscriberRepo,
    test_email_sender: NewsletterEmailSender,
    test_rate_limiter: InMemoryRateLimiter,
    test_email_adapter: DevEmailAdapter,
) -> Generator[TestClient, None, None]:
    """Create test client with dependency overrides."""
    # Override dependencies
    app.dependency_overrides[get_newsletter_repo] = lambda: test_repo
    app.dependency_overrides[get_newsletter_email_sender] = lambda: test_email_sender
    app.dependency_overrides[get_rate_limiter] = lambda: test_rate_limiter
    app.dependency_overrides[get_email_adapter] = lambda: test_email_adapter

    yield TestClient(app)

    # Clean up overrides
    app.dependency_overrides.clear()


# --- Subscribe Endpoint Tests (TA-0074, TA-0075, TA-0076) ---


class TestSubscribeEndpoint:
    """Tests for POST /api/public/newsletter/subscribe."""

    def test_subscribe_success(
        self, client: TestClient, test_repo: SQLiteNewsletterSubscriberRepo
    ) -> None:
        """TA-0074: Valid email creates pending subscriber."""
        response = client.post(
            "/api/public/newsletter/subscribe",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "check your email" in data["message"].lower()

        # Verify subscriber created in DB
        subscriber = test_repo.get_by_email("test@example.com")
        assert subscriber is not None
        assert subscriber.status == SubscriberStatus.PENDING

    def test_subscribe_sends_confirmation_email(
        self, client: TestClient, test_email_adapter: DevEmailAdapter
    ) -> None:
        """TA-0076: Confirmation email is sent."""
        response = client.post(
            "/api/public/newsletter/subscribe",
            json={"email": "email@example.com"},
        )

        assert response.status_code == 200
        assert test_email_adapter.email_count >= 1

        # Check email was sent to correct recipient
        email = test_email_adapter.get_last_email()
        assert email is not None
        assert email.recipient == "email@example.com"
        assert "confirm" in email.subject.lower()

    def test_subscribe_invalid_email_format(self, client: TestClient) -> None:
        """TA-0074: Invalid email format returns 400."""
        response = client.post(
            "/api/public/newsletter/subscribe",
            json={"email": "not-an-email"},
        )

        assert response.status_code == 422  # Pydantic validation

    def test_subscribe_disposable_email_rejected(
        self, client: TestClient
    ) -> None:
        """TA-0075: Disposable email domains are rejected."""
        response = client.post(
            "/api/public/newsletter/subscribe",
            json={"email": "test@mailinator.com"},
        )

        assert response.status_code == 400
        assert "permanent email" in response.json()["detail"].lower()

    def test_subscribe_rate_limit(
        self, client: TestClient, test_rate_limiter: InMemoryRateLimiter
    ) -> None:
        """TA-0076: Rate limit of 10 per IP per hour enforced."""
        # Exhaust rate limit
        for _i in range(10):
            test_rate_limiter.record_attempt("testclient")

        response = client.post(
            "/api/public/newsletter/subscribe",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 429

    def test_subscribe_already_confirmed_idempotent(
        self, client: TestClient, test_repo: SQLiteNewsletterSubscriberRepo
    ) -> None:
        """Already confirmed subscriber returns success without revealing status."""
        # Create confirmed subscriber
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="existing@example.com",
            status=SubscriberStatus.CONFIRMED,
            confirmation_token=None,
            unsubscribe_token="unsub-token",
            created_at=datetime.now(UTC),
            confirmed_at=datetime.now(UTC),
        )
        test_repo.save(subscriber)

        response = client.post(
            "/api/public/newsletter/subscribe",
            json={"email": "existing@example.com"},
        )

        # Returns success to not reveal subscription status (privacy)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_subscribe_pending_resends_confirmation(
        self,
        client: TestClient,
        test_repo: SQLiteNewsletterSubscriberRepo,
        test_email_adapter: DevEmailAdapter,
    ) -> None:
        """Pending subscriber gets confirmation resent."""
        # Create pending subscriber
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="pending@example.com",
            status=SubscriberStatus.PENDING,
            confirmation_token="existing-token",
            unsubscribe_token="unsub-token",
            created_at=datetime.now(UTC),
        )
        test_repo.save(subscriber)

        initial_count = test_email_adapter.email_count

        response = client.post(
            "/api/public/newsletter/subscribe",
            json={"email": "pending@example.com"},
        )

        assert response.status_code == 200
        # Email should be resent
        assert test_email_adapter.email_count > initial_count

    def test_subscribe_response_no_email_echo(self, client: TestClient) -> None:
        """TA-0076: Response doesn't echo back email (privacy)."""
        response = client.post(
            "/api/public/newsletter/subscribe",
            json={"email": "private@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "private@example.com" not in str(data)


# --- Confirm Endpoint Tests (TA-0077, TA-0078, TA-0079, TA-0080) ---


class TestConfirmEndpoint:
    """Tests for GET /api/public/newsletter/confirm."""

    def test_confirm_success(
        self, client: TestClient, test_repo: SQLiteNewsletterSubscriberRepo
    ) -> None:
        """TA-0079: Valid token confirms subscription."""
        # Create pending subscriber
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="toconfirm@example.com",
            status=SubscriberStatus.PENDING,
            confirmation_token="valid-token-123",
            unsubscribe_token="unsub-token",
            created_at=datetime.now(UTC),
        )
        test_repo.save(subscriber)

        response = client.get("/api/public/newsletter/confirm?token=valid-token-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "confirmed" in data["message"].lower()

        # Verify status changed
        updated = test_repo.get_by_email("toconfirm@example.com")
        assert updated is not None
        assert updated.status == SubscriberStatus.CONFIRMED

    def test_confirm_invalid_token(self, client: TestClient) -> None:
        """TA-0077: Invalid token returns error."""
        response = client.get("/api/public/newsletter/confirm?token=invalid-token")

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_confirm_missing_token(self, client: TestClient) -> None:
        """Missing token returns 422 (required query param)."""
        response = client.get("/api/public/newsletter/confirm")

        assert response.status_code == 422

    def test_confirm_expired_token(
        self, client: TestClient, test_repo: SQLiteNewsletterSubscriberRepo
    ) -> None:
        """TA-0078: Expired token returns error."""
        # Create subscriber with old creation date (expired)
        from datetime import timedelta

        old_date = datetime.now(UTC) - timedelta(hours=50)  # Past 48h expiry
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="expired@example.com",
            status=SubscriberStatus.PENDING,
            confirmation_token="expired-token",
            unsubscribe_token="unsub-token",
            created_at=old_date,
        )
        test_repo.save(subscriber)

        response = client.get("/api/public/newsletter/confirm?token=expired-token")

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    def test_confirm_idempotent(
        self, client: TestClient, test_repo: SQLiteNewsletterSubscriberRepo
    ) -> None:
        """TA-0080: Already confirmed returns success."""
        # Create already confirmed subscriber (no confirmation token)
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="already@example.com",
            status=SubscriberStatus.CONFIRMED,
            confirmation_token="still-has-token",  # Shouldn't matter
            unsubscribe_token="unsub-token",
            created_at=datetime.now(UTC),
            confirmed_at=datetime.now(UTC),
        )
        test_repo.save(subscriber)

        response = client.get("/api/public/newsletter/confirm?token=still-has-token")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "already" in data["message"].lower()


# --- Unsubscribe Endpoint Tests (TA-0081, TA-0082, TA-0083) ---


class TestUnsubscribeEndpoint:
    """Tests for GET /api/public/newsletter/unsubscribe."""

    def test_unsubscribe_success(
        self, client: TestClient, test_repo: SQLiteNewsletterSubscriberRepo
    ) -> None:
        """TA-0082: Valid token unsubscribes user."""
        # Create confirmed subscriber
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="tounsub@example.com",
            status=SubscriberStatus.CONFIRMED,
            confirmation_token=None,
            unsubscribe_token="unsub-token-123",
            created_at=datetime.now(UTC),
            confirmed_at=datetime.now(UTC),
        )
        test_repo.save(subscriber)

        response = client.get("/api/public/newsletter/unsubscribe?token=unsub-token-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "unsubscribed" in data["message"].lower()

        # Verify status changed
        updated = test_repo.get_by_email("tounsub@example.com")
        assert updated is not None
        assert updated.status == SubscriberStatus.UNSUBSCRIBED

    def test_unsubscribe_invalid_token(self, client: TestClient) -> None:
        """TA-0081: Invalid token returns error."""
        response = client.get("/api/public/newsletter/unsubscribe?token=bad-token")

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_unsubscribe_missing_token(self, client: TestClient) -> None:
        """Missing token returns 422."""
        response = client.get("/api/public/newsletter/unsubscribe")

        assert response.status_code == 422

    def test_unsubscribe_idempotent(
        self, client: TestClient, test_repo: SQLiteNewsletterSubscriberRepo
    ) -> None:
        """TA-0083: Already unsubscribed returns success."""
        # Create unsubscribed subscriber
        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="alreadyunsub@example.com",
            status=SubscriberStatus.UNSUBSCRIBED,
            confirmation_token=None,
            unsubscribe_token="unsub-token-456",
            created_at=datetime.now(UTC),
            confirmed_at=datetime.now(UTC),
            unsubscribed_at=datetime.now(UTC),
        )
        test_repo.save(subscriber)

        response = client.get("/api/public/newsletter/unsubscribe?token=unsub-token-456")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "already" in data["message"].lower()


# --- Email Sender Adapter Tests ---


class TestNewsletterEmailSender:
    """Tests for NewsletterEmailSender adapter."""

    def test_send_confirmation_email(self, test_email_adapter: DevEmailAdapter) -> None:
        """Confirmation email is sent with correct content."""
        sender = NewsletterEmailSender(test_email_adapter)

        result = sender.send_confirmation_email(
            recipient_email="test@example.com",
            confirmation_url="http://test.local/confirm?token=abc",
            site_name="Test Site",
        )

        assert result is True
        email = test_email_adapter.get_last_email()
        assert email is not None
        assert email.recipient == "test@example.com"
        assert "Test Site" in email.subject
        assert "http://test.local/confirm?token=abc" in email.body_html

    def test_send_welcome_email(self, test_email_adapter: DevEmailAdapter) -> None:
        """Welcome email is sent with unsubscribe link."""
        sender = NewsletterEmailSender(test_email_adapter)

        result = sender.send_welcome_email(
            recipient_email="test@example.com",
            unsubscribe_url="http://test.local/unsubscribe?token=xyz",
            site_name="Test Site",
        )

        assert result is True
        email = test_email_adapter.get_last_email()
        assert email is not None
        assert "Welcome" in email.subject
        assert "http://test.local/unsubscribe?token=xyz" in email.body_html


# --- Rate Limiter Tests ---


class TestInMemoryRateLimiter:
    """Tests for InMemoryRateLimiter."""

    def test_allows_within_limit(self) -> None:
        """Allows requests within limit."""
        limiter = InMemoryRateLimiter()

        for _i in range(9):
            limiter.record_attempt("ip1")

        allowed, remaining = limiter.check_rate_limit("ip1", limit=10, window_seconds=3600)
        assert allowed is True
        assert remaining == 1

    def test_blocks_at_limit(self) -> None:
        """Blocks requests at limit."""
        limiter = InMemoryRateLimiter()

        for _i in range(10):
            limiter.record_attempt("ip2")

        allowed, remaining = limiter.check_rate_limit("ip2", limit=10, window_seconds=3600)
        assert allowed is False
        assert remaining == 0

    def test_separate_keys(self) -> None:
        """Different IPs have separate limits."""
        limiter = InMemoryRateLimiter()

        for _i in range(10):
            limiter.record_attempt("ip3")

        allowed, _ = limiter.check_rate_limit("ip4", limit=10, window_seconds=3600)
        assert allowed is True
