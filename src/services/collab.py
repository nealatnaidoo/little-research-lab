from datetime import datetime
from uuid import UUID, uuid4

from src.domain.entities import CollaborationGrant, CollabScope, User
from src.domain.policy import PolicyEngine
from src.ports.repo import CollabRepoPort, ContentRepoPort, UserRepoPort


class CollabService:
    def __init__(
        self,
        collab_repo: CollabRepoPort,
        content_repo: ContentRepoPort,
        user_repo: UserRepoPort,
        policy: PolicyEngine
    ):
        self.repo = collab_repo
        self.content_repo = content_repo
        self.user_repo = user_repo
        self.policy = policy

    def grant_access(
        self, actor: User, content_id: UUID, target_email: str, scope: CollabScope
    ) -> CollaborationGrant:
        # 1. Fetch Content
        item = self.content_repo.get_by_id(content_id)
        if not item:
            raise ValueError("Content not found")
            
        # 2. Check Permission (Actor must be owner or admin)
        # We can reuse owns_content predicate or specific "manage_collab" rule
        if not self.policy.can_manage_collaborators(actor, item):
            raise PermissionError("Cannot manage collaborators for this item")
            
        # 3. Fetch Target User
        target = self.user_repo.get_by_email(target_email)
        if not target:
            raise ValueError("Target user not found")
            
        if target.id == item.owner_user_id:
             raise ValueError("User is already the owner")

        # 4. Upsert Grant
        # Check existing?
        existing = self.repo.get_by_content_and_user(content_id, target.id)
        if existing:
            existing.scope = scope
            self.repo.save(existing)
            return existing
            
        grant = CollaborationGrant(
            id=uuid4(),
            content_item_id=content_id,
            user_id=target.id,
            scope=scope,
            created_at=datetime.utcnow()
        )
        self.repo.save(grant)
        return grant

    def revoke_access(self, actor: User, content_id: UUID, target_user_id: UUID) -> None:
        item = self.content_repo.get_by_id(content_id)
        if not item:
            raise ValueError("Content not found")
            
        if not self.policy.can_manage_collaborators(actor, item):
             raise PermissionError("Cannot manage collaborators")
             
        grant = self.repo.get_by_content_and_user(content_id, target_user_id)
        if grant:
            self.repo.delete(grant.id)

    def list_collaborators(self, actor: User, content_id: UUID) -> list[tuple[User, CollabScope]]:
        # Returns list of (User, scope)
        # Check if actor can view collaborators? Usually if they can edit/view item.
        # For simplicity, if they can view the item, they can see collaborators? 
        # Or just restrict to owner/admin?
        # Let's say: accessible to owner/admin for now.
        
        item = self.content_repo.get_by_id(content_id)
        if not item:
            return []
            
        if not self.policy.can_manage_collaborators(actor, item):
             raise PermissionError("Access denied")
             
        grants = self.repo.list_by_content(content_id)
        results: list[tuple[User, CollabScope]] = []
        for g in grants:
            user = self.user_repo.get_by_id(g.user_id)
            if user:
                results.append((user, g.scope))
        return results
