"""
Tests for Backup and Restore Scripts (NFR-R2, T-0048).

Test assertions:
- TA-0050: Backup creates valid archives
- TA-0050: Restore drill verifies backup integrity
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tarfile
from pathlib import Path

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from backup import (
    backup_assets,
    backup_database,
    create_manifest,
    get_file_hash,
    run_backup,
)
from restore_drill import (
    run_restore_drill,
    verify_assets_backup,
    verify_database_backup,
)

# --- Fixtures ---


@pytest.fixture
def sample_db(tmp_path: Path) -> Path:
    """Create a sample SQLite database."""
    db_path = tmp_path / "data" / "lrl.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create sample schema
    cursor.execute("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            email TEXT,
            name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE content (
            id TEXT PRIMARY KEY,
            title TEXT,
            body TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE assets (
            id TEXT PRIMARY KEY,
            filename TEXT
        )
    """)

    # Insert sample data
    cursor.execute("INSERT INTO users VALUES ('u1', 'test@example.com', 'Test User')")
    cursor.execute("INSERT INTO content VALUES ('c1', 'Test Post', 'Body content')")

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def sample_assets(tmp_path: Path) -> Path:
    """Create sample assets directory."""
    assets_path = tmp_path / "data" / "assets"
    assets_path.mkdir(parents=True, exist_ok=True)

    # Create sample files
    (assets_path / "file1.txt").write_text("Content 1")
    (assets_path / "file2.pdf").write_bytes(b"PDF content")

    subdir = assets_path / "subdir"
    subdir.mkdir()
    (subdir / "file3.jpg").write_bytes(b"JPG content")

    return assets_path


@pytest.fixture
def sample_data_dir(sample_db: Path, sample_assets: Path) -> Path:
    """Get data directory with database and assets."""
    return sample_db.parent


# --- get_file_hash Tests ---


class TestGetFileHash:
    """Tests for file hash calculation."""

    def test_hash_consistent(self, tmp_path: Path) -> None:
        """Hash is consistent for same content."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Hello, World!")

        hash1 = get_file_hash(file_path)
        hash2 = get_file_hash(file_path)

        assert hash1 == hash2

    def test_hash_different_for_different_content(self, tmp_path: Path) -> None:
        """Hash differs for different content."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("Content A")
        file2.write_text("Content B")

        assert get_file_hash(file1) != get_file_hash(file2)

    def test_hash_is_sha256(self, tmp_path: Path) -> None:
        """Hash is SHA256 format (64 hex chars)."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("test")

        file_hash = get_file_hash(file_path)

        assert len(file_hash) == 64
        assert all(c in "0123456789abcdef" for c in file_hash)


# --- backup_database Tests ---


class TestBackupDatabase:
    """Tests for database backup."""

    def test_backup_creates_file(self, sample_db: Path, tmp_path: Path) -> None:
        """TA-0050: Backup creates database file."""
        output_dir = tmp_path / "backups"
        output_dir.mkdir()

        result = backup_database(sample_db, output_dir, "20250101_120000")

        assert Path(result["backup"]).exists()
        assert result["type"] == "database"

    def test_backup_is_valid_sqlite(self, sample_db: Path, tmp_path: Path) -> None:
        """TA-0050: Backup is valid SQLite database."""
        output_dir = tmp_path / "backups"
        output_dir.mkdir()

        result = backup_database(sample_db, output_dir, "20250101_120000")
        backup_path = Path(result["backup"])

        # Should be openable as SQLite
        conn = sqlite3.connect(str(backup_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()

        assert len(tables) > 0

    def test_backup_contains_data(self, sample_db: Path, tmp_path: Path) -> None:
        """TA-0050: Backup contains original data."""
        output_dir = tmp_path / "backups"
        output_dir.mkdir()

        result = backup_database(sample_db, output_dir, "20250101_120000")
        backup_path = Path(result["backup"])

        conn = sqlite3.connect(str(backup_path))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        conn.close()

        assert len(users) == 1
        assert users[0][1] == "test@example.com"

    def test_backup_includes_hash(self, sample_db: Path, tmp_path: Path) -> None:
        """TA-0050: Backup result includes SHA256 hash."""
        output_dir = tmp_path / "backups"
        output_dir.mkdir()

        result = backup_database(sample_db, output_dir, "20250101_120000")

        assert "sha256" in result
        assert len(result["sha256"]) == 64


# --- backup_assets Tests ---


class TestBackupAssets:
    """Tests for assets backup."""

    def test_backup_creates_archive(self, sample_assets: Path, tmp_path: Path) -> None:
        """TA-0050: Backup creates archive file."""
        output_dir = tmp_path / "backups"
        output_dir.mkdir()

        result = backup_assets(sample_assets, output_dir, "20250101_120000")

        assert Path(result["backup"]).exists()
        assert result["type"] == "assets"
        assert result["backup"].endswith(".tar.gz")

    def test_backup_contains_all_files(self, sample_assets: Path, tmp_path: Path) -> None:
        """TA-0050: Backup contains all asset files."""
        output_dir = tmp_path / "backups"
        output_dir.mkdir()

        result = backup_assets(sample_assets, output_dir, "20250101_120000")

        # 3 files: file1.txt, file2.pdf, subdir/file3.jpg
        assert result["file_count"] == 3

    def test_backup_is_extractable(self, sample_assets: Path, tmp_path: Path) -> None:
        """TA-0050: Backup archive can be extracted."""
        output_dir = tmp_path / "backups"
        output_dir.mkdir()

        result = backup_assets(sample_assets, output_dir, "20250101_120000")
        backup_path = Path(result["backup"])

        # Extract to temp location
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        with tarfile.open(str(backup_path), "r:gz") as tar:
            tar.extractall(str(extract_dir))

        # Files should exist
        extracted_files = list(extract_dir.rglob("*"))
        assert len([f for f in extracted_files if f.is_file()]) == 3


# --- create_manifest Tests ---


class TestCreateManifest:
    """Tests for manifest creation."""

    def test_creates_manifest_file(self, tmp_path: Path) -> None:
        """Manifest file is created."""
        backups = [{"type": "database", "backup": "/path/to/db"}]

        manifest_path = create_manifest(tmp_path, "20250101_120000", backups)

        assert manifest_path.exists()
        assert "backup_manifest_" in manifest_path.name

    def test_manifest_is_valid_json(self, tmp_path: Path) -> None:
        """Manifest is valid JSON."""
        backups = [{"type": "database", "backup": "/path/to/db", "sha256": "abc"}]

        manifest_path = create_manifest(tmp_path, "20250101_120000", backups)

        with open(manifest_path) as f:
            data = json.load(f)

        assert "timestamp_utc" in data
        assert "backups" in data
        assert data["backups"] == backups


# --- run_backup Tests ---


class TestRunBackup:
    """Tests for full backup procedure."""

    def test_full_backup(self, sample_data_dir: Path, tmp_path: Path) -> None:
        """TA-0050: Full backup creates all files."""
        backup_dir = tmp_path / "backups"

        report = run_backup(
            data_dir=str(sample_data_dir),
            backup_dir=str(backup_dir),
        )

        assert report["success"]
        assert len(report["backups"]) == 2  # db + assets
        assert backup_dir.exists()

    def test_db_only_backup(self, sample_data_dir: Path, tmp_path: Path) -> None:
        """Database-only backup works."""
        backup_dir = tmp_path / "backups"

        report = run_backup(
            data_dir=str(sample_data_dir),
            backup_dir=str(backup_dir),
            db_only=True,
        )

        assert report["success"]
        assert len(report["backups"]) == 1
        assert report["backups"][0]["type"] == "database"

    def test_assets_only_backup(self, sample_data_dir: Path, tmp_path: Path) -> None:
        """Assets-only backup works."""
        backup_dir = tmp_path / "backups"

        report = run_backup(
            data_dir=str(sample_data_dir),
            backup_dir=str(backup_dir),
            assets_only=True,
        )

        assert report["success"]
        assert len(report["backups"]) == 1
        assert report["backups"][0]["type"] == "assets"


# --- verify_database_backup Tests ---


class TestVerifyDatabaseBackup:
    """Tests for database verification."""

    def test_valid_backup_passes(self, sample_db: Path, tmp_path: Path) -> None:
        """Valid database backup passes verification."""
        output_dir = tmp_path / "backups"
        output_dir.mkdir()

        backup_result = backup_database(sample_db, output_dir, "20250101_120000")
        backup_path = Path(backup_result["backup"])

        verify_result = verify_database_backup(backup_path, backup_result["sha256"])

        assert verify_result["success"]

    def test_wrong_hash_fails(self, sample_db: Path, tmp_path: Path) -> None:
        """Wrong hash fails verification."""
        output_dir = tmp_path / "backups"
        output_dir.mkdir()

        backup_result = backup_database(sample_db, output_dir, "20250101_120000")
        backup_path = Path(backup_result["backup"])

        verify_result = verify_database_backup(backup_path, "wrong_hash")

        assert not verify_result["success"]

    def test_corrupt_db_fails(self, tmp_path: Path) -> None:
        """Corrupt database fails verification."""
        fake_db = tmp_path / "corrupt.db"
        fake_db.write_text("not a database")

        verify_result = verify_database_backup(fake_db, None)

        assert not verify_result["success"]


# --- verify_assets_backup Tests ---


class TestVerifyAssetsBackup:
    """Tests for assets verification."""

    def test_valid_backup_passes(self, sample_assets: Path, tmp_path: Path) -> None:
        """Valid assets backup passes verification."""
        output_dir = tmp_path / "backups"
        output_dir.mkdir()
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        backup_result = backup_assets(sample_assets, output_dir, "20250101_120000")
        backup_path = Path(backup_result["backup"])

        verify_result = verify_assets_backup(backup_path, backup_result["sha256"], extract_dir)

        assert verify_result["success"]

    def test_wrong_hash_fails(self, sample_assets: Path, tmp_path: Path) -> None:
        """Wrong hash fails verification."""
        output_dir = tmp_path / "backups"
        output_dir.mkdir()
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        backup_result = backup_assets(sample_assets, output_dir, "20250101_120000")
        backup_path = Path(backup_result["backup"])

        verify_result = verify_assets_backup(backup_path, "wrong_hash", extract_dir)

        assert not verify_result["success"]


# --- run_restore_drill Tests ---


class TestRunRestoreDrill:
    """Tests for full restore drill."""

    def test_drill_passes_valid_backup(self, sample_data_dir: Path, tmp_path: Path) -> None:
        """TA-0050: Restore drill passes for valid backup."""
        backup_dir = tmp_path / "backups"

        # Create backup
        run_backup(
            data_dir=str(sample_data_dir),
            backup_dir=str(backup_dir),
        )

        # Run drill
        drill_report = run_restore_drill(backup_dir=str(backup_dir))

        assert drill_report["success"]
        assert len(drill_report["verifications"]) == 2

    def test_drill_fails_missing_manifest(self, tmp_path: Path) -> None:
        """Drill fails when manifest is missing."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        drill_report = run_restore_drill(backup_dir=str(empty_dir))

        assert not drill_report["success"]
        assert len(drill_report["errors"]) > 0

    def test_drill_without_args_fails(self) -> None:
        """Drill without arguments fails gracefully."""
        drill_report = run_restore_drill()

        assert not drill_report["success"]
