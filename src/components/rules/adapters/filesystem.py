"""
File system and environment adapters for the rules component.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


class LocalFileSystemAdapter:
    """Adapter for local file system operations."""

    def read_yaml(self, path: Path) -> dict[str, Any]:
        """Read and parse a YAML file."""
        with open(path) as f:
            result: dict[str, Any] = yaml.safe_load(f)
            return result

    def exists(self, path: Path) -> bool:
        """Check if a file exists."""
        return path.exists()


class OsEnvironmentAdapter:
    """Adapter for OS environment variables."""

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get an environment variable."""
        return os.environ.get(key, default)


# Default adapter instances
default_filesystem = LocalFileSystemAdapter()
default_environment = OsEnvironmentAdapter()
