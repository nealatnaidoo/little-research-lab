## COMPONENT_ID
C0-rules

## PURPOSE
Load and validate the rules.yaml configuration file with fail-fast behavior.
All domain behavior is driven by rules, and invalid rules must halt startup.

## INPUTS
- `LoadRulesInput`: Optional path to rules file
- `ValidateRulesInput`: Rules dictionary for validation only

## OUTPUTS
- `LoadRulesOutput`: Loaded and validated rules dictionary, or errors
- `ValidateRulesOutput`: Validation result with errors list

## DEPENDENCIES (PORTS)
- `FileSystemPort`: Read YAML files from disk
- `EnvironmentPort`: Read environment variables (RULES_PATH)

## SIDE EFFECTS
- File system read (via FileSystemPort)
- Environment variable read (via EnvironmentPort)

## INVARIANTS
- I1: Rules must pass schema validation before use
- I2: `security.deny_by_default` must be true (HV1)
- I3: `security.session.cookie.http_only` must be true (HV1)
- I4: `security.session.cookie.secure` must be true (HV1)
- I5: `analytics.privacy.store_ip` must be false (HV2)
- I6: `analytics.privacy.store_full_user_agent` must be false (HV2)
- I7: `analytics.privacy.store_cookies` must be false (HV2)
- I8: `analytics.privacy.store_visitor_identifiers` must be false (HV2)
- I9: `analytics.ingestion.schema.forbidden_fields` must include PII fields (HV2)

## ERROR SEMANTICS
- Returns errors in output object, does not throw (except for unrecoverable I/O)
- `RulesValidationError` exception available for fail-fast startup pattern
- Empty rules dict returned on load failure

## TESTS
- `tests/unit/test_rules.py`: TA-0100 (26 tests)
  - Schema validation
  - Required field checks
  - Security invariant enforcement
  - Privacy invariant enforcement

## EVIDENCE
- `artifacts/pytest-rules-report.json`
