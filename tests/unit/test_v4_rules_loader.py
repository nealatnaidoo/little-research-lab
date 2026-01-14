"""
TA-E2.3-01: V4 rules loader and validator tests.

Tests for loading and validating creator-publisher-v4_rules.yaml.
Implements fail-fast behavior for missing required sections.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from src.rules.v4_loader import (
    V4RulesValidationError,
    load_v4_rules,
    validate_required_sections,
)

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestLoadV4Rules:
    """TA-E2.3-01: Test v4 rules file loading."""

    def test_load_actual_v4_rules_file(self) -> None:
        """Load the actual creator-publisher-v4_rules.yaml file."""
        rules_path = PROJECT_ROOT / "creator-publisher-v4_rules.yaml"
        rules = load_v4_rules(rules_path)

        assert isinstance(rules, dict)
        assert "meta" in rules
        assert rules["meta"]["project_slug"] == "creator-publisher-v4"

    def test_load_nonexistent_file_raises(self) -> None:
        """Loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_v4_rules(Path("/nonexistent/rules.yaml"))

    def test_load_invalid_yaml_raises(self) -> None:
        """Loading invalid YAML raises ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()

            with pytest.raises(ValueError, match="Invalid YAML"):
                load_v4_rules(Path(f.name))

    def test_load_strips_markdown_code_fences(self) -> None:
        """Loader handles markdown-wrapped YAML files."""
        content = '''## creator-publisher-v4_rules.yaml

```yaml
meta:
  project_slug: test-project
  version: 1
  required_sections: []
```
'''
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(content)
            f.flush()

            rules = load_v4_rules(Path(f.name))
            assert rules["meta"]["project_slug"] == "test-project"


class TestValidateRequiredSections:
    """TA-E2.3-01: Test required section validation."""

    def test_all_required_sections_present(self) -> None:
        """No error when all required sections are present."""
        rules = {
            "meta": {
                "project_slug": "test",
                "version": 1,
                "required_sections": ["auth", "content"],
            },
            "auth": {"roles": {}},
            "content": {"states": []},
        }

        # Should not raise
        validate_required_sections(rules)

    def test_missing_required_section_raises(self) -> None:
        """Missing required section raises V4RulesValidationError."""
        rules = {
            "meta": {
                "project_slug": "test",
                "version": 1,
                "required_sections": ["auth", "content", "missing_section"],
            },
            "auth": {"roles": {}},
            "content": {"states": []},
        }

        with pytest.raises(V4RulesValidationError) as exc_info:
            validate_required_sections(rules)

        assert "missing_section" in str(exc_info.value)

    def test_multiple_missing_sections_reported(self) -> None:
        """All missing sections are reported in error."""
        rules = {
            "meta": {
                "project_slug": "test",
                "version": 1,
                "required_sections": ["auth", "content", "media", "analytics"],
            },
            "auth": {"roles": {}},
        }

        with pytest.raises(V4RulesValidationError) as exc_info:
            validate_required_sections(rules)

        error_msg = str(exc_info.value)
        assert "content" in error_msg
        assert "media" in error_msg
        assert "analytics" in error_msg

    def test_missing_meta_section_raises(self) -> None:
        """Missing meta section raises V4RulesValidationError."""
        rules = {"auth": {}}

        with pytest.raises(V4RulesValidationError, match="meta"):
            validate_required_sections(rules)

    def test_missing_required_sections_key_raises(self) -> None:
        """Missing required_sections key in meta raises error."""
        rules = {
            "meta": {
                "project_slug": "test",
                "version": 1,
            },
            "auth": {},
        }

        with pytest.raises(V4RulesValidationError, match="required_sections"):
            validate_required_sections(rules)

    def test_empty_required_sections_valid(self) -> None:
        """Empty required_sections list is valid."""
        rules = {
            "meta": {
                "project_slug": "test",
                "version": 1,
                "required_sections": [],
            },
        }

        # Should not raise
        validate_required_sections(rules)


class TestFailFastBehavior:
    """TA-E2.3-01: Test fail-fast validation behavior."""

    def test_load_with_validation_fails_fast(self) -> None:
        """load_v4_rules with validate=True fails fast on missing sections."""
        content = yaml.dump({
            "meta": {
                "project_slug": "test",
                "version": 1,
                "required_sections": ["auth", "missing"],
            },
            "auth": {},
        })

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(content)
            f.flush()

            with pytest.raises(V4RulesValidationError):
                load_v4_rules(Path(f.name), validate=True)

    def test_load_without_validation_succeeds(self) -> None:
        """load_v4_rules with validate=False loads without checking sections."""
        content = yaml.dump({
            "meta": {
                "project_slug": "test",
                "version": 1,
                "required_sections": ["auth", "missing"],
            },
            "auth": {},
        })

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(content)
            f.flush()

            rules = load_v4_rules(Path(f.name), validate=False)
            assert rules["meta"]["project_slug"] == "test"


class TestActualV4RulesFile:
    """TA-E2.3-01: Test actual v4 rules file validation."""

    def test_v4_rules_has_required_meta_fields(self) -> None:
        """V4 rules file has required meta fields."""
        rules_path = PROJECT_ROOT / "creator-publisher-v4_rules.yaml"
        rules = load_v4_rules(rules_path, validate=False)

        assert "meta" in rules
        assert "project_slug" in rules["meta"]
        assert "version" in rules["meta"]
        assert "required_sections" in rules["meta"]

    def test_v4_rules_passes_validation(self) -> None:
        """V4 rules file passes required section validation."""
        rules_path = PROJECT_ROOT / "creator-publisher-v4_rules.yaml"

        # Should not raise
        rules = load_v4_rules(rules_path, validate=True)
        assert rules["meta"]["project_slug"] == "creator-publisher-v4"

    def test_v4_rules_has_all_required_sections(self) -> None:
        """V4 rules file has all sections listed in meta.required_sections."""
        rules_path = PROJECT_ROOT / "creator-publisher-v4_rules.yaml"
        rules = load_v4_rules(rules_path, validate=False)

        required = rules["meta"]["required_sections"]
        for section in required:
            assert section in rules, f"Missing required section: {section}"


class TestV4RulesValidationError:
    """Test V4RulesValidationError exception."""

    def test_error_contains_missing_sections(self) -> None:
        """Error message lists all missing sections."""
        error = V4RulesValidationError(["auth", "content"])
        assert "auth" in str(error)
        assert "content" in str(error)

    def test_error_is_value_error_subclass(self) -> None:
        """V4RulesValidationError is a ValueError subclass."""
        error = V4RulesValidationError(["auth"])
        assert isinstance(error, ValueError)
