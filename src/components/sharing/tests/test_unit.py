"""
Unit tests for Sharing component.

Spec refs: E15.2
Test assertions: TA-0070, TA-0071

Tests:
- TA-0070: Share URLs include platform-specific UTM params
- TA-0071: UTM params follow standard format
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from ..component import (
    DEFAULT_UTM_MEDIUM,
    DEFAULT_UTM_SOURCE_MAP,
    add_utm_params,
    add_utm_params_with_validation,
    build_content_url,
    generate_share_url,
    run,
    validate_base_url,
    validate_platform,
    validate_slug,
)
from ..models import (
    AddUtmParamsInput,
    AddUtmParamsOutput,
    GenerateShareUrlInput,
    GenerateShareUrlOutput,
    SharingPlatform,
)

# --- Test Fixtures ---


class MockSharingRules:
    """Mock implementation of SharingRulesPort."""

    def __init__(
        self,
        enabled: bool = True,
        platforms: tuple[SharingPlatform, ...] = ("twitter", "linkedin", "facebook", "native"),
        utm_medium: str = "social",
        utm_campaign_source: str = "slug",
        prefer_native: bool = True,
    ) -> None:
        self._enabled = enabled
        self._platforms = platforms
        self._utm_medium = utm_medium
        self._utm_campaign_source = utm_campaign_source
        self._prefer_native = prefer_native

    def is_enabled(self) -> bool:
        return self._enabled

    def get_platforms(self) -> tuple[SharingPlatform, ...]:
        return self._platforms

    def get_utm_medium(self) -> str:
        return self._utm_medium

    def get_utm_source_for_platform(self, platform: SharingPlatform) -> str:
        return DEFAULT_UTM_SOURCE_MAP.get(platform, platform)

    def get_utm_campaign_source(self) -> str:
        return self._utm_campaign_source

    def prefer_native_share_on_mobile(self) -> bool:
        return self._prefer_native


@pytest.fixture
def mock_rules() -> MockSharingRules:
    """Create mock sharing rules."""
    return MockSharingRules()


# --- Validation Tests ---


class TestValidateBaseUrl:
    """Tests for base URL validation."""

    def test_valid_https_url(self) -> None:
        """Valid HTTPS URL passes validation."""
        errors = validate_base_url("https://example.com")
        assert errors == []

    def test_valid_http_url(self) -> None:
        """Valid HTTP URL passes validation."""
        errors = validate_base_url("http://localhost:3000")
        assert errors == []

    def test_empty_url_fails(self) -> None:
        """Empty URL fails validation."""
        errors = validate_base_url("")
        assert len(errors) == 1
        assert errors[0].code == "EMPTY_BASE_URL"

    def test_missing_scheme_fails(self) -> None:
        """URL without scheme fails validation."""
        errors = validate_base_url("example.com")
        assert any(e.code == "MISSING_SCHEME" for e in errors)

    def test_invalid_scheme_fails(self) -> None:
        """URL with invalid scheme fails validation."""
        errors = validate_base_url("ftp://example.com")
        assert any(e.code == "INVALID_SCHEME" for e in errors)


class TestValidateSlug:
    """Tests for slug validation."""

    def test_valid_slug(self) -> None:
        """Valid slug passes validation."""
        errors = validate_slug("my-article-slug")
        assert errors == []

    def test_slug_with_numbers(self) -> None:
        """Slug with numbers passes validation."""
        errors = validate_slug("article-2024-01-15")
        assert errors == []

    def test_empty_slug_fails(self) -> None:
        """Empty slug fails validation."""
        errors = validate_slug("")
        assert len(errors) == 1
        assert errors[0].code == "EMPTY_SLUG"

    def test_slug_with_spaces_fails(self) -> None:
        """Slug with spaces fails validation."""
        errors = validate_slug("my article")
        assert any(e.code == "INVALID_SLUG_CHARS" for e in errors)

    def test_slug_with_quotes_fails(self) -> None:
        """Slug with quotes fails validation."""
        errors = validate_slug('my"article')
        assert any(e.code == "INVALID_SLUG_CHARS" for e in errors)


class TestValidatePlatform:
    """Tests for platform validation."""

    @pytest.mark.parametrize("platform", ["twitter", "linkedin", "facebook", "native"])
    def test_valid_platforms(self, platform: str) -> None:
        """Valid platforms pass validation."""
        errors = validate_platform(platform)
        assert errors == []

    def test_invalid_platform_fails(self) -> None:
        """Invalid platform fails validation."""
        errors = validate_platform("instagram")
        assert len(errors) == 1
        assert errors[0].code == "INVALID_PLATFORM"


# --- Pure Function Tests ---


class TestBuildContentUrl:
    """Tests for build_content_url function."""

    def test_basic_url_construction(self) -> None:
        """Constructs basic content URL correctly."""
        url = build_content_url(
            base_url="https://example.com",
            content_slug="my-article",
            content_path_prefix="/p",
        )
        assert url == "https://example.com/p/my-article"

    def test_trailing_slash_in_base_url(self) -> None:
        """Handles trailing slash in base URL."""
        url = build_content_url(
            base_url="https://example.com/",
            content_slug="my-article",
            content_path_prefix="/p",
        )
        assert url == "https://example.com/p/my-article"

    def test_prefix_without_leading_slash(self) -> None:
        """Handles prefix without leading slash."""
        url = build_content_url(
            base_url="https://example.com",
            content_slug="my-article",
            content_path_prefix="r",
        )
        assert url == "https://example.com/r/my-article"

    def test_resource_prefix(self) -> None:
        """Works with resource prefix."""
        url = build_content_url(
            base_url="https://example.com",
            content_slug="my-pdf",
            content_path_prefix="/r",
        )
        assert url == "https://example.com/r/my-pdf"


class TestAddUtmParams:
    """Tests for add_utm_params function (TA-0071)."""

    def test_adds_basic_utm_params(self) -> None:
        """Adds basic UTM params to URL."""
        result = add_utm_params(
            url="https://example.com/p/article",
            utm_source="twitter",
            utm_medium="social",
            utm_campaign="article",
        )

        parsed = urlparse(result)
        params = parse_qs(parsed.query)

        assert params["utm_source"] == ["twitter"]
        assert params["utm_medium"] == ["social"]
        assert params["utm_campaign"] == ["article"]

    def test_preserves_existing_params(self) -> None:
        """Preserves existing query parameters."""
        result = add_utm_params(
            url="https://example.com/p/article?ref=homepage",
            utm_source="twitter",
        )

        parsed = urlparse(result)
        params = parse_qs(parsed.query)

        assert params["ref"] == ["homepage"]
        assert params["utm_source"] == ["twitter"]

    def test_overrides_existing_utm_params(self) -> None:
        """Overrides existing UTM params."""
        result = add_utm_params(
            url="https://example.com/p/article?utm_source=old",
            utm_source="new",
        )

        parsed = urlparse(result)
        params = parse_qs(parsed.query)

        assert params["utm_source"] == ["new"]

    def test_default_utm_medium(self) -> None:
        """Uses default UTM medium."""
        result = add_utm_params(
            url="https://example.com/p/article",
            utm_source="twitter",
        )

        parsed = urlparse(result)
        params = parse_qs(parsed.query)

        assert params["utm_medium"] == [DEFAULT_UTM_MEDIUM]

    def test_optional_utm_content(self) -> None:
        """Adds optional utm_content."""
        result = add_utm_params(
            url="https://example.com/p/article",
            utm_source="twitter",
            utm_content="sidebar",
        )

        parsed = urlparse(result)
        params = parse_qs(parsed.query)

        assert params["utm_content"] == ["sidebar"]

    def test_optional_utm_term(self) -> None:
        """Adds optional utm_term."""
        result = add_utm_params(
            url="https://example.com/p/article",
            utm_source="google",
            utm_medium="cpc",
            utm_term="python+tutorial",
        )

        parsed = urlparse(result)
        params = parse_qs(parsed.query)

        assert params["utm_term"] == ["python+tutorial"]

    def test_omits_none_params(self) -> None:
        """Omits None optional params."""
        result = add_utm_params(
            url="https://example.com/p/article",
            utm_source="twitter",
            utm_campaign=None,
        )

        parsed = urlparse(result)
        params = parse_qs(parsed.query)

        assert "utm_campaign" not in params


class TestAddUtmParamsWithValidation:
    """Tests for add_utm_params_with_validation function."""

    def test_valid_input_succeeds(self) -> None:
        """Valid input produces successful output."""
        inp = AddUtmParamsInput(
            url="https://example.com/p/article",
            utm_source="twitter",
        )
        result = add_utm_params_with_validation(inp)

        assert result.success is True
        assert result.url is not None
        assert "utm_source=twitter" in result.url

    def test_empty_url_fails(self) -> None:
        """Empty URL fails validation."""
        inp = AddUtmParamsInput(url="", utm_source="twitter")
        result = add_utm_params_with_validation(inp)

        assert result.success is False
        assert any(e.code == "EMPTY_URL" for e in result.errors)

    def test_relative_url_fails(self) -> None:
        """Relative URL fails validation."""
        inp = AddUtmParamsInput(url="/p/article", utm_source="twitter")
        result = add_utm_params_with_validation(inp)

        assert result.success is False
        assert any(e.code == "INVALID_URL" for e in result.errors)

    def test_empty_utm_source_fails(self) -> None:
        """Empty utm_source fails validation."""
        inp = AddUtmParamsInput(
            url="https://example.com/p/article",
            utm_source="",
        )
        result = add_utm_params_with_validation(inp)

        assert result.success is False
        assert any(e.code == "EMPTY_UTM_SOURCE" for e in result.errors)


# --- Generate Share URL Tests (TA-0070) ---


class TestGenerateShareUrl:
    """Tests for generate_share_url function (TA-0070)."""

    def test_twitter_share_url(self) -> None:
        """Generates correct Twitter share URL."""
        result = generate_share_url(
            content_slug="my-article",
            platform="twitter",
            base_url="https://example.com",
            content_path_prefix="/p",
            title="My Article Title",
        )

        assert result.success is True
        assert result.share_url is not None
        assert "twitter.com/intent/tweet" in result.share_url
        assert result.utm_source == "twitter"
        assert result.utm_medium == "social"
        assert result.utm_campaign == "my-article"

    def test_linkedin_share_url(self) -> None:
        """Generates correct LinkedIn share URL."""
        result = generate_share_url(
            content_slug="my-article",
            platform="linkedin",
            base_url="https://example.com",
        )

        assert result.success is True
        assert result.share_url is not None
        assert "linkedin.com/sharing" in result.share_url
        assert result.utm_source == "linkedin"

    def test_facebook_share_url(self) -> None:
        """Generates correct Facebook share URL."""
        result = generate_share_url(
            content_slug="my-article",
            platform="facebook",
            base_url="https://example.com",
        )

        assert result.success is True
        assert result.share_url is not None
        assert "facebook.com/sharer" in result.share_url
        assert result.utm_source == "facebook"

    def test_native_share_url(self) -> None:
        """Generates native share URL (just the tracked content URL)."""
        result = generate_share_url(
            content_slug="my-article",
            platform="native",
            base_url="https://example.com",
        )

        assert result.success is True
        assert result.share_url is not None
        # Native share URL is the content URL with UTM params (URL-encoded)
        # The template is "{url}" so the result is the URL-encoded tracked URL
        from urllib.parse import unquote
        decoded_url = unquote(result.share_url)
        assert "example.com/p/my-article" in decoded_url
        assert "utm_source=share" in decoded_url

    def test_share_url_includes_utm_params(self) -> None:
        """Share URL includes all required UTM params."""
        result = generate_share_url(
            content_slug="test-article",
            platform="twitter",
            base_url="https://example.com",
        )

        assert result.success is True
        # The content URL within the share URL should have UTM params
        assert "utm_source" in (result.share_url or "")
        assert "utm_medium" in (result.share_url or "")
        assert "utm_campaign" in (result.share_url or "")

    def test_custom_utm_source_map(self) -> None:
        """Uses custom UTM source map."""
        result = generate_share_url(
            content_slug="my-article",
            platform="twitter",
            base_url="https://example.com",
            utm_source_map={"twitter": "x", "linkedin": "ln", "facebook": "fb", "native": "web"},
        )

        assert result.success is True
        assert result.utm_source == "x"

    def test_custom_utm_medium(self) -> None:
        """Uses custom UTM medium."""
        result = generate_share_url(
            content_slug="my-article",
            platform="twitter",
            base_url="https://example.com",
            utm_medium="referral",
        )

        assert result.utm_medium == "referral"

    def test_resource_path_prefix(self) -> None:
        """Works with resource path prefix."""
        result = generate_share_url(
            content_slug="my-pdf",
            platform="twitter",
            base_url="https://example.com",
            content_path_prefix="/r",
        )

        assert result.success is True
        # The content URL within the share URL is URL-encoded
        from urllib.parse import unquote
        decoded_url = unquote(result.share_url or "")
        assert "/r/my-pdf" in decoded_url

    def test_invalid_base_url_fails(self) -> None:
        """Invalid base URL returns errors."""
        result = generate_share_url(
            content_slug="my-article",
            platform="twitter",
            base_url="not-a-url",
        )

        assert result.success is False
        assert len(result.errors) > 0
        assert result.share_url is None

    def test_empty_slug_fails(self) -> None:
        """Empty slug returns errors."""
        result = generate_share_url(
            content_slug="",
            platform="twitter",
            base_url="https://example.com",
        )

        assert result.success is False
        assert any(e.code == "EMPTY_SLUG" for e in result.errors)

    def test_invalid_platform_fails(self) -> None:
        """Invalid platform returns errors."""
        result = generate_share_url(
            content_slug="my-article",
            platform="instagram",  # type: ignore
            base_url="https://example.com",
        )

        assert result.success is False
        assert any(e.code == "INVALID_PLATFORM" for e in result.errors)



# --- Run Tests (Atomic Component) ---


class TestRun:
    """Tests for run() entry point (Atomic Component Pattern)."""

    def test_run_generate_share_url(self, mock_rules: MockSharingRules) -> None:
        """run() handles GenerateShareUrlInput."""
        inp = GenerateShareUrlInput(
            content_slug="test-article",
            platform="twitter",
            base_url="https://example.com",
        )
        result = run(inp, rules=mock_rules)

        assert isinstance(result, GenerateShareUrlOutput)
        assert result.success is True
        assert result.utm_medium == "social"  # From mock rules

    def test_run_add_utm_params(self) -> None:
        """run() handles AddUtmParamsInput."""
        inp = AddUtmParamsInput(
            url="https://example.com/p/article",
            utm_source="email",
            utm_campaign="newsletter",
        )
        result = run(inp)

        assert isinstance(result, AddUtmParamsOutput)
        assert result.success is True
        assert "utm_source=email" in (result.url or "")
        assert "utm_campaign=newsletter" in (result.url or "")

    def test_run_unknown_input_raises(self) -> None:
        """run() raises ValueError for unknown input."""
        with pytest.raises(ValueError, match="Unknown input type"):
            run("invalid-input")  # type: ignore


# --- Integration Tests ---


class TestShareUrlIntegration:
    """Integration tests for complete share URL generation flow."""

    def test_full_twitter_share_flow(self) -> None:
        """Complete Twitter share URL generation."""
        result = generate_share_url(
            content_slug="python-tutorial-2024",
            platform="twitter",
            base_url="https://littleresearchlab.com",
            content_path_prefix="/p",
            title="Learn Python in 2024",
        )

        assert result.success is True
        assert result.share_url is not None

        # Verify Twitter URL structure
        assert result.share_url.startswith("https://twitter.com/intent/tweet")

        # Verify UTM params are in the encoded content URL
        has_encoded = "utm_source%3Dtwitter" in result.share_url
        has_plain = "utm_source=twitter" in result.share_url
        assert has_encoded or has_plain

    def test_url_encoding_in_share_url(self) -> None:
        """Share URL properly encodes content URL."""
        result = generate_share_url(
            content_slug="article-with-special",
            platform="twitter",
            base_url="https://example.com",
            title="Article & Special <Chars>",
        )

        assert result.success is True
        # The URL should be properly encoded
        assert "<" not in result.share_url  # type: ignore
        assert ">" not in result.share_url  # type: ignore

    def test_utm_params_survive_encoding(self) -> None:
        """UTM params are present in final share URL after encoding."""
        result = generate_share_url(
            content_slug="my-article",
            platform="linkedin",
            base_url="https://example.com",
        )

        assert result.success is True
        # LinkedIn URL contains encoded content URL with UTM params
        share_url = result.share_url or ""
        # UTM params should be URL-encoded within the share URL
        assert "utm_source" in share_url or "utm_source%3D" in share_url
