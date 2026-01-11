import hashlib
import json
from unittest.mock import Mock

import pytest

from src.adapters.render.mpl_renderer import MatplotlibRenderer


@pytest.fixture
def mock_store():
    return Mock()

@pytest.fixture
def renderer(mock_store):
    return MatplotlibRenderer(mock_store)

def test_render_chart_cache_miss(renderer, mock_store):
    spec = {
        "type": "bar",
        "title": "Test Chart",
        "data": {"x": ["A", "B"], "y": [1, 2]}
    }
    
    # Setup cache miss
    mock_store.get.side_effect = FileNotFoundError 
    
    # Act
    data = renderer.render_chart(spec)
    
    # Assert
    assert data is not None
    assert len(data) > 0
    # PNG signature: 89 50 4E 47 0D 0A 1A 0A
    assert data.startswith(b"\x89PNG")
    
    # Verify save called
    # Calculate expected key
    spec_str = json.dumps(spec, sort_keys=True)
    h_input = f"{spec_str}|800|600|100"
    digest = hashlib.md5(h_input.encode("utf-8")).hexdigest()
    expected_key = f"charts/{digest}.png"
    
    mock_store.save.assert_called_once_with(expected_key, data)

def test_render_chart_cache_hit(renderer, mock_store):
    spec = {"type": "line", "data": {"x": [1, 2], "y": [1, 2]}}
    cached_bytes = b"fake_png_data"
    
    # Setup cache hit
    mock_store.get.return_value = cached_bytes
    
    # Act
    data = renderer.render_chart(spec)
    
    # Assert
    assert data == cached_bytes
    mock_store.save.assert_not_called()
    
def test_render_supported_types(renderer, mock_store):
    # Just ensure no exceptions for supported types
    mock_store.get.side_effect = FileNotFoundError
    
    for t in ["bar", "line", "scatter"]:
        spec = {
            "type": t,
            "data": {"x": [1, 2, 3], "y": [4, 5, 6]}
        }
        data = renderer.render_chart(spec)
        assert data.startswith(b"\x89PNG")
