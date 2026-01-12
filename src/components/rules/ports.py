"""
Rules component port definitions.

Spec refs: E0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class FileSystemPort(Protocol):
    """Port for file system operations."""

    def read_yaml(self, path: Path) -> dict[str, Any]:
        """Read and parse a YAML file."""
        ...

    def exists(self, path: Path) -> bool:
        """Check if a file exists."""
        ...


class EnvironmentPort(Protocol):
    """Port for environment variable access."""

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get an environment variable."""
        ...
