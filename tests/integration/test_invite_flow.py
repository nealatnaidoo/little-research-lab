
from datetime import datetime
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

def test_invite_creation_and_redemption(clean_context):
    ctx = clean_context
    
    # 1. Create Admin User (Creator)
    pwd_hash = ctx.auth_service.auth_adapter.hash_password("adminpass")
    admin = User(
        id=uuid4(), email="admin@test.com", display_name="Admin", 
        password_hash=pwd_hash, roles=["admin"], status="active",
        created_at=datetime.utcnow(), updated_at=datetime.utcnow()
    )
    ctx.auth_service.user_repo.save(admin)
    
    # 2. Create Invite
    token = ctx.invite_service.create_invite(admin, "editor")
    assert token is not None
    assert len(token) > 20
    
    # 3. Redeem Invite
    user = ctx.invite_service.redeem_invite(
        token, "new@test.com", "New Editor", "password123"
    )
    
    assert user.email == "new@test.com"
    assert "editor" in user.roles
    assert user.status == "active"
    
    # 4. VerifyDB
    saved_user = ctx.auth_service.user_repo.get_by_email("new@test.com")
    assert saved_user is not None
    assert saved_user.id == user.id
    
    # 5. Verify Token Consumed
    # Try redeeming again
    with pytest.raises(ValueError, match="Invite already redeemed"):
        ctx.invite_service.redeem_invite(
            token, "hacker@test.com", "Hacker", "pwd"
        )

def test_invite_permissions(clean_context):
    ctx = clean_context
    
    # Viewer tries to invite
    pwd_hash = ctx.auth_service.auth_adapter.hash_password("pass")
    viewer = User(
        id=uuid4(), email="viewer@test.com", display_name="Viewer", 
        password_hash=pwd_hash, roles=["viewer"], status="active",
        created_at=datetime.utcnow(), updated_at=datetime.utcnow()
    )
    ctx.auth_service.user_repo.save(viewer)
    
    with pytest.raises(PermissionError):
        ctx.invite_service.create_invite(viewer, "editor")
