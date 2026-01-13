"""Links component - Navigation and social link management."""

from ._impl import LinkService, LinkValidationError
from .component import (
    CreateLinkInput,
    DeleteLinkInput,
    GetLinkInput,
    LinkListOutput,
    LinkOperationOutput,
    UpdateLinkInput,
    run_create,
    run_delete,
    run_get,
    run_list,
    run_update,
)

__all__ = [
    "LinkService",
    "LinkValidationError",
    "CreateLinkInput",
    "UpdateLinkInput",
    "DeleteLinkInput",
    "GetLinkInput",
    "LinkOperationOutput",
    "LinkListOutput",
    "run_create",
    "run_update",
    "run_delete",
    "run_get",
    "run_list",
]
