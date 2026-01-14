"""
Unit tests for Engagement component.

Spec refs: E14.1, E14.2, E14.3
Test assertions: TA-0058, TA-0059, TA-0060
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest

from ..component import (
    bucket_scroll_depth,
    bucket_time_on_page,
    is_engaged_session,
    run_calculate,
    run_query_distribution,
    run_query_top_engaged_content,
    run_query_totals,
    validate_engagement_input,
)
from ..models import (
    CalculateEngagementInput,
    QueryEngagementDistributionInput,
    QueryEngagementTotalsInput,
    QueryTopEngagedContentInput,
)
from ..ports import EngagementRepoPort, EngagementRulesPort, TimePort


# --- Test Fixtures ---


class FakeTimePort:
    """Fake time port for testing."""

    def __init__(self, fixed_time: datetime | None = None):
        self._now = fixed_time or datetime(2026, 1, 14, 12, 0, 0, tzinfo=timezone.utc)

    def now_utc(self) -> datetime:
        return self._now

    def truncate_to_day(self, dt: datetime) -> datetime:
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)


class FakeEngagementRepo:
    """Fake engagement repo for testing."""

    def __init__(self):
        self.sessions: list[dict[str, Any]] = []

    def store_session(
        self,
        content_id: UUID,
        date: datetime,
        time_bucket: str,
        scroll_bucket: str,
        is_engaged: bool,
    ) -> None:
        self.sessions.append(
            {
                "content_id": content_id,
                "date": date,
                "time_bucket": time_bucket,
                "scroll_bucket": scroll_bucket,
                "is_engaged": is_engaged,
            }
        )

    def get_totals(
        self,
        content_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        engaged_only: bool = False,
    ) -> dict[str, int]:
        filtered = self.sessions
        if content_id:
            filtered = [s for s in filtered if s["content_id"] == content_id]
        total = len(filtered)
        engaged = len([s for s in filtered if s["is_engaged"]])
        return {"total_sessions": total, "engaged_sessions": engaged}

    def get_distribution(
        self,
        distribution_type: str,
        content_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        bucket_key = "time_bucket" if distribution_type == "time" else "scroll_bucket"
        counts: dict[str, int] = {}
        for session in self.sessions:
            bucket = session[bucket_key]
            counts[bucket] = counts.get(bucket, 0) + 1
        return [{"bucket": k, "count": v} for k, v in counts.items()]

    def get_top_engaged_content(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        content_stats: dict[UUID, dict[str, int]] = {}
        for session in self.sessions:
            cid = session["content_id"]
            if cid not in content_stats:
                content_stats[cid] = {"total_sessions": 0, "engaged_sessions": 0}
            content_stats[cid]["total_sessions"] += 1
            if session["is_engaged"]:
                content_stats[cid]["engaged_sessions"] += 1
        result = [
            {"content_id": cid, **stats} for cid, stats in content_stats.items()
        ]
        result.sort(key=lambda x: x["engaged_sessions"], reverse=True)
        return result[:limit]


class FakeEngagementRules:
    """Fake engagement rules for testing."""

    def is_enabled(self) -> bool:
        return True

    def get_min_time_on_page_seconds(self) -> int:
        return 30

    def get_min_scroll_depth_percent(self) -> int:
        return 25

    def get_time_buckets(self) -> tuple[str, ...]:
        return ("0-10s", "10-30s", "30-60s", "60-120s", "120-300s", "300+s")

    def get_scroll_buckets(self) -> tuple[str, ...]:
        return ("0-25%", "25-50%", "50-75%", "75-100%")


# --- TA-0058: Engagement Threshold Tests ---


class TestEngagementThreshold:
    """Tests for TA-0058: Engagement threshold calculation."""

    def test_engaged_meets_both_thresholds(self):
        """Session with 30s+ and 25%+ scroll is engaged."""
        assert is_engaged_session(30, 25) is True
        assert is_engaged_session(60, 50) is True
        assert is_engaged_session(300, 100) is True

    def test_not_engaged_insufficient_time(self):
        """Session with <30s is not engaged even with high scroll."""
        assert is_engaged_session(29, 100) is False
        assert is_engaged_session(10, 75) is False
        assert is_engaged_session(0, 50) is False

    def test_not_engaged_insufficient_scroll(self):
        """Session with <25% scroll is not engaged even with long time."""
        assert is_engaged_session(300, 24) is False
        assert is_engaged_session(60, 10) is False
        assert is_engaged_session(120, 0) is False

    def test_not_engaged_fails_both(self):
        """Session failing both thresholds is not engaged."""
        assert is_engaged_session(10, 10) is False
        assert is_engaged_session(0, 0) is False

    def test_engaged_exactly_at_threshold(self):
        """Session exactly at thresholds is engaged."""
        assert is_engaged_session(30, 25) is True

    def test_custom_thresholds(self):
        """Custom thresholds are respected."""
        # Custom: 60s minimum, 50% scroll minimum
        assert is_engaged_session(60, 50, min_time_seconds=60, min_scroll_percent=50) is True
        assert is_engaged_session(59, 50, min_time_seconds=60, min_scroll_percent=50) is False
        assert is_engaged_session(60, 49, min_time_seconds=60, min_scroll_percent=50) is False


# --- TA-0059: Input Validation Tests ---


class TestInputValidation:
    """Tests for TA-0059: Input validation."""

    def test_valid_input(self):
        """Valid input produces no errors."""
        errors = validate_engagement_input(30, 50)
        assert len(errors) == 0

    def test_negative_time_rejected(self):
        """Negative time on page is rejected."""
        errors = validate_engagement_input(-1, 50)
        assert len(errors) == 1
        assert errors[0].code == "INVALID_TIME"
        assert errors[0].field_name == "time_on_page_seconds"

    def test_excessive_time_rejected(self):
        """Time > 3600s is rejected."""
        errors = validate_engagement_input(3601, 50)
        assert len(errors) == 1
        assert errors[0].code == "INVALID_TIME"

    def test_negative_scroll_rejected(self):
        """Negative scroll depth is rejected."""
        errors = validate_engagement_input(30, -1)
        assert len(errors) == 1
        assert errors[0].code == "INVALID_SCROLL"
        assert errors[0].field_name == "scroll_depth_percent"

    def test_excessive_scroll_rejected(self):
        """Scroll > 100% is rejected."""
        errors = validate_engagement_input(30, 101)
        assert len(errors) == 1
        assert errors[0].code == "INVALID_SCROLL"

    def test_multiple_errors_returned(self):
        """Multiple validation errors are all returned."""
        errors = validate_engagement_input(-1, -1)
        assert len(errors) == 2
        codes = {e.code for e in errors}
        assert "INVALID_TIME" in codes
        assert "INVALID_SCROLL" in codes

    def test_boundary_values_valid(self):
        """Boundary values (0, 100%, 3600s) are valid."""
        assert len(validate_engagement_input(0, 0)) == 0
        assert len(validate_engagement_input(3600, 100)) == 0


# --- TA-0060: Bucketing Tests (Privacy Enforcement) ---


class TestTimeBucketing:
    """Tests for TA-0060: Time bucketing for privacy."""

    def test_time_bucket_0_10(self):
        """Time 0-9s maps to 0-10s bucket."""
        assert bucket_time_on_page(0) == "0-10s"
        assert bucket_time_on_page(5) == "0-10s"
        assert bucket_time_on_page(9.9) == "0-10s"

    def test_time_bucket_10_30(self):
        """Time 10-29s maps to 10-30s bucket."""
        assert bucket_time_on_page(10) == "10-30s"
        assert bucket_time_on_page(20) == "10-30s"
        assert bucket_time_on_page(29.9) == "10-30s"

    def test_time_bucket_30_60(self):
        """Time 30-59s maps to 30-60s bucket."""
        assert bucket_time_on_page(30) == "30-60s"
        assert bucket_time_on_page(45) == "30-60s"
        assert bucket_time_on_page(59.9) == "30-60s"

    def test_time_bucket_60_120(self):
        """Time 60-119s maps to 60-120s bucket."""
        assert bucket_time_on_page(60) == "60-120s"
        assert bucket_time_on_page(90) == "60-120s"
        assert bucket_time_on_page(119.9) == "60-120s"

    def test_time_bucket_120_300(self):
        """Time 120-299s maps to 120-300s bucket."""
        assert bucket_time_on_page(120) == "120-300s"
        assert bucket_time_on_page(200) == "120-300s"
        assert bucket_time_on_page(299.9) == "120-300s"

    def test_time_bucket_300_plus(self):
        """Time 300s+ maps to 300+s bucket."""
        assert bucket_time_on_page(300) == "300+s"
        assert bucket_time_on_page(600) == "300+s"
        assert bucket_time_on_page(3600) == "300+s"


class TestScrollBucketing:
    """Tests for TA-0060: Scroll bucketing for privacy."""

    def test_scroll_bucket_0_25(self):
        """Scroll 0-24% maps to 0-25% bucket."""
        assert bucket_scroll_depth(0) == "0-25%"
        assert bucket_scroll_depth(10) == "0-25%"
        assert bucket_scroll_depth(24.9) == "0-25%"

    def test_scroll_bucket_25_50(self):
        """Scroll 25-49% maps to 25-50% bucket."""
        assert bucket_scroll_depth(25) == "25-50%"
        assert bucket_scroll_depth(35) == "25-50%"
        assert bucket_scroll_depth(49.9) == "25-50%"

    def test_scroll_bucket_50_75(self):
        """Scroll 50-74% maps to 50-75% bucket."""
        assert bucket_scroll_depth(50) == "50-75%"
        assert bucket_scroll_depth(60) == "50-75%"
        assert bucket_scroll_depth(74.9) == "50-75%"

    def test_scroll_bucket_75_100(self):
        """Scroll 75-100% maps to 75-100% bucket."""
        assert bucket_scroll_depth(75) == "75-100%"
        assert bucket_scroll_depth(90) == "75-100%"
        assert bucket_scroll_depth(100) == "75-100%"

    def test_scroll_clamped_to_range(self):
        """Out of range values are clamped."""
        assert bucket_scroll_depth(-10) == "0-25%"
        assert bucket_scroll_depth(150) == "75-100%"


# --- Integration Tests ---


class TestCalculateEngagement:
    """Integration tests for run_calculate."""

    def test_calculate_engaged_session(self):
        """Engaged session is correctly calculated and stored."""
        content_id = uuid4()
        repo = FakeEngagementRepo()
        time_port = FakeTimePort()

        inp = CalculateEngagementInput(
            content_id=content_id,
            time_on_page_seconds=45,  # 30-60s bucket
            scroll_depth_percent=75,
        )

        result = run_calculate(inp, repo=repo, time_port=time_port)

        assert result.success is True
        assert result.is_engaged is True
        assert result.time_bucket == "30-60s"
        assert result.scroll_bucket == "75-100%"
        assert result.session is not None
        assert result.session.is_engaged is True

        # Check stored
        assert len(repo.sessions) == 1
        stored = repo.sessions[0]
        assert stored["content_id"] == content_id
        assert stored["is_engaged"] is True
        assert stored["time_bucket"] == "30-60s"
        assert stored["scroll_bucket"] == "75-100%"

    def test_calculate_not_engaged_session(self):
        """Non-engaged session is correctly calculated."""
        content_id = uuid4()
        repo = FakeEngagementRepo()

        inp = CalculateEngagementInput(
            content_id=content_id,
            time_on_page_seconds=5,  # 0-10s bucket
            scroll_depth_percent=10,
        )

        result = run_calculate(inp, repo=repo)

        assert result.success is True
        assert result.is_engaged is False
        assert result.time_bucket == "0-10s"
        assert result.scroll_bucket == "0-25%"

    def test_calculate_without_repo_no_storage(self):
        """Without repo, session is not stored."""
        inp = CalculateEngagementInput(
            content_id=uuid4(),
            time_on_page_seconds=60,
            scroll_depth_percent=50,
        )

        result = run_calculate(inp)

        assert result.success is True
        assert result.session is not None
        # No way to verify storage without repo - that's the point

    def test_calculate_invalid_input_rejected(self):
        """Invalid input returns error without storage."""
        repo = FakeEngagementRepo()

        inp = CalculateEngagementInput(
            content_id=uuid4(),
            time_on_page_seconds=-1,
            scroll_depth_percent=50,
        )

        result = run_calculate(inp, repo=repo)

        assert result.success is False
        assert len(result.errors) == 1
        assert len(repo.sessions) == 0  # Not stored

    def test_calculate_date_truncated_to_day(self):
        """Timestamp is truncated to day for privacy (TA-0060)."""
        content_id = uuid4()
        repo = FakeEngagementRepo()
        # Time with specific hour/minute/second
        time_port = FakeTimePort(datetime(2026, 1, 14, 15, 30, 45, tzinfo=timezone.utc))

        inp = CalculateEngagementInput(
            content_id=content_id,
            time_on_page_seconds=60,
            scroll_depth_percent=50,
        )

        result = run_calculate(inp, repo=repo, time_port=time_port)

        assert result.success is True
        # Date should be truncated - no time component
        stored_date = repo.sessions[0]["date"]
        assert stored_date.hour == 0
        assert stored_date.minute == 0
        assert stored_date.second == 0


class TestQueryTotals:
    """Tests for run_query_totals (TA-0065)."""

    def test_query_totals_empty(self):
        """Empty repo returns zero totals."""
        repo = FakeEngagementRepo()

        inp = QueryEngagementTotalsInput()
        result = run_query_totals(inp, repo=repo)

        assert result.success is True
        assert result.total_sessions == 0
        assert result.engaged_sessions == 0
        assert result.engagement_rate == 0.0

    def test_query_totals_with_data(self):
        """Totals are correctly calculated."""
        repo = FakeEngagementRepo()
        content_id = uuid4()

        # Add some sessions
        for _ in range(3):
            repo.store_session(content_id, datetime.now(), "30-60s", "50-75%", True)
        for _ in range(2):
            repo.store_session(content_id, datetime.now(), "0-10s", "0-25%", False)

        inp = QueryEngagementTotalsInput()
        result = run_query_totals(inp, repo=repo)

        assert result.total_sessions == 5
        assert result.engaged_sessions == 3
        assert result.engagement_rate == 0.6  # 3/5


class TestQueryDistribution:
    """Tests for run_query_distribution (TA-0066)."""

    def test_query_time_distribution(self):
        """Time distribution is correctly calculated."""
        repo = FakeEngagementRepo()
        content_id = uuid4()

        repo.store_session(content_id, datetime.now(), "30-60s", "50-75%", True)
        repo.store_session(content_id, datetime.now(), "30-60s", "50-75%", True)
        repo.store_session(content_id, datetime.now(), "0-10s", "0-25%", False)

        inp = QueryEngagementDistributionInput(distribution_type="time")
        result = run_query_distribution(inp, repo=repo)

        assert result.success is True
        assert result.total_sessions == 3
        assert len(result.buckets) == 2

        # Find buckets
        bucket_map = {b.bucket: b for b in result.buckets}
        assert bucket_map["30-60s"].count == 2
        assert bucket_map["0-10s"].count == 1

    def test_query_scroll_distribution(self):
        """Scroll distribution is correctly calculated."""
        repo = FakeEngagementRepo()
        content_id = uuid4()

        repo.store_session(content_id, datetime.now(), "30-60s", "75-100%", True)
        repo.store_session(content_id, datetime.now(), "30-60s", "75-100%", True)
        repo.store_session(content_id, datetime.now(), "0-10s", "0-25%", False)

        inp = QueryEngagementDistributionInput(distribution_type="scroll")
        result = run_query_distribution(inp, repo=repo)

        assert result.success is True
        bucket_map = {b.bucket: b for b in result.buckets}
        assert bucket_map["75-100%"].count == 2
        assert bucket_map["0-25%"].count == 1


class TestQueryTopEngagedContent:
    """Tests for run_query_top_engaged_content (TA-0065, TA-0066)."""

    def test_query_top_engaged_content(self):
        """Top engaged content is correctly ranked."""
        repo = FakeEngagementRepo()
        content_a = uuid4()
        content_b = uuid4()

        # Content A: 3 engaged out of 4
        for _ in range(3):
            repo.store_session(content_a, datetime.now(), "30-60s", "50-75%", True)
        repo.store_session(content_a, datetime.now(), "0-10s", "0-25%", False)

        # Content B: 1 engaged out of 2
        repo.store_session(content_b, datetime.now(), "30-60s", "50-75%", True)
        repo.store_session(content_b, datetime.now(), "0-10s", "0-25%", False)

        inp = QueryTopEngagedContentInput(limit=10)
        result = run_query_top_engaged_content(inp, repo=repo)

        assert result.success is True
        assert len(result.items) == 2

        # Content A should be first (more engaged sessions)
        assert result.items[0].content_id == content_a
        assert result.items[0].engaged_sessions == 3
        assert result.items[0].engagement_rate == 0.75  # 3/4

        assert result.items[1].content_id == content_b
        assert result.items[1].engaged_sessions == 1
