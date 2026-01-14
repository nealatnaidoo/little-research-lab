import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated
from typing import Any as AnyType
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from src.adapters.auth.crypto import JWTAuthAdapter
from src.adapters.auth.session_store import InMemorySessionStore
from src.adapters.clock import SystemClock
from src.adapters.fs.filestore import FileSystemStore
from src.adapters.sqlite.repos import (
    SQLiteAssetRepo,
    SQLiteCollabRepo,
    SQLiteContentRepo,
    SQLiteLinkRepo,
    SQLiteRedirectRepo,
    SQLiteSiteSettingsRepo,
    SQLiteUserRepo,
)
from src.api.auth_utils import decode_access_token

# Atomic components are stateless, so we import them here for dependency injection.
# Dependencies are injected as ports/repos/adapters.
from src.components.links import LinkService
from src.components.settings import SettingsService
from src.domain.blocks import BlockValidator
from src.domain.entities import User
from src.domain.policy import PolicyEngine
from src.rules.loader import load_rules
from src.rules.models import Rules


# --- Settings ---
class Settings:
    def __init__(self) -> None:
        self.base_dir = Path(os.getcwd())
        self.db_path = f"{os.environ.get('LAB_DATA_DIR', './data')}/lrl.db"
        self.assets_dir = Path(f"{os.environ.get('LAB_DATA_DIR', './data')}/assets")
        self.rules_path = self.base_dir / "rules.yaml"


@lru_cache
def get_settings() -> Settings:
    return Settings()


# --- Rules ---
@lru_cache
def get_rules(settings: Settings = Depends(get_settings)) -> Rules:
    return load_rules(settings.rules_path)


# --- Repos ---
def get_content_repo(settings: Settings = Depends(get_settings)) -> SQLiteContentRepo:
    return SQLiteContentRepo(settings.db_path)


def get_asset_repo(settings: Settings = Depends(get_settings)) -> SQLiteAssetRepo:
    return SQLiteAssetRepo(settings.db_path)


def get_collab_repo(settings: Settings = Depends(get_settings)) -> SQLiteCollabRepo:
    return SQLiteCollabRepo(settings.db_path)


def get_site_settings_repo(settings: Settings = Depends(get_settings)) -> SQLiteSiteSettingsRepo:
    return SQLiteSiteSettingsRepo(settings.db_path)


def get_link_repo(settings: Settings = Depends(get_settings)) -> SQLiteLinkRepo:
    return SQLiteLinkRepo(settings.db_path)


def get_user_repo(settings: Settings = Depends(get_settings)) -> SQLiteUserRepo:
    return SQLiteUserRepo(settings.db_path)


def get_redirect_repo(settings: Settings = Depends(get_settings)) -> SQLiteRedirectRepo:
    return SQLiteRedirectRepo(settings.db_path)


# --- Component Services ---
def get_settings_service(
    repo: SQLiteSiteSettingsRepo = Depends(get_site_settings_repo),
) -> SettingsService:
    """Get settings component service."""
    return SettingsService(repo=repo)


def get_link_service(
    repo: SQLiteLinkRepo = Depends(get_link_repo),
) -> LinkService:
    """Get link component service."""
    return LinkService(repo=repo)


# --- Services ---
def get_policy(rules: Rules = Depends(get_rules)) -> PolicyEngine:
    return PolicyEngine(rules)


def get_block_validator(rules: Rules = Depends(get_rules)) -> BlockValidator:
    return BlockValidator(rules.blocks)


# --- Auth ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    user_repo: SQLiteUserRepo = Depends(get_user_repo),
) -> User:
    # 1. Try Cookie first (HttpOnly)
    cookie_token = request.cookies.get("access_token")
    if cookie_token and cookie_token.startswith("Bearer "):
        token = cookie_token.split(" ")[1]

    # 2. Try Header (OAuth2Bearer) - handled by Depends(oauth2_scheme) if not in cookie
    # If both missing, token is None

    if not token:
        # Fallback for dev: check if X-Token header? No, strict auth.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Decode
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None or not isinstance(user_id, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # 4. Fetch User
    user = user_repo.get_by_id(UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user


def get_file_store(settings: Settings = Depends(get_settings)) -> FileSystemStore:
    return FileSystemStore(base_path=str(settings.assets_dir))


# Adapters needed for component injection
def get_auth_adapter() -> JWTAuthAdapter:
    return JWTAuthAdapter()


# Session store singleton for auth component
_session_store_instance: InMemorySessionStore | None = None


def get_session_store() -> InMemorySessionStore:
    """Get session store singleton."""
    global _session_store_instance
    if _session_store_instance is None:
        _session_store_instance = InMemorySessionStore()
    return _session_store_instance


# Time adapter for deterministic time operations
_clock_instance: SystemClock | None = None


def get_clock() -> SystemClock:
    """Get clock singleton."""
    global _clock_instance
    if _clock_instance is None:
        _clock_instance = SystemClock()
    return _clock_instance


class AssetRulesAdapter:
    """Adapter to map generic Rules to Asset component RulesPort."""

    def __init__(self, rules: Rules):
        self._rules = rules.uploads

    def get_max_upload_bytes(self) -> int:
        return self._rules.max_upload_bytes

    def get_allowed_extensions(self) -> list[str]:
        return self._rules.allowlist_extensions

    def get_allowed_mime_types(self) -> list[str]:
        return self._rules.allowlist_mime_types


def get_asset_rules(rules: Rules = Depends(get_rules)) -> AssetRulesAdapter:
    return AssetRulesAdapter(rules)


# TODO: Implement full SQLiteVersionRepo - using in-memory stub for now
class InMemoryVersionRepo:
    """Stub version repo for assets component. Implement SQLite version later."""

    def __init__(self) -> None:
        self._versions: dict[str, AnyType] = {}
        self._latest: dict[str, str] = {}  # asset_id -> version_id
        self._counters: dict[str, int] = {}  # asset_id -> next version number

    def get_by_id(self, version_id: "UUID") -> AnyType:
        return self._versions.get(str(version_id))

    def get_versions(self, asset_id: "UUID") -> list[AnyType]:
        return [v for v in self._versions.values() if str(v.asset_id) == str(asset_id)]

    def get_next_version_number(self, asset_id: "UUID") -> int:
        key = str(asset_id)
        self._counters[key] = self._counters.get(key, 0) + 1
        return self._counters[key]

    def save(self, version: AnyType) -> AnyType:
        self._versions[str(version.id)] = version
        return version

    def set_latest(self, asset_id: "UUID", version_id: "UUID") -> None:
        self._latest[str(asset_id)] = str(version_id)

    def get_latest(self, asset_id: "UUID") -> AnyType:
        """Get the version marked as latest for an asset."""
        version_id = self._latest.get(str(asset_id))
        if version_id:
            return self._versions.get(version_id)
        return None

    def get_by_storage_key(self, key: str) -> AnyType:
        """Get version by storage key."""
        for v in self._versions.values():
            if v.storage_key == key:
                return v
        return None


_version_repo_instance: InMemoryVersionRepo | None = None


def get_version_repo() -> InMemoryVersionRepo:
    """Get version repo singleton."""
    global _version_repo_instance
    if _version_repo_instance is None:
        _version_repo_instance = InMemoryVersionRepo()
    return _version_repo_instance


# --- Public Visibility Guard (R1, T-0046) ---


def require_published(content: AnyType) -> AnyType:
    """
    Ensure content is published for public access (R1).

    Raises HTTPException(404) if content is not published.
    This enforces the rule: public_visibility.only_status = "published"

    Spec refs: R1, T-0046
    """
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")

    if getattr(content, "status", None) != "published":
        raise HTTPException(status_code=404, detail="Content not found")

    return content


def get_published_content_or_404(
    content: AnyType,
    detail: str = "Content not found",
) -> AnyType:
    """
    Return content if published, else raise 404.

    A variant of require_published that allows custom error message.

    Spec refs: R1, T-0046
    """
    if content is None:
        raise HTTPException(status_code=404, detail=detail)

    if getattr(content, "status", None) != "published":
        raise HTTPException(status_code=404, detail=detail)

    return content
