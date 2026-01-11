import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from src.adapters.auth.crypto import JWTAuthAdapter
from src.adapters.fs.filestore import FileSystemStore
from src.adapters.sqlite.repos import (
    SQLiteAssetRepo,
    SQLiteCollabRepo,
    SQLiteContentRepo,
    SQLiteLinkRepo,
    SQLiteSiteSettingsRepo,
    SQLiteUserRepo,
)
from src.api.auth_utils import decode_access_token
from src.domain.blocks import BlockValidator
from src.domain.entities import User
from src.domain.policy import PolicyEngine
from src.rules.loader import load_rules
from src.rules.models import Rules
from src.services.asset import AssetService
from src.services.auth import AuthService
from src.services.content import ContentService


# --- Settings ---
class Settings:
    def __init__(self) -> None:
        self.base_dir = Path(os.getcwd())
        self.db_path = f"{os.environ.get('LAB_DATA_DIR', './data')}/lrl.db"
        self.assets_dir = Path(f"{os.environ.get('LAB_DATA_DIR', './data')}/assets")
        self.rules_path = self.base_dir / "research-lab-bio_rules.yaml"


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

# --- Services ---
def get_policy(rules: Rules = Depends(get_rules)) -> PolicyEngine:
    return PolicyEngine(rules)

def get_block_validator(rules: Rules = Depends(get_rules)) -> BlockValidator:
    return BlockValidator(rules.blocks)

def get_content_service(
    repo: SQLiteContentRepo = Depends(get_content_repo),
    policy: PolicyEngine = Depends(get_policy),
    validator: BlockValidator = Depends(get_block_validator),
    collab_repo: SQLiteCollabRepo = Depends(get_collab_repo)
) -> ContentService:
    return ContentService(repo=repo, policy=policy, validator=validator, collab_repo=collab_repo)

def get_file_store(settings: Settings = Depends(get_settings)) -> FileSystemStore:
    return FileSystemStore(base_path=str(settings.assets_dir))

def get_asset_service(
    repo: SQLiteAssetRepo = Depends(get_asset_repo),
    policy: PolicyEngine = Depends(get_policy),
    file_store: FileSystemStore = Depends(get_file_store),
    rules: Rules = Depends(get_rules),
) -> AssetService:
    return AssetService(repo=repo, filestore=file_store, policy=policy, rules=rules.uploads)

# --- Auth ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    user_repo: SQLiteUserRepo = Depends(get_user_repo)
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

# --- Auth Service ---
def get_auth_service(
    user_repo: SQLiteUserRepo = Depends(get_user_repo),
    policy: PolicyEngine = Depends(get_policy),
) -> AuthService:
    return AuthService(user_repo=user_repo, auth_adapter=JWTAuthAdapter(), policy=policy)
