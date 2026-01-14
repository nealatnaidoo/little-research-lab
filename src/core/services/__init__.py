# little-research-lab-v3 — Services (Domain Services)
# Orchestrate domain logic with injected ports

# =============================================================================
# DEPRECATED - This directory is deprecated as of 2026-01-12
# =============================================================================
# All services in this directory have been migrated to atomic components
# in src/components/. See DEPRECATED.md for migration map.
#
# Do NOT add new code here. Use src/components/ instead.
# =============================================================================

import warnings

warnings.warn(
    "src.core.services is deprecated. Import from src.components.* instead. "
    "This module will be removed on 2026-02-14. "
    "See src/core/services/DEPRECATED.md for migration map.",
    DeprecationWarning,
    stacklevel=2,
)
