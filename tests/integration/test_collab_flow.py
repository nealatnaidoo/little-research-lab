
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from src.domain.entities import ContentItem, User
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
    
    # Ensure update check uses db
    ctx = ServiceContext.create(db_path, fs_path, rules)
    return ctx

def test_collaboration_grant_flow(clean_context):
    ctx = clean_context
    
    # 1. Setup Users
    owner = _create_user(ctx, "owner@test.com", "Owner", ["admin"]) # Admin or Publisher
    collab = _create_user(ctx, "collab@test.com", "Collab", ["viewer"])
    
    # 2. Owner Creates Private Content
    item = ContentItem(
        id=uuid4(),
        owner_user_id=owner.id,
        type="post",
        slug="secret-plans",
        title="Secret Plans",
        status="draft",
        visibility="private",
        blocks=[]
    )
    # Owner creates
    saved_item = ctx.content_service.create_item(owner, item)
    
    # 3. Collab tries to edit -> Fail
    update_data = saved_item.model_copy()
    update_data.title = "Hacked Plans"
    
    with pytest.raises(PermissionError):
        ctx.content_service.update_item(collab, update_data)
        
    # 4. Owner grants access (Edit)
    ctx.collab_service.grant_access(owner, saved_item.id, collab.email, "edit")
    
    # Verify grant exists
    grants = ctx.collab_service.list_collaborators(owner, saved_item.id)
    assert len(grants) == 1
    assert grants[0][0].id == collab.id
    assert grants[0][1] == "edit"
    
    # 5. Collab tries to edit -> Success
    update_data.title = "Co-authored Plans"
    updated = ctx.content_service.update_item(collab, update_data)
    assert updated.title == "Co-authored Plans"
    
    # 6. Owner Revokes
    ctx.collab_service.revoke_access(owner, saved_item.id, collab.id)
    
    # 7. Collab tries to edit -> Fail
    update_data.title = "Hacked Again"
    with pytest.raises(PermissionError):
        ctx.content_service.update_item(collab, update_data)

def _create_user(ctx, email, name, roles):
    pwd_hash = ctx.auth_service.auth_adapter.hash_password("password")
    user = User(
        id=uuid4(), email=email, display_name=name, 
        password_hash=pwd_hash, roles=roles, status="active",
        created_at=datetime.utcnow(), updated_at=datetime.utcnow()
    )
    ctx.auth_service.user_repo.save(user)
    return user
