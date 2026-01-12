"""
Tests for CI Configuration (T-0004).

Spec refs: QG, TA-0102
Test assertions:
- TA-0102: CI config smoke tests

These tests verify the CI workflow configuration is valid and
contains the expected structure.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# --- Test Fixtures ---


@pytest.fixture
def ci_workflow_path() -> Path:
    """Path to CI workflow file."""
    return Path(__file__).parent.parent.parent / ".github" / "workflows" / "ci.yml"


@pytest.fixture
def ci_config(ci_workflow_path: Path) -> dict:
    """Load and parse CI workflow configuration."""
    assert ci_workflow_path.exists(), f"CI workflow not found: {ci_workflow_path}"
    content = ci_workflow_path.read_text()
    config = yaml.safe_load(content)
    # YAML 1.1 treats "on" as boolean True, normalize it
    if True in config and "on" not in config:
        config["on"] = config.pop(True)
    return config


# --- TA-0102: CI Config Smoke Tests ---


class TestCIConfigExists:
    """Tests that CI configuration exists."""

    def test_workflow_file_exists(self, ci_workflow_path: Path) -> None:
        """TA-0102: CI workflow file exists."""
        assert ci_workflow_path.exists()

    def test_workflow_is_valid_yaml(self, ci_config: dict) -> None:
        """TA-0102: CI workflow is valid YAML."""
        assert ci_config is not None
        assert isinstance(ci_config, dict)


class TestCITriggers:
    """Tests for CI workflow triggers."""

    def test_has_on_section(self, ci_config: dict) -> None:
        """TA-0102: CI config has 'on' trigger section."""
        assert "on" in ci_config

    def test_triggers_on_push_to_main(self, ci_config: dict) -> None:
        """TA-0102: CI triggers on push to main."""
        on_config = ci_config.get("on", {})
        assert "push" in on_config
        push_config = on_config["push"]
        assert "branches" in push_config
        assert "main" in push_config["branches"]

    def test_triggers_on_pull_request_to_main(self, ci_config: dict) -> None:
        """TA-0102: CI triggers on PR to main."""
        on_config = ci_config.get("on", {})
        assert "pull_request" in on_config
        pr_config = on_config["pull_request"]
        assert "branches" in pr_config
        assert "main" in pr_config["branches"]


class TestCIJobs:
    """Tests for CI workflow jobs."""

    def test_has_jobs_section(self, ci_config: dict) -> None:
        """TA-0102: CI config has jobs section."""
        assert "jobs" in ci_config

    def test_has_quality_gates_job(self, ci_config: dict) -> None:
        """TA-0102: CI has quality-gates job."""
        jobs = ci_config.get("jobs", {})
        assert "quality-gates" in jobs

    def test_job_runs_on_ubuntu(self, ci_config: dict) -> None:
        """TA-0102: Quality gates job runs on ubuntu-latest."""
        job = ci_config.get("jobs", {}).get("quality-gates", {})
        assert job.get("runs-on") == "ubuntu-latest"


class TestCISteps:
    """Tests for CI workflow steps."""

    def test_has_checkout_step(self, ci_config: dict) -> None:
        """TA-0102: Job has checkout step."""
        job = ci_config.get("jobs", {}).get("quality-gates", {})
        steps = job.get("steps", [])
        checkout_steps = [s for s in steps if "actions/checkout" in str(s.get("uses", ""))]
        assert len(checkout_steps) >= 1

    def test_has_python_setup_step(self, ci_config: dict) -> None:
        """TA-0102: Job has Python setup step."""
        job = ci_config.get("jobs", {}).get("quality-gates", {})
        steps = job.get("steps", [])
        python_steps = [s for s in steps if "setup-python" in str(s.get("uses", ""))]
        assert len(python_steps) >= 1

    def test_python_version_312(self, ci_config: dict) -> None:
        """TA-0102: Python version is 3.12."""
        job = ci_config.get("jobs", {}).get("quality-gates", {})
        steps = job.get("steps", [])
        python_step = next(
            (s for s in steps if "setup-python" in str(s.get("uses", ""))),
            None,
        )
        assert python_step is not None
        version = python_step.get("with", {}).get("python-version")
        assert version in ("3.12", '"3.12"')

    def test_has_install_dependencies_step(self, ci_config: dict) -> None:
        """TA-0102: Job has dependency installation step."""
        job = ci_config.get("jobs", {}).get("quality-gates", {})
        steps = job.get("steps", [])
        install_steps = [s for s in steps if "Install dependencies" in str(s.get("name", ""))]
        assert len(install_steps) >= 1

    def test_has_quality_gates_step(self, ci_config: dict) -> None:
        """TA-0102: Job has quality gates run step."""
        job = ci_config.get("jobs", {}).get("quality-gates", {})
        steps = job.get("steps", [])
        gate_steps = [s for s in steps if "Quality Gates" in str(s.get("name", ""))]
        assert len(gate_steps) >= 1

    def test_quality_gates_runs_script(self, ci_config: dict) -> None:
        """TA-0102: Quality gates step runs the correct script."""
        job = ci_config.get("jobs", {}).get("quality-gates", {})
        steps = job.get("steps", [])
        gate_step = next(
            (s for s in steps if s.get("name") == "Run Quality Gates"),
            None,
        )
        assert gate_step is not None
        run_cmd = gate_step.get("run", "")
        assert "quality_gates.py" in run_cmd


class TestCIArtifacts:
    """Tests for CI artifact upload."""

    def test_has_artifact_upload_step(self, ci_config: dict) -> None:
        """TA-0102: Job uploads artifacts."""
        job = ci_config.get("jobs", {}).get("quality-gates", {})
        steps = job.get("steps", [])
        artifact_steps = [s for s in steps if "upload-artifact" in str(s.get("uses", ""))]
        assert len(artifact_steps) >= 1

    def test_uploads_json_report(self, ci_config: dict) -> None:
        """TA-0102: Artifacts include JSON report."""
        job = ci_config.get("jobs", {}).get("quality-gates", {})
        steps = job.get("steps", [])
        artifact_step = next(
            (s for s in steps if "upload-artifact" in str(s.get("uses", ""))),
            None,
        )
        assert artifact_step is not None
        path = artifact_step.get("with", {}).get("path", "")
        assert "quality_gates_run.json" in path

    def test_uploads_markdown_summary(self, ci_config: dict) -> None:
        """TA-0102: Artifacts include markdown summary."""
        job = ci_config.get("jobs", {}).get("quality-gates", {})
        steps = job.get("steps", [])
        artifact_step = next(
            (s for s in steps if "upload-artifact" in str(s.get("uses", ""))),
            None,
        )
        assert artifact_step is not None
        path = artifact_step.get("with", {}).get("path", "")
        assert "quality_gates_summary.md" in path


class TestCIPermissions:
    """Tests for CI workflow permissions."""

    def test_has_permissions(self, ci_config: dict) -> None:
        """TA-0102: CI config has permissions section."""
        assert "permissions" in ci_config

    def test_has_pr_write_permission(self, ci_config: dict) -> None:
        """TA-0102: CI has pull-requests write permission for comments."""
        permissions = ci_config.get("permissions", {})
        # Either explicit write or not restricted
        pr_perm = permissions.get("pull-requests")
        assert pr_perm == "write"


class TestCIFailureHandling:
    """Tests for CI failure handling."""

    def test_gates_status_check_exists(self, ci_config: dict) -> None:
        """TA-0102: CI has gates status check step."""
        job = ci_config.get("jobs", {}).get("quality-gates", {})
        steps = job.get("steps", [])
        check_steps = [s for s in steps if "Check Gates Status" in str(s.get("name", ""))]
        assert len(check_steps) >= 1

    def test_gates_step_continues_on_error(self, ci_config: dict) -> None:
        """TA-0102: Quality gates step continues on error for artifact upload."""
        job = ci_config.get("jobs", {}).get("quality-gates", {})
        steps = job.get("steps", [])
        gate_step = next(
            (s for s in steps if s.get("name") == "Run Quality Gates"),
            None,
        )
        assert gate_step is not None
        # Should have continue-on-error to allow artifact upload
        assert gate_step.get("continue-on-error") is True


class TestCIPRComments:
    """Tests for CI PR comment functionality."""

    def test_has_pr_comment_step(self, ci_config: dict) -> None:
        """TA-0102: CI has PR comment step."""
        job = ci_config.get("jobs", {}).get("quality-gates", {})
        steps = job.get("steps", [])
        comment_steps = [s for s in steps if "Post PR Comment" in str(s.get("name", ""))]
        assert len(comment_steps) >= 1

    def test_pr_comment_only_on_pr(self, ci_config: dict) -> None:
        """TA-0102: PR comment only runs on pull requests."""
        job = ci_config.get("jobs", {}).get("quality-gates", {})
        steps = job.get("steps", [])
        comment_step = next(
            (s for s in steps if "Post PR Comment" in str(s.get("name", ""))),
            None,
        )
        assert comment_step is not None
        condition = comment_step.get("if", "")
        assert "pull_request" in condition


# --- Integration Tests ---


class TestCIConfigIntegration:
    """Integration tests for CI configuration."""

    def test_full_workflow_structure(self, ci_config: dict) -> None:
        """TA-0102: Full workflow has expected structure."""
        # Top-level keys
        assert "name" in ci_config
        assert "on" in ci_config
        assert "jobs" in ci_config

        # Job structure
        job = ci_config["jobs"]["quality-gates"]
        assert "runs-on" in job
        assert "steps" in job

        # Step count (should have multiple steps)
        steps = job["steps"]
        assert len(steps) >= 5  # checkout, python, install, gates, artifacts, check

    def test_workflow_name(self, ci_config: dict) -> None:
        """TA-0102: Workflow has correct name."""
        assert ci_config.get("name") == "Quality Gates"
