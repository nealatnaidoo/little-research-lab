# Component Contract: C2-PublicTemplates

## COMPONENT_ID

C2-PublicTemplates

## PURPOSE

Provides public template rendering logic for posts, resources, and link hubs. Generates SSR-correct metadata (OG/Twitter), sanitizes links for security, and validates prose structure for accessibility. This component's pure functions support server-side rendering without external dependencies.

## INPUTS

- `ContentItem`: Content entity with title, slug, body, blocks, og_image, published_at
- `SiteConfig`: Site-level configuration (base_url, site_name, default_og_image)
- `RenderOptions`: Template rendering options (max_width, typography_scale)

## OUTPUTS

- `SSRMetadata`: Complete metadata for SSR (og:*, twitter:*, canonical)
- `SanitizedContent`: Content with sanitized links and validated structure
- `RenderResult`: Rendered content with metadata and accessibility info

## DEPENDENCIES (PORTS)

- None for FC (pure functions)
- IS may use: StoragePort (for asset URLs), CachePort (for cache headers)

## SIDE EFFECTS

- None in FC (pure rendering/transformation)
- IS: HTTP response headers, cache tag registration

## INVARIANTS

- I1: All external links must have rel="noopener noreferrer" (R6)
- I2: OG metadata must match actual content (SSR correctness)
- I3: Content must not render draft/scheduled state publicly (R2)
- I4: Canonical URLs must be absolute and use HTTPS
- I5: Image URLs in metadata must be absolute URLs

## ERROR SEMANTICS

- Pure functions return result types with validation status
- No exceptions for data issues - returns sanitized defaults
- Missing required fields logged and replaced with safe defaults

## RULES DEPENDENCIES

- Section: `content.sanitization`
- Keys: `rel_attribute_policy.external_links`, `enforce_heading_order`
- Section: `content.visibility`
- Keys: `public_visible_states`

## SPEC REFS

- Epics: E2.1 (Posts template v4), E2.2 (Resource template), E2.3 (Caching)
- Test Assertions: TA-E2.1-01 (SSR metadata), TA-E2.1-02 (LCP budget), TA-E2.1-03 (link sanitizer)
- Regression Invariants: R2 (draft isolation), R6 (external links)

## FC (Functional Core)

Pure functions with no I/O:

### Metadata Generation
- `generate_ssr_metadata(content, site_config) -> SSRMetadata`: Generate complete OG/Twitter metadata
- `generate_canonical_url(slug, base_url) -> str`: Generate canonical URL
- `generate_og_image_url(og_image_id, base_url) -> str | None`: Generate OG image URL

### Link Sanitization
- `sanitize_external_links(html) -> str`: Add rel attributes to external links
- `extract_links(html) -> list[LinkInfo]`: Extract all links from content
- `is_external_link(href, base_url) -> bool`: Check if link is external

### Content Validation
- `validate_content_visibility(state, published_at) -> ValidationResult`: Check if content can be public
- `validate_prose_structure(blocks) -> ValidationResult`: Check heading order and structure

### Template Helpers
- `truncate_description(text, max_length) -> str`: Truncate for meta description
- `extract_first_paragraph(blocks) -> str`: Extract first text block for description
- `format_publish_date(dt, format) -> str`: Format publish date for display

### Resource Template (E2.2)
- `supports_pdf_embed(user_agent) -> tuple[bool, str | None]`: Check if browser supports inline PDF embed (TA-E2.2-01)
- `generate_resource_urls(asset_id, base_url) -> tuple[embed, download, open]`: Generate resource viewing URLs (TA-E2.2-02)
- `format_file_size(size_bytes) -> str`: Format file size for human display
- `format_page_count(page_count) -> str | None`: Format page count for display
- `generate_resource_render_config(resource, base_url, user_agent) -> ResourceRenderConfig`: Generate complete render config
- `generate_resource_metadata(title, slug, description, resource, published_at, site_config) -> SSRMetadata`: Generate resource page metadata

### Link Hub Template (Epic1/Epic2)
- `validate_link_hub_accessibility(has_main, has_nav, headings, link_count) -> AccessibilityCheckResult`: Validate landmarks/headings (TA-E1.1-02)
- `prepare_link_hub_item(id, title, url, icon, position, group_id, base_url) -> LinkHubItem`: Prepare single link for rendering
- `group_link_hub_items(links, groups) -> list[LinkHubGroup]`: Group links by group_id
- `generate_link_hub_metadata(config, link_count, site_config) -> SSRMetadata`: Generate SSR metadata for /links page
- `generate_link_hub_render_data(config, links, groups, base_url) -> LinkHubRenderData`: Generate complete render data

### Caching Policy (E2.3)
- `determine_cache_policy(state, published_at, now) -> CachePolicy`: Determine cache policy based on content state (TA-E2.3-01, R2)
- `generate_cache_headers(policy, etag) -> dict[str, str]`: Generate HTTP cache headers (TA-E2.3-01)
- `generate_asset_cache_headers(is_immutable, etag) -> dict[str, str]`: Generate asset cache headers
- `should_include_in_sitemap(state, published_at, now) -> bool`: Check sitemap inclusion (TA-E2.3-03)
- `filter_sitemap_entries(entries, base_url, now) -> list[SitemapEntry]`: Filter and format sitemap entries
- `generate_cache_tag(content_type, content_id, prefix) -> str`: Generate single cache tag
- `generate_cache_tags(content_type, content_id, slug, prefix) -> list[str]`: Generate all cache tags
- `validate_cache_policy_r2(state, published_at, cache_control, now) -> CachePolicyValidation`: Validate R2 compliance (TA-E2.3-02)

## IS (Imperative Shell)

I/O handlers and adapters:

- `PostTemplateHandler`: Next.js page handler integration
- `MetadataHandler`: Generate metadata for App Router generateMetadata
- `CacheHeaderHandler`: Set cache-control headers based on content state

### P3 RevalidationAdapter (E2.3)
- `RevalidationPort`: Protocol for cache revalidation operations
- `RevalidationAdapter`: Abstract base class for revalidation
- `StubRevalidationAdapter`: Test stub that records revalidation calls
- `RevalidationResult`: Result of revalidation operation

## TESTS

- `tests/unit/test_public_templates.py`: SSR metadata and link sanitization tests
  - Metadata generation tests (TA-E2.1-01)
  - Link sanitization tests (TA-E2.1-03)
  - Visibility validation tests
  - Prose structure validation tests
- `tests/unit/test_resource_template.py`: Resource template tests (E2.2)
  - PDF embed support detection (TA-E2.2-01)
  - Resource URL generation (TA-E2.2-02)
  - File size/page count formatting
  - Resource metadata generation
- `tests/unit/test_link_hub_template.py`: Link hub template tests (Epic1/Epic2)
  - Accessibility validation - landmarks/headings (TA-E1.1-02)
  - Link preparation and external detection
  - Link grouping
  - SSR metadata generation
- `tests/unit/test_caching_policy.py`: Caching policy tests (E2.3)
  - Cache policy determination (TA-E2.3-01)
  - Draft isolation validation (TA-E2.3-02, R2)
  - Sitemap filtering (TA-E2.3-03)
  - Cache tag generation
  - Revalidation adapter
- Test Assertions: TA-E2.1-01, TA-E2.1-03, TA-E2.2-01, TA-E2.2-02, TA-E1.1-02, TA-E2.3-01, TA-E2.3-02, TA-E2.3-03

## EVIDENCE

- `artifacts/public_templates_validation.json`: Validation run results
- LCP budget tests: Frontend Playwright tests (TA-E2.1-02)
