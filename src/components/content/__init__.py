"""
Content component - Content lifecycle and state machine management.

Spec refs: E2, E3, E4, SM1
"""

from .component import (
    run,
    run_create,
    run_delete,
    run_get,
    run_list,
    run_transition,
    run_update,
)
from .models import (
    ContentListOutput,
    ContentOperationOutput,
    ContentOutput,
    ContentValidationError,
    CreateContentInput,
    DeleteContentInput,
    GetContentInput,
    ListContentInput,
    TransitionContentInput,
    UpdateContentInput,
)
from .ports import (
    AssetResolverPort,
    ContentRepoPort,
    RulesPort,
    TimePort,
)

__all__ = [
    # Entry points
    "run",
    "run_create",
    "run_delete",
    "run_get",
    "run_list",
    "run_transition",
    "run_update",
    # Input models
    "CreateContentInput",
    "DeleteContentInput",
    "GetContentInput",
    "ListContentInput",
    "TransitionContentInput",
    "UpdateContentInput",
    # Output models
    "ContentListOutput",
    "ContentOperationOutput",
    "ContentOutput",
    "ContentValidationError",
    # Ports
    "AssetResolverPort",
    "ContentRepoPort",
    "RulesPort",
    "TimePort",
]
