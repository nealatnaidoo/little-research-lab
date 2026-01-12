"""
Collab component - Collaboration management for content sharing.

Manages collaboration grants for content items, allowing users to grant
and revoke access to other users with specific scopes (view, edit).
"""

from .component import (
    run,
    run_grant,
    run_list,
    run_revoke,
)
from .models import (
    CollabListOutput,
    CollabOutput,
    GrantAccessInput,
    ListCollaboratorsInput,
    RevokeAccessInput,
    # Removed non-existent models (Validation, Output wrappers if mapped differently)
)
from .ports import (
    CollabRepoPort,
    ContentRepoPort,
    # PolicyPort, # Removed
    UserRepoPort,
)

__all__ = [
    # Entry points
    "run",
    "run_grant",
    "run_list",
    "run_revoke",
    # Input models
    "GrantAccessInput",
    "ListCollaboratorsInput",
    "RevokeAccessInput",
    # Output models
    "CollabListOutput",
    "CollabOutput",
    # Ports
    "CollabRepoPort",
    "ContentRepoPort",
    # "PolicyPort", # Removed
    "UserRepoPort",
]
