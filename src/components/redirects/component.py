"""
Redirects component - URL redirect management.

Spec refs: E7.1
Test assertions: TA-0043, TA-0044, TA-0045

Handles redirect creation, validation, and chain resolution.

Invariants:
- I1: Source path must be unique
- I2: No circular redirects
- I3: Status code must be 301 or 302
- I4: Target must be valid URL or relative path
- I5: Cannot redirect to self
"""

from __future__ import annotations

from ._impl import (
    Redirect as LegacyRedirect,
)
from ._impl import (
    RedirectConfig,
    RedirectService,
)
from ._impl import (
    RedirectValidationError as LegacyError,
)
from .models import (
    CreateRedirectInput,
    DeleteRedirectInput,
    GetRedirectInput,
    ListRedirectsInput,
    Redirect,
    RedirectListOutput,
    RedirectOperationOutput,
    RedirectOutput,
    RedirectValidationError,
    ResolveOutput,
    ResolveRedirectInput,
    UpdateRedirectInput,
)
from .ports import RedirectRepoPort, RouteCheckerPort, RulesPort


def _convert_redirect(legacy: LegacyRedirect | None) -> Redirect | None:
    """Convert legacy redirect to component model."""
    if legacy is None:
        return None
    return Redirect(
        id=legacy.id,
        source_path=legacy.source_path,
        target_path=legacy.target_path,
        status_code=legacy.status_code,
        enabled=legacy.enabled,
        created_at=legacy.created_at,
        updated_at=legacy.updated_at,
        created_by=legacy.created_by,
        notes=legacy.notes,
    )


def _convert_errors(
    legacy_errors: list[LegacyError],
) -> list[RedirectValidationError]:
    """Convert legacy errors to component errors."""
    return [
        RedirectValidationError(
            code=e.code,
            message=e.message,
            field=e.field,
        )
        for e in legacy_errors
    ]


def _build_config(rules: RulesPort | None) -> RedirectConfig:
    """Build redirect config from rules port."""
    if rules is None:
        return RedirectConfig()

    return RedirectConfig(
        enabled=rules.is_enabled(),
        status_code=rules.get_default_status_code(),
        max_chain_length=rules.get_max_chain_length(),
        require_internal_targets=rules.require_internal_targets(),
        prevent_loops=rules.get_prevent_loops(),
        preserve_utm_params=rules.get_preserve_utm_params(),
    )


def _create_service(
    repo: RedirectRepoPort,
    route_checker: RouteCheckerPort | None,
    rules: RulesPort | None,
) -> RedirectService:
    """Create redirect service from ports."""
    config = _build_config(rules)
    return RedirectService(
        repo=repo,  # type: ignore[arg-type]  # Protocol structural mismatch
        route_checker=route_checker,
        config=config,
    )


# --- Component Entry Points ---


def run_create(
    inp: CreateRedirectInput,
    *,
    repo: RedirectRepoPort,
    route_checker: RouteCheckerPort | None = None,
    rules: RulesPort | None = None,
) -> RedirectOperationOutput:
    """
    Create a new redirect (TA-0043, TA-0044, TA-0045).

    Args:
        inp: Input containing source, target, and options.
        repo: Redirect repository port.
        route_checker: Optional route checker port.
        rules: Optional rules port for configuration.

    Returns:
        RedirectOperationOutput with created redirect or errors.
    """
    service = _create_service(repo, route_checker, rules)

    legacy_redirect, legacy_errors = service.create(
        source_path=inp.source_path,
        target_path=inp.target_path,
        status_code=inp.status_code,
        created_by=inp.created_by,
        notes=inp.notes,
    )

    redirect = _convert_redirect(legacy_redirect)
    errors = _convert_errors(legacy_errors)

    return RedirectOperationOutput(
        redirect=redirect,
        errors=errors,
        success=len(errors) == 0,
    )


def run_update(
    inp: UpdateRedirectInput,
    *,
    repo: RedirectRepoPort,
    route_checker: RouteCheckerPort | None = None,
    rules: RulesPort | None = None,
) -> RedirectOperationOutput:
    """
    Update an existing redirect.

    Args:
        inp: Input containing redirect_id and updates.
        repo: Redirect repository port.
        route_checker: Optional route checker port.
        rules: Optional rules port for configuration.

    Returns:
        RedirectOperationOutput with updated redirect or errors.
    """
    service = _create_service(repo, route_checker, rules)

    legacy_redirect, legacy_errors = service.update(
        redirect_id=inp.redirect_id,
        updates=inp.updates,
    )

    redirect = _convert_redirect(legacy_redirect)
    errors = _convert_errors(legacy_errors)

    return RedirectOperationOutput(
        redirect=redirect,
        errors=errors,
        success=len(errors) == 0,
    )


def run_delete(
    inp: DeleteRedirectInput,
    *,
    repo: RedirectRepoPort,
    route_checker: RouteCheckerPort | None = None,
    rules: RulesPort | None = None,
) -> RedirectOperationOutput:
    """
    Delete a redirect.

    Args:
        inp: Input containing redirect_id.
        repo: Redirect repository port.
        route_checker: Optional route checker port.
        rules: Optional rules port for configuration.

    Returns:
        RedirectOperationOutput indicating success or failure.
    """
    service = _create_service(repo, route_checker, rules)

    deleted = service.delete(inp.redirect_id)

    if not deleted:
        return RedirectOperationOutput(
            redirect=None,
            errors=[
                RedirectValidationError(
                    code="not_found",
                    message=f"Redirect {inp.redirect_id} not found",
                )
            ],
            success=False,
        )

    return RedirectOperationOutput(
        redirect=None,
        errors=[],
        success=True,
    )


def run_get(
    inp: GetRedirectInput,
    *,
    repo: RedirectRepoPort,
    route_checker: RouteCheckerPort | None = None,
    rules: RulesPort | None = None,
) -> RedirectOutput:
    """
    Get a redirect by ID or source path.

    Args:
        inp: Input containing redirect_id or source_path.
        repo: Redirect repository port.
        route_checker: Optional route checker port.
        rules: Optional rules port for configuration.

    Returns:
        RedirectOutput with redirect or error.
    """
    service = _create_service(repo, route_checker, rules)

    legacy_redirect: LegacyRedirect | None = None

    if inp.redirect_id is not None:
        legacy_redirect = service.get(inp.redirect_id)
    elif inp.source_path is not None:
        legacy_redirect = service.get_by_source(inp.source_path)
    else:
        return RedirectOutput(
            redirect=None,
            errors=[
                RedirectValidationError(
                    code="invalid_input",
                    message="Either redirect_id or source_path must be provided",
                )
            ],
            success=False,
        )

    redirect = _convert_redirect(legacy_redirect)

    if redirect is None:
        return RedirectOutput(
            redirect=None,
            errors=[
                RedirectValidationError(
                    code="not_found",
                    message="Redirect not found",
                )
            ],
            success=False,
        )

    return RedirectOutput(
        redirect=redirect,
        errors=[],
        success=True,
    )


def run_list(
    inp: ListRedirectsInput,
    *,
    repo: RedirectRepoPort,
    route_checker: RouteCheckerPort | None = None,
    rules: RulesPort | None = None,
) -> RedirectListOutput:
    """
    List all redirects.

    Args:
        inp: Input (empty).
        repo: Redirect repository port.
        route_checker: Optional route checker port.
        rules: Optional rules port for configuration.

    Returns:
        RedirectListOutput with list of redirects.
    """
    service = _create_service(repo, route_checker, rules)

    legacy_redirects = service.list_all()
    redirects = tuple(_convert_redirect(r) for r in legacy_redirects if r is not None)

    return RedirectListOutput(
        redirects=redirects,  # type: ignore[arg-type]
        errors=[],
        success=True,
    )


def run_resolve(
    inp: ResolveRedirectInput,
    *,
    repo: RedirectRepoPort,
    route_checker: RouteCheckerPort | None = None,
    rules: RulesPort | None = None,
) -> ResolveOutput:
    """
    Resolve a path through the redirect chain.

    Args:
        inp: Input containing path to resolve.
        repo: Redirect repository port.
        route_checker: Optional route checker port.
        rules: Optional rules port for configuration.

    Returns:
        ResolveOutput with final target and status code.
    """
    service = _create_service(repo, route_checker, rules)

    result = service.resolve(inp.path)

    if result is None:
        return ResolveOutput(
            final_target=None,
            status_code=None,
            errors=[],
            success=True,
        )

    final_target, status_code = result

    return ResolveOutput(
        final_target=final_target,
        status_code=status_code,
        errors=[],
        success=True,
    )


def run(
    inp: (
        CreateRedirectInput
        | UpdateRedirectInput
        | DeleteRedirectInput
        | GetRedirectInput
        | ListRedirectsInput
        | ResolveRedirectInput
    ),
    *,
    repo: RedirectRepoPort,
    route_checker: RouteCheckerPort | None = None,
    rules: RulesPort | None = None,
) -> RedirectOutput | RedirectListOutput | RedirectOperationOutput | ResolveOutput:
    """
    Main entry point for the redirects component.

    Dispatches to appropriate handler based on input type.

    Args:
        inp: Input object determining the operation.
        repo: Redirect repository port.
        route_checker: Optional route checker port.
        rules: Optional rules port for configuration.

    Returns:
        Appropriate output object based on input type.
    """
    if isinstance(inp, CreateRedirectInput):
        return run_create(inp, repo=repo, route_checker=route_checker, rules=rules)
    elif isinstance(inp, UpdateRedirectInput):
        return run_update(inp, repo=repo, route_checker=route_checker, rules=rules)
    elif isinstance(inp, DeleteRedirectInput):
        return run_delete(inp, repo=repo, route_checker=route_checker, rules=rules)
    elif isinstance(inp, GetRedirectInput):
        return run_get(inp, repo=repo, route_checker=route_checker, rules=rules)
    elif isinstance(inp, ListRedirectsInput):
        return run_list(inp, repo=repo, route_checker=route_checker, rules=rules)
    elif isinstance(inp, ResolveRedirectInput):
        return run_resolve(inp, repo=repo, route_checker=route_checker, rules=rules)
    else:
        raise ValueError(f"Unknown input type: {type(inp)}")
