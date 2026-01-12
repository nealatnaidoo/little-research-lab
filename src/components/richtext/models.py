"""
Richtext component input/output models.

Spec refs: E4.1, E4.2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# --- Validation Error ---


@dataclass(frozen=True)
class RichTextValidationError:
    """Rich text validation error."""

    code: str
    message: str
    path: str | None = None


# --- Input Models ---


@dataclass(frozen=True)
class ValidateRichTextInput:
    """Input for validating rich text JSON structure."""

    document: dict[str, Any]


@dataclass(frozen=True)
class SanitizeRichTextInput:
    """Input for sanitizing rich text for XSS prevention."""

    document: dict[str, Any]


@dataclass(frozen=True)
class TransformRichTextInput:
    """Input for transforming and sanitizing rich text."""

    document: dict[str, Any]


# --- Output Models ---


@dataclass(frozen=True)
class ValidateOutput:
    """Output for validation result."""

    is_valid: bool
    errors: list[RichTextValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class SanitizeOutput:
    """Output for sanitized rich text."""

    document: dict[str, Any] | None
    errors: list[RichTextValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class TransformOutput:
    """Output for transformed and sanitized rich text."""

    document: dict[str, Any] | None
    errors: list[RichTextValidationError] = field(default_factory=list)
    success: bool = True
