#!/usr/bin/env python3
"""
Restore Drill Script (NFR-R2, T-0048).

Verifies that backups can be successfully restored.

This script performs a "drill" restore to a temporary location,
verifies the data integrity, and cleans up. It does NOT modify
the production data.

Spec refs: NFR-R2, TA-0050
Test assertions:
- TA-0050: Restore drill verifies backup integrity

Usage:
    python scripts/restore_drill.py --backup ./backups/
    python scripts/restore_drill.py --manifest ./backups/backup_manifest_*.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tarfile
import tempfile
from pathlib import Path

# --- Verification Functions ---


def get_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_database_backup(backup_path: Path, expected_hash: str | None) -> dict:
    """
    Verify database backup can be restored.

    Tests:
    1. File can be opened as SQLite database
    2. Schema is valid (can query tables)
    3. Hash matches (if provided)
    """
    results = {
        "file": str(backup_path),
        "checks": [],
        "success": True,
    }

    # Check 1: Hash verification
    if expected_hash:
        actual_hash = get_file_hash(backup_path)
        hash_ok = actual_hash == expected_hash
        results["checks"].append(
            {
                "name": "hash_verification",
                "passed": hash_ok,
                "expected": expected_hash,
                "actual": actual_hash,
            }
        )
        if not hash_ok:
            results["success"] = False

    # Check 2: Can open as SQLite
    try:
        conn = sqlite3.connect(str(backup_path))
        cursor = conn.cursor()

        # Check 3: Can query schema
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        results["checks"].append(
            {
                "name": "sqlite_open",
                "passed": True,
                "tables_found": len(tables),
                "tables": tables,
            }
        )

        # Check 4: Has expected tables
        expected_tables = {"users", "content", "assets"}
        found_tables = set(tables)
        has_expected = expected_tables.issubset(found_tables)

        results["checks"].append(
            {
                "name": "schema_valid",
                "passed": has_expected,
                "expected_tables": list(expected_tables),
                "found_tables": tables,
            }
        )
        if not has_expected:
            results["success"] = False

    except sqlite3.Error as e:
        results["checks"].append(
            {
                "name": "sqlite_open",
                "passed": False,
                "error": str(e),
            }
        )
        results["success"] = False

    return results


def verify_assets_backup(
    backup_path: Path,
    expected_hash: str | None,
    temp_dir: Path,
) -> dict:
    """
    Verify assets backup can be restored.

    Tests:
    1. Archive can be extracted
    2. Files are not corrupted
    3. Hash matches (if provided)
    """
    results = {
        "file": str(backup_path),
        "checks": [],
        "success": True,
    }

    # Check 1: Hash verification
    if expected_hash:
        actual_hash = get_file_hash(backup_path)
        hash_ok = actual_hash == expected_hash
        results["checks"].append(
            {
                "name": "hash_verification",
                "passed": hash_ok,
                "expected": expected_hash,
                "actual": actual_hash,
            }
        )
        if not hash_ok:
            results["success"] = False

    # Check 2: Can extract archive
    try:
        with tarfile.open(str(backup_path), "r:gz") as tar:
            members = tar.getmembers()
            file_count = len([m for m in members if m.isfile()])

            # Extract to temp dir
            tar.extractall(str(temp_dir))

        results["checks"].append(
            {
                "name": "extract_archive",
                "passed": True,
                "file_count": file_count,
            }
        )

        # Check 3: Extracted files exist
        extracted_files = list(temp_dir.rglob("*"))
        extracted_file_count = len([f for f in extracted_files if f.is_file()])

        results["checks"].append(
            {
                "name": "files_extracted",
                "passed": extracted_file_count == file_count,
                "expected": file_count,
                "actual": extracted_file_count,
            }
        )

    except tarfile.TarError as e:
        results["checks"].append(
            {
                "name": "extract_archive",
                "passed": False,
                "error": str(e),
            }
        )
        results["success"] = False

    return results


def run_restore_drill(
    backup_dir: str | None = None,
    manifest_path: str | None = None,
) -> dict:
    """
    Run restore drill procedure.

    Returns drill report dict.
    """
    report = {
        "success": True,
        "verifications": [],
        "errors": [],
    }

    # Find manifest
    if manifest_path:
        manifest_file = Path(manifest_path)
    elif backup_dir:
        backup_path = Path(backup_dir)
        # Find most recent manifest
        manifests = sorted(backup_path.glob("backup_manifest_*.json"), reverse=True)
        if not manifests:
            report["success"] = False
            report["errors"].append(f"No manifest found in {backup_dir}")
            return report
        manifest_file = manifests[0]
    else:
        report["success"] = False
        report["errors"].append("Must specify --backup or --manifest")
        return report

    print(f"Using manifest: {manifest_file}")

    # Load manifest
    try:
        with open(manifest_file) as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        report["success"] = False
        report["errors"].append(f"Failed to load manifest: {e}")
        return report

    print(f"Backup timestamp: {manifest['timestamp_utc']}")
    print(f"Backups to verify: {len(manifest['backups'])}")
    print()

    # Create temp directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for backup_info in manifest["backups"]:
            backup_path = Path(backup_info["backup"])
            expected_hash = backup_info.get("sha256")

            if not backup_path.exists():
                report["verifications"].append(
                    {
                        "type": backup_info["type"],
                        "file": str(backup_path),
                        "success": False,
                        "error": "File not found",
                    }
                )
                report["success"] = False
                continue

            print(f"Verifying {backup_info['type']}: {backup_path.name}")

            if backup_info["type"] == "database":
                result = verify_database_backup(backup_path, expected_hash)
            elif backup_info["type"] == "assets":
                assets_temp = temp_path / "assets"
                assets_temp.mkdir()
                result = verify_assets_backup(backup_path, expected_hash, assets_temp)
            else:
                result = {
                    "file": str(backup_path),
                    "success": False,
                    "error": f"Unknown backup type: {backup_info['type']}",
                }

            report["verifications"].append(result)

            # Print check results
            for check in result.get("checks", []):
                status = "PASS" if check["passed"] else "FAIL"
                print(f"  [{status}] {check['name']}")

            if not result["success"]:
                report["success"] = False

            print()

    return report


# --- CLI ---


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Verify backup integrity with a restore drill.")
    parser.add_argument(
        "--backup",
        help="Backup directory to verify",
    )
    parser.add_argument(
        "--manifest",
        help="Specific manifest file to use",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    if not args.json:
        print("=" * 60)
        print("Little Research Lab: Restore Drill")
        print("=" * 60)
        print()

    report = run_restore_drill(
        backup_dir=args.backup,
        manifest_path=args.manifest,
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("=" * 60)
        if report["success"]:
            print("RESTORE DRILL PASSED: All backups verified successfully!")
            return 0
        else:
            print("RESTORE DRILL FAILED: Some verifications failed.")
            if report["errors"]:
                print("\nErrors:")
                for error in report["errors"]:
                    print(f"  - {error}")
            return 1


if __name__ == "__main__":
    exit(main())
