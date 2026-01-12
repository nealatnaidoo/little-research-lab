"""
AnalyticsAttributionService (E6.2) - UTM and referrer attribution parsing.

Handles parsing and classification of traffic sources.

Spec refs: E6.2, TA-0036, TA-0037
Test assertions:
- TA-0036: UTM parameter parsing and validation
- TA-0037: Referrer domain extraction and classification

Key behaviors:
- Extract and validate UTM parameters
- Parse referrer URLs and extract domains
- Classify traffic sources (organic, social, email, etc.)
- Handle edge cases (missing, malformed data)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any
from urllib.parse import urlparse

# --- Enums ---


class TrafficSource(str, Enum):
    """Traffic source classification."""

    DIRECT = "direct"  # No referrer
    ORGANIC_SEARCH = "organic_search"  # Google, Bing, etc.
    PAID_SEARCH = "paid_search"  # CPC campaigns
    SOCIAL = "social"  # Facebook, Twitter, etc.
    EMAIL = "email"  # Email campaigns
    REFERRAL = "referral"  # Other websites
    AFFILIATE = "affiliate"  # Affiliate traffic
    DISPLAY = "display"  # Display ads
    OTHER = "other"


class SearchEngine(str, Enum):
    """Known search engines."""

    GOOGLE = "google"
    BING = "bing"
    YAHOO = "yahoo"
    DUCKDUCKGO = "duckduckgo"
    BAIDU = "baidu"
    YANDEX = "yandex"
    OTHER = "other"


class SocialNetwork(str, Enum):
    """Known social networks."""

    FACEBOOK = "facebook"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    PINTEREST = "pinterest"
    REDDIT = "reddit"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    OTHER = "other"


# --- Configuration ---


@dataclass(frozen=True)
class AttributionConfig:
    """Attribution configuration."""

    # Search engine domain patterns
    search_engine_domains: tuple[tuple[str, SearchEngine], ...] = (
        ("google.", SearchEngine.GOOGLE),
        ("bing.", SearchEngine.BING),
        ("yahoo.", SearchEngine.YAHOO),
        ("duckduckgo.", SearchEngine.DUCKDUCKGO),
        ("baidu.", SearchEngine.BAIDU),
        ("yandex.", SearchEngine.YANDEX),
    )

    # Social network domain patterns
    social_network_domains: tuple[tuple[str, SocialNetwork], ...] = (
        ("facebook.", SocialNetwork.FACEBOOK),
        ("fb.", SocialNetwork.FACEBOOK),
        ("twitter.", SocialNetwork.TWITTER),
        ("x.com", SocialNetwork.TWITTER),
        ("t.co", SocialNetwork.TWITTER),
        ("linkedin.", SocialNetwork.LINKEDIN),
        ("lnkd.", SocialNetwork.LINKEDIN),
        ("instagram.", SocialNetwork.INSTAGRAM),
        ("pinterest.", SocialNetwork.PINTEREST),
        ("reddit.", SocialNetwork.REDDIT),
        ("youtube.", SocialNetwork.YOUTUBE),
        ("youtu.be", SocialNetwork.YOUTUBE),
        ("tiktok.", SocialNetwork.TIKTOK),
    )

    # UTM medium mappings
    medium_to_source: dict[str, TrafficSource] = None  # type: ignore

    def __post_init__(self) -> None:
        """Initialize medium mappings."""
        if self.medium_to_source is None:
            object.__setattr__(
                self,
                "medium_to_source",
                {
                    "cpc": TrafficSource.PAID_SEARCH,
                    "ppc": TrafficSource.PAID_SEARCH,
                    "paid": TrafficSource.PAID_SEARCH,
                    "paidsearch": TrafficSource.PAID_SEARCH,
                    "email": TrafficSource.EMAIL,
                    "newsletter": TrafficSource.EMAIL,
                    "social": TrafficSource.SOCIAL,
                    "social-media": TrafficSource.SOCIAL,
                    "affiliate": TrafficSource.AFFILIATE,
                    "display": TrafficSource.DISPLAY,
                    "banner": TrafficSource.DISPLAY,
                    "cpm": TrafficSource.DISPLAY,
                    "organic": TrafficSource.ORGANIC_SEARCH,
                    "referral": TrafficSource.REFERRAL,
                },
            )


DEFAULT_CONFIG = AttributionConfig()


# --- Data Models ---


@dataclass
class UTMParams:
    """Parsed UTM parameters (TA-0036)."""

    source: str | None = None
    medium: str | None = None
    campaign: str | None = None
    content: str | None = None
    term: str | None = None

    def has_any(self) -> bool:
        """Check if any UTM parameter is present."""
        return any(
            [
                self.source,
                self.medium,
                self.campaign,
                self.content,
                self.term,
            ]
        )


@dataclass
class ReferrerInfo:
    """Parsed referrer information (TA-0037)."""

    url: str | None = None
    domain: str | None = None
    subdomain: str | None = None
    path: str | None = None
    is_search_engine: bool = False
    search_engine: SearchEngine | None = None
    is_social_network: bool = False
    social_network: SocialNetwork | None = None


@dataclass
class Attribution:
    """Full attribution result."""

    source: TrafficSource
    utm: UTMParams
    referrer: ReferrerInfo
    channel: str  # Human-readable channel name


# --- Parsing Functions ---


def parse_utm_params(data: dict[str, Any]) -> UTMParams:
    """
    Parse UTM parameters from data (TA-0036).

    Handles both prefixed (utm_source) and unprefixed (source) keys.
    Normalizes values to lowercase.
    """

    def get_param(key: str) -> str | None:
        # Try prefixed first, then unprefixed
        value = data.get(f"utm_{key}") or data.get(key)
        if value and isinstance(value, str):
            return value.strip().lower() or None
        return None

    return UTMParams(
        source=get_param("source"),
        medium=get_param("medium"),
        campaign=get_param("campaign"),
        content=get_param("content"),
        term=get_param("term"),
    )


def parse_domain(url: str) -> tuple[str | None, str | None]:
    """
    Extract domain and subdomain from URL.

    Returns (domain, subdomain) tuple.
    """
    if not url:
        return None, None

    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()

        if not host:
            return None, None

        # Remove port if present
        if ":" in host:
            host = host.split(":")[0]

        # Extract domain parts
        parts = host.split(".")

        if len(parts) >= 2:
            # Handle common TLDs
            if parts[-1] in ("uk", "au", "nz", "jp", "de") and len(parts) >= 3:
                # Two-part TLD like .co.uk
                domain = ".".join(parts[-3:])
                subdomain = ".".join(parts[:-3]) if len(parts) > 3 else None
            else:
                domain = ".".join(parts[-2:])
                subdomain = ".".join(parts[:-2]) if len(parts) > 2 else None
        else:
            domain = host
            subdomain = None

        return domain, subdomain

    except Exception:
        return None, None


def parse_referrer(
    url: str | None,
    config: AttributionConfig = DEFAULT_CONFIG,
) -> ReferrerInfo:
    """
    Parse referrer URL (TA-0037).

    Extracts domain, detects search engines and social networks.
    """
    if not url:
        return ReferrerInfo()

    try:
        parsed = urlparse(url)
        domain, subdomain = parse_domain(url)

        info = ReferrerInfo(
            url=url,
            domain=domain,
            subdomain=subdomain,
            path=parsed.path or None,
        )

        if not domain:
            return info

        # Check for search engines
        for pattern, engine in config.search_engine_domains:
            if pattern in domain or (subdomain and pattern in subdomain):
                info.is_search_engine = True
                info.search_engine = engine
                break

        # Check for social networks
        for pattern, network in config.social_network_domains:
            if pattern in domain or (subdomain and pattern in subdomain):
                info.is_social_network = True
                info.social_network = network
                break

        return info

    except Exception:
        return ReferrerInfo(url=url)


def classify_traffic_source(
    utm: UTMParams,
    referrer: ReferrerInfo,
    config: AttributionConfig = DEFAULT_CONFIG,
) -> TrafficSource:
    """
    Classify traffic source based on UTM and referrer.

    Priority:
    1. UTM medium if present
    2. UTM source if present
    3. Referrer classification
    4. Default to direct
    """
    # Check UTM medium first
    if utm.medium:
        medium_lower = utm.medium.lower()
        if medium_lower in config.medium_to_source:
            return config.medium_to_source[medium_lower]

    # Check UTM source
    if utm.source:
        source_lower = utm.source.lower()

        # Check if source matches a search engine
        for pattern, _ in config.search_engine_domains:
            if pattern.rstrip(".") in source_lower:
                if utm.medium and utm.medium in ("cpc", "ppc", "paid"):
                    return TrafficSource.PAID_SEARCH
                return TrafficSource.ORGANIC_SEARCH

        # Check if source matches a social network
        for pattern, _ in config.social_network_domains:
            if pattern.rstrip(".") in source_lower:
                return TrafficSource.SOCIAL

        # Check for email
        if "email" in source_lower or "newsletter" in source_lower:
            return TrafficSource.EMAIL

    # Fall back to referrer-based classification
    if referrer.is_search_engine:
        return TrafficSource.ORGANIC_SEARCH

    if referrer.is_social_network:
        return TrafficSource.SOCIAL

    if referrer.domain:
        return TrafficSource.REFERRAL

    return TrafficSource.DIRECT


def get_channel_name(
    source: TrafficSource,
    utm: UTMParams,
    referrer: ReferrerInfo,
) -> str:
    """
    Get human-readable channel name.
    """
    if source == TrafficSource.DIRECT:
        return "Direct"

    if source == TrafficSource.ORGANIC_SEARCH:
        if referrer.search_engine:
            return f"Organic Search ({referrer.search_engine.value.title()})"
        if utm.source:
            return f"Organic Search ({utm.source.title()})"
        return "Organic Search"

    if source == TrafficSource.PAID_SEARCH:
        if utm.source:
            return f"Paid Search ({utm.source.title()})"
        return "Paid Search"

    if source == TrafficSource.SOCIAL:
        if referrer.social_network:
            return f"Social ({referrer.social_network.value.title()})"
        if utm.source:
            return f"Social ({utm.source.title()})"
        return "Social"

    if source == TrafficSource.EMAIL:
        if utm.campaign:
            return f"Email ({utm.campaign})"
        return "Email"

    if source == TrafficSource.REFERRAL:
        if referrer.domain:
            return f"Referral ({referrer.domain})"
        return "Referral"

    if source == TrafficSource.AFFILIATE:
        return "Affiliate"

    if source == TrafficSource.DISPLAY:
        return "Display"

    return "Other"


# --- Attribution Service ---


class AttributionService:
    """
    Attribution service (E6.2).

    Parses UTM parameters and referrer data to classify traffic sources.
    """

    def __init__(
        self,
        config: AttributionConfig | None = None,
    ) -> None:
        """Initialize service."""
        self._config = config or DEFAULT_CONFIG

    def parse_utm(self, data: dict[str, Any]) -> UTMParams:
        """Parse UTM parameters from data (TA-0036)."""
        return parse_utm_params(data)

    def parse_referrer(self, url: str | None) -> ReferrerInfo:
        """Parse referrer URL (TA-0037)."""
        return parse_referrer(url, self._config)

    def classify(
        self,
        utm: UTMParams,
        referrer: ReferrerInfo,
    ) -> TrafficSource:
        """Classify traffic source."""
        return classify_traffic_source(utm, referrer, self._config)

    def attribute(
        self,
        data: dict[str, Any],
        referrer_url: str | None = None,
    ) -> Attribution:
        """
        Full attribution from data.

        Parses UTM params, referrer, and classifies traffic source.
        """
        utm = self.parse_utm(data)
        referrer = self.parse_referrer(referrer_url or data.get("referrer"))
        source = self.classify(utm, referrer)
        channel = get_channel_name(source, utm, referrer)

        return Attribution(
            source=source,
            utm=utm,
            referrer=referrer,
            channel=channel,
        )


# --- Factory ---


def create_attribution_service(
    config: AttributionConfig | None = None,
) -> AttributionService:
    """Create an AttributionService."""
    return AttributionService(config=config)
