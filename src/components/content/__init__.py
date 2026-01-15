"""
Content component - Content lifecycle and state machine management.

Spec refs: E2, E3, E4, SM1
"""

# Re-exports from legacy content service (pending full migration)
from src.core.services.content import (
    ContentService,
    ContentStateMachine,
    InvalidTransitionError,
    PublishGuardError,
    StateTransition,
    create_content_service,
    extract_asset_references,
    validate_content_fields,
    validate_publish_at,
)

from .component import (
    run,
    run_create,
    run_delete,
    run_get,
    run_get_related,
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
    GetRelatedInput,
    ListContentInput,
    RelatedArticlesOutput,
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
    "run_get_related",
    "run_list",
    "run_transition",
    "run_update",
    # Input models
    "CreateContentInput",
    "DeleteContentInput",
    "GetContentInput",
    "GetRelatedInput",
    "ListContentInput",
    "TransitionContentInput",
    "UpdateContentInput",
    # Output models
    "ContentListOutput",
    "ContentOperationOutput",
    "ContentOutput",
    "ContentValidationError",
    "RelatedArticlesOutput",
    # Ports
    "AssetResolverPort",
    "ContentRepoPort",
    "RulesPort",
    "TimePort",
    # Legacy service re-exports
    "ContentService",
    "ContentStateMachine",
    "InvalidTransitionError",
    "PublishGuardError",
    "StateTransition",
    "create_content_service",
    "extract_asset_references",
    "validate_content_fields",
    "validate_publish_at",
]
