import sqlite3

import pytest

from src.adapters.sqlite.migrator import SQLiteMigrator


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_db.sqlite")

@pytest.fixture
def migrations_dir():
    # Use the real migrations directory or a mocked one?
    # Real one is better to test actual SQL validity too.
    return "migrations"

def test_migrator_creates_migration_table(temp_db_path, migrations_dir):
    migrator = SQLiteMigrator(temp_db_path, migrations_dir)
    migrator.run_migrations()
    
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations'"
    )
    assert cursor.fetchone() is not None
    conn.close()

def test_migrator_applies_initial(temp_db_path, migrations_dir):
    migrator = SQLiteMigrator(temp_db_path, migrations_dir)
    migrator.run_migrations()
    
    conn = sqlite3.connect(temp_db_path)
    
    # Check users table exists
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    assert cursor.fetchone() is not None

    # Check _migrations has record
    cursor = conn.execute("SELECT filename FROM _migrations WHERE filename='001_initial.sql'")
    assert cursor.fetchone() is not None
    
    conn.close()

def test_migrator_is_idempotent(temp_db_path, migrations_dir):
    migrator = SQLiteMigrator(temp_db_path, migrations_dir)
    
    # Run twice
    migrator.run_migrations()
    migrator.run_migrations()
    
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.execute("SELECT count(*) FROM _migrations WHERE filename='001_initial.sql'")
    assert cursor.fetchone()[0] == 1
    conn.close()
