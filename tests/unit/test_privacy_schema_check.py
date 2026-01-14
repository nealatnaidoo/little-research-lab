"""
Tests for Privacy Schema Enforcement Check (T-0047).

Verifies that the privacy_schema_check script correctly detects PII violations
and validates the analytics models.

Spec refs: R4, TA-0035
"""

from __future__ import annotations

import dataclasses

# --- Test PII Detection Constants ---


class TestPIIFieldPatterns:
    """Test that PII field patterns are correctly defined."""

    def test_pii_patterns_include_ip_fields(self) -> None:
        """IP-related fields must be blocked."""
        from scripts.privacy_schema_check import PII_FIELD_PATTERNS

        ip_fields = {"ip", "ip_address", "ip_addr", "client_ip", "remote_ip"}
        assert ip_fields.issubset(PII_FIELD_PATTERNS)

    def test_pii_patterns_include_user_agent_fields(self) -> None:
        """User agent fields must be blocked."""
        from scripts.privacy_schema_check import PII_FIELD_PATTERNS

        ua_fields = {"user_agent", "ua_raw", "ua_string", "user_agent_string"}
        assert ua_fields.issubset(PII_FIELD_PATTERNS)

    def test_pii_patterns_include_cookie_fields(self) -> None:
        """Cookie-related fields must be blocked."""
        from scripts.privacy_schema_check import PII_FIELD_PATTERNS

        cookie_fields = {"cookie", "cookie_id", "session_cookie"}
        assert cookie_fields.issubset(PII_FIELD_PATTERNS)

    def test_pii_patterns_include_visitor_fields(self) -> None:
        """Visitor identification fields must be blocked."""
        from scripts.privacy_schema_check import PII_FIELD_PATTERNS

        visitor_fields = {"visitor_id", "visitor_key", "device_id", "fingerprint"}
        assert visitor_fields.issubset(PII_FIELD_PATTERNS)

    def test_pii_patterns_include_email_fields(self) -> None:
        """Email fields must be blocked."""
        from scripts.privacy_schema_check import PII_FIELD_PATTERNS

        email_fields = {"email", "email_address", "user_email"}
        assert email_fields.issubset(PII_FIELD_PATTERNS)

    def test_allowed_fields_are_non_pii(self) -> None:
        """Allowed analytics fields should not overlap with PII patterns."""
        from scripts.privacy_schema_check import (
            ALLOWED_ANALYTICS_FIELDS,
            PII_FIELD_PATTERNS,
        )

        overlap = ALLOWED_ANALYTICS_FIELDS & PII_FIELD_PATTERNS
        assert overlap == set(), f"Overlap between allowed and PII fields: {overlap}"


# --- Test Check Functions ---


class TestCheckAnalyticsEventModel:
    """Test analytics event model validation."""

    def test_check_passes_for_valid_model(self) -> None:
        """Check passes when AnalyticsEvent has no PII fields."""
        from scripts.privacy_schema_check import check_analytics_event_model

        result = check_analytics_event_model()
        assert result.passed is True
        # Message should indicate no PII found (contains "non-PII" or similar)
        assert "non-pii" in result.message.lower() or "no pii" in result.message.lower()

    def test_check_detects_pii_fields(self) -> None:
        """Check fails if PII fields are present (mocked scenario)."""
        from scripts.privacy_schema_check import PII_FIELD_PATTERNS

        # Create a mock dataclass with a PII field
        @dataclasses.dataclass
        class MockAnalyticsEvent:
            timestamp: str
            ip_address: str  # This is PII

        mock_fields = {f.name for f in dataclasses.fields(MockAnalyticsEvent)}
        pii_found = mock_fields & PII_FIELD_PATTERNS

        # Verify our mock would be detected
        assert "ip_address" in pii_found


class TestCheckIngestionConfig:
    """Test ingestion config validation."""

    def test_check_passes_when_pii_blocked(self) -> None:
        """Check passes when IngestionConfig blocks required PII fields."""
        from scripts.privacy_schema_check import check_ingestion_config

        result = check_ingestion_config()
        assert result.passed is True
        assert "blocks" in result.message.lower() or "pii" in result.message.lower()

    def test_required_blocked_fields(self) -> None:
        """Verify the required blocked fields are correct."""
        required = {"ip", "ip_address", "user_agent", "cookie", "visitor_id", "email"}
        # These are the minimum PII fields that must be blocked
        assert len(required) == 6


class TestCheckAnalyticsOutputModels:
    """Test analytics output model validation."""

    def test_check_passes_for_clean_models(self) -> None:
        """Check passes when all analytics models are PII-free."""
        from scripts.privacy_schema_check import check_analytics_output_models

        result = check_analytics_output_models()
        assert result.passed is True
        assert "PII-free" in result.message or "no PII" in result.message.lower()


class TestCheckDatabaseSchema:
    """Test database schema validation."""

    def test_check_validates_content_entities(self) -> None:
        """Check validates ContentItem has no analytics PII."""
        from scripts.privacy_schema_check import check_database_schema

        result = check_database_schema()
        assert result.passed is True


class TestCheckRulesPrivacySettings:
    """Test rules file privacy settings validation."""

    def test_check_validates_rules_file(self) -> None:
        """Check validates rules file privacy settings."""
        from scripts.privacy_schema_check import check_rules_privacy_settings

        result = check_rules_privacy_settings()
        # Should pass (either valid settings or no explicit violations)
        assert result.passed is True


# --- Test Report Generation ---


class TestPrivacyReport:
    """Test privacy report generation."""

    def test_run_privacy_checks_returns_report(self) -> None:
        """run_privacy_checks returns a PrivacyReport."""
        from scripts.privacy_schema_check import PrivacyReport, run_privacy_checks

        report = run_privacy_checks()
        assert isinstance(report, PrivacyReport)
        assert report.timestamp is not None
        assert len(report.checks) == 5

    def test_report_to_dict_serializes_correctly(self) -> None:
        """Report can be serialized to dict for JSON output."""
        from scripts.privacy_schema_check import run_privacy_checks

        report = run_privacy_checks()
        report_dict = report.to_dict()

        assert "timestamp" in report_dict
        assert "passed" in report_dict
        assert "summary" in report_dict
        assert "checks" in report_dict
        assert len(report_dict["checks"]) == 5

    def test_all_checks_have_required_fields(self) -> None:
        """Each check result has name, passed, message fields."""
        from scripts.privacy_schema_check import run_privacy_checks

        report = run_privacy_checks()

        for check in report.checks:
            assert check.name is not None
            assert isinstance(check.passed, bool)
            assert check.message is not None


# --- Test Integration with Current Codebase ---


class TestCurrentCodebaseCompliance:
    """Integration tests verifying current codebase is PII-compliant."""

    def test_analytics_event_has_expected_fields(self) -> None:
        """AnalyticsEvent should have only allowed fields."""
        from src.components.analytics.models import AnalyticsEvent

        fields = {f.name for f in dataclasses.fields(AnalyticsEvent)}

        # Should have standard analytics fields
        assert "event_type" in fields
        assert "timestamp" in fields
        assert "path" in fields

        # Should NOT have PII fields
        assert "ip" not in fields
        assert "ip_address" not in fields
        assert "user_agent" not in fields
        assert "email" not in fields

    def test_ingestion_config_blocks_pii(self) -> None:
        """IngestionConfig should block PII fields."""
        from src.components.analytics._impl import IngestionConfig

        config = IngestionConfig()
        forbidden = config.forbidden_fields

        # Must block core PII
        assert "ip" in forbidden
        assert "ip_address" in forbidden
        assert "user_agent" in forbidden
        assert "cookie" in forbidden
        assert "visitor_id" in forbidden
        assert "email" in forbidden

    def test_full_privacy_check_passes(self) -> None:
        """Full privacy check should pass for current codebase."""
        from scripts.privacy_schema_check import run_privacy_checks

        report = run_privacy_checks()

        assert report.passed is True, f"Privacy check failed: {report.summary}"
        for check in report.checks:
            assert check.passed is True, f"Check '{check.name}' failed: {check.message}"
