"""
RedirectService (E7.1) - URL redirect management with validation.

Handles redirect creation, validation, and chain resolution.

Spec refs: E7.1, TA-0043, TA-0044, TA-0045, R5
Test assertions:
- TA-0043: Loop detection prevents circular redirects
- TA-0044: Open redirect prevention (internal targets only)
- TA-0045: Chain length validation (max 3)

Key behaviors:
- Redirects use 301 status code by default
- Only internal targets allowed (no open redirects)
- Maximum chain length of 3
- Prevents redirect loops
- Prevents collisions with existing routes
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from urllib.parse import urlparse
from uuid import UUID, uuid4

# --- Configuration ---


@dataclass(frozen=True)
class RedirectConfig:
    """Redirect configuration from rules."""

    enabled: bool = True
    status_code: int = 301

    # Constraints
    require_internal_targets: bool = True
    allow_external_targets: bool = False
    max_chain_length: int = 3
    prevent_loops: bool = True
    prevent_collisions_with_routes: bool = True

    # UTM preservation
    preserve_utm_params: bool = True


DEFAULT_CONFIG = RedirectConfig()


# --- Time Port Protocol ---


class TimePort(Protocol):
    """Time provider interface."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...


# --- Validation Errors ---


@dataclass
class RedirectValidationError:
    """Redirect validation error."""

    code: str
    message: str
    field: str | None = None


# --- Redirect Model ---


@dataclass
class Redirect:
    """URL redirect mapping."""

    id: UUID
    source_path: str  # e.g., "/old-page"
    target_path: str  # e.g., "/new-page"
    status_code: int  # 301 or 302
    enabled: bool
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    notes: str | None = None


# --- Repository Protocol ---


class RedirectRepoPort(Protocol):
    """Repository interface for redirects."""

    def get_by_id(self, redirect_id: UUID) -> Redirect | None:
        """Get redirect by ID."""
        ...

    def get_by_source(self, source_path: str) -> Redirect | None:
        """Get redirect by source path."""
        ...

    def save(self, redirect: Redirect) -> Redirect:
        """Save or update redirect."""
        ...

    def delete(self, redirect_id: UUID) -> None:
        """Delete redirect."""
        ...

    def list_all(self) -> list[Redirect]:
        """List all redirects."""
        ...


class RouteCheckerPort(Protocol):
    """Interface for checking existing routes."""

    def route_exists(self, path: str) -> bool:
        """Check if a path matches an existing route."""
        ...


# --- Validation Functions ---


def normalize_path(path: str) -> str:
    """Normalize a path for comparison."""
    if not path:
        return "/"

    # Remove trailing slash (except for root)
    path = path.rstrip("/") or "/"

    # Ensure leading slash
    if not path.startswith("/"):
        path = "/" + path

    return path.lower()


def is_internal_path(path: str) -> bool:
    """Check if path is internal (not a full URL)."""
    if not path:
        return False

    # Check for protocol
    if "://" in path:
        return False

    # Check for protocol-relative URL
    if path.startswith("//"):
        return False

    # Check for dangerous protocols (javascript:, data:, etc.)
    lower_path = path.lower()
    dangerous_protocols = ("javascript:", "data:", "vbscript:", "file:")
    if any(lower_path.startswith(proto) for proto in dangerous_protocols):
        return False

    return True


def is_absolute_url(url: str) -> bool:
    """Check if URL is absolute (has scheme)."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def validate_source_path(
    source: str,
    config: RedirectConfig = DEFAULT_CONFIG,
) -> list[RedirectValidationError]:
    """Validate source path."""
    errors: list[RedirectValidationError] = []

    if not source:
        errors.append(
            RedirectValidationError(
                code="source_required",
                message="Source path is required",
                field="source_path",
            )
        )
        return errors

    if not source.startswith("/"):
        errors.append(
            RedirectValidationError(
                code="source_must_start_with_slash",
                message="Source path must start with /",
                field="source_path",
            )
        )

    if is_absolute_url(source):
        errors.append(
            RedirectValidationError(
                code="source_cannot_be_url",
                message="Source must be a path, not a full URL",
                field="source_path",
            )
        )

    return errors


def validate_target_path(
    target: str,
    config: RedirectConfig = DEFAULT_CONFIG,
) -> list[RedirectValidationError]:
    """Validate target path (TA-0044)."""
    errors: list[RedirectValidationError] = []

    if not target:
        errors.append(
            RedirectValidationError(
                code="target_required",
                message="Target path is required",
                field="target_path",
            )
        )
        return errors

    # Check for open redirect (TA-0044)
    if config.require_internal_targets:
        if is_absolute_url(target):
            errors.append(
                RedirectValidationError(
                    code="external_target_not_allowed",
                    message="External URLs not allowed as redirect targets",
                    field="target_path",
                )
            )
        elif not is_internal_path(target):
            errors.append(
                RedirectValidationError(
                    code="invalid_target_path",
                    message="Target must be an internal path",
                    field="target_path",
                )
            )

    return errors


def detect_loop(
    source: str,
    target: str,
    repo: RedirectRepoPort,
    config: RedirectConfig = DEFAULT_CONFIG,
) -> list[RedirectValidationError]:
    """
    Detect redirect loops (TA-0043).

    Checks if adding this redirect would create a cycle.
    """
    errors: list[RedirectValidationError] = []

    if not config.prevent_loops:
        return errors

    # Normalize paths
    norm_source = normalize_path(source)
    norm_target = normalize_path(target)

    # Direct loop: A -> A
    if norm_source == norm_target:
        errors.append(
            RedirectValidationError(
                code="redirect_loop",
                message="Redirect cannot point to itself",
                field="target_path",
            )
        )
        return errors

    # Check for indirect loops: A -> B -> ... -> A
    visited = {norm_source}
    current = norm_target
    chain_length = 1

    while chain_length <= config.max_chain_length + 1:
        if current in visited:
            errors.append(
                RedirectValidationError(
                    code="redirect_loop",
                    message=f"Redirect would create a loop via {current}",
                    field="target_path",
                )
            )
            break

        # Look up next redirect in chain
        existing = repo.get_by_source(current)
        if existing is None:
            break

        visited.add(current)
        current = normalize_path(existing.target_path)
        chain_length += 1

    return errors


def validate_chain_length(
    target: str,
    repo: RedirectRepoPort,
    config: RedirectConfig = DEFAULT_CONFIG,
) -> list[RedirectValidationError]:
    """
    Validate redirect chain length (TA-0045).

    Ensures total chain length doesn't exceed max.
    """
    errors: list[RedirectValidationError] = []

    # Count existing chain length from target
    current = normalize_path(target)
    chain_length = 0

    while chain_length < config.max_chain_length + 1:
        existing = repo.get_by_source(current)
        if existing is None:
            break

        chain_length += 1
        current = normalize_path(existing.target_path)

    # Adding this redirect adds 1 to the chain
    total_length = chain_length + 1

    if total_length > config.max_chain_length:
        errors.append(
            RedirectValidationError(
                code="chain_too_long",
                message=f"Redirect chain would exceed max length of {config.max_chain_length}",
                field="target_path",
            )
        )

    return errors


def validate_collision(
    source: str,
    route_checker: RouteCheckerPort | None,
    config: RedirectConfig = DEFAULT_CONFIG,
) -> list[RedirectValidationError]:
    """
    Validate no collision with existing routes.
    """
    errors: list[RedirectValidationError] = []

    if not config.prevent_collisions_with_routes:
        return errors

    if route_checker is None:
        return errors

    if route_checker.route_exists(source):
        errors.append(
            RedirectValidationError(
                code="route_collision",
                message=f"Source path '{source}' conflicts with an existing route",
                field="source_path",
            )
        )

    return errors


# --- Redirect Service ---


class RedirectService:
    """
    Redirect service (E7.1).

    Manages URL redirects with validation.
    """

    def __init__(
        self,
        repo: RedirectRepoPort,
        route_checker: RouteCheckerPort | None = None,
        time_port: TimePort | None = None,
        config: RedirectConfig | None = None,
    ) -> None:
        """Initialize service."""
        self._repo = repo
        self._route_checker = route_checker
        self._time_port = time_port
        self._config = config or DEFAULT_CONFIG

    def _now(self) -> datetime:
        """Get current time via injected port (deterministic core)."""
        if self._time_port:
            return self._time_port.now_utc()
        # Fallback for backward compatibility - should inject TimePort in production
        from src.adapters.time_london import LondonTimeAdapter

        return LondonTimeAdapter().now_utc()

    def get(self, redirect_id: UUID) -> Redirect | None:
        """Get redirect by ID."""
        return self._repo.get_by_id(redirect_id)

    def get_by_source(self, source_path: str) -> Redirect | None:
        """Get redirect by source path."""
        normalized = normalize_path(source_path)
        return self._repo.get_by_source(normalized)

    def create(
        self,
        source_path: str,
        target_path: str,
        status_code: int | None = None,
        created_by: UUID | None = None,
        notes: str | None = None,
    ) -> tuple[Redirect | None, list[RedirectValidationError]]:
        """
        Create a new redirect.

        Validates:
        - Source path format
        - Target path format (TA-0044: no open redirects)
        - No loops (TA-0043)
        - Chain length (TA-0045)
        - No route collisions

        Returns:
            Tuple of (redirect, errors). Redirect is None if validation fails.
        """
        errors: list[RedirectValidationError] = []

        # Normalize paths
        norm_source = normalize_path(source_path)
        norm_target = normalize_path(target_path)

        # Validate source
        errors.extend(validate_source_path(source_path, self._config))

        # Validate target (TA-0044)
        errors.extend(validate_target_path(target_path, self._config))

        if errors:
            return None, errors

        # Check for existing redirect at source
        existing = self._repo.get_by_source(norm_source)
        if existing:
            errors.append(
                RedirectValidationError(
                    code="source_exists",
                    message=f"Redirect already exists for '{norm_source}'",
                    field="source_path",
                )
            )
            return None, errors

        # Check for loops (TA-0043)
        errors.extend(detect_loop(norm_source, norm_target, self._repo, self._config))

        # Check chain length (TA-0045)
        errors.extend(validate_chain_length(norm_target, self._repo, self._config))

        # Check route collision
        errors.extend(
            validate_collision(
                norm_source,
                self._route_checker,
                self._config,
            )
        )

        if errors:
            return None, errors

        # Create redirect
        now = self._now()
        redirect = Redirect(
            id=uuid4(),
            source_path=norm_source,
            target_path=norm_target,
            status_code=status_code or self._config.status_code,
            enabled=True,
            created_at=now,
            updated_at=now,
            created_by=created_by,
            notes=notes,
        )

        saved = self._repo.save(redirect)
        return saved, []

    def update(
        self,
        redirect_id: UUID,
        updates: dict[str, Any],
    ) -> tuple[Redirect | None, list[RedirectValidationError]]:
        """
        Update an existing redirect.

        Validates same constraints as create.
        """
        errors: list[RedirectValidationError] = []

        redirect = self._repo.get_by_id(redirect_id)
        if redirect is None:
            errors.append(
                RedirectValidationError(
                    code="not_found",
                    message=f"Redirect {redirect_id} not found",
                )
            )
            return None, errors

        # Apply updates
        new_target = updates.get("target_path", redirect.target_path)
        new_source = updates.get("source_path", redirect.source_path)

        # Normalize
        norm_source = normalize_path(new_source)
        norm_target = normalize_path(new_target)

        # Validate if source changed
        if "source_path" in updates:
            errors.extend(validate_source_path(new_source, self._config))

            # Check for collision with other redirects
            existing = self._repo.get_by_source(norm_source)
            if existing and existing.id != redirect_id:
                errors.append(
                    RedirectValidationError(
                        code="source_exists",
                        message=f"Redirect already exists for '{norm_source}'",
                        field="source_path",
                    )
                )

        # Validate if target changed
        if "target_path" in updates:
            errors.extend(validate_target_path(new_target, self._config))
            errors.extend(detect_loop(norm_source, norm_target, self._repo, self._config))
            errors.extend(validate_chain_length(norm_target, self._repo, self._config))

        if errors:
            return redirect, errors

        # Apply updates
        if "source_path" in updates:
            redirect.source_path = norm_source
        if "target_path" in updates:
            redirect.target_path = norm_target
        if "status_code" in updates:
            redirect.status_code = updates["status_code"]
        if "enabled" in updates:
            redirect.enabled = updates["enabled"]
        if "notes" in updates:
            redirect.notes = updates["notes"]

        redirect.updated_at = self._now()
        saved = self._repo.save(redirect)
        return saved, []

    def delete(self, redirect_id: UUID) -> bool:
        """Delete a redirect."""
        redirect = self._repo.get_by_id(redirect_id)
        if redirect is None:
            return False

        self._repo.delete(redirect_id)
        return True

    def resolve(self, path: str) -> tuple[str, int] | None:
        """
        Resolve a path through the redirect chain.

        Returns:
            Tuple of (final_target, status_code) or None if no redirect.
        """
        normalized = normalize_path(path)
        redirect = self._repo.get_by_source(normalized)

        if redirect is None or not redirect.enabled:
            return None

        # Follow chain (respecting max length)
        current = redirect
        final_target = current.target_path
        final_status = current.status_code
        chain_count = 1

        while chain_count < self._config.max_chain_length:
            next_redirect = self._repo.get_by_source(normalize_path(final_target))
            if next_redirect is None or not next_redirect.enabled:
                break

            final_target = next_redirect.target_path
            # Use the last redirect's status code
            final_status = next_redirect.status_code
            chain_count += 1

        return final_target, final_status

    def list_all(self) -> list[Redirect]:
        """List all redirects."""
        return self._repo.list_all()

    def validate_all(self) -> list[tuple[Redirect, list[RedirectValidationError]]]:
        """
        Validate all existing redirects.

        Returns list of (redirect, errors) for redirects with issues.
        """
        results = []
        all_redirects = self._repo.list_all()

        for redirect in all_redirects:
            errors: list[RedirectValidationError] = []

            # Check target validity
            errors.extend(validate_target_path(redirect.target_path, self._config))

            # Check for loops
            errors.extend(
                detect_loop(
                    redirect.source_path,
                    redirect.target_path,
                    self._repo,
                    self._config,
                )
            )

            if errors:
                results.append((redirect, errors))

        return results


# --- Factory ---


def create_redirect_service(
    repo: RedirectRepoPort,
    route_checker: RouteCheckerPort | None = None,
    config: RedirectConfig | None = None,
) -> RedirectService:
    """Create a RedirectService."""
    return RedirectService(
        repo=repo,
        route_checker=route_checker,
        config=config,
    )
