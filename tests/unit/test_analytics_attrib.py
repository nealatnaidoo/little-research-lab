"""
Tests for AnalyticsAttributionService (E6.2).

Test assertions:
- TA-0036: UTM parameter parsing and validation
- TA-0037: Referrer domain extraction and classification
"""

from __future__ import annotations

import pytest

from src.components.analytics import (
    AttributionConfig,
    AttributionService,
    ReferrerInfo,
    SearchEngine,
    SocialNetwork,
    TrafficSource,
    UTMParams,
    classify_traffic_source,
    create_attribution_service,
    get_channel_name,
    parse_domain,
    parse_referrer,
    parse_utm_params,
)

# --- Fixtures ---


@pytest.fixture
def service() -> AttributionService:
    """Attribution service."""
    return AttributionService()


# --- TA-0036: UTM Parameter Parsing ---


class TestParseUTMParams:
    """Test TA-0036: UTM parameter parsing."""

    def test_parse_prefixed_utm(self) -> None:
        """Parse prefixed UTM parameters."""
        data = {
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "summer_sale",
            "utm_content": "banner_1",
            "utm_term": "running shoes",
        }

        result = parse_utm_params(data)

        assert result.source == "google"
        assert result.medium == "cpc"
        assert result.campaign == "summer_sale"
        assert result.content == "banner_1"
        assert result.term == "running shoes"

    def test_parse_unprefixed(self) -> None:
        """Parse unprefixed parameters."""
        data = {
            "source": "newsletter",
            "medium": "email",
        }

        result = parse_utm_params(data)

        assert result.source == "newsletter"
        assert result.medium == "email"

    def test_prefixed_takes_priority(self) -> None:
        """Prefixed UTM takes priority over unprefixed."""
        data = {
            "utm_source": "google",
            "source": "bing",
        }

        result = parse_utm_params(data)
        assert result.source == "google"

    def test_normalize_to_lowercase(self) -> None:
        """Values are normalized to lowercase."""
        data = {
            "utm_source": "GOOGLE",
            "utm_medium": "CPC",
        }

        result = parse_utm_params(data)

        assert result.source == "google"
        assert result.medium == "cpc"

    def test_strip_whitespace(self) -> None:
        """Whitespace is stripped."""
        data = {"utm_source": "  google  "}

        result = parse_utm_params(data)
        assert result.source == "google"

    def test_empty_values_become_none(self) -> None:
        """Empty strings become None."""
        data = {"utm_source": "", "utm_medium": "   "}

        result = parse_utm_params(data)

        assert result.source is None
        assert result.medium is None

    def test_no_params_returns_empty(self) -> None:
        """No UTM params returns empty object."""
        data = {"path": "/page"}

        result = parse_utm_params(data)

        assert result.source is None
        assert result.medium is None
        assert result.campaign is None
        assert not result.has_any()

    def test_has_any_true(self) -> None:
        """has_any returns True when any param present."""
        result = UTMParams(source="google")
        assert result.has_any() is True

    def test_has_any_false(self) -> None:
        """has_any returns False when no params."""
        result = UTMParams()
        assert result.has_any() is False


# --- Domain Parsing ---


class TestParseDomain:
    """Test domain parsing."""

    def test_simple_domain(self) -> None:
        """Parse simple domain."""
        domain, subdomain = parse_domain("https://example.com/path")

        assert domain == "example.com"
        assert subdomain is None

    def test_subdomain(self) -> None:
        """Parse domain with subdomain."""
        domain, subdomain = parse_domain("https://www.example.com/path")

        assert domain == "example.com"
        assert subdomain == "www"

    def test_multiple_subdomains(self) -> None:
        """Parse multiple subdomains."""
        domain, subdomain = parse_domain("https://blog.www.example.com")

        assert domain == "example.com"
        assert subdomain == "blog.www"

    def test_with_port(self) -> None:
        """Handle URL with port."""
        domain, subdomain = parse_domain("http://localhost:8080/path")

        assert domain == "localhost"  # Not ideal but handles edge case

    def test_empty_url(self) -> None:
        """Handle empty URL."""
        domain, subdomain = parse_domain("")

        assert domain is None
        assert subdomain is None

    def test_invalid_url(self) -> None:
        """Handle invalid URL gracefully."""
        domain, subdomain = parse_domain("not a url")

        assert domain is None
        assert subdomain is None


# --- TA-0037: Referrer Parsing ---


class TestParseReferrer:
    """Test TA-0037: Referrer domain extraction and classification."""

    def test_empty_referrer(self) -> None:
        """Handle empty referrer."""
        result = parse_referrer(None)

        assert result.url is None
        assert result.domain is None
        assert not result.is_search_engine
        assert not result.is_social_network

    def test_google_search(self) -> None:
        """Detect Google as search engine."""
        result = parse_referrer("https://www.google.com/search?q=test")

        assert result.domain == "google.com"
        assert result.is_search_engine is True
        assert result.search_engine == SearchEngine.GOOGLE
        assert result.is_social_network is False

    def test_bing_search(self) -> None:
        """Detect Bing as search engine."""
        result = parse_referrer("https://www.bing.com/search?q=test")

        assert result.is_search_engine is True
        assert result.search_engine == SearchEngine.BING

    def test_duckduckgo_search(self) -> None:
        """Detect DuckDuckGo as search engine."""
        result = parse_referrer("https://duckduckgo.com/?q=test")

        assert result.is_search_engine is True
        assert result.search_engine == SearchEngine.DUCKDUCKGO

    def test_facebook_social(self) -> None:
        """Detect Facebook as social network."""
        result = parse_referrer("https://www.facebook.com/post/123")

        assert result.is_social_network is True
        assert result.social_network == SocialNetwork.FACEBOOK
        assert result.is_search_engine is False

    def test_twitter_social(self) -> None:
        """Detect Twitter as social network."""
        result = parse_referrer("https://twitter.com/user/status/123")

        assert result.is_social_network is True
        assert result.social_network == SocialNetwork.TWITTER

    def test_x_dot_com(self) -> None:
        """Detect x.com as Twitter."""
        result = parse_referrer("https://x.com/user/status/123")

        assert result.is_social_network is True
        assert result.social_network == SocialNetwork.TWITTER

    def test_tco_short_link(self) -> None:
        """Detect t.co short links as Twitter."""
        result = parse_referrer("https://t.co/abc123")

        assert result.is_social_network is True
        assert result.social_network == SocialNetwork.TWITTER

    def test_linkedin_social(self) -> None:
        """Detect LinkedIn as social network."""
        result = parse_referrer("https://www.linkedin.com/post/123")

        assert result.is_social_network is True
        assert result.social_network == SocialNetwork.LINKEDIN

    def test_youtube_social(self) -> None:
        """Detect YouTube as social network."""
        result = parse_referrer("https://www.youtube.com/watch?v=abc")

        assert result.is_social_network is True
        assert result.social_network == SocialNetwork.YOUTUBE

    def test_regular_referrer(self) -> None:
        """Regular referrer is not classified."""
        result = parse_referrer("https://example.com/page")

        assert result.domain == "example.com"
        assert result.is_search_engine is False
        assert result.is_social_network is False


# --- Traffic Source Classification ---


class TestClassifyTrafficSource:
    """Test traffic source classification."""

    def test_direct_no_data(self) -> None:
        """No referrer or UTM = direct."""
        utm = UTMParams()
        referrer = ReferrerInfo()

        result = classify_traffic_source(utm, referrer)
        assert result == TrafficSource.DIRECT

    def test_organic_search_from_referrer(self) -> None:
        """Search engine referrer = organic search."""
        utm = UTMParams()
        referrer = ReferrerInfo(
            domain="google.com",
            is_search_engine=True,
            search_engine=SearchEngine.GOOGLE,
        )

        result = classify_traffic_source(utm, referrer)
        assert result == TrafficSource.ORGANIC_SEARCH

    def test_paid_search_from_utm(self) -> None:
        """CPC medium = paid search."""
        utm = UTMParams(source="google", medium="cpc")
        referrer = ReferrerInfo()

        result = classify_traffic_source(utm, referrer)
        assert result == TrafficSource.PAID_SEARCH

    def test_social_from_referrer(self) -> None:
        """Social network referrer = social."""
        utm = UTMParams()
        referrer = ReferrerInfo(
            domain="facebook.com",
            is_social_network=True,
            social_network=SocialNetwork.FACEBOOK,
        )

        result = classify_traffic_source(utm, referrer)
        assert result == TrafficSource.SOCIAL

    def test_email_from_medium(self) -> None:
        """Email medium = email."""
        utm = UTMParams(source="newsletter", medium="email")
        referrer = ReferrerInfo()

        result = classify_traffic_source(utm, referrer)
        assert result == TrafficSource.EMAIL

    def test_referral(self) -> None:
        """Regular referrer = referral."""
        utm = UTMParams()
        referrer = ReferrerInfo(domain="example.com")

        result = classify_traffic_source(utm, referrer)
        assert result == TrafficSource.REFERRAL

    def test_utm_takes_priority_over_referrer(self) -> None:
        """UTM medium takes priority."""
        utm = UTMParams(medium="email")
        referrer = ReferrerInfo(
            domain="google.com",
            is_search_engine=True,
        )

        result = classify_traffic_source(utm, referrer)
        assert result == TrafficSource.EMAIL


# --- Channel Naming ---


class TestGetChannelName:
    """Test human-readable channel names."""

    def test_direct(self) -> None:
        """Direct channel."""
        name = get_channel_name(
            TrafficSource.DIRECT,
            UTMParams(),
            ReferrerInfo(),
        )
        assert name == "Direct"

    def test_organic_with_engine(self) -> None:
        """Organic search with known engine."""
        name = get_channel_name(
            TrafficSource.ORGANIC_SEARCH,
            UTMParams(),
            ReferrerInfo(search_engine=SearchEngine.GOOGLE),
        )
        assert "Google" in name

    def test_social_with_network(self) -> None:
        """Social with known network."""
        name = get_channel_name(
            TrafficSource.SOCIAL,
            UTMParams(),
            ReferrerInfo(social_network=SocialNetwork.FACEBOOK),
        )
        assert "Facebook" in name

    def test_referral_with_domain(self) -> None:
        """Referral with domain."""
        name = get_channel_name(
            TrafficSource.REFERRAL,
            UTMParams(),
            ReferrerInfo(domain="example.com"),
        )
        assert "example.com" in name


# --- Attribution Service ---


class TestAttributionService:
    """Test the full attribution service."""

    def test_attribute_direct(self, service: AttributionService) -> None:
        """Direct traffic attribution."""
        result = service.attribute({}, None)

        assert result.source == TrafficSource.DIRECT
        assert result.channel == "Direct"

    def test_attribute_with_utm(self, service: AttributionService) -> None:
        """Attribution with UTM parameters."""
        data = {
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "summer_sale",
        }

        result = service.attribute(data)

        assert result.source == TrafficSource.PAID_SEARCH
        assert result.utm.source == "google"
        assert result.utm.medium == "cpc"
        assert result.utm.campaign == "summer_sale"

    def test_attribute_with_referrer(self, service: AttributionService) -> None:
        """Attribution with referrer."""
        result = service.attribute({}, "https://www.google.com/search?q=test")

        assert result.source == TrafficSource.ORGANIC_SEARCH
        assert result.referrer.is_search_engine is True

    def test_attribute_combined(self, service: AttributionService) -> None:
        """Attribution with both UTM and referrer."""
        data = {"utm_source": "facebook", "utm_medium": "social"}
        referrer = "https://facebook.com/post/123"

        result = service.attribute(data, referrer)

        assert result.source == TrafficSource.SOCIAL
        assert result.utm.source == "facebook"
        assert result.referrer.is_social_network is True

    def test_attribute_from_data_referrer(self, service: AttributionService) -> None:
        """Attribution uses referrer from data if not passed."""
        data = {"referrer": "https://twitter.com/status/123"}

        result = service.attribute(data)

        assert result.referrer.is_social_network is True
        assert result.source == TrafficSource.SOCIAL


# --- Factory ---


class TestFactory:
    """Test factory function."""

    def test_create_service(self) -> None:
        """Factory creates service."""
        service = create_attribution_service()
        assert isinstance(service, AttributionService)

    def test_create_with_config(self) -> None:
        """Factory accepts config."""
        config = AttributionConfig()
        service = create_attribution_service(config)
        assert isinstance(service, AttributionService)
