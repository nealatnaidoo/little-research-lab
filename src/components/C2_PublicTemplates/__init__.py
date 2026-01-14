"""
C2-PublicTemplates: Public template rendering component.

Provides SSR metadata generation, link sanitization, and content validation
for public-facing templates (posts, resources, link hubs).

Spec refs: E2.1, E2.2, TA-E2.1-01, TA-E2.1-03, R2, R6
"""

import importlib

from src.components.C2_PublicTemplates.fc import (
    AccessibilityCheckResult,
    CachePolicy,
    CachePolicyValidation,
    LinkHubConfig,
    LinkHubGroup,
    LinkHubItem,
    LinkHubRenderData,
    LinkInfo,
    ResourceInfo,
    ResourceRenderConfig,
    SiteConfig,
    SitemapEntry,
    SSRMetadata,
    ValidationResult,
    determine_cache_policy,
    extract_first_paragraph,
    extract_links,
    filter_sitemap_entries,
    format_file_size,
    format_page_count,
    format_publish_date,
    generate_asset_cache_headers,
    generate_cache_headers,
    generate_cache_tag,
    generate_cache_tags,
    generate_canonical_url,
    generate_link_hub_metadata,
    generate_link_hub_render_data,
    generate_og_image_url,
    generate_resource_metadata,
    generate_resource_render_config,
    generate_resource_urls,
    generate_ssr_metadata,
    group_link_hub_items,
    is_external_link,
    prepare_link_hub_item,
    sanitize_external_links,
    should_include_in_sitemap,
    supports_pdf_embed,
    truncate_description,
    validate_cache_policy_r2,
    validate_content_visibility,
    validate_link_hub_accessibility,
    validate_prose_structure,
)

# Import IS module (named 'is' which is a Python keyword, so use importlib)
_is_module = importlib.import_module("src.components.C2_PublicTemplates.is")
RevalidationAdapter = _is_module.RevalidationAdapter
RevalidationPort = _is_module.RevalidationPort
RevalidationResult = _is_module.RevalidationResult
StubRevalidationAdapter = _is_module.StubRevalidationAdapter

__all__ = [
    # Data classes
    "SSRMetadata",
    "SiteConfig",
    "LinkInfo",
    "ValidationResult",
    "ResourceInfo",
    "ResourceRenderConfig",
    "LinkHubConfig",
    "LinkHubItem",
    "LinkHubGroup",
    "LinkHubRenderData",
    "AccessibilityCheckResult",
    "CachePolicy",
    "CachePolicyValidation",
    "SitemapEntry",
    # SSR metadata generation
    "generate_ssr_metadata",
    "generate_canonical_url",
    "generate_og_image_url",
    # Link sanitization
    "sanitize_external_links",
    "extract_links",
    "is_external_link",
    # Content validation
    "validate_content_visibility",
    "validate_prose_structure",
    # Template helpers
    "truncate_description",
    "extract_first_paragraph",
    "format_publish_date",
    # Resource template (E2.2)
    "supports_pdf_embed",
    "generate_resource_urls",
    "format_file_size",
    "format_page_count",
    "generate_resource_render_config",
    "generate_resource_metadata",
    # Link hub template (Epic1/Epic2)
    "validate_link_hub_accessibility",
    "prepare_link_hub_item",
    "group_link_hub_items",
    "generate_link_hub_metadata",
    "generate_link_hub_render_data",
    # Caching policy (E2.3)
    "determine_cache_policy",
    "generate_cache_headers",
    "generate_asset_cache_headers",
    "should_include_in_sitemap",
    "filter_sitemap_entries",
    "generate_cache_tag",
    "generate_cache_tags",
    "validate_cache_policy_r2",
    # Revalidation adapter (P3)
    "RevalidationAdapter",
    "RevalidationPort",
    "RevalidationResult",
    "StubRevalidationAdapter",
]
