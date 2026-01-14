"""
Links component - Navigation and social link management.

Spec refs: Link management
"""

# Legacy _impl re-exports for backwards compatibility
from ._impl import LinkService, validate_link_data
from .component import (
    run_create,
    run_delete,
    run_get,
    run_list,
    run_update,
)
from .models import (
    CreateLinkInput,
    DeleteLinkInput,
    GetLinkInput,
    LinkListOutput,
    LinkOperationOutput,
    LinkValidationError,
    UpdateLinkInput,
)
from .ports import LinkRepoPort

__all__ = [
    # Entry points
    "run_create",
    "run_update",
    "run_delete",
    "run_get",
    "run_list",
    # Input models
    "CreateLinkInput",
    "UpdateLinkInput",
    "DeleteLinkInput",
    "GetLinkInput",
    # Output models
    "LinkOperationOutput",
    "LinkListOutput",
    "LinkValidationError",
    # Ports
    "LinkRepoPort",
    # Legacy _impl re-exports
    "LinkService",
    "validate_link_data",
]
