from typing import Any, Protocol


class RendererPort(Protocol):
    def render_chart(self, spec: dict[str, Any], width: int, height: int, dpi: int) -> bytes:
        """Render a chart spec to image bytes (PNG/SVG)."""
        ...
