from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.app_shell.rate_limit import RateLimiter
    from src.components.scheduler.ports import PublishJobRepoPort
    from src.ports.renderer import RendererPort
    from src.ports.repo import (
        AssetRepoPort,
        CollabRepoPort,
        ContentRepoPort,
        InviteRepoPort,
        LinkRepoPort,
        UserRepoPort,
    )

from src.adapters.auth.crypto import Argon2AuthAdapter
from src.adapters.auth.session_store import InMemorySessionStore
from src.adapters.clock import SystemClock
from src.adapters.fs.filestore import FileSystemStore
from src.adapters.render.mpl_renderer import MatplotlibRenderer
from src.adapters.sqlite.repos import (
    SQLiteAssetRepo,
    SQLiteCollabRepo,
    SQLiteContentRepo,
    SQLiteInviteRepo,
    SQLiteLinkRepo,
    SQLitePublishJobRepo,
    SQLiteUserRepo,
)
from src.app_shell.rate_limit import RateLimiter
from src.domain.blocks import BlockValidator
from src.domain.policy import PolicyEngine
from src.rules.models import Rules


@dataclass
class ServiceContext:
    # Repositories
    user_repo: UserRepoPort
    content_repo: ContentRepoPort
    asset_repo: AssetRepoPort
    link_repo: LinkRepoPort
    invite_repo: InviteRepoPort
    collab_repo: CollabRepoPort
    publish_job_repo: PublishJobRepoPort

    # Adapters
    renderer: RendererPort
    # Type as AuthAdapterPort if imported, using Any to avoid circular deps
    auth_adapter: Any
    clock: Any
    session_store: Any

    # Domain
    policy: PolicyEngine
    validator: BlockValidator
    rules: Rules
    rate_limiter: RateLimiter

    # Legacy services - stubs for app_shell compatibility during migration
    # TODO: Remove after app_shell migrated to atomic components (EV-0003)
    content_service: Any = None
    asset_service: Any = None
    publish_service: Any = None
    auth_service: Any = None
    invite_service: Any = None

    @classmethod
    def create(cls, db_path: str, fs_path: str, rules: Rules) -> ServiceContext:
        # Adapters
        user_repo = SQLiteUserRepo(db_path)
        content_repo = SQLiteContentRepo(db_path)
        asset_repo = SQLiteAssetRepo(db_path)
        link_repo = SQLiteLinkRepo(db_path)
        invite_repo = SQLiteInviteRepo(db_path)
        collab_repo = SQLiteCollabRepo(db_path)
        publish_job_repo = SQLitePublishJobRepo(db_path)

        fs_store = FileSystemStore(fs_path)
        renderer = MatplotlibRenderer(fs_store)
        auth_adapter = Argon2AuthAdapter()
        clock = SystemClock()
        session_store = InMemorySessionStore()

        # Domain
        policy = PolicyEngine(rules)
        validator = BlockValidator(rules.blocks)

        rate_limiter = RateLimiter(rules.rate_limits)

        return cls(
            user_repo=user_repo,
            content_repo=content_repo,
            asset_repo=asset_repo,
            link_repo=link_repo,
            invite_repo=invite_repo,
            collab_repo=collab_repo,
            publish_job_repo=publish_job_repo,
            renderer=renderer,
            auth_adapter=auth_adapter,
            clock=clock,
            session_store=session_store,
            policy=policy,
            validator=validator,
            rules=rules,
            rate_limiter=rate_limiter,
        )
