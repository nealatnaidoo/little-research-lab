## COMPONENT_ID
C12-sharing

## PURPOSE
Generate social sharing URLs with privacy-preserving attribution parameters (UTM).
Ensures all outbound social links have consistent tracking without PII leakage.

## INPUTS
- `GenerateShareUrlInput`: Content slug, platform choice (twitter/linkedin/facebook/natives), base URL.
- `AddUtmParamsInput`: Raw URL + UTM source/medium/campaign intent.

## OUTPUTS
- `GenerateShareUrlOutput`: Formatted platform-specific share intetn URL with encoded params.
- `AddUtmParamsOutput`: URL with appended UTM query parameters.

## DEPENDENCIES (PORTS)
- `SharingRulesPort`: Configuration for enabled platforms and default UTM values.

## SIDE EFFECTS
- None (Pure functional component).

## INVARIANTS
- I1: All generated URLs MUST be absolute (start with http/https).
- I2: UTM parameters override existing query params if collision occurs.
- I3: Native platform returns raw URL; Social platforms return Intent URL.

## ERROR SEMANTICS
- Returns `SharingValidationError` list in output objects.
- Does not raise exceptions for validation failures (returns success=False).

## TESTS
- `test_unit.py`: Top-level component dispatch and logic.
- `test_properties.py`: Fuzzing for URL encoding safety.
- Test Assertions: TA-0070 (Share URLs), TA-0071 (UTM).

## EVIDENCE
- `artifacts/pytest-sharing-report.json`
