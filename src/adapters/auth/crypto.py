import hashlib
from datetime import timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from src.api.auth_utils import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


class JWTAuthAdapter:
    """Auth adapter that uses JWT tokens and passlib for password hashing."""

    def hash_password(self, password: str) -> str:
        return get_password_hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return verify_password(plain, hashed)

    def hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def create_token(self, user_id: Any, ttl_minutes: int) -> str:
        return create_access_token({"sub": str(user_id)}, timedelta(minutes=ttl_minutes))

    def validate_token(self, token: str) -> Any | None:
        payload = decode_access_token(token)
        return payload.get("sub") if payload else None


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
        return hashlib.sha256(token.encode()).hexdigest()

    def create_token(self, user_id: Any, ttl_minutes: int) -> str:
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
