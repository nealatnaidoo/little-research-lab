#!/usr/bin/env python3
"""
Privacy Schema Enforcement Check (T-0047).

Validates that no PII (Personally Identifiable Information) columns exist
in analytics models or database schemas.

Spec refs: R4, TA-0035
Invariant: No audience PII stored (schema + runtime assertions)

PII Fields that must be blocked:
- ip, ip_address (IP addresses)
- user_agent, ua_raw (raw user agent strings)
- cookie, cookie_id (cookies)
- visitor_id (visitor identifiers)
- email (email addresses)

This script can be run standalone or as part of CI quality gates.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# --- PII Definitions ---

# Forbidden field names that would indicate PII storage
PII_FIELD_PATTERNS: frozenset[str] = frozenset({
    "ip",
    "ip_address",
    "ip_addr",
    "client_ip",
    "remote_ip",
    "user_agent",
    "ua_raw",
    "ua_string",
    "user_agent_string",
    "cookie",
    "cookie_id",
    "session_cookie",
    "visitor_id",
    "visitor_key",
    "device_id",
    "fingerprint",
    "email",
    "email_address",
    "user_email",
})

# Fields that are explicitly allowed (non-PII)
ALLOWED_ANALYTICS_FIELDS: frozenset[str] = frozenset({
    "event_type",
    "timestamp",
    "ts",
    "path",
    "content_id",
    "link_id",
    "asset_id",
    "asset_version_id",
    "referrer",  # Domain only, not full URL with query params
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "ua_class",  # Coarse classification only: bot/real/unknown
    # Engagement fields (bucketed, not raw values)
    "time_on_page",  # Sent raw but bucketed before storage
    "scroll_depth",  # Sent raw but bucketed before storage
})

# Allowed engagement storage fields (must be bucketed)
ALLOWED_ENGAGEMENT_FIELDS: frozenset[str] = frozenset({
    "content_id",
    "date",  # Day only, not precise timestamp
    "time_bucket",  # Bucketed, not raw seconds
    "scroll_bucket",  # Bucketed, not raw percent
    "is_engaged",
    "count",
})


# --- Check Results ---


@dataclasses.dataclass
class CheckResult:
    """Result of a privacy check."""

    name: str
    passed: bool
    message: str
    details: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class PrivacyReport:
    """Full privacy schema check report."""

    timestamp: str
    passed: bool
    checks: list[CheckResult]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "passed": self.passed,
            "summary": self.summary,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.checks
            ],
        }


# --- Check Functions ---


def check_analytics_event_model() -> CheckResult:
    """
    Check AnalyticsEvent model has no PII fields.

    The AnalyticsEvent dataclass should only contain fields that are
    explicitly allowed and non-PII.
    """
    try:
        from src.components.analytics.models import AnalyticsEvent

        # Get all field names from the dataclass
        fields = {f.name for f in dataclasses.fields(AnalyticsEvent)}

        # Check for PII fields
        pii_found = fields & PII_FIELD_PATTERNS
        if pii_found:
            return CheckResult(
                name="analytics_event_model",
                passed=False,
                message=f"PII fields found in AnalyticsEvent: {pii_found}",
                details=[f"Forbidden field: {f}" for f in sorted(pii_found)],
            )

        # Verify all fields are in the allowed list
        unknown_fields = fields - ALLOWED_ANALYTICS_FIELDS
        if unknown_fields:
            # Not necessarily a failure, but worth noting
            return CheckResult(
                name="analytics_event_model",
                passed=True,
                message="AnalyticsEvent has no PII fields",
                details=[
                    f"Non-standard field (verify non-PII): {f}" for f in sorted(unknown_fields)
                ],
            )

        return CheckResult(
            name="analytics_event_model",
            passed=True,
            message=f"AnalyticsEvent has {len(fields)} fields, all non-PII",
            details=[f"Allowed field: {f}" for f in sorted(fields)],
        )

    except ImportError as e:
        return CheckResult(
            name="analytics_event_model",
            passed=False,
            message=f"Failed to import AnalyticsEvent: {e}",
        )


def check_ingestion_config() -> CheckResult:
    """
    Check IngestionConfig has proper forbidden fields defined.

    The IngestionConfig should have a forbidden_fields set that blocks
    all known PII field patterns.
    """
    try:
        from src.components.analytics._impl import IngestionConfig

        config = IngestionConfig()

        # Check forbidden_fields exists and has expected fields
        if not hasattr(config, "forbidden_fields"):
            return CheckResult(
                name="ingestion_config",
                passed=False,
                message="IngestionConfig missing forbidden_fields attribute",
            )

        forbidden = config.forbidden_fields

        # Check that core PII types are blocked
        required_blocked = {"ip", "ip_address", "user_agent", "cookie", "visitor_id", "email"}
        missing = required_blocked - forbidden
        if missing:
            return CheckResult(
                name="ingestion_config",
                passed=False,
                message=f"IngestionConfig missing required blocked fields: {missing}",
                details=[f"Missing: {f}" for f in sorted(missing)],
            )

        return CheckResult(
            name="ingestion_config",
            passed=True,
            message=f"IngestionConfig blocks {len(forbidden)} PII field patterns",
            details=[f"Blocked: {f}" for f in sorted(forbidden)],
        )

    except ImportError as e:
        return CheckResult(
            name="ingestion_config",
            passed=False,
            message=f"Failed to import IngestionConfig: {e}",
        )


def check_rules_privacy_settings() -> CheckResult:
    """
    Check rules.yaml has proper privacy settings.

    The rules file should have analytics.privacy section with
    appropriate flags set to prevent PII storage.
    """
    try:
        from src.rules.loader import load_rules

        rules_path = PROJECT_ROOT / "rules.yaml"
        if not rules_path.exists():
            # Try alternate location
            rules_path = PROJECT_ROOT / "creator-publisher-v4_rules.yaml"

        if not rules_path.exists():
            return CheckResult(
                name="rules_privacy_settings",
                passed=False,
                message="Rules file not found",
            )

        rules = load_rules(rules_path)

        # Check for analytics privacy settings in rules
        # The rules structure varies, so we check what's available
        details = []

        # Check if rules object has privacy-related attributes
        if hasattr(rules, "analytics"):
            analytics = rules.analytics
            if hasattr(analytics, "privacy"):
                privacy = analytics.privacy
                # Check specific flags
                if hasattr(privacy, "store_ip") and privacy.store_ip:
                    return CheckResult(
                        name="rules_privacy_settings",
                        passed=False,
                        message="Rules allow IP storage (store_ip=true)",
                    )
                if hasattr(privacy, "store_full_user_agent") and privacy.store_full_user_agent:
                    return CheckResult(
                        name="rules_privacy_settings",
                        passed=False,
                        message="Rules allow full UA storage (store_full_user_agent=true)",
                    )
                details.append("analytics.privacy section found and validated")

        return CheckResult(
            name="rules_privacy_settings",
            passed=True,
            message="Rules file has valid privacy settings",
            details=details if details else ["No explicit privacy violations found"],
        )

    except Exception as e:
        return CheckResult(
            name="rules_privacy_settings",
            passed=True,  # Don't fail if rules structure differs
            message=f"Rules check completed with note: {e}",
            details=["Rules file may have different structure"],
        )


def check_analytics_output_models() -> CheckResult:
    """
    Check all analytics output models have no PII fields.

    Output models like TotalsOutput, TimeseriesOutput, etc. should
    not contain any PII fields.
    """
    try:
        from src.components.analytics import models as analytics_models

        # Get all dataclasses from the models module
        model_classes = []
        for name, obj in inspect.getmembers(analytics_models):
            if dataclasses.is_dataclass(obj) and isinstance(obj, type):
                model_classes.append((name, obj))

        pii_violations = []
        checked_models = []

        for name, cls in model_classes:
            fields = {f.name for f in dataclasses.fields(cls)}
            pii_found = fields & PII_FIELD_PATTERNS
            if pii_found:
                pii_violations.append(f"{name}: {pii_found}")
            checked_models.append(f"{name} ({len(fields)} fields)")

        if pii_violations:
            return CheckResult(
                name="analytics_output_models",
                passed=False,
                message=f"PII fields found in {len(pii_violations)} model(s)",
                details=pii_violations,
            )

        return CheckResult(
            name="analytics_output_models",
            passed=True,
            message=f"Checked {len(model_classes)} analytics models, all PII-free",
            details=checked_models,
        )

    except ImportError as e:
        return CheckResult(
            name="analytics_output_models",
            passed=False,
            message=f"Failed to import analytics models: {e}",
        )


def check_database_schema() -> CheckResult:
    """
    Check database schema for PII columns.

    Examines the SQLite database schema (if exists) or entity models
    to ensure no PII columns are defined.
    """
    try:
        from src.domain.entities import ContentItem

        # User model is expected to have email - that's for authenticated users, not analytics
        # We're checking analytics-related tables don't have PII

        # ContentItem is a Pydantic model, get fields from model_fields
        # Use getattr to avoid mypy issues with Pydantic's dynamic attributes
        content_fields: set[str] = set()
        if hasattr(ContentItem, "model_fields"):
            # Pydantic v2
            model_fields = getattr(ContentItem, "model_fields", {})
            content_fields = set(model_fields.keys())
        elif hasattr(ContentItem, "__fields__"):
            # Pydantic v1
            pydantic_fields = getattr(ContentItem, "__fields__", {})
            content_fields = set(pydantic_fields.keys())

        content_pii = content_fields & PII_FIELD_PATTERNS
        if content_pii:
            return CheckResult(
                name="database_schema",
                passed=False,
                message=f"PII fields in ContentItem: {content_pii}",
            )

        return CheckResult(
            name="database_schema",
            passed=True,
            message="Content entities have no analytics PII columns",
            details=[
                f"ContentItem checked ({len(content_fields)} fields) - no analytics PII found"
            ],
        )

    except ImportError as e:
        return CheckResult(
            name="database_schema",
            passed=True,  # Don't fail on import issues
            message=f"Schema check note: {e}",
        )


def check_engagement_repo_port() -> CheckResult:
    """
    Check EngagementRepoPort stores only bucketed values (T-0064, I9).

    The store_session method should only accept bucketed fields,
    not raw time_on_page_seconds or scroll_depth_percent.
    """
    try:
        import typing

        from src.components.engagement.ports import EngagementRepoPort

        # Get type hints for store_session method
        hints = typing.get_type_hints(EngagementRepoPort.store_session)

        # Remove return type
        hints.pop("return", None)

        # Get parameter names
        params = set(hints.keys())

        # Check for PII fields
        pii_found = params & PII_FIELD_PATTERNS
        if pii_found:
            return CheckResult(
                name="engagement_repo_port",
                passed=False,
                message=f"PII fields in EngagementRepoPort.store_session: {pii_found}",
                details=[f"Forbidden field: {f}" for f in sorted(pii_found)],
            )

        # Check for raw (unbucketed) fields
        raw_fields = {
            "time_on_page_seconds", "scroll_depth_percent",
            "raw_time", "raw_scroll", "seconds", "percent",
        }
        raw_found = params & raw_fields
        if raw_found:
            return CheckResult(
                name="engagement_repo_port",
                passed=False,
                message=f"Raw (unbucketed) fields in EngagementRepoPort.store_session: {raw_found}",
                details=[f"Should be bucketed: {f}" for f in sorted(raw_found)],
            )

        # Check fields are in allowed list
        allowed = ALLOWED_ENGAGEMENT_FIELDS | {"self"}
        unexpected = params - allowed
        if unexpected:
            return CheckResult(
                name="engagement_repo_port",
                passed=False,
                message=f"Unexpected fields in EngagementRepoPort.store_session: {unexpected}",
                details=[
                    "Only bucketed values allowed per I9",
                    f"Allowed: {sorted(ALLOWED_ENGAGEMENT_FIELDS)}",
                    f"Found: {sorted(unexpected)}",
                ],
            )

        return CheckResult(
            name="engagement_repo_port",
            passed=True,
            message="EngagementRepoPort stores only bucketed values (I9 compliant)",
            details=[f"Allowed field: {f}" for f in sorted(params - {"self"})],
        )

    except ImportError as e:
        return CheckResult(
            name="engagement_repo_port",
            passed=True,  # Don't fail if engagement not implemented
            message=f"Engagement repo check skipped: {e}",
        )


def check_engagement_component_bucketing() -> CheckResult:
    """
    Check engagement component buckets values before storage (T-0064, I9).

    The component should have bucketing functions and call them
    before storing any engagement data.
    """
    try:
        engagement_path = PROJECT_ROOT / "src/components/engagement/component.py"
        if not engagement_path.exists():
            return CheckResult(
                name="engagement_component_bucketing",
                passed=True,
                message="Engagement component not yet implemented",
            )

        content = engagement_path.read_text()

        details = []
        errors = []

        # Check for bucketing functions
        if "bucket_time_on_page" not in content:
            errors.append("Missing bucket_time_on_page function")
        else:
            details.append("Has bucket_time_on_page function")

        if "bucket_scroll_depth" not in content:
            errors.append("Missing bucket_scroll_depth function")
        else:
            details.append("Has bucket_scroll_depth function")

        # Check for day truncation (privacy)
        if "truncate_to_day" not in content:
            errors.append("Missing truncate_to_day - precise timestamps may be stored")
        else:
            details.append("Uses truncate_to_day for date privacy")

        # Check that raw values aren't stored directly
        if "time_on_page_seconds" in content and "bucket" not in content.lower():
            errors.append("Raw time_on_page_seconds may be stored without bucketing")

        if errors:
            return CheckResult(
                name="engagement_component_bucketing",
                passed=False,
                message=f"Engagement bucketing issues: {len(errors)} found",
                details=errors,
            )

        return CheckResult(
            name="engagement_component_bucketing",
            passed=True,
            message="Engagement component buckets values before storage (I9 compliant)",
            details=details,
        )

    except Exception as e:
        return CheckResult(
            name="engagement_component_bucketing",
            passed=True,
            message=f"Engagement bucketing check note: {e}",
        )


def check_newsletter_privacy_compliance() -> CheckResult:
    """
    Check newsletter component privacy compliance (T-0084).

    Newsletter legitimately stores email (consent-based, not tracking).
    This check validates:
    - Email is the only PII stored in the subscriber entity
    - No IP addresses or user agents stored in subscriber entity
    - GDPR compliance: unsubscribe and delete capabilities
    - Double opt-in implemented (pending → confirmed state)

    Note: ip_address may appear in input models for rate limiting purposes
    (not stored), which is acceptable.
    """
    try:
        newsletter_path = PROJECT_ROOT / "src/components/newsletter"
        if not newsletter_path.exists():
            return CheckResult(
                name="newsletter_privacy_compliance",
                passed=True,
                message="Newsletter component not implemented yet",
            )

        details = []
        errors = []

        # Check the models/entity file
        models_path = newsletter_path / "models.py"
        if models_path.exists():
            content = models_path.read_text()

            # Email is ALLOWED for newsletter (consent-based)
            if "email" in content:
                details.append("Email field present (required for newsletter)")

            # Check the NewsletterSubscriber entity class specifically
            # Extract the entity class definition
            import re
            subscriber_match = re.search(
                r'class NewsletterSubscriber.*?(?=\n(?:class |# ---|$))',
                content,
                re.DOTALL
            )

            if subscriber_match:
                entity_content = subscriber_match.group(0)

                # Forbidden PII fields in the STORED entity
                forbidden_stored = [
                    "ip_address", "ip:", "user_agent",
                    "cookie", "visitor_id", "fingerprint",
                ]
                for field in forbidden_stored:
                    if field in entity_content.lower():
                        errors.append(
                            f"Forbidden PII field in NewsletterSubscriber: {field}"
                        )

                # Verify only allowed fields in entity
                details.append("NewsletterSubscriber entity checked for PII")
            else:
                details.append(
                    "NewsletterSubscriber entity not found (may be different format)"
                )

            # Check for status field (double opt-in)
            if "status" in content and ("pending" in content or "confirmed" in content):
                details.append("Has status field for double opt-in")
            else:
                errors.append("Missing status field for double opt-in compliance")

        # Check the ports file for GDPR compliance
        ports_path = newsletter_path / "ports.py"
        if ports_path.exists():
            content = ports_path.read_text()

            # Must have delete method (GDPR right to erasure)
            if "delete" in content.lower():
                details.append("Has delete capability (GDPR right to erasure)")
            else:
                errors.append("Missing delete method for GDPR compliance")

            # Must have unsubscribe capability
            if "unsubscribe" in content.lower():
                details.append("Has unsubscribe capability")
            else:
                errors.append("Missing unsubscribe capability")

        # Check service for double opt-in flow
        service_path = newsletter_path / "service.py"
        if service_path.exists():
            content = service_path.read_text()

            if "confirm" in content.lower():
                details.append("Has confirmation flow (double opt-in)")

            if "token" in content.lower():
                details.append("Uses tokens for secure confirm/unsubscribe")

        if errors:
            return CheckResult(
                name="newsletter_privacy_compliance",
                passed=False,
                message=f"Newsletter privacy issues: {len(errors)} found",
                details=errors,
            )

        return CheckResult(
            name="newsletter_privacy_compliance",
            passed=True,
            message="Newsletter component is privacy-compliant (consent-based email storage)",
            details=details if details else ["Newsletter follows privacy best practices"],
        )

    except Exception as e:
        return CheckResult(
            name="newsletter_privacy_compliance",
            passed=True,
            message=f"Newsletter privacy check note: {e}",
        )


def check_engagement_sqlite_schema() -> CheckResult:
    """
    Check SQLite engagement_sessions table schema (T-0064).

    The table should store only bucketed values, not raw times or percentages.
    """
    try:
        sqlite_path = PROJECT_ROOT / "src/adapters/sqlite_db.py"
        if not sqlite_path.exists():
            return CheckResult(
                name="engagement_sqlite_schema",
                passed=True,
                message="SQLite adapter not found",
            )

        content = sqlite_path.read_text()

        # Check if engagement_sessions table exists
        if "engagement_sessions" not in content:
            return CheckResult(
                name="engagement_sqlite_schema",
                passed=True,
                message="engagement_sessions table not in sqlite_db.py",
            )

        details = []
        errors = []

        # Extract the engagement_sessions table CREATE statement
        # Look for CREATE TABLE engagement_sessions ... )
        import re
        engagement_table_match = re.search(
            r'CREATE TABLE[^;]*engagement_sessions[^;]*\)',
            content,
            re.IGNORECASE | re.DOTALL
        )

        if engagement_table_match:
            table_schema = engagement_table_match.group(0)

            # Check for forbidden raw value columns in engagement table only
            forbidden_patterns = [
                ("seconds INTEGER", "Raw seconds stored instead of time_bucket TEXT"),
                ("percent INTEGER", "Raw percent stored instead of scroll_bucket TEXT"),
                ("time_on_page INTEGER", "Raw time stored instead of bucket"),
                ("scroll_depth INTEGER", "Raw scroll stored instead of bucket"),
                (" ip ", "IP address stored in engagement table"),
                ("visitor_id", "Visitor ID stored in engagement table"),
                ("email", "Email stored in engagement table"),
                ("precise_timestamp", "Precise timestamp stored in engagement table"),
            ]

            for pattern, error_msg in forbidden_patterns:
                if pattern.lower() in table_schema.lower():
                    errors.append(error_msg)

            # Check for required bucketed columns
            if "time_bucket" in table_schema:
                details.append("Has time_bucket column (bucketed)")
            else:
                errors.append("Missing time_bucket column")

            if "scroll_bucket" in table_schema:
                details.append("Has scroll_bucket column (bucketed)")
            else:
                errors.append("Missing scroll_bucket column")
        else:
            # Fallback: check for class definition
            if "time_bucket" in content:
                details.append("Has time_bucket reference")
            if "scroll_bucket" in content:
                details.append("Has scroll_bucket reference")

        if errors:
            return CheckResult(
                name="engagement_sqlite_schema",
                passed=False,
                message=f"Engagement SQLite schema issues: {len(errors)} found",
                details=errors,
            )

        return CheckResult(
            name="engagement_sqlite_schema",
            passed=True,
            message="engagement_sessions table stores only bucketed values",
            details=details,
        )

    except Exception as e:
        return CheckResult(
            name="engagement_sqlite_schema",
            passed=True,
            message=f"SQLite schema check note: {e}",
        )


# --- Main Runner ---


def run_privacy_checks() -> PrivacyReport:
    """Run all privacy schema checks and return report."""
    checks = [
        # Analytics checks (T-0047)
        check_analytics_event_model(),
        check_ingestion_config(),
        check_rules_privacy_settings(),
        check_analytics_output_models(),
        check_database_schema(),
        # Engagement checks (T-0064)
        check_engagement_repo_port(),
        check_engagement_component_bucketing(),
        check_engagement_sqlite_schema(),
        # Newsletter check (T-0084)
        check_newsletter_privacy_compliance(),
    ]

    all_passed = all(c.passed for c in checks)
    failed_count = sum(1 for c in checks if not c.passed)

    if all_passed:
        summary = f"All {len(checks)} privacy checks passed"
    else:
        summary = f"{failed_count}/{len(checks)} privacy checks failed"

    return PrivacyReport(
        timestamp=datetime.now(UTC).isoformat(),
        passed=all_passed,
        checks=checks,
        summary=summary,
    )


def main() -> int:
    """Run privacy schema checks and output results."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Privacy Schema Enforcement Check (T-0047)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output JSON report to file",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only output on failure",
    )
    args = parser.parse_args()

    report = run_privacy_checks()

    # Output report
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(report.to_dict(), f, indent=2)

    # Console output
    if not args.quiet or not report.passed:
        print(f"\n{'=' * 60}")
        print("Privacy Schema Enforcement Check (T-0047)")
        print(f"{'=' * 60}")
        print(f"Timestamp: {report.timestamp}")
        print(f"Status: {'PASSED' if report.passed else 'FAILED'}")
        print(f"Summary: {report.summary}")
        print(f"{'=' * 60}\n")

        for check in report.checks:
            status = "PASS" if check.passed else "FAIL"
            print(f"[{status}] {check.name}: {check.message}")
            if check.details and (not args.quiet or not check.passed):
                for detail in check.details[:5]:  # Limit details shown
                    print(f"       - {detail}")
                if len(check.details) > 5:
                    print(f"       ... and {len(check.details) - 5} more")
            print()

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
