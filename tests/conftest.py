import os
import sqlite3
from pathlib import Path

import pytest

from src.adapters.sqlite.migrator import SQLiteMigrator
from src.rules.loader import load_rules
from src.ui.context import ServiceContext


@pytest.fixture
def test_data_dir(tmp_path):
    return str(tmp_path)


@pytest.fixture
def test_ctx(test_data_dir):
    """
    Creates a full ServiceContext backed by a temporary SQLite DB and FileStore.
    """
    db_path = os.path.join(test_data_dir, "lrl.db")

    # 1. Migrations
    migrator = SQLiteMigrator(db_path, "migrations")
    migrator.run_migrations()

    # 2. Config/Rules - Load REAL rules from project root
    # Assuming tests run from project root.
    rules_path = Path("rules.yaml").resolve()
    if not rules_path.exists():
        # Fallback for when running in IDE / weird cwd?
        # Or just fail fast.
        raise FileNotFoundError(f"Rules not found at {rules_path}")

    rules = load_rules(rules_path)

    # 3. Create Admin User manually
    conn = sqlite3.connect(db_path)
    # Be careful with created_at format (sqlite adapter usually expects isoformat)
    from uuid import uuid4

    admin_id = str(uuid4())

    conn.execute(
        "INSERT INTO users "
        "(id, email, display_name, password_hash, status, created_at, updated_at) "
        "VALUES (?, 'admin@example.com', 'Admin', 'hash', 'active', "
        "'2025-01-01T00:00:00', '2025-01-01T00:00:00')",
        (admin_id,),
    )
    # Role - map admin to 'owner' for full access in tests.
    conn.execute(
        "INSERT INTO role_assignments (id, user_id, role, created_at) "
        "VALUES (?, ?, 'owner', '2025-01-01T00:00:00')",
        (str(uuid4()), admin_id),
    )
    conn.commit()
    conn.close()

    # 4. Context
    fs_path = os.path.join(test_data_dir, "filestore")
    os.makedirs(fs_path, exist_ok=True)

    ctx = ServiceContext.create(db_path=db_path, fs_path=fs_path, rules=rules)
    return ctx
    return ctx
