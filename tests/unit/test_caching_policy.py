"""
TA-E2.3-01, TA-E2.3-02, TA-E2.3-03: Caching policy tests.

Tests for C2-PublicTemplates caching policy functionality:
- Cache policy determination (TA-E2.3-01)
- Draft isolation validation (TA-E2.3-02, R2)
- Sitemap filtering (TA-E2.3-03)
- Cache tag generation
- Revalidation adapter

These tests ensure caching policy adheres to R2 (draft isolation)
and provides correct cache headers for content states.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.components.C2_PublicTemplates import (
    RevalidationResult,
    StubRevalidationAdapter,
    determine_cache_policy,
    filter_sitemap_entries,
    generate_asset_cache_headers,
    generate_cache_headers,
    generate_cache_tag,
    generate_cache_tags,
    should_include_in_sitemap,
    validate_cache_policy_r2,
)
from src.components.C2_PublicTemplates.fc import (
    DEFAULT_IMMUTABLE_CACHE_CONTROL,
    DEFAULT_PRIVATE_CACHE_CONTROL,
    DEFAULT_PUBLISHED_CACHE_CONTROL,
)


@pytest.fixture
def now() -> datetime:
    """Fixed 'now' time for tests."""
    return datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def past_time(now: datetime) -> datetime:
    """Time in the past."""
    return now - timedelta(days=7)


@pytest.fixture
def future_time(now: datetime) -> datetime:
    """Time in the future."""
    return now + timedelta(days=7)


class TestCachePolicyDetermination:
    """TA-E2.3-01: Cache policy determination tests."""

    def test_published_content_is_publicly_cacheable(self, now: datetime) -> None:
        """Published content can be cached publicly."""
        policy = determine_cache_policy("published", None, now)

        assert policy.is_public is True
        assert policy.can_be_cached is True
        assert "public" in policy.cache_control
        assert "no-store" not in policy.cache_control

    def test_published_with_past_date_is_cacheable(
        self, now: datetime, past_time: datetime
    ) -> None:
        """Published content with past date is cacheable."""
        policy = determine_cache_policy("published", past_time, now)

        assert policy.is_public is True
        assert policy.can_be_cached is True

    def test_published_with_future_date_is_not_cacheable(
        self, now: datetime, future_time: datetime
    ) -> None:
        """Published content with future date is NOT cacheable (R2)."""
        policy = determine_cache_policy("published", future_time, now)

        assert policy.is_public is False
        assert policy.can_be_cached is False
        assert "no-store" in policy.cache_control

    def test_draft_is_never_publicly_cacheable(self, now: datetime) -> None:
        """Draft content is never publicly cacheable (R2)."""
        policy = determine_cache_policy("draft", None, now)

        assert policy.is_public is False
        assert policy.can_be_cached is False
        assert "private" in policy.cache_control
        assert "no-store" in policy.cache_control

    def test_scheduled_future_is_not_cacheable(
        self, now: datetime, future_time: datetime
    ) -> None:
        """Scheduled content with future date is NOT cacheable (R2)."""
        policy = determine_cache_policy("scheduled", future_time, now)

        assert policy.is_public is False
        assert policy.can_be_cached is False

    def test_scheduled_past_is_cacheable(
        self, now: datetime, past_time: datetime
    ) -> None:
        """Scheduled content that has 'gone live' is cacheable."""
        policy = determine_cache_policy("scheduled", past_time, now)

        assert policy.is_public is True
        assert policy.can_be_cached is True

    def test_archived_is_not_publicly_cacheable(self, now: datetime) -> None:
        """Archived content is not publicly cacheable."""
        policy = determine_cache_policy("archived", None, now)

        assert policy.is_public is False
        assert policy.can_be_cached is False

    def test_unknown_state_defaults_to_private(self, now: datetime) -> None:
        """Unknown state defaults to private."""
        policy = determine_cache_policy("unknown_state", None, now)

        assert policy.is_public is False
        assert policy.can_be_cached is False


class TestCacheHeaders:
    """TA-E2.3-01: Cache header generation tests."""

    def test_generates_cache_control_header(self, now: datetime) -> None:
        """Generates Cache-Control header from policy."""
        policy = determine_cache_policy("published", None, now)
        headers = generate_cache_headers(policy)

        assert "Cache-Control" in headers
        assert headers["Cache-Control"] == DEFAULT_PUBLISHED_CACHE_CONTROL

    def test_adds_etag_when_provided(self, now: datetime) -> None:
        """Adds ETag header when provided."""
        policy = determine_cache_policy("published", None, now)
        headers = generate_cache_headers(policy, etag="abc123")

        assert "ETag" in headers
        assert headers["ETag"] == '"abc123"'

    def test_adds_vary_for_private_responses(self, now: datetime) -> None:
        """Adds Vary header for private responses."""
        policy = determine_cache_policy("draft", None, now)
        headers = generate_cache_headers(policy)

        assert "Vary" in headers
        assert headers["Vary"] == "Cookie"

    def test_no_vary_for_public_responses(self, now: datetime) -> None:
        """No Vary header for public responses."""
        policy = determine_cache_policy("published", None, now)
        headers = generate_cache_headers(policy)

        assert "Vary" not in headers


class TestAssetCacheHeaders:
    """Asset cache header tests."""

    def test_immutable_assets_have_long_cache(self) -> None:
        """Immutable assets have long cache time."""
        headers = generate_asset_cache_headers(is_immutable=True)

        assert headers["Cache-Control"] == DEFAULT_IMMUTABLE_CACHE_CONTROL
        assert "immutable" in headers["Cache-Control"]

    def test_mutable_assets_have_short_cache(self) -> None:
        """Mutable assets have shorter cache time."""
        headers = generate_asset_cache_headers(is_immutable=False)

        assert "immutable" not in headers["Cache-Control"]

    def test_asset_etag_included(self) -> None:
        """Asset ETag is included when provided."""
        headers = generate_asset_cache_headers(etag="file-hash")

        assert headers["ETag"] == '"file-hash"'


class TestDraftIsolationValidation:
    """TA-E2.3-02: Draft isolation validation tests (R2)."""

    def test_draft_with_public_cache_is_violation(self, now: datetime) -> None:
        """Draft content with public cache headers violates R2."""
        result = validate_cache_policy_r2(
            content_state="draft",
            published_at=None,
            cache_control="public, max-age=300",
            now=now,
        )

        assert result.is_valid is False
        assert len(result.violations) > 0
        assert "R2" in result.violations[0]

    def test_draft_with_private_cache_is_valid(self, now: datetime) -> None:
        """Draft content with private cache headers is valid."""
        result = validate_cache_policy_r2(
            content_state="draft",
            published_at=None,
            cache_control=DEFAULT_PRIVATE_CACHE_CONTROL,
            now=now,
        )

        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_scheduled_future_with_public_cache_is_violation(
        self, now: datetime, future_time: datetime
    ) -> None:
        """Future scheduled content with public cache violates R2."""
        result = validate_cache_policy_r2(
            content_state="scheduled",
            published_at=future_time,
            cache_control="public, s-maxage=300",
            now=now,
        )

        assert result.is_valid is False
        assert "R2" in result.violations[0]

    def test_published_with_public_cache_is_valid(self, now: datetime) -> None:
        """Published content with public cache is valid."""
        result = validate_cache_policy_r2(
            content_state="published",
            published_at=None,
            cache_control=DEFAULT_PUBLISHED_CACHE_CONTROL,
            now=now,
        )

        assert result.is_valid is True

    def test_archived_with_public_cache_is_violation(self, now: datetime) -> None:
        """Archived content with public cache violates R2."""
        result = validate_cache_policy_r2(
            content_state="archived",
            published_at=None,
            cache_control="public, max-age=300",
            now=now,
        )

        assert result.is_valid is False


class TestSitemapFiltering:
    """TA-E2.3-03: Sitemap filtering tests."""

    def test_published_content_included_in_sitemap(
        self, now: datetime, past_time: datetime
    ) -> None:
        """Published content is included in sitemap."""
        assert should_include_in_sitemap("published", past_time, now) is True

    def test_draft_excluded_from_sitemap(self, now: datetime) -> None:
        """Draft content is excluded from sitemap."""
        assert should_include_in_sitemap("draft", None, now) is False

    def test_scheduled_excluded_from_sitemap(self, now: datetime) -> None:
        """Scheduled content is excluded from sitemap."""
        assert should_include_in_sitemap("scheduled", None, now) is False

    def test_archived_excluded_from_sitemap(self, now: datetime) -> None:
        """Archived content is excluded from sitemap."""
        assert should_include_in_sitemap("archived", None, now) is False

    def test_published_with_future_date_excluded(
        self, now: datetime, future_time: datetime
    ) -> None:
        """Published content with future date is excluded."""
        assert should_include_in_sitemap("published", future_time, now) is False

    def test_filter_sitemap_entries_excludes_drafts(
        self, now: datetime, past_time: datetime
    ) -> None:
        """filter_sitemap_entries excludes non-published content."""
        entries = [
            ("post-1", "post", past_time, past_time),
            ("draft-1", "post", None, None),  # Will be filtered (no published_at)
        ]

        result = filter_sitemap_entries(entries, "https://example.com", now)

        # Only published entry should be included
        assert len(result) == 1
        assert "post-1" in result[0].loc

    def test_sitemap_entry_has_correct_url(
        self, now: datetime, past_time: datetime
    ) -> None:
        """Sitemap entry has correct URL format."""
        entries = [("my-post", "post", past_time, past_time)]

        result = filter_sitemap_entries(entries, "https://example.com", now)

        assert result[0].loc == "https://example.com/p/my-post"

    def test_sitemap_entry_for_resource(
        self, now: datetime, past_time: datetime
    ) -> None:
        """Resource entries use /r/ path."""
        entries = [("my-resource", "resource", past_time, past_time)]

        result = filter_sitemap_entries(entries, "https://example.com", now)

        assert result[0].loc == "https://example.com/r/my-resource"

    def test_sitemap_entry_has_lastmod(
        self, now: datetime, past_time: datetime
    ) -> None:
        """Sitemap entry has lastmod date."""
        entries = [("post-1", "post", past_time, past_time)]

        result = filter_sitemap_entries(entries, "https://example.com", now)

        assert result[0].lastmod is not None
        assert "2024-06-08" in result[0].lastmod


class TestCacheTagGeneration:
    """Cache tag generation tests."""

    def test_generates_single_tag(self) -> None:
        """Generates single cache tag."""
        tag = generate_cache_tag("post", "123")

        assert tag == "content:post:123"

    def test_respects_custom_prefix(self) -> None:
        """Respects custom tag prefix."""
        tag = generate_cache_tag("post", "123", tag_prefix="cache:")

        assert tag == "cache:post:123"

    def test_generates_multiple_tags(self) -> None:
        """Generates multiple cache tags."""
        tags = generate_cache_tags("post", "123", slug="my-post")

        assert "content:post:123" in tags
        assert "content:post:slug:my-post" in tags
        assert "content:post:all" in tags

    def test_generates_tags_without_slug(self) -> None:
        """Generates tags without slug."""
        tags = generate_cache_tags("resource", "456")

        assert "content:resource:456" in tags
        assert "content:resource:all" in tags
        assert len([t for t in tags if "slug" in t]) == 0


class TestRevalidationAdapter:
    """Revalidation adapter tests."""

    def test_stub_adapter_records_tag_revalidation(self) -> None:
        """Stub adapter records tag revalidation calls."""
        adapter = StubRevalidationAdapter()

        result = adapter.revalidate_tag("content:post:123")

        assert result is True
        assert "content:post:123" in adapter.revalidated_tags

    def test_stub_adapter_records_path_revalidation(self) -> None:
        """Stub adapter records path revalidation calls."""
        adapter = StubRevalidationAdapter()

        result = adapter.revalidate_path("/p/my-post")

        assert result is True
        assert "/p/my-post" in adapter.revalidated_paths

    def test_revalidate_multiple_tags(self) -> None:
        """Revalidates multiple tags."""
        adapter = StubRevalidationAdapter()
        tags = ["content:post:1", "content:post:2"]

        results = adapter.revalidate_tags(tags)

        assert all(results.values())
        assert len(adapter.revalidated_tags) == 2

    def test_revalidate_content(self) -> None:
        """Revalidates all tags for content."""
        adapter = StubRevalidationAdapter()

        result = adapter.revalidate_content(
            content_type="post",
            content_id="123",
            slug="my-post",
        )

        assert isinstance(result, RevalidationResult)
        assert result.success is True
        assert len(result.tags_revalidated) >= 2

    def test_stub_adapter_reset(self) -> None:
        """Stub adapter can be reset."""
        adapter = StubRevalidationAdapter()
        adapter.revalidate_tag("test")
        adapter.revalidate_path("/test")

        adapter.reset()

        assert len(adapter.revalidated_tags) == 0
        assert len(adapter.revalidated_paths) == 0
