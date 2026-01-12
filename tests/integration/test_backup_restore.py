import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Paths relative to project root
PROJECT_ROOT = Path.cwd()


@pytest.fixture
def test_env(tmp_path):
    """
    Sets up a temporary environment with:
    - rules.yaml (copied)
    - dummy lrl.db
    - dummy filestore/
    """
    # Copy rules.yaml
    rules_src = PROJECT_ROOT / "rules.yaml"
    rules_dst = tmp_path / "rules.yaml"
    shutil.copy(rules_src, rules_dst)

    # Create dummy data
    db_path = tmp_path / "lrl.db"
    db_path.write_text("dummy database content")

    fs_path = tmp_path / "filestore"
    fs_path.mkdir()
    (fs_path / "test_asset.txt").write_text("dummy asset")

    # Environment for subprocess
    env = os.environ.copy()
    # Add project root to PYTHONPATH so src module is found
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    return tmp_path, env


def test_backup_and_restore_cycle(test_env):
    tmp_path, env = test_env

    # 1. Run Backup
    # python -m src.app_shell.cli backup
    result = subprocess.run(
        [sys.executable, "-m", "src.app_shell.cli", "backup"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Backup created" in result.stdout

    # Verify zip exists
    backup_dir = tmp_path / "backups"
    assert backup_dir.exists()
    zips = list(backup_dir.glob("backup_*.zip"))
    assert len(zips) == 1

    # 2. Simulate Disaster (Delete data)
    (tmp_path / "lrl.db").unlink()
    shutil.rmtree(tmp_path / "filestore")

    assert not (tmp_path / "lrl.db").exists()
    assert not (tmp_path / "filestore").exists()

    # 3. Run Restore
    # python -m src.app_shell.cli restore --latest
    result = subprocess.run(
        [sys.executable, "-m", "src.app_shell.cli", "restore", "--latest"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Restore complete" in result.stdout

    # 4. Verify Data Restored
    assert (tmp_path / "lrl.db").exists()
    assert (tmp_path / "lrl.db").read_text() == "dummy database content"
    assert (tmp_path / "filestore").exists()
    assert (tmp_path / "filestore" / "test_asset.txt").read_text() == "dummy asset"
