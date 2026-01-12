"""
Redirects component - URL redirect management.

Spec refs: E7.1
"""

# Re-exports from _impl for backwards compatibility
# Note: Redirect and RedirectValidationError from _impl must be imported to ensure
# type consistency with RedirectService which uses _impl types
from ._impl import (
    Redirect,
    RedirectConfig,
    RedirectService,
    RedirectValidationError,
)
from .component import (
    run,
    run_create,
    run_delete,
    run_get,
    run_list,
    run_resolve,
    run_update,
)
from .models import (
    CreateRedirectInput,
    DeleteRedirectInput,
    GetRedirectInput,
    ListRedirectsInput,
    RedirectListOutput,
    RedirectOperationOutput,
    RedirectOutput,
    ResolveOutput,
    ResolveRedirectInput,
    UpdateRedirectInput,
)
from .ports import RedirectRepoPort, RouteCheckerPort, RulesPort

__all__ = [
    # Entry points
    "run",
    "run_create",
    "run_delete",
    "run_get",
    "run_list",
    "run_resolve",
    "run_update",
    # Input models
    "CreateRedirectInput",
    "DeleteRedirectInput",
    "GetRedirectInput",
    "ListRedirectsInput",
    "ResolveRedirectInput",
    "UpdateRedirectInput",
    # Output models
    "Redirect",
    "RedirectListOutput",
    "RedirectOperationOutput",
    "RedirectOutput",
    "RedirectValidationError",
    "ResolveOutput",
    # Ports
    "RedirectRepoPort",
    "RouteCheckerPort",
    "RulesPort",
    # Legacy _impl re-exports
    "RedirectConfig",
    "RedirectService",
]
