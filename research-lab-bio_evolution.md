# research-lab-bio_evolution.md

## Drift governance
- Any discovery that changes scope, security posture, architecture, rules, or testability must be logged as an EV entry.
- Coding must halt on drift triggers until BA artifacts are updated (spec/rules/tasklist/decisions/gates).

## Open entries

(No open entries)

## Resolved entries

### EV-0004: Frontend Migration from Flet to React/Next.js
- **Date**: 2026-01-11
- **Trigger**: Persistent Flet version compatibility issues (WebSocket errors, API changes between 0.28.x versions, DatePicker/TimePicker API instability) blocking reliable UI development.
- **Description**: Flet compiles Python to Flutter/Dart for web via WebSocket rendering. This architecture has proven fragile:
  1. WebSocket "Receive loop error: 'text'" requiring pinned websockets <14.0
  2. `ft.animation.Animation` vs `ft.Animation` API changes
  3. `DatePicker.pick_date()` method doesn't exist in 0.28.x
  4. Small community = limited solutions for edge cases
  5. Testing Flet views is non-trivial (EV-0001)
- **Impact**:
  - Development velocity significantly reduced by debugging Flet compatibility
  - UI cannot achieve "Premium" polish due to Flet limitations
  - Long-term maintainability risk with niche framework
- **Proposed change**:
  1. Migrate frontend from Flet to **React/Next.js**
  2. Convert Python backend to **REST API** (FastAPI) consumed by React
  3. Preserve all domain logic, services, and adapters (clean architecture pays off)
  4. Use existing Flet code as **specification** for React components
  5. Phased migration: API first, then component-by-component UI rebuild
- **Affected artifacts**:
  - `research-lab-bio_spec.md` (tech stack, architecture)
  - `research-lab-bio_decisions.md` (D-0005)
  - `research-lab-bio_tasklist.md` (new migration epic)
  - `README.md` (tech stack badges, setup instructions)
  - `pyproject.toml` (remove flet dependencies, add fastapi)
  - All `src/ui/` and `src/app_shell/` code (to be replaced)
- **Halt required**: Yes - spec update required before coding
- **Resolution**: Resolved - spec, decisions, README, and tasklist updated. Ready for T-0047+ implementation.
- **Links to decisions/tasks**: D-0005, T-0047 through T-0063

### EV-0001: Flet UI Testing Strategy
- **Date**: 2026-01-10
- **Trigger**: Audit revealed lack of automated tests for UI tasks (T-0022 to T-0026), violating System Prompt Rule #5 (Strict TDD).
- **Description**: Testing Flet Views via `pytest` is non-trivial and often brittle. Strict TDD was applied to Domain/Services but not View layers.
- **Impact**: "Done" definition was technically violated. Regression risk in UI wiring (e.g., event handlers).
- **Proposed change**:
  1. Formalize "Service Integration Tests" (testing logic flow) as the mandatory automated gate.
  2. Accept "Manual Verification with Walkthrough Evidence" as sufficient for View Layout/Rendering.
  3. Update `research-lab-bio_coding_agent_system_prompt.md` or Rules to reflect this distinction.
- **Affected artifacts**: System Prompt, Rules, Tasklist ("Done" criteria).
- **Halt required**: No (Remediation via Audit performed).
- **Resolution**: Adopted "Service Integration Tests" + Manual UI Verification as standard.

### EV-0002: Premium UI Gap
- **Date**: 2026-01-10
- **Trigger**: "Web Application Development" prompt requires "Premium Designs" and "Wow" factor. Current implementation is standard Material Design (Functional but Basic).
- **Description**: Focus has been on Architecture/Ports/Logic (Functional Core). UI is utilitarian.
- **Impact**: Product may not meet "Premium" expectation.
- **Proposed change**:
  1. Schedule specific "UX/UI Polish" tasks (after T-0030) to apply custom themes, animations (`ft.AnimatedSwitcher`), and fonts.
  2. Create `src/ui/theme.py` to centralize "Premium" config.
- **Affected artifacts**: Tasklist.
- **Resolution**: Implemented T-0035 (Premium Theme, Layout, Components).

### EV-0001
- **ID**: EV-0001
- **Status**: [RESOLVED]
- **Date Detected**: 2024-01-24
- **Description**: The complexity of service interactions (Publishing, Scheduling, Access Control) requires a dedicated integration test suite beyond unit tests.
- **Impact**: High risk of regression in end-to-end flows.
- **Resolution**: Implemented `tests/integration/test_user_journey.py` covering the full lifecycle.

### EV-0002
- **ID**: EV-0002
- **Status**: [RESOLVED]
- **Date Detected**: 2024-01-24
- **Description**: UI State logic (Theme, Session) lacked unit test coverage.
- **Impact**: Moderate risk of UI breakage.
- **Resolution**: Implemented `tests/unit/test_ui_logic.py`.

### EV-0003: Continuous Type Safety
- **Date**: 2026-01-10
- **Trigger**: Audit found 45+ `mypy` errors after feature completion.
- **Description**: Type checking was deferred until Audit, leading to accumulated debt and logic bugs (e.g. `None` safety).
- **Impact**: Increased remediation cost and potential runtime crashes.
- **Proposed change**:
  1. Enforce `scripts/run_quality_gates.py` execution *after every single task*.
  2. Update "Done" definition to explicitly require clean `mypy` output.
- **Affected artifacts**: Workflow/Process.
- **Resolution**: Adopted strict Quality Gate enforcement for T-0035/T-0036.

### EV-0001 (template)
- Date:
- Trigger:
- Description:
- Impact:
- Proposed change:
- Affected artifacts:
- Halt required: yes/no
- Resolution:
- Links to decisions/tasks:
