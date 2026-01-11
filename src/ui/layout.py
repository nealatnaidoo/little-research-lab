
from collections.abc import Callable
from typing import Any

import flet as ft

from src.ui.state import AppState


class MainLayout(ft.Row): # type: ignore
    """
    The main responsive layout structure.
    - Desktop: NavigationRail (Left) + Content (Right)
    - Mobile: AppBar with Drawer + Content
    """
    def __init__(
        self,
        page: ft.Page,
        app_state: AppState,
        content: ft.Control, # The dynamic view
        on_logout: Callable[[], None],
        on_nav: Callable[[str], None],
        toggle_theme: Callable[[], None],
        current_route: str = "/",
    ):
        super().__init__(expand=True, spacing=0)
        self.page = page
        self.app_state = app_state
        self.on_logout = on_logout
        self.on_nav = on_nav
        self.toggle_theme = toggle_theme
        
        # Determine if we act as admin layout
        is_admin = self.app_state.current_user is not None
        
        # Determine selection
        # Simple heuristic mapping
        idx = None
        if current_route == "/":
            idx = 0
        elif current_route == "/dashboard" and is_admin:
            idx = 1
        elif current_route == "/login" and not is_admin:
            idx = 1
            
        # Navigation Rail (Desktop)
        self.rail = ft.NavigationRail(
            selected_index=idx,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            leading=ft.Container(
                content=ft.Icon(ft.Icons.SCIENCE, size=32, color="primary"),
                padding=20,
            ),
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME,
                    label="Home",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.DASHBOARD_OUTLINED, 
                    selected_icon=ft.Icons.DASHBOARD, 
                    label="Dashboard"
                ),
            ] if is_admin else [
                 ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME,
                    label="Home",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.LOGIN, 
                    label="Login"
                ),
            ],
            on_change=self._rail_change,
            bgcolor="surface",
        )
        
        # Content Wrapper
        self.content_area = ft.Container(
            content=content,
            expand=True,
            padding=20,
            alignment=ft.alignment.top_left,
        )
        
        # AppBar (Floating action for Theme/User)
        self.app_bar = ft.Container(
            content=ft.Row(
                [
                    ft.Text("Research Lab Bio", size=20, weight=ft.FontWeight.BOLD, color="primary"),
                    ft.Container(expand=True),
                    ft.IconButton(
                        ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE,
                        on_click=lambda _: self.toggle_theme()
                    ),
                    ft.PopupMenuButton(
                        icon=ft.Icons.PERSON,
                        items=[
                            ft.PopupMenuItem(text="Logout", on_click=lambda _: self.on_logout())
                        ]
                    ) if is_admin else ft.FilledButton(
                        "Login", 
                        icon=ft.Icons.LOGIN,
                        on_click=lambda _: self.on_nav("/login")
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            bgcolor="surfaceVariant",
        )

        # Layout Assembly
        # We start with Rail + Content.
        # Ideally we wrap content in a Column to put AppBar on top
        
        right_panel = ft.Column(
            [
                self.app_bar,
                self.content_area
            ],
            expand=True,
            spacing=0
        )
        
        self.controls = [
            self.rail,
            ft.VerticalDivider(width=1, color="outlineVariant"),
            right_panel
        ]

    def _rail_change(self, e: Any) -> None:
        idx = e.control.selected_index
        # Hardcoded route map for now - improvement: pass routes
        is_admin = self.app_state.current_user is not None
        
        if is_admin:
            if idx == 0:
                self.on_nav("/")
            elif idx == 1:
                self.on_nav("/dashboard")
        else:
            if idx == 0:
                self.on_nav("/")
            elif idx == 1:
                self.on_nav("/login")
