"""Integration tests for content API routes."""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.adapters.sqlite.repos import SQLiteContentRepo, SQLiteUserRepo
from src.api.auth_utils import get_password_hash
from src.api.deps import Settings, get_settings
from src.api.main import app
from src.domain.entities import ContentItem, User


@pytest.fixture
def test_db_path(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    db = d / "test.db"
    return str(db)


@pytest.fixture
def override_settings(test_db_path, tmp_path):
    def _settings():
        s = Settings()
        s.db_path = test_db_path
        s.assets_dir = tmp_path / "assets"
        s.assets_dir.mkdir(exist_ok=True)
        s.rules_path = Path(os.getcwd()) / "research-lab-bio_rules.yaml"
        return s

    app.dependency_overrides[get_settings] = _settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def setup_db(test_db_path):
    conn = sqlite3.connect(test_db_path)
    conn.execute("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            display_name TEXT,
            password_hash TEXT,
            status TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE role_assignments (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            role TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE content_items (
            id TEXT PRIMARY KEY,
            type TEXT,
            slug TEXT,
            title TEXT,
            summary TEXT,
            status TEXT,
            visibility TEXT,
            publish_at TEXT,
            published_at TEXT,
            owner_user_id TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE content_blocks (
            id TEXT PRIMARY KEY,
            content_item_id TEXT,
            block_type TEXT,
            data_json TEXT,
            position INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE collaborators (
            id TEXT PRIMARY KEY,
            content_item_id TEXT,
            user_id TEXT,
            role TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE collaboration_grants (
            id TEXT PRIMARY KEY,
            content_item_id TEXT,
            user_id TEXT,
            role TEXT,
            granted_by_user_id TEXT,
            created_at TEXT
        )
    """)
    conn.close()
    return test_db_path


@pytest.fixture
def admin_user(setup_db):
    repo = SQLiteUserRepo(setup_db)
    hashed = get_password_hash("admin123")
    uid = uuid4()
    u = User(
        id=uid,
        email="admin@example.com",
        display_name="Admin",
        password_hash=hashed,
        roles=["admin"],
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    repo.save(u)
    return u


@pytest.fixture
def editor_user(setup_db):
    repo = SQLiteUserRepo(setup_db)
    hashed = get_password_hash("editor123")
    uid = uuid4()
    u = User(
        id=uid,
        email="editor@example.com",
        display_name="Editor",
        password_hash=hashed,
        roles=["editor"],
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    repo.save(u)
    return u


@pytest.fixture
def client_with_db(override_settings, setup_db):
    return TestClient(app)


@pytest.fixture
def authenticated_admin(client_with_db, admin_user):
    resp = client_with_db.post(
        "/api/auth/login", data={"username": "admin@example.com", "password": "admin123"}
    )
    assert resp.status_code == 200
    return client_with_db


@pytest.fixture
def authenticated_editor(client_with_db, editor_user):
    # Clear cookies from previous session
    client_with_db.cookies.clear()
    resp = client_with_db.post(
        "/api/auth/login", data={"username": "editor@example.com", "password": "editor123"}
    )
    assert resp.status_code == 200
    return client_with_db


def test_create_content(authenticated_admin):
    resp = authenticated_admin.post(
        "/api/content",
        json={
            "type": "post",
            "slug": "test-post",
            "title": "Test Post",
            "summary": "A test post",
            "status": "draft",
            "visibility": "public",
            "blocks": [
                {"block_type": "markdown", "data_json": {"text": "Hello"}, "position": 0}
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Post"
    assert data["slug"] == "test-post"
    assert data["status"] == "draft"


def test_list_content(authenticated_admin, setup_db):
    # Create some content first
    repo = SQLiteContentRepo(setup_db)
    item = ContentItem(
        id=uuid4(),
        type="post",
        slug="existing-post",
        title="Existing Post",
        summary="",
        status="draft",
        visibility="public",
        owner_user_id=uuid4(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    repo.save(item)

    resp = authenticated_admin.get("/api/content")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_content_by_id(authenticated_admin, setup_db):
    repo = SQLiteContentRepo(setup_db)
    item_id = uuid4()
    item = ContentItem(
        id=item_id,
        type="post",
        slug="get-test",
        title="Get Test",
        summary="",
        status="draft",
        visibility="public",
        owner_user_id=uuid4(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    repo.save(item)

    resp = authenticated_admin.get(f"/api/content/{item_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Get Test"


def test_update_content(authenticated_admin, setup_db):
    repo = SQLiteContentRepo(setup_db)
    item_id = uuid4()
    item = ContentItem(
        id=item_id,
        type="post",
        slug="update-test",
        title="Original Title",
        summary="",
        status="draft",
        visibility="public",
        owner_user_id=uuid4(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    repo.save(item)

    resp = authenticated_admin.put(
        f"/api/content/{item_id}",
        json={"title": "Updated Title", "status": "published"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated Title"
    assert data["status"] == "published"


def test_delete_content(authenticated_admin, setup_db):
    repo = SQLiteContentRepo(setup_db)
    item_id = uuid4()
    item = ContentItem(
        id=item_id,
        type="post",
        slug="delete-test",
        title="To Delete",
        summary="",
        status="draft",
        visibility="public",
        owner_user_id=uuid4(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    repo.save(item)

    resp = authenticated_admin.delete(f"/api/content/{item_id}")
    assert resp.status_code == 204


def test_content_not_found(authenticated_admin):
    fake_id = uuid4()
    resp = authenticated_admin.get(f"/api/content/{fake_id}")
    assert resp.status_code == 404


def test_unauthenticated_access(client_with_db, setup_db):
    client_with_db.cookies.clear()
    resp = client_with_db.get("/api/content")
    assert resp.status_code == 401
