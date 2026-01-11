
from pathlib import Path
from uuid import uuid4

import pytest

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
    
    rules = load_rules(Path("rules.yaml"))
    
    ctx = ServiceContext.create(db_path, fs_path, rules)
    return ctx

def _create_user(ctx, email, display_name, roles, status="active"):
    pwd_hash = ctx.auth_service.auth_adapter.hash_password("password")
    user = User(
        id=uuid4(),
        email=email,
        display_name=display_name,
        password_hash=pwd_hash,
        roles=roles,
        status=status
    )
    ctx.auth_service.user_repo.save(user)
    return user

def test_admin_can_update_user(clean_context):
    ctx = clean_context
    admin = _create_user(ctx, "admin@test.com", "Admin", ["admin"])
    target = _create_user(ctx, "user@test.com", "User", ["viewer"])
    
    # 1. Promote to Editor
    updated = ctx.auth_service.update_user(
        admin, str(target.id), ["editor", "viewer"], "active"
    )
    assert "editor" in updated.roles
    
    # 2. Verify persistence
    fetched = ctx.auth_service.user_repo.get_by_id(target.id)
    assert "editor" in fetched.roles
    
    # 3. Disable User
    ctx.auth_service.update_user(admin, str(target.id), fetched.roles, "disabled")
    fetched = ctx.auth_service.user_repo.get_by_id(target.id)
    assert fetched.status == "disabled"
    assert ctx.auth_service.login(target.email, "any") is None # Login blocked

def test_non_admin_cannot_update_user(clean_context):
    ctx = clean_context
    user = _create_user(ctx, "user@test.com", "User", ["viewer"])
    target = _create_user(ctx, "target@test.com", "Target", ["viewer"])
    
    with pytest.raises(PermissionError):
        ctx.auth_service.update_user(user, str(target.id), ["admin"], "active")

def test_self_lockout_prevention(clean_context):
    ctx = clean_context
    admin = _create_user(ctx, "admin@test.com", "Admin", ["admin"])
    
    # Try removing admin role
    with pytest.raises(ValueError):
        ctx.auth_service.update_user(admin, str(admin.id), ["viewer"], "active")
        
    # Try disabling self
    with pytest.raises(ValueError):
        ctx.auth_service.update_user(admin, str(admin.id), ["admin"], "disabled")
