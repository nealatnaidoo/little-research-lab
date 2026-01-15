"""
Sharing component - Social share URL generation with UTM tracking.

Spec refs: E15.2
Test assertions: TA-0070, TA-0071

Generates share URLs with platform-specific UTM params for attribution tracking.

Invariants:
- All share URLs include proper UTM parameters
- UTM params follow standard naming (utm_source, utm_medium, utm_campaign)
- Platform-specific URL templates for social networks
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from .models import (
    AddUtmParamsInput,
    AddUtmParamsOutput,
    GenerateShareUrlInput,
    GenerateShareUrlOutput,
    SharingPlatform,
    SharingValidationError,
)
from .ports import SharingRulesPort

# --- Default Configuration ---

DEFAULT_UTM_MEDIUM = "social"

DEFAULT_UTM_SOURCE_MAP: dict[SharingPlatform, str] = {
    "twitter": "twitter",
    "linkedin": "linkedin",
    "facebook": "facebook",
    "native": "share",
}

# Share URL templates for each platform
# {url} = encoded content URL, {title} = encoded title, {description} = encoded description
PLATFORM_SHARE_TEMPLATES: dict[SharingPlatform, str] = {
    "twitter": "https://twitter.com/intent/tweet?url={url}&text={title}",
    "linkedin": "https://www.linkedin.com/sharing/share-offsite/?url={url}",
    "facebook": "https://www.facebook.com/sharer/sharer.php?u={url}",
    "native": "{url}",  # Native share API uses the URL directly
}


# --- Pure Functions (Functional Core) ---


def validate_base_url(base_url: str) -> list[SharingValidationError]:
    """
    Validate that base_url is a valid absolute URL.

    Args:
        base_url: The base URL to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors: list[SharingValidationError] = []

    if not base_url:
        errors.append(
            SharingValidationError(
                code="EMPTY_BASE_URL",
                message="Base URL cannot be empty",
                field_name="base_url",
            )
        )
        return errors

    parsed = urlparse(base_url)

    if not parsed.scheme:
        errors.append(
            SharingValidationError(
                code="MISSING_SCHEME",
                message="Base URL must include scheme (http or https)",
                field_name="base_url",
            )
        )

    if not parsed.netloc:
        errors.append(
            SharingValidationError(
                code="MISSING_HOST",
                message="Base URL must include host",
                field_name="base_url",
            )
        )

    if parsed.scheme and parsed.scheme not in ("http", "https"):
        errors.append(
            SharingValidationError(
                code="INVALID_SCHEME",
                message="Base URL scheme must be http or https",
                field_name="base_url",
            )
        )

    return errors


def validate_slug(slug: str) -> list[SharingValidationError]:
    """
    Validate that slug is valid for URL construction.

    Args:
        slug: The content slug to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors: list[SharingValidationError] = []

    if not slug:
        errors.append(
            SharingValidationError(
                code="EMPTY_SLUG",
                message="Content slug cannot be empty",
                field_name="content_slug",
            )
        )
        return errors

    # Check for invalid characters
    invalid_chars = set('<>"\' ')
    found_invalid = [c for c in slug if c in invalid_chars]
    if found_invalid:
        errors.append(
            SharingValidationError(
                code="INVALID_SLUG_CHARS",
                message=f"Slug contains invalid characters: {found_invalid}",
                field_name="content_slug",
            )
        )

    return errors


def validate_platform(platform: str) -> list[SharingValidationError]:
    """
    Validate that platform is a supported sharing platform.

    Args:
        platform: The platform to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors: list[SharingValidationError] = []
    valid_platforms = {"twitter", "linkedin", "facebook", "native"}

    if platform not in valid_platforms:
        errors.append(
            SharingValidationError(
                code="INVALID_PLATFORM",
                message=f"Platform must be one of: {', '.join(sorted(valid_platforms))}",
                field_name="platform",
            )
        )

    return errors


def add_utm_params(
    url: str,
    utm_source: str,
    utm_medium: str = DEFAULT_UTM_MEDIUM,
    utm_campaign: str | None = None,
    utm_content: str | None = None,
    utm_term: str | None = None,
) -> str:
    """
    Add UTM parameters to a URL (TA-0071).

    Pure function that adds UTM tracking parameters to any URL,
    preserving existing query parameters.

    Args:
        url: The URL to add UTM params to
        utm_source: Traffic source (e.g., "twitter", "linkedin")
        utm_medium: Traffic medium (default "social")
        utm_campaign: Campaign name (usually the content slug)
        utm_content: Optional content identifier
        utm_term: Optional keyword term

    Returns:
        URL with UTM parameters added
    """
    parsed = urlparse(url)

    # Parse existing query params
    existing_params = parse_qs(parsed.query, keep_blank_values=True)

    # Build UTM params dict (only include non-None values)
    utm_params: dict[str, str] = {
        "utm_source": utm_source,
        "utm_medium": utm_medium,
    }

    if utm_campaign:
        utm_params["utm_campaign"] = utm_campaign
    if utm_content:
        utm_params["utm_content"] = utm_content
    if utm_term:
        utm_params["utm_term"] = utm_term

    # Merge params (UTM params override existing)
    # Convert existing params from list to single values
    merged_params: dict[str, str] = {}
    for key, values in existing_params.items():
        if values:
            merged_params[key] = values[0]

    # Add UTM params (overriding any existing UTM params)
    merged_params.update(utm_params)

    # Rebuild URL with new query string
    new_query = urlencode(merged_params)
    new_parsed = parsed._replace(query=new_query)

    return urlunparse(new_parsed)


def build_content_url(
    base_url: str,
    content_slug: str,
    content_path_prefix: str = "/p",
) -> str:
    """
    Build the full content URL from base URL, prefix, and slug.

    Args:
        base_url: Site base URL (e.g., "https://example.com")
        content_slug: Content slug (e.g., "my-article")
        content_path_prefix: Path prefix (e.g., "/p" for posts)

    Returns:
        Full content URL
    """
    # Ensure base_url doesn't end with /
    base = base_url.rstrip("/")

    # Ensure prefix starts with /
    if content_path_prefix.startswith("/"):
        prefix = content_path_prefix
    else:
        prefix = f"/{content_path_prefix}"

    # Ensure slug doesn't start with /
    slug = content_slug.lstrip("/")

    return f"{base}{prefix}/{slug}"


def generate_share_url(
    content_slug: str,
    platform: SharingPlatform,
    base_url: str,
    content_path_prefix: str = "/p",
    utm_source_map: dict[SharingPlatform, str] | None = None,
    utm_medium: str = DEFAULT_UTM_MEDIUM,
    title: str | None = None,
    description: str | None = None,
) -> GenerateShareUrlOutput:
    """
    Generate a share URL for a specific platform with UTM params (TA-0070).

    Pure function that creates platform-specific share URLs with
    proper UTM attribution parameters.

    Args:
        content_slug: The content slug
        platform: Target sharing platform
        base_url: Site base URL
        content_path_prefix: Path prefix for content URLs
        utm_source_map: Optional custom UTM source mapping
        utm_medium: UTM medium value (default "social")
        title: Optional content title for share text
        description: Optional content description

    Returns:
        GenerateShareUrlOutput with share URL or errors
    """
    errors: list[SharingValidationError] = []

    # Validate inputs
    errors.extend(validate_base_url(base_url))
    errors.extend(validate_slug(content_slug))
    errors.extend(validate_platform(platform))

    if errors:
        return GenerateShareUrlOutput(
            share_url=None,
            platform=platform,
            utm_source="",
            utm_medium=utm_medium,
            utm_campaign="",
            errors=errors,
            success=False,
        )

    # Get UTM source for platform
    source_map = utm_source_map or DEFAULT_UTM_SOURCE_MAP
    utm_source = source_map.get(platform, platform)

    # Use slug as campaign
    utm_campaign = content_slug

    # Build content URL with UTM params
    content_url = build_content_url(base_url, content_slug, content_path_prefix)
    tracked_url = add_utm_params(
        url=content_url,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
    )

    # Get platform share template
    template = PLATFORM_SHARE_TEMPLATES.get(platform, "{url}")

    # URL-encode parameters for the share URL
    from urllib.parse import quote

    encoded_url = quote(tracked_url, safe="")
    encoded_title = quote(title or content_slug, safe="")
    encoded_description = quote(description or "", safe="")

    # Build the final share URL
    share_url = template.format(
        url=encoded_url,
        title=encoded_title,
        description=encoded_description,
    )

    return GenerateShareUrlOutput(
        share_url=share_url,
        platform=platform,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        errors=[],
        success=True,
    )


def add_utm_params_with_validation(inp: AddUtmParamsInput) -> AddUtmParamsOutput:
    """
    Add UTM params with input validation (TA-0071).

    Wrapper around add_utm_params that validates input.

    Args:
        inp: AddUtmParamsInput with URL and UTM values

    Returns:
        AddUtmParamsOutput with modified URL or errors
    """
    errors: list[SharingValidationError] = []

    # Validate URL
    if not inp.url:
        errors.append(
            SharingValidationError(
                code="EMPTY_URL",
                message="URL cannot be empty",
                field_name="url",
            )
        )
        return AddUtmParamsOutput(url=None, errors=errors, success=False)

    parsed = urlparse(inp.url)
    if not parsed.scheme or not parsed.netloc:
        errors.append(
            SharingValidationError(
                code="INVALID_URL",
                message="URL must be absolute with scheme and host",
                field_name="url",
            )
        )
        return AddUtmParamsOutput(url=None, errors=errors, success=False)

    # Validate utm_source
    if not inp.utm_source:
        errors.append(
            SharingValidationError(
                code="EMPTY_UTM_SOURCE",
                message="UTM source cannot be empty",
                field_name="utm_source",
            )
        )
        return AddUtmParamsOutput(url=None, errors=errors, success=False)

    # Add UTM params
    result_url = add_utm_params(
        url=inp.url,
        utm_source=inp.utm_source,
        utm_medium=inp.utm_medium,
        utm_campaign=inp.utm_campaign,
        utm_content=inp.utm_content,
        utm_term=inp.utm_term,
    )

    return AddUtmParamsOutput(url=result_url, errors=[], success=True)


# --- Service Class (Shell) ---



def run_generate_share_url(
    inp: GenerateShareUrlInput,
    *,
    rules: SharingRulesPort | None = None,
) -> GenerateShareUrlOutput:
    """
    Generate share URL handler (Functional Core).
    """
    # Use defaults if rules not provided (though rules are expected)
    utm_medium = DEFAULT_UTM_MEDIUM
    source_map: dict[SharingPlatform, str] = {}

    if rules:
        utm_medium = rules.get_utm_medium()
        for p in ("twitter", "linkedin", "facebook", "native"):
            # Cast platform string to literal type for type safety
            platform_key: SharingPlatform = p
            source_map[platform_key] = rules.get_utm_source_for_platform(platform_key)

    return generate_share_url(
        content_slug=inp.content_slug,
        platform=inp.platform,
        base_url=inp.base_url,
        content_path_prefix=inp.content_path_prefix,
        utm_source_map=source_map,
        utm_medium=utm_medium,
        title=inp.title,
        description=inp.description,
    )


def run_add_utm_params(
    inp: AddUtmParamsInput,
) -> AddUtmParamsOutput:
    """
    Add UTM params handler (Functional Core).
    """
    return add_utm_params_with_validation(inp)


def run(
    inp: GenerateShareUrlInput | AddUtmParamsInput,
    *,
    rules: SharingRulesPort | None = None,
) -> GenerateShareUrlOutput | AddUtmParamsOutput:
    """
    Main component entry point (Atomic Component Pattern).

    Args:
        inp: Input model (GenerateShareUrlInput or AddUtmParamsInput)
        rules: Configuration rules port

    Returns:
        Output model (GenerateShareUrlOutput or AddUtmParamsOutput)
    """
    if isinstance(inp, GenerateShareUrlInput):
        return run_generate_share_url(inp, rules=rules)
    elif isinstance(inp, AddUtmParamsInput):
        return run_add_utm_params(inp)
    else:
        raise ValueError(f"Unknown input type: {type(inp)}")
