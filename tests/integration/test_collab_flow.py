from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from src.components.collab.component import run_grant, run_revoke
from src.components.collab.models import GrantAccessInput, RevokeAccessInput
from src.components.content.component import run_create as run_create_content
from src.components.content.component import run_update as run_update_content
from src.components.content.models import CreateContentInput, UpdateContentInput
from src.domain.entities import User
from src.rules.loader import load_rules
from src.ui.context import ServiceContext


@pytest.fixture
def clean_context(tmp_path):
    # Setup context with temp DB and Rules
    db_path = str(tmp_path / "test.db")
    fs_path = str(tmp_path / "filestore")

    # Initialize DB (migrations)
    import sqlite3

    conn = sqlite3.connect(db_path)
    with open("migrations/001_initial.sql") as f:
        schema = f.read().split("-- Down")[0]
        conn.executescript(schema)
    conn.close()

    rules = load_rules(Path("rules.yaml"))  # Use real rules

    # Ensure update check uses db
    ctx = ServiceContext.create(db_path, fs_path, rules)
    return ctx


def test_collaboration_grant_flow(clean_context):
    ctx = clean_context

    # 1. Setup Users
    owner = _create_user(ctx, "owner@test.com", "Owner", ["admin"])
    collab = _create_user(ctx, "collab@test.com", "Collab", ["viewer"])

    # 2. Owner Creates Private Content
    create_inp = CreateContentInput(
        owner_user_id=owner.id,
        type="post",
        title="Secret Plans",
        slug="secret-plans",
        summary="Secret",
        blocks=[{"type": "markdown", "data": {"text": "Top Secret"}}],
    )

    res_create = run_create_content(
        create_inp,
        repo=ctx.content_repo,
        time=ctx.clock,
    )
    assert res_create.success, f"Create failed: {res_create.errors}"
    saved_item = res_create.content

    # 3. Collab tries to edit -> Fail (Shell Check)
    # Simulate App Shell Policy Check
    grant = ctx.collab_repo.get_by_content_and_user(saved_item.id, collab.id)
    # Policy check logic: Owner can edit, or Grant with 'edit' scope
    can_edit = (saved_item.owner_user_id == collab.id) or (grant and grant.scope == "edit")

    assert not can_edit

    # 4. Owner grants access
    grant_inp = GrantAccessInput(
        actor=owner, content_id=saved_item.id, target_email=collab.email, scope="edit"
    )
    res_grant = run_grant(
        grant_inp,
        ctx.collab_repo,
        ctx.content_repo,
        ctx.user_repo,
        ctx.policy,
        ctx.clock,
    )
    assert res_grant.success

    # 5. Collab tries to edit -> Success
    # Check permission again
    grant_new = ctx.collab_repo.get_by_content_and_user(saved_item.id, collab.id)
    is_owner = saved_item.owner_user_id == collab.id
    has_edit = grant_new and grant_new.scope == "edit"
    can_edit_now = is_owner or has_edit
    assert can_edit_now

    update_inp_success = UpdateContentInput(
        content_id=saved_item.id, updates={"title": "Co-authored Plans"}
    )
    res_update = run_update_content(
        update_inp_success,
        repo=ctx.content_repo,
        time=ctx.clock,
    )
    assert res_update.success
    assert res_update.content.title == "Co-authored Plans"

    # 6. Owner Revokes
    revoke_inp = RevokeAccessInput(actor=owner, content_id=saved_item.id, target_user_id=collab.id)
    run_revoke(revoke_inp, ctx.collab_repo, ctx.content_repo, ctx.policy)

    # 7. Collab tries to edit -> Fail
    grant_revoked = ctx.collab_repo.get_by_content_and_user(saved_item.id, collab.id)
    is_owner_final = saved_item.owner_user_id == collab.id
    has_edit_final = grant_revoked and grant_revoked.scope == "edit"
    can_edit_final = is_owner_final or has_edit_final
    assert not can_edit_final


def _create_user(ctx, email, name, roles):
    pwd_hash = ctx.auth_adapter.hash_password("password")
    user = User(
        id=uuid4(),
        email=email,
        display_name=name,
        password_hash=pwd_hash,
        roles=roles,
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    ctx.user_repo.save(user)
    return user
