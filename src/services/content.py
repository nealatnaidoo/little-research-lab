from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from src.domain.blocks import BlockValidator
from src.domain.entities import ContentItem, User
from src.domain.policy import PolicyEngine
from src.ports.repo import CollabRepoPort, ContentRepoPort


class ContentService:
    def __init__(
        self, 
        repo: ContentRepoPort, 
        policy: PolicyEngine, 
        validator: BlockValidator,
        collab_repo: CollabRepoPort | None = None
    ):
        self.repo = repo
        self.policy = policy
        self.validator = validator
        self.collab_repo = collab_repo

    def _get_context(self, user: User | None, item: ContentItem) -> dict[str, Any]:
        if not user or not self.collab_repo:
            return {}
        grant = self.collab_repo.get_by_content_and_user(item.id, user.id)
        return {"grants": [grant] if grant else []}

    def create_item(self, user: User, item: ContentItem) -> ContentItem:
        # 1. Policy Check
        if not self.policy.check_permission(user, user.roles, "content:create", resource=item):
             raise PermissionError("User not allowed to create content")
        
        # 2. Block Validation
        if item.blocks:
            for block in item.blocks:
                self.validator.validate(block)
        
        # 3. Save
        if not item.id:
            item.id = uuid4()
        now = datetime.now()
        if not item.created_at: 
            item.created_at = now
        item.updated_at = now
        
        if not item.owner_user_id:
            item.owner_user_id = user.id

        self.repo.save(item)
        return item

    def get_item(self, user: User | None, item_id: UUID) -> ContentItem | None:
        item = self.repo.get_by_id(item_id)
        if not item:
            return None
            
        roles = user.roles if user else []
        perm = "content:read"
        if item.status == "draft":
            perm = "content:read_draft"
            
        context = self._get_context(user, item)
        if not self.policy.check_permission(user, roles, perm, resource=item, context=context):
            raise PermissionError("Access denied")
            
        return item

    def update_item(self, user: User, item: ContentItem) -> ContentItem:
        existing = self.repo.get_by_id(item.id)
        if not existing:
             raise ValueError("Item does not exist")
             
        context = self._get_context(user, existing)
        if not self.policy.check_permission(
            user, user.roles, "content:edit", resource=existing, context=context
        ):
             raise PermissionError("User not allowed to edit this content")
             
        for block in item.blocks:
            self.validator.validate(block)
            
        item.updated_at = datetime.now()
        self.repo.save(item)
        return item

    def delete_item(self, user: User, item_id: UUID) -> None:
        existing = self.repo.get_by_id(item_id)
        if not existing:
             raise ValueError("Item does not exist")
             
        context = self._get_context(user, existing)
        if not self.policy.check_permission(
            user, user.roles, "content:delete", resource=existing, context=context
        ):
             raise PermissionError("User not allowed to delete this content")
             
        self.repo.delete(item_id)

    def list_public_items(self) -> list[ContentItem]:
        """
        List all published items visible to public.
        """
        # We assume no user needed to check this, it's public listing.
        # Although list filtering is usually done by repo.
        items = self.repo.list_items(filters={"status": "published", "visibility": "public"})
        # Sort by published_at desc ideally
        items.sort(key=lambda x: x.published_at or x.created_at, reverse=True)
        return items
