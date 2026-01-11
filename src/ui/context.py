from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.app_shell.rate_limit import RateLimiter
    from src.ports.renderer import RendererPort
    from src.ports.repo import (
        AssetRepoPort,
        CollabRepoPort,
        ContentRepoPort,
        InviteRepoPort,
        LinkRepoPort,
        UserRepoPort,
    )
    from src.services.collab import CollabService
    from src.services.invite import InviteService
    from src.services.publish import PublishService

from src.adapters.auth.crypto import Argon2AuthAdapter
from src.adapters.fs.filestore import FileSystemStore
from src.adapters.render.mpl_renderer import MatplotlibRenderer
from src.adapters.sqlite.repos import (
    SQLiteAssetRepo,
    SQLiteCollabRepo,
    SQLiteContentRepo,
    SQLiteInviteRepo,
    SQLiteLinkRepo,
    SQLiteUserRepo,
)
from src.domain.blocks import BlockValidator
from src.domain.policy import PolicyEngine
from src.ports.renderer import RendererPort
from src.ports.repo import (
    AssetRepoPort,
    CollabRepoPort,
    ContentRepoPort,
    InviteRepoPort,
    LinkRepoPort,
    UserRepoPort,
)
from src.rules.models import Rules
from src.services.asset import AssetService
from src.services.auth import AuthService
from src.services.content import ContentService


@dataclass
class ServiceContext:
    auth_service: AuthService
    content_service: ContentService
    asset_service: AssetService
    publish_service: PublishService
    invite_service: InviteService
    collab_service: CollabService
    user_repo: UserRepoPort
    content_repo: ContentRepoPort
    asset_repo: AssetRepoPort
    link_repo: LinkRepoPort
    invite_repo: InviteRepoPort
    collab_repo: CollabRepoPort
    renderer: RendererPort
    policy: PolicyEngine
    rate_limiter: RateLimiter
    rules: Rules
    clock: Any = None # For testing/injection
    # Add other services/repos as needed
    
    @classmethod
    def create(cls, db_path: str, fs_path: str, rules: Rules) -> ServiceContext:
        # Adapters
        user_repo = SQLiteUserRepo(db_path)
        content_repo = SQLiteContentRepo(db_path)
        asset_repo = SQLiteAssetRepo(db_path)
        link_repo = SQLiteLinkRepo(db_path)
        invite_repo = SQLiteInviteRepo(db_path)
        collab_repo = SQLiteCollabRepo(db_path)
        
        fs_store = FileSystemStore(fs_path)
        renderer = MatplotlibRenderer(fs_store)
        auth_adapter = Argon2AuthAdapter()
        
        # Domain
        policy = PolicyEngine(rules)
        validator = BlockValidator(rules.blocks)
        
        # Services
        # Adapters for Publish
        from src.adapters.clock import SystemClock
        from src.services.publish import PublishService
        
        auth_service = AuthService(user_repo, auth_adapter, policy)
        content_service = ContentService(content_repo, policy, validator, collab_repo)
        asset_service = AssetService(asset_repo, fs_store, policy, rules.uploads)
        
        clock = SystemClock()
        publish_service = PublishService(content_repo, policy, clock)
        
        from src.services.invite import InviteService
        invite_service = InviteService(invite_repo, user_repo, auth_adapter, policy)

        from src.services.collab import CollabService
        collab_service = CollabService(collab_repo, content_repo, user_repo, policy)
        
        from src.app_shell.rate_limit import RateLimiter
        rate_limiter = RateLimiter(rules.rate_limits)
        
        return cls(
            auth_service=auth_service,
            content_service=content_service,
            asset_service=asset_service,
            publish_service=publish_service,
            invite_service=invite_service,
            collab_service=collab_service,
            user_repo=user_repo,
            content_repo=content_repo,
            asset_repo=asset_repo,
            link_repo=link_repo,
            invite_repo=invite_repo,
            collab_repo=collab_repo,
            renderer=renderer,
            policy=policy,
            rate_limiter=rate_limiter,
            rules=rules,
            clock=clock
        )
