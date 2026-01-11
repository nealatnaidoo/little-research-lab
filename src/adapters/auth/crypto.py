from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


class Argon2AuthAdapter:
    def __init__(self) -> None:
        self.ph = PasswordHasher()

    def hash_password(self, password: str) -> str:
        return str(self.ph.hash(password))

    def verify_password(self, password: str, hash_str: str) -> bool:
        try:
            self.ph.verify(hash_str, password)
            return True
        except VerifyMismatchError:
            return False

    def hash_token(self, token: str) -> str:
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()

    def create_token(self, user_id: Any, ttl_minutes: int) -> str:
        # Simple random token for now.
        import secrets
        return secrets.token_urlsafe(32)

    def validate_token(self, token: str) -> Any | None:
        # Adapter doesn't store tokens, Service does.
        # If this adapter was JWT, it would validate signature.
        # Since we use opaque tokens in memory (Service side), this might be a no-op or
        # the Port design assumed JWT.
        # For now, let's just say this adapter only creates opaque tokens.
        # The Service `get_user_by_token` handles validation in our current MVP.
        return None
