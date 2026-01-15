"""
Unit tests for admin newsletter API endpoints.

Spec refs: E16.4
Test assertions: TA-0084, TA-0085, TA-0086, TA-0087
"""

import sqlite3
from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.adapters.sqlite_db import SQLiteNewsletterSubscriberRepo
from src.api.deps import get_current_user, get_newsletter_repo
from src.api.main import app
from src.components.newsletter.models import NewsletterSubscriber, SubscriberStatus
from src.domain.entities import User

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
def test_user() -> User:
    """Create test admin user."""
    return User(
        id=uuid4(),
        email="admin@example.com",
        display_name="Admin User",
        password_hash="test",
        roles=["admin"],
        status="active",
    )


@pytest.fixture
def client(
    test_repo: SQLiteNewsletterSubscriberRepo,
    test_user: User,
) -> Generator[TestClient, None, None]:
    """Create test client with dependency overrides."""
    # Override dependencies
    app.dependency_overrides[get_newsletter_repo] = lambda: test_repo
    app.dependency_overrides[get_current_user] = lambda: test_user

    yield TestClient(app)

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def sample_subscribers(test_repo: SQLiteNewsletterSubscriberRepo) -> list[NewsletterSubscriber]:
    """Create sample subscribers."""
    subscribers = [
        NewsletterSubscriber(
            id=uuid4(),
            email="pending@example.com",
            status=SubscriberStatus.PENDING,
            confirmation_token="token-1",
            unsubscribe_token="unsub-1",
            created_at=datetime.now(UTC),
        ),
        NewsletterSubscriber(
            id=uuid4(),
            email="confirmed@example.com",
            status=SubscriberStatus.CONFIRMED,
            confirmation_token=None,
            unsubscribe_token="unsub-2",
            created_at=datetime.now(UTC),
            confirmed_at=datetime.now(UTC),
        ),
        NewsletterSubscriber(
            id=uuid4(),
            email="unsubscribed@example.com",
            status=SubscriberStatus.UNSUBSCRIBED,
            confirmation_token=None,
            unsubscribe_token="unsub-3",
            created_at=datetime.now(UTC),
            confirmed_at=datetime.now(UTC),
            unsubscribed_at=datetime.now(UTC),
        ),
    ]
    for s in subscribers:
        test_repo.save(s)
    return subscribers


# --- List Subscribers Tests (TA-0084) ---


class TestListSubscribers:
    """Tests for GET /api/admin/newsletter/subscribers."""

    def test_list_all_subscribers(
        self, client: TestClient, sample_subscribers: list[NewsletterSubscriber]
    ) -> None:
        """TA-0084: List all subscribers."""
        response = client.get("/api/admin/newsletter/subscribers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["subscribers"]) == 3

    def test_list_with_pagination(
        self, client: TestClient, sample_subscribers: list[NewsletterSubscriber]
    ) -> None:
        """TA-0084: Pagination works correctly."""
        response = client.get("/api/admin/newsletter/subscribers?limit=2&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["subscribers"]) == 2
        assert data["offset"] == 0
        assert data["limit"] == 2

    def test_list_filter_by_status(
        self, client: TestClient, sample_subscribers: list[NewsletterSubscriber]
    ) -> None:
        """TA-0084: Filter by status."""
        response = client.get("/api/admin/newsletter/subscribers?status=confirmed")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["subscribers"]) == 1
        assert data["subscribers"][0]["status"] == "confirmed"

    def test_list_no_tokens_in_response(
        self, client: TestClient, sample_subscribers: list[NewsletterSubscriber]
    ) -> None:
        """TA-0085: Response doesn't include tokens (security)."""
        response = client.get("/api/admin/newsletter/subscribers")

        assert response.status_code == 200
        data = response.json()
        for subscriber in data["subscribers"]:
            assert "confirmation_token" not in subscriber
            assert "unsubscribe_token" not in subscriber

    def test_list_empty(self, client: TestClient) -> None:
        """Empty list returns correctly."""
        response = client.get("/api/admin/newsletter/subscribers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["subscribers"]) == 0


# --- Get Subscriber Tests (TA-0085) ---


class TestGetSubscriber:
    """Tests for GET /api/admin/newsletter/subscribers/{id}."""

    def test_get_subscriber(
        self, client: TestClient, sample_subscribers: list[NewsletterSubscriber]
    ) -> None:
        """TA-0085: Get subscriber by ID."""
        subscriber = sample_subscribers[0]
        response = client.get(f"/api/admin/newsletter/subscribers/{subscriber.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(subscriber.id)
        assert data["email"] == subscriber.email

    def test_get_subscriber_not_found(self, client: TestClient) -> None:
        """Returns 404 for non-existent subscriber."""
        fake_id = uuid4()
        response = client.get(f"/api/admin/newsletter/subscribers/{fake_id}")

        assert response.status_code == 404


# --- Delete Subscriber Tests (TA-0086) ---


class TestDeleteSubscriber:
    """Tests for DELETE /api/admin/newsletter/subscribers/{id}."""

    def test_delete_subscriber_gdpr(
        self,
        client: TestClient,
        test_repo: SQLiteNewsletterSubscriberRepo,
        sample_subscribers: list[NewsletterSubscriber],
    ) -> None:
        """TA-0086: Delete subscriber (GDPR right to erasure)."""
        subscriber = sample_subscribers[0]

        response = client.delete(f"/api/admin/newsletter/subscribers/{subscriber.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify deleted from DB
        assert test_repo.get_by_id(subscriber.id) is None

    def test_delete_not_found(self, client: TestClient) -> None:
        """Returns 404 for non-existent subscriber."""
        fake_id = uuid4()
        response = client.delete(f"/api/admin/newsletter/subscribers/{fake_id}")

        assert response.status_code == 404


# --- Export CSV Tests (TA-0087) ---


class TestExportSubscribers:
    """Tests for GET /api/admin/newsletter/subscribers/export/csv."""

    def test_export_csv(
        self, client: TestClient, sample_subscribers: list[NewsletterSubscriber]
    ) -> None:
        """TA-0087: Export subscribers to CSV."""
        response = client.get("/api/admin/newsletter/subscribers/export/csv")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]

        # Parse CSV content
        content = response.text
        lines = content.strip().split("\n")
        assert len(lines) == 4  # header + 3 subscribers
        assert "email,status,created_at,confirmed_at,unsubscribed_at" in lines[0]

    def test_export_csv_with_filter(
        self, client: TestClient, sample_subscribers: list[NewsletterSubscriber]
    ) -> None:
        """TA-0087: Export filtered subscribers."""
        response = client.get("/api/admin/newsletter/subscribers/export/csv?status=confirmed")

        assert response.status_code == 200
        content = response.text
        lines = content.strip().split("\n")
        assert len(lines) == 2  # header + 1 confirmed subscriber

    def test_export_csv_no_tokens(
        self, client: TestClient, sample_subscribers: list[NewsletterSubscriber]
    ) -> None:
        """CSV export doesn't include tokens (security)."""
        response = client.get("/api/admin/newsletter/subscribers/export/csv")

        assert response.status_code == 200
        content = response.text
        assert "token" not in content.lower()
        assert "confirmation_token" not in content
        assert "unsubscribe_token" not in content


# --- Stats Endpoint Tests ---


class TestNewsletterStats:
    """Tests for GET /api/admin/newsletter/stats."""

    def test_get_stats(
        self, client: TestClient, sample_subscribers: list[NewsletterSubscriber]
    ) -> None:
        """Get subscriber statistics."""
        response = client.get("/api/admin/newsletter/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["pending"] == 1
        assert data["confirmed"] == 1
        assert data["unsubscribed"] == 1

    def test_get_stats_empty(self, client: TestClient) -> None:
        """Stats with no subscribers."""
        response = client.get("/api/admin/newsletter/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["pending"] == 0
        assert data["confirmed"] == 0
        assert data["unsubscribed"] == 0
