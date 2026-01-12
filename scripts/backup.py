#!/usr/bin/env python3
"""
Backup Script (NFR-R2, T-0048).

Creates timestamped backups of the database and assets.

Spec refs: NFR-R2, TA-0050
Test assertions:
- TA-0050: Backup creates valid archives

Usage:
    python scripts/backup.py                    # Backup to ./backups/
    python scripts/backup.py --out /path/to/   # Backup to custom path
    python scripts/backup.py --db-only         # Database only
    python scripts/backup.py --assets-only     # Assets only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tarfile
from datetime import UTC, datetime
from pathlib import Path

# --- Configuration ---

DEFAULT_DATA_DIR = os.environ.get("LAB_DATA_DIR", "./data")
DEFAULT_BACKUP_DIR = "./backups"
DB_FILENAME = "lrl.db"
ASSETS_DIRNAME = "assets"


# --- Backup Functions ---


def get_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def backup_database(
    db_path: Path,
    output_dir: Path,
    timestamp: str,
) -> dict[str, str]:
    """
    Backup SQLite database using online backup.

    Uses SQLite backup API to create a consistent copy.
    """
    backup_name = f"lrl_db_{timestamp}.sqlite"
    backup_path = output_dir / backup_name

    # Use SQLite backup API for consistency
    source = sqlite3.connect(str(db_path))
    dest = sqlite3.connect(str(backup_path))

    try:
        source.backup(dest)
    finally:
        source.close()
        dest.close()

    # Calculate hash for verification
    file_hash = get_file_hash(backup_path)

    return {
        "type": "database",
        "source": str(db_path),
        "backup": str(backup_path),
        "size_bytes": backup_path.stat().st_size,
        "sha256": file_hash,
    }


def backup_assets(
    assets_dir: Path,
    output_dir: Path,
    timestamp: str,
) -> dict[str, str]:
    """
    Backup assets directory as a compressed tarball.

    Creates a .tar.gz archive of all assets.
    """
    backup_name = f"lrl_assets_{timestamp}.tar.gz"
    backup_path = output_dir / backup_name

    # Count files for report
    file_count = 0
    total_size = 0

    with tarfile.open(str(backup_path), "w:gz") as tar:
        for item in assets_dir.rglob("*"):
            if item.is_file():
                file_count += 1
                total_size += item.stat().st_size
                # Add with relative path from assets dir
                arcname = item.relative_to(assets_dir.parent)
                tar.add(str(item), arcname=str(arcname))

    # Calculate hash for verification
    file_hash = get_file_hash(backup_path)

    return {
        "type": "assets",
        "source": str(assets_dir),
        "backup": str(backup_path),
        "file_count": file_count,
        "total_source_size_bytes": total_size,
        "archive_size_bytes": backup_path.stat().st_size,
        "sha256": file_hash,
    }


def create_manifest(
    output_dir: Path,
    timestamp: str,
    backups: list[dict],
) -> Path:
    """Create a manifest file with backup metadata."""
    manifest_path = output_dir / f"backup_manifest_{timestamp}.json"

    manifest = {
        "timestamp_utc": timestamp,
        "created_at": datetime.now(UTC).isoformat(),
        "version": "1.0",
        "backups": backups,
    }

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest_path


def run_backup(
    data_dir: str = DEFAULT_DATA_DIR,
    backup_dir: str = DEFAULT_BACKUP_DIR,
    db_only: bool = False,
    assets_only: bool = False,
) -> dict:
    """
    Run full backup procedure.

    Returns backup report dict.
    """
    data_path = Path(data_dir)
    output_path = Path(backup_dir)

    # Create backup directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate timestamp
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    backups = []

    # Backup database
    if not assets_only:
        db_path = data_path / DB_FILENAME
        if db_path.exists():
            print(f"Backing up database: {db_path}")
            result = backup_database(db_path, output_path, timestamp)
            backups.append(result)
            print(f"  -> {result['backup']} ({result['size_bytes']} bytes)")
        else:
            print(f"Warning: Database not found at {db_path}")

    # Backup assets
    if not db_only:
        assets_path = data_path / ASSETS_DIRNAME
        if assets_path.exists():
            print(f"Backing up assets: {assets_path}")
            result = backup_assets(assets_path, output_path, timestamp)
            backups.append(result)
            print(
                f"  -> {result['backup']} "
                f"({result['file_count']} files, {result['archive_size_bytes']} bytes)"
            )
        else:
            print(f"Warning: Assets directory not found at {assets_path}")

    # Create manifest
    if backups:
        manifest_path = create_manifest(output_path, timestamp, backups)
        print(f"\nManifest: {manifest_path}")

    report = {
        "success": len(backups) > 0,
        "timestamp": timestamp,
        "backup_dir": str(output_path),
        "backups": backups,
    }

    return report


# --- CLI ---


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Create backups of Little Research Lab data.")
    parser.add_argument(
        "--data-dir",
        default=DEFAULT_DATA_DIR,
        help=f"Source data directory (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_BACKUP_DIR,
        help=f"Output backup directory (default: {DEFAULT_BACKUP_DIR})",
    )
    parser.add_argument(
        "--db-only",
        action="store_true",
        help="Only backup database",
    )
    parser.add_argument(
        "--assets-only",
        action="store_true",
        help="Only backup assets",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    print("=" * 60)
    print("Little Research Lab: Backup")
    print("=" * 60)
    print()

    report = run_backup(
        data_dir=args.data_dir,
        backup_dir=args.out,
        db_only=args.db_only,
        assets_only=args.assets_only,
    )

    print()
    if report["success"]:
        print("Backup completed successfully!")
        print(f"Backup directory: {report['backup_dir']}")
        return 0
    else:
        print("No backups created.")
        return 1


if __name__ == "__main__":
    exit(main())
