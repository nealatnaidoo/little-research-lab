"""
Render component - SSR metadata builder.

Spec refs: E1.2
"""

# Re-exports from _impl for backwards compatibility
# Note: PageMetadata from _impl is used to ensure type consistency with RenderService
from ._impl import (
    PageMetadata,
    RenderService,
    create_render_service,
)
from .component import (
    run,
    run_content_metadata,
    run_homepage_metadata,
    run_page_metadata,
)
from .models import (
    MetaTag,
    RenderContentMetadataInput,
    RenderHomepageMetadataInput,
    RenderOutput,
    RenderPageMetadataInput,
    RenderValidationError,
)
from .ports import RulesPort, SettingsPort

__all__ = [
    # Entry points
    "run",
    "run_content_metadata",
    "run_homepage_metadata",
    "run_page_metadata",
    # Input models
    "RenderContentMetadataInput",
    "RenderHomepageMetadataInput",
    "RenderPageMetadataInput",
    # Output models
    "MetaTag",
    "PageMetadata",
    "RenderOutput",
    "RenderValidationError",
    # Ports
    "RulesPort",
    "SettingsPort",
    # Legacy _impl re-exports
    "RenderService",
    "create_render_service",
]
