from typing import Any, Protocol


class AuthPort(Protocol):
    def hash_password(self, password: str) -> str: ...

    def verify_password(self, plain: str, hashed: str) -> bool: ...

    def hash_token(self, token: str) -> str:
        """Hash a high-entropy token (SHA256) for storage."""
        ...

    def create_token(self, user_id: Any, ttl_minutes: int) -> str:
        # TODO(T-0005): user_id might be UUID
        ...

    def validate_token(self, token: str) -> Any | None:
        # Returns user_id or None if invalid/expired
        ...
