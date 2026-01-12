from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from src.components.invite.component import run_create, run_redeem
from src.components.invite.models import CreateInviteInput, RedeemInviteInput
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
    ctx = ServiceContext.create(db_path, fs_path, rules)
    return ctx


def test_invite_creation_and_redemption(clean_context):
    ctx = clean_context

    # 1. Create Admin User (Creator)
    pwd_hash = ctx.auth_adapter.hash_password("adminpass")
    admin = User(
        id=uuid4(),
        email="admin@test.com",
        display_name="Admin",
        password_hash=pwd_hash,
        roles=["admin"],
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    ctx.user_repo.save(admin)

    # 2. Create Invite
    create_inp = CreateInviteInput(creator=admin, role="editor")
    res_create = run_create(
        create_inp,
        invite_repo=ctx.invite_repo,
        policy=ctx.policy,
        time=ctx.clock,
    )

    assert res_create.success
    token = res_create.token
    assert token is not None
    assert len(token) > 20

    # 3. Redeem Invite
    redeem_inp = RedeemInviteInput(
        token=token, email="new@test.com", display_name="New Editor", password="password123"
    )

    res_redeem = run_redeem(
        redeem_inp,
        invite_repo=ctx.invite_repo,
        user_repo=ctx.user_repo,
        auth_adapter=ctx.auth_adapter,
        time=ctx.clock,
    )
    assert res_redeem.success
    user = res_redeem.user

    assert user.email == "new@test.com"
    assert "editor" in user.roles
    assert user.status == "active"

    # 4. VerifyDB
    saved_user = ctx.user_repo.get_by_email("new@test.com")
    assert saved_user is not None
    assert saved_user.id == user.id

    # 5. Verify Token Consumed
    # Try redeeming again
    res_redeem_again = run_redeem(
        redeem_inp,
        invite_repo=ctx.invite_repo,
        user_repo=ctx.user_repo,
        auth_adapter=ctx.auth_adapter,
        time=ctx.clock,
    )
    assert not res_redeem_again.success
    assert "already redeemed" in res_redeem_again.error


def test_invite_permissions(clean_context):
    ctx = clean_context

    # Viewer tries to invite
    pwd_hash = ctx.auth_adapter.hash_password("pass")
    viewer = User(
        id=uuid4(),
        email="viewer@test.com",
        display_name="Viewer",
        password_hash=pwd_hash,
        roles=["viewer"],
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    ctx.user_repo.save(viewer)

    create_inp = CreateInviteInput(creator=viewer, role="editor")
    res_create = run_create(
        create_inp,
        invite_repo=ctx.invite_repo,
        policy=ctx.policy,
        time=ctx.clock,
    )
    assert not res_create.success
    assert "cannot create invites" in res_create.error
