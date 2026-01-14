"""
Public SSR Routes (E1.2) - Server-side rendered pages with metadata.

Serves HTML pages with proper meta tags for crawlers and social previews.
Wires SettingsService, ContentService, and RenderService together.

Spec refs: E1.2, TA-0003, TA-0004
Test assertions:
- TA-0003: Public SSR reflects settings
- TA-0004: SSR meta snapshot (title, description, canonical, OG, Twitter)
"""

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response

from src.api.deps import (
    get_content_repo,
    get_site_settings_repo,
    get_version_repo,
    require_published,
)
from src.components.C2_PublicTemplates import SitemapEntry, filter_sitemap_entries
from src.components.render import PageMetadata, RenderService, create_render_service
from src.components.settings import SettingsService

router = APIRouter()


# --- Configuration ---

DEFAULT_BASE_URL = "https://littleresearchlab.com"
DEFAULT_OG_IMAGE = "/assets/default-og.png"


# --- HTML Rendering ---


def render_meta_tags_html(metadata: PageMetadata) -> str:
    """Render PageMetadata to HTML meta tag string."""
    html_parts: list[str] = []

    # Title (not a meta tag, but in head)
    html_parts.append(f"<title>{_escape_html(metadata.title)}</title>")

    # Standard meta tags
    for tag in metadata.to_meta_tags():
        if tag.property:
            html_parts.append(
                f'<meta property="{_escape_html(tag.property)}" '
                f'content="{_escape_html(tag.content)}" />'
            )
        elif tag.name:
            html_parts.append(
                f'<meta name="{_escape_html(tag.name)}" content="{_escape_html(tag.content)}" />'
            )

    # Canonical link
    html_parts.append(f'<link rel="canonical" href="{_escape_html(metadata.canonical_url)}" />')

    return "\n    ".join(html_parts)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def render_ssr_page(metadata: PageMetadata, body_content: str = "") -> str:
    """
    Render complete SSR HTML page with metadata.

    Returns minimal HTML for crawlers with full head metadata.
    """
    meta_html = render_meta_tags_html(metadata)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    {meta_html}
</head>
<body>
    {body_content}
</body>
</html>"""


# --- Dependency Injection ---


def get_settings_service(
    repo: Any = Depends(get_site_settings_repo),
) -> SettingsService:
    """Create SettingsService with dependencies."""
    from src.components.settings import NoOpCacheInvalidator

    return SettingsService(repo=repo, cache_invalidator=NoOpCacheInvalidator())


def get_render_service(request: Request) -> RenderService:
    """Create RenderService with request context."""
    # Build base URL from request
    base_url = str(request.base_url).rstrip("/")
    return create_render_service(
        base_url=base_url,
        default_og_image_url=f"{base_url}{DEFAULT_OG_IMAGE}",
    )


# --- SSR Endpoints ---


@router.get(
    "/",
    response_class=HTMLResponse,
    summary="Homepage SSR",
    description="Server-side rendered homepage with meta tags (TA-0003, TA-0004).",
)
def ssr_homepage(
    settings_service: SettingsService = Depends(get_settings_service),
    render_service: RenderService = Depends(get_render_service),
) -> HTMLResponse:
    """
    Serve SSR homepage.

    Returns HTML with proper meta tags derived from settings.
    """
    settings = settings_service.get()
    metadata = render_service.build_homepage_metadata(settings)

    body = f"""
    <main>
        <h1>{_escape_html(settings.site_title)}</h1>
        <p>{_escape_html(settings.site_subtitle)}</p>
        <noscript>
            <p>JavaScript is required for the full experience.
            Visit our <a href="/api/public/home">API</a> for content.</p>
        </noscript>
    </main>
    """

    html = render_ssr_page(metadata, body)
    return HTMLResponse(content=html, status_code=200)


@router.get(
    "/p/{slug}",
    response_class=HTMLResponse,
    summary="Post SSR",
    description="Server-side rendered post page with meta tags.",
)
def ssr_post(
    slug: str,
    settings_service: SettingsService = Depends(get_settings_service),
    render_service: RenderService = Depends(get_render_service),
    content_repo: Any = Depends(get_content_repo),
) -> HTMLResponse:
    """
    Serve SSR post page.

    Returns HTML with meta tags for the specific post.
    """
    settings = settings_service.get()

    # Get content by slug and enforce published-only (R2, T-0046)
    content = content_repo.get_by_slug(slug, "post")
    content = require_published(content)

    metadata = render_service.build_content_metadata(settings, content)

    body = f"""
    <article>
        <h1>{_escape_html(content.title)}</h1>
        <p>{_escape_html(content.summary or "")}</p>
        <noscript>
            <p>JavaScript is required for the full reading experience.</p>
        </noscript>
    </article>
    """

    html = render_ssr_page(metadata, body)
    return HTMLResponse(content=html, status_code=200)


@router.get(
    "/page/{slug}",
    response_class=HTMLResponse,
    summary="Static page SSR",
    description="Server-side rendered static page with meta tags.",
)
def ssr_page(
    slug: str,
    settings_service: SettingsService = Depends(get_settings_service),
    render_service: RenderService = Depends(get_render_service),
    content_repo: Any = Depends(get_content_repo),
) -> HTMLResponse:
    """
    Serve SSR static page (about, contact, etc.).

    Returns HTML with meta tags for the specific page.
    """
    settings = settings_service.get()

    # Get content by slug and enforce published-only (R2, T-0046)
    content = content_repo.get_by_slug(slug, "page")
    content = require_published(content)

    metadata = render_service.build_content_metadata(settings, content)

    body = f"""
    <article>
        <h1>{_escape_html(content.title)}</h1>
        <p>{_escape_html(content.summary or "")}</p>
        <noscript>
            <p>JavaScript is required for the full reading experience.</p>
        </noscript>
    </article>
    """

    html = render_ssr_page(metadata, body)
    return HTMLResponse(content=html, status_code=200)


# --- Metadata-only endpoint (for debugging/testing) ---


@router.get(
    "/meta",
    summary="Get SSR metadata",
    description="Get SSR metadata as JSON (for testing TA-0003, TA-0004).",
)
def get_ssr_metadata(
    path: str = "/",
    settings_service: SettingsService = Depends(get_settings_service),
    render_service: RenderService = Depends(get_render_service),
) -> dict[str, Any]:
    """
    Get SSR metadata for a path.

    Returns metadata as JSON for testing and debugging.
    """
    settings = settings_service.get()
    metadata = render_service.build_page_metadata(settings, path=path)

    return {
        "title": metadata.title,
        "description": metadata.description,
        "canonical_url": metadata.canonical_url,
        "og_title": metadata.og_title,
        "og_description": metadata.og_description,
        "og_type": metadata.og_type,
        "og_url": metadata.og_url,
        "og_image": metadata.og_image,
        "og_site_name": metadata.og_site_name,
        "twitter_card": metadata.twitter_card,
        "robots": metadata.robots,
    }


# --- Resource(PDF) SSR (E3.2, TA-0016, TA-0017, TA-0018) ---


def _render_pdf_embed_html(
    pdf_url: str,
    download_url: str,
    filename: str,
) -> str:
    """
    Render PDF embed HTML with fallback for iOS/Safari (TA-0017).

    Returns HTML with:
    - PDF embed/object for desktop browsers
    - Fallback links for iOS/Safari (Open in new tab + Download)
    """
    escaped_url = _escape_html(pdf_url)
    escaped_download = _escape_html(download_url)
    escaped_filename = _escape_html(filename)

    return f"""
    <div class="pdf-container">
        <!-- PDF embed for desktop browsers -->
        <object data="{escaped_url}" type="application/pdf"
                width="100%" height="600px" class="pdf-embed">
            <!-- Fallback for browsers that don't support PDF embed -->
            <div class="pdf-fallback">
                <p>Your browser doesn't support embedded PDFs.</p>
                <div class="pdf-actions">
                    <a href="{escaped_url}" target="_blank"
                       rel="noopener noreferrer" class="btn btn-primary">
                        Open PDF in New Tab
                    </a>
                    <a href="{escaped_download}" download="{escaped_filename}"
                       class="btn btn-secondary">
                        Download PDF
                    </a>
                </div>
            </div>
        </object>
        <!-- Always show download link below embed -->
        <div class="pdf-download-section">
            <a href="{escaped_download}" download="{escaped_filename}"
               class="download-link">
                Download: {escaped_filename}
            </a>
        </div>
    </div>
    """


@router.get(
    "/r/{slug}",
    response_class=HTMLResponse,
    summary="Resource(PDF) SSR",
    description="Server-side rendered PDF resource page (E3.2, TA-0016, TA-0017, TA-0018).",
)
def ssr_resource_pdf(
    slug: str,
    request: Request,
    settings_service: SettingsService = Depends(get_settings_service),
    render_service: RenderService = Depends(get_render_service),
    content_repo: Any = Depends(get_content_repo),
    version_repo: Any = Depends(get_version_repo),
) -> HTMLResponse:
    """
    Serve SSR Resource(PDF) page.

    Spec refs: E3.2, TA-0016, TA-0017, TA-0018

    Features:
    - TA-0016: SSR page with proper meta tags for crawlers
    - TA-0017: PDF embed with iOS/Safari fallback
    - TA-0018: Download route works (provides download link)

    Returns HTML with:
    - Meta tags (title, description, OG tags for PDF preview)
    - PDF embed/viewer
    - Fallback links for non-supporting browsers
    - Download link
    """
    settings = settings_service.get()

    # Get resource by slug and enforce published-only (R2, T-0046)
    content = content_repo.get_by_slug(slug, "resource_pdf")
    content = require_published(content)

    # Build page metadata
    metadata = render_service.build_content_metadata(settings, content)

    # Get PDF URL for embed
    base_url = str(request.base_url).rstrip("/")

    # Try to get PDF asset URL from content's blocks (if stored there)
    # or from pdf_asset_id if this is a ResourcePDF entity
    pdf_asset_id = getattr(content, "pdf_asset_id", None)

    # Construct PDF URLs
    if pdf_asset_id:
        # Use /latest route for the asset (allows admin to rollback)
        pdf_url = f"{base_url}/api/public/assets/{pdf_asset_id}/latest"
        download_url = f"{pdf_url}?download=1"
    else:
        # Fallback: no PDF attached yet (shouldn't happen for published)
        pdf_url = ""
        download_url = ""

    # Get display filename
    filename = getattr(content, "download_filename", None)
    if not filename:
        filename = f"{slug}.pdf"

    # Build body content
    body_parts = [
        "<article class='resource-pdf'>",
        f"<h1>{_escape_html(content.title)}</h1>",
    ]

    if content.summary:
        body_parts.append(f"<p class='summary'>{_escape_html(content.summary)}</p>")

    if pdf_url:
        body_parts.append(_render_pdf_embed_html(pdf_url, download_url, filename))
    else:
        body_parts.append("<p class='no-pdf'>PDF not available. Please check back later.</p>")

    body_parts.append(
        """
        <noscript>
            <p>JavaScript is optional for this page.
            Use the links above to view or download the PDF.</p>
        </noscript>
        </article>
        """
    )

    body = "\n".join(body_parts)

    html = render_ssr_page(metadata, body)
    return HTMLResponse(content=html, status_code=200)


# --- Sitemap (R2, T-0046) ---


def _render_sitemap_xml(entries: list[SitemapEntry]) -> str:
    """
    Render sitemap entries to XML string.

    Args:
        entries: List of SitemapEntry objects

    Returns:
        Valid sitemap.xml content
    """
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for entry in entries:
        xml_parts.append("  <url>")
        xml_parts.append(f"    <loc>{_escape_html(entry.loc)}</loc>")
        if entry.lastmod:
            xml_parts.append(f"    <lastmod>{entry.lastmod}</lastmod>")
        if entry.changefreq:
            xml_parts.append(f"    <changefreq>{entry.changefreq}</changefreq>")
        if entry.priority is not None:
            xml_parts.append(f"    <priority>{entry.priority}</priority>")
        xml_parts.append("  </url>")

    xml_parts.append("</urlset>")
    return "\n".join(xml_parts)


@router.get(
    "/sitemap.xml",
    response_class=Response,
    summary="XML Sitemap",
    description="Sitemap for search engines (R2, T-0046). Only published content included.",
)
def sitemap_xml(
    request: Request,
    content_repo: Any = Depends(get_content_repo),
) -> Response:
    """
    Generate sitemap.xml with published content only (R2, T-0046).

    Implements invariant R2: Draft and future scheduled content
    must never be publicly served or cached, including in sitemap.

    Returns XML sitemap with:
    - Published posts at /p/{slug}
    - Published resources at /r/{slug}
    - Published pages at /{slug}

    Excludes:
    - Draft content
    - Scheduled content (future publish dates)
    - Archived content
    """
    base_url = str(request.base_url).rstrip("/")

    # Get all content items with status and timestamps
    all_items = content_repo.list_items({})

    # Build entry tuples: (slug, content_type, published_at, updated_at)
    entry_tuples: list[tuple[str, str, Any, Any]] = []
    for item in all_items:
        # Only include items that are published (filter_sitemap_entries will
        # also verify, but pre-filter to avoid processing unnecessary items)
        if item.status == "published":
            entry_tuples.append((
                item.slug,
                item.type,
                getattr(item, "published_at", None),
                getattr(item, "updated_at", None),
            ))

    # Filter entries using the R2-compliant filter function
    sitemap_entries = filter_sitemap_entries(entry_tuples, base_url)

    # Add homepage
    sitemap_entries.insert(
        0,
        SitemapEntry(
            loc=f"{base_url}/",
            changefreq="daily",
            priority=1.0,
        ),
    )

    xml_content = _render_sitemap_xml(sitemap_entries)

    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={
            "Cache-Control": "public, max-age=3600",  # 1 hour cache
        },
    )
