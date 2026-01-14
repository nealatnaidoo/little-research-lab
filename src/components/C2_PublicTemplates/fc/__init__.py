"""
C2-PublicTemplates Functional Core: Pure template rendering functions.

No I/O operations - all functions are pure and deterministic.
Implements SSR metadata generation and link sanitization per E2.1 spec.

Spec refs: E2.1, TA-E2.1-01, TA-E2.1-03, R2, R6
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse


def _get_now_fallback() -> datetime:
    """Get current time via adapter when `now` parameter is not provided.

    This maintains backward compatibility while satisfying deterministic core principle.
    Callers should prefer passing an explicit `now` parameter for full determinism.
    """
    from src.adapters.time_london import LondonTimeAdapter

    return LondonTimeAdapter().now_utc()


@dataclass
class SiteConfig:
    """Site-level configuration for template rendering."""

    base_url: str
    site_name: str
    default_og_image: str | None = None
    twitter_handle: str | None = None


@dataclass
class SSRMetadata:
    """Complete SSR metadata for a page."""

    title: str
    description: str
    canonical_url: str
    og_title: str
    og_description: str
    og_type: str
    og_url: str
    og_image: str | None
    og_site_name: str
    twitter_card: str
    twitter_title: str
    twitter_description: str
    twitter_image: str | None
    twitter_site: str | None
    published_time: str | None = None
    modified_time: str | None = None


@dataclass
class LinkInfo:
    """Information about a link in content."""

    href: str
    text: str
    rel: str
    is_external: bool
    position: int


@dataclass
class ValidationResult:
    """Result of content validation."""

    is_valid: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# METADATA GENERATION (TA-E2.1-01)
# ═══════════════════════════════════════════════════════════════════════════


def generate_canonical_url(slug: str, base_url: str) -> str:
    """
    Generate canonical URL for content.

    Invariant I4: Canonical URLs must be absolute and use HTTPS.

    Args:
        slug: Content slug
        base_url: Site base URL

    Returns:
        Absolute canonical URL
    """
    # Ensure base_url uses HTTPS
    if base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://", 1)

    # Ensure base_url ends with /
    if not base_url.endswith("/"):
        base_url += "/"

    # Build canonical URL
    return urljoin(base_url, f"p/{slug}")


def generate_og_image_url(
    og_image_id: str | None,
    base_url: str,
    default_image: str | None = None,
) -> str | None:
    """
    Generate OG image URL.

    Invariant I5: Image URLs in metadata must be absolute URLs.

    Args:
        og_image_id: Asset ID for OG image
        base_url: Site base URL
        default_image: Default image URL if no og_image_id

    Returns:
        Absolute image URL or None
    """
    if og_image_id:
        # Ensure HTTPS
        if base_url.startswith("http://"):
            base_url = base_url.replace("http://", "https://", 1)
        if not base_url.endswith("/"):
            base_url += "/"
        return urljoin(base_url, f"assets/{og_image_id}")

    if default_image:
        # Ensure default is absolute
        if default_image.startswith("/"):
            if base_url.startswith("http://"):
                base_url = base_url.replace("http://", "https://", 1)
            return urljoin(base_url, default_image)
        return default_image

    return None


def generate_ssr_metadata(
    title: str,
    slug: str,
    description: str | None,
    og_image_id: str | None,
    published_at: datetime | None,
    updated_at: datetime | None,
    site_config: SiteConfig,
    content_type: str = "article",
) -> SSRMetadata:
    """
    Generate complete SSR metadata for a content page.

    Invariant I2: OG metadata must match actual content.

    Args:
        title: Content title
        slug: Content slug
        description: Content description/summary
        og_image_id: Asset ID for OG image
        published_at: Publication timestamp
        updated_at: Last update timestamp
        site_config: Site configuration
        content_type: Type of content (article, resource)

    Returns:
        Complete SSRMetadata for the page
    """
    canonical = generate_canonical_url(slug, site_config.base_url)
    og_image = generate_og_image_url(
        og_image_id,
        site_config.base_url,
        site_config.default_og_image,
    )

    # Truncate description for meta tags
    meta_description = truncate_description(description or "", 160)
    og_description = truncate_description(description or "", 200)

    # Format timestamps
    published_time = None
    modified_time = None
    if published_at:
        published_time = published_at.isoformat()
    if updated_at:
        modified_time = updated_at.isoformat()

    return SSRMetadata(
        title=title,
        description=meta_description,
        canonical_url=canonical,
        og_title=title,
        og_description=og_description,
        og_type=content_type,
        og_url=canonical,
        og_image=og_image,
        og_site_name=site_config.site_name,
        twitter_card="summary_large_image" if og_image else "summary",
        twitter_title=title,
        twitter_description=og_description,
        twitter_image=og_image,
        twitter_site=site_config.twitter_handle,
        published_time=published_time,
        modified_time=modified_time,
    )


# ═══════════════════════════════════════════════════════════════════════════
# LINK SANITIZATION (TA-E2.1-03, R6)
# ═══════════════════════════════════════════════════════════════════════════

# Pattern to match anchor tags
ANCHOR_PATTERN = re.compile(
    r'<a\s+([^>]*?)href=["\']([^"\']+)["\']([^>]*)>',
    re.IGNORECASE | re.DOTALL,
)

# Pattern to extract rel attribute
REL_PATTERN = re.compile(r'rel=["\']([^"\']*)["\']', re.IGNORECASE)


def is_external_link(href: str, base_url: str | None = None) -> bool:
    """
    Check if a link is external.

    External links are those that:
    - Start with http:// or https:// and point to different domain
    - Start with // (protocol-relative)

    Args:
        href: Link href value
        base_url: Site base URL for comparison

    Returns:
        True if link is external
    """
    # Protocol-relative URLs are always external
    if href.startswith("//"):
        return True

    # Check for absolute URLs
    if href.startswith(("http://", "https://")):
        if not base_url:
            return True

        # Parse and compare domains
        link_parsed = urlparse(href)
        base_parsed = urlparse(base_url)

        return link_parsed.netloc.lower() != base_parsed.netloc.lower()

    # Relative URLs are internal
    return False


def extract_links(html_content: str, base_url: str | None = None) -> list[LinkInfo]:
    """
    Extract all links from HTML content.

    Args:
        html_content: HTML content string
        base_url: Site base URL for external detection

    Returns:
        List of LinkInfo objects
    """
    links: list[LinkInfo] = []
    position = 0

    for match in ANCHOR_PATTERN.finditer(html_content):
        before_href = match.group(1)
        href = match.group(2)
        after_href = match.group(3)

        # Extract rel attribute
        rel = ""
        rel_match = REL_PATTERN.search(before_href + after_href)
        if rel_match:
            rel = rel_match.group(1)

        # Extract link text (simplified - between > and </a>)
        end_pos = match.end()
        close_pos = html_content.find("</a>", end_pos)
        text = ""
        if close_pos > end_pos:
            text = html_content[end_pos:close_pos]
            # Strip HTML tags from text
            text = re.sub(r"<[^>]+>", "", text).strip()

        links.append(
            LinkInfo(
                href=href,
                text=text,
                rel=rel,
                is_external=is_external_link(href, base_url),
                position=position,
            )
        )
        position += 1

    return links


def sanitize_external_links(
    html_content: str,
    base_url: str | None = None,
) -> str:
    """
    Sanitize external links by adding rel="noopener noreferrer".

    Invariant I1: All external links must have rel="noopener noreferrer" (R6).

    Args:
        html_content: HTML content string
        base_url: Site base URL for external detection

    Returns:
        HTML content with sanitized links
    """

    def replace_link(match: re.Match[str]) -> str:
        before_href = match.group(1)
        href = match.group(2)
        after_href = match.group(3)

        # Check if external
        if not is_external_link(href, base_url):
            return match.group(0)  # Return unchanged

        # Check existing rel attribute
        full_attrs = before_href + after_href
        rel_match = REL_PATTERN.search(full_attrs)

        if rel_match:
            # Update existing rel attribute
            existing_rel = set(rel_match.group(1).lower().split())
            existing_rel.add("noopener")
            existing_rel.add("noreferrer")
            new_rel = " ".join(sorted(existing_rel))

            # Split back into before/after href
            if 'rel="' in before_href or "rel='" in before_href:
                new_before = REL_PATTERN.sub(f'rel="{new_rel}"', before_href)
                new_after = after_href
            else:
                new_before = before_href
                new_after = REL_PATTERN.sub(f'rel="{new_rel}"', after_href)

            return f'<a {new_before}href="{href}"{new_after}>'
        else:
            # Add rel attribute
            return f'<a {before_href}href="{href}" rel="noopener noreferrer"{after_href}>'

    return ANCHOR_PATTERN.sub(replace_link, html_content)


# ═══════════════════════════════════════════════════════════════════════════
# CONTENT VALIDATION (R2)
# ═══════════════════════════════════════════════════════════════════════════

VALID_PUBLIC_STATES = {"published"}


def validate_content_visibility(
    state: str,
    published_at: datetime | None,
    now: datetime | None = None,
) -> ValidationResult:
    """
    Validate that content can be publicly visible.

    Invariant I3: Content must not render draft/scheduled state publicly (R2).

    Args:
        state: Content state (draft, scheduled, published, archived)
        published_at: Publication timestamp
        now: Current time for comparison (uses LondonTimeAdapter if None)

    Returns:
        ValidationResult indicating if content is publicly visible
    """
    violations = []

    # Check state
    if state not in VALID_PUBLIC_STATES:
        violations.append(f"Content state '{state}' is not publicly visible")

    # Check published_at for published content
    if state == "published" and published_at:
        if now is None:
            now = _get_now_fallback()

        if published_at > now:
            violations.append("Content publish date is in the future")

    return ValidationResult(
        is_valid=len(violations) == 0,
        violations=violations,
    )


def validate_prose_structure(
    blocks: list[dict[str, Any]],
) -> ValidationResult:
    """
    Validate prose structure for accessibility.

    Checks heading order (no skipped levels) per C1-DesignSystemKit rules.

    Args:
        blocks: Content blocks list

    Returns:
        ValidationResult with any structure violations
    """
    from src.components.C1_DesignSystemKit.fc import validate_heading_order

    # Extract heading levels from blocks
    heading_levels: list[int] = []

    for block in blocks:
        block_type = block.get("block_type", "")
        data = block.get("data_json", {})

        # Check for heading blocks
        if block_type == "heading":
            level = data.get("level", 1)
            heading_levels.append(level)

        # Check for headings in rich text (TipTap format)
        elif block_type == "text" or block_type == "tiptap":
            content = data.get("content", []) or data.get("tiptap", {}).get(
                "content", []
            )
            if isinstance(content, list):
                for node in content:
                    if node.get("type") == "heading":
                        level = node.get("attrs", {}).get("level", 1)
                        heading_levels.append(level)

    # Delegate to C1 design system validation
    c1_result = validate_heading_order(heading_levels)
    # Convert C1 ValidationResult to C2 ValidationResult
    return ValidationResult(
        is_valid=c1_result.is_valid,
        violations=c1_result.violations,
        warnings=c1_result.warnings,
    )


# ═══════════════════════════════════════════════════════════════════════════
# TEMPLATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════


def truncate_description(text: str, max_length: int = 160) -> str:
    """
    Truncate text for meta description.

    Args:
        text: Text to truncate
        max_length: Maximum length (default 160 for SEO)

    Returns:
        Truncated text with ellipsis if needed
    """
    # Strip HTML tags
    clean_text = re.sub(r"<[^>]+>", "", text)
    # Normalize whitespace
    clean_text = " ".join(clean_text.split())
    # Decode HTML entities
    clean_text = html.unescape(clean_text)

    if len(clean_text) <= max_length:
        return clean_text

    # Truncate at word boundary
    truncated = clean_text[: max_length - 3]
    last_space = truncated.rfind(" ")
    if last_space > max_length // 2:
        truncated = truncated[:last_space]

    return truncated + "..."


def extract_first_paragraph(blocks: list[dict[str, Any]]) -> str:
    """
    Extract first paragraph text from content blocks.

    Args:
        blocks: Content blocks list

    Returns:
        First paragraph text or empty string
    """
    for block in blocks:
        block_type = block.get("block_type", "")
        data = block.get("data_json", {})

        if block_type == "text":
            text = str(data.get("text", ""))
            if text:
                return text

        if block_type == "paragraph":
            text = str(data.get("text", ""))
            if text:
                return text

        # Handle TipTap format
        if block_type == "tiptap":
            content = data.get("content", [])
            for node in content:
                if node.get("type") == "paragraph":
                    text_content = node.get("content", [])
                    text_parts = []
                    for part in text_content:
                        if part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                    if text_parts:
                        return " ".join(text_parts)

    return ""


def format_publish_date(
    dt: datetime | None,
    format_string: str = "%B %d, %Y",
) -> str:
    """
    Format publish date for display.

    Args:
        dt: Datetime to format
        format_string: strftime format string

    Returns:
        Formatted date string or empty string
    """
    if dt is None:
        return ""
    return dt.strftime(format_string)


# ═══════════════════════════════════════════════════════════════════════════
# RESOURCE TEMPLATE (E2.2)
# PDF embed/fallback, download links, file metadata
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class ResourceInfo:
    """Information about a resource (PDF) for template rendering."""

    asset_id: str
    filename: str
    mime_type: str
    file_size_bytes: int
    page_count: int | None = None


@dataclass
class ResourceRenderConfig:
    """Configuration for resource template rendering."""

    embed_url: str
    download_url: str
    open_url: str
    file_size_display: str
    page_count_display: str | None
    supports_embed: bool
    fallback_reason: str | None = None


# User agents that don't support inline PDF embed well
# iOS Safari, older mobile browsers, some in-app browsers
EMBED_UNSUPPORTED_PATTERNS = (
    r"iPhone.*Safari",
    r"iPad.*Safari",
    r"iPod.*Safari",
    r"CriOS",  # Chrome on iOS
    r"FxiOS",  # Firefox on iOS
    r"EdgiOS",  # Edge on iOS
    r"FBAN",  # Facebook in-app browser
    r"FBAV",  # Facebook app
    r"Instagram",
    r"LinkedIn",
    r"Twitter",
)

# Compiled pattern for efficiency
_EMBED_UNSUPPORTED_RE = re.compile("|".join(EMBED_UNSUPPORTED_PATTERNS), re.IGNORECASE)


def supports_pdf_embed(user_agent: str | None) -> tuple[bool, str | None]:
    """
    Check if the user agent supports inline PDF embedding.

    iOS Safari and some in-app browsers don't render embedded PDFs well.
    In these cases, we should show download/open fallback prominently.

    Args:
        user_agent: HTTP User-Agent header value

    Returns:
        Tuple of (supports_embed, fallback_reason)
    """
    if not user_agent:
        # Unknown UA - assume embed works
        return True, None

    match = _EMBED_UNSUPPORTED_RE.search(user_agent)
    if match:
        matched_pattern = match.group(0)

        # Determine fallback reason
        if "iPhone" in matched_pattern or "iPad" in matched_pattern:
            reason = "iOS Safari doesn't support inline PDF viewing"
        elif "CriOS" in matched_pattern or "FxiOS" in matched_pattern:
            reason = "iOS browsers don't support inline PDF viewing"
        elif any(
            x in matched_pattern
            for x in ["FBAN", "FBAV", "Instagram", "LinkedIn", "Twitter"]
        ):
            reason = "In-app browsers don't support inline PDF viewing"
        else:
            reason = "Your browser may not support inline PDF viewing"

        return False, reason

    return True, None


def generate_resource_urls(
    asset_id: str,
    base_url: str,
) -> tuple[str, str, str]:
    """
    Generate URLs for resource viewing/downloading.

    Args:
        asset_id: Asset identifier
        base_url: Site base URL

    Returns:
        Tuple of (embed_url, download_url, open_url)
    """
    # Ensure HTTPS and trailing slash
    if base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://", 1)
    if not base_url.endswith("/"):
        base_url += "/"

    # Embed URL - for iframe/object tag
    embed_url = urljoin(base_url, f"assets/{asset_id}")

    # Download URL - with Content-Disposition: attachment
    download_url = urljoin(base_url, f"assets/{asset_id}?download=true")

    # Open URL - opens in new tab (same as embed but for link)
    open_url = embed_url

    return embed_url, download_url, open_url


def format_file_size(size_bytes: int) -> str:
    """
    Format file size for human-readable display.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted string like "1.5 MB" or "256 KB"
    """
    if size_bytes < 0:
        return "Unknown size"

    if size_bytes == 0:
        return "0 B"

    # Define units
    units = [
        (1024 * 1024 * 1024, "GB"),
        (1024 * 1024, "MB"),
        (1024, "KB"),
        (1, "B"),
    ]

    for divisor, unit in units:
        if size_bytes >= divisor:
            value = size_bytes / divisor
            # Use 1 decimal for MB and GB, none for KB and B
            if unit in ("GB", "MB"):
                return f"{value:.1f} {unit}"
            return f"{int(value)} {unit}"

    return f"{size_bytes} B"


def format_page_count(page_count: int | None) -> str | None:
    """
    Format page count for display.

    Args:
        page_count: Number of pages, or None if unknown

    Returns:
        Formatted string like "12 pages" or None if unknown
    """
    if page_count is None or page_count < 1:
        return None

    if page_count == 1:
        return "1 page"

    return f"{page_count} pages"


def generate_resource_render_config(
    resource: ResourceInfo,
    base_url: str,
    user_agent: str | None = None,
) -> ResourceRenderConfig:
    """
    Generate complete render configuration for a resource template.

    Handles embed support detection and URL generation.

    Args:
        resource: Resource information
        base_url: Site base URL
        user_agent: HTTP User-Agent for embed detection

    Returns:
        ResourceRenderConfig with all template data
    """
    # Check embed support
    supports_embed, fallback_reason = supports_pdf_embed(user_agent)

    # Only PDFs can be embedded
    if resource.mime_type != "application/pdf":
        supports_embed = False
        fallback_reason = "Only PDF files support inline viewing"

    # Generate URLs
    embed_url, download_url, open_url = generate_resource_urls(
        resource.asset_id, base_url
    )

    # Format display values
    file_size_display = format_file_size(resource.file_size_bytes)
    page_count_display = format_page_count(resource.page_count)

    return ResourceRenderConfig(
        embed_url=embed_url,
        download_url=download_url,
        open_url=open_url,
        file_size_display=file_size_display,
        page_count_display=page_count_display,
        supports_embed=supports_embed,
        fallback_reason=fallback_reason,
    )


def generate_resource_metadata(
    title: str,
    slug: str,
    description: str | None,
    resource: ResourceInfo,
    published_at: datetime | None,
    site_config: SiteConfig,
) -> SSRMetadata:
    """
    Generate SSR metadata for a resource page.

    Similar to post metadata but with resource-specific details.

    Args:
        title: Resource title
        slug: Resource slug
        description: Resource description
        resource: Resource information
        published_at: Publication timestamp
        site_config: Site configuration

    Returns:
        SSRMetadata for the resource page
    """
    # Build enhanced description with file info
    file_info_parts = [format_file_size(resource.file_size_bytes)]
    page_count = format_page_count(resource.page_count)
    if page_count:
        file_info_parts.append(page_count)

    file_info = " · ".join(file_info_parts)

    # Combine with description
    if description:
        full_description = f"{description} ({file_info})"
    else:
        full_description = f"PDF resource: {file_info}"

    # Generate canonical URL for resources (uses /r/ path)
    canonical = generate_canonical_url(slug, site_config.base_url)
    canonical = canonical.replace("/p/", "/r/")

    # Use default OG image for resources (PDFs don't have preview images)
    og_image = generate_og_image_url(
        None, site_config.base_url, site_config.default_og_image
    )

    meta_description = truncate_description(full_description, 160)
    og_description = truncate_description(full_description, 200)

    published_time = published_at.isoformat() if published_at else None

    return SSRMetadata(
        title=title,
        description=meta_description,
        canonical_url=canonical,
        og_title=title,
        og_description=og_description,
        og_type="article",
        og_url=canonical,
        og_image=og_image,
        og_site_name=site_config.site_name,
        twitter_card="summary",  # No large image for PDFs
        twitter_title=title,
        twitter_description=og_description,
        twitter_image=og_image,
        twitter_site=site_config.twitter_handle,
        published_time=published_time,
        modified_time=None,
    )


# ═══════════════════════════════════════════════════════════════════════════
# LINK HUB TEMPLATE (Epic1/Epic2)
# Linktree-style page with profile, bio, and curated links
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class LinkHubConfig:
    """Configuration for link hub page."""

    title: str
    bio: str | None = None
    profile_image_id: str | None = None
    show_social_links: bool = True


@dataclass
class LinkHubItem:
    """A link item prepared for template rendering."""

    id: str
    title: str
    url: str
    icon: str | None
    position: int
    group_id: str | None = None
    is_external: bool = False


@dataclass
class LinkHubGroup:
    """A group of links for organized display."""

    id: str | None
    title: str | None
    links: list[LinkHubItem]
    position: int = 0


@dataclass
class LinkHubRenderData:
    """Complete render data for link hub template."""

    config: LinkHubConfig
    groups: list[LinkHubGroup]
    profile_image_url: str | None
    total_links: int


@dataclass
class AccessibilityCheckResult:
    """Result of accessibility validation."""

    is_valid: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    landmarks_found: list[str] = field(default_factory=list)


# Required landmarks for a well-structured page
REQUIRED_LANDMARKS = {"main", "nav"}

# Valid heading levels and their hierarchy
VALID_HEADING_LEVELS = {1, 2, 3, 4, 5, 6}


def validate_link_hub_accessibility(
    has_main_landmark: bool,
    has_nav_landmark: bool,
    heading_levels: list[int],
    link_count: int,
) -> AccessibilityCheckResult:
    """
    Validate link hub page accessibility (TA-E1.1-02).

    Checks for proper landmarks and heading structure.

    Args:
        has_main_landmark: Whether page has <main> element
        has_nav_landmark: Whether page has <nav> element
        heading_levels: List of heading levels used (e.g., [1, 2, 2])
        link_count: Number of links on the page

    Returns:
        AccessibilityCheckResult with violations and warnings
    """
    violations = []
    warnings = []
    landmarks_found = []

    # Check landmarks
    if has_main_landmark:
        landmarks_found.append("main")
    else:
        violations.append("Missing <main> landmark")

    if has_nav_landmark:
        landmarks_found.append("nav")
    else:
        violations.append("Missing <nav> landmark for links")

    # Check heading structure
    if heading_levels:
        # First heading should be h1
        if heading_levels[0] != 1:
            violations.append(
                f"Page should start with h1, found h{heading_levels[0]}"
            )

        # Check for skipped levels
        for i in range(1, len(heading_levels)):
            current = heading_levels[i]
            previous = heading_levels[i - 1]

            # Can go up (h2->h1) or down by 1 (h1->h2), not skip (h1->h3)
            if current > previous + 1:
                violations.append(
                    f"Skipped heading level: h{previous} to h{current}"
                )
    else:
        violations.append("Page has no headings")

    # Warnings for best practices
    if link_count > 20:
        warnings.append(
            f"High link count ({link_count}). Consider grouping for better UX"
        )

    if link_count > 0 and not has_nav_landmark:
        warnings.append("Links should be in a <nav> landmark for screen readers")

    return AccessibilityCheckResult(
        is_valid=len(violations) == 0,
        violations=violations,
        warnings=warnings,
        landmarks_found=landmarks_found,
    )


def prepare_link_hub_item(
    link_id: str,
    title: str,
    url: str,
    icon: str | None,
    position: int,
    group_id: str | None,
    base_url: str | None = None,
) -> LinkHubItem:
    """
    Prepare a single link item for rendering.

    Determines if link is external for proper rel attribute handling.

    Args:
        link_id: Unique identifier
        title: Display title
        url: Link URL
        icon: Optional icon identifier
        position: Sort position
        group_id: Optional group identifier
        base_url: Site base URL for external detection

    Returns:
        LinkHubItem ready for template rendering
    """
    return LinkHubItem(
        id=link_id,
        title=title,
        url=url,
        icon=icon,
        position=position,
        group_id=group_id,
        is_external=is_external_link(url, base_url),
    )


def group_link_hub_items(
    links: list[LinkHubItem],
    groups: dict[str, str],
) -> list[LinkHubGroup]:
    """
    Group links by their group_id.

    Links without a group are placed in a default "ungrouped" group.

    Args:
        links: List of prepared link items
        groups: Dict mapping group_id to group title

    Returns:
        List of LinkHubGroup sorted by position
    """
    # Group links by group_id
    grouped: dict[str | None, list[LinkHubItem]] = {}

    for link in links:
        group_key = link.group_id
        if group_key not in grouped:
            grouped[group_key] = []
        grouped[group_key].append(link)

    # Sort links within each group by position
    for group_links in grouped.values():
        group_links.sort(key=lambda x: x.position)

    # Build LinkHubGroup list
    result: list[LinkHubGroup] = []

    # First add ungrouped links (group_id is None)
    if None in grouped:
        result.append(
            LinkHubGroup(
                id=None,
                title=None,
                links=grouped[None],
                position=-1,  # Ungrouped first
            )
        )

    # Then add named groups
    for group_id, title in groups.items():
        if group_id in grouped:
            result.append(
                LinkHubGroup(
                    id=group_id,
                    title=title,
                    links=grouped[group_id],
                    position=len(result),
                )
            )

    # Sort groups by position
    result.sort(key=lambda g: g.position)

    return result


def generate_link_hub_metadata(
    config: LinkHubConfig,
    link_count: int,
    site_config: SiteConfig,
) -> SSRMetadata:
    """
    Generate SSR metadata for link hub page.

    Args:
        config: Link hub configuration
        link_count: Number of links for description
        site_config: Site configuration

    Returns:
        SSRMetadata for the link hub page
    """
    # Build description
    if config.bio:
        description = truncate_description(config.bio, 160)
    else:
        description = f"Links and resources from {site_config.site_name}"
        if link_count > 0:
            description += f" ({link_count} links)"

    og_description = truncate_description(config.bio or description, 200)

    # Canonical URL for /links page
    base_url = site_config.base_url
    if base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://", 1)
    if not base_url.endswith("/"):
        base_url += "/"
    canonical = urljoin(base_url, "links")

    # Profile image or default OG image
    og_image = None
    if config.profile_image_id:
        og_image = generate_og_image_url(
            config.profile_image_id, site_config.base_url, None
        )
    elif site_config.default_og_image:
        og_image = generate_og_image_url(
            None, site_config.base_url, site_config.default_og_image
        )

    return SSRMetadata(
        title=config.title,
        description=description,
        canonical_url=canonical,
        og_title=config.title,
        og_description=og_description,
        og_type="profile",  # Profile type for link hub
        og_url=canonical,
        og_image=og_image,
        og_site_name=site_config.site_name,
        twitter_card="summary",
        twitter_title=config.title,
        twitter_description=og_description,
        twitter_image=og_image,
        twitter_site=site_config.twitter_handle,
        published_time=None,
        modified_time=None,
    )


def generate_link_hub_render_data(
    config: LinkHubConfig,
    links: list[tuple[str, str, str, str | None, int, str | None]],
    groups: dict[str, str],
    base_url: str,
) -> LinkHubRenderData:
    """
    Generate complete render data for link hub template.

    Args:
        config: Link hub configuration
        links: List of (id, title, url, icon, position, group_id) tuples
        groups: Dict mapping group_id to group title
        base_url: Site base URL for external link detection

    Returns:
        LinkHubRenderData ready for template rendering
    """
    # Prepare link items
    prepared_links = [
        prepare_link_hub_item(
            link_id=link[0],
            title=link[1],
            url=link[2],
            icon=link[3],
            position=link[4],
            group_id=link[5],
            base_url=base_url,
        )
        for link in links
    ]

    # Group links
    grouped = group_link_hub_items(prepared_links, groups)

    # Generate profile image URL
    profile_image_url = None
    if config.profile_image_id:
        profile_image_url = generate_og_image_url(
            config.profile_image_id, base_url, None
        )

    return LinkHubRenderData(
        config=config,
        groups=grouped,
        profile_image_url=profile_image_url,
        total_links=len(links),
    )


# ═══════════════════════════════════════════════════════════════════════════
# CACHING POLICY (E2.3)
# Cache headers, draft isolation, sitemap filtering
# ═══════════════════════════════════════════════════════════════════════════

# Cache policy types
CACHE_POLICY_PUBLIC = "public"
CACHE_POLICY_PRIVATE = "private"
CACHE_POLICY_IMMUTABLE = "immutable"

# Default cache header values from rules
DEFAULT_PUBLISHED_CACHE_CONTROL = (
    "public, max-age=0, s-maxage=300, stale-while-revalidate=86400"
)
DEFAULT_PRIVATE_CACHE_CONTROL = "private, no-store"
DEFAULT_IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"

# Content states that are publicly visible
PUBLIC_VISIBLE_STATES = {"published"}

# Content states that must never be cached publicly (R2)
NEVER_CACHE_PUBLIC_STATES = {"draft", "scheduled", "archived"}


@dataclass
class CachePolicy:
    """Cache policy configuration for a response."""

    cache_control: str
    is_public: bool
    can_be_cached: bool
    cache_tags: list[str] = field(default_factory=list)
    etag: str | None = None


@dataclass
class SitemapEntry:
    """Entry for sitemap generation."""

    loc: str
    lastmod: str | None = None
    changefreq: str | None = None
    priority: float | None = None


@dataclass
class CachePolicyValidation:
    """Result of cache policy validation."""

    is_valid: bool
    violations: list[str] = field(default_factory=list)
    policy_applied: str | None = None


def determine_cache_policy(
    content_state: str,
    published_at: datetime | None,
    now: datetime | None = None,
) -> CachePolicy:
    """
    Determine cache policy based on content state (R2, TA-E2.3-01).

    Invariant R2: Draft and future scheduled content must never be
    publicly cached.

    Args:
        content_state: Content state (draft, scheduled, published, archived)
        published_at: Publication timestamp
        now: Current time for comparison

    Returns:
        CachePolicy with appropriate headers
    """
    if now is None:
        now = _get_now_fallback()

    # R2: Drafts never publicly cacheable
    if content_state == "draft":
        return CachePolicy(
            cache_control=DEFAULT_PRIVATE_CACHE_CONTROL,
            is_public=False,
            can_be_cached=False,
        )

    # R2: Scheduled content with future date never publicly cacheable
    if content_state == "scheduled":
        if published_at is None or published_at > now:
            return CachePolicy(
                cache_control=DEFAULT_PRIVATE_CACHE_CONTROL,
                is_public=False,
                can_be_cached=False,
            )
        # Scheduled content that has "gone live" can be cached
        return CachePolicy(
            cache_control=DEFAULT_PUBLISHED_CACHE_CONTROL,
            is_public=True,
            can_be_cached=True,
        )

    # R2: Archived content not publicly cacheable
    if content_state == "archived":
        return CachePolicy(
            cache_control=DEFAULT_PRIVATE_CACHE_CONTROL,
            is_public=False,
            can_be_cached=False,
        )

    # Published content is cacheable
    if content_state == "published":
        # But not if publish date is in the future
        if published_at and published_at > now:
            return CachePolicy(
                cache_control=DEFAULT_PRIVATE_CACHE_CONTROL,
                is_public=False,
                can_be_cached=False,
            )

        return CachePolicy(
            cache_control=DEFAULT_PUBLISHED_CACHE_CONTROL,
            is_public=True,
            can_be_cached=True,
        )

    # Unknown state - default to private
    return CachePolicy(
        cache_control=DEFAULT_PRIVATE_CACHE_CONTROL,
        is_public=False,
        can_be_cached=False,
    )


def generate_cache_headers(
    policy: CachePolicy,
    etag: str | None = None,
) -> dict[str, str]:
    """
    Generate HTTP cache headers from policy (TA-E2.3-01).

    Args:
        policy: Cache policy configuration
        etag: Optional ETag value

    Returns:
        Dict of header name to value
    """
    headers: dict[str, str] = {
        "Cache-Control": policy.cache_control,
    }

    if etag:
        headers["ETag"] = f'"{etag}"'

    if not policy.is_public:
        # Add Vary header for private responses
        headers["Vary"] = "Cookie"

    return headers


def generate_asset_cache_headers(
    is_immutable: bool = True,
    etag: str | None = None,
) -> dict[str, str]:
    """
    Generate cache headers for asset responses.

    Assets are immutable by default with long cache times.

    Args:
        is_immutable: Whether asset is immutable
        etag: Optional ETag value

    Returns:
        Dict of header name to value
    """
    headers: dict[str, str] = {}

    if is_immutable:
        headers["Cache-Control"] = DEFAULT_IMMUTABLE_CACHE_CONTROL
    else:
        headers["Cache-Control"] = DEFAULT_PUBLISHED_CACHE_CONTROL

    if etag:
        headers["ETag"] = f'"{etag}"'

    return headers


def should_include_in_sitemap(
    content_state: str,
    published_at: datetime | None,
    now: datetime | None = None,
) -> bool:
    """
    Check if content should be included in sitemap (TA-E2.3-03).

    R2: Drafts and future scheduled content must be excluded.

    Args:
        content_state: Content state
        published_at: Publication timestamp
        now: Current time for comparison

    Returns:
        True if content should be in sitemap
    """
    if now is None:
        now = _get_now_fallback()

    # Only published content in sitemap
    if content_state != "published":
        return False

    # Published but with future date - exclude
    if published_at and published_at > now:
        return False

    return True


def filter_sitemap_entries(
    entries: list[tuple[str, str, datetime | None, datetime | None]],
    base_url: str,
    now: datetime | None = None,
) -> list[SitemapEntry]:
    """
    Filter and format sitemap entries (TA-E2.3-03).

    Args:
        entries: List of (slug, content_type, published_at, updated_at) tuples
        base_url: Site base URL
        now: Current time for filtering

    Returns:
        List of SitemapEntry objects for valid entries
    """
    if now is None:
        now = _get_now_fallback()

    # Ensure HTTPS and trailing slash
    if base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://", 1)
    if not base_url.endswith("/"):
        base_url += "/"

    result: list[SitemapEntry] = []

    for slug, content_type, published_at, updated_at in entries:
        # No published_at means content isn't published - exclude
        if published_at is None:
            continue
        # Only include published content that's not future-dated
        if not should_include_in_sitemap("published", published_at, now):
            continue

        # Generate URL based on content type
        if content_type == "post":
            loc = urljoin(base_url, f"p/{slug}")
        elif content_type == "resource":
            loc = urljoin(base_url, f"r/{slug}")
        else:
            loc = urljoin(base_url, slug)

        # Format lastmod
        lastmod = None
        if updated_at:
            lastmod = updated_at.strftime("%Y-%m-%d")
        elif published_at:
            lastmod = published_at.strftime("%Y-%m-%d")

        result.append(
            SitemapEntry(
                loc=loc,
                lastmod=lastmod,
                changefreq="weekly",
                priority=0.8 if content_type == "post" else 0.6,
            )
        )

    return result


def generate_cache_tag(
    content_type: str,
    content_id: str,
    tag_prefix: str = "content:",
) -> str:
    """
    Generate cache tag for content revalidation.

    Args:
        content_type: Type of content (post, resource, link)
        content_id: Content identifier
        tag_prefix: Tag prefix from rules

    Returns:
        Cache tag string
    """
    return f"{tag_prefix}{content_type}:{content_id}"


def generate_cache_tags(
    content_type: str,
    content_id: str,
    slug: str | None = None,
    tag_prefix: str = "content:",
) -> list[str]:
    """
    Generate all cache tags for content.

    Generates tags for ID and optionally slug for flexible revalidation.

    Args:
        content_type: Type of content
        content_id: Content identifier
        slug: Optional content slug
        tag_prefix: Tag prefix from rules

    Returns:
        List of cache tags
    """
    tags = [generate_cache_tag(content_type, content_id, tag_prefix)]

    if slug:
        tags.append(f"{tag_prefix}{content_type}:slug:{slug}")

    # Add type-level tag for bulk revalidation
    tags.append(f"{tag_prefix}{content_type}:all")

    return tags


def validate_cache_policy_r2(
    content_state: str,
    published_at: datetime | None,
    cache_control: str,
    now: datetime | None = None,
) -> CachePolicyValidation:
    """
    Validate that cache policy adheres to R2 (TA-E2.3-02).

    R2: Draft and future scheduled content must never be publicly cached.

    Args:
        content_state: Content state
        published_at: Publication timestamp
        cache_control: Applied Cache-Control header
        now: Current time for comparison

    Returns:
        CachePolicyValidation with any violations
    """
    if now is None:
        now = _get_now_fallback()

    violations = []

    # Check if this is content that should never be public
    is_non_public_content = (
        content_state in NEVER_CACHE_PUBLIC_STATES
        or (content_state == "published" and published_at and published_at > now)
        or (content_state == "scheduled" and (not published_at or published_at > now))
    )

    # Check if cache control allows public caching
    is_public_cache = "public" in cache_control.lower() and "no-store" not in cache_control.lower()

    if is_non_public_content and is_public_cache:
        violations.append(
            f"R2 VIOLATION: {content_state} content has public cache headers: {cache_control}"
        )

    return CachePolicyValidation(
        is_valid=len(violations) == 0,
        violations=violations,
        policy_applied=cache_control,
    )
