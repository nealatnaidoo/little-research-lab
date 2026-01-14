from datetime import UTC, datetime

import flet as ft

from src.ui.components.premium_card import PremiumCard
from src.ui.context import ServiceContext
from src.ui.state import AppState


def PublicHomeContent(page: ft.Page, ctx: ServiceContext, state: AppState) -> ft.Control:
    # 1. Fetch Data
    all_items = ctx.content_service.repo.list_items(filters={})
    now = datetime.now(UTC)
    published_items = [
        item
        for item in all_items
        if item.status == "published"
        and (item.published_at is None or item.published_at <= now)
    ]
    published_items.sort(key=lambda x: x.published_at or datetime.min, reverse=True)

    all_links = ctx.link_repo.get_all()
    public_links = [
        link for link in all_links if link.visibility == "public" and link.status == "active"
    ]

    # 2. UI Components

    # Links Section
    files_grid = ft.GridView(
        expand=False,
        runs_count=5,
        max_extent=150,
        child_aspect_ratio=1.0,
        spacing=10,
        run_spacing=10,
    )

    for link in public_links:
        # Premium Card for Link
        card = PremiumCard(
            content=ft.Column(
                [
                    ft.Icon(name=link.icon or "link", size=30, color="primary"),
                    ft.Text(link.title, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            on_click=lambda _, url=link.url: page.launch_url(str(url)),
        )
        files_grid.controls.append(card)

    # Posts Section
    posts_list = ft.ListView(expand=True, spacing=10, padding=10)

    if not published_items:
        posts_list.controls.append(ft.Text("No updates yet.", italic=True))

    for item in published_items:
        sub_text = item.summary or "No summary"
        date_str = item.published_at.strftime("%Y-%m-%d") if item.published_at else ""

        tile = PremiumCard(
            content=ft.Column(
                [
                    ft.Text(item.title, size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{date_str} • {sub_text}", size=12, color="onSurfaceVariant"),
                ]
            ),
            on_click=lambda _, pid=str(item.id): page.go(f"/post/{pid}"),
        )
        posts_list.controls.append(tile)

    # Layout
    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Quick Links", size=20, weight=ft.FontWeight.BOLD, color="primary"),
                files_grid,
                ft.Divider(),
                ft.Text("Latest Updates", size=20, weight=ft.FontWeight.BOLD, color="primary"),
                posts_list,
            ]
        ),
        padding=10,
        expand=True,
    )
