"""
TA-0103: Repository contract tests.

Verifies that the SQLite repository implementations satisfy their port contracts.
These tests ensure Postgres-compatible behavior by testing against abstract interfaces.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from src.adapters.sqlite_db import (
    SQLiteAnalyticsAggregateRepo,
    SQLiteAssetVersionRepo,
    SQLiteAuditLogRepo,
    SQLiteNewsletterSubscriberRepo,
    SQLitePublishJobRepo,
    SQLiteRedirectRepo,
    SQLiteUnitOfWork,
)
from src.components.newsletter.models import NewsletterSubscriber, SubscriberStatus
from src.core.entities import (
    AssetVersion,
    AuditEvent,
    PublishJob,
    RedirectRule,
)


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Create a temporary database with v3 schema."""
    db_file = tmp_path / "test.db"
    import sqlite3

    conn = sqlite3.connect(str(db_file))
    # Create v3 tables
    conn.executescript(
        """
        -- Asset versions (E4)
        CREATE TABLE IF NOT EXISTS asset_versions (
            id TEXT PRIMARY KEY,
            asset_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            storage_key TEXT NOT NULL UNIQUE,
            sha256 TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            mime_type TEXT NOT NULL,
            filename_original TEXT NOT NULL,
            is_latest INTEGER DEFAULT 0,
            created_by_user_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Publish jobs (E5)
        CREATE TABLE IF NOT EXISTS publish_jobs (
            id TEXT PRIMARY KEY,
            content_id TEXT NOT NULL,
            publish_at_utc TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            attempts INTEGER DEFAULT 0,
            last_attempt_at TEXT,
            next_retry_at TEXT,
            completed_at TEXT,
            actual_publish_at TEXT,
            error_message TEXT,
            claimed_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(content_id, publish_at_utc)
        );

        -- Analytics aggregates (E6)
        CREATE TABLE IF NOT EXISTS analytics_aggregates (
            id TEXT PRIMARY KEY,
            bucket_type TEXT NOT NULL,
            bucket_start TEXT NOT NULL,
            event_type TEXT NOT NULL,
            content_id TEXT,
            asset_id TEXT,
            link_id TEXT,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            referrer_domain TEXT,
            ua_class TEXT DEFAULT 'unknown',
            count_total INTEGER DEFAULT 0,
            count_real INTEGER DEFAULT 0,
            count_bot INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Redirect rules (E7)
        CREATE TABLE IF NOT EXISTS redirect_rules (
            id TEXT PRIMARY KEY,
            source_path TEXT NOT NULL UNIQUE,
            target_path TEXT NOT NULL,
            status_code INTEGER DEFAULT 301,
            is_active INTEGER DEFAULT 1,
            preserve_query_params INTEGER DEFAULT 1,
            created_by_user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Audit events (E8)
        CREATE TABLE IF NOT EXISTS audit_events (
            id TEXT PRIMARY KEY,
            actor_user_id TEXT,
            action TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            meta_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Newsletter subscribers (E16)
        CREATE TABLE IF NOT EXISTS newsletter_subscribers (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL CHECK(status IN ('pending', 'confirmed', 'unsubscribed')),
            confirmation_token TEXT,
            unsubscribe_token TEXT,
            created_at TEXT NOT NULL,
            confirmed_at TEXT,
            unsubscribed_at TEXT
        );
        """
    )
    conn.commit()
    conn.close()
    return str(db_file)


class TestAssetVersionRepoContract:
    """TA-0103: AssetVersion repository contract tests."""

    def test_save_and_get_by_id(self, db_path: str) -> None:
        """Versions can be saved and retrieved by ID."""
        repo = SQLiteAssetVersionRepo(db_path)
        user_id = uuid4()
        asset_id = uuid4()

        version = AssetVersion(
            id=uuid4(),
            asset_id=asset_id,
            version_number=1,
            storage_key=f"assets/{asset_id}/v1",
            sha256="abc123",
            size_bytes=1024,
            mime_type="image/png",
            filename_original="test.png",
            is_latest=True,
            created_by_user_id=user_id,
        )

        repo.save(version)
        retrieved = repo.get_by_id(version.id)

        assert retrieved is not None
        assert retrieved.id == version.id
        assert retrieved.sha256 == "abc123"
        assert retrieved.is_latest is True

    def test_get_by_storage_key(self, db_path: str) -> None:
        """Versions can be retrieved by storage key."""
        repo = SQLiteAssetVersionRepo(db_path)
        user_id = uuid4()
        asset_id = uuid4()
        storage_key = f"assets/{asset_id}/v1"

        version = AssetVersion(
            id=uuid4(),
            asset_id=asset_id,
            version_number=1,
            storage_key=storage_key,
            sha256="xyz789",
            size_bytes=2048,
            mime_type="application/pdf",
            filename_original="doc.pdf",
            created_by_user_id=user_id,
        )

        repo.save(version)
        retrieved = repo.get_by_storage_key(storage_key)

        assert retrieved is not None
        assert retrieved.storage_key == storage_key

    def test_list_by_asset_ordered(self, db_path: str) -> None:
        """Versions are listed in version_number order."""
        repo = SQLiteAssetVersionRepo(db_path)
        user_id = uuid4()
        asset_id = uuid4()

        # Save versions out of order
        for v in [3, 1, 2]:
            version = AssetVersion(
                id=uuid4(),
                asset_id=asset_id,
                version_number=v,
                storage_key=f"assets/{asset_id}/v{v}",
                sha256=f"hash{v}",
                size_bytes=1024 * v,
                mime_type="image/png",
                filename_original="test.png",
                created_by_user_id=user_id,
            )
            repo.save(version)

        versions = repo.list_by_asset(asset_id)
        assert len(versions) == 3
        assert [v.version_number for v in versions] == [1, 2, 3]

    def test_set_latest_clears_previous(self, db_path: str) -> None:
        """Setting latest clears previous latest flag."""
        repo = SQLiteAssetVersionRepo(db_path)
        user_id = uuid4()
        asset_id = uuid4()

        v1 = AssetVersion(
            id=uuid4(),
            asset_id=asset_id,
            version_number=1,
            storage_key=f"assets/{asset_id}/v1",
            sha256="hash1",
            size_bytes=1024,
            mime_type="image/png",
            filename_original="test.png",
            is_latest=True,
            created_by_user_id=user_id,
        )
        v2 = AssetVersion(
            id=uuid4(),
            asset_id=asset_id,
            version_number=2,
            storage_key=f"assets/{asset_id}/v2",
            sha256="hash2",
            size_bytes=2048,
            mime_type="image/png",
            filename_original="test.png",
            is_latest=False,
            created_by_user_id=user_id,
        )

        repo.save(v1)
        repo.save(v2)

        # v1 is latest initially
        assert repo.get_latest(asset_id).id == v1.id  # type: ignore[union-attr]

        # Set v2 as latest
        repo.set_latest(asset_id, v2.id)

        # Now v2 is latest, v1 is not
        latest = repo.get_latest(asset_id)
        assert latest is not None
        assert latest.id == v2.id

        v1_updated = repo.get_by_id(v1.id)
        assert v1_updated is not None
        assert v1_updated.is_latest is False


class TestPublishJobRepoContract:
    """TA-0103: PublishJob repository contract tests."""

    def test_idempotency_key_unique(self, db_path: str) -> None:
        """Idempotency key (content_id, publish_at_utc) is unique."""
        repo = SQLitePublishJobRepo(db_path)
        content_id = uuid4()
        publish_at = datetime.now(UTC) + timedelta(hours=1)

        job1 = PublishJob(
            content_id=content_id,
            publish_at_utc=publish_at,
        )

        job2 = PublishJob(
            content_id=content_id,
            publish_at_utc=publish_at,
        )

        # First save succeeds
        repo.save(job1)

        # Second save with same idempotency key raises
        with pytest.raises(sqlite3.IntegrityError):
            repo.save(job2)

    def test_create_if_not_exists_idempotent(self, db_path: str) -> None:
        """create_if_not_exists returns existing job if present."""
        repo = SQLitePublishJobRepo(db_path)
        content_id = uuid4()
        publish_at = datetime.now(UTC) + timedelta(hours=1)

        job = PublishJob(
            content_id=content_id,
            publish_at_utc=publish_at,
        )

        # First call creates
        result1, created1 = repo.create_if_not_exists(job)
        assert created1 is True
        assert result1.id == job.id

        # Second call returns existing
        job2 = PublishJob(
            content_id=content_id,
            publish_at_utc=publish_at,
        )
        result2, created2 = repo.create_if_not_exists(job2)
        assert created2 is False
        assert result2.id == job.id  # Returns original

    def test_claim_next_runnable_sets_status(self, db_path: str) -> None:
        """claim_next_runnable sets status to running."""
        repo = SQLitePublishJobRepo(db_path)
        content_id = uuid4()
        now = datetime.now(UTC)
        past = now - timedelta(minutes=5)

        job = PublishJob(
            content_id=content_id,
            publish_at_utc=past,
            status="queued",
        )
        repo.save(job)

        claimed = repo.claim_next_runnable("worker-1", now)
        assert claimed is not None
        assert claimed.status == "running"
        assert claimed.claimed_by == "worker-1"

    def test_claim_respects_publish_time(self, db_path: str) -> None:
        """Jobs are not claimed before their publish time."""
        repo = SQLitePublishJobRepo(db_path)
        content_id = uuid4()
        now = datetime.now(UTC)
        future = now + timedelta(hours=1)

        job = PublishJob(
            content_id=content_id,
            publish_at_utc=future,
            status="queued",
        )
        repo.save(job)

        # Should not claim future job
        claimed = repo.claim_next_runnable("worker-1", now)
        assert claimed is None


class TestAnalyticsAggregateRepoContract:
    """TA-0103: AnalyticsEventAggregate repository contract tests."""

    def test_get_or_create_bucket_creates(self, db_path: str) -> None:
        """get_or_create_bucket creates new bucket if not exists."""
        repo = SQLiteAnalyticsAggregateRepo(db_path)
        bucket_start = datetime(2026, 1, 11, 10, 0, 0)

        bucket = repo.get_or_create_bucket(
            bucket_type="hour",
            bucket_start=bucket_start,
            event_type="page_view",
            dimensions={"utm_source": "twitter", "ua_class": "real"},
        )

        assert bucket.bucket_type == "hour"
        assert bucket.event_type == "page_view"
        assert bucket.count_total == 0

    def test_increment_updates_counts(self, db_path: str) -> None:
        """increment updates aggregate counts."""
        repo = SQLiteAnalyticsAggregateRepo(db_path)
        bucket_start = datetime(2026, 1, 11, 10, 0, 0)

        bucket = repo.get_or_create_bucket(
            bucket_type="hour",
            bucket_start=bucket_start,
            event_type="page_view",
            dimensions={"ua_class": "real"},
        )

        repo.increment(bucket.id, count_total=5, count_real=4, count_bot=1)

        # Query to verify
        results = repo.query(
            bucket_type="hour",
            start=bucket_start,
            end=bucket_start + timedelta(hours=1),
            event_type="page_view",
        )
        assert len(results) == 1
        assert results[0].count_total == 5
        assert results[0].count_real == 4
        assert results[0].count_bot == 1


class TestRedirectRepoContract:
    """TA-0103: RedirectRule repository contract tests."""

    def test_source_path_unique(self, db_path: str) -> None:
        """Source paths must be unique."""
        repo = SQLiteRedirectRepo(db_path)
        user_id = uuid4()

        rule1 = RedirectRule(
            source_path="/old-page",
            target_path="/new-page",
            created_by_user_id=user_id,
        )
        rule2 = RedirectRule(
            source_path="/old-page",
            target_path="/different-page",
            created_by_user_id=user_id,
        )

        repo.save(rule1)

        with pytest.raises(sqlite3.IntegrityError):
            repo.save(rule2)

    def test_get_by_source_path_active_only(self, db_path: str) -> None:
        """get_by_source_path only returns active rules."""
        repo = SQLiteRedirectRepo(db_path)
        user_id = uuid4()

        rule = RedirectRule(
            source_path="/inactive",
            target_path="/target",
            is_active=False,
            created_by_user_id=user_id,
        )
        repo.save(rule)

        result = repo.get_by_source_path("/inactive")
        assert result is None

    def test_list_active_filters(self, db_path: str) -> None:
        """list_active only returns active rules."""
        repo = SQLiteRedirectRepo(db_path)
        user_id = uuid4()

        for i, active in enumerate([True, False, True]):
            rule = RedirectRule(
                source_path=f"/path{i}",
                target_path="/target",
                is_active=active,
                created_by_user_id=user_id,
            )
            repo.save(rule)

        active_rules = repo.list_active()
        assert len(active_rules) == 2


class TestAuditLogRepoContract:
    """TA-0103: AuditLogEvent repository contract tests."""

    def test_append_only(self, db_path: str) -> None:
        """Audit events are append-only."""
        repo = SQLiteAuditLogRepo(db_path)
        user_id = uuid4()

        event = AuditEvent(
            actor_user_id=user_id,
            action="settings.update",
            target_type="settings",
            target_id="1",
            meta_json={"field": "site_title", "old": "Old", "new": "New"},
        )

        result = repo.append(event)
        assert result.id == event.id

        # Verify it's stored
        recent = repo.list_recent(10)
        assert len(recent) == 1
        assert recent[0].action == "settings.update"

    def test_list_by_target(self, db_path: str) -> None:
        """Events can be queried by target."""
        repo = SQLiteAuditLogRepo(db_path)
        user_id = uuid4()

        # Create events for different targets
        for target_id in ["content-1", "content-1", "content-2"]:
            event = AuditEvent(
                actor_user_id=user_id,
                action="content.update",
                target_type="content",
                target_id=target_id,
                meta_json={},
            )
            repo.append(event)

        results = repo.list_by_target("content", "content-1")
        assert len(results) == 2

    def test_list_by_actor(self, db_path: str) -> None:
        """Events can be queried by actor."""
        repo = SQLiteAuditLogRepo(db_path)
        user1 = uuid4()
        user2 = uuid4()

        for uid, count in [(user1, 3), (user2, 2)]:
            for _ in range(count):
                event = AuditEvent(
                    actor_user_id=uid,
                    action="test",
                    target_type="test",
                    target_id="1",
                    meta_json={},
                )
                repo.append(event)

        results = repo.list_by_actor(user1)
        assert len(results) == 3


class TestUnitOfWorkContract:
    """TA-0103: Unit of Work contract tests."""

    def test_transaction_commit(self, db_path: str) -> None:
        """Committed changes persist."""
        with SQLiteUnitOfWork(db_path) as uow:
            rule = RedirectRule(
                source_path="/test-commit",
                target_path="/target",
                created_by_user_id=uuid4(),
            )
            uow.redirects.save(rule)
            uow.commit()

        # Verify outside transaction
        repo = SQLiteRedirectRepo(db_path)
        result = repo.get_by_source_path("/test-commit")
        assert result is not None

    def test_transaction_rollback_on_exception(self, db_path: str) -> None:
        """Changes are rolled back on exception."""
        try:
            with SQLiteUnitOfWork(db_path) as uow:
                rule = RedirectRule(
                    source_path="/test-rollback",
                    target_path="/target",
                    created_by_user_id=uuid4(),
                )
                uow.redirects.save(rule)
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify change was rolled back
        repo = SQLiteRedirectRepo(db_path)
        result = repo.get_by_source_path("/test-rollback")
        assert result is None


class TestNewsletterSubscriberRepoContract:
    """TA-0103: NewsletterSubscriber repository contract tests."""

    def test_save_and_get_by_id(self, db_path: str) -> None:
        """Subscribers can be saved and retrieved by ID."""
        repo = SQLiteNewsletterSubscriberRepo(db_path)

        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.PENDING,
            confirmation_token="conf123",
            unsubscribe_token="unsub123",
            created_at=datetime.now(UTC),
        )

        repo.save(subscriber)
        retrieved = repo.get_by_id(subscriber.id)

        assert retrieved is not None
        assert retrieved.id == subscriber.id
        assert retrieved.email == subscriber.email
        assert retrieved.status == SubscriberStatus.PENDING

    def test_get_by_email(self, db_path: str) -> None:
        """Subscribers can be retrieved by email."""
        repo = SQLiteNewsletterSubscriberRepo(db_path)

        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="test@example.com",
            status=SubscriberStatus.PENDING,
        )
        repo.save(subscriber)

        # Should find by exact match
        retrieved = repo.get_by_email("test@example.com")
        assert retrieved is not None
        assert retrieved.id == subscriber.id

        # Should find by case-insensitive match
        retrieved2 = repo.get_by_email("TEST@Example.COM")
        assert retrieved2 is not None
        assert retrieved2.id == subscriber.id

    def test_get_by_confirmation_token(self, db_path: str) -> None:
        """Subscribers can be retrieved by confirmation token."""
        repo = SQLiteNewsletterSubscriberRepo(db_path)

        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.PENDING,
            confirmation_token="unique_conf_token",
        )
        repo.save(subscriber)

        retrieved = repo.get_by_confirmation_token("unique_conf_token")
        assert retrieved is not None
        assert retrieved.id == subscriber.id

        # Non-existent token returns None
        assert repo.get_by_confirmation_token("nonexistent") is None

    def test_get_by_unsubscribe_token(self, db_path: str) -> None:
        """Subscribers can be retrieved by unsubscribe token."""
        repo = SQLiteNewsletterSubscriberRepo(db_path)

        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.CONFIRMED,
            unsubscribe_token="unique_unsub_token",
        )
        repo.save(subscriber)

        retrieved = repo.get_by_unsubscribe_token("unique_unsub_token")
        assert retrieved is not None
        assert retrieved.id == subscriber.id

    def test_update_subscriber(self, db_path: str) -> None:
        """Subscribers can be updated."""
        repo = SQLiteNewsletterSubscriberRepo(db_path)

        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="user@example.com",
            status=SubscriberStatus.PENDING,
            confirmation_token="token",
        )
        repo.save(subscriber)

        # Update to confirmed
        confirmed = NewsletterSubscriber(
            id=subscriber.id,
            email=subscriber.email,
            status=SubscriberStatus.CONFIRMED,
            confirmation_token=None,  # Cleared
            confirmed_at=datetime.now(UTC),
        )
        repo.save(confirmed)

        retrieved = repo.get_by_id(subscriber.id)
        assert retrieved is not None
        assert retrieved.status == SubscriberStatus.CONFIRMED
        assert retrieved.confirmation_token is None
        assert retrieved.confirmed_at is not None

    def test_delete_subscriber(self, db_path: str) -> None:
        """Subscribers can be deleted (GDPR)."""
        repo = SQLiteNewsletterSubscriberRepo(db_path)

        subscriber = NewsletterSubscriber(
            id=uuid4(),
            email="delete@example.com",
            status=SubscriberStatus.CONFIRMED,
        )
        repo.save(subscriber)

        result = repo.delete(subscriber.id)
        assert result is True

        # Verify deleted
        assert repo.get_by_id(subscriber.id) is None
        assert repo.get_by_email("delete@example.com") is None

    def test_delete_nonexistent(self, db_path: str) -> None:
        """Deleting non-existent subscriber returns False."""
        repo = SQLiteNewsletterSubscriberRepo(db_path)
        result = repo.delete(uuid4())
        assert result is False

    def test_list_by_status(self, db_path: str) -> None:
        """Subscribers can be listed by status."""
        repo = SQLiteNewsletterSubscriberRepo(db_path)

        # Create subscribers with different statuses
        for i, status in enumerate([
            SubscriberStatus.PENDING,
            SubscriberStatus.CONFIRMED,
            SubscriberStatus.CONFIRMED,
            SubscriberStatus.UNSUBSCRIBED,
        ]):
            subscriber = NewsletterSubscriber(
                id=uuid4(),
                email=f"user{i}@example.com",
                status=status,
            )
            repo.save(subscriber)

        confirmed = repo.list_by_status(SubscriberStatus.CONFIRMED)
        assert len(confirmed) == 2

        pending = repo.list_by_status(SubscriberStatus.PENDING)
        assert len(pending) == 1

    def test_count_by_status(self, db_path: str) -> None:
        """Subscribers can be counted by status."""
        repo = SQLiteNewsletterSubscriberRepo(db_path)

        for i, status in enumerate([
            SubscriberStatus.PENDING,
            SubscriberStatus.CONFIRMED,
            SubscriberStatus.CONFIRMED,
        ]):
            subscriber = NewsletterSubscriber(
                id=uuid4(),
                email=f"count{i}@example.com",
                status=status,
            )
            repo.save(subscriber)

        assert repo.count_by_status(SubscriberStatus.CONFIRMED) == 2
        assert repo.count_by_status(SubscriberStatus.PENDING) == 1
        assert repo.count_by_status(SubscriberStatus.UNSUBSCRIBED) == 0

    def test_email_unique_constraint(self, db_path: str) -> None:
        """Email addresses must be unique."""
        repo = SQLiteNewsletterSubscriberRepo(db_path)

        sub1 = NewsletterSubscriber(
            id=uuid4(),
            email="unique@example.com",
            status=SubscriberStatus.PENDING,
        )
        sub2 = NewsletterSubscriber(
            id=uuid4(),
            email="unique@example.com",  # Same email
            status=SubscriberStatus.PENDING,
        )

        repo.save(sub1)

        with pytest.raises(sqlite3.IntegrityError):
            repo.save(sub2)

    def test_list_all_with_pagination(self, db_path: str) -> None:
        """list_all returns paginated results."""
        repo = SQLiteNewsletterSubscriberRepo(db_path)

        for i in range(5):
            subscriber = NewsletterSubscriber(
                id=uuid4(),
                email=f"page{i}@example.com",
                status=SubscriberStatus.CONFIRMED,
            )
            repo.save(subscriber)

        # First page
        page1 = repo.list_all(limit=2, offset=0)
        assert len(page1) == 2

        # Second page
        page2 = repo.list_all(limit=2, offset=2)
        assert len(page2) == 2

        # Third page (only 1 remaining)
        page3 = repo.list_all(limit=2, offset=4)
        assert len(page3) == 1

    def test_count_all(self, db_path: str) -> None:
        """count_all returns total subscriber count."""
        repo = SQLiteNewsletterSubscriberRepo(db_path)

        for i in range(3):
            subscriber = NewsletterSubscriber(
                id=uuid4(),
                email=f"total{i}@example.com",
                status=SubscriberStatus.CONFIRMED,
            )
            repo.save(subscriber)

        assert repo.count_all() == 3
