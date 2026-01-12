"""Integration tests for users API routes."""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.adapters.sqlite.repos import SQLiteUserRepo
from src.api.auth_utils import get_password_hash
from src.api.deps import Settings, get_settings
from src.api.main import app
from src.domain.entities import User


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
        s.rules_path = Path(os.getcwd()) / "rules.yaml"
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
def viewer_user(setup_db):
    repo = SQLiteUserRepo(setup_db)
    hashed = get_password_hash("viewer123")
    uid = uuid4()
    u = User(
        id=uid,
        email="viewer@example.com",
        display_name="Viewer",
        password_hash=hashed,
        roles=["viewer"],
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
def authenticated_viewer(client_with_db, viewer_user):
    client_with_db.cookies.clear()
    resp = client_with_db.post(
        "/api/auth/login", data={"username": "viewer@example.com", "password": "viewer123"}
    )
    assert resp.status_code == 200
    return client_with_db


def test_list_users_as_admin(authenticated_admin):
    resp = authenticated_admin.get("/api/users")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_list_users_forbidden_for_non_admin(authenticated_viewer):
    resp = authenticated_viewer.get("/api/users")
    assert resp.status_code == 403


def test_create_user_as_admin(authenticated_admin):
    resp = authenticated_admin.post(
        "/api/users",
        json={
            "email": "newuser@example.com",
            "password": "newpass123",
            "roles": ["editor"],
            "display_name": "New User",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "newuser@example.com"
    assert data["display_name"] == "New User"


def test_create_user_duplicate_email(authenticated_admin, admin_user):
    resp = authenticated_admin.post(
        "/api/users",
        json={
            "email": "admin@example.com",
            "password": "pass123",
            "roles": ["viewer"],
        },
    )
    assert resp.status_code == 400
    assert "already in use" in resp.json()["detail"]


def test_create_user_forbidden_for_non_admin(authenticated_viewer):
    resp = authenticated_viewer.post(
        "/api/users",
        json={
            "email": "another@example.com",
            "password": "pass123",
            "roles": ["viewer"],
        },
    )
    assert resp.status_code == 403


def test_update_user_as_admin(authenticated_admin, viewer_user):
    resp = authenticated_admin.put(
        f"/api/users/{viewer_user.id}",
        json={"roles": ["editor"], "status": "active"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "editor" in data["roles"]


def test_update_user_not_found(authenticated_admin):
    fake_id = uuid4()
    resp = authenticated_admin.put(
        f"/api/users/{fake_id}",
        json={"roles": ["viewer"]},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_admin_cannot_remove_own_admin_role(authenticated_admin, admin_user):
    resp = authenticated_admin.put(
        f"/api/users/{admin_user.id}",
        json={"roles": ["viewer"]},
    )
    assert resp.status_code == 400
    assert "Cannot remove admin role from yourself" in resp.json()["detail"]


def test_admin_cannot_disable_self(authenticated_admin, admin_user):
    resp = authenticated_admin.put(
        f"/api/users/{admin_user.id}",
        json={"status": "disabled"},
    )
    assert resp.status_code == 400
    assert "Cannot disable yourself" in resp.json()["detail"]


def test_unauthenticated_access(client_with_db, setup_db):
    client_with_db.cookies.clear()
    resp = client_with_db.get("/api/users")
    assert resp.status_code == 401
