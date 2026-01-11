import logging

import flet as ft

from src.ui.components.premium_card import PremiumCard
from src.ui.context import ServiceContext
from src.ui.state import AppState

logger = logging.getLogger(__name__)

def AdminDashboardContent(page: ft.Page, ctx: ServiceContext, state: AppState) -> ft.Control:
    # 1. Health Check
    health_status = "Unknown"
    health_color = "grey"
    try:
        ctx.content_service.repo.list_items(filters={"status": "published"}) 
        health_status = "Operational"
        health_color = "green"
    except Exception as e:
        health_status = f"Error: {e}"
        health_color = "error"
    
    # 2. Stats
    items = ctx.content_service.repo.list_items(filters={})
    stats = {
        "draft": 0,
        "published": 0,
        "scheduled": 0,
        "archived": 0
    }
    for i in items:
        if i.status in stats:
            stats[i.status] += 1
            
    # Helper for Stat Card
    def curr_stat(label: str, value: int, icon: str, color: str) -> ft.Control:
        return PremiumCard(
            content=ft.Column(
                [
                    ft.Icon(name=icon, size=30, color=color),
                    ft.Text(str(value), size=30, weight=ft.FontWeight.BOLD),
                    ft.Text(label, size=14, color="onSurfaceVariant")
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            width=160,
            height=160
        )

    # 3. UI
    return ft.Container(
        content=ft.Column([
            # Header
            ft.Text("Dashboard", size=28, weight=ft.FontWeight.BOLD, color="primary"),
            ft.Divider(),
            
            # Health
            PremiumCard(
                content=ft.Row([
                    ft.Icon(ft.Icons.HEALTH_AND_SAFETY, color=health_color, size=30),
                    ft.Column([
                        ft.Text("System Status", size=14, color="onSurfaceVariant"),
                        ft.Text(health_status, size=18, weight=ft.FontWeight.BOLD)
                    ])
                ], alignment=ft.MainAxisAlignment.START),
                padding=20
            ),
            
            # Navigation / Actions
            ft.Text("Quick Actions", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.ElevatedButton(
                    "Content", 
                    icon=ft.Icons.ARTICLE, 
                    on_click=lambda _: page.go("/admin/content")
                ),
                ft.ElevatedButton(
                    "Assets", 
                    icon=ft.Icons.IMAGE, 
                    on_click=lambda _: page.go("/admin/assets")
                ),
                ft.ElevatedButton(
                    "Schedule", 
                    icon=ft.Icons.SCHEDULE, 
                    on_click=lambda _: page.go("/admin/schedule")
                ),
                ft.ElevatedButton(
                    "Users", 
                    icon=ft.Icons.PEOPLE, 
                    on_click=lambda _: page.go("/admin/users")
                ),
            ], wrap=True),
            
            ft.Divider(),
            
            # Stats
            ft.Text("Overview", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([
                curr_stat("Drafts", stats["draft"], ft.Icons.EDIT_DOCUMENT, "orange"),
                curr_stat("Scheduled", stats["scheduled"], ft.Icons.SCHEDULE, "blue"),
                curr_stat("Published", stats["published"], ft.Icons.PUBLIC, "green"),
                curr_stat("Archived", stats["archived"], ft.Icons.ARCHIVE, "grey"),
            ], wrap=True)
        ], scroll=ft.ScrollMode.AUTO),
        padding=20,
        expand=True
    )
