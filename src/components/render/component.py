"""
Render component - SSR metadata builder.

Spec refs: E1.2
Test assertions: TA-0004, TA-0005

Builds deterministic page metadata from content + settings for public SSR pages.

Invariants:
- I1: Output is sanitized HTML (no XSS)
- I2: Only allowed tags in output
- I3: URLs are validated
- I4: Heading extraction preserves hierarchy
"""

from __future__ import annotations

from ._impl import (
    PageMetadata as LegacyPageMetadata,
)
from ._impl import (
    RenderService,
)
from .models import (
    MetaTag,
    PageMetadata,
    RenderContentMetadataInput,
    RenderHomepageMetadataInput,
    RenderOutput,
    RenderPageMetadataInput,
)
from .ports import RulesPort, SettingsPort


def _convert_metadata(legacy: LegacyPageMetadata) -> PageMetadata:
    """Convert legacy page metadata to component model."""
    extra_meta = tuple(
        MetaTag(name=m.name, property=m.property, content=m.content) for m in legacy.extra_meta
    )
    return PageMetadata(
        title=legacy.title,
        description=legacy.description,
        canonical_url=legacy.canonical_url,
        robots=legacy.robots,
        og_title=legacy.og_title,
        og_description=legacy.og_description,
        og_type=legacy.og_type,
        og_url=legacy.og_url,
        og_image=legacy.og_image,
        og_image_alt=legacy.og_image_alt,
        og_site_name=legacy.og_site_name,
        twitter_card=legacy.twitter_card,
        twitter_title=legacy.twitter_title,
        twitter_description=legacy.twitter_description,
        twitter_image=legacy.twitter_image,
        twitter_image_alt=legacy.twitter_image_alt,
        extra_meta=extra_meta,
    )


def _create_service(
    settings_port: SettingsPort | None,
    rules: RulesPort | None,
) -> RenderService:
    """Create render service from ports."""
    base_url = settings_port.get_base_url() if settings_port else "http://localhost"
    default_og = settings_port.get_default_og_image_url() if settings_port else None
    routing_config = rules.get_routing_config() if rules else {}

    return RenderService(
        base_url=base_url,
        default_og_image_url=default_og,
        routing_config=routing_config,
    )


# --- Component Entry Points ---


def run_page_metadata(
    inp: RenderPageMetadataInput,
    *,
    settings_port: SettingsPort | None = None,
    rules: RulesPort | None = None,
) -> RenderOutput:
    """
    Build complete page metadata (TA-0004).

    Args:
        inp: Input containing settings, optional content, and overrides.
        settings_port: Optional settings port for configuration.
        rules: Optional rules port for routing configuration.

    Returns:
        RenderOutput with page metadata.
    """
    service = _create_service(settings_port, rules)

    legacy_metadata = service.build_page_metadata(
        settings=inp.settings,
        content=inp.content,
        path=inp.path,
        page_title=inp.page_title,
        page_description=inp.page_description,
        og_image_url=inp.og_image_url,
    )

    metadata = _convert_metadata(legacy_metadata)

    return RenderOutput(
        metadata=metadata,
        errors=[],
        success=True,
    )


def run_content_metadata(
    inp: RenderContentMetadataInput,
    *,
    settings_port: SettingsPort | None = None,
    rules: RulesPort | None = None,
) -> RenderOutput:
    """
    Build metadata for a content page (TA-0004).

    Args:
        inp: Input containing settings and content.
        settings_port: Optional settings port for configuration.
        rules: Optional rules port for routing configuration.

    Returns:
        RenderOutput with content metadata.
    """
    service = _create_service(settings_port, rules)

    legacy_metadata = service.build_content_metadata(
        settings=inp.settings,
        content=inp.content,
        og_image_url=inp.og_image_url,
    )

    metadata = _convert_metadata(legacy_metadata)

    return RenderOutput(
        metadata=metadata,
        errors=[],
        success=True,
    )


def run_homepage_metadata(
    inp: RenderHomepageMetadataInput,
    *,
    settings_port: SettingsPort | None = None,
    rules: RulesPort | None = None,
) -> RenderOutput:
    """
    Build metadata for the homepage (TA-0004, TA-0005).

    Args:
        inp: Input containing settings and optional OG image.
        settings_port: Optional settings port for configuration.
        rules: Optional rules port for routing configuration.

    Returns:
        RenderOutput with homepage metadata.
    """
    service = _create_service(settings_port, rules)

    legacy_metadata = service.build_homepage_metadata(
        settings=inp.settings,
        og_image_url=inp.og_image_url,
    )

    metadata = _convert_metadata(legacy_metadata)

    return RenderOutput(
        metadata=metadata,
        errors=[],
        success=True,
    )


def run(
    inp: RenderPageMetadataInput | RenderContentMetadataInput | RenderHomepageMetadataInput,
    *,
    settings_port: SettingsPort | None = None,
    rules: RulesPort | None = None,
) -> RenderOutput:
    """
    Main entry point for the render component.

    Dispatches to appropriate handler based on input type.

    Args:
        inp: Input object determining the operation.
        settings_port: Optional settings port for configuration.
        rules: Optional rules port for routing configuration.

    Returns:
        RenderOutput with page metadata.
    """
    if isinstance(inp, RenderPageMetadataInput):
        return run_page_metadata(inp, settings_port=settings_port, rules=rules)
    elif isinstance(inp, RenderContentMetadataInput):
        return run_content_metadata(inp, settings_port=settings_port, rules=rules)
    elif isinstance(inp, RenderHomepageMetadataInput):
        return run_homepage_metadata(inp, settings_port=settings_port, rules=rules)
    else:
        raise ValueError(f"Unknown input type: {type(inp)}")
