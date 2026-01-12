"""Publish component models - frozen dataclass inputs and outputs."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PublishValidationError:
    """Validation error details for publish operations."""

    code: str
    message: str
    field: str


@dataclass(frozen=True)
class PublishNowInput:
    """Input for immediate publish operation."""

    user_id: UUID
    item_id: UUID


@dataclass(frozen=True)
class PublishNowOutput:
    """Output for immediate publish operation."""

    errors: list[PublishValidationError]
    success: bool


@dataclass(frozen=True)
class ScheduleInput:
    """Input for scheduling a publish operation."""

    user_id: UUID
    item_id: UUID
    at_datetime: datetime


@dataclass(frozen=True)
class ScheduleOutput:
    """Output for scheduling a publish operation."""

    errors: list[PublishValidationError]
    success: bool


@dataclass(frozen=True)
class UnpublishInput:
    """Input for unpublish operation."""

    user_id: UUID
    item_id: UUID


@dataclass(frozen=True)
class UnpublishOutput:
    """Output for unpublish operation."""

    errors: list[PublishValidationError]
    success: bool


@dataclass(frozen=True)
class ProcessDueInput:
    """Input for processing due scheduled items - empty input."""

    pass


@dataclass(frozen=True)
class ProcessDueOutput:
    """Output for processing due scheduled items."""

    count: int
    errors: list[PublishValidationError]
    success: bool
