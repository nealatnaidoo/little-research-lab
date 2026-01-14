import logging
import uuid
from datetime import UTC, datetime

import flet as ft

from src.domain.entities import ContentBlock, ContentItem
from src.ui.context import ServiceContext
from src.ui.state import AppState

logger = logging.getLogger(__name__)


def ContentListContent(page: ft.Page, ctx: ServiceContext, state: AppState) -> ft.Control:
    # Fetch all items
    items = ctx.content_service.repo.list_items(filters={})
    items.sort(key=lambda x: x.updated_at, reverse=True)

    def edit_item(e: ft.ControlEvent) -> None:
        item_id = e.control.data
        page.go(f"/admin/content/{item_id}")

    def delete_item(e: ft.ControlEvent) -> None:
        item_id = e.control.data
        try:
            if not state.current_user:
                raise ValueError("Not logged in")
            ctx.content_service.delete_item(state.current_user, uuid.UUID(item_id))
            page.go("/admin/content")
            page.update()
        except Exception as err:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {err}"))
            page.snack_bar.open = True
            page.update()

    def create_new(_: ft.ControlEvent) -> None:
        page.go("/admin/content/new")

    # DataTable
    rows = []
    for item in items:
        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(item.title)),
                    ft.DataCell(ft.Text(item.slug)),
                    ft.DataCell(ft.Text(item.status)),
                    ft.DataCell(ft.Text(item.updated_at.strftime("%Y-%m-%d %H:%M"))),
                    ft.DataCell(
                        ft.Row(
                            [
                                ft.IconButton(ft.Icons.EDIT, on_click=edit_item, data=str(item.id)),
                                ft.IconButton(
                                    ft.Icons.DELETE,
                                    on_click=delete_item,
                                    data=str(item.id),
                                    icon_color="red",
                                ),
                            ]
                        )
                    ),
                ],
            )
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Content Management",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color="primary",
                        ),
                        ft.ElevatedButton(
                            "New Post",
                            icon=ft.Icons.ADD,
                            on_click=create_new,
                            bgcolor="primary",
                            color="onPrimary",
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(),
                ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("Title")),
                        ft.DataColumn(ft.Text("Slug")),
                        ft.DataColumn(ft.Text("Status")),
                        ft.DataColumn(ft.Text("Updated")),
                        ft.DataColumn(ft.Text("Actions")),
                    ],
                    rows=rows,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=20,
        expand=True,
    )


def ContentEditContent(
    page: ft.Page, ctx: ServiceContext, state: AppState, item_id: str | None = None
) -> ft.Control:
    # State for form
    is_new = item_id == "new" or item_id is None

    # Load item if editing
    item = None
    if not is_new and item_id:
        try:
            item = ctx.content_service.repo.get_by_id(uuid.UUID(item_id))
        except Exception:
            return ft.Text("Item not found", color="red")

    # Form Controls
    title_field = ft.TextField(label="Title", value=item.title if item else "")
    slug_field = ft.TextField(label="Slug", value=item.slug if item else "")
    summary_field = ft.TextField(
        label="Summary", value=item.summary if item else "", multiline=True
    )

    blocks_col = ft.Column(spacing=10)
    current_blocks: list[ContentBlock] = item.blocks if item and item.blocks else []

    def render_blocks() -> None:
        blocks_col.controls.clear()
        for i, block in enumerate(current_blocks):
            if block.block_type == "markdown":
                val = block.data_json.get("text", "")

                def on_change(e: ft.ControlEvent, idx: int = i) -> None:
                    current_blocks[idx].data_json["text"] = e.control.value

                blocks_col.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(f"Block {i + 1}: Markdown", weight=ft.FontWeight.BOLD),
                                    ft.TextField(
                                        value=val, multiline=True, min_lines=3, on_change=on_change
                                    ),
                                    ft.IconButton(
                                        ft.Icons.DELETE, on_click=lambda _, idx=i: delete_block(idx)
                                    ),
                                ]
                            ),
                            padding=10,
                        )
                    )
                )
        page.update()

    def delete_block(idx: int) -> None:
        current_blocks.pop(idx)
        render_blocks()

    def add_text_block(_: ft.ControlEvent) -> None:
        current_blocks.append(ContentBlock(block_type="markdown", data_json={"text": ""}))
        render_blocks()

    render_blocks()

    def save(_: ft.ControlEvent) -> None:
        try:
            nonlocal item
            if not title_field.value:
                raise ValueError("Title is required")
            now = datetime.now(UTC)

            if is_new:
                if not state.current_user:
                    raise ValueError("Not logged in")

                new_item = ContentItem(
                    owner_user_id=state.current_user.id,
                    type="post",
                    title=title_field.value,
                    slug=slug_field.value or title_field.value.lower().replace(" ", "-"),
                    status="draft",
                    summary=summary_field.value,
                    blocks=current_blocks,
                    created_at=now,
                    updated_at=now,
                )
                created = ctx.content_service.create_item(state.current_user, new_item)
                page.snack_bar = ft.SnackBar(ft.Text("Created!"))
                page.snack_bar.open = True
                page.go(f"/admin/content/{created.id}")
            else:
                if not item:
                    return
                updated_item = item.model_copy(
                    update={
                        "title": title_field.value,
                        "slug": slug_field.value,
                        "summary": summary_field.value,
                        "blocks": current_blocks,
                        "updated_at": now,
                    }
                )
                if not state.current_user:
                    raise ValueError("Not logged in")

                ctx.content_service.update_item(state.current_user, updated_item)
                page.snack_bar = ft.SnackBar(ft.Text("Saved!"))
                page.snack_bar.open = True
                page.update()

        except Exception as e:
            logger.error(f"Save error: {e}")
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {e}"))
            page.snack_bar.open = True
            page.update()

    def share_click(_: ft.ControlEvent) -> None:
        if not item:
            return
        # Simple share: copy link to clipboard
        link = f"/post/{item.id}"
        page.set_clipboard(link)
        page.snack_bar = ft.SnackBar(ft.Text(f"Public link copied: {link}"))
        page.snack_bar.open = True
        page.update()

    def publish_now(_: ft.ControlEvent) -> None:
        """Publish content immediately (draft -> published)."""
        if not item or not state.current_user:
            return
        try:
            ctx.publish_service.publish_now(state.current_user, item.id)
            page.snack_bar = ft.SnackBar(ft.Text("Published successfully!"))
            page.snack_bar.open = True
            # Refresh the page to show updated status
            page.go(f"/admin/content/{item.id}")
        except PermissionError as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"Permission denied: {e}"))
            page.snack_bar.open = True
            page.update()
        except Exception as e:
            logger.error(f"Publish error: {e}")
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {e}"))
            page.snack_bar.open = True
            page.update()

    # Schedule functionality with date/time picker
    selected_date: datetime | None = None

    def on_date_picked(e: ft.ControlEvent) -> None:
        """Handle date selection, then show time picker."""
        nonlocal selected_date
        if e.control.value:
            selected_date = e.control.value
            # Flet 0.28: use open property instead of pick_time()
            time_picker.open = True
            page.update()

    def on_time_picked(e: ft.ControlEvent) -> None:
        """Handle time selection and schedule the content."""
        if not item or not state.current_user or not selected_date:
            return
        if e.control.value:
            schedule_dt = datetime.combine(selected_date.date(), e.control.value)
            try:
                ctx.publish_service.schedule(state.current_user, item.id, schedule_dt)
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Scheduled for {schedule_dt.strftime('%Y-%m-%d %H:%M')}")
                )
                page.snack_bar.open = True
                page.go(f"/admin/content/{item.id}")
            except ValueError as err:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {err}"))
                page.snack_bar.open = True
                page.update()
            except PermissionError as err:
                page.snack_bar = ft.SnackBar(ft.Text(f"Permission denied: {err}"))
                page.snack_bar.open = True
                page.update()

    date_picker = ft.DatePicker(on_change=on_date_picked)
    time_picker = ft.TimePicker(on_change=on_time_picked)
    page.overlay.extend([date_picker, time_picker])

    def schedule_click(_: ft.ControlEvent) -> None:
        """Open date picker to start scheduling flow."""
        # Flet 0.28: use open property instead of pick_date()
        date_picker.open = True
        page.update()

    def unpublish(_: ft.ControlEvent) -> None:
        """Unpublish content (published/scheduled -> draft)."""
        if not item or not state.current_user:
            return
        try:
            ctx.publish_service.unpublish(state.current_user, item.id)
            page.snack_bar = ft.SnackBar(ft.Text("Moved to draft."))
            page.snack_bar.open = True
            page.go(f"/admin/content/{item.id}")
        except PermissionError as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"Permission denied: {e}"))
            page.snack_bar.open = True
            page.update()
        except Exception as e:
            logger.error(f"Unpublish error: {e}")
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {e}"))
            page.snack_bar.open = True
            page.update()

    # Determine content status for button logic
    current_status = item.status if item else "draft"
    can_publish = not is_new and current_status == "draft"
    can_unpublish = not is_new and current_status in ("published", "scheduled")

    # Status badge colors
    status_colors = {
        "draft": ("grey", "Draft"),
        "scheduled": ("orange", "Scheduled"),
        "published": ("green", "Published"),
        "archived": ("red", "Archived"),
    }
    badge_color, badge_text = status_colors.get(current_status, ("grey", current_status))

    def preview_click(_: ft.ControlEvent) -> None:
        """Open preview of content in public view."""
        if not item:
            return
        # Navigate to the public post view by ID (admin can see drafts)
        page.go(f"/post/{item.id}")

    # Build action buttons
    action_buttons = [
        ft.ElevatedButton("Share", icon=ft.Icons.SHARE, on_click=share_click),
        ft.ElevatedButton("Save", icon=ft.Icons.SAVE, on_click=save),
    ]
    # Preview is available for all existing items (not just drafts)
    if not is_new and item:
        action_buttons.insert(
            0, ft.ElevatedButton("Preview", icon=ft.Icons.PREVIEW, on_click=preview_click)
        )
    if can_unpublish:
        action_buttons.insert(
            0, ft.ElevatedButton("Unpublish", icon=ft.Icons.UNPUBLISHED, on_click=unpublish)
        )
    if can_publish:
        action_buttons.insert(
            0, ft.ElevatedButton("Schedule", icon=ft.Icons.SCHEDULE, on_click=schedule_click)
        )
        action_buttons.insert(
            0,
            ft.ElevatedButton(
                "Publish Now",
                icon=ft.Icons.PUBLISH,
                on_click=publish_now,
                bgcolor="primary",
                color="onPrimary",
            ),
        )

    # Status badge for non-new items
    status_badge = None
    if not is_new and item:
        status_badge = ft.Container(
            content=ft.Text(badge_text, size=12, color="white"),
            bgcolor=badge_color,
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            border_radius=12,
        )

    # Header row with title and status
    header_content = [ft.Text("Edit Content", size=24, weight=ft.FontWeight.BOLD, color="primary")]
    if status_badge:
        header_content.append(status_badge)

    # Layout
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [ft.Row(header_content, spacing=10), ft.Row(action_buttons)],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(),
                ft.Container(
                    content=ft.Column(
                        [
                            title_field,
                            slug_field,
                            summary_field,
                            ft.Divider(),
                            ft.Text("Content Blocks", size=16, weight=ft.FontWeight.BOLD),
                            blocks_col,
                            ft.Row(
                                [
                                    ft.ElevatedButton(
                                        "Add Markdown",
                                        icon=ft.Icons.TEXT_FIELDS,
                                        on_click=add_text_block,
                                    ),
                                ]
                            ),
                        ],
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    expand=True,
                ),
            ]
        ),
        padding=20,
        expand=True,
    )
