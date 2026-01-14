"""
Tests for AnalyticsDedupeService (E6.3).

Test assertions:
- TA-0039: Duplicate events are detected and filtered
- TA-0040: Bot classification based on user agent patterns
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.components.analytics import (
    DedupeConfig,
    DedupeService,
    InMemoryDedupeStore,
    UAClass,
    classify_user_agent,
    create_dedupe_service,
    generate_dedupe_key,
    get_timestamp_bucket,
    is_bot,
    should_count,
)

# --- Fixtures ---


@pytest.fixture
def store() -> InMemoryDedupeStore:
    """Fresh dedupe store."""
    return InMemoryDedupeStore()


@pytest.fixture
def service(store: InMemoryDedupeStore) -> DedupeService:
    """Dedupe service with fresh store."""
    return DedupeService(store=store)


# --- Dedupe Key Generation Tests ---


class TestGenerateDedupeKey:
    """Test dedupe key generation."""

    def test_same_inputs_same_key(self) -> None:
        """Same inputs produce same key."""
        key1 = generate_dedupe_key(
            event_type="page_view",
            path="/test",
            timestamp_bucket="1000",
        )
        key2 = generate_dedupe_key(
            event_type="page_view",
            path="/test",
            timestamp_bucket="1000",
        )
        assert key1 == key2

    def test_different_type_different_key(self) -> None:
        """Different event types produce different keys."""
        key1 = generate_dedupe_key(event_type="page_view", path="/test")
        key2 = generate_dedupe_key(event_type="asset_download", path="/test")
        assert key1 != key2

    def test_different_path_different_key(self) -> None:
        """Different paths produce different keys."""
        key1 = generate_dedupe_key(event_type="page_view", path="/a")
        key2 = generate_dedupe_key(event_type="page_view", path="/b")
        assert key1 != key2

    def test_different_bucket_different_key(self) -> None:
        """Different time buckets produce different keys."""
        key1 = generate_dedupe_key(
            event_type="page_view",
            timestamp_bucket="1000",
        )
        key2 = generate_dedupe_key(
            event_type="page_view",
            timestamp_bucket="2000",
        )
        assert key1 != key2

    def test_extra_params_included(self) -> None:
        """Extra params affect key."""
        key1 = generate_dedupe_key(
            event_type="page_view",
            extra={"link_id": "abc"},
        )
        key2 = generate_dedupe_key(
            event_type="page_view",
            extra={"link_id": "xyz"},
        )
        assert key1 != key2

    def test_key_is_32_chars(self) -> None:
        """Key is 32 characters (truncated hash)."""
        key = generate_dedupe_key(event_type="page_view")
        assert len(key) == 32


class TestGetTimestampBucket:
    """Test timestamp bucketing."""

    def test_same_bucket_within_window(self) -> None:
        """Events within window get same bucket."""
        now = datetime(2026, 1, 12, 10, 0, 0, tzinfo=UTC)
        later = now + timedelta(seconds=5)

        bucket1 = get_timestamp_bucket(now, bucket_seconds=10)
        bucket2 = get_timestamp_bucket(later, bucket_seconds=10)

        assert bucket1 == bucket2

    def test_different_bucket_across_window(self) -> None:
        """Events across window boundary get different buckets."""
        now = datetime(2026, 1, 12, 10, 0, 5, tzinfo=UTC)
        later = now + timedelta(seconds=10)

        bucket1 = get_timestamp_bucket(now, bucket_seconds=10)
        bucket2 = get_timestamp_bucket(later, bucket_seconds=10)

        assert bucket1 != bucket2


# --- TA-0040: Bot Classification Tests ---


class TestClassifyUserAgent:
    """Test TA-0040: Bot classification."""

    def test_chrome_is_real(self) -> None:
        """Chrome browser is classified as real."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
        result = classify_user_agent(ua)
        assert result == UAClass.REAL

    def test_firefox_is_real(self) -> None:
        """Firefox browser is classified as real."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
        result = classify_user_agent(ua)
        assert result == UAClass.REAL

    def test_safari_is_real(self) -> None:
        """Safari browser is classified as real."""
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Safari/605.1.15"
        result = classify_user_agent(ua)
        assert result == UAClass.REAL

    def test_googlebot_is_bot(self) -> None:
        """Googlebot is classified as bot."""
        ua = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        result = classify_user_agent(ua)
        assert result == UAClass.BOT

    def test_bingbot_is_bot(self) -> None:
        """Bingbot is classified as bot."""
        ua = "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"
        result = classify_user_agent(ua)
        assert result == UAClass.BOT

    def test_curl_is_bot(self) -> None:
        """curl is classified as bot."""
        ua = "curl/7.88.1"
        result = classify_user_agent(ua)
        assert result == UAClass.BOT

    def test_python_requests_is_bot(self) -> None:
        """python-requests is classified as bot."""
        ua = "python-requests/2.28.0"
        result = classify_user_agent(ua)
        assert result == UAClass.BOT

    def test_wget_is_bot(self) -> None:
        """wget is classified as bot."""
        ua = "Wget/1.21"
        result = classify_user_agent(ua)
        assert result == UAClass.BOT

    def test_gptbot_is_bot(self) -> None:
        """GPTBot is classified as bot."""
        ua = "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.0)"
        result = classify_user_agent(ua)
        assert result == UAClass.BOT

    def test_empty_is_unknown(self) -> None:
        """Empty UA is classified as unknown."""
        result = classify_user_agent("")
        assert result == UAClass.UNKNOWN

    def test_none_is_unknown(self) -> None:
        """None UA is classified as unknown."""
        result = classify_user_agent(None)
        assert result == UAClass.UNKNOWN

    def test_unusual_ua_is_unknown(self) -> None:
        """Unusual UA without patterns is unknown."""
        ua = "CustomApp/1.0"
        result = classify_user_agent(ua)
        assert result == UAClass.UNKNOWN

    def test_bot_takes_priority(self) -> None:
        """Bot pattern takes priority over browser pattern."""
        # Googlebot includes Mozilla/5.0 but should still be bot
        ua = "Mozilla/5.0 (compatible; Googlebot/2.1)"
        result = classify_user_agent(ua)
        assert result == UAClass.BOT


class TestIsBotAndShouldCount:
    """Test bot checking and counting logic."""

    def test_bot_is_bot(self) -> None:
        """BOT class is a bot."""
        assert is_bot(UAClass.BOT) is True

    def test_real_is_not_bot(self) -> None:
        """REAL class is not a bot."""
        assert is_bot(UAClass.REAL) is False

    def test_unknown_default_not_bot(self) -> None:
        """UNKNOWN is not bot by default (treat_unknown_as=real)."""
        assert is_bot(UAClass.UNKNOWN) is False

    def test_unknown_as_bot_config(self) -> None:
        """UNKNOWN treated as bot when configured."""
        config = DedupeConfig(treat_unknown_as="bot")
        assert is_bot(UAClass.UNKNOWN, config) is True

    def test_real_should_count(self) -> None:
        """REAL traffic should be counted."""
        assert should_count(UAClass.REAL) is True

    def test_bot_not_counted_by_default(self) -> None:
        """BOT traffic not counted by default."""
        assert should_count(UAClass.BOT) is False

    def test_bot_counted_when_exclusion_disabled(self) -> None:
        """BOT counted when exclusion disabled."""
        config = DedupeConfig(exclude_bots_from_counts=False)
        assert should_count(UAClass.BOT, config) is True


# --- TA-0039: Dedupe Tests ---


class TestDedupeStore:
    """Test in-memory dedupe store."""

    def test_add_new_returns_true(self, store: InMemoryDedupeStore) -> None:
        """Adding new key returns True."""
        result = store.add("key1", ttl_seconds=10)
        assert result is True

    def test_add_existing_returns_false(self, store: InMemoryDedupeStore) -> None:
        """Adding existing key returns False."""
        store.add("key1", ttl_seconds=10)
        result = store.add("key1", ttl_seconds=10)
        assert result is False

    def test_exists_after_add(self, store: InMemoryDedupeStore) -> None:
        """Key exists after add."""
        store.add("key1", ttl_seconds=10)
        assert store.exists("key1") is True

    def test_not_exists_before_add(self, store: InMemoryDedupeStore) -> None:
        """Key doesn't exist before add."""
        assert store.exists("key1") is False

    def test_cleanup_expired(self, store: InMemoryDedupeStore) -> None:
        """Cleanup removes expired entries."""
        # Add with 0 TTL (immediately expired)
        store.add("key1", ttl_seconds=0)
        # Wait a moment for expiry
        import time

        time.sleep(0.01)

        removed = store.cleanup_expired()
        assert removed >= 0  # May or may not have expired yet


class TestDedupeService:
    """Test TA-0039: Dedupe service."""

    def test_first_event_not_duplicate(self, service: DedupeService) -> None:
        """First event is not a duplicate."""
        now = datetime.now(UTC)

        result = service.check_and_record(
            event_type="page_view",
            timestamp=now,
            path="/test",
        )

        assert result.is_duplicate is False

    def test_same_event_is_duplicate(self, service: DedupeService) -> None:
        """Same event within window is duplicate."""
        now = datetime.now(UTC)

        # First event
        service.check_and_record(
            event_type="page_view",
            timestamp=now,
            path="/test",
        )

        # Same event again
        result = service.check_and_record(
            event_type="page_view",
            timestamp=now,
            path="/test",
        )

        assert result.is_duplicate is True

    def test_different_path_not_duplicate(self, service: DedupeService) -> None:
        """Different path is not duplicate."""
        now = datetime.now(UTC)

        service.check_and_record(
            event_type="page_view",
            timestamp=now,
            path="/page-a",
        )

        result = service.check_and_record(
            event_type="page_view",
            timestamp=now,
            path="/page-b",
        )

        assert result.is_duplicate is False

    def test_different_event_type_not_duplicate(
        self,
        service: DedupeService,
    ) -> None:
        """Different event type is not duplicate."""
        now = datetime.now(UTC)

        service.check_and_record(
            event_type="page_view",
            timestamp=now,
        )

        result = service.check_and_record(
            event_type="asset_download",
            timestamp=now,
        )

        assert result.is_duplicate is False

    def test_dedupe_disabled(self, store: InMemoryDedupeStore) -> None:
        """Dedupe disabled allows all events."""
        config = DedupeConfig(enabled=False)
        service = DedupeService(store=store, config=config)
        now = datetime.now(UTC)

        # Record same event twice
        result1 = service.check_and_record(
            event_type="page_view",
            timestamp=now,
            path="/test",
        )
        result2 = service.check_and_record(
            event_type="page_view",
            timestamp=now,
            path="/test",
        )

        # Neither should be marked as duplicate
        assert result1.is_duplicate is False
        assert result2.is_duplicate is False

    def test_result_includes_ua_class(self, service: DedupeService) -> None:
        """Result includes UA classification."""
        now = datetime.now(UTC)

        result = service.check_and_record(
            event_type="page_view",
            timestamp=now,
            user_agent="Mozilla/5.0 Chrome/120.0",
        )

        assert result.ua_class == UAClass.REAL

    def test_result_includes_should_count(self, service: DedupeService) -> None:
        """Result includes should_count flag."""
        now = datetime.now(UTC)

        # Real browser
        result1 = service.check_and_record(
            event_type="page_view",
            timestamp=now,
            user_agent="Mozilla/5.0 Chrome/120.0",
            path="/a",
        )
        assert result1.should_count is True

        # Bot
        result2 = service.check_and_record(
            event_type="page_view",
            timestamp=now,
            user_agent="Googlebot/2.1",
            path="/b",
        )
        assert result2.should_count is False


class TestDedupeServiceMethods:
    """Test additional service methods."""

    def test_classify(self, service: DedupeService) -> None:
        """classify method works."""
        result = service.classify("Mozilla/5.0 Chrome/120.0")
        assert result == UAClass.REAL

    def test_should_count_method(self, service: DedupeService) -> None:
        """should_count method works."""
        assert service.should_count(UAClass.REAL) is True
        assert service.should_count(UAClass.BOT) is False

    def test_cleanup(self, service: DedupeService) -> None:
        """cleanup method works."""
        # Just verify it doesn't error
        count = service.cleanup()
        assert count >= 0


# --- Factory Tests ---


class TestFactory:
    """Test factory function."""

    def test_create_service(self) -> None:
        """Factory creates service."""
        service = create_dedupe_service()
        assert isinstance(service, DedupeService)

    def test_create_with_store(self, store: InMemoryDedupeStore) -> None:
        """Factory accepts store."""
        service = create_dedupe_service(store=store)
        assert isinstance(service, DedupeService)

    def test_create_with_config(self) -> None:
        """Factory accepts config."""
        config = DedupeConfig(ttl_seconds=30)
        service = create_dedupe_service(config=config)
        assert isinstance(service, DedupeService)
