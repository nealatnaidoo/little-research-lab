
import flet as ft


class AppTheme:
    """
    Centralized theme configuration for the application.
    Implements a 'Science/Tech' aesthetic with deep blues and teals.
    """
    
    # Fonts
    font_family = "Inter" # Requires Google Fonts loading or system font
    
    # Colors - Light
    primary_light = "#2c3e50" # Deep Blue Gray
    on_primary_light = "#ffffff"
    secondary_light = "#16a085" # Teal
    background_light = "#f8f9fa"
    surface_light = "#ffffff"
    error_light = "#e74c3c"
    
    # Colors - Dark
    primary_dark = "#34495e"
    on_primary_dark = "#ecf0f1"
    secondary_dark = "#1abc9c"
    background_dark = "#121212"
    surface_dark = "#1e1e1e"
    
    @classmethod
    def light_theme(cls) -> ft.Theme:
        return ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=cls.primary_light,
                on_primary=cls.on_primary_light,
                secondary=cls.secondary_light,
                background=cls.background_light,
                surface=cls.surface_light,
                error=cls.error_light,
            ),
            font_family=cls.font_family,
            use_material3=True,
            # visual_density=ft.ThemeVisualDensity.COMFORTABLE,  # Removed to fix test environment issue
        )

    @classmethod
    def dark_theme(cls) -> ft.Theme:
        return ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=cls.primary_dark,
                on_primary=cls.on_primary_dark,
                secondary=cls.secondary_dark,
                background=cls.background_dark,
                surface=cls.surface_dark,
                error=cls.error_light, # Keep red for error
                # brightness=ft.Brightness.DARK,
            ),
            font_family=cls.font_family,
            use_material3=True, 
            # visual_density=ft.ThemeVisualDensity.COMFORTABLE,
        )
