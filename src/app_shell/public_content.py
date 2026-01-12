import base64
import logging
from uuid import UUID

import flet as ft

from src.domain.entities import ContentItem
from src.ui.context import ServiceContext
from src.ui.state import AppState

logger = logging.getLogger(__name__)


def _resolve_content_item(
    ctx: ServiceContext, identifier: str | None, item_type: str = "post"
) -> ContentItem | None:
    """Resolve content item by slug or UUID."""
    if not identifier:
        return None

    # First try as slug
    item = ctx.content_service.repo.get_by_slug(identifier, item_type)
    if item:
        return item  # type: ignore[no-any-return]

    # Fall back to UUID lookup
    try:
        uid = UUID(identifier)
        item = ctx.content_service.repo.get_by_id(uid)
        if item and item.type == item_type:
            return item  # type: ignore[no-any-return]
    except (ValueError, KeyError, TypeError):
        pass

    return None


def PublicPostContent(
    page: ft.Page,
    ctx: ServiceContext,
    state: AppState,
    item_id: str | None = None,
    slug: str | None = None,
) -> ft.Control:
    identifier = slug or item_id
    if not identifier:
        return ft.Text("Post identifier required", color="red")

    item = _resolve_content_item(ctx, identifier, "post")

    if not item:
        return ft.Text("Post not found", size=20)

    # Permission Check
    is_public = item.status == "published"
    if not is_public:
        return ft.Text("Content not found (Private)", size=20)

    # Render Content
    controls: list[ft.Control] = []

    # Back Button
    controls.append(
        ft.Container(
            content=ft.TextButton("← Back to Home", on_click=lambda _: page.go("/")), padding=10
        )
    )

    # Title
    controls.append(ft.Text(item.title, size=30, weight=ft.FontWeight.BOLD, color="primary"))
    if item.published_at:
        date_str = item.published_at.strftime("%Y-%m-%d")
        controls.append(ft.Text(f"Published: {date_str}", italic=True, color="onSurfaceVariant"))
    controls.append(ft.Divider())

    # Blocks
    if item.blocks:
        for block in item.blocks:
            if block.block_type == "markdown":
                controls.append(
                    ft.Markdown(
                        block.data_json.get("text", ""),
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                    )
                )
            elif block.block_type == "image":
                url = block.data_json.get("url")
                caption = block.data_json.get("caption")
                if url:
                    img = ft.Image(src=url, width=600, height=400, fit=ft.ImageFit.CONTAIN)
                    controls.append(img)
                if caption:
                    controls.append(ft.Text(caption, size=12, italic=True))
            elif block.block_type == "chart":
                spec = block.data_json.get("spec")
                if spec:
                    try:
                        png_bytes = ctx.renderer.render_chart(spec, 600, 400, 100)
                        b64 = base64.b64encode(png_bytes).decode("utf-8")
                        img = ft.Image(src_base64=b64)
                        controls.append(img)
                    except Exception as e:
                        logger.error(f"Failed to render chart: {e}")
                        controls.append(ft.Text(f"[Chart Error: {e}]", color="red"))

            controls.append(ft.Container(height=10))

    return ft.Container(
        content=ft.Column(controls, scroll=ft.ScrollMode.AUTO), padding=20, expand=True
    )


def PublicPageContent(
    page: ft.Page, ctx: ServiceContext, state: AppState, slug: str | None = None
) -> ft.Control:
    """Render a static page by slug (About, Now, Projects, etc.)."""
    if not slug:
        return ft.Text("Page slug required", color="red")

    item = _resolve_content_item(ctx, slug, "page")

    if not item:
        return ft.Text("Page not found", size=20)

    # Permission Check - pages must be published
    if item.status != "published":
        return ft.Text("Page not found", size=20)

    # Render Content (similar to post but without date emphasis)
    controls: list[ft.Control] = []

    # Back Button
    controls.append(
        ft.Container(
            content=ft.TextButton("← Back to Home", on_click=lambda _: page.go("/")), padding=10
        )
    )

    # Title
    controls.append(ft.Text(item.title, size=30, weight=ft.FontWeight.BOLD, color="primary"))
    controls.append(ft.Divider())

    # Blocks
    if item.blocks:
        for block in item.blocks:
            if block.block_type == "markdown":
                controls.append(
                    ft.Markdown(
                        block.data_json.get("text", ""),
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                    )
                )
            elif block.block_type == "image":
                url = block.data_json.get("url")
                caption = block.data_json.get("caption")
                if url:
                    img = ft.Image(src=url, width=600, height=400, fit=ft.ImageFit.CONTAIN)
                    controls.append(img)
                if caption:
                    controls.append(ft.Text(caption, size=12, italic=True))
            elif block.block_type == "chart":
                spec = block.data_json.get("spec")
                if spec:
                    try:
                        png_bytes = ctx.renderer.render_chart(spec, 600, 400, 100)
                        b64 = base64.b64encode(png_bytes).decode("utf-8")
                        img = ft.Image(src_base64=b64)
                        controls.append(img)
                    except Exception as e:
                        logger.error(f"Failed to render chart: {e}")
                        controls.append(ft.Text(f"[Chart Error: {e}]", color="red"))

            controls.append(ft.Container(height=10))

    return ft.Container(
        content=ft.Column(controls, scroll=ft.ScrollMode.AUTO), padding=20, expand=True
    )


def LinkRedirectContent(
    page: ft.Page, ctx: ServiceContext, state: AppState, slug: str | None = None
) -> ft.Control:
    """Handle link redirect by slug - shows link info or redirects."""
    if not slug:
        return ft.Text("Link slug required", color="red")

    # Find link by slug
    all_links = ctx.link_repo.get_all()
    link = next((lnk for lnk in all_links if lnk.slug == slug), None)

    if not link:
        return ft.Text("Link not found", size=20)

    # Check visibility and status
    if link.status != "active" or link.visibility == "private":
        return ft.Text("Link not found", size=20)

    # Display link page with redirect option
    return ft.Container(
        content=ft.Column(
            [
                ft.TextButton("← Back to Home", on_click=lambda _: page.go("/")),
                ft.Divider(),
                ft.Icon(name=link.icon or "link", size=48, color="primary"),
                ft.Text(link.title, size=24, weight=ft.FontWeight.BOLD),
                ft.Text(f"Redirecting to: {link.url}", color="onSurfaceVariant"),
                ft.Container(height=20),
                ft.ElevatedButton(
                    "Go to Link",
                    icon=ft.Icons.OPEN_IN_NEW,
                    on_click=lambda _: page.launch_url(str(link.url)),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=40,
        expand=True,
        alignment=ft.alignment.center,
    )


def TagFilterContent(
    page: ft.Page, ctx: ServiceContext, state: AppState, tag: str | None = None
) -> ft.Control:
    """Display posts filtered by tag (future: implement tagging system)."""
    if not tag:
        return ft.Text("Tag required", color="red")

    # For now, filter by searching title/summary for tag
    # Future: implement proper tagging system with ContentItem.tags field
    all_items = ctx.content_service.repo.list_items(filters={"status": "published"})

    # Simple tag matching in title or summary
    tag_lower = tag.lower()
    filtered = [
        item
        for item in all_items
        if tag_lower in item.title.lower() or tag_lower in (item.summary or "").lower()
    ]

    controls: list[ft.Control] = []

    # Back Button
    controls.append(
        ft.Container(
            content=ft.TextButton("← Back to Home", on_click=lambda _: page.go("/")), padding=10
        )
    )

    # Header
    controls.append(
        ft.Text(f"Posts tagged: {tag}", size=24, weight=ft.FontWeight.BOLD, color="primary")
    )
    controls.append(ft.Divider())

    if not filtered:
        controls.append(ft.Text("No posts found with this tag.", italic=True))
    else:
        for item in filtered:
            date_str = item.published_at.strftime("%Y-%m-%d") if item.published_at else ""
            controls.append(
                ft.ListTile(
                    title=ft.Text(item.title, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(f"{date_str} • {item.summary or 'No summary'}"),
                    on_click=lambda _, slug=item.slug: page.go(f"/p/{slug}"),
                )
            )

    return ft.Container(
        content=ft.Column(controls, scroll=ft.ScrollMode.AUTO), padding=20, expand=True
    )
