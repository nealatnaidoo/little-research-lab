"""
DEPRECATED: Legacy services directory.

This directory is deprecated as of 2026-01-12.
All services have been migrated to atomic components in src/components/.

Migration map:
- auth.py -> src/components/auth/
- collab.py -> src/components/collab/
- invite.py -> src/components/invite/
- publish.py -> src/components/publish/
- bootstrap.py -> src/components/bootstrap/

See DEPRECATED.md in this directory for more details.
"""

import warnings

warnings.warn(
    "src.services is deprecated. Use src.components instead.",
    DeprecationWarning,
    stacklevel=2,
)
