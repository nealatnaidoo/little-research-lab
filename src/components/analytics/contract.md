## COMPONENT_ID
C7-analytics

## PURPOSE
Ingest, deduplicate, and aggregate analytics events with privacy enforcement.
Provides dashboard queries and time-bucketed aggregation.

## INPUTS
- `IngestEventInput`: Ingest raw analytics event
- `QueryTotalsInput`: Query aggregated totals
- `QueryTimeseriesInput`: Query time-bucketed data
- `QueryTopContentInput`: Query top content by views

## OUTPUTS
- `IngestOutput`: Ingestion result (accepted/rejected)
- `TotalsOutput`: Aggregated totals
- `TimeseriesOutput`: Time-bucketed data points
- `TopContentOutput`: Ranked content list

## DEPENDENCIES (PORTS)
- `AnalyticsRepoPort`: Database access for events/aggregates
- `DedupePort`: Deduplication logic
- `RulesPort`: Analytics rules (modes, ingestion, aggregation, privacy)

## SIDE EFFECTS
- Database write for events and aggregates
- Deduplication state updates

## INVARIANTS
- I1: No PII stored (IP, user agent, cookies, email) - HV2
- I2: Forbidden fields rejected on ingest
- I3: Bot traffic classified and tracked separately
- I4: Events deduplicated within time window
- I5: Aggregates rolled up by minute/hour/day

## ERROR SEMANTICS
- Silently drops forbidden fields (privacy)
- Returns rejection for invalid events
- Graceful degradation on storage errors

## TESTS
- `tests/unit/test_analytics_*.py`: TA-0040, TA-0041, TA-0042 (tests)
  - Privacy enforcement (HV2)
  - Event ingestion and deduplication
  - Aggregation queries

## EVIDENCE
- `artifacts/pytest-analytics-*.json`
