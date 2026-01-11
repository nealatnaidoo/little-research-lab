from typing import Any

import flet as ft


class PremiumCard(ft.Container): # type: ignore
    """
    A unified Card component with hover effects and consistent styling.
    """
    def __init__(
        self,
        content: ft.Control,
        width: float | None = None,
        height: float | None = None,
        padding: float = 20,
        on_click: Any | None = None,
        expand: bool | int = False,
    ):
        super().__init__(
            content=content,
            width=width,
            height=height,
            padding=padding,
            border_radius=ft.border_radius.all(12),
            bgcolor="surfaceVariant", # Adapts to theme
            animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_hover=self._on_hover,
            on_click=on_click,
            expand=expand,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color="#1A000000",
                offset=ft.Offset(0, 4),
            )
        )
        self.original_scale = 1.0
        self.scale = 1.0

    def _on_hover(self, e: ft.HoverEvent) -> None:
        """
        Micro-interaction: Scale up slightly and lift shadow on hover.
        """
        if e.data == "true":
            self.scale = 1.02
            self.shadow.blur_radius = 20
            self.shadow.offset = ft.Offset(0, 8)
            self.shadow.color = "#26000000"
        else:
            self.scale = 1.0
            self.shadow.blur_radius = 10
            self.shadow.offset = ft.Offset(0, 4)
            self.shadow.color = "#1A000000"
        self.update()
