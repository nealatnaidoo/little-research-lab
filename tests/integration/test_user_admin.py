from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from src.components.auth.component import run_login, run_update_user
from src.components.auth.models import LoginInput, UpdateUserInput
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


def _create_user(ctx, email, display_name, roles, status="active"):
    pwd_hash = ctx.auth_adapter.hash_password("password")
    now = datetime.now(UTC)
    user = User(
        id=uuid4(),
        email=email,
        display_name=display_name,
        password_hash=pwd_hash,
        roles=roles,
        status=status,
        created_at=now,
        updated_at=now,
    )

    ctx.user_repo.save(user)
    return user


def test_admin_can_update_user(clean_context):
    ctx = clean_context
    admin = _create_user(ctx, "admin@test.com", "Admin", ["admin"])
    target = _create_user(ctx, "user@test.com", "User", ["viewer"])

    # 1. Promote to Editor
    inp = UpdateUserInput(
        actor=admin, target_id=str(target.id), new_roles=["editor", "viewer"], new_status="active"
    )
    result = run_update_user(
        inp,
        ctx.user_repo,
        ctx.policy,
        ctx.session_store,
        ctx.clock,
    )

    assert result.success is True
    assert "editor" in result.user.roles

    # 2. Verify persistence
    fetched = ctx.user_repo.get_by_id(target.id)
    assert "editor" in fetched.roles

    # 3. Disable User
    inp_disable = UpdateUserInput(actor=admin, target_id=str(target.id), new_status="disabled")
    result_disable = run_update_user(
        inp_disable,
        ctx.user_repo,
        ctx.policy,
        ctx.session_store,
        ctx.clock,
    )
    assert result_disable.success is True

    fetched = ctx.user_repo.get_by_id(target.id)
    assert fetched.status == "disabled"

    # Login blocked check requires run_login
    login_inp = LoginInput(email=target.email, password="password")
    login_res = run_login(login_inp, ctx.user_repo, ctx.auth_adapter)
    assert login_res.success is False
    assert "disabled" in login_res.error


def test_non_admin_cannot_update_user(clean_context):
    ctx = clean_context
    user = _create_user(ctx, "user@test.com", "User", ["viewer"])
    target = _create_user(ctx, "target@test.com", "Target", ["viewer"])

    inp = UpdateUserInput(
        actor=user, target_id=str(target.id), new_roles=["admin"], new_status="active"
    )
    result = run_update_user(
        inp,
        ctx.user_repo,
        ctx.policy,
        ctx.session_store,
        ctx.clock,
    )
    assert result.success is False
    assert "Access denied" in result.error


def test_self_lockout_prevention(clean_context):
    ctx = clean_context
    admin = _create_user(ctx, "admin@test.com", "Admin", ["admin"])

    # Try removing admin role
    inp_role = UpdateUserInput(
        actor=admin, target_id=str(admin.id), new_roles=["viewer"], new_status="active"
    )
    res_role = run_update_user(
        inp_role,
        ctx.user_repo,
        ctx.policy,
        ctx.session_store,
        ctx.clock,
    )
    assert res_role.success is False
    assert "Cannot remove admin role" in res_role.error

    # Try disabling self
    inp_disable = UpdateUserInput(
        actor=admin, target_id=str(admin.id), new_roles=["admin"], new_status="disabled"
    )
    res_disable = run_update_user(
        inp_disable,
        ctx.user_repo,
        ctx.policy,
        ctx.session_store,
        ctx.clock,
    )
    assert res_disable.success is False
    assert "Cannot disable yourself" in res_disable.error
