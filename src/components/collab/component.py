from uuid import uuid4

from src.domain.entities import CollaborationGrant, CollabScope, User
from src.domain.policy import PolicyEngine

from .models import (
    CollabListOutput,
    CollabOutput,
    GrantAccessInput,
    ListCollaboratorsInput,
    RevokeAccessInput,
)
from .ports import CollabRepoPort, ContentRepoPort, TimePort, UserRepoPort


def run_grant(
    inp: GrantAccessInput,
    collab_repo: CollabRepoPort,
    content_repo: ContentRepoPort,
    user_repo: UserRepoPort,
    policy: PolicyEngine,
    time: TimePort,
) -> CollabOutput:
    item = content_repo.get_by_id(inp.content_id)
    if not item:
        return CollabOutput(success=False, error="Content not found")

    if not policy.can_manage_collaborators(inp.actor, item):
        return CollabOutput(success=False, error="Cannot manage collaborators for this item")

    target = user_repo.get_by_email(inp.target_email)
    if not target:
        return CollabOutput(success=False, error="Target user not found")

    if target.id == item.owner_user_id:
        return CollabOutput(success=False, error="User is already the owner")

    existing = collab_repo.get_by_content_and_user(inp.content_id, target.id)
    if existing:
        existing.scope = inp.scope
        collab_repo.save(existing)
        return CollabOutput(grant=existing, success=True)

    grant = CollaborationGrant(
        id=uuid4(),
        content_item_id=inp.content_id,
        user_id=target.id,
        scope=inp.scope,
        created_at=time.now_utc(),
    )
    collab_repo.save(grant)
    return CollabOutput(grant=grant, success=True)


def run_revoke(
    inp: RevokeAccessInput,
    collab_repo: CollabRepoPort,
    content_repo: ContentRepoPort,
    policy: PolicyEngine,
) -> CollabOutput:
    item = content_repo.get_by_id(inp.content_id)
    if not item:
        return CollabOutput(success=False, error="Content not found")

    if not policy.can_manage_collaborators(inp.actor, item):
        return CollabOutput(success=False, error="Cannot manage collaborators")

    grant = collab_repo.get_by_content_and_user(inp.content_id, inp.target_user_id)
    if grant:
        collab_repo.delete(grant.id)

    return CollabOutput(success=True)


def run_list(
    inp: ListCollaboratorsInput,
    collab_repo: CollabRepoPort,
    content_repo: ContentRepoPort,
    user_repo: UserRepoPort,
    policy: PolicyEngine,
) -> CollabListOutput:
    item = content_repo.get_by_id(inp.content_id)
    if not item:
        return CollabListOutput(collaborators=[], success=False, error="Content not found")

    if not policy.can_manage_collaborators(inp.actor, item):
        # Sticking to legacy behavior for now
        return CollabListOutput(collaborators=[], success=False, error="Access denied")

    grants = collab_repo.list_by_content(inp.content_id)
    results: list[tuple[User, CollabScope]] = []
    for g in grants:
        user = user_repo.get_by_id(g.user_id)
        if user:
            results.append((user, g.scope))

    return CollabListOutput(collaborators=results, success=True)


def run(
    inp: GrantAccessInput | RevokeAccessInput | ListCollaboratorsInput,
    *,
    collab_repo: CollabRepoPort,
    content_repo: ContentRepoPort,
    user_repo: UserRepoPort | None = None,
    policy: PolicyEngine,
    time: TimePort | None = None,
) -> CollabOutput | CollabListOutput:
    if isinstance(inp, GrantAccessInput):
        assert user_repo and time
        return run_grant(inp, collab_repo, content_repo, user_repo, policy, time)

    elif isinstance(inp, RevokeAccessInput):
        return run_revoke(inp, collab_repo, content_repo, policy)

    elif isinstance(inp, ListCollaboratorsInput):
        assert user_repo
        return run_list(inp, collab_repo, content_repo, user_repo, policy)

    else:
        raise ValueError(f"Unknown input type: {type(inp)}")
