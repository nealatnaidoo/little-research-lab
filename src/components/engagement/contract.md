# Engagement Component (C14)

## Purpose
Collects, processes, and aggregates user engagement metrics (time on page, scroll depth) in a privacy-preserving manner using bucketing strategies.

## Inputs
- `CalculateEngagementInput`: Raw session telemetry (time on page, scroll depth).
- `QueryEngagementTotalsInput`: Filters for aggregated total stats.
- `QueryEngagementDistributionInput`: Filters for bucket distribution analysis.
- `QueryTopEngagedContentInput`: Filters for ranking top content.

## Outputs
- `CalculateEngagementOutput`: Processed session data with privacy buckets applied.
- `EngagementTotalsOutput`: Aggregated engagement counts and rates.
- `EngagementDistributionOutput`: Histogram data for engagement metrics.
- `TopEngagedContentOutput`: Ranked list of most engaging content.

## Dependencies (Ports)
- `EngagementRepoPort`: Persistence for session data and aggregation queries.
- `EngagementRulesPort`: Configuration for engagement thresholds and buckets.
- `TimePort`: Configurable time source for consistent testing.

## Invariants
- **I1**: Privacy First - Exact time-on-page and scroll-depth are NEVER stored directly; only buckets.
- **I2**: Engagement logic (time + scroll) is applied consistently across all inputs.
- **I3**: Validation prevents negative times or invalid percentages (>100%).

## Error Semantics
- `EngagementValidationError`: Raised for invalid input data (e.g., negative time).
- `ValueError`: Raised for missing required ports in query operations.

## Tests
- `tests/test_unit.py`: Verifies bucketing logic, thresholds, and proper input validation.
- `tests/test_integration.py`: Verifies repository storage and aggregation queries.

## Evidence
- `contracts.md`: This file.
- `component.py`: Functional core implementation with `run()` entry point.
- `models.py`: Pydantic models for inputs/outputs.
- `ports.py`: Abstract base classes for dependencies.
