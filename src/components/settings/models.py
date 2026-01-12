"""
Settings component input/output models.

Spec refs: E1.1, TA-0001, TA-0002
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core.entities import SiteSettings


@dataclass(frozen=True)
class GetSettingsInput:
    """Input for getting settings."""

    pass


@dataclass(frozen=True)
class GetSettingsOutput:
    """Output from getting settings."""

    settings: SiteSettings


@dataclass(frozen=True)
class UpdateSettingsInput:
    """Input for updating settings."""

    updates: dict[str, Any]


@dataclass(frozen=True)
class ValidationError:
    """Validation error with actionable message."""

    field: str
    code: str
    message: str


@dataclass(frozen=True)
class UpdateSettingsOutput:
    """Output from updating settings."""

    settings: SiteSettings
    errors: list[ValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class ResetSettingsInput:
    """Input for resetting settings to defaults."""

    pass


@dataclass(frozen=True)
class ResetSettingsOutput:
    """Output from resetting settings."""

    settings: SiteSettings


@dataclass
class ValidationRule:
    """Validation rule specification."""

    field_name: str
    min_length: int | None = None
    max_length: int | None = None
    required: bool = False
    allowed_values: list[str] | None = None
    is_url: bool = False
