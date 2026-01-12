"""
Tests for Admin Settings API (E1.1).

Test assertions:
- TA-0001: GET returns settings (fallback defaults if DB row missing)
- TA-0002: PUT validates fields, returns 400 with actionable messages
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.core.services.settings import SettingsService, get_default_settings
from src.domain.entities import SiteSettings, User

# --- Mock Repository ---


class MockSettingsRepo:
    """In-memory settings repository for testing."""

    def __init__(self, initial: SiteSettings | None = None) -> None:
        self._settings = initial

    def get(self) -> SiteSettings | None:
        return self._settings

    def save(self, settings: SiteSettings) -> SiteSettings:
        self._settings = settings
        return settings


class MockUserRepo:
    """Mock user repository for testing."""

    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    def add(self, user: User) -> None:
        self._users[user.id] = user

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        for user in self._users.values():
            if user.email == email:
                return user
        return None


# --- Test Fixtures ---


@pytest.fixture
def mock_settings_repo() -> MockSettingsRepo:
    """Empty settings repo (no data)."""
    return MockSettingsRepo()


@pytest.fixture
def mock_settings_repo_with_data() -> MockSettingsRepo:
    """Settings repo with existing settings."""
    settings = SiteSettings(
        site_title="Test Site",
        site_subtitle="Test Subtitle",
        avatar_asset_id=None,
        theme="dark",
        social_links_json={"twitter": "https://twitter.com/test"},
        updated_at=datetime.now(UTC),
    )
    return MockSettingsRepo(settings)


@pytest.fixture
def admin_user() -> User:
    """Admin user for testing."""
    return User(
        id=uuid4(),
        email="admin@test.com",
        display_name="Admin User",
        password_hash="hashed",
        roles=["admin"],
        status="active",
    )


# --- TA-0001: GET Settings Fallback Defaults ---


class TestGetSettingsDefaults:
    """Test TA-0001: GET returns defaults when DB row missing."""

    def test_get_settings_returns_defaults_when_empty(
        self,
        mock_settings_repo: MockSettingsRepo,
    ) -> None:
        """GET returns fallback defaults when no settings in DB."""
        service = SettingsService(repo=mock_settings_repo)
        settings = service.get()

        defaults = get_default_settings()
        assert settings.site_title == defaults.site_title
        assert settings.site_subtitle == defaults.site_subtitle
        assert settings.theme == defaults.theme

    def test_get_settings_returns_stored_when_present(
        self,
        mock_settings_repo_with_data: MockSettingsRepo,
    ) -> None:
        """GET returns stored settings when present."""
        service = SettingsService(repo=mock_settings_repo_with_data)
        settings = service.get()

        assert settings.site_title == "Test Site"
        assert settings.site_subtitle == "Test Subtitle"
        assert settings.theme == "dark"

    def test_defaults_have_all_required_fields(self) -> None:
        """Default settings have all required fields populated."""
        defaults = get_default_settings()

        assert defaults.site_title is not None
        assert len(defaults.site_title) > 0
        assert defaults.theme in ("light", "dark", "system")
        assert defaults.updated_at is not None


# --- TA-0002: PUT Settings Validation ---


class TestUpdateSettingsValidation:
    """Test TA-0002: PUT validates with actionable error messages."""

    def test_update_valid_fields_succeeds(
        self,
        mock_settings_repo: MockSettingsRepo,
    ) -> None:
        """Valid field updates succeed and persist."""
        service = SettingsService(repo=mock_settings_repo)

        settings, errors = service.update(
            {
                "site_title": "New Title",
                "site_subtitle": "New Subtitle",
                "theme": "dark",
            }
        )

        assert errors == []
        assert settings.site_title == "New Title"
        assert settings.site_subtitle == "New Subtitle"
        assert settings.theme == "dark"

        # Verify persisted
        stored = service.get()
        assert stored.site_title == "New Title"

    def test_update_empty_title_fails_validation(
        self,
        mock_settings_repo: MockSettingsRepo,
    ) -> None:
        """Empty site_title returns validation error."""
        service = SettingsService(repo=mock_settings_repo)

        settings, errors = service.update({"site_title": ""})

        assert len(errors) > 0
        assert any(e.field == "site_title" for e in errors)
        assert any(e.code == "required" for e in errors)

    def test_update_title_too_long_fails_validation(
        self,
        mock_settings_repo: MockSettingsRepo,
    ) -> None:
        """Title exceeding max length returns validation error."""
        service = SettingsService(repo=mock_settings_repo)

        long_title = "A" * 150  # Exceeds 100 char limit
        settings, errors = service.update({"site_title": long_title})

        assert len(errors) > 0
        assert any(e.field == "site_title" for e in errors)
        assert any(e.code == "max_length" for e in errors)

    def test_update_subtitle_too_long_fails_validation(
        self,
        mock_settings_repo: MockSettingsRepo,
    ) -> None:
        """Subtitle exceeding max length returns validation error."""
        service = SettingsService(repo=mock_settings_repo)

        # First set a valid title
        service.update({"site_title": "Valid Title"})

        long_subtitle = "B" * 250  # Exceeds 200 char limit
        settings, errors = service.update({"site_subtitle": long_subtitle})

        assert len(errors) > 0
        assert any(e.field == "site_subtitle" for e in errors)
        assert any(e.code == "max_length" for e in errors)

    def test_update_invalid_theme_fails_validation(
        self,
        mock_settings_repo: MockSettingsRepo,
    ) -> None:
        """Invalid theme value returns validation error."""
        service = SettingsService(repo=mock_settings_repo)

        # First set a valid title
        service.update({"site_title": "Valid Title"})

        settings, errors = service.update({"theme": "invalid_theme"})

        assert len(errors) > 0
        assert any(e.field == "theme" for e in errors)
        assert any(e.code == "invalid_value" for e in errors)

    def test_validation_errors_have_actionable_messages(
        self,
        mock_settings_repo: MockSettingsRepo,
    ) -> None:
        """Validation errors include actionable messages."""
        service = SettingsService(repo=mock_settings_repo)

        settings, errors = service.update({"site_title": ""})

        assert len(errors) > 0
        for error in errors:
            assert error.field is not None
            assert error.code is not None
            assert error.message is not None
            assert len(error.message) > 0

    def test_update_social_links_valid_url_succeeds(
        self,
        mock_settings_repo: MockSettingsRepo,
    ) -> None:
        """Valid social link URLs succeed."""
        service = SettingsService(repo=mock_settings_repo)

        settings, errors = service.update(
            {
                "site_title": "Test Site",
                "social_links_json": {
                    "twitter": "https://twitter.com/test",
                    "github": "https://github.com/test",
                },
            }
        )

        assert errors == []
        assert settings.social_links_json["twitter"] == "https://twitter.com/test"

    def test_update_social_links_invalid_url_fails(
        self,
        mock_settings_repo: MockSettingsRepo,
    ) -> None:
        """Invalid social link URL returns validation error."""
        service = SettingsService(repo=mock_settings_repo)

        # First set a valid title
        service.update({"site_title": "Valid Title"})

        settings, errors = service.update(
            {
                "social_links_json": {
                    "twitter": "not-a-valid-url",
                },
            }
        )

        assert len(errors) > 0
        assert any("social_links" in e.field for e in errors)
        assert any(e.code == "invalid_url" for e in errors)

    def test_update_preserves_existing_values(
        self,
        mock_settings_repo_with_data: MockSettingsRepo,
    ) -> None:
        """Partial update preserves existing values."""
        service = SettingsService(repo=mock_settings_repo_with_data)

        # Only update subtitle
        settings, errors = service.update({"site_subtitle": "Updated Subtitle"})

        assert errors == []
        assert settings.site_subtitle == "Updated Subtitle"
        # Original values preserved
        assert settings.site_title == "Test Site"
        assert settings.theme == "dark"

    def test_update_sets_updated_at(
        self,
        mock_settings_repo: MockSettingsRepo,
    ) -> None:
        """Update sets updated_at timestamp."""
        service = SettingsService(repo=mock_settings_repo)

        before = datetime.now(UTC)
        settings, errors = service.update({"site_title": "New Title"})
        after = datetime.now(UTC)

        assert errors == []
        # Handle both timezone-aware and naive datetimes
        updated = settings.updated_at
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=UTC)
        assert before <= updated <= after


# --- Multiple Validation Errors ---


class TestMultipleValidationErrors:
    """Test that multiple errors are returned together."""

    def test_multiple_errors_returned_together(
        self,
        mock_settings_repo: MockSettingsRepo,
    ) -> None:
        """Multiple validation failures return all errors."""
        service = SettingsService(repo=mock_settings_repo)

        # First set a valid title to allow subsequent validations
        service.update({"site_title": "Valid Title"})

        # Now try to update with multiple invalid fields
        long_subtitle = "B" * 250
        settings, errors = service.update(
            {
                "site_title": "",  # Required
                "site_subtitle": long_subtitle,  # Too long
            }
        )

        # Should have at least 2 errors
        assert len(errors) >= 2


# --- Edge Cases ---


class TestEdgeCases:
    """Test edge cases for settings."""

    def test_empty_updates_no_change(
        self,
        mock_settings_repo_with_data: MockSettingsRepo,
    ) -> None:
        """Empty updates dict returns current settings unchanged."""
        service = SettingsService(repo=mock_settings_repo_with_data)

        settings, errors = service.update({})

        assert errors == []
        assert settings.site_title == "Test Site"

    def test_null_avatar_clears_value(
        self,
        mock_settings_repo_with_data: MockSettingsRepo,
    ) -> None:
        """Setting avatar_asset_id to None clears it."""
        service = SettingsService(repo=mock_settings_repo_with_data)

        settings, errors = service.update({"avatar_asset_id": None})

        assert errors == []
        assert settings.avatar_asset_id is None

    def test_valid_avatar_uuid_accepted(
        self,
        mock_settings_repo: MockSettingsRepo,
    ) -> None:
        """Valid UUID for avatar_asset_id is accepted."""
        service = SettingsService(repo=mock_settings_repo)

        asset_id = uuid4()
        settings, errors = service.update(
            {
                "site_title": "Test",
                "avatar_asset_id": asset_id,
            }
        )

        assert errors == []
        assert settings.avatar_asset_id == asset_id

    def test_valid_themes(
        self,
        mock_settings_repo: MockSettingsRepo,
    ) -> None:
        """All valid theme values are accepted."""
        service = SettingsService(repo=mock_settings_repo)

        for theme in ["light", "dark", "system"]:
            settings, errors = service.update(
                {
                    "site_title": "Test",
                    "theme": theme,
                }
            )
            assert errors == [], f"Theme '{theme}' should be valid"
            assert settings.theme == theme


# --- Cache Invalidation (R6) ---


class MockCacheInvalidator:
    """Mock cache invalidator for testing."""

    def __init__(self) -> None:
        self.invalidate_count = 0

    def invalidate_settings(self) -> None:
        self.invalidate_count += 1


class TestCacheInvalidation:
    """Test R6: Cache invalidation on settings update."""

    def test_update_triggers_cache_invalidation(
        self,
        mock_settings_repo: MockSettingsRepo,
    ) -> None:
        """Successful update triggers cache invalidation."""
        invalidator = MockCacheInvalidator()
        service = SettingsService(
            repo=mock_settings_repo,
            cache_invalidator=invalidator,
        )

        settings, errors = service.update({"site_title": "New Title"})

        assert errors == []
        assert invalidator.invalidate_count == 1

    def test_failed_validation_no_cache_invalidation(
        self,
        mock_settings_repo: MockSettingsRepo,
    ) -> None:
        """Failed validation does not trigger cache invalidation."""
        invalidator = MockCacheInvalidator()
        service = SettingsService(
            repo=mock_settings_repo,
            cache_invalidator=invalidator,
        )

        settings, errors = service.update({"site_title": ""})  # Invalid

        assert len(errors) > 0
        assert invalidator.invalidate_count == 0
