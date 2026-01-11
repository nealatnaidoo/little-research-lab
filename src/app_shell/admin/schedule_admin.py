import logging

import flet as ft

from src.domain.entities import ContentItem
from src.ui.context import ServiceContext
from src.ui.state import AppState

logger = logging.getLogger(__name__)

def ScheduleView(page: ft.Page, ctx: ServiceContext, state: AppState) -> ft.View:
    
    def fetch_items() -> list[ContentItem]:
        # Ideally the repo supports filtering, but for now we filter in-memory if repo doesn't
        all_items = ctx.content_service.repo.list_items(filters={})
        return [i for i in all_items if i.status == "scheduled"]

    def refresh_data() -> None:
        scheduled_items = fetch_items()
        rows.clear()
        for item in scheduled_items:
            rows.append(ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(item.title)),
                    ft.DataCell(ft.Text(item.updated_at.strftime("%Y-%m-%d %H:%M"))),
                    ft.DataCell(ft.Text("Scheduled")), # Status is known
                ]
            ))
        page.update()

    def run_scheduler(e: ft.ControlEvent) -> None:
        try:
            count = ctx.publish_service.process_due_items()
            page.snack_bar = ft.SnackBar(ft.Text(f"Scheduler ran. Published {count} items."))
            page.snack_bar.open = True
            refresh_data()
        except Exception as err:
            logger.error(f"Scheduler error: {err}")
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {err}"))
            page.snack_bar.open = True
            page.update()

    # Initial Data
    rows: list[ft.DataRow] = []
    refresh_data()

    # Return just the content - MainLayout handles the app bar/navigation
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Schedule Management", size=24, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton(
                    "Run Scheduler Now",
                    icon=ft.Icons.UPDATE,
                    on_click=run_scheduler
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Title")),
                    ft.DataColumn(ft.Text("Scheduled For")),
                    # Note: updated_at used as proxy for sched time in MVP
                    ft.DataColumn(ft.Text("Status")),
                ],
                rows=rows,
            ),
            ft.Text(
                "Note: Items in 'scheduled' status will be published when their "
                "designated time (currently using updated_at) is passed.",
                size=12,
                italic=True
            )
        ], scroll=ft.ScrollMode.AUTO),
        padding=20,
        expand=True
    )
