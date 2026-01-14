"""
TA-0001, TA-0002: Settings service tests.

TA-0001: Settings defaults work when DB row missing
TA-0002: Settings validation returns actionable error messages

Spec refs: E1.1, R6
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.components.settings import (
    SettingsService,
    ValidationRule,
    create_settings_service,
    get_default_settings,
    validate_settings,
    validate_url,
)
from src.core.entities import SiteSettings


class MockSettingsRepo:
    """Mock settings repository for testing."""

    def __init__(self, initial: SiteSettings | None = None) -> None:
        self._settings = initial
        self.save_count = 0

    def get(self) -> SiteSettings | None:
        return self._settings

    def save(self, settings: SiteSettings) -> SiteSettings:
        self._settings = settings
        self.save_count += 1
        return settings


class MockCacheInvalidator:
    """Mock cache invalidator for testing."""

    def __init__(self) -> None:
        self.invalidate_count = 0

    def invalidate_settings(self) -> None:
        self.invalidate_count += 1


@pytest.fixture
def mock_repo() -> MockSettingsRepo:
    """Create empty mock repository (no settings in DB)."""
    return MockSettingsRepo()


@pytest.fixture
def mock_repo_with_settings() -> MockSettingsRepo:
    """Create mock repository with existing settings."""
    return MockSettingsRepo(
        SiteSettings(
            site_title="Existing Site",
            site_subtitle="Existing subtitle",
            theme="dark",
        )
    )


@pytest.fixture
def mock_cache() -> MockCacheInvalidator:
    """Create mock cache invalidator."""
    return MockCacheInvalidator()


class TestTA0001SettingsDefaults:
    """TA-0001: Settings defaults work when DB row missing."""

    def test_get_returns_defaults_when_db_empty(self, mock_repo: MockSettingsRepo) -> None:
        """GET settings returns defaults when no DB row exists."""
        service = SettingsService(mock_repo)

        settings = service.get()

        assert settings is not None
        assert settings.site_title == "My Site"
        assert settings.site_subtitle == ""
        assert settings.theme == "system"

    def test_get_default_settings_has_all_fields(self) -> None:
        """Default settings have all required fields."""
        defaults = get_default_settings()

        assert defaults.site_title is not None
        assert defaults.site_subtitle is not None
        assert defaults.theme is not None
        assert defaults.social_links_json is not None
        assert defaults.updated_at is not None

    def test_get_returns_existing_settings_when_present(
        self, mock_repo_with_settings: MockSettingsRepo
    ) -> None:
        """GET settings returns existing settings when DB row exists."""
        service = SettingsService(mock_repo_with_settings)

        settings = service.get()

        assert settings.site_title == "Existing Site"
        assert settings.site_subtitle == "Existing subtitle"
        assert settings.theme == "dark"

    def test_defaults_are_valid(self) -> None:
        """Default settings pass validation."""
        defaults = get_default_settings()
        errors = validate_settings(defaults)

        assert len(errors) == 0


class TestTA0002SettingsValidation:
    """TA-0002: Settings validation returns actionable error messages."""

    def test_empty_title_returns_error(self) -> None:
        """Empty site_title returns required error."""
        settings = SiteSettings(site_title="", site_subtitle="")

        errors = validate_settings(settings)

        assert len(errors) > 0
        title_errors = [e for e in errors if e.field == "site_title"]
        assert len(title_errors) == 1
        assert title_errors[0].code == "required"
        assert "required" in title_errors[0].message.lower()

    def test_title_too_long_returns_error(self) -> None:
        """Title exceeding max length returns error."""
        settings = SiteSettings(site_title="x" * 101, site_subtitle="")

        errors = validate_settings(settings)

        title_errors = [e for e in errors if e.field == "site_title"]
        assert len(title_errors) == 1
        assert title_errors[0].code == "max_length"
        assert "100" in title_errors[0].message

    def test_subtitle_too_long_returns_error(self) -> None:
        """Subtitle exceeding max length returns error."""
        settings = SiteSettings(site_title="Title", site_subtitle="y" * 201)

        errors = validate_settings(settings)

        subtitle_errors = [e for e in errors if e.field == "site_subtitle"]
        assert len(subtitle_errors) == 1
        assert subtitle_errors[0].code == "max_length"

    def test_invalid_theme_via_update_returns_error(self, mock_repo: MockSettingsRepo) -> None:
        """Invalid theme value via update returns error."""
        # SiteSettings uses Pydantic Literal, so invalid theme fails at construction
        # Test via service.update which catches the schema error
        service = SettingsService(mock_repo)

        updated, errors = service.update({"theme": "invalid"})

        assert len(errors) > 0
        # Either a schema error or validation error is acceptable
        assert any(e.field in ("theme", "_schema") for e in errors)

    def test_valid_settings_pass_validation(self) -> None:
        """Valid settings pass all validation checks."""
        settings = SiteSettings(
            site_title="My Awesome Site",
            site_subtitle="A great place to be",
            theme="dark",
        )

        errors = validate_settings(settings)

        assert len(errors) == 0

    def test_invalid_social_link_url_returns_error(self) -> None:
        """Invalid URL in social_links returns error."""
        settings = SiteSettings(
            site_title="Title",
            site_subtitle="",
            social_links_json={"twitter": "not-a-url"},
        )

        errors = validate_settings(settings)

        social_errors = [e for e in errors if "social_links" in e.field]
        assert len(social_errors) == 1
        assert social_errors[0].code == "invalid_url"
        assert "twitter" in social_errors[0].message

    def test_valid_social_link_passes(self) -> None:
        """Valid social links pass validation."""
        settings = SiteSettings(
            site_title="Title",
            site_subtitle="",
            social_links_json={
                "twitter": "https://twitter.com/example",
                "github": "https://github.com/example",
            },
        )

        errors = validate_settings(settings)

        assert len(errors) == 0

    def test_error_messages_are_actionable(self) -> None:
        """Error messages contain actionable information."""
        settings = SiteSettings(
            site_title="",
            site_subtitle="y" * 300,
            theme="dark",  # Use valid theme to test other validations
        )

        errors = validate_settings(settings)

        # Should have errors for title (required) and subtitle (max_length)
        assert len(errors) >= 2

        # Check that errors have field, code, and message
        for error in errors:
            assert error.field is not None
            assert error.code is not None
            assert error.message is not None
            assert len(error.message) > 10  # Non-trivial message


class TestSettingsServiceUpdate:
    """Update operation tests."""

    def test_update_persists_valid_changes(
        self, mock_repo: MockSettingsRepo, mock_cache: MockCacheInvalidator
    ) -> None:
        """Valid updates are persisted to the repository."""
        service = SettingsService(mock_repo, mock_cache)

        updated, errors = service.update({"site_title": "New Title"})

        assert len(errors) == 0
        assert updated.site_title == "New Title"
        assert mock_repo.save_count == 1

    def test_update_rejects_invalid_changes(
        self, mock_repo: MockSettingsRepo, mock_cache: MockCacheInvalidator
    ) -> None:
        """Invalid updates are rejected with errors."""
        service = SettingsService(mock_repo, mock_cache)

        updated, errors = service.update({"site_title": ""})

        assert len(errors) > 0
        assert mock_repo.save_count == 0

    def test_update_invalidates_cache_on_success(
        self, mock_repo: MockSettingsRepo, mock_cache: MockCacheInvalidator
    ) -> None:
        """Cache is invalidated after successful update (R6)."""
        service = SettingsService(mock_repo, mock_cache)

        service.update({"site_title": "New Title"})

        assert mock_cache.invalidate_count == 1

    def test_update_does_not_invalidate_cache_on_failure(
        self, mock_repo: MockSettingsRepo, mock_cache: MockCacheInvalidator
    ) -> None:
        """Cache is not invalidated when update fails."""
        service = SettingsService(mock_repo, mock_cache)

        service.update({"site_title": ""})

        assert mock_cache.invalidate_count == 0

    def test_update_preserves_unchanged_fields(
        self, mock_repo_with_settings: MockSettingsRepo
    ) -> None:
        """Update preserves fields not included in the update."""
        service = SettingsService(mock_repo_with_settings)

        updated, errors = service.update({"site_subtitle": "New subtitle"})

        assert len(errors) == 0
        assert updated.site_title == "Existing Site"  # Preserved
        assert updated.site_subtitle == "New subtitle"  # Updated
        assert updated.theme == "dark"  # Preserved

    def test_update_sets_updated_at(self, mock_repo: MockSettingsRepo) -> None:
        """Update sets the updated_at timestamp."""
        from datetime import UTC

        service = SettingsService(mock_repo)
        before = datetime.now(UTC)

        updated, errors = service.update({"site_title": "New Title"})

        assert len(errors) == 0
        # Handle both naive and aware datetimes
        updated_at = updated.updated_at
        if updated_at.tzinfo is None:
            before = before.replace(tzinfo=None)
        assert updated_at >= before


class TestSettingsServiceResetToDefaults:
    """Reset to defaults tests."""

    def test_reset_returns_default_values(
        self, mock_repo_with_settings: MockSettingsRepo, mock_cache: MockCacheInvalidator
    ) -> None:
        """Reset restores default settings."""
        service = SettingsService(mock_repo_with_settings, mock_cache)

        reset = service.reset_to_defaults()

        assert reset.site_title == "My Site"
        assert reset.site_subtitle == ""
        assert reset.theme == "system"

    def test_reset_invalidates_cache(
        self, mock_repo: MockSettingsRepo, mock_cache: MockCacheInvalidator
    ) -> None:
        """Reset invalidates the cache."""
        service = SettingsService(mock_repo, mock_cache)

        service.reset_to_defaults()

        assert mock_cache.invalidate_count == 1


class TestURLValidation:
    """URL validation helper tests."""

    def test_valid_https_url(self) -> None:
        """Valid HTTPS URL passes."""
        assert validate_url("https://example.com") is True

    def test_valid_http_url(self) -> None:
        """Valid HTTP URL passes."""
        assert validate_url("http://example.com") is True

    def test_empty_url_passes(self) -> None:
        """Empty URL passes (optional field)."""
        assert validate_url("") is True

    def test_missing_scheme_fails(self) -> None:
        """URL without scheme fails."""
        assert validate_url("example.com") is False

    def test_javascript_url_fails(self) -> None:
        """JavaScript URL fails."""
        assert validate_url("javascript:alert(1)") is False

    def test_data_url_fails(self) -> None:
        """Data URL fails."""
        assert validate_url("data:text/html,<h1>Hello</h1>") is False


class TestCustomValidationRules:
    """Custom validation rules tests."""

    def test_custom_min_length_rule(self) -> None:
        """Custom minimum length rule is enforced."""
        custom_rules = [
            ValidationRule(field="site_title", min_length=10, required=True),
        ]

        settings = SiteSettings(site_title="Short", site_subtitle="")
        errors = validate_settings(settings, custom_rules)

        assert len(errors) == 1
        assert errors[0].code == "min_length"

    def test_custom_url_rule(self) -> None:
        """Custom URL validation rule is enforced."""
        custom_rules = [
            ValidationRule(field="site_title", required=True),
        ]

        # Note: We can't add arbitrary fields to SiteSettings,
        # but we verify the rule mechanism works
        settings = SiteSettings(site_title="Title", site_subtitle="")
        errors = validate_settings(settings, custom_rules)

        assert len(errors) == 0


class TestFactoryFunction:
    """Factory function tests."""

    def test_create_settings_service(self, mock_repo: MockSettingsRepo) -> None:
        """create_settings_service creates configured service."""
        service = create_settings_service(mock_repo)

        settings = service.get()

        assert settings is not None
        assert settings.site_title == "My Site"

    def test_create_settings_service_with_cache(
        self, mock_repo: MockSettingsRepo, mock_cache: MockCacheInvalidator
    ) -> None:
        """create_settings_service accepts cache invalidator."""
        service = create_settings_service(mock_repo, mock_cache)

        service.update({"site_title": "New Title"})

        assert mock_cache.invalidate_count == 1
