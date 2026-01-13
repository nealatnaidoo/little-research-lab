"""
Integration tests for admin links API endpoints.

Tests the HTTP layer including authentication, request/response formatting.
"""

import os
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

# Set test database before importing app
os.environ["LAB_DATA_DIR"] = "/tmp/lrl_test"

from src.adapters.sqlite.repos import SQLiteLinkRepo, SQLiteUserRepo
from src.api.main import app
from src.domain.entities import User


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Set up test database directory and schema."""
    test_dir = Path("/tmp/lrl_test")
    test_dir.mkdir(parents=True, exist_ok=True)

    db_path = test_dir / "lrl.db"

    # Create database with schema
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create links table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS link_items (
            id TEXT PRIMARY KEY,
            slug TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            icon TEXT,
            status TEXT NOT NULL,
            position INTEGER NOT NULL,
            visibility TEXT NOT NULL,
            group_id TEXT
        )
    """)

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            email TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Create role_assignments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS role_assignments (
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            PRIMARY KEY (user_id, role)
        )
    """)

    conn.commit()
    conn.close()

    yield

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def db_path():
    """Test database path."""
    return "/tmp/lrl_test/lrl.db"


@pytest.fixture
def link_repo(db_path):
    """Create link repository."""
    return SQLiteLinkRepo(db_path)


@pytest.fixture
def user_repo(db_path):
    """Create user repository."""
    return SQLiteUserRepo(db_path)


@pytest.fixture
def test_user(user_repo):
    """Create test user."""
    user = User(
        id=uuid4(),
        username="testuser",
        email="test@example.com",
        display_name="Test User",
        password_hash="$2b$12$test",  # Mock hash
        status="active",
    )
    user_repo.save(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """Create auth token for test user."""
    from src.api.auth_utils import create_access_token

    return create_access_token({"sub": str(test_user.id)})


@pytest.fixture
def auth_headers(auth_token):
    """Create auth headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(autouse=True)
def clear_links(link_repo):
    """Clear all links before each test."""
    for link in link_repo.get_all():
        link_repo.delete(link.id)


@pytest.fixture(autouse=True)
def clear_users(db_path):
    """Clear all users before each test."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DELETE FROM role_assignments")
        conn.execute("DELETE FROM users")
        conn.commit()
    finally:
        conn.close()


# --- Authentication Tests ---


def test_list_links_requires_auth(client):
    """Test that listing links requires authentication."""
    response = client.get("/api/admin/links")

    assert response.status_code == 401


def test_create_link_requires_auth(client):
    """Test that creating links requires authentication."""
    response = client.post(
        "/api/admin/links",
        json={
            "title": "GitHub",
            "slug": "github",
            "url": "https://github.com/user",
        },
    )

    assert response.status_code == 401


def test_get_link_requires_auth(client):
    """Test that getting a link requires authentication."""
    link_id = str(uuid4())
    response = client.get(f"/api/admin/links/{link_id}")

    assert response.status_code == 401


def test_update_link_requires_auth(client):
    """Test that updating links requires authentication."""
    link_id = str(uuid4())
    response = client.put(
        f"/api/admin/links/{link_id}",
        json={"title": "New Title"},
    )

    assert response.status_code == 401


def test_delete_link_requires_auth(client):
    """Test that deleting links requires authentication."""
    link_id = str(uuid4())
    response = client.delete(f"/api/admin/links/{link_id}")

    assert response.status_code == 401


# --- List Links Tests ---


def test_list_links_empty(client, auth_headers):
    """Test listing links when none exist."""
    response = client.get("/api/admin/links", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_links_with_data(client, auth_headers, link_repo):
    """Test listing links."""
    from src.domain.entities import LinkItem

    # Create test links
    link1 = LinkItem(
        id=uuid4(),
        title="GitHub",
        slug="github",
        url="https://github.com/user",
        icon="github",
        status="active",
        position=1,
        visibility="public",
    )
    link2 = LinkItem(
        id=uuid4(),
        title="Twitter",
        slug="twitter",
        url="https://twitter.com/user",
        icon="twitter",
        status="active",
        position=2,
        visibility="public",
    )
    link_repo.save(link1)
    link_repo.save(link2)

    response = client.get("/api/admin/links", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # Check first link
    item1 = next(item for item in data["items"] if item["slug"] == "github")
    assert item1["title"] == "GitHub"
    assert item1["url"] == "https://github.com/user"
    assert item1["icon"] == "github"
    assert item1["status"] == "active"
    assert item1["position"] == 1
    assert item1["visibility"] == "public"


# --- Create Link Tests ---


def test_create_link_success(client, auth_headers):
    """Test creating a link successfully."""
    response = client.post(
        "/api/admin/links",
        headers=auth_headers,
        json={
            "title": "GitHub",
            "slug": "github",
            "url": "https://github.com/user",
            "icon": "github",
            "status": "active",
            "position": 1,
            "visibility": "public",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "GitHub"
    assert data["slug"] == "github"
    assert data["url"] == "https://github.com/user"
    assert data["icon"] == "github"
    assert data["status"] == "active"
    assert data["position"] == 1
    assert data["visibility"] == "public"
    assert "id" in data


def test_create_link_minimal_fields(client, auth_headers):
    """Test creating link with minimal fields."""
    response = client.post(
        "/api/admin/links",
        headers=auth_headers,
        json={
            "title": "GitHub",
            "slug": "github",
            "url": "https://github.com/user",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "GitHub"
    assert data["slug"] == "github"
    assert data["status"] == "active"  # default
    assert data["position"] == 0  # default
    assert data["visibility"] == "public"  # default


def test_create_link_validation_error_title(client, auth_headers):
    """Test creating link with invalid title."""
    response = client.post(
        "/api/admin/links",
        headers=auth_headers,
        json={
            "title": "",
            "slug": "github",
            "url": "https://github.com/user",
        },
    )

    assert response.status_code == 400
    errors = response.json()["detail"]
    assert len(errors) == 1
    assert errors[0]["code"] == "title_required"
    assert errors[0]["field"] == "title"


def test_create_link_validation_error_url(client, auth_headers):
    """Test creating link with invalid URL."""
    response = client.post(
        "/api/admin/links",
        headers=auth_headers,
        json={
            "title": "GitHub",
            "slug": "github",
            "url": "not-a-url",
        },
    )

    assert response.status_code == 400
    errors = response.json()["detail"]
    assert len(errors) == 1
    assert errors[0]["code"] == "url_invalid_scheme"


def test_create_link_duplicate_slug(client, auth_headers):
    """Test creating link with duplicate slug."""
    # Create first link
    client.post(
        "/api/admin/links",
        headers=auth_headers,
        json={
            "title": "GitHub",
            "slug": "github",
            "url": "https://github.com/user1",
        },
    )

    # Try to create second link with same slug
    response = client.post(
        "/api/admin/links",
        headers=auth_headers,
        json={
            "title": "GitHub 2",
            "slug": "github",
            "url": "https://github.com/user2",
        },
    )

    assert response.status_code == 400
    errors = response.json()["detail"]
    assert len(errors) == 1
    assert errors[0]["code"] == "slug_duplicate"


# --- Get Link Tests ---


def test_get_link_success(client, auth_headers, link_repo):
    """Test getting a link by ID."""
    from src.domain.entities import LinkItem

    # Create test link
    link = LinkItem(
        id=uuid4(),
        title="GitHub",
        slug="github",
        url="https://github.com/user",
        icon="github",
        status="active",
        position=1,
        visibility="public",
    )
    link_repo.save(link)

    response = client.get(
        f"/api/admin/links/{str(link.id)}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(link.id)
    assert data["title"] == "GitHub"
    assert data["slug"] == "github"


def test_get_link_not_found(client, auth_headers):
    """Test getting non-existent link."""
    link_id = str(uuid4())
    response = client.get(
        f"/api/admin/links/{link_id}",
        headers=auth_headers,
    )

    assert response.status_code == 404


# --- Update Link Tests ---


def test_update_link_success(client, auth_headers, link_repo):
    """Test updating a link."""
    from src.domain.entities import LinkItem

    # Create test link
    link = LinkItem(
        id=uuid4(),
        title="GitHub",
        slug="github",
        url="https://github.com/user",
        icon="github",
        status="active",
        position=1,
        visibility="public",
    )
    link_repo.save(link)

    # Update link
    response = client.put(
        f"/api/admin/links/{str(link.id)}",
        headers=auth_headers,
        json={
            "title": "GitHub Updated",
            "url": "https://github.com/newuser",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "GitHub Updated"
    assert data["url"] == "https://github.com/newuser"
    assert data["slug"] == "github"  # unchanged


def test_update_link_not_found(client, auth_headers):
    """Test updating non-existent link."""
    link_id = str(uuid4())
    response = client.put(
        f"/api/admin/links/{link_id}",
        headers=auth_headers,
        json={"title": "New Title"},
    )

    assert response.status_code == 404


def test_update_link_validation_error(client, auth_headers, link_repo):
    """Test updating link with invalid data."""
    from src.domain.entities import LinkItem

    # Create test link
    link = LinkItem(
        id=uuid4(),
        title="GitHub",
        slug="github",
        url="https://github.com/user",
        status="active",
        position=1,
        visibility="public",
    )
    link_repo.save(link)

    # Try to update with invalid URL
    response = client.put(
        f"/api/admin/links/{str(link.id)}",
        headers=auth_headers,
        json={"url": "not-a-url"},
    )

    assert response.status_code == 400
    errors = response.json()["detail"]
    assert len(errors) == 1
    assert errors[0]["code"] == "url_invalid_scheme"


# --- Delete Link Tests ---


def test_delete_link_success(client, auth_headers, link_repo):
    """Test deleting a link."""
    from src.domain.entities import LinkItem

    # Create test link
    link = LinkItem(
        id=uuid4(),
        title="GitHub",
        slug="github",
        url="https://github.com/user",
        status="active",
        position=1,
        visibility="public",
    )
    link_repo.save(link)

    # Delete link
    response = client.delete(
        f"/api/admin/links/{str(link.id)}",
        headers=auth_headers,
    )

    assert response.status_code == 204

    # Verify link is gone
    links = link_repo.get_all()
    assert len(links) == 0


def test_delete_link_not_found(client, auth_headers):
    """Test deleting non-existent link."""
    link_id = str(uuid4())
    response = client.delete(
        f"/api/admin/links/{link_id}",
        headers=auth_headers,
    )

    assert response.status_code == 404
