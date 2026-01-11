import base64
import logging
from uuid import UUID

import flet as ft

from src.domain.entities import User
from src.ui.context import ServiceContext
from src.ui.state import AppState

logger = logging.getLogger(__name__)


class AssetHandler:
    def __init__(self, ctx: ServiceContext):
        self.ctx = ctx

    def get_asset_content_base64(self, user: User | None, asset_id: UUID) -> str | None:
        """
        Retrieves asset content and returns it as a base64 string suitable for Flet images.
        Returns None if not found or no permission.
        """
        try:
            # Service handles permission check
            data = self.ctx.asset_service.get_asset_content(user, asset_id)
            return base64.b64encode(data).decode("utf-8")
        except PermissionError:
            logger.warning(
                f"Permission denied for asset {asset_id} user {user.id if user else 'anon'}"
            )
            return None
        except ValueError:
            logger.warning(f"Asset {asset_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error serving asset {asset_id}: {e}")
            return None


def PublicAssetContent(
    page: ft.Page,
    ctx: ServiceContext,
    state: AppState,
    asset_id: str | None = None
) -> ft.Control:
    """
    Public asset view - serves assets that are public or attached to published content.
    Per spec E5.2: Public can fetch only assets that are public OR referenced by
    published public content.
    """
    if not asset_id:
        return ft.Text("Asset ID required", color="red")

    try:
        uid = UUID(asset_id)
    except ValueError:
        return ft.Text("Invalid asset ID", color="red")

    # Get asset metadata first
    asset = ctx.asset_repo.get_by_id(uid)
    if not asset:
        return ft.Text("Asset not found", size=20)

    # Check visibility - public assets are always accessible
    # For unlisted/private, would need to check if referenced by published content
    # For now, only serve public assets to anonymous users
    user = state.current_user
    if asset.visibility == "private" and not user:
        return ft.Text("Asset not found", size=20)

    # Get content
    handler = AssetHandler(ctx)
    b64_content = handler.get_asset_content_base64(user, uid)

    if not b64_content:
        return ft.Text("Unable to load asset", color="red")

    # Determine display based on mime type
    controls: list[ft.Control] = []

    controls.append(ft.Container(
        content=ft.TextButton("← Back", on_click=lambda _: page.go("/")),
        padding=10
    ))

    if asset.mime_type.startswith("image/"):
        controls.append(ft.Image(
            src_base64=b64_content,
            fit=ft.ImageFit.CONTAIN,
            width=800
        ))
    elif asset.mime_type == "application/pdf":
        # PDF preview not directly supported, show download info
        controls.append(ft.Text(f"PDF: {asset.filename_original}", size=18))
        controls.append(ft.Text("PDF preview not available in browser view."))
    else:
        controls.append(ft.Text(f"File: {asset.filename_original}", size=18))
        controls.append(ft.Text(f"Type: {asset.mime_type}"))
        controls.append(ft.Text(f"Size: {asset.size_bytes} bytes"))

    # File info
    controls.append(ft.Divider())
    filename_text = ft.Text(
        f"Filename: {asset.filename_original}", size=12, color="onSurfaceVariant"
    )
    controls.append(filename_text)
    size_text = ft.Text(
        f"Size: {asset.size_bytes:,} bytes", size=12, color="onSurfaceVariant"
    )
    controls.append(size_text)

    return ft.Container(
        content=ft.Column(controls, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=20,
        expand=True,
        alignment=ft.alignment.center
    )
