"""
Tests for Health Endpoints (T-0049).

Spec refs: NFR-R3, TA-0120
Test assertions:
- TA-0120: Health endpoints respond correctly
"""

from __future__ import annotations

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.shell.http.health import (
    CheckResult,
    DatabaseCheck,
    HealthCheckRegistry,
    HealthStatus,
    MetricsCollector,
    ProcessCheck,
    StartupCheck,
    StartupTracker,
    create_health_router,
    get_health_registry,
    get_metrics_collector,
    mark_startup_complete,
    setup_default_health_checks,
)

# --- Test Fixtures ---


@pytest.fixture
def registry() -> HealthCheckRegistry:
    """Create a fresh registry for testing."""
    return HealthCheckRegistry()


@pytest.fixture
def metrics() -> MetricsCollector:
    """Create a fresh metrics collector for testing."""
    return MetricsCollector()


@pytest.fixture
def app(registry: HealthCheckRegistry, metrics: MetricsCollector) -> FastAPI:
    """Create test FastAPI app with health router."""
    app = FastAPI()
    router = create_health_router(
        version="1.0.0-test",
        registry=registry,
        metrics=metrics,
    )
    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_startup_tracker() -> None:
    """Reset startup tracker before each test."""
    StartupTracker._start_time = None


# --- HealthStatus Tests ---


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_healthy_value(self) -> None:
        """Test HEALTHY status value."""
        assert HealthStatus.HEALTHY.value == "healthy"

    def test_unhealthy_value(self) -> None:
        """Test UNHEALTHY status value."""
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_degraded_value(self) -> None:
        """Test DEGRADED status value."""
        assert HealthStatus.DEGRADED.value == "degraded"


# --- CheckResult Tests ---


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_create_basic_result(self) -> None:
        """Test creating basic check result."""
        result = CheckResult(
            name="test",
            status=HealthStatus.HEALTHY,
        )
        assert result.name == "test"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == ""
        assert result.latency_ms == 0.0
        assert result.details == {}

    def test_create_full_result(self) -> None:
        """Test creating full check result."""
        result = CheckResult(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message="Connection refused",
            latency_ms=150.5,
            details={"host": "localhost", "port": 5432},
        )
        assert result.name == "database"
        assert result.status == HealthStatus.UNHEALTHY
        assert result.message == "Connection refused"
        assert result.latency_ms == 150.5
        assert result.details == {"host": "localhost", "port": 5432}


# --- StartupTracker Tests ---


class TestStartupTracker:
    """Tests for StartupTracker."""

    def test_not_started_initially(self) -> None:
        """Test tracker is not started initially."""
        assert not StartupTracker.is_started()
        assert StartupTracker.get_uptime_seconds() == 0.0

    def test_mark_started(self) -> None:
        """Test marking startup complete."""
        StartupTracker.mark_started()
        assert StartupTracker.is_started()

    def test_uptime_increases(self) -> None:
        """Test uptime increases after start."""
        StartupTracker.mark_started()
        time.sleep(0.01)
        uptime = StartupTracker.get_uptime_seconds()
        assert uptime > 0
        assert uptime < 1.0  # Should be very small


# --- MetricsCollector Tests ---


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_initial_snapshot(self, metrics: MetricsCollector) -> None:
        """Test initial metrics snapshot."""
        snapshot = metrics.get_snapshot()
        assert snapshot.request_count == 0
        assert snapshot.error_count == 0
        assert snapshot.avg_response_time_ms == 0.0

    def test_record_request(self, metrics: MetricsCollector) -> None:
        """Test recording a request."""
        metrics.record_request(50.0)
        snapshot = metrics.get_snapshot()
        assert snapshot.request_count == 1
        assert snapshot.error_count == 0
        assert snapshot.avg_response_time_ms == 50.0

    def test_record_error_request(self, metrics: MetricsCollector) -> None:
        """Test recording an error request."""
        metrics.record_request(100.0, is_error=True)
        snapshot = metrics.get_snapshot()
        assert snapshot.request_count == 1
        assert snapshot.error_count == 1

    def test_record_multiple_requests(self, metrics: MetricsCollector) -> None:
        """Test recording multiple requests."""
        metrics.record_request(100.0)
        metrics.record_request(200.0)
        metrics.record_request(300.0)
        snapshot = metrics.get_snapshot()
        assert snapshot.request_count == 3
        assert snapshot.avg_response_time_ms == 200.0  # (100+200+300)/3

    def test_reset(self, metrics: MetricsCollector) -> None:
        """Test resetting metrics."""
        metrics.record_request(100.0)
        metrics.record_request(200.0, is_error=True)
        metrics.reset()
        snapshot = metrics.get_snapshot()
        assert snapshot.request_count == 0
        assert snapshot.error_count == 0

    def test_uptime_in_snapshot(self, metrics: MetricsCollector) -> None:
        """Test uptime is included in snapshot."""
        StartupTracker.mark_started()
        snapshot = metrics.get_snapshot()
        assert snapshot.uptime_seconds >= 0


# --- HealthCheckRegistry Tests ---


class TestHealthCheckRegistry:
    """Tests for HealthCheckRegistry."""

    def test_empty_registry(self, registry: HealthCheckRegistry) -> None:
        """Test empty registry returns no results."""
        results = registry.run_all()
        assert results == []

    def test_register_check(self, registry: HealthCheckRegistry) -> None:
        """Test registering a check."""
        registry.register(ProcessCheck())
        results = registry.run_all()
        assert len(results) == 1
        assert results[0].name == "process"

    def test_register_multiple_checks(self, registry: HealthCheckRegistry) -> None:
        """Test registering multiple checks."""
        registry.register(ProcessCheck())
        registry.register(StartupCheck())
        results = registry.run_all()
        assert len(results) == 2

    def test_clear_registry(self, registry: HealthCheckRegistry) -> None:
        """Test clearing registry."""
        registry.register(ProcessCheck())
        registry.clear()
        results = registry.run_all()
        assert results == []


# --- ProcessCheck Tests ---


class TestProcessCheck:
    """Tests for ProcessCheck."""

    def test_check_always_healthy(self) -> None:
        """Test process check is always healthy."""
        check = ProcessCheck()
        result = check.check()
        assert result.status == HealthStatus.HEALTHY
        assert result.name == "process"
        assert "running" in result.message.lower()


# --- StartupCheck Tests ---


class TestStartupCheck:
    """Tests for StartupCheck."""

    def test_unhealthy_before_startup(self) -> None:
        """Test startup check is unhealthy before startup."""
        check = StartupCheck()
        result = check.check()
        assert result.status == HealthStatus.UNHEALTHY
        assert result.name == "startup"

    def test_healthy_after_startup(self) -> None:
        """Test startup check is healthy after startup."""
        StartupTracker.mark_started()
        check = StartupCheck()
        result = check.check()
        assert result.status == HealthStatus.HEALTHY
        assert "uptime_seconds" in result.details


# --- DatabaseCheck Tests ---


class TestDatabaseCheck:
    """Tests for DatabaseCheck."""

    def test_no_check_function_healthy(self) -> None:
        """Test database check with no check function is healthy."""
        check = DatabaseCheck()
        result = check.check()
        assert result.status == HealthStatus.HEALTHY
        assert "not configured" in result.message.lower()

    def test_successful_check(self) -> None:
        """Test successful database check."""
        check = DatabaseCheck(check_fn=lambda: None)
        result = check.check()
        assert result.status == HealthStatus.HEALTHY
        assert result.latency_ms >= 0

    def test_failed_check(self) -> None:
        """Test failed database check."""

        def failing_check() -> None:
            raise ConnectionError("Connection refused")

        check = DatabaseCheck(check_fn=failing_check)
        result = check.check()
        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection refused" in result.message


# --- Health Endpoint Tests (TA-0120) ---


class TestHealthEndpoint:
    """Tests for /health endpoint - TA-0120."""

    def test_health_empty_registry(self, client: TestClient) -> None:
        """TA-0120: Test health endpoint with empty registry."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"] == []

    def test_health_all_passing(self, client: TestClient, registry: HealthCheckRegistry) -> None:
        """TA-0120: Test health endpoint with all passing checks."""
        StartupTracker.mark_started()
        registry.register(ProcessCheck())
        registry.register(StartupCheck())

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert len(data["checks"]) == 2

    def test_health_one_failing(self, client: TestClient, registry: HealthCheckRegistry) -> None:
        """TA-0120: Test health endpoint with one failing check."""
        # Don't mark started - startup check will fail
        registry.register(ProcessCheck())
        registry.register(StartupCheck())

        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"

    def test_health_includes_version(self, client: TestClient) -> None:
        """TA-0120: Test health endpoint includes version."""
        response = client.get("/health")
        data = response.json()
        assert data["version"] == "1.0.0-test"

    def test_health_includes_uptime(self, client: TestClient) -> None:
        """TA-0120: Test health endpoint includes uptime."""
        StartupTracker.mark_started()
        response = client.get("/health")
        data = response.json()
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], float)


# --- Readiness Endpoint Tests ---


class TestReadinessEndpoint:
    """Tests for /health/ready endpoint."""

    def test_ready_empty_registry(self, client: TestClient) -> None:
        """Test readiness with empty registry."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True

    def test_ready_all_passing(self, client: TestClient, registry: HealthCheckRegistry) -> None:
        """Test readiness with all passing checks."""
        StartupTracker.mark_started()
        registry.register(ProcessCheck())
        registry.register(StartupCheck())

        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True

    def test_not_ready_one_failing(self, client: TestClient, registry: HealthCheckRegistry) -> None:
        """Test readiness with one failing check."""
        registry.register(ProcessCheck())
        registry.register(StartupCheck())  # Will fail - not started

        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["ready"] is False

    def test_ready_includes_check_details(
        self, client: TestClient, registry: HealthCheckRegistry
    ) -> None:
        """Test readiness includes check details."""
        registry.register(ProcessCheck())
        response = client.get("/health/ready")
        data = response.json()
        assert "checks" in data
        assert len(data["checks"]) == 1


# --- Liveness Endpoint Tests ---


class TestLivenessEndpoint:
    """Tests for /health/live endpoint."""

    def test_always_alive(self, client: TestClient) -> None:
        """Test liveness always returns 200."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True

    def test_includes_uptime(self, client: TestClient) -> None:
        """Test liveness includes uptime."""
        StartupTracker.mark_started()
        response = client.get("/health/live")
        data = response.json()
        assert "uptime_seconds" in data


# --- Metrics Endpoint Tests ---


class TestMetricsEndpoint:
    """Tests for /metrics endpoint."""

    def test_metrics_initial(self, client: TestClient) -> None:
        """Test metrics endpoint with initial values."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["request_count"] == 0
        assert data["error_count"] == 0
        assert data["avg_response_time_ms"] == 0.0

    def test_metrics_after_recording(self, client: TestClient, metrics: MetricsCollector) -> None:
        """Test metrics endpoint after recording."""
        metrics.record_request(100.0)
        metrics.record_request(200.0, is_error=True)

        response = client.get("/metrics")
        data = response.json()
        assert data["request_count"] == 2
        assert data["error_count"] == 1
        assert data["avg_response_time_ms"] == 150.0

    def test_metrics_includes_uptime(self, client: TestClient) -> None:
        """Test metrics includes uptime."""
        StartupTracker.mark_started()
        response = client.get("/metrics")
        data = response.json()
        assert "uptime_seconds" in data


# --- Factory Function Tests ---


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_setup_default_health_checks(self, registry: HealthCheckRegistry) -> None:
        """Test setup_default_health_checks registers defaults."""
        setup_default_health_checks(registry)
        results = registry.run_all()
        names = {r.name for r in results}
        assert "process" in names
        assert "startup" in names

    def test_mark_startup_complete(self) -> None:
        """Test mark_startup_complete."""
        assert not StartupTracker.is_started()
        mark_startup_complete()
        assert StartupTracker.is_started()

    def test_get_health_registry_singleton(self) -> None:
        """Test get_health_registry returns same instance."""
        reg1 = get_health_registry()
        reg2 = get_health_registry()
        assert reg1 is reg2

    def test_get_metrics_collector_singleton(self) -> None:
        """Test get_metrics_collector returns same instance."""
        met1 = get_metrics_collector()
        met2 = get_metrics_collector()
        assert met1 is met2


# --- Custom Health Check Tests ---


class TestCustomHealthCheck:
    """Tests for custom health checks."""

    def test_custom_check_protocol(self, registry: HealthCheckRegistry) -> None:
        """Test custom check implementing protocol."""

        class CustomCheck:
            name = "custom"

            def check(self) -> CheckResult:
                return CheckResult(
                    name=self.name,
                    status=HealthStatus.DEGRADED,
                    message="Running in degraded mode",
                )

        registry.register(CustomCheck())
        results = registry.run_all()
        assert len(results) == 1
        assert results[0].name == "custom"
        assert results[0].status == HealthStatus.DEGRADED


# --- Integration Tests ---


class TestHealthIntegration:
    """Integration tests for health module."""

    def test_full_health_flow(
        self,
        client: TestClient,
        registry: HealthCheckRegistry,
        metrics: MetricsCollector,
    ) -> None:
        """Test full health check flow."""
        # Set up
        setup_default_health_checks(registry)
        mark_startup_complete()

        # Record some metrics
        metrics.record_request(50.0)
        metrics.record_request(100.0)

        # Check health
        health_response = client.get("/health")
        assert health_response.status_code == 200

        # Check readiness
        ready_response = client.get("/health/ready")
        assert ready_response.status_code == 200

        # Check liveness
        live_response = client.get("/health/live")
        assert live_response.status_code == 200

        # Check metrics
        metrics_response = client.get("/metrics")
        metrics_data = metrics_response.json()
        assert metrics_data["request_count"] == 2

    def test_degraded_state_detection(
        self,
        client: TestClient,
        registry: HealthCheckRegistry,
    ) -> None:
        """Test detection of degraded state."""

        class DegradedCheck:
            name = "degraded"

            def check(self) -> CheckResult:
                return CheckResult(
                    name=self.name,
                    status=HealthStatus.DEGRADED,
                    message="Running in degraded mode",
                )

        registry.register(ProcessCheck())
        registry.register(DegradedCheck())

        # With one healthy and one degraded, overall should be degraded
        response = client.get("/health")
        # Degraded returns 503 to signal Kubernetes not to route traffic
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
