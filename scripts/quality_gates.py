#!/usr/bin/env python3
"""
Quality Gates Runner (T-0003).

Runs all quality gates and generates evidence artifacts.

Spec refs: QG, R1, TA-0101
Test assertions:
- TA-0101: Gates produce valid JSON artifacts

Gates:
1. Rules gate: rules.yaml schema validation
2. Lint gate: ruff linting
3. Type gate: mypy type checking
4. Test gate: pytest tests
5. Security gate: security-related tests
6. Privacy gate: analytics schema enforcement
7. Reliability gate: scheduler + DST tests
8. Regression gate: R1-R6 invariants
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --- Configuration ---

ARTIFACTS_DIR = Path("artifacts")
PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class GateConfig:
    """Configuration for a quality gate."""

    name: str
    description: str
    command: list[str]
    required: bool = True
    timeout_seconds: int = 300
    test_markers: list[str] = field(default_factory=list)


# Gate definitions
GATES: list[GateConfig] = [
    GateConfig(
        name="rules",
        description="Rules schema validation",
        command=["python", "-m", "pytest", "tests/unit/test_rules.py", "-v", "-q"],
    ),
    GateConfig(
        name="lint",
        description="Code linting (ruff)",
        command=["python", "-m", "ruff", "check", "."],
    ),
    GateConfig(
        name="format",
        description="Code formatting check (ruff)",
        command=["python", "-m", "ruff", "format", "--check", "."],
        required=False,  # Warning only
    ),
    GateConfig(
        name="types",
        description="Type checking (mypy)",
        command=["python", "-m", "mypy", "src", "--ignore-missing-imports"],
    ),
    GateConfig(
        name="tests",
        description="All tests (pytest)",
        command=[
            "python",
            "-m",
            "pytest",
            "tests/",
            "-q",
            "--json-report",
            f"--json-report-file={ARTIFACTS_DIR / 'pytest-report.json'}",
        ],
        timeout_seconds=600,
    ),
    GateConfig(
        name="security",
        description="Security tests (XSS, uploads, redirects)",
        command=[
            "python",
            "-m",
            "pytest",
            "tests/",
            "-k",
            "sanitiz or xss or redirect or upload or forbidden",
            "-v",
            "-q",
        ],
        test_markers=["TA-0021", "TA-0022", "TA-0043", "TA-0044", "TA-0045"],
    ),
    GateConfig(
        name="privacy",
        description="Privacy tests (PII prevention)",
        command=[
            "python",
            "-m",
            "pytest",
            "tests/",
            "-k",
            "pii or forbidden_field or privacy",
            "-v",
            "-q",
        ],
        test_markers=["TA-0034", "TA-0035"],
    ),
    GateConfig(
        name="reliability",
        description="Reliability tests (scheduler, DST)",
        command=[
            "python",
            "-m",
            "pytest",
            "tests/",
            "-k",
            "schedul or idempoten or dst or timezone",
            "-v",
            "-q",
        ],
        test_markers=["TA-0027", "TA-0028", "TA-0029", "TA-0030"],
    ),
]


# --- Result Types ---


@dataclass
class GateResult:
    """Result from running a gate."""

    name: str
    status: str  # "pass" | "fail" | "skip" | "warn"
    exit_code: int
    duration_seconds: float
    stdout: str
    stderr: str
    command: list[str]
    required: bool


@dataclass
class GatesReport:
    """Full quality gates report."""

    timestamp_utc: str
    overall_status: str  # "pass" | "fail"
    total_gates: int
    passed_gates: int
    failed_gates: int
    warned_gates: int
    skipped_gates: int
    gates: list[dict[str, Any]]
    summary: str


# --- Gate Runner ---


def run_gate(config: GateConfig) -> GateResult:
    """Run a single quality gate."""
    import time

    print(f"[{config.name}] {config.description}...", end="", flush=True)

    start_time = time.time()

    try:
        result = subprocess.run(
            config.command,
            capture_output=True,
            text=True,
            timeout=config.timeout_seconds,
            cwd=PROJECT_ROOT,
        )
        duration = time.time() - start_time

        if result.returncode == 0:
            status = "pass"
            print(f" PASS ({duration:.1f}s)")
        elif not config.required:
            status = "warn"
            print(f" WARN ({duration:.1f}s)")
        else:
            status = "fail"
            print(f" FAIL ({duration:.1f}s)")

        return GateResult(
            name=config.name,
            status=status,
            exit_code=result.returncode,
            duration_seconds=duration,
            stdout=result.stdout,
            stderr=result.stderr,
            command=config.command,
            required=config.required,
        )

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f" TIMEOUT ({duration:.1f}s)")
        return GateResult(
            name=config.name,
            status="fail",
            exit_code=-1,
            duration_seconds=duration,
            stdout="",
            stderr=f"Timeout after {config.timeout_seconds}s",
            command=config.command,
            required=config.required,
        )

    except Exception as e:
        duration = time.time() - start_time
        print(f" ERROR ({duration:.1f}s)")
        return GateResult(
            name=config.name,
            status="fail",
            exit_code=-1,
            duration_seconds=duration,
            stdout="",
            stderr=str(e),
            command=config.command,
            required=config.required,
        )


def run_all_gates(
    gates: list[GateConfig] | None = None,
    skip_gates: list[str] | None = None,
) -> list[GateResult]:
    """Run all configured gates."""
    gates = gates or GATES
    skip_gates = skip_gates or []

    results = []
    for config in gates:
        if config.name in skip_gates:
            results.append(
                GateResult(
                    name=config.name,
                    status="skip",
                    exit_code=0,
                    duration_seconds=0,
                    stdout="",
                    stderr="Skipped by user",
                    command=config.command,
                    required=config.required,
                )
            )
            print(f"[{config.name}] SKIPPED")
        else:
            results.append(run_gate(config))

    return results


# --- Report Generation ---


def generate_report(results: list[GateResult]) -> GatesReport:
    """Generate gates report from results."""
    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")
    warned = sum(1 for r in results if r.status == "warn")
    skipped = sum(1 for r in results if r.status == "skip")

    # Overall status: fail if any required gate failed
    required_failures = [r for r in results if r.status == "fail" and r.required]
    overall_status = "fail" if required_failures else "pass"

    # Generate summary
    summary_lines = [
        "# Quality Gates Summary",
        "",
        f"**Status**: {overall_status.upper()}",
        f"**Timestamp**: {datetime.datetime.now(datetime.UTC).isoformat()}",
        "",
        "## Results",
        "",
        "| Gate | Status | Duration | Required |",
        "|------|--------|----------|----------|",
    ]

    for r in results:
        status_emoji = {"pass": "✅", "fail": "❌", "warn": "⚠️", "skip": "⏭️"}.get(r.status, "?")
        required_str = "Yes" if r.required else "No"
        summary_lines.append(
            f"| {r.name} | {status_emoji} {r.status.upper()} "
            f"| {r.duration_seconds:.1f}s | {required_str} |"
        )

    summary_lines.extend(
        [
            "",
            "## Statistics",
            "",
            f"- Total: {len(results)}",
            f"- Passed: {passed}",
            f"- Failed: {failed}",
            f"- Warnings: {warned}",
            f"- Skipped: {skipped}",
        ]
    )

    if required_failures:
        summary_lines.extend(
            [
                "",
                "## Failures",
                "",
            ]
        )
        for r in required_failures:
            summary_lines.extend(
                [
                    f"### {r.name}",
                    "",
                    f"Command: `{' '.join(r.command)}`",
                    "",
                    "```",
                    r.stderr or r.stdout or "No output",
                    "```",
                    "",
                ]
            )

    return GatesReport(
        timestamp_utc=datetime.datetime.now(datetime.UTC).isoformat(),
        overall_status=overall_status,
        total_gates=len(results),
        passed_gates=passed,
        failed_gates=failed,
        warned_gates=warned,
        skipped_gates=skipped,
        gates=[
            {
                "name": r.name,
                "status": r.status,
                "exit_code": r.exit_code,
                "duration_seconds": r.duration_seconds,
                "required": r.required,
                "command": r.command,
            }
            for r in results
        ],
        summary="\n".join(summary_lines),
    )


def write_artifacts(report: GatesReport) -> None:
    """Write report artifacts."""
    ARTIFACTS_DIR.mkdir(exist_ok=True)

    # Write JSON report
    json_path = ARTIFACTS_DIR / "quality_gates_run.json"
    with open(json_path, "w") as f:
        json.dump(
            {
                "timestamp_utc": report.timestamp_utc,
                "overall_status": report.overall_status,
                "total_gates": report.total_gates,
                "passed_gates": report.passed_gates,
                "failed_gates": report.failed_gates,
                "warned_gates": report.warned_gates,
                "skipped_gates": report.skipped_gates,
                "gates": report.gates,
            },
            f,
            indent=2,
        )
    print(f"\nJSON report: {json_path}")

    # Write markdown summary
    md_path = ARTIFACTS_DIR / "quality_gates_summary.md"
    with open(md_path, "w") as f:
        f.write(report.summary)
    print(f"Markdown summary: {md_path}")


# --- CLI ---


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run quality gates and generate evidence artifacts."
    )
    parser.add_argument(
        "--skip",
        nargs="*",
        default=[],
        help="Gates to skip (e.g., --skip lint format)",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        help="Only run specified gates (e.g., --only tests)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available gates and exit",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ARTIFACTS_DIR / "quality_gates_run.json",
        help="Output path for JSON report",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    print("=" * 60)
    print("Little Research Lab: Quality Gates Runner")
    print("=" * 60)
    print()

    if args.list:
        print("Available gates:")
        for gate in GATES:
            req = "required" if gate.required else "optional"
            print(f"  - {gate.name}: {gate.description} ({req})")
        return 0

    # Determine which gates to run
    gates_to_run = GATES
    if args.only:
        gates_to_run = [g for g in GATES if g.name in args.only]
        if not gates_to_run:
            print(f"Error: No gates found matching: {args.only}")
            return 1

    # Run gates
    results = run_all_gates(gates_to_run, skip_gates=args.skip)

    # Generate and write report
    report = generate_report(results)
    write_artifacts(report)

    # Print final status
    print()
    print("=" * 60)
    if report.overall_status == "pass":
        print("SUCCESS: All required quality gates passed.")
        return 0
    else:
        print("FAILURE: One or more required quality gates failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
