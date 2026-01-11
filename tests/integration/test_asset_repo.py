from datetime import datetime
from uuid import uuid4

import pytest

from src.adapters.sqlite.migrator import SQLiteMigrator
from src.adapters.sqlite.repos import SQLiteAssetRepo
from src.domain.entities import Asset


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_asset.db")

@pytest.fixture
def repo(db_path):
    migrator = SQLiteMigrator(db_path, "migrations")
    migrator.run_migrations()
    return SQLiteAssetRepo(db_path)

@pytest.fixture
def user_id(db_path):
    import sqlite3
    from uuid import UUID
    conn = sqlite3.connect(db_path)
    uid = str(uuid4())
    conn.execute(
        "INSERT INTO users (id, email, display_name, password_hash, status, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", 
        (
            uid, "owner@example.com", "Owner", "hash", "active", 
            datetime.utcnow().isoformat(), datetime.utcnow().isoformat()
        )
    )
    conn.commit()
    conn.close()
    return UUID(uid)

def test_save_and_get_asset(repo, user_id):
    uid = uuid4()
    asset = Asset(
        id=uid,
        filename_original="test.png",
        mime_type="image/png",
        size_bytes=1024,
        sha256="deadbeef",
        storage_path="assets/deadbeef.png",
        visibility="private",
        created_by_user_id=user_id,
        created_at=datetime.utcnow()
    )
    
    repo.save(asset)
    
    fetched = repo.get_by_id(uid)
    assert fetched is not None
    assert fetched.filename_original == "test.png"
    assert fetched.mime_type == "image/png"
    assert fetched.size_bytes == 1024
    
def test_list_assets(repo, user_id):
    a1 = Asset(
        id=uuid4(), filename_original="a1.png", mime_type="x", size_bytes=1, 
        sha256="a", storage_path="p1", created_by_user_id=user_id
    )
    a2 = Asset(
        id=uuid4(), filename_original="a2.png", mime_type="x", size_bytes=1, 
        sha256="b", storage_path="p2", created_by_user_id=user_id
    )
    
    repo.save(a1)
    repo.save(a2)
    
    assets = repo.list_assets()
    assert len(assets) == 2
    ids = [a.id for a in assets]
    assert a1.id in ids
    assert a2.id in ids

def test_upsert_asset(repo, user_id):
    uid = uuid4()
    asset = Asset(
        id=uid, filename_original="v1", mime_type="x", size_bytes=1, 
        sha256="a", storage_path="p", created_by_user_id=user_id
    )
    repo.save(asset)
    
    asset.filename_original = "v2"
    repo.save(asset)
    
    fetched = repo.get_by_id(uid)
    assert fetched.filename_original == "v2"
