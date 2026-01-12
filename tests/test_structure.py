"""
TA-0000: Structure lint tests
Verify that the v3 atomic component skeleton exists and follows conventions.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


class TestProjectStructure:
    """TA-0000: Verify project structure follows v3 conventions."""

    def test_core_directories_exist(self) -> None:
        """Core functional directories must exist."""
        assert (PROJECT_ROOT / "src" / "core").is_dir()
        assert (PROJECT_ROOT / "src" / "core" / "ports").is_dir()
        assert (PROJECT_ROOT / "src" / "core" / "services").is_dir()

    def test_shell_directories_exist(self) -> None:
        """Shell (imperative) directories must exist."""
        assert (PROJECT_ROOT / "src" / "shell").is_dir()
        assert (PROJECT_ROOT / "src" / "shell" / "http").is_dir()
        assert (PROJECT_ROOT / "src" / "shell" / "ui").is_dir()

    def test_adapters_directory_exists(self) -> None:
        """Adapters directory must exist."""
        assert (PROJECT_ROOT / "src" / "adapters").is_dir()

    def test_manifests_directory_exists(self) -> None:
        """Manifests directory must exist."""
        assert (PROJECT_ROOT / "manifests").is_dir()

    def test_artifacts_directory_exists(self) -> None:
        """Artifacts directory must exist for evidence output."""
        assert (PROJECT_ROOT / "artifacts").is_dir()

    def test_tests_structure_exists(self) -> None:
        """Test directories must follow conventions."""
        assert (PROJECT_ROOT / "tests").is_dir()
        assert (PROJECT_ROOT / "tests" / "unit").is_dir()
        assert (PROJECT_ROOT / "tests" / "integration").is_dir()
        assert (PROJECT_ROOT / "tests" / "regression").is_dir()

    def test_component_manifest_exists_and_valid(self) -> None:
        """Component manifest must exist and be valid JSON."""
        manifest_path = PROJECT_ROOT / "manifests" / "component_manifest.json"
        assert manifest_path.is_file(), "component_manifest.json must exist"

        with open(manifest_path) as f:
            manifest = json.load(f)

        assert manifest.get("schema_version") == "1.0"
        assert manifest.get("project_slug") == "little-research-lab-v3"
        assert "components" in manifest
        assert "ports" in manifest
        assert len(manifest["components"]) == 14  # C0-C13
        assert len(manifest["ports"]) == 4  # P1-P4

    def test_init_files_present(self) -> None:
        """Python packages must have __init__.py files."""
        packages = [
            "src/core",
            "src/core/ports",
            "src/core/services",
            "src/shell",
            "src/shell/http",
            "src/shell/ui",
            "src/adapters",
            "tests",
            "tests/unit",
            "tests/integration",
            "tests/regression",
        ]
        for pkg in packages:
            init_file = PROJECT_ROOT / pkg / "__init__.py"
            assert init_file.is_file(), f"Missing __init__.py in {pkg}"


class TestV3ArtifactsPresent:
    """Verify v3 BA artifacts are present."""

    def test_spec_exists(self) -> None:
        assert (PROJECT_ROOT / "little-research-lab-v3_spec.md").is_file()

    def test_tasklist_exists(self) -> None:
        assert (PROJECT_ROOT / "little-research-lab-v3_tasklist.md").is_file()

    def test_rules_exists(self) -> None:
        assert (PROJECT_ROOT / "little-research-lab-v3_rules.yaml").is_file()

    def test_quality_gates_exists(self) -> None:
        assert (PROJECT_ROOT / "little-research-lab-v3_quality_gates.md").is_file()

    def test_evolution_exists(self) -> None:
        assert (PROJECT_ROOT / "little-research-lab-v3_evolution.md").is_file()

    def test_decisions_exists(self) -> None:
        assert (PROJECT_ROOT / "little-research-lab-v3_decisions.md").is_file()
