import os
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from jose import jwt
from passlib.context import CryptContext

SECRET_KEY = os.environ.get("LAB_SECRET_KEY", "dev-secret-unsafe")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    result: bool = pwd_context.verify(plain_password, hashed_password)
    return result


def get_password_hash(password: str) -> str:
    result: str = pwd_context.hash(password)
    return result


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    now_utc: datetime | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Claims to encode in the token
        expires_delta: Optional custom expiration delta
        now_utc: Current UTC time (for testing/determinism). Defaults to datetime.now(UTC).
    """
    to_encode = data.copy()
    current_time = now_utc if now_utc is not None else datetime.now(UTC)

    if expires_delta:
        expire = current_time + expires_delta
    else:
        expire = current_time + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt: str = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return cast(dict[str, Any], payload)
    except jwt.JWTError:
        return None
