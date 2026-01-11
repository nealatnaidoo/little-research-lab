import os
from pathlib import Path


class FileSystemStore:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path).resolve()
        if not self.base_path.exists():
            os.makedirs(self.base_path, exist_ok=True)

    def _safe_path(self, path: str) -> Path:
        # Prevent traversal
        target = (self.base_path / path).resolve()
        if not str(target).startswith(str(self.base_path)):
            raise ValueError(f"Path traversal attempt detected: {path}")
        return target

    def save(self, name: str, data: bytes) -> str:
        """Save bytes and return an identifier/path."""
        target = self._safe_path(name)
        # Ensure parent exists
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            f.write(data)
        # Return path relative to base, as that's what we store/retrieve by
        return str(target.relative_to(self.base_path))

    def get(self, path: str) -> bytes:
        """Retrieve bytes by path. Raises FileNotFoundError."""
        target = self._safe_path(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {path}")
        with open(target, "rb") as f:
            return f.read()

    def delete(self, path: str) -> None:
        target = self._safe_path(path)
        if target.exists():
            os.remove(target)
