import os
import sys
from datetime import datetime
from uuid import uuid4

# Add root to pythonpath
sys.path.append(os.getcwd())

from src.adapters.sqlite.repos import SQLiteUserRepo
from src.api.auth_utils import get_password_hash
from src.domain.entities import User


def seed():
    data_dir = os.environ.get("LAB_DATA_DIR", "./data")
    os.makedirs(data_dir, exist_ok=True)

    db_path = f"{data_dir}/lrl.db"
    print(f"Seeding to {db_path}")

    # Initialize DB (create tables if needed) - The repos assume tables exist?
    # Usually migrations create tables.
    # For this pure-python-sqlite repo, we might need DDL.
    # Let's assume schema.sql exists or we need to run it.
    # T-0047/Basic: Did we create schema?
    # I recall I only wrote Repos, assuming tables exist.
    # The `SQLiteContentRepo` doesn't create tables.
    # I might need to initialize the DB schema first!

    conn = SQLiteUserRepo(db_path)._get_conn()
    cursor = conn.cursor()

    # Simple DDL for MVP
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE,
        display_name TEXT,
        password_hash TEXT,
        status TEXT,
        created_at TEXT,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS role_assignments (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        role TEXT,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS content_items (
        id TEXT PRIMARY KEY,
        type TEXT,
        slug TEXT,
        title TEXT,
        summary TEXT,
        status TEXT,
        publish_at TEXT,
        published_at TEXT,
        owner_user_id TEXT,
        visibility TEXT,
        created_at TEXT,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS content_blocks (
        id TEXT PRIMARY KEY,
        content_item_id TEXT,
        block_type TEXT,
        data_json TEXT, -- JSON
        position INTEGER,
        FOREIGN KEY(content_item_id) REFERENCES content_items(id)
    );
    CREATE TABLE IF NOT EXISTS assets (
        id TEXT PRIMARY KEY,
        filename_original TEXT,
        mime_type TEXT,
        size_bytes INTEGER,
        sha256 TEXT,
        storage_path TEXT,
        visibility TEXT,
        created_by_user_id TEXT,
        created_at TEXT
    );
    """)
    conn.commit()

    repo = SQLiteUserRepo(db_path)
    email = "admin@example.com"

    existing = repo.get_by_email(email)
    if not existing:
        u = User(
            id=uuid4(),
            email=email,
            display_name="Admin",
            password_hash=get_password_hash("changeme"),
            roles=["admin"],
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        repo.save(u)
        print(f"Created user: {email} / changeme")
    else:
        print(f"User {email} already exists")


if __name__ == "__main__":
    seed()
