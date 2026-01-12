from typing import Protocol


class FileStorePort(Protocol):
    def save(self, name: str, data: bytes) -> str:
        """Save bytes and return an identifier/path."""
        ...

    def get(self, path: str) -> bytes:
        """Retrieve bytes by path. Raises FileNotFoundError."""
        ...

    def delete(self, path: str) -> None: ...
