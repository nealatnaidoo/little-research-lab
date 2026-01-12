import sqlite3
from datetime import datetime
from uuid import uuid4

import pytest

from src.adapters.sqlite.migrator import SQLiteMigrator
from src.adapters.sqlite.repos import SQLiteContentRepo
from src.domain.entities import ContentBlock, ContentItem


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def migrator(db_path):
    return SQLiteMigrator(db_path, "migrations")


@pytest.fixture
def repo(db_path, migrator):
    migrator.run_migrations()
    return SQLiteContentRepo(db_path)


@pytest.fixture
def user_repo(db_path):
    conn = sqlite3.connect(db_path)
    uid = str(uuid4())
    conn.execute(
        "INSERT INTO users "
        "(id, email, display_name, password_hash, status, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            uid,
            "test@example.com",
            "Test User",
            "hash",
            "active",
            datetime.now().isoformat(),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return uid


def test_save_and_get_content(repo, user_repo):
    item_id = uuid4()
    owner_id = user_repo

    item = ContentItem(
        id=item_id,
        type="post",
        slug="test-slug",
        title="Test Title",
        summary="Summary",
        status="draft",  # Using string literal
        owner_user_id=owner_id,
        visibility="private",  # Using string literal
        blocks=[
            ContentBlock(block_type="markdown", data_json={"text": "Hello"}),
            ContentBlock(block_type="image", data_json={"asset_id": str(uuid4())}),
        ],
    )

    repo.save(item)

    fetched = repo.get_by_id(item_id)
    assert fetched is not None
    assert fetched.title == "Test Title"
    assert len(fetched.blocks) == 2
    assert fetched.blocks[0].data_json["text"] == "Hello"


def test_update_content(repo, user_repo):
    item_id = uuid4()
    item = ContentItem(
        id=item_id,
        type="post",
        slug="update-slug",
        title="Original",
        status="draft",
        owner_user_id=user_repo,
        visibility="private",
    )
    repo.save(item)

    item.title = "Updated"
    repo.save(item)

    fetched = repo.get_by_id(item_id)
    assert fetched.title == "Updated"


def test_delete_content(repo, user_repo):
    item_id = uuid4()
    item = ContentItem(
        id=item_id,
        type="post",
        slug="del-slug",
        title="Del",
        status="draft",
        owner_user_id=user_repo,
        visibility="private",
    )
    repo.save(item)

    repo.delete(item_id)
    assert repo.get_by_id(item_id) is None
