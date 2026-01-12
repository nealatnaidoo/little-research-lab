"""
TA-0100: Rules schema validation tests.

Verifies that the rules loader correctly validates rules.yaml structure
and enforces hard-verify constraints (HV1, HV2).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.core.services.rules import (
    RulesSchema,
    RulesValidationError,
    init_rules,
    load_and_validate_rules,
    load_rules_file,
    reset_rules,
    validate_rules,
)


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def valid_rules_path(project_root: Path) -> Path:
    """Path to the actual rules.yaml file."""
    return project_root / "little-research-lab-v3_rules.yaml"


@pytest.fixture(autouse=True)
def cleanup_rules() -> None:
    """Reset rules singleton after each test."""
    yield
    reset_rules()


def create_temp_rules(rules: dict[str, Any]) -> Path:
    """Create a temporary rules file for testing."""
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with open(path, "w") as f:
        yaml.dump(rules, f)
    return Path(path)


class TestRulesLoading:
    """Test rules file loading."""

    def test_load_actual_rules_file(self, valid_rules_path: Path) -> None:
        """Rules file loads successfully."""
        rules = load_rules_file(valid_rules_path)
        assert isinstance(rules, dict)
        assert rules["schema_version"] == 1
        assert rules["project_slug"] == "little-research-lab-v3"

    def test_load_nonexistent_file_raises(self) -> None:
        """Loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_rules_file("/nonexistent/path/rules.yaml")

    def test_load_invalid_yaml_raises(self) -> None:
        """Loading invalid YAML raises error."""
        fd, path = tempfile.mkstemp(suffix=".yaml")
        with open(path, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            load_rules_file(path)


class TestRulesSchemaValidation:
    """Test rules schema validation logic."""

    def test_valid_rules_passes_validation(self, valid_rules_path: Path) -> None:
        """The actual rules.yaml passes all validation."""
        rules = load_rules_file(valid_rules_path)
        errors = validate_rules(rules)
        assert errors == [], f"Validation errors: {errors}"

    def test_missing_schema_version_fails(self) -> None:
        """Missing schema_version is reported."""
        rules = {"project_slug": "test", "required_sections": []}
        errors = validate_rules(rules)
        assert any("schema_version" in e for e in errors)

    def test_wrong_schema_version_fails(self) -> None:
        """Wrong schema_version is reported."""
        rules = {"schema_version": 99, "project_slug": "test", "required_sections": []}
        errors = validate_rules(rules)
        assert any("schema_version" in e and "expected 1" in e for e in errors)

    def test_missing_project_slug_fails(self) -> None:
        """Missing project_slug is reported."""
        rules = {"schema_version": 1, "required_sections": []}
        errors = validate_rules(rules)
        assert any("project_slug" in e for e in errors)

    def test_empty_project_slug_fails(self) -> None:
        """Empty project_slug is reported."""
        rules = {"schema_version": 1, "project_slug": "", "required_sections": []}
        errors = validate_rules(rules)
        assert any("project_slug must be a non-empty string" in e for e in errors)

    def test_missing_required_sections_fails(self) -> None:
        """Missing required_sections field is reported."""
        rules = {"schema_version": 1, "project_slug": "test"}
        errors = validate_rules(rules)
        assert any("required_sections" in e for e in errors)

    def test_missing_section_fails(self) -> None:
        """Missing a required section is reported."""
        rules = {
            "schema_version": 1,
            "project_slug": "test",
            "required_sections": ["security"],
            # security section is missing
        }
        errors = validate_rules(rules)
        assert any("Missing required section: security" in e for e in errors)

    def test_section_not_dict_fails(self) -> None:
        """Section that's not a dictionary is reported."""
        rules = {
            "schema_version": 1,
            "project_slug": "test",
            "required_sections": ["security"],
            "security": "not a dict",
        }
        errors = validate_rules(rules)
        assert any("security must be a dictionary" in e for e in errors)


class TestHV1SecurityValidation:
    """Test hard-verify security constraints (HV1)."""

    def test_deny_by_default_must_be_true(self) -> None:
        """security.deny_by_default must be true."""
        rules = {
            "schema_version": 1,
            "project_slug": "test",
            "required_sections": [],
            "security": {"deny_by_default": False, "session": {}, "headers": {}},
        }
        errors = validate_rules(rules)
        assert any("deny_by_default must be true" in e for e in errors)

    def test_cookie_http_only_must_be_true(self) -> None:
        """security.session.cookie.http_only must be true."""
        rules = {
            "schema_version": 1,
            "project_slug": "test",
            "required_sections": [],
            "security": {
                "deny_by_default": True,
                "session": {"cookie": {"http_only": False, "secure": True}},
                "headers": {},
            },
        }
        errors = validate_rules(rules)
        assert any("http_only must be true" in e for e in errors)

    def test_cookie_secure_must_be_true(self) -> None:
        """security.session.cookie.secure must be true."""
        rules = {
            "schema_version": 1,
            "project_slug": "test",
            "required_sections": [],
            "security": {
                "deny_by_default": True,
                "session": {"cookie": {"http_only": True, "secure": False}},
                "headers": {},
            },
        }
        errors = validate_rules(rules)
        assert any("secure must be true" in e for e in errors)


class TestHV2PrivacyValidation:
    """Test hard-verify privacy constraints (HV2)."""

    def test_store_ip_must_be_false(self) -> None:
        """analytics.privacy.store_ip must be false."""
        rules = {
            "schema_version": 1,
            "project_slug": "test",
            "required_sections": [],
            "analytics": {
                "modes": [],
                "ingestion": {"schema": {"forbidden_fields": []}},
                "aggregation": {},
                "privacy": {
                    "store_ip": True,
                    "store_full_user_agent": False,
                    "store_cookies": False,
                    "store_visitor_identifiers": False,
                },
            },
        }
        errors = validate_rules(rules)
        assert any("store_ip must be false" in e for e in errors)

    def test_store_full_user_agent_must_be_false(self) -> None:
        """analytics.privacy.store_full_user_agent must be false."""
        rules = {
            "schema_version": 1,
            "project_slug": "test",
            "required_sections": [],
            "analytics": {
                "modes": [],
                "ingestion": {"schema": {"forbidden_fields": []}},
                "aggregation": {},
                "privacy": {
                    "store_ip": False,
                    "store_full_user_agent": True,
                    "store_cookies": False,
                    "store_visitor_identifiers": False,
                },
            },
        }
        errors = validate_rules(rules)
        assert any("store_full_user_agent must be false" in e for e in errors)

    def test_forbidden_fields_must_include_pii(self) -> None:
        """analytics.ingestion.schema.forbidden_fields must include PII fields."""
        rules = {
            "schema_version": 1,
            "project_slug": "test",
            "required_sections": [],
            "analytics": {
                "modes": [],
                "ingestion": {"schema": {"forbidden_fields": []}},
                "aggregation": {},
                "privacy": {
                    "store_ip": False,
                    "store_full_user_agent": False,
                    "store_cookies": False,
                    "store_visitor_identifiers": False,
                },
            },
        }
        errors = validate_rules(rules)
        assert any("forbidden_fields must include" in e for e in errors)


class TestLoadAndValidate:
    """Test combined load and validate function."""

    def test_load_and_validate_actual_rules(self, valid_rules_path: Path) -> None:
        """load_and_validate_rules succeeds with valid rules."""
        rules = load_and_validate_rules(valid_rules_path)
        assert rules["schema_version"] == 1

    def test_load_and_validate_raises_on_invalid(self) -> None:
        """load_and_validate_rules raises RulesValidationError on invalid rules."""
        invalid_rules = {"schema_version": 99}
        path = create_temp_rules(invalid_rules)

        with pytest.raises(RulesValidationError) as exc_info:
            load_and_validate_rules(path)

        assert len(exc_info.value.errors) > 0


class TestInitRules:
    """Test rules initialization for startup."""

    def test_init_rules_success(self, valid_rules_path: Path) -> None:
        """init_rules loads and validates successfully."""
        rules = init_rules(valid_rules_path)
        assert rules["schema_version"] == 1

    def test_init_rules_fail_fast(self) -> None:
        """init_rules raises immediately on invalid rules."""
        invalid_rules = {"schema_version": 99}
        path = create_temp_rules(invalid_rules)

        with pytest.raises(RulesValidationError):
            init_rules(path)


class TestActualRulesFileComprehensive:
    """Comprehensive tests on the actual rules.yaml file."""

    def test_all_required_sections_present(self, valid_rules_path: Path) -> None:
        """All required sections are present in rules.yaml."""
        rules = load_rules_file(valid_rules_path)
        schema = RulesSchema()

        for section in schema.REQUIRED_SECTIONS:
            assert section in rules, f"Missing section: {section}"
            assert isinstance(rules[section], dict), f"Section {section} is not a dict"

    def test_content_status_machine_valid(self, valid_rules_path: Path) -> None:
        """Content status machine has valid transitions."""
        rules = load_rules_file(valid_rules_path)
        status_machine = rules["content"]["status_machine"]

        # Check all statuses exist
        assert "draft" in status_machine
        assert "scheduled" in status_machine
        assert "published" in status_machine

        # Check transitions are valid
        for _status, config in status_machine.items():
            assert "can_transition_to" in config
            for target in config["can_transition_to"]:
                assert target in status_machine, f"Invalid transition target: {target}"

    def test_analytics_modes_valid(self, valid_rules_path: Path) -> None:
        """Analytics modes include required options."""
        rules = load_rules_file(valid_rules_path)
        modes = rules["analytics"]["modes"]

        assert "off" in modes
        assert "basic" in modes

    def test_asset_versioning_immutable(self, valid_rules_path: Path) -> None:
        """Asset versioning is configured as immutable."""
        rules = load_rules_file(valid_rules_path)
        versioning = rules["assets"]["versioning"]

        assert versioning["immutable_versions"] is True

    def test_env_required_vars_present(self, valid_rules_path: Path) -> None:
        """Required environment variables are specified."""
        rules = load_rules_file(valid_rules_path)
        required = rules["env"]["required"]

        assert "BASE_URL" in required
        assert "SESSION_SECRET" in required
        assert "DATABASE_URL" in required
