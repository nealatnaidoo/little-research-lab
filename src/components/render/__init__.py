"""
Render component - SSR metadata builder.

Spec refs: E1.2
"""

# Re-exports from _impl for backwards compatibility
# Note: PageMetadata from _impl is used to ensure type consistency with RenderService
# Re-exports from legacy canonical service (pending migration)
from src.core.services.canonical import (
    CanonicalConfig,
    CanonicalService,
    create_canonical_service,
    normalize_path,
    normalize_url,
)
from src.core.services.canonical import (
    build_canonical_url as build_canonical_url_with_config,
)

# Note: build_canonical_url imported from render.py for (base_url, path) signature
# Use build_canonical_url_with_config for (path, base_url, config) signature
# Re-exports from legacy render service (pending migration)
from src.core.services.render import (
    ImageInfo,
    build_canonical_url,
    get_content_path,
    resolve_og_image,
    truncate_description,
)

# Re-exports from legacy resource_pdf service (pending migration)
from src.core.services.resource_pdf import (
    PinnedPolicy,
    ResourcePDF,
    ResourcePDFService,
    ResourceValidationError,
    create_resource_pdf_service,
    validate_pinned_policy,
    validate_resource_fields,
)

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
    # Legacy canonical re-exports
    "CanonicalConfig",
    "CanonicalService",
    "build_canonical_url",
    "build_canonical_url_with_config",
    "create_canonical_service",
    "normalize_path",
    "normalize_url",
    # Legacy render re-exports
    "ImageInfo",
    "get_content_path",
    "resolve_og_image",
    "truncate_description",
    # Legacy resource_pdf re-exports
    "PinnedPolicy",
    "ResourcePDF",
    "ResourcePDFService",
    "ResourceValidationError",
    "create_resource_pdf_service",
    "validate_pinned_policy",
    "validate_resource_fields",
]
