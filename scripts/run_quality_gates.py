#!/usr/bin/env python3
import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

# --- Types ---


class GateResult(TypedDict):
    status: str  # "pass" | "fail"
    exit_code: int
    stdout: str
    stderr: str
    command: list[str]


class GatesReport(TypedDict):
    timestamp_utc: str
    overall_status: str  # "pass" | "fail"
    gates: dict[str, GateResult]


# --- Config ---

ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)

COMMANDS = {
    "lint": ["python3", "-m", "ruff", "check", "."],
    "types": ["python3", "-m", "mypy", "src"],
    "tests": [
        "python3",
        "-m",
        "pytest",
        "-q",
        "--maxfail=1",
        "--disable-warnings",
        "--json-report",
        f"--json-report-file={ARTIFACTS_DIR / 'pytest-report.json'}",
    ],
}

# --- Execution ---


def run_command(name: str, cmd: list[str]) -> GateResult:
    print(f"[{name}] Running: {' '.join(cmd)} ...", end="", flush=True)
    try:
        # Run process, capture output. Text mode for easier string handling.
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # We want to capture failure, not raise exception
        )
        status = "pass" if result.returncode == 0 else "fail"
        print(f" {status.upper()}")
        return {
            "status": status,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": cmd,
        }
    except Exception as e:
        print(" ERROR (Exception)")
        return {"status": "fail", "exit_code": -1, "stdout": "", "stderr": str(e), "command": cmd}


def main() -> None:
    print("=== Little Research Lab: Quality Gates Runner ===")

    results: dict[str, GateResult] = {}
    overall_pass = True

    # Run all gates
    for name, cmd in COMMANDS.items():
        res = run_command(name, cmd)
        results[name] = res
        if res["status"] != "pass":
            overall_pass = False

    # Construct Report
    report: GatesReport = {
        "timestamp_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "overall_status": "pass" if overall_pass else "fail",
        "gates": results,
    }

    # Write Artifact
    report_path = ARTIFACTS_DIR / "quality_gates_run.json"
    try:
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport written to: {report_path}")
    except Exception as e:
        print(f"\nFAILED to write report artifact: {e}")
        sys.exit(2)

    # Exit with code
    if overall_pass:
        print("\nSUCCESS: All quality gates passed.")
        sys.exit(0)
    else:
        print("\nFAILURE: One or more quality gates failed.")
        # Print details of failures
        for name, res in results.items():
            if res["status"] == "fail":
                print(f"\n--- {name} FAILED (exit code {res['exit_code']}) ---")
                if res["stdout"].strip():
                    print("STDOUT:")
                    print(res["stdout"])
                if res["stderr"].strip():
                    print("STDERR:")
                    print(res["stderr"])
        sys.exit(1)


if __name__ == "__main__":
    main()
