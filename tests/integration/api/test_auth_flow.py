import os
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


# --- Fixtures ---
@pytest.fixture
def test_db_path(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    db = d / "test.db"
    return str(db)

@pytest.fixture
def override_settings(test_db_path):
    def _settings():
        s = Settings()
        s.db_path = test_db_path
        # Use existing rules file from project root
        s.rules_path = Path(os.getcwd()) / "research-lab-bio_rules.yaml"
        return s
    
    app.dependency_overrides[get_settings] = _settings
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def client_with_db(override_settings, test_db_path):
    # Initialize DB schema? 
    # Repos create tables on first write? No, we need DDL.
    # In SQLiteAdapter, we assumed existing schema or created it?
    # Actually, we rely on `src/adapters/sqlite/migrator.py` or manual setup usually.
    # Let's check `migrator.py` available usage.
    # Or just use `sqlite3` to dump schema.
    
    # For now, let's look at `T-0009`. It says migrations setup.
    # We'll just create the `users` table manually for this test.
    import sqlite3
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
    
    return TestClient(app)

def test_auth_happy_path(client_with_db, test_db_path):
    # 1. Create User
    repo = SQLiteUserRepo(test_db_path)
    hashed = get_password_hash("secret123")
    uid = uuid4()
    u = User(
        id=uid, email="test@example.com", display_name="Tester",
        password_hash=hashed, roles=["viewer"], status="active",
        created_at=datetime.now(), updated_at=datetime.now()
    )
    repo.save(u)
    
    # 2. Login
    # OAuth2PasswordRequestForm expects form data, not JSON
    resp = client_with_db.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "secret123"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert resp.cookies.get("access_token") is not None
    
    # 3. Access Protected Route (/me)
    # The client automatically handles cookies in subsequent requests
    resp_me = client_with_db.get("/api/auth/me")
    assert resp_me.status_code == 200
    assert resp_me.json()["email"] == "test@example.com"

def test_auth_failure(client_with_db):
    resp = client_with_db.post("/api/auth/login", data={
        "username": "wrong@example.com",
        "password": "wrong"
    })
    assert resp.status_code == 401

def test_protected_route_unauthorized(client_with_db):
    # Ensure no cookies
    client_with_db.cookies.clear()
    resp = client_with_db.get("/api/auth/me")
    assert resp.status_code == 401
