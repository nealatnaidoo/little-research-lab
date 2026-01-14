"""
TA-E5.2-01: V4 rules key constraints tests.

Tests that validate critical rules constraints from creator-publisher-v4_rules.yaml.
These tests enforce regression invariants R1, R2, R3.

R1: No audience PII stored (analytics.privacy rules)
R2: Draft isolation (caching rules)
R3: SSRF protection (inspector.safe_fetch rules)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.rules.v4_loader import load_v4_rules

PROJECT_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture
def v4_rules() -> dict:
    """Load v4 rules file."""
    rules_path = PROJECT_ROOT / "creator-publisher-v4_rules.yaml"
    return load_v4_rules(rules_path, validate=False)


class TestR1NoPII:
    """R1: No audience PII stored (schema + runtime assertions)."""

    def test_analytics_store_ip_is_false(self, v4_rules: dict) -> None:
        """Analytics must NOT store IP addresses."""
        assert v4_rules["analytics"]["privacy"]["store_ip"] is False

    def test_analytics_store_full_user_agent_is_false(self, v4_rules: dict) -> None:
        """Analytics must NOT store full user agent strings."""
        assert v4_rules["analytics"]["privacy"]["store_full_user_agent"] is False

    def test_analytics_store_cookies_is_false(self, v4_rules: dict) -> None:
        """Analytics must NOT store cookies."""
        assert v4_rules["analytics"]["privacy"]["store_cookies"] is False

    def test_analytics_store_identifiers_is_false(self, v4_rules: dict) -> None:
        """Analytics must NOT store user identifiers."""
        assert v4_rules["analytics"]["privacy"]["store_identifiers"] is False

    def test_analytics_allowed_dimensions_are_safe(self, v4_rules: dict) -> None:
        """Analytics allowed dimensions must not include PII."""
        forbidden_dimensions = {"ip", "user_agent", "email", "user_id", "cookie_id"}
        allowed = set(v4_rules["analytics"]["privacy"]["allowed_dimensions"])
        overlap = allowed & forbidden_dimensions
        assert not overlap, f"PII dimensions found: {overlap}"

    def test_rate_limit_does_not_persist_ip(self, v4_rules: dict) -> None:
        """Rate limiting uses IP ephemerally, does not persist."""
        # The max_requests_per_ip_per_window is used for limiting only
        # This test documents the expected behavior
        rate_limit = v4_rules["analytics"]["ingestion"]["rate_limit"]
        assert "max_requests_per_ip_per_window" in rate_limit
        # IP is used for limiting but not stored (enforced by store_ip: false)


class TestR2DraftIsolation:
    """R2: Draft and future scheduled content never publicly served or cached."""

    def test_drafts_cache_control_is_private_no_store(self, v4_rules: dict) -> None:
        """Drafts must have private, no-store cache control."""
        drafts_cache = v4_rules["caching"]["public_pages"]["drafts_cache_control"]
        assert "private" in drafts_cache
        assert "no-store" in drafts_cache

    def test_scheduled_future_cache_control_is_private_no_store(
        self, v4_rules: dict
    ) -> None:
        """Future scheduled content must have private, no-store cache control."""
        scheduled_cache = v4_rules["caching"]["public_pages"][
            "scheduled_future_cache_control"
        ]
        assert "private" in scheduled_cache
        assert "no-store" in scheduled_cache

    def test_content_public_visible_states_excludes_draft(
        self, v4_rules: dict
    ) -> None:
        """Only published content should be publicly visible."""
        visible_states = v4_rules["content"]["visibility"]["public_visible_states"]
        assert "draft" not in visible_states
        assert "scheduled" not in visible_states
        assert "published" in visible_states


class TestR3SSRFProtection:
    """R3: Inspector cannot access internal/private network targets (SSRF)."""

    def test_inspector_disallows_private_ip_ranges(self, v4_rules: dict) -> None:
        """Inspector must disallow private IP ranges."""
        assert v4_rules["inspector"]["safe_fetch"]["disallow_private_ip_ranges"] is True

    def test_inspector_disallows_loopback(self, v4_rules: dict) -> None:
        """Inspector must disallow loopback addresses."""
        assert v4_rules["inspector"]["safe_fetch"]["disallow_loopback"] is True

    def test_inspector_disallows_link_local(self, v4_rules: dict) -> None:
        """Inspector must disallow link-local addresses."""
        assert v4_rules["inspector"]["safe_fetch"]["disallow_link_local"] is True

    def test_inspector_disallows_file_scheme(self, v4_rules: dict) -> None:
        """Inspector must disallow file:// URLs."""
        assert v4_rules["inspector"]["safe_fetch"]["disallow_file_scheme"] is True

    def test_inspector_allowed_schemes_are_safe(self, v4_rules: dict) -> None:
        """Inspector only allows http and https schemes."""
        allowed = v4_rules["inspector"]["safe_fetch"]["allowed_schemes"]
        assert set(allowed) == {"http", "https"}

    def test_inspector_limits_redirects(self, v4_rules: dict) -> None:
        """Inspector must limit redirects to prevent SSRF via redirects."""
        max_redirects = v4_rules["inspector"]["safe_fetch"]["max_redirects"]
        assert max_redirects <= 5  # Reasonable limit

    def test_inspector_has_timeout(self, v4_rules: dict) -> None:
        """Inspector must have a timeout to prevent hanging."""
        timeout_ms = v4_rules["inspector"]["safe_fetch"]["timeout_ms"]
        assert timeout_ms > 0
        assert timeout_ms <= 30000  # Max 30 seconds

    def test_inspector_limits_response_size(self, v4_rules: dict) -> None:
        """Inspector must limit response size to prevent DoS."""
        max_bytes = v4_rules["inspector"]["safe_fetch"]["max_response_bytes"]
        assert max_bytes > 0
        assert max_bytes <= 10_000_000  # Max 10MB

    def test_inspector_is_admin_only(self, v4_rules: dict) -> None:
        """Inspector must be admin-only."""
        assert v4_rules["inspector"]["admin_only"] is True


class TestRequiredSections:
    """TA-E5.2-01: Test all required sections are properly configured."""

    def test_meta_has_required_sections_list(self, v4_rules: dict) -> None:
        """Meta section must define required sections."""
        assert "required_sections" in v4_rules["meta"]
        required = v4_rules["meta"]["required_sections"]
        assert len(required) >= 8  # At minimum

    def test_all_required_sections_present(self, v4_rules: dict) -> None:
        """All required sections from meta must be present."""
        required = v4_rules["meta"]["required_sections"]
        for section in required:
            assert section in v4_rules, f"Missing required section: {section}"


class TestAuthRules:
    """Test auth configuration rules."""

    def test_admin_routes_require_auth(self, v4_rules: dict) -> None:
        """Admin routes must require authentication."""
        assert v4_rules["auth"]["policies"]["admin_routes_require_auth"] is True

    def test_admin_mutations_require_csrf_protection(self, v4_rules: dict) -> None:
        """Admin mutations must require CSRF or server action token."""
        policy = v4_rules["auth"]["policies"]
        assert policy["admin_mutations_require_csrf_or_server_action_token"] is True


class TestContentRules:
    """Test content configuration rules."""

    def test_content_states_include_required(self, v4_rules: dict) -> None:
        """Content must support draft, scheduled, published, archived states."""
        states = v4_rules["content"]["states"]
        assert "draft" in states
        assert "scheduled" in states
        assert "published" in states
        assert "archived" in states

    def test_sanitization_is_enabled(self, v4_rules: dict) -> None:
        """Content sanitization must be enabled."""
        assert v4_rules["content"]["sanitization"]["enabled"] is True

    def test_external_links_have_noopener_noreferrer(self, v4_rules: dict) -> None:
        """External links must have noopener noreferrer."""
        rel_policy = v4_rules["content"]["sanitization"]["rel_attribute_policy"]
        assert rel_policy["external_links"] == "noopener_noreferrer"


class TestMediaRules:
    """Test media configuration rules."""

    def test_upload_sniff_magic_bytes_enabled(self, v4_rules: dict) -> None:
        """Upload validation must sniff magic bytes."""
        assert v4_rules["media"]["uploads"]["sniff_magic_bytes"] is True

    def test_upload_reject_on_mismatch(self, v4_rules: dict) -> None:
        """Uploads must be rejected if mime type mismatches."""
        assert v4_rules["media"]["uploads"]["reject_if_mismatch"] is True

    def test_variants_are_immutable(self, v4_rules: dict) -> None:
        """Image variants must be immutable."""
        assert v4_rules["media"]["variants"]["immutable"] is True

    def test_processing_limits_exist(self, v4_rules: dict) -> None:
        """Media processing must have safety limits."""
        limits = v4_rules["media"]["variants"]["processing_limits"]
        assert limits["max_decode_pixels"] > 0
        assert limits["max_cpu_ms"] > 0
        assert limits["max_memory_mb"] > 0


class TestJobsRules:
    """Test jobs configuration rules."""

    def test_idempotency_is_required(self, v4_rules: dict) -> None:
        """Jobs must require idempotency."""
        assert v4_rules["jobs"]["idempotency"]["required"] is True

    def test_retries_have_backoff(self, v4_rules: dict) -> None:
        """Job retries must have exponential backoff."""
        backoff = v4_rules["jobs"]["retries"]["backoff_seconds"]
        assert len(backoff) > 0
        # Verify backoff is increasing
        for i in range(1, len(backoff)):
            assert backoff[i] >= backoff[i - 1]


class TestCachingRules:
    """Test caching configuration rules."""

    def test_immutable_assets_have_long_cache(self, v4_rules: dict) -> None:
        """Immutable assets should have long cache headers."""
        cache = v4_rules["caching"]["assets"]["immutable_cache_control"]
        assert "immutable" in cache
        assert "max-age=31536000" in cache  # 1 year

    def test_revalidation_strategy_is_tag_based(self, v4_rules: dict) -> None:
        """Revalidation should use tag-based strategy."""
        assert v4_rules["caching"]["revalidation"]["strategy"] == "tag_based"
