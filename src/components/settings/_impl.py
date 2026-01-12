"""
SettingsService (E1.1) - Site settings management.

Provides singleton settings read/write with validation and fallback defaults.
Implements C5 from the spec.

Spec refs: E1.1, TA-0001, TA-0002, R6
Test assertions:
- TA-0001: Settings defaults work when DB row missing
- TA-0002: Settings validation returns actionable error messages

Key behaviors:
- GET always returns settings (fallback to defaults if missing)
- PUT validates fields before persisting
- Cache invalidation hook for SSR cache coordination (R6)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlparse

from src.core.entities import SiteSettings

# --- Validation Rules ---


@dataclass
class ValidationRule:
    """Validation rule specification."""

    field: str
    min_length: int | None = None
    max_length: int | None = None
    required: bool = False
    allowed_values: list[str] | None = None
    is_url: bool = False


DEFAULT_RULES = [
    ValidationRule(field="site_title", min_length=1, max_length=100, required=True),
    ValidationRule(field="site_subtitle", max_length=200),
    ValidationRule(field="theme", allowed_values=["light", "dark", "system"]),
]


@dataclass
class ValidationError:
    """Validation error with actionable message."""

    field: str
    code: str
    message: str


# --- Default Settings ---


def get_default_settings() -> SiteSettings:
    """
    Get fallback default settings.

    Used when DB row doesn't exist (TA-0001).
    """
    return SiteSettings(
        site_title="My Site",
        site_subtitle="",
        avatar_asset_id=None,
        theme="system",
        social_links_json={},
        updated_at=datetime.now(UTC),
    )


# --- Settings Repository Protocol ---


class SettingsRepoPort(Protocol):
    """Repository interface for settings."""

    def get(self) -> SiteSettings | None:
        """Get current settings, or None if not configured."""
        ...

    def save(self, settings: SiteSettings) -> SiteSettings:
        """Save or update settings (upsert)."""
        ...


# --- Cache Invalidation Hook ---


class CacheInvalidator(Protocol):
    """Cache invalidation hook for R6 compliance."""

    def invalidate_settings(self) -> None:
        """Invalidate cached settings across SSR."""
        ...


class NoOpCacheInvalidator:
    """Default no-op cache invalidator."""

    def invalidate_settings(self) -> None:
        """No-op implementation."""
        pass


# --- Validation Functions ---


def validate_url(value: str) -> bool:
    """Validate URL format."""
    if not value:
        return True  # Empty is valid (optional)
    try:
        result = urlparse(value)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def validate_social_links(links: dict[str, str]) -> list[ValidationError]:
    """Validate social links dictionary."""
    errors: list[ValidationError] = []
    for key, url in links.items():
        if not validate_url(url):
            errors.append(
                ValidationError(
                    field=f"social_links_json.{key}",
                    code="invalid_url",
                    message=f"Invalid URL format for '{key}': must be http or https URL",
                )
            )
    return errors


def validate_settings(
    settings: SiteSettings,
    rules: list[ValidationRule] | None = None,
) -> list[ValidationError]:
    """
    Validate settings against rules.

    Returns list of validation errors (TA-0002).
    """
    rules = rules or DEFAULT_RULES
    errors: list[ValidationError] = []

    for rule in rules:
        value = getattr(settings, rule.field, None)

        # Required check
        if rule.required and (value is None or value == ""):
            errors.append(
                ValidationError(
                    field=rule.field,
                    code="required",
                    message=f"Field '{rule.field}' is required",
                )
            )
            continue

        # Skip further validation if empty and not required
        if value is None or value == "":
            continue

        # Length checks (for strings)
        if isinstance(value, str):
            if rule.min_length is not None and len(value) < rule.min_length:
                errors.append(
                    ValidationError(
                        field=rule.field,
                        code="min_length",
                        message=(
                            f"Field '{rule.field}' must be at least {rule.min_length} characters"
                        ),
                    )
                )

            if rule.max_length is not None and len(value) > rule.max_length:
                errors.append(
                    ValidationError(
                        field=rule.field,
                        code="max_length",
                        message=(
                            f"Field '{rule.field}' must not exceed {rule.max_length} characters"
                        ),
                    )
                )

        # Allowed values check
        if rule.allowed_values is not None and value not in rule.allowed_values:
            errors.append(
                ValidationError(
                    field=rule.field,
                    code="invalid_value",
                    message=(
                        f"Field '{rule.field}' must be one of: {', '.join(rule.allowed_values)}"
                    ),
                )
            )

        # URL validation
        if rule.is_url and isinstance(value, str) and not validate_url(value):
            errors.append(
                ValidationError(
                    field=rule.field,
                    code="invalid_url",
                    message=f"Field '{rule.field}' must be a valid http or https URL",
                )
            )

    # Validate social links
    if settings.social_links_json:
        errors.extend(validate_social_links(settings.social_links_json))

    return errors


def _parse_pydantic_errors(exc: Exception) -> list[ValidationError]:
    """
    Parse Pydantic ValidationError to extract field-specific errors.

    Returns list of ValidationError with proper field names, or empty list
    if the exception is not a Pydantic ValidationError.
    """
    try:
        from pydantic import ValidationError as PydanticValidationError

        if not isinstance(exc, PydanticValidationError):
            return []

        errors: list[ValidationError] = []
        for error in exc.errors():
            # Get field path (e.g., ('theme',) or ('social_links_json', 'twitter'))
            loc = error.get("loc", ())
            field = ".".join(str(part) for part in loc) if loc else "_schema"

            # Map Pydantic error types to our error codes
            error_type = error.get("type", "unknown")
            code = "invalid_value"
            if "literal" in error_type:
                code = "invalid_value"
            elif "string" in error_type:
                code = "invalid_type"
            elif "missing" in error_type:
                code = "required"

            # Build actionable message
            msg = error.get("msg", "Invalid value")

            errors.append(
                ValidationError(
                    field=field,
                    code=code,
                    message=f"Field '{field}': {msg}",
                )
            )

        return errors
    except ImportError:
        return []


# --- Settings Service ---


class SettingsService:
    """
    Site settings service (C5).

    Provides:
    - Get settings with fallback defaults (TA-0001)
    - Update settings with validation (TA-0002)
    - Cache invalidation for R6 compliance
    """

    def __init__(
        self,
        repo: SettingsRepoPort,
        cache_invalidator: CacheInvalidator | None = None,
        rules: list[ValidationRule] | None = None,
    ) -> None:
        """
        Initialize settings service.

        Args:
            repo: Settings repository
            cache_invalidator: Optional cache invalidator for SSR cache
            rules: Optional custom validation rules
        """
        self._repo = repo
        self._cache_invalidator = cache_invalidator or NoOpCacheInvalidator()
        self._rules = rules or DEFAULT_RULES

    def get(self) -> SiteSettings:
        """
        Get current settings.

        Always returns settings - uses defaults if DB row missing (TA-0001).
        """
        settings = self._repo.get()
        if settings is None:
            return get_default_settings()
        return settings

    def update(
        self,
        updates: dict[str, Any],
    ) -> tuple[SiteSettings, list[ValidationError]]:
        """
        Update settings.

        Args:
            updates: Dictionary of fields to update

        Returns:
            Tuple of (updated_settings, validation_errors)
            If validation_errors is non-empty, settings were not saved.

        Validates before saving (TA-0002).
        """
        # Get current settings or defaults
        current = self.get()

        # Apply updates
        updated_dict = current.model_dump()
        updated_dict.update(updates)
        updated_dict["updated_at"] = datetime.now(UTC)

        # Create new settings object
        try:
            new_settings = SiteSettings(**updated_dict)
        except Exception as e:
            # Try to parse Pydantic validation errors for field-specific messages
            errors = _parse_pydantic_errors(e)
            if errors:
                return current, errors
            # Fall back to generic schema error
            return current, [
                ValidationError(
                    field="_schema",
                    code="invalid_schema",
                    message=f"Invalid settings structure: {e}",
                )
            ]

        # Validate
        errors = validate_settings(new_settings, self._rules)
        if errors:
            return current, errors

        # Save
        saved = self._repo.save(new_settings)

        # Invalidate cache (R6)
        self._cache_invalidator.invalidate_settings()

        return saved, []

    def reset_to_defaults(self) -> SiteSettings:
        """
        Reset settings to defaults.

        Returns the default settings after saving.
        """
        defaults = get_default_settings()
        saved = self._repo.save(defaults)
        self._cache_invalidator.invalidate_settings()
        return saved


# --- Factory ---


def create_settings_service(
    repo: SettingsRepoPort,
    cache_invalidator: CacheInvalidator | None = None,
) -> SettingsService:
    """
    Create a settings service.

    Args:
        repo: Settings repository
        cache_invalidator: Optional cache invalidator

    Returns:
        Configured SettingsService
    """
    return SettingsService(repo, cache_invalidator)
