from uuid import uuid4

import pytest

from src.adapters.sqlite.migrator import SQLiteMigrator
from src.adapters.sqlite.repos import SQLiteLinkRepo
from src.domain.entities import LinkItem


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_links.db")

@pytest.fixture
def migrator(db_path):
    return SQLiteMigrator(db_path, "migrations")

@pytest.fixture
def repo(db_path, migrator):
    migrator.run_migrations()
    return SQLiteLinkRepo(db_path)

def test_save_and_list_links(repo):
    link = LinkItem(
        id=uuid4(),
        slug="google",
        title="Google",
        url="https://google.com",
        icon="icon",
        status="active",
        position=0,
        visibility="public"
    )
    
    saved = repo.save(link)
    assert saved == link
    
    all_links = repo.get_all()
    assert len(all_links) == 1
    assert all_links[0].title == "Google"

def test_delete_link(repo):
    link = LinkItem(
        id=uuid4(),
        slug="del",
        title="Delete Me",
        url="https://del.com",
        icon="icon",
        status="active",
        position=1,
        visibility="private"
    )
    repo.save(link)
    assert len(repo.get_all()) == 1
    
    repo.delete(link.id)
    assert len(repo.get_all()) == 0
