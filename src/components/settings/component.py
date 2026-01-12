"""
Settings component - Site settings management.

Spec refs: E1.1, TA-0001, TA-0002, R6

Provides singleton settings read/write with validation and fallback defaults.
"""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

from src.core.entities import SiteSettings

from .models import (
    GetSettingsInput,
    GetSettingsOutput,
    ResetSettingsInput,
    ResetSettingsOutput,
    UpdateSettingsInput,
    UpdateSettingsOutput,
    ValidationError,
    ValidationRule,
)
from .ports import CacheInvalidatorPort, SettingsRepoPort

# --- Default Validation Rules ---

DEFAULT_RULES = [
    ValidationRule(field_name="site_title", min_length=1, max_length=100, required=True),
    ValidationRule(field_name="site_subtitle", max_length=200),
    ValidationRule(field_name="theme", allowed_values=["light", "dark", "system"]),
]


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


# --- Validation Functions ---


def _validate_url(value: str) -> bool:
    """Validate URL format."""
    if not value:
        return True
    try:
        result = urlparse(value)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def _validate_social_links(links: dict[str, str]) -> list[ValidationError]:
    """Validate social links dictionary."""
    errors: list[ValidationError] = []
    for key, url in links.items():
        if not _validate_url(url):
            errors.append(
                ValidationError(
                    field=f"social_links_json.{key}",
                    code="invalid_url",
                    message=f"Invalid URL format for '{key}': must be http or https URL",
                )
            )
    return errors


def _validate_settings(
    settings: SiteSettings,
    rules: list[ValidationRule],
) -> list[ValidationError]:
    """Validate settings against rules."""
    errors: list[ValidationError] = []

    for rule in rules:
        value = getattr(settings, rule.field_name, None)

        # Required check
        if rule.required and (value is None or value == ""):
            errors.append(
                ValidationError(
                    field=rule.field_name,
                    code="required",
                    message=f"Field '{rule.field_name}' is required",
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
                        field=rule.field_name,
                        code="min_length",
                        message=(
                            f"Field '{rule.field_name}' must be at least "
                            f"{rule.min_length} characters"
                        ),
                    )
                )

            if rule.max_length is not None and len(value) > rule.max_length:
                errors.append(
                    ValidationError(
                        field=rule.field_name,
                        code="max_length",
                        message=(
                            f"Field '{rule.field_name}' must not exceed "
                            f"{rule.max_length} characters"
                        ),
                    )
                )

        # Allowed values check
        if rule.allowed_values is not None and value not in rule.allowed_values:
            errors.append(
                ValidationError(
                    field=rule.field_name,
                    code="invalid_value",
                    message=(
                        f"Field '{rule.field_name}' must be one of: "
                        f"{', '.join(rule.allowed_values)}"
                    ),
                )
            )

        # URL validation
        if rule.is_url and isinstance(value, str) and not _validate_url(value):
            errors.append(
                ValidationError(
                    field=rule.field_name,
                    code="invalid_url",
                    message=f"Field '{rule.field_name}' must be a valid http or https URL",
                )
            )

    # Validate social links
    if settings.social_links_json:
        errors.extend(_validate_social_links(settings.social_links_json))

    return errors


def _parse_pydantic_errors(exc: Exception) -> list[ValidationError]:
    """Parse Pydantic ValidationError to extract field-specific errors."""
    try:
        from pydantic import ValidationError as PydanticValidationError

        if not isinstance(exc, PydanticValidationError):
            return []

        errors: list[ValidationError] = []
        for error in exc.errors():
            loc = error.get("loc", ())
            field = ".".join(str(part) for part in loc) if loc else "_schema"
            error_type = error.get("type", "unknown")
            code = "invalid_value"
            if "literal" in error_type:
                code = "invalid_value"
            elif "string" in error_type:
                code = "invalid_type"
            elif "missing" in error_type:
                code = "required"

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


# --- Component Entry Points ---


def run_get(
    inp: GetSettingsInput,
    *,
    repo: SettingsRepoPort,
) -> GetSettingsOutput:
    """
    Get current settings.

    Always returns settings - uses defaults if DB row missing (TA-0001).

    Args:
        inp: Input (empty for get operation).
        repo: Settings repository port.

    Returns:
        GetSettingsOutput with current settings.
    """
    settings = repo.get()
    if settings is None:
        settings = get_default_settings()
    return GetSettingsOutput(settings=settings)


def run_update(
    inp: UpdateSettingsInput,
    *,
    repo: SettingsRepoPort,
    cache: CacheInvalidatorPort | None = None,
    rules: list[ValidationRule] | None = None,
) -> UpdateSettingsOutput:
    """
    Update settings.

    Validates before saving (TA-0002).

    Args:
        inp: Input containing updates dictionary.
        repo: Settings repository port.
        cache: Optional cache invalidator port.
        rules: Optional custom validation rules.

    Returns:
        UpdateSettingsOutput with updated settings or validation errors.
    """
    if rules is None:
        rules = DEFAULT_RULES

    # Get current settings or defaults
    current = repo.get()
    if current is None:
        current = get_default_settings()

    # Apply updates
    updated_dict = current.model_dump()
    updated_dict.update(inp.updates)
    updated_dict["updated_at"] = datetime.now(UTC)

    # Create new settings object
    try:
        new_settings = SiteSettings(**updated_dict)
    except Exception as e:
        errors = _parse_pydantic_errors(e)
        if errors:
            return UpdateSettingsOutput(settings=current, errors=errors, success=False)
        return UpdateSettingsOutput(
            settings=current,
            errors=[
                ValidationError(
                    field="_schema",
                    code="invalid_schema",
                    message=f"Invalid settings structure: {e}",
                )
            ],
            success=False,
        )

    # Validate
    errors = _validate_settings(new_settings, rules)
    if errors:
        return UpdateSettingsOutput(settings=current, errors=errors, success=False)

    # Save
    saved = repo.save(new_settings)

    # Invalidate cache (R6)
    if cache is not None:
        cache.invalidate_settings()

    return UpdateSettingsOutput(settings=saved, errors=[], success=True)


def run_reset(
    inp: ResetSettingsInput,
    *,
    repo: SettingsRepoPort,
    cache: CacheInvalidatorPort | None = None,
) -> ResetSettingsOutput:
    """
    Reset settings to defaults.

    Args:
        inp: Input (empty for reset operation).
        repo: Settings repository port.
        cache: Optional cache invalidator port.

    Returns:
        ResetSettingsOutput with default settings.
    """
    defaults = get_default_settings()
    saved = repo.save(defaults)

    if cache is not None:
        cache.invalidate_settings()

    return ResetSettingsOutput(settings=saved)


def run(
    inp: GetSettingsInput | UpdateSettingsInput | ResetSettingsInput,
    *,
    repo: SettingsRepoPort,
    cache: CacheInvalidatorPort | None = None,
    rules: list[ValidationRule] | None = None,
) -> GetSettingsOutput | UpdateSettingsOutput | ResetSettingsOutput:
    """
    Main entry point for the settings component.

    Dispatches to appropriate handler based on input type.

    Args:
        inp: Input object (GetSettingsInput, UpdateSettingsInput, or ResetSettingsInput).
        repo: Settings repository port.
        cache: Optional cache invalidator port.
        rules: Optional custom validation rules.

    Returns:
        Appropriate output object based on input type.
    """
    if isinstance(inp, GetSettingsInput):
        return run_get(inp, repo=repo)
    elif isinstance(inp, UpdateSettingsInput):
        return run_update(inp, repo=repo, cache=cache, rules=rules)
    elif isinstance(inp, ResetSettingsInput):
        return run_reset(inp, repo=repo, cache=cache)
    else:
        raise ValueError(f"Unknown input type: {type(inp)}")
