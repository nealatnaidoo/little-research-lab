# Monetization Component (C11)

## Purpose
Pure functions for content monetization and paywall enforcement. Determines content access based on visitor entitlements and content tiers, calculates preview blocks for restricted content, and filters content server-side to prevent client-side bypass.

## Inputs
- `AccessCheckInput`: Content tier and visitor entitlement for access determination.
- `PreviewBlocksInput`: Content tier and total block count for preview calculation.
- `FilterContentInput`: Content blocks, tier, and entitlement for server-side filtering.

## Outputs
- `AccessCheckOutput`: Access determination with preview block count if restricted.
- `PreviewBlocksOutput`: Calculated preview count, is_limited flag, and hidden blocks count.
- `FilterContentOutput`: Filtered content blocks with visibility metadata.

## Dependencies (Ports)
- `PaymentPort`: External payment/subscription verification (stub for MVP).

## Invariants
- **I10**: Server-side enforcement - All access checks happen server-side; client never sees full content without proper entitlement.
- **R8**: No client-side bypass - Content filtering is applied on the server before transmission.
- **Entitlement Hierarchy**: subscriber > premium > free (higher levels can access all lower tier content).

## Error Semantics
- Invalid tier or entitlement falls back to "free" tier behavior.
- Disabled monetization grants full access to all content.
- Missing config uses default values (monetization disabled).

## Tests
- `tests/test_unit.py`: Verifies access check logic (TA-0093), paywall info generation (TA-0094), preview block calculation (TA-0095), and server-side content filtering (TA-0096).

## Evidence
- `contract.md`: This file.
- `component.py`: Functional core implementation with `run()` entry point.
- `models.py`: Dataclass models for inputs/outputs and entitlement mapping.
- `ports.py`: Protocol definitions for payment integration.
