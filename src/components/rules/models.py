"""
Rules component input/output models.

Spec refs: E0, HV1, HV2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LoadRulesInput:
    """Input for loading rules."""

    rules_path: Path | str | None = None


@dataclass(frozen=True)
class LoadRulesOutput:
    """Output from loading rules."""

    rules: dict[str, Any]
    errors: list[str] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class ValidateRulesInput:
    """Input for validating rules."""

    rules: dict[str, Any]


@dataclass(frozen=True)
class ValidateRulesOutput:
    """Output from validating rules."""

    errors: list[str]
    is_valid: bool


@dataclass
class RulesSchema:
    """Expected schema for rules.yaml validation."""

    REQUIRED_TOP_LEVEL: list[str] = field(
        default_factory=lambda: ["schema_version", "project_slug", "required_sections"]
    )

    EXPECTED_SCHEMA_VERSION: int = 1

    REQUIRED_SECTIONS: list[str] = field(
        default_factory=lambda: [
            "security",
            "auth",
            "routing",
            "content",
            "assets",
            "scheduler",
            "analytics",
            "redirects",
            "observability",
            "feature_flags",
            "env",
        ]
    )

    SECTION_REQUIRED_FIELDS: dict[str, list[str]] = field(
        default_factory=lambda: {
            "security": ["deny_by_default", "session", "headers"],
            "auth": ["roles", "admin_only_routes_prefixes", "rate_limits"],
            "routing": ["timezone_display", "namespaces", "public_visibility"],
            "content": ["types", "status_machine", "publish_guards"],
            "assets": ["kinds", "versioning", "serving", "storage"],
            "scheduler": ["idempotency", "timing", "retries"],
            "analytics": ["modes", "ingestion", "aggregation", "privacy"],
            "redirects": ["enabled", "status_code", "constraints"],
            "observability": ["logs", "metrics", "health"],
            "feature_flags": [],
            "env": ["required"],
        }
    )
