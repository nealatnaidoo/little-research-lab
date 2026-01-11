import flet as ft
from datetime import datetime
import uuid
from src.ui.theme import AppTheme
from src.ui.state import AppState
from src.domain.entities import User

def test_app_theme_modes():
    """Test that AppTheme returns correct color schemes for modes."""
    # Test Light
    light = AppTheme.light_theme()
    assert light.color_scheme.primary == AppTheme.primary_light

    # Test Dark
    dark = AppTheme.dark_theme()
    assert dark.color_scheme.primary == AppTheme.primary_dark
    # assert dark.color_scheme.brightness == ft.Brightness.DARK

def test_app_state_logout():
    """Test AppState logout clears user."""
    state = AppState()
    # Mock user with valid fields
    user = User(
        id=uuid.uuid4(),
        email="test@test.com",
        display_name="Test",
        password_hash="pw",
        roles=[],
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    state.current_user = user
    assert state.current_user is not None
    
    state.logout()
    assert state.current_user is None
