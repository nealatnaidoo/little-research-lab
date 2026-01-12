"""
Adapters for the rules component.
"""

from .filesystem import (
    LocalFileSystemAdapter,
    OsEnvironmentAdapter,
    default_environment,
    default_filesystem,
)

__all__ = [
    "LocalFileSystemAdapter",
    "OsEnvironmentAdapter",
    "default_filesystem",
    "default_environment",
]
