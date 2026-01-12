"""
Tests for Quality Gates Runner (T-0003).

Spec refs: QG, R1, TA-0101
Test assertions:
- TA-0101: Gates produce valid JSON artifacts
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from quality_gates import (
    GATES,
    GateConfig,
    GateResult,
    GatesReport,
    generate_report,
    run_all_gates,
    run_gate,
    write_artifacts,
)

# --- Test Fixtures ---


@pytest.fixture
def sample_gate_config() -> GateConfig:
    """Create a sample gate config for testing."""
    return GateConfig(
        name="test_gate",
        description="Test gate",
        command=["echo", "hello"],
        required=True,
        timeout_seconds=30,
    )


@pytest.fixture
def sample_gate_result() -> GateResult:
    """Create a sample gate result for testing."""
    return GateResult(
        name="test_gate",
        status="pass",
        exit_code=0,
        duration_seconds=1.5,
        stdout="hello\n",
        stderr="",
        command=["echo", "hello"],
        required=True,
    )


@pytest.fixture
def sample_results() -> list[GateResult]:
    """Create sample results for report testing."""
    return [
        GateResult(
            name="gate1",
            status="pass",
            exit_code=0,
            duration_seconds=1.0,
            stdout="passed",
            stderr="",
            command=["cmd1"],
            required=True,
        ),
        GateResult(
            name="gate2",
            status="fail",
            exit_code=1,
            duration_seconds=2.0,
            stdout="",
            stderr="error occurred",
            command=["cmd2"],
            required=True,
        ),
        GateResult(
            name="gate3",
            status="warn",
            exit_code=1,
            duration_seconds=0.5,
            stdout="warning",
            stderr="",
            command=["cmd3"],
            required=False,
        ),
        GateResult(
            name="gate4",
            status="skip",
            exit_code=0,
            duration_seconds=0,
            stdout="",
            stderr="Skipped by user",
            command=["cmd4"],
            required=True,
        ),
    ]


# --- GateConfig Tests ---


class TestGateConfig:
    """Tests for GateConfig dataclass."""

    def test_create_basic_config(self) -> None:
        """Test creating a basic gate config."""
        config = GateConfig(
            name="lint",
            description="Run linting",
            command=["ruff", "check", "."],
        )

        assert config.name == "lint"
        assert config.description == "Run linting"
        assert config.command == ["ruff", "check", "."]
        assert config.required is True  # Default
        assert config.timeout_seconds == 300  # Default
        assert config.test_markers == []  # Default

    def test_create_optional_config(self) -> None:
        """Test creating an optional gate config."""
        config = GateConfig(
            name="format",
            description="Check formatting",
            command=["ruff", "format", "--check", "."],
            required=False,
        )

        assert config.name == "format"
        assert config.required is False

    def test_create_config_with_markers(self) -> None:
        """Test creating config with test markers."""
        config = GateConfig(
            name="security",
            description="Security tests",
            command=["pytest", "-k", "security"],
            test_markers=["TA-0021", "TA-0022"],
        )

        assert config.test_markers == ["TA-0021", "TA-0022"]

    def test_create_config_with_custom_timeout(self) -> None:
        """Test creating config with custom timeout."""
        config = GateConfig(
            name="tests",
            description="All tests",
            command=["pytest"],
            timeout_seconds=600,
        )

        assert config.timeout_seconds == 600


# --- GateResult Tests ---


class TestGateResult:
    """Tests for GateResult dataclass."""

    def test_create_pass_result(self) -> None:
        """Test creating a passing result."""
        result = GateResult(
            name="lint",
            status="pass",
            exit_code=0,
            duration_seconds=2.5,
            stdout="All checks passed",
            stderr="",
            command=["ruff", "check", "."],
            required=True,
        )

        assert result.name == "lint"
        assert result.status == "pass"
        assert result.exit_code == 0
        assert result.duration_seconds == 2.5
        assert result.required is True

    def test_create_fail_result(self) -> None:
        """Test creating a failing result."""
        result = GateResult(
            name="tests",
            status="fail",
            exit_code=1,
            duration_seconds=30.0,
            stdout="",
            stderr="3 tests failed",
            command=["pytest"],
            required=True,
        )

        assert result.status == "fail"
        assert result.exit_code == 1
        assert "3 tests failed" in result.stderr

    def test_create_warn_result(self) -> None:
        """Test creating a warning result."""
        result = GateResult(
            name="format",
            status="warn",
            exit_code=1,
            duration_seconds=1.0,
            stdout="Would reformat 5 files",
            stderr="",
            command=["ruff", "format", "--check"],
            required=False,
        )

        assert result.status == "warn"
        assert result.required is False

    def test_create_skip_result(self) -> None:
        """Test creating a skipped result."""
        result = GateResult(
            name="security",
            status="skip",
            exit_code=0,
            duration_seconds=0,
            stdout="",
            stderr="Skipped by user",
            command=["pytest", "-k", "security"],
            required=True,
        )

        assert result.status == "skip"
        assert result.duration_seconds == 0


# --- GatesReport Tests ---


class TestGatesReport:
    """Tests for GatesReport dataclass."""

    def test_create_report(self, sample_results: list[GateResult]) -> None:
        """Test creating a gates report."""
        report = GatesReport(
            timestamp_utc="2025-01-01T00:00:00+00:00",
            overall_status="fail",
            total_gates=4,
            passed_gates=1,
            failed_gates=1,
            warned_gates=1,
            skipped_gates=1,
            gates=[{"name": r.name, "status": r.status} for r in sample_results],
            summary="# Summary\n\nTest summary",
        )

        assert report.overall_status == "fail"
        assert report.total_gates == 4
        assert report.passed_gates == 1
        assert report.failed_gates == 1
        assert len(report.gates) == 4


# --- run_gate Tests ---


class TestRunGate:
    """Tests for run_gate function."""

    @patch("quality_gates.subprocess.run")
    def test_run_gate_success(
        self,
        mock_run: MagicMock,
        sample_gate_config: GateConfig,
    ) -> None:
        """Test running a gate that succeeds."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="success output",
            stderr="",
        )

        result = run_gate(sample_gate_config)

        assert result.status == "pass"
        assert result.exit_code == 0
        assert result.name == "test_gate"
        assert result.stdout == "success output"

    @patch("quality_gates.subprocess.run")
    def test_run_gate_failure_required(
        self,
        mock_run: MagicMock,
        sample_gate_config: GateConfig,
    ) -> None:
        """Test running a required gate that fails."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error output",
        )

        result = run_gate(sample_gate_config)

        assert result.status == "fail"
        assert result.exit_code == 1
        assert result.stderr == "error output"

    @patch("quality_gates.subprocess.run")
    def test_run_gate_failure_optional(
        self,
        mock_run: MagicMock,
    ) -> None:
        """Test running an optional gate that fails (becomes warning)."""
        config = GateConfig(
            name="optional",
            description="Optional gate",
            command=["test"],
            required=False,
        )
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="",
        )

        result = run_gate(config)

        assert result.status == "warn"
        assert result.required is False

    @patch("quality_gates.subprocess.run")
    def test_run_gate_timeout(
        self,
        mock_run: MagicMock,
    ) -> None:
        """Test running a gate that times out."""
        import subprocess

        config = GateConfig(
            name="slow",
            description="Slow gate",
            command=["sleep", "1000"],
            timeout_seconds=1,
        )
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep", timeout=1)

        result = run_gate(config)

        assert result.status == "fail"
        assert result.exit_code == -1
        assert "Timeout" in result.stderr

    @patch("quality_gates.subprocess.run")
    def test_run_gate_exception(
        self,
        mock_run: MagicMock,
        sample_gate_config: GateConfig,
    ) -> None:
        """Test running a gate that raises exception."""
        mock_run.side_effect = OSError("Command not found")

        result = run_gate(sample_gate_config)

        assert result.status == "fail"
        assert result.exit_code == -1
        assert "Command not found" in result.stderr

    @patch("quality_gates.subprocess.run")
    def test_run_gate_captures_duration(
        self,
        mock_run: MagicMock,
        sample_gate_config: GateConfig,
    ) -> None:
        """Test that gate run captures duration."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = run_gate(sample_gate_config)

        assert result.duration_seconds >= 0
        assert isinstance(result.duration_seconds, float)


# --- run_all_gates Tests ---


class TestRunAllGates:
    """Tests for run_all_gates function."""

    @patch("quality_gates.run_gate")
    def test_run_all_gates_default(self, mock_run: MagicMock) -> None:
        """Test running all default gates."""
        mock_run.return_value = GateResult(
            name="test",
            status="pass",
            exit_code=0,
            duration_seconds=1.0,
            stdout="",
            stderr="",
            command=["test"],
            required=True,
        )

        results = run_all_gates()

        assert len(results) == len(GATES)
        assert mock_run.call_count == len(GATES)

    @patch("quality_gates.run_gate")
    def test_run_all_gates_with_skip(self, mock_run: MagicMock) -> None:
        """Test running gates with some skipped."""
        mock_run.return_value = GateResult(
            name="test",
            status="pass",
            exit_code=0,
            duration_seconds=1.0,
            stdout="",
            stderr="",
            command=["test"],
            required=True,
        )

        results = run_all_gates(skip_gates=["lint", "format"])

        # Should have skipped lint and format
        skipped = [r for r in results if r.status == "skip"]
        assert len(skipped) == 2
        assert {r.name for r in skipped} == {"lint", "format"}

    @patch("quality_gates.run_gate")
    def test_run_all_gates_custom_list(self, mock_run: MagicMock) -> None:
        """Test running custom list of gates."""
        mock_run.return_value = GateResult(
            name="test",
            status="pass",
            exit_code=0,
            duration_seconds=1.0,
            stdout="",
            stderr="",
            command=["test"],
            required=True,
        )

        custom_gates = [
            GateConfig(name="gate1", description="Gate 1", command=["cmd1"]),
            GateConfig(name="gate2", description="Gate 2", command=["cmd2"]),
        ]

        results = run_all_gates(gates=custom_gates)

        assert len(results) == 2


# --- generate_report Tests ---


class TestGenerateReport:
    """Tests for generate_report function."""

    def test_generate_report_all_pass(self) -> None:
        """Test generating report with all passing gates."""
        results = [
            GateResult(
                name=f"gate{i}",
                status="pass",
                exit_code=0,
                duration_seconds=1.0,
                stdout="",
                stderr="",
                command=[f"cmd{i}"],
                required=True,
            )
            for i in range(3)
        ]

        report = generate_report(results)

        assert report.overall_status == "pass"
        assert report.total_gates == 3
        assert report.passed_gates == 3
        assert report.failed_gates == 0

    def test_generate_report_with_failure(self, sample_results: list[GateResult]) -> None:
        """Test generating report with failures."""
        report = generate_report(sample_results)

        assert report.overall_status == "fail"
        assert report.passed_gates == 1
        assert report.failed_gates == 1
        assert report.warned_gates == 1
        assert report.skipped_gates == 1

    def test_generate_report_optional_failure_not_fail(self) -> None:
        """Test that optional gate failure doesn't fail overall."""
        results = [
            GateResult(
                name="required",
                status="pass",
                exit_code=0,
                duration_seconds=1.0,
                stdout="",
                stderr="",
                command=["cmd"],
                required=True,
            ),
            GateResult(
                name="optional",
                status="warn",  # Failed but optional
                exit_code=1,
                duration_seconds=1.0,
                stdout="",
                stderr="",
                command=["cmd"],
                required=False,
            ),
        ]

        report = generate_report(results)

        assert report.overall_status == "pass"
        assert report.warned_gates == 1

    def test_generate_report_summary_markdown(self, sample_results: list[GateResult]) -> None:
        """Test that report summary is valid markdown."""
        report = generate_report(sample_results)

        assert "# Quality Gates Summary" in report.summary
        assert "| Gate | Status |" in report.summary
        assert "## Statistics" in report.summary
        assert "## Failures" in report.summary  # Has failures

    def test_generate_report_gates_data(self, sample_results: list[GateResult]) -> None:
        """Test that gates data is correctly captured."""
        report = generate_report(sample_results)

        assert len(report.gates) == 4
        assert all("name" in g for g in report.gates)
        assert all("status" in g for g in report.gates)
        assert all("duration_seconds" in g for g in report.gates)

    def test_generate_report_timestamp(self, sample_results: list[GateResult]) -> None:
        """Test that report has valid timestamp."""
        report = generate_report(sample_results)

        assert report.timestamp_utc is not None
        # Should be ISO format
        assert "T" in report.timestamp_utc


# --- write_artifacts Tests (TA-0101) ---


class TestWriteArtifacts:
    """Tests for write_artifacts function - TA-0101."""

    def test_write_artifacts_creates_json(
        self, tmp_path: Path, sample_results: list[GateResult]
    ) -> None:
        """TA-0101: Test that JSON artifact is created."""
        import quality_gates

        original_dir = quality_gates.ARTIFACTS_DIR
        quality_gates.ARTIFACTS_DIR = tmp_path

        try:
            report = generate_report(sample_results)
            write_artifacts(report)

            json_path = tmp_path / "quality_gates_run.json"
            assert json_path.exists()
        finally:
            quality_gates.ARTIFACTS_DIR = original_dir

    def test_write_artifacts_valid_json(
        self, tmp_path: Path, sample_results: list[GateResult]
    ) -> None:
        """TA-0101: Test that JSON artifact is valid JSON."""
        import quality_gates

        original_dir = quality_gates.ARTIFACTS_DIR
        quality_gates.ARTIFACTS_DIR = tmp_path

        try:
            report = generate_report(sample_results)
            write_artifacts(report)

            json_path = tmp_path / "quality_gates_run.json"
            with open(json_path) as f:
                data = json.load(f)

            # Should not raise - valid JSON
            assert isinstance(data, dict)
        finally:
            quality_gates.ARTIFACTS_DIR = original_dir

    def test_write_artifacts_json_structure(
        self, tmp_path: Path, sample_results: list[GateResult]
    ) -> None:
        """TA-0101: Test that JSON artifact has expected structure."""
        import quality_gates

        original_dir = quality_gates.ARTIFACTS_DIR
        quality_gates.ARTIFACTS_DIR = tmp_path

        try:
            report = generate_report(sample_results)
            write_artifacts(report)

            json_path = tmp_path / "quality_gates_run.json"
            with open(json_path) as f:
                data = json.load(f)

            # Check required fields
            assert "timestamp_utc" in data
            assert "overall_status" in data
            assert "total_gates" in data
            assert "passed_gates" in data
            assert "failed_gates" in data
            assert "warned_gates" in data
            assert "skipped_gates" in data
            assert "gates" in data
            assert isinstance(data["gates"], list)
        finally:
            quality_gates.ARTIFACTS_DIR = original_dir

    def test_write_artifacts_creates_markdown(
        self, tmp_path: Path, sample_results: list[GateResult]
    ) -> None:
        """Test that markdown summary is created."""
        import quality_gates

        original_dir = quality_gates.ARTIFACTS_DIR
        quality_gates.ARTIFACTS_DIR = tmp_path

        try:
            report = generate_report(sample_results)
            write_artifacts(report)

            md_path = tmp_path / "quality_gates_summary.md"
            assert md_path.exists()
        finally:
            quality_gates.ARTIFACTS_DIR = original_dir

    def test_write_artifacts_markdown_content(
        self, tmp_path: Path, sample_results: list[GateResult]
    ) -> None:
        """Test that markdown summary has expected content."""
        import quality_gates

        original_dir = quality_gates.ARTIFACTS_DIR
        quality_gates.ARTIFACTS_DIR = tmp_path

        try:
            report = generate_report(sample_results)
            write_artifacts(report)

            md_path = tmp_path / "quality_gates_summary.md"
            content = md_path.read_text()

            assert "# Quality Gates Summary" in content
            assert "**Status**:" in content
        finally:
            quality_gates.ARTIFACTS_DIR = original_dir

    def test_write_artifacts_creates_directory(
        self, tmp_path: Path, sample_results: list[GateResult]
    ) -> None:
        """Test that artifacts directory is created if it doesn't exist."""
        import quality_gates

        original_dir = quality_gates.ARTIFACTS_DIR
        new_dir = tmp_path / "new_artifacts"
        quality_gates.ARTIFACTS_DIR = new_dir

        try:
            assert not new_dir.exists()

            report = generate_report(sample_results)
            write_artifacts(report)

            assert new_dir.exists()
            assert (new_dir / "quality_gates_run.json").exists()
        finally:
            quality_gates.ARTIFACTS_DIR = original_dir


# --- GATES Configuration Tests ---


class TestGatesConfiguration:
    """Tests for GATES configuration."""

    def test_gates_not_empty(self) -> None:
        """Test that GATES list is not empty."""
        assert len(GATES) > 0

    def test_all_gates_have_name(self) -> None:
        """Test that all gates have a name."""
        for gate in GATES:
            assert gate.name
            assert isinstance(gate.name, str)

    def test_all_gates_have_description(self) -> None:
        """Test that all gates have a description."""
        for gate in GATES:
            assert gate.description
            assert isinstance(gate.description, str)

    def test_all_gates_have_command(self) -> None:
        """Test that all gates have a command."""
        for gate in GATES:
            assert gate.command
            assert isinstance(gate.command, list)
            assert len(gate.command) > 0

    def test_gates_unique_names(self) -> None:
        """Test that all gate names are unique."""
        names = [g.name for g in GATES]
        assert len(names) == len(set(names))

    def test_required_gates_exist(self) -> None:
        """Test that key required gates exist."""
        names = {g.name for g in GATES}
        required = {"rules", "lint", "types", "tests"}
        assert required.issubset(names)

    def test_security_gate_has_markers(self) -> None:
        """Test that security gate has test markers."""
        security_gate = next((g for g in GATES if g.name == "security"), None)
        assert security_gate is not None
        assert len(security_gate.test_markers) > 0

    def test_privacy_gate_has_markers(self) -> None:
        """Test that privacy gate has test markers."""
        privacy_gate = next((g for g in GATES if g.name == "privacy"), None)
        assert privacy_gate is not None
        assert len(privacy_gate.test_markers) > 0

    def test_reliability_gate_has_markers(self) -> None:
        """Test that reliability gate has test markers."""
        reliability_gate = next((g for g in GATES if g.name == "reliability"), None)
        assert reliability_gate is not None
        assert len(reliability_gate.test_markers) > 0


# --- Integration Tests ---


class TestQualityGatesIntegration:
    """Integration tests for quality gates."""

    @patch("quality_gates.subprocess.run")
    def test_full_run_cycle(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test full cycle: run gates -> generate report -> write artifacts."""
        import quality_gates

        original_dir = quality_gates.ARTIFACTS_DIR
        quality_gates.ARTIFACTS_DIR = tmp_path

        try:
            # Mock all gate runs to pass
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

            # Run gates
            results = run_all_gates()

            # Generate report
            report = generate_report(results)

            # Write artifacts
            write_artifacts(report)

            # Verify
            json_path = tmp_path / "quality_gates_run.json"
            assert json_path.exists()

            with open(json_path) as f:
                data = json.load(f)

            assert data["overall_status"] == "pass"
            assert data["total_gates"] == len(GATES)
        finally:
            quality_gates.ARTIFACTS_DIR = original_dir

    @patch("quality_gates.subprocess.run")
    def test_partial_run_with_skip(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test partial run with some gates skipped."""
        import quality_gates

        original_dir = quality_gates.ARTIFACTS_DIR
        quality_gates.ARTIFACTS_DIR = tmp_path

        try:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

            # Run with skips
            results = run_all_gates(skip_gates=["lint", "format", "types"])
            report = generate_report(results)
            write_artifacts(report)

            with open(tmp_path / "quality_gates_run.json") as f:
                data = json.load(f)

            assert data["skipped_gates"] == 3
        finally:
            quality_gates.ARTIFACTS_DIR = original_dir
