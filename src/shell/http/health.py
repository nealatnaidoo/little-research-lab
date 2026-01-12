"""
Health endpoints (T-0049).

Provides health check and metrics endpoints for monitoring.

Spec refs: NFR-R3, TA-0120
Test assertions:
- TA-0120: Health endpoints respond correctly

Key behaviors:
- /health: Basic health status
- /health/ready: Readiness probe (dependency checks)
- /health/live: Liveness probe (process alive)
- /metrics: Basic metrics (optional scaffolding)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

# --- Types ---


class HealthStatus(str, Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


@dataclass
class CheckResult:
    """Result of a single health check."""

    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthResponse:
    """Full health check response."""

    status: HealthStatus
    checks: list[CheckResult]
    version: str = "0.0.0"
    uptime_seconds: float = 0.0


# --- Health Check Protocol ---


class HealthCheck(Protocol):
    """Protocol for health checks."""

    name: str

    def check(self) -> CheckResult:
        """Run the health check and return result."""
        ...


# --- Startup Tracker ---


class StartupTracker:
    """Tracks application startup time for uptime calculation."""

    _start_time: float | None = None

    @classmethod
    def mark_started(cls) -> None:
        """Mark the application as started."""
        cls._start_time = time.time()

    @classmethod
    def get_uptime_seconds(cls) -> float:
        """Get uptime in seconds since start."""
        if cls._start_time is None:
            return 0.0
        return time.time() - cls._start_time

    @classmethod
    def is_started(cls) -> bool:
        """Check if application has been marked as started."""
        return cls._start_time is not None


# --- Metrics Collector ---


@dataclass
class MetricsSnapshot:
    """Snapshot of application metrics."""

    request_count: int = 0
    error_count: int = 0
    avg_response_time_ms: float = 0.0
    uptime_seconds: float = 0.0


class MetricsCollector:
    """
    Simple in-memory metrics collector.

    Production systems should use Prometheus or similar.
    """

    def __init__(self) -> None:
        """Initialize collector."""
        self._request_count = 0
        self._error_count = 0
        self._total_response_time_ms = 0.0

    def record_request(self, response_time_ms: float, is_error: bool = False) -> None:
        """Record a request."""
        self._request_count += 1
        self._total_response_time_ms += response_time_ms
        if is_error:
            self._error_count += 1

    def get_snapshot(self) -> MetricsSnapshot:
        """Get current metrics snapshot."""
        avg_response_time = (
            self._total_response_time_ms / self._request_count if self._request_count > 0 else 0.0
        )
        return MetricsSnapshot(
            request_count=self._request_count,
            error_count=self._error_count,
            avg_response_time_ms=avg_response_time,
            uptime_seconds=StartupTracker.get_uptime_seconds(),
        )

    def reset(self) -> None:
        """Reset all metrics."""
        self._request_count = 0
        self._error_count = 0
        self._total_response_time_ms = 0.0


# Global metrics instance (singleton for simplicity)
_metrics = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    return _metrics


# --- Health Check Registry ---


class HealthCheckRegistry:
    """Registry of health checks to run."""

    def __init__(self) -> None:
        """Initialize registry."""
        self._checks: list[HealthCheck] = []

    def register(self, check: HealthCheck) -> None:
        """Register a health check."""
        self._checks.append(check)

    def run_all(self) -> list[CheckResult]:
        """Run all registered checks."""
        return [check.check() for check in self._checks]

    def clear(self) -> None:
        """Clear all registered checks."""
        self._checks = []


# Global registry instance
_registry = HealthCheckRegistry()


def get_health_registry() -> HealthCheckRegistry:
    """Get the global health check registry."""
    return _registry


# --- Built-in Checks ---


class ProcessCheck:
    """Basic process liveness check."""

    name = "process"

    def check(self) -> CheckResult:
        """Check if process is alive (always true if we get here)."""
        return CheckResult(
            name=self.name,
            status=HealthStatus.HEALTHY,
            message="Process is running",
        )


class StartupCheck:
    """Check if application has completed startup."""

    name = "startup"

    def check(self) -> CheckResult:
        """Check if startup is complete."""
        if StartupTracker.is_started():
            return CheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Startup complete",
                details={"uptime_seconds": StartupTracker.get_uptime_seconds()},
            )
        return CheckResult(
            name=self.name,
            status=HealthStatus.UNHEALTHY,
            message="Startup not complete",
        )


# --- Database Check (example dependency check) ---


class DatabaseCheck:
    """Database connectivity check."""

    name = "database"

    def __init__(self, check_fn: Any = None) -> None:
        """Initialize with optional check function."""
        self._check_fn = check_fn

    def check(self) -> CheckResult:
        """Check database connectivity."""
        start = time.time()

        if self._check_fn is None:
            return CheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Database check not configured",
            )

        try:
            self._check_fn()
            latency = (time.time() - start) * 1000
            return CheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Database connected",
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return CheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {e!s}",
                latency_ms=latency,
            )


# --- FastAPI Router ---


def create_health_router(
    version: str = "0.0.0",
    registry: HealthCheckRegistry | None = None,
    metrics: MetricsCollector | None = None,
) -> APIRouter:
    """
    Create FastAPI router for health endpoints.

    Args:
        version: Application version string
        registry: Health check registry (uses global if None)
        metrics: Metrics collector (uses global if None)

    Returns:
        FastAPI router with health endpoints
    """
    router = APIRouter(tags=["health"])
    reg = registry or get_health_registry()
    met = metrics or get_metrics_collector()

    @router.get(
        "/health",
        response_model=None,
        responses={
            200: {"description": "Service is healthy"},
            503: {"description": "Service is unhealthy"},
        },
    )
    def health_check() -> JSONResponse:
        """
        Basic health check endpoint.

        Returns overall health status based on all registered checks.
        """
        results = reg.run_all()

        # Determine overall status
        if all(r.status == HealthStatus.HEALTHY for r in results):
            overall = HealthStatus.HEALTHY
        elif any(r.status == HealthStatus.UNHEALTHY for r in results):
            overall = HealthStatus.UNHEALTHY
        else:
            overall = HealthStatus.DEGRADED

        response = {
            "status": overall.value,
            "version": version,
            "uptime_seconds": StartupTracker.get_uptime_seconds(),
            "checks": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "latency_ms": r.latency_ms,
                }
                for r in results
            ],
        }

        status_code = (
            status.HTTP_200_OK
            if overall == HealthStatus.HEALTHY
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return JSONResponse(content=response, status_code=status_code)

    @router.get(
        "/health/ready",
        response_model=None,
        responses={
            200: {"description": "Service is ready to accept traffic"},
            503: {"description": "Service is not ready"},
        },
    )
    def readiness_check() -> JSONResponse:
        """
        Kubernetes-style readiness probe.

        Checks if the service is ready to accept traffic.
        Returns 200 if all dependency checks pass.
        """
        results = reg.run_all()

        # For readiness, all checks must pass
        is_ready = all(r.status == HealthStatus.HEALTHY for r in results)

        response = {
            "ready": is_ready,
            "checks": [
                {"name": r.name, "status": r.status.value, "message": r.message} for r in results
            ],
        }

        status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

        return JSONResponse(content=response, status_code=status_code)

    @router.get(
        "/health/live",
        response_model=None,
        responses={
            200: {"description": "Service process is alive"},
        },
    )
    def liveness_check() -> JSONResponse:
        """
        Kubernetes-style liveness probe.

        Simple check that the process is alive and responding.
        This should always return 200 unless the process is dead.
        """
        return JSONResponse(
            content={"alive": True, "uptime_seconds": StartupTracker.get_uptime_seconds()},
            status_code=status.HTTP_200_OK,
        )

    @router.get(
        "/metrics",
        response_model=None,
    )
    def metrics_endpoint() -> JSONResponse:
        """
        Basic metrics endpoint.

        Returns application metrics snapshot.
        For production, consider using Prometheus format.
        """
        snapshot = met.get_snapshot()

        return JSONResponse(
            content={
                "request_count": snapshot.request_count,
                "error_count": snapshot.error_count,
                "avg_response_time_ms": snapshot.avg_response_time_ms,
                "uptime_seconds": snapshot.uptime_seconds,
            },
            status_code=status.HTTP_200_OK,
        )

    return router


# --- Factory Functions ---


def setup_default_health_checks(registry: HealthCheckRegistry | None = None) -> None:
    """
    Register default health checks.

    Call during application startup to set up basic checks.
    """
    reg = registry or get_health_registry()
    reg.register(ProcessCheck())
    reg.register(StartupCheck())


def mark_startup_complete() -> None:
    """Mark application startup as complete."""
    StartupTracker.mark_started()
