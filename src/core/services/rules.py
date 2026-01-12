"""
Rules loader and schema validator for little-research-lab-v3.

Spec refs: E0, HV1, HV2
Test assertions: TA-0100

This module provides fail-fast validation of the rules.yaml configuration.
All domain behavior is driven by rules, and invalid rules must halt startup.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Default rules file path (relative to project root)
DEFAULT_RULES_PATH = "little-research-lab-v3_rules.yaml"


class RulesValidationError(Exception):
    """Raised when rules.yaml fails schema validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Rules validation failed: {'; '.join(errors)}")


@dataclass
class RulesSchema:
    """Expected schema for rules.yaml validation."""

    # Required top-level fields
    REQUIRED_TOP_LEVEL: list[str] = field(
        default_factory=lambda: ["schema_version", "project_slug", "required_sections"]
    )

    # Expected schema version
    EXPECTED_SCHEMA_VERSION: int = 1

    # Required sections (must match required_sections field in rules.yaml)
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

    # Section-specific required fields
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
            "feature_flags": [],  # Optional flags, no required fields
            "env": ["required"],
        }
    )


def _find_project_root() -> Path:
    """Find project root by looking for marker files."""
    current = Path.cwd()

    # Walk up looking for pyproject.toml or .git
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent

    return current


def load_rules_file(rules_path: Path | str | None = None) -> dict[str, Any]:
    """
    Load rules.yaml from disk.

    Args:
        rules_path: Path to rules file. If None, uses default location.

    Returns:
        Parsed rules dictionary.

    Raises:
        FileNotFoundError: If rules file doesn't exist.
        yaml.YAMLError: If rules file is invalid YAML.
    """
    if rules_path is None:
        # Check environment variable first
        env_path = os.environ.get("RULES_PATH")
        if env_path:
            rules_path = Path(env_path)
        else:
            rules_path = _find_project_root() / DEFAULT_RULES_PATH

    rules_path = Path(rules_path)

    if not rules_path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")

    with open(rules_path) as f:
        result: dict[str, Any] = yaml.safe_load(f)
        return result


def validate_rules(rules: dict[str, Any], schema: RulesSchema | None = None) -> list[str]:
    """
    Validate rules dictionary against schema.

    Args:
        rules: Parsed rules dictionary.
        schema: Schema to validate against. Uses default if None.

    Returns:
        List of validation error messages (empty if valid).
    """
    if schema is None:
        schema = RulesSchema()

    errors: list[str] = []

    # Check required top-level fields
    for field_name in schema.REQUIRED_TOP_LEVEL:
        if field_name not in rules:
            errors.append(f"Missing required top-level field: {field_name}")

    # Check schema version
    if "schema_version" in rules:
        if rules["schema_version"] != schema.EXPECTED_SCHEMA_VERSION:
            errors.append(
                f"Invalid schema_version: expected {schema.EXPECTED_SCHEMA_VERSION}, "
                f"got {rules['schema_version']}"
            )

    # Check project_slug is a non-empty string
    if "project_slug" in rules:
        if not isinstance(rules["project_slug"], str) or not rules["project_slug"]:
            errors.append("project_slug must be a non-empty string")

    # Check required_sections matches expected sections
    if "required_sections" in rules:
        declared_sections = set(rules["required_sections"])
        expected_sections = set(schema.REQUIRED_SECTIONS)
        missing_declared = expected_sections - declared_sections
        if missing_declared:
            errors.append(f"required_sections missing expected: {sorted(missing_declared)}")

    # Check all required sections exist
    for section in schema.REQUIRED_SECTIONS:
        if section not in rules:
            errors.append(f"Missing required section: {section}")
        elif not isinstance(rules[section], dict):
            errors.append(f"Section {section} must be a dictionary")
        else:
            # Check section-specific required fields
            required_fields = schema.SECTION_REQUIRED_FIELDS.get(section, [])
            for field_name in required_fields:
                if field_name not in rules[section]:
                    errors.append(f"Section {section} missing required field: {field_name}")

    # Validate specific critical security settings (HV1)
    if "security" in rules and isinstance(rules["security"], dict):
        security = rules["security"]
        if security.get("deny_by_default") is not True:
            errors.append("security.deny_by_default must be true (HV1)")

        if "session" in security and isinstance(security["session"], dict):
            session = security["session"]
            if "cookie" in session and isinstance(session["cookie"], dict):
                cookie = session["cookie"]
                if cookie.get("http_only") is not True:
                    errors.append("security.session.cookie.http_only must be true (HV1)")
                if cookie.get("secure") is not True:
                    errors.append("security.session.cookie.secure must be true (HV1)")

    # Validate analytics privacy settings (HV2)
    if "analytics" in rules and isinstance(rules["analytics"], dict):
        analytics = rules["analytics"]
        if "privacy" in analytics and isinstance(analytics["privacy"], dict):
            privacy = analytics["privacy"]
            if privacy.get("store_ip") is not False:
                errors.append("analytics.privacy.store_ip must be false (HV2)")
            if privacy.get("store_full_user_agent") is not False:
                errors.append("analytics.privacy.store_full_user_agent must be false (HV2)")
            if privacy.get("store_cookies") is not False:
                errors.append("analytics.privacy.store_cookies must be false (HV2)")
            if privacy.get("store_visitor_identifiers") is not False:
                errors.append("analytics.privacy.store_visitor_identifiers must be false (HV2)")

        if "ingestion" in analytics and isinstance(analytics["ingestion"], dict):
            ingestion = analytics["ingestion"]
            if "schema" in ingestion and isinstance(ingestion["schema"], dict):
                schema_def = ingestion["schema"]
                forbidden = schema_def.get("forbidden_fields", [])
                required_forbidden = ["ip", "ip_address", "user_agent", "cookie", "email"]
                missing_forbidden = set(required_forbidden) - set(forbidden)
                if missing_forbidden:
                    errors.append(
                        f"analytics.ingestion.schema.forbidden_fields must include: "
                        f"{sorted(missing_forbidden)} (HV2)"
                    )

    return errors


def load_and_validate_rules(rules_path: Path | str | None = None) -> dict[str, Any]:
    """
    Load and validate rules.yaml with fail-fast behavior.

    This is the main entry point for startup validation.

    Args:
        rules_path: Path to rules file. If None, uses default location.

    Returns:
        Validated rules dictionary.

    Raises:
        FileNotFoundError: If rules file doesn't exist.
        yaml.YAMLError: If rules file is invalid YAML.
        RulesValidationError: If rules fail schema validation.
    """
    rules = load_rules_file(rules_path)
    errors = validate_rules(rules)

    if errors:
        raise RulesValidationError(errors)

    return rules


# Singleton for app-wide rules access
_loaded_rules: dict[str, Any] | None = None


def get_rules() -> dict[str, Any]:
    """
    Get the loaded rules (must call init_rules first).

    Returns:
        Rules dictionary.

    Raises:
        RuntimeError: If rules have not been initialized.
    """
    if _loaded_rules is None:
        raise RuntimeError("Rules not initialized. Call init_rules() at startup.")
    return _loaded_rules


def init_rules(rules_path: Path | str | None = None) -> dict[str, Any]:
    """
    Initialize rules at application startup.

    This should be called once at startup before any request handling.
    Fail-fast: raises on any validation error.

    Args:
        rules_path: Path to rules file. If None, uses default location.

    Returns:
        Validated rules dictionary.

    Raises:
        FileNotFoundError: If rules file doesn't exist.
        yaml.YAMLError: If rules file is invalid YAML.
        RulesValidationError: If rules fail schema validation.
    """
    global _loaded_rules
    _loaded_rules = load_and_validate_rules(rules_path)
    return _loaded_rules


def reset_rules() -> None:
    """Reset loaded rules (for testing only)."""
    global _loaded_rules
    _loaded_rules = None
