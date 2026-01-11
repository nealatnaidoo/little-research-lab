from uuid import uuid4

import pytest

from src.adapters.sqlite.migrator import SQLiteMigrator
from src.adapters.sqlite.repos import SQLiteUserRepo
from src.domain.entities import User


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_user.db")

@pytest.fixture
def repo(db_path):
    migrator = SQLiteMigrator(db_path, "migrations")
    migrator.run_migrations()
    return SQLiteUserRepo(db_path)

def test_save_and_get_user(repo):
    uid = uuid4()
    user = User(
        id=uid,
        email="test@example.com",
        display_name="Test User",
        password_hash="hashed_secret",
        roles=["editor"],
        status="active"
    )
    
    repo.save(user)
    
    fetched = repo.get_by_id(uid)
    assert fetched is not None
    assert fetched.email == "test@example.com"
    assert fetched.display_name == "Test User"
    assert fetched.roles == ["editor"]
    assert fetched.status == "active"
    
    # Check email fetch
    fetched_email = repo.get_by_email("test@example.com")
    assert fetched_email is not None
    assert fetched_email.id == uid

def test_get_missing_user(repo):
    assert repo.get_by_id(uuid4()) is None
    assert repo.get_by_email("missing@example.com") is None

def test_update_user(repo):
    uid = uuid4()
    user = User(
        id=uid, email="update@example.com", display_name="Old", password_hash="h"
    )
    repo.save(user)
    
    user.display_name = "New"
    user.roles = ["admin"]
    repo.save(user)
    
    fetched = repo.get_by_id(uid)
    assert fetched.display_name == "New"
    assert "admin" in fetched.roles
