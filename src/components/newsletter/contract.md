## COMPONENT_ID
C10-newsletter

## PURPOSE
Manage newsletter subscriptions with double opt-in verification and strictly enforcing anti-abuse rules.

## INPUTS
- `SubscribeInput`: Email address to subscribe.
- `ConfirmSubscriptionInput`: Token for confirming subscription.
- `UnsubscribeInput`: Token for unsubscribing.
- `AdminListSubscribersInput`: Filters (status, date range) and pagination for admin listing.
- `AdminDeleteSubscriberInput`: Email to GDPR delete.

## OUTPUTS
- `SubscribeOutput`: Result of subscription request (success/fail).
- `ConfirmSubscriptionOutput`: Result of confirmation (success/fail/already_confirmed).
- `UnsubscribeOutput`: Result of unsubscribe (success/fail).
- `AdminListSubscribersOutput`: Paginated list of subscribers without tokens.
- `AdminNewsletterStatsOutput`: Aggregate counts by status.

## DEPENDENCIES (PORTS)
- `NewsletterRepoPort`: Persistence for subscribers and tokens.
- `EmailPort`: Sending verification and welcome emails.
- `DisposableEmailPort`: Validating email domains.
- `RateLimiterPort`: Preventing abuse of signup endpoints.

## SIDE EFFECTS
- S1: Persists subscriber state to database.
- S2: Sends transactional emails via EmailPort.
- S3: Emits audit logs for GDPR actions.

## INVARIANTS
- I1: Subscribers MUST verify email (double opt-in) before receiving newsletters.
- I2: Unsubscribe tokens must be one-time use or idempotent.
- I3: Disposable email addresses MUST be rejected.
- I4: Signup endpoints MUST be rate-limited by IP.

## ERROR SEMANTICS
- Returns `NewsletterValidationError` or `NewsletterError` list in output objects.
- Does not raise exceptions for expected validation failures.

## TESTS
- `test_unit.py`: Top-level component dispatch and logic.
- `test_rate_limits.py`: Verification of abuse prevention.
- Test Assertions: TA-0074-TA-0087.

## EVIDENCE
- `artifacts/pytest-newsletter-report.json`
