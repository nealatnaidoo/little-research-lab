from datetime import datetime
from uuid import UUID

from src.domain.entities import User
from src.domain.policy import PolicyEngine
from src.domain.state import transition
from src.ports.clock import ClockPort
from src.ports.repo import ContentRepoPort


class PublishService:
    def __init__(self, repo: ContentRepoPort, policy: PolicyEngine, clock: ClockPort):
        self.repo = repo
        self.policy = policy
        self.clock = clock

    def publish_now(self, user: User, item_id: UUID) -> None:
        item = self.repo.get_by_id(item_id)
        if not item:
            raise ValueError("Item not found")

        if not self.policy.check_permission(user, user.roles, "content:publish", resource=item):
            raise PermissionError("User not allowed to publish this content")

        item = transition(item, "published", self.clock.now())
        self.repo.save(item)

    def schedule(self, user: User, item_id: UUID, at_datetime: datetime) -> None:
        item = self.repo.get_by_id(item_id)
        if not item:
            raise ValueError("Item not found")

        if not self.policy.check_permission(user, user.roles, "content:publish", resource=item):
             raise PermissionError("User not allowed to schedule this content")

        if at_datetime <= self.clock.now():
            raise ValueError("Cannot schedule in the past")

        # Set date first so transition validation passes
        item = item.model_copy(update={"publish_at": at_datetime})
        item = transition(item, "scheduled", self.clock.now())
        self.repo.save(item)

    def unpublish(self, user: User, item_id: UUID) -> None:
        item = self.repo.get_by_id(item_id)
        if not item:
            raise ValueError("Item not found")

        if not self.policy.check_permission(user, user.roles, "content:publish", resource=item):
             raise PermissionError("User not allowed to unpublish")

        item = transition(item, "draft", self.clock.now())
        self.repo.save(item)

    def process_due_items(self) -> int:
        """
        Check for scheduled items that are due and publish them.
        Returns number of items published.
        """
        all_items = self.repo.list_items(filters={"status": "scheduled"})
        
        count = 0
        now = self.clock.now()
        
        for item in all_items:
            if item.status == "scheduled" and item.publish_at and item.publish_at <= now:
                try:
                    # Automate transition
                    item = transition(item, "published", now)
                    self.repo.save(item)
                    count += 1
                except Exception:
                    continue
                    
        return count
