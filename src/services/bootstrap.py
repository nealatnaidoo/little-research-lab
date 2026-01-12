"""Legacy bootstrap wrapper - redirects to atomic component.

DEPRECATED: This module exists only for backwards compatibility.
New code should import from src/components/bootstrap/ directly.
"""

from __future__ import annotations

import os
import sys
import warnings
from typing import TYPE_CHECKING

from src.components.bootstrap.component import run
from src.components.bootstrap.models import BootstrapInput

if TYPE_CHECKING:
    from src.rules.models import AdminBootstrapRules, Rules
    from src.ui.context import ServiceContext


class _RulesAdapter:
    """Adapter to bridge Rules to RulesPort protocol."""

    def __init__(self, rules: Rules) -> None:
        self._rules = rules

    def get_bootstrap_config(self) -> AdminBootstrapRules:
        return self._rules.ops.bootstrap_admin


def bootstrap_system(ctx: ServiceContext) -> None:
    """
    Check if system needs bootstrapping (Day 0) and create owner account if configured.

    DEPRECATED: This function is deprecated. Use src/components/bootstrap/ directly.
    """
    warnings.warn(
        "bootstrap_system from src/services/bootstrap is deprecated. "
        "Use src/components/bootstrap/ instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Get bootstrap credentials from environment
    email = os.environ.get("LRL_BOOTSTRAP_EMAIL")
    password = os.environ.get("LRL_BOOTSTRAP_PASSWORD")

    # Create input for new component
    inp = BootstrapInput(
        bootstrap_email=email,
        bootstrap_password=password,
    )

    # Create adapters for the new component
    rules_adapter = _RulesAdapter(ctx.rules)

    # Call new component
    result = run(
        inp,
        user_repo=ctx.user_repo,
        auth_adapter=ctx.auth_adapter,
        rules=rules_adapter,
        time=ctx.clock,
    )

    # Log result (matching old behavior)
    if result.created and result.user:
        print(f"BOOTSTRAP: Owner account created for {result.user.email}")
    elif result.skipped_reason:
        print(f"BOOTSTRAP INFO: {result.skipped_reason}")
    elif not result.success:
        errors_str = ", ".join(str(e) for e in (result.errors or []))
        print(f"BOOTSTRAP ERROR: {errors_str}", file=sys.stderr)
