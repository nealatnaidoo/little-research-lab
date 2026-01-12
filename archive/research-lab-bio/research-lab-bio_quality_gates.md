# research-lab-bio_quality_gates.md

## Required commands
- Format/lint: `python -m ruff check .`
- Type check: `python -m mypy src`
- Tests: `python -m pytest -q --maxfail=1 --disable-warnings --json-report --json-report-file=artifacts/pytest-report.json`
- Quality gates runner: `python scripts/run_quality_gates.py`

## Evidence artifacts (must be produced)
- `artifacts/pytest-report.json`
- `artifacts/quality_gates_run.json`

## CI blocking rules
- Any non-zero exit code from lint/typecheck/tests/gates fails CI.
- Missing evidence artifacts fails CI.
- Overrides allowed only by:
  1) recording a decision (D-xxxx) and
  2) updating spec + tasklist + gates accordingly.

## Minimum acceptance thresholds
- All tests passing.
- No “fail-fast” rules violations.
- Security tests for R1–R4 must pass before any deploy-tag is created.
