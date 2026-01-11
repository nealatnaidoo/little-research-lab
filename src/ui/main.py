import logging
import os
import sqlite3

import flet as ft

from src.app_shell.admin.content_admin import ContentEditContent, ContentListContent

# Legacy/Refactored Imports
from src.app_shell.admin.dashboard import AdminDashboardContent
from src.app_shell.config import validate_ops_rules
from src.app_shell.asset_routes import PublicAssetContent
from src.app_shell.public_content import (
    LinkRedirectContent,
    PublicPageContent,
    PublicPostContent,
    TagFilterContent,
)
from src.app_shell.public_home import PublicHomeContent
from src.rules.loader import load_rules
from src.services.bootstrap import bootstrap_system
from src.ui.context import ServiceContext
from src.ui.layout import MainLayout
from src.ui.state import AppState
from src.ui.theme import AppTheme
from src.ui.views.login import LoginView

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration from environment (with sensible defaults for local dev)
DB_PATH = os.environ.get("LRL_DB_PATH", "lrl.db")
FS_PATH = os.environ.get("LRL_FS_PATH", "filestore")
DATA_DIR = os.environ.get("LRL_DATA_DIR", ".")
RULES_PATH = os.environ.get("LRL_RULES_PATH", "rules.yaml")


def init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        res = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users';"
        )
        if not res.fetchone():
            logger.info("Initializing database schema...")
            with open("migrations/001_initial.sql") as f:
                schema = f.read()
                up_script = schema.split("-- Down")[0]
                conn.executescript(up_script)
            logger.info("Database schema initialized.")
    finally:
        conn.close()


def main(page: ft.Page) -> None:
    from pathlib import Path

    page.title = "Little Research Lab"

    # 0. Theme Setup (T-0035)
    page.theme = AppTheme.light_theme()
    page.dark_theme = AppTheme.dark_theme()
    page.theme_mode = ft.ThemeMode.LIGHT

    # 1. Ensure data directories exist
    data_dir = Path(DATA_DIR)
    fs_path = Path(FS_PATH)

    if DATA_DIR != ".":
        data_dir.mkdir(parents=True, exist_ok=True)
    fs_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Data directory: {data_dir.absolute()}")
    logger.info(f"Database path: {DB_PATH}")
    logger.info(f"Filestore path: {FS_PATH}")

    # 2. Initialize Database
    init_db(DB_PATH)

    # 3. Load Rules
    rules_path = Path(RULES_PATH)
    if not rules_path.exists():
        error_msg = f"Error: {RULES_PATH} not found. Please create it."
        logger.error(error_msg)
        page.add(ft.Text(error_msg, color="red", size=20))
        return

    rules = load_rules(rules_path)
    logger.info("Rules loaded successfully")

    # 4. Validate Production Config
    validate_ops_rules(rules, base_dir=data_dir if DATA_DIR != "." else Path("."))

    # 4. Create Context
    ctx = ServiceContext.create(DB_PATH, FS_PATH, rules)

    # 5. Bootstrap Owner
    bootstrap_system(ctx)

    # 6. App State
    state = AppState()

    # 7. Routing Setup
    from typing import Any, cast

    from src.app_shell.router import Router

    router = Router(page, state)

    # --- Layout Wrapper ---
    def make_view(route: str, content: ft.Control | ft.View) -> ft.View:
        def handle_nav(r: str) -> None:
            page.go(r)
        
        def handle_logout() -> None:
            state.logout()
            page.go("/login")
            
        def toggle_theme() -> None:
            if page.theme_mode == ft.ThemeMode.LIGHT:
                page.theme_mode = ft.ThemeMode.DARK
            else:
                page.theme_mode = ft.ThemeMode.LIGHT
            page.update()

        # Handle content being a View (Legacy) or Control (Refactored)
        real_content: ft.Control
        if isinstance(content, ft.View):
            # Hack: Wrap View controls in a Column to embed in Layout
            # This might Result in double AppBars if the View had one.
            real_content = ft.Column(
                 # Expand logic might be lost, ensuring expand=True
                controls=content.controls,
                expand=True
            )
        else:
            real_content = content
            
        layout = MainLayout(
            page=page,
            app_state=state,
            content=real_content,
            on_logout=handle_logout,
            on_nav=handle_nav,
            toggle_theme=toggle_theme,
            current_route=route
        )
        
        # Return a fresh View wrapping the Layout
        return ft.View(route, [layout], padding=0)

    # --- Builders ---

    def home_builder(_: ft.Page) -> ft.View:
        content = PublicHomeContent(page, ctx, state)
        return make_view("/", content)

    # Slug-based post route per spec E1.2: /p/{slug}
    def post_slug_builder(_: ft.Page, **kwargs: Any) -> ft.View:
        slug = kwargs.get("slug")
        content = PublicPostContent(page, ctx, state, slug=slug)
        return make_view(f"/p/{slug}", content)

    # Legacy ID-based post route (backwards compatibility)
    def post_id_builder(_: ft.Page, **kwargs: Any) -> ft.View:
        cid = kwargs.get("item_id")
        content = PublicPostContent(page, ctx, state, item_id=cid)
        return make_view(f"/post/{cid}", content)

    # Page route per spec E1.2: /page/{slug}
    def page_slug_builder(_: ft.Page, **kwargs: Any) -> ft.View:
        slug = kwargs.get("slug")
        content = PublicPageContent(page, ctx, state, slug=slug)
        return make_view(f"/page/{slug}", content)

    # Link redirect route per spec E1.3: /l/{slug}
    def link_redirect_builder(_: ft.Page, **kwargs: Any) -> ft.View:
        slug = kwargs.get("slug")
        content = LinkRedirectContent(page, ctx, state, slug=slug)
        return make_view(f"/l/{slug}", content)

    # Tag filtering route per spec: /tag/{tag}
    def tag_filter_builder(_: ft.Page, **kwargs: Any) -> ft.View:
        tag = kwargs.get("tag")
        content = TagFilterContent(page, ctx, state, tag=tag)
        return make_view(f"/tag/{tag}", content)

    # Asset public route per spec E5.2: /assets/{asset_id}
    def asset_public_builder(_: ft.Page, **kwargs: Any) -> ft.View:
        asset_id = kwargs.get("asset_id")
        content = PublicAssetContent(page, ctx, state, asset_id=asset_id)
        return make_view(f"/assets/{asset_id}", content)

    def login_builder(_: ft.Page) -> ft.View:
        # LoginView returns a control (LoginView object) or View?
        # Checked earlier: returned in a list `[LoginView(...)]`. So it is a Control.
        content = LoginView(page, ctx, state)
        return make_view("/login", content)

    def dashboard_builder(_: ft.Page) -> ft.View:
        content = AdminDashboardContent(page, ctx, state)
        return make_view("/dashboard", content)

    def content_list_builder(_: ft.Page) -> ft.View:
        content = ContentListContent(page, ctx, state)
        return make_view("/admin/content", content)
        
    def content_edit_builder(_: ft.Page, **kwargs: Any) -> ft.View:
        item_id = kwargs.get("item_id")
        content = ContentEditContent(page, ctx, state, item_id=item_id)
        return make_view(f"/admin/content/{item_id}", content)

    # Legacy Admin (Not refactored yet)
    from src.app_shell.admin.assets_admin import AssetListView
    from src.app_shell.admin.schedule_admin import ScheduleView
    from src.app_shell.admin.users_admin import UserEditView, UserListView
    
    def asset_list_builder(_: ft.Page) -> ft.View:
        return make_view("/admin/assets", AssetListView(page, ctx, state))
        
    def schedule_builder(_: ft.Page) -> ft.View:
        return make_view("/admin/schedule", ScheduleView(page, ctx, state))
        
    def user_list_builder(_: ft.Page) -> ft.View:
         return make_view("/admin/users", UserListView(page, ctx, state))
         
    def user_edit_builder(_: ft.Page, **kwargs: Any) -> ft.View:
        uid = cast(str, kwargs.get("user_id"))
        return make_view(f"/admin/users/{uid}", UserEditView(page, ctx, state, user_id=uid))
        
    # Invite is public
    from src.app_shell.invite_routes import RedeemInviteView
    def invite_builder(_: ft.Page, **kwargs: Any) -> ft.View:
        token = kwargs.get("token", "")
        # RedeemInviteView is likely a View.
        return make_view(f"/invite/{token}", RedeemInviteView(page, ctx, state, token=token))

    # --- Register Routes ---

    # Public routes per spec Information Architecture
    router.register("/", home_builder, protected=False)
    router.register("/login", login_builder, protected=False)

    # Content routes - slug-based per spec E1.2
    router.register_dynamic(r"^/p/(?P<slug>[a-z0-9-]+)$", post_slug_builder, protected=False)
    router.register_dynamic(r"^/page/(?P<slug>[a-z0-9-]+)$", page_slug_builder, protected=False)

    # Legacy ID-based route for backwards compatibility
    router.register_dynamic(r"^/post/(?P<item_id>.+)$", post_id_builder, protected=False)

    # Link redirect per spec E1.3
    router.register_dynamic(r"^/l/(?P<slug>[a-z0-9-]+)$", link_redirect_builder, protected=False)

    # Tag filtering per spec
    router.register_dynamic(r"^/tag/(?P<tag>.+)$", tag_filter_builder, protected=False)

    # Asset serving per spec E5.2
    router.register_dynamic(r"^/assets/(?P<asset_id>.+)$", asset_public_builder, protected=False)

    # Invite redemption
    router.register_dynamic(r"^/invite/(?P<token>.+)$", invite_builder, protected=False)
    
    # Protected 
    router.register("/dashboard", dashboard_builder, protected=True)
    router.register("/admin/content", content_list_builder, protected=True)
    router.register("/admin/content/new", 
        lambda p: make_view(
            "/admin/content/new", 
            ContentEditContent(p, ctx, state, item_id="new")
        ), 
        protected=True
    )
    router.register_dynamic(
        r"^/admin/content/(?P<item_id>.+)$", 
        content_edit_builder, 
        protected=True
    )
    
    router.register("/admin/assets", asset_list_builder, protected=True)
    router.register("/admin/schedule", schedule_builder, protected=True)
    router.register("/admin/users", user_list_builder, protected=True)
    router.register_dynamic(r"^/admin/users/(?P<user_id>.+)$", user_edit_builder, protected=True)
    
    # Wire up events
    page.on_route_change = router.handle_route_change
    page.on_view_pop = router.view_pop

    # Go to initial route (default to "/" if route is empty)
    page.go(page.route or "/")

if __name__ == "__main__":
    ft.app(target=main)

