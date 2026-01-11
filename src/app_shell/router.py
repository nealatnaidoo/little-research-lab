import logging
import re
from collections.abc import Callable
from typing import Any, NamedTuple

import flet as ft

from src.ui.state import AppState

logger = logging.getLogger(__name__)

class RouteConfig(NamedTuple):
    # builder accepts page and **kwargs
    builder: Callable[..., ft.View] 
    protected: bool

class Router:
    def __init__(self, page: ft.Page, state: AppState):
        self.page = page
        self.state = state
        self.routes: dict[str, RouteConfig] = {}
        # Simple dynamic routes: regex -> config
        self.dynamic_routes: dict[str, RouteConfig] = {}
        
    def register(
        self, 
        route: str, 
        builder: Callable[..., ft.View], 
        protected: bool = True
    ) -> None:
        self.routes[route] = RouteConfig(builder, protected)
        
    def register_dynamic(
        self,
        pattern: str,
        builder: Callable[..., ft.View],
        protected: bool = True
    ) -> None:
        """Register a regex pattern route. 
        Example: '^/post/(?P<item_id>.+)$'
        The builder will receive regex group dict as kwargs.
        """
        self.dynamic_routes[pattern] = RouteConfig(builder, protected)
        
    def handle_route_change(self, e: ft.RouteChangeEvent) -> None:
        route = e.route or "/"  # Default empty route to "/"
        logger.info(f"Navigate to: {route}")
        
        # Clear existing views
        self.page.views.clear()
        
        # 1. Exact Match
        config = self.routes.get(route)
        kwargs: dict[str, Any] = {}
        
        # 2. Dynamic Match
        if not config:
            for pattern, dyn_config in self.dynamic_routes.items():
                match = re.match(pattern, route)
                if match:
                    config = dyn_config
                    kwargs = match.groupdict()
                    break
        
        if not config:
            # 404 - no matching route found
            logger.warning(f"No route found for: {route}")
            self.page.views.append(
                ft.View(
                    "/404",
                    [ft.AppBar(title=ft.Text("404")), ft.Text(f"Page not found: {route}")]
                )
            )
            self.page.update()
            return

        # Auth Guard
        if config.protected and not self.state.current_user:
            logger.info(f"Access denied to {route}. Redirecting to /login.")
            self.page.go("/login")
            return
            
        # Build View
        # Pass page first, then kwargs
        try:
            view = config.builder(self.page, **kwargs)
            self.page.views.append(view)
            self.page.update()
        except TypeError as err:
            logger.error(f"Error building view for {route}: {err}")
            # Fallback error view?
            self.page.views.append(ft.View("/error", [ft.Text(f"Error: {err}")]))
            self.page.update()
        
    def view_pop(self, view: ft.View) -> None:
        self.page.views.pop()
        top_view = self.page.views[-1]
        self.page.go(top_view.route)
