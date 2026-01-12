"""
Rules component - Load and validate rules.yaml configuration.

Spec refs: E0, HV1, HV2
Test assertions: TA-0100

This component provides fail-fast validation of the rules.yaml configuration.
All domain behavior is driven by rules, and invalid rules must halt startup.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    LoadRulesInput,
    LoadRulesOutput,
    RulesSchema,
    ValidateRulesInput,
    ValidateRulesOutput,
)
from .ports import EnvironmentPort, FileSystemPort

# Default rules file path (relative to project root)
DEFAULT_RULES_PATH = "little-research-lab-v3_rules.yaml"


class RulesValidationError(Exception):
    """Raised when rules.yaml fails schema validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Rules validation failed: {'; '.join(errors)}")


def _find_project_root() -> Path:
    """Find project root by looking for marker files."""
    current = Path.cwd()

    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent

    return current


def _validate_rules_dict(rules: dict[str, Any], schema: RulesSchema) -> list[str]:
    """Pure validation logic - no I/O."""
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


def run_validate(
    inp: ValidateRulesInput,
    *,
    schema: RulesSchema | None = None,
) -> ValidateRulesOutput:
    """
    Validate rules dictionary against schema.

    Pure function - no I/O operations.

    Args:
        inp: Input containing rules dictionary to validate.
        schema: Schema to validate against. Uses default if None.

    Returns:
        ValidateRulesOutput with validation errors (empty if valid).
    """
    if schema is None:
        schema = RulesSchema()

    errors = _validate_rules_dict(inp.rules, schema)
    return ValidateRulesOutput(errors=errors, is_valid=len(errors) == 0)


def run_load(
    inp: LoadRulesInput,
    *,
    fs: FileSystemPort,
    env: EnvironmentPort,
) -> LoadRulesOutput:
    """
    Load rules from file system.

    Args:
        inp: Input containing optional rules path.
        fs: File system port for reading files.
        env: Environment port for reading env vars.

    Returns:
        LoadRulesOutput with loaded rules or errors.
    """
    rules_path: Path

    if inp.rules_path is not None:
        rules_path = Path(inp.rules_path)
    else:
        env_path = env.get("RULES_PATH")
        if env_path:
            rules_path = Path(env_path)
        else:
            rules_path = _find_project_root() / DEFAULT_RULES_PATH

    if not fs.exists(rules_path):
        return LoadRulesOutput(
            rules={},
            errors=[f"Rules file not found: {rules_path}"],
            success=False,
        )

    try:
        rules = fs.read_yaml(rules_path)
        return LoadRulesOutput(rules=rules, errors=[], success=True)
    except Exception as e:
        return LoadRulesOutput(
            rules={},
            errors=[f"Failed to parse rules file: {e}"],
            success=False,
        )


def run(
    inp: LoadRulesInput,
    *,
    fs: FileSystemPort,
    env: EnvironmentPort,
    schema: RulesSchema | None = None,
) -> LoadRulesOutput:
    """
    Load and validate rules with fail-fast behavior.

    This is the main entry point for the rules component.

    Args:
        inp: Input containing optional rules path.
        fs: File system port for reading files.
        env: Environment port for reading env vars.
        schema: Schema to validate against. Uses default if None.

    Returns:
        LoadRulesOutput with validated rules or errors.
    """
    # Load rules from file
    load_result = run_load(inp, fs=fs, env=env)
    if not load_result.success:
        return load_result

    # Validate loaded rules
    validate_result = run_validate(
        ValidateRulesInput(rules=load_result.rules),
        schema=schema,
    )

    if not validate_result.is_valid:
        return LoadRulesOutput(
            rules=load_result.rules,
            errors=validate_result.errors,
            success=False,
        )

    return load_result
