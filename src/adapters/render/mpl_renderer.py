import hashlib
import json
from io import BytesIO
from typing import Any

import matplotlib.figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from src.ports.filestore import FileStorePort


class MatplotlibRenderer:
    def __init__(self, cache_store: FileStorePort):
        self.cache_store = cache_store

    def render_chart(
        self, spec: dict[str, Any], width: int = 800, height: int = 600, dpi: int = 100
    ) -> bytes:
        """
        Renders a chart based on the spec.
        Spec Schema:
        {
            "type": "bar" | "line" | "scatter",
            "title": str,
            "data": {
                "x": list[int|float|str],
                "y": list[int|float]
            },
            "xlabel": str,
            "ylabel": str
        }
        """
        # 1. Compute Hash for Cache
        # Canonical JSON repr
        spec_str = json.dumps(spec, sort_keys=True)
        # Include dim in hash
        hash_input = f"{spec_str}|{width}|{height}|{dpi}"
        digest = hashlib.md5(hash_input.encode("utf-8")).hexdigest()
        cache_key = f"charts/{digest}.png"

        # 2. Check Cache
        try:
            return self.cache_store.get(cache_key)
        except FileNotFoundError:
            pass

        # 3. Render
        fig = matplotlib.figure.Figure(figsize=(width / dpi, height / dpi), dpi=dpi)
        FigureCanvasAgg(fig)  # Attach canvas backend
        ax = fig.add_subplot(111)

        c_type = spec.get("type", "line")
        data = spec.get("data", {})
        x = data.get("x", [])
        y = data.get("y", [])

        if c_type == "bar":
            ax.bar(x, y)
        elif c_type == "scatter":
            ax.scatter(x, y)
        else: # line
            ax.plot(x, y)

        if title := spec.get("title"):
            ax.set_title(title)
        if xlabel := spec.get("xlabel"):
            ax.set_xlabel(xlabel)
        if ylabel := spec.get("ylabel"):
            ax.set_ylabel(ylabel)
            
        fig.tight_layout()

        # 4. Save to Bytes
        buf = BytesIO()
        fig.savefig(buf, format="png")
        png_data = buf.getvalue()
        buf.close()

        # 5. Write to Cache
        self.cache_store.save(cache_key, png_data)

        return png_data
