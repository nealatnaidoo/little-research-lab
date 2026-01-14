"""
TA-E1.1-01: Component template structure tests.

Tests for v4 atomic component template and manifest schema validation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestTemplateStructure:
    """TA-E1.1-01: Verify _template has required structure."""

    def test_template_directory_exists(self) -> None:
        """Template directory must exist."""
        template_path = PROJECT_ROOT / "src" / "components" / "_template"
        assert template_path.is_dir(), "_template directory must exist"

    def test_template_has_fc_directory(self) -> None:
        """Template must have fc/ (Functional Core) directory."""
        fc_path = PROJECT_ROOT / "src" / "components" / "_template" / "fc"
        assert fc_path.is_dir(), "fc/ directory must exist"
        assert (fc_path / "__init__.py").is_file(), "fc/__init__.py must exist"

    def test_template_has_is_directory(self) -> None:
        """Template must have is/ (Imperative Shell) directory."""
        is_path = PROJECT_ROOT / "src" / "components" / "_template" / "is"
        assert is_path.is_dir(), "is/ directory must exist"
        assert (is_path / "__init__.py").is_file(), "is/__init__.py must exist"

    def test_template_has_tests_directory(self) -> None:
        """Template must have tests/ directory."""
        tests_path = PROJECT_ROOT / "src" / "components" / "_template" / "tests"
        assert tests_path.is_dir(), "tests/ directory must exist"
        assert (tests_path / "__init__.py").is_file(), "tests/__init__.py must exist"

    def test_template_has_contract(self) -> None:
        """Template must have contract.md."""
        contract_path = PROJECT_ROOT / "src" / "components" / "_template" / "contract.md"
        assert contract_path.is_file(), "contract.md must exist"

    def test_template_has_init(self) -> None:
        """Template must have __init__.py."""
        init_path = PROJECT_ROOT / "src" / "components" / "_template" / "__init__.py"
        assert init_path.is_file(), "__init__.py must exist"


class TestContractTemplate:
    """TA-E1.1-01: Contract template includes all required sections."""

    @pytest.fixture
    def contract_content(self) -> str:
        """Load contract template content."""
        contract_path = PROJECT_ROOT / "src" / "components" / "_template" / "contract.md"
        return contract_path.read_text()

    def test_has_component_id_section(self, contract_content: str) -> None:
        """Contract must have COMPONENT_ID section."""
        assert "## COMPONENT_ID" in contract_content

    def test_has_purpose_section(self, contract_content: str) -> None:
        """Contract must have PURPOSE section."""
        assert "## PURPOSE" in contract_content

    def test_has_inputs_section(self, contract_content: str) -> None:
        """Contract must have INPUTS section."""
        assert "## INPUTS" in contract_content

    def test_has_outputs_section(self, contract_content: str) -> None:
        """Contract must have OUTPUTS section."""
        assert "## OUTPUTS" in contract_content

    def test_has_dependencies_section(self, contract_content: str) -> None:
        """Contract must have DEPENDENCIES (PORTS) section."""
        assert "## DEPENDENCIES (PORTS)" in contract_content

    def test_has_side_effects_section(self, contract_content: str) -> None:
        """Contract must have SIDE EFFECTS section."""
        assert "## SIDE EFFECTS" in contract_content

    def test_has_invariants_section(self, contract_content: str) -> None:
        """Contract must have INVARIANTS section."""
        assert "## INVARIANTS" in contract_content

    def test_has_error_semantics_section(self, contract_content: str) -> None:
        """Contract must have ERROR SEMANTICS section."""
        assert "## ERROR SEMANTICS" in contract_content

    def test_has_fc_section(self, contract_content: str) -> None:
        """Contract must have FC (Functional Core) section."""
        assert "## FC (Functional Core)" in contract_content

    def test_has_is_section(self, contract_content: str) -> None:
        """Contract must have IS (Imperative Shell) section."""
        assert "## IS (Imperative Shell)" in contract_content

    def test_has_tests_section(self, contract_content: str) -> None:
        """Contract must have TESTS section."""
        assert "## TESTS" in contract_content

    def test_has_evidence_section(self, contract_content: str) -> None:
        """Contract must have EVIDENCE section."""
        assert "## EVIDENCE" in contract_content


class TestManifestSchema:
    """TA-E1.1-01: Manifest schema validation tests."""

    @pytest.fixture
    def schema(self) -> dict:
        """Load manifest schema."""
        schema_path = PROJECT_ROOT / "schemas" / "manifest.schema.json"
        with open(schema_path) as f:
            return json.load(f)

    def test_schema_exists(self) -> None:
        """Manifest schema must exist."""
        schema_path = PROJECT_ROOT / "schemas" / "manifest.schema.json"
        assert schema_path.is_file(), "manifest.schema.json must exist"

    def test_schema_is_valid_json(self) -> None:
        """Schema must be valid JSON."""
        schema_path = PROJECT_ROOT / "schemas" / "manifest.schema.json"
        with open(schema_path) as f:
            schema = json.load(f)
        assert isinstance(schema, dict)

    def test_schema_has_required_fields(self, schema: dict) -> None:
        """Schema must define required fields."""
        assert "$schema" in schema
        assert "title" in schema
        assert "properties" in schema
        assert "required" in schema

    def test_schema_requires_components(self, schema: dict) -> None:
        """Schema must require components field."""
        assert "components" in schema["required"]

    def test_schema_requires_ports(self, schema: dict) -> None:
        """Schema must require ports field."""
        assert "ports" in schema["required"]

    def test_schema_defines_component_structure(self, schema: dict) -> None:
        """Schema must define component structure."""
        assert "$defs" in schema
        assert "component" in schema["$defs"]
        component_def = schema["$defs"]["component"]
        assert "id" in component_def["required"]
        assert "name" in component_def["required"]
        assert "path" in component_def["required"]
        assert "status" in component_def["required"]

    def test_schema_defines_port_structure(self, schema: dict) -> None:
        """Schema must define port structure."""
        assert "port" in schema["$defs"]
        port_def = schema["$defs"]["port"]
        assert "id" in port_def["required"]
        assert "name" in port_def["required"]
        assert "adapters" in port_def["required"]


class TestFCISDocstrings:
    """TA-E1.1-01: Verify FC and IS have proper documentation."""

    def test_fc_init_has_docstring(self) -> None:
        """FC __init__.py must have documentation."""
        fc_init = PROJECT_ROOT / "src" / "components" / "_template" / "fc" / "__init__.py"
        content = fc_init.read_text()
        assert '"""' in content, "FC must have docstring"
        assert "pure" in content.lower(), "FC docstring must mention pure functions"
        assert "no I/O" in content or "No I/O" in content or "no io" in content.lower()

    def test_is_init_has_docstring(self) -> None:
        """IS __init__.py must have documentation."""
        is_init = PROJECT_ROOT / "src" / "components" / "_template" / "is" / "__init__.py"
        content = is_init.read_text()
        assert '"""' in content, "IS must have docstring"
        assert "shell" in content.lower() or "I/O" in content

    def test_tests_init_has_docstring(self) -> None:
        """Tests __init__.py must have documentation."""
        tests_init = PROJECT_ROOT / "src" / "components" / "_template" / "tests" / "__init__.py"
        content = tests_init.read_text()
        assert '"""' in content, "Tests must have docstring"
