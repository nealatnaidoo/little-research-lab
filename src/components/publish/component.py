"""Publish component - handles content publishing lifecycle operations."""

from src.components.publish.models import (
    ProcessDueInput,
    ProcessDueOutput,
    PublishNowInput,
    PublishNowOutput,
    PublishValidationError,
    ScheduleInput,
    ScheduleOutput,
    UnpublishInput,
    UnpublishOutput,
)
from src.components.publish.ports import ClockPort, ContentRepoPort, PolicyPort, UserRepoPort
from src.domain.state import transition

# Type alias for all supported inputs
PublishInput = PublishNowInput | ScheduleInput | UnpublishInput | ProcessDueInput
PublishOutput = PublishNowOutput | ScheduleOutput | UnpublishOutput | ProcessDueOutput


class PublishComponent:
    """Component for managing content publishing lifecycle."""

    def __init__(
        self,
        content_repo: ContentRepoPort,
        user_repo: UserRepoPort,
        policy: PolicyPort,
        clock: ClockPort,
    ) -> None:
        self._content_repo = content_repo
        self._user_repo = user_repo
        self._policy = policy
        self._clock = clock

    def run(self, input_data: PublishInput) -> PublishOutput:
        """Main dispatcher - routes to appropriate handler based on input type."""
        if isinstance(input_data, PublishNowInput):
            return self.run_publish_now(input_data)
        elif isinstance(input_data, ScheduleInput):
            return self.run_schedule(input_data)
        elif isinstance(input_data, UnpublishInput):
            return self.run_unpublish(input_data)
        elif isinstance(input_data, ProcessDueInput):
            return self.run_process_due(input_data)
        else:
            # Should never happen with type checking, but handle gracefully
            raise TypeError(f"Unknown input type: {type(input_data)}")

    def run_publish_now(self, input_data: PublishNowInput) -> PublishNowOutput:
        """Publish a content item immediately."""
        errors: list[PublishValidationError] = []

        # Get user
        user = self._user_repo.get_by_id(input_data.user_id)
        if not user:
            errors.append(
                PublishValidationError(
                    code="USER_NOT_FOUND",
                    message="User not found",
                    field="user_id",
                )
            )
            return PublishNowOutput(errors=errors, success=False)

        # Get content item
        item = self._content_repo.get_by_id(input_data.item_id)
        if not item:
            errors.append(
                PublishValidationError(
                    code="ITEM_NOT_FOUND",
                    message="Item not found",
                    field="item_id",
                )
            )
            return PublishNowOutput(errors=errors, success=False)

        # Check permission
        if not self._policy.check_permission(
            user, list(user.roles), "content:publish", resource=item
        ):
            errors.append(
                PublishValidationError(
                    code="PERMISSION_DENIED",
                    message="User not allowed to publish this content",
                    field="user_id",
                )
            )
            return PublishNowOutput(errors=errors, success=False)

        # Perform transition
        try:
            now = self._clock.now()
            updated_item = transition(item, "published", now)
            self._content_repo.save(updated_item)
        except ValueError as e:
            errors.append(
                PublishValidationError(
                    code="TRANSITION_ERROR",
                    message=str(e),
                    field="status",
                )
            )
            return PublishNowOutput(errors=errors, success=False)

        return PublishNowOutput(errors=[], success=True)

    def run_schedule(self, input_data: ScheduleInput) -> ScheduleOutput:
        """Schedule a content item for future publication."""
        errors: list[PublishValidationError] = []

        # Get user
        user = self._user_repo.get_by_id(input_data.user_id)
        if not user:
            errors.append(
                PublishValidationError(
                    code="USER_NOT_FOUND",
                    message="User not found",
                    field="user_id",
                )
            )
            return ScheduleOutput(errors=errors, success=False)

        # Get content item
        item = self._content_repo.get_by_id(input_data.item_id)
        if not item:
            errors.append(
                PublishValidationError(
                    code="ITEM_NOT_FOUND",
                    message="Item not found",
                    field="item_id",
                )
            )
            return ScheduleOutput(errors=errors, success=False)

        # Check permission
        if not self._policy.check_permission(
            user, list(user.roles), "content:publish", resource=item
        ):
            errors.append(
                PublishValidationError(
                    code="PERMISSION_DENIED",
                    message="User not allowed to schedule this content",
                    field="user_id",
                )
            )
            return ScheduleOutput(errors=errors, success=False)

        # Validate schedule time is in the future
        now = self._clock.now()
        if input_data.at_datetime <= now:
            errors.append(
                PublishValidationError(
                    code="INVALID_SCHEDULE_TIME",
                    message="Cannot schedule in the past",
                    field="at_datetime",
                )
            )
            return ScheduleOutput(errors=errors, success=False)

        # Perform transition
        try:
            # Set publish_at first so transition validation passes
            item = item.model_copy(update={"publish_at": input_data.at_datetime})
            updated_item = transition(item, "scheduled", now)
            self._content_repo.save(updated_item)
        except ValueError as e:
            errors.append(
                PublishValidationError(
                    code="TRANSITION_ERROR",
                    message=str(e),
                    field="status",
                )
            )
            return ScheduleOutput(errors=errors, success=False)

        return ScheduleOutput(errors=[], success=True)

    def run_unpublish(self, input_data: UnpublishInput) -> UnpublishOutput:
        """Unpublish a content item (return to draft)."""
        errors: list[PublishValidationError] = []

        # Get user
        user = self._user_repo.get_by_id(input_data.user_id)
        if not user:
            errors.append(
                PublishValidationError(
                    code="USER_NOT_FOUND",
                    message="User not found",
                    field="user_id",
                )
            )
            return UnpublishOutput(errors=errors, success=False)

        # Get content item
        item = self._content_repo.get_by_id(input_data.item_id)
        if not item:
            errors.append(
                PublishValidationError(
                    code="ITEM_NOT_FOUND",
                    message="Item not found",
                    field="item_id",
                )
            )
            return UnpublishOutput(errors=errors, success=False)

        # Check permission
        if not self._policy.check_permission(
            user, list(user.roles), "content:publish", resource=item
        ):
            errors.append(
                PublishValidationError(
                    code="PERMISSION_DENIED",
                    message="User not allowed to unpublish",
                    field="user_id",
                )
            )
            return UnpublishOutput(errors=errors, success=False)

        # Perform transition
        try:
            now = self._clock.now()
            updated_item = transition(item, "draft", now)
            self._content_repo.save(updated_item)
        except ValueError as e:
            errors.append(
                PublishValidationError(
                    code="TRANSITION_ERROR",
                    message=str(e),
                    field="status",
                )
            )
            return UnpublishOutput(errors=errors, success=False)

        return UnpublishOutput(errors=[], success=True)

    def run_process_due(self, input_data: ProcessDueInput) -> ProcessDueOutput:
        """Process scheduled items that are due for publication."""
        _ = input_data  # Explicitly mark as intentionally unused
        errors: list[PublishValidationError] = []
        count = 0
        now = self._clock.now()

        # Get all scheduled items
        all_items = self._content_repo.list_items(filters={"status": "scheduled"})

        for item in all_items:
            if item.status == "scheduled" and item.publish_at and item.publish_at <= now:
                try:
                    updated_item = transition(item, "published", now)
                    self._content_repo.save(updated_item)
                    count += 1
                except ValueError as e:
                    errors.append(
                        PublishValidationError(
                            code="TRANSITION_ERROR",
                            message=f"Failed to publish item {item.id}: {e}",
                            field="item_id",
                        )
                    )
                    # Continue processing other items

        # Success if we processed any items or there were no errors
        success = len(errors) == 0
        return ProcessDueOutput(count=count, errors=errors, success=success)
