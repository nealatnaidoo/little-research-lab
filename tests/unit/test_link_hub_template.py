"""
TA-E1.1-02: Link hub template tests.

Tests for C2-PublicTemplates link hub template functionality:
- Accessibility validation - landmarks and headings (TA-E1.1-02)
- Link preparation with external detection
- Link grouping
- SSR metadata generation for /links page

These tests ensure the link hub page meets accessibility standards
and provides proper SSR metadata for social sharing.
"""

from __future__ import annotations

import pytest

from src.components.C2_PublicTemplates.fc import (
    LinkHubConfig,
    SiteConfig,
    generate_link_hub_metadata,
    generate_link_hub_render_data,
    group_link_hub_items,
    prepare_link_hub_item,
    validate_link_hub_accessibility,
)


@pytest.fixture
def site_config() -> SiteConfig:
    """Standard site configuration for tests."""
    return SiteConfig(
        base_url="https://example.com",
        site_name="Test Site",
        default_og_image="/images/default-og.png",
        twitter_handle="@testsite",
    )


@pytest.fixture
def link_hub_config() -> LinkHubConfig:
    """Standard link hub configuration for tests."""
    return LinkHubConfig(
        title="My Links",
        bio="A collection of useful links and resources.",
        profile_image_id="profile123",
        show_social_links=True,
    )


class TestLinkHubAccessibility:
    """TA-E1.1-02: Link hub accessibility validation tests."""

    def test_valid_page_structure_passes(self) -> None:
        """Valid page with landmarks and headings passes."""
        result = validate_link_hub_accessibility(
            has_main_landmark=True,
            has_nav_landmark=True,
            heading_levels=[1, 2, 2],
            link_count=5,
        )

        assert result.is_valid is True
        assert len(result.violations) == 0
        assert "main" in result.landmarks_found
        assert "nav" in result.landmarks_found

    def test_missing_main_landmark_fails(self) -> None:
        """Missing main landmark is a violation."""
        result = validate_link_hub_accessibility(
            has_main_landmark=False,
            has_nav_landmark=True,
            heading_levels=[1],
            link_count=5,
        )

        assert result.is_valid is False
        assert any("main" in v.lower() for v in result.violations)

    def test_missing_nav_landmark_fails(self) -> None:
        """Missing nav landmark is a violation."""
        result = validate_link_hub_accessibility(
            has_main_landmark=True,
            has_nav_landmark=False,
            heading_levels=[1],
            link_count=5,
        )

        assert result.is_valid is False
        assert any("nav" in v.lower() for v in result.violations)

    def test_no_headings_fails(self) -> None:
        """Page with no headings fails."""
        result = validate_link_hub_accessibility(
            has_main_landmark=True,
            has_nav_landmark=True,
            heading_levels=[],
            link_count=5,
        )

        assert result.is_valid is False
        assert any("no headings" in v.lower() for v in result.violations)

    def test_first_heading_not_h1_fails(self) -> None:
        """Page starting with h2 fails."""
        result = validate_link_hub_accessibility(
            has_main_landmark=True,
            has_nav_landmark=True,
            heading_levels=[2, 3],
            link_count=5,
        )

        assert result.is_valid is False
        assert any("h1" in v for v in result.violations)

    def test_skipped_heading_level_fails(self) -> None:
        """Skipped heading level (h1 to h3) fails."""
        result = validate_link_hub_accessibility(
            has_main_landmark=True,
            has_nav_landmark=True,
            heading_levels=[1, 3],  # Skips h2
            link_count=5,
        )

        assert result.is_valid is False
        assert any("skipped" in v.lower() for v in result.violations)

    def test_heading_can_go_up_levels(self) -> None:
        """Heading can go from h3 back to h2."""
        result = validate_link_hub_accessibility(
            has_main_landmark=True,
            has_nav_landmark=True,
            heading_levels=[1, 2, 3, 2],  # h3 back to h2 is OK
            link_count=5,
        )

        assert result.is_valid is True

    def test_high_link_count_warning(self) -> None:
        """High link count triggers warning."""
        result = validate_link_hub_accessibility(
            has_main_landmark=True,
            has_nav_landmark=True,
            heading_levels=[1],
            link_count=25,
        )

        assert result.is_valid is True
        assert any("25" in w for w in result.warnings)

    def test_links_without_nav_warning(self) -> None:
        """Links without nav landmark triggers warning."""
        result = validate_link_hub_accessibility(
            has_main_landmark=True,
            has_nav_landmark=False,
            heading_levels=[1],
            link_count=5,
        )

        # Violation for missing nav, plus warning about links
        assert not result.is_valid
        assert any("nav" in w.lower() for w in result.warnings)


class TestLinkHubItemPreparation:
    """Link item preparation tests."""

    def test_prepares_internal_link(self) -> None:
        """Correctly identifies internal link."""
        item = prepare_link_hub_item(
            link_id="link1",
            title="Internal Link",
            url="/about",
            icon="info",
            position=0,
            group_id=None,
            base_url="https://example.com",
        )

        assert item.id == "link1"
        assert item.title == "Internal Link"
        assert item.url == "/about"
        assert item.is_external is False

    def test_prepares_external_link(self) -> None:
        """Correctly identifies external link."""
        item = prepare_link_hub_item(
            link_id="link2",
            title="External Link",
            url="https://other.com/page",
            icon="external",
            position=1,
            group_id="social",
            base_url="https://example.com",
        )

        assert item.id == "link2"
        assert item.is_external is True
        assert item.group_id == "social"

    def test_same_domain_is_internal(self) -> None:
        """Same domain absolute URL is internal."""
        item = prepare_link_hub_item(
            link_id="link3",
            title="Same Domain",
            url="https://example.com/page",
            icon=None,
            position=0,
            group_id=None,
            base_url="https://example.com",
        )

        assert item.is_external is False


class TestLinkGrouping:
    """Link grouping tests."""

    def test_groups_links_by_group_id(self) -> None:
        """Links are grouped by group_id."""
        links = [
            prepare_link_hub_item("1", "Link 1", "/a", None, 0, "group1", None),
            prepare_link_hub_item("2", "Link 2", "/b", None, 1, "group1", None),
            prepare_link_hub_item("3", "Link 3", "/c", None, 0, "group2", None),
        ]
        groups = {"group1": "Group One", "group2": "Group Two"}

        result = group_link_hub_items(links, groups)

        # Should have 2 groups
        group_ids = [g.id for g in result]
        assert "group1" in group_ids
        assert "group2" in group_ids

    def test_ungrouped_links_first(self) -> None:
        """Links without group_id appear first."""
        links = [
            prepare_link_hub_item("1", "Grouped", "/a", None, 0, "group1", None),
            prepare_link_hub_item("2", "Ungrouped", "/b", None, 0, None, None),
        ]
        groups = {"group1": "Group One"}

        result = group_link_hub_items(links, groups)

        # Ungrouped should be first (position -1)
        assert result[0].id is None
        assert result[0].links[0].title == "Ungrouped"

    def test_links_sorted_by_position_within_group(self) -> None:
        """Links within a group are sorted by position."""
        links = [
            prepare_link_hub_item("1", "Third", "/c", None, 2, "group1", None),
            prepare_link_hub_item("2", "First", "/a", None, 0, "group1", None),
            prepare_link_hub_item("3", "Second", "/b", None, 1, "group1", None),
        ]
        groups = {"group1": "Group One"}

        result = group_link_hub_items(links, groups)

        group_links = result[0].links
        assert group_links[0].title == "First"
        assert group_links[1].title == "Second"
        assert group_links[2].title == "Third"

    def test_empty_links_returns_empty_groups(self) -> None:
        """Empty links list returns empty groups."""
        result = group_link_hub_items([], {"group1": "Group One"})

        assert len(result) == 0


class TestLinkHubMetadata:
    """Link hub SSR metadata generation tests."""

    def test_generates_metadata_with_bio(
        self, site_config: SiteConfig, link_hub_config: LinkHubConfig
    ) -> None:
        """Generates metadata using bio for description."""
        metadata = generate_link_hub_metadata(
            config=link_hub_config,
            link_count=10,
            site_config=site_config,
        )

        assert metadata.title == "My Links"
        assert "collection" in metadata.description.lower()

    def test_generates_default_description_without_bio(
        self, site_config: SiteConfig
    ) -> None:
        """Generates default description when no bio."""
        config = LinkHubConfig(title="Links", bio=None)
        metadata = generate_link_hub_metadata(
            config=config,
            link_count=5,
            site_config=site_config,
        )

        assert "Test Site" in metadata.description
        assert "5 links" in metadata.description

    def test_canonical_url_is_links_page(
        self, site_config: SiteConfig, link_hub_config: LinkHubConfig
    ) -> None:
        """Canonical URL points to /links."""
        metadata = generate_link_hub_metadata(
            config=link_hub_config,
            link_count=10,
            site_config=site_config,
        )

        assert metadata.canonical_url == "https://example.com/links"

    def test_uses_profile_og_type(
        self, site_config: SiteConfig, link_hub_config: LinkHubConfig
    ) -> None:
        """Uses 'profile' OG type for link hub."""
        metadata = generate_link_hub_metadata(
            config=link_hub_config,
            link_count=10,
            site_config=site_config,
        )

        assert metadata.og_type == "profile"

    def test_uses_profile_image_for_og(
        self, site_config: SiteConfig, link_hub_config: LinkHubConfig
    ) -> None:
        """Uses profile image for OG image."""
        metadata = generate_link_hub_metadata(
            config=link_hub_config,
            link_count=10,
            site_config=site_config,
        )

        assert metadata.og_image is not None
        assert "profile123" in metadata.og_image

    def test_falls_back_to_default_og_image(self, site_config: SiteConfig) -> None:
        """Falls back to default OG image when no profile image."""
        config = LinkHubConfig(title="Links", profile_image_id=None)
        metadata = generate_link_hub_metadata(
            config=config,
            link_count=10,
            site_config=site_config,
        )

        assert metadata.og_image is not None
        assert "default-og" in metadata.og_image

    def test_uses_summary_twitter_card(
        self, site_config: SiteConfig, link_hub_config: LinkHubConfig
    ) -> None:
        """Uses summary Twitter card (not large image)."""
        metadata = generate_link_hub_metadata(
            config=link_hub_config,
            link_count=10,
            site_config=site_config,
        )

        assert metadata.twitter_card == "summary"


class TestLinkHubRenderData:
    """Link hub render data generation tests."""

    def test_generates_complete_render_data(
        self, site_config: SiteConfig, link_hub_config: LinkHubConfig
    ) -> None:
        """Generates complete render data."""
        links = [
            ("id1", "Link 1", "https://external.com", "icon1", 0, None),
            ("id2", "Link 2", "/internal", None, 1, "group1"),
        ]
        groups = {"group1": "Social"}

        render_data = generate_link_hub_render_data(
            config=link_hub_config,
            links=links,
            groups=groups,
            base_url=site_config.base_url,
        )

        assert render_data.config == link_hub_config
        assert render_data.total_links == 2
        assert render_data.profile_image_url is not None

    def test_marks_external_links(self, link_hub_config: LinkHubConfig) -> None:
        """External links are marked correctly."""
        links = [
            ("id1", "External", "https://other.com", None, 0, None),
            ("id2", "Internal", "/page", None, 1, None),
        ]

        render_data = generate_link_hub_render_data(
            config=link_hub_config,
            links=links,
            groups={},
            base_url="https://example.com",
        )

        # Find the ungrouped group
        ungrouped = next(g for g in render_data.groups if g.id is None)
        external_link = next(
            link for link in ungrouped.links if link.title == "External"
        )
        internal_link = next(
            link for link in ungrouped.links if link.title == "Internal"
        )

        assert external_link.is_external is True
        assert internal_link.is_external is False

    def test_handles_empty_links(self, link_hub_config: LinkHubConfig) -> None:
        """Handles empty links list."""
        render_data = generate_link_hub_render_data(
            config=link_hub_config,
            links=[],
            groups={},
            base_url="https://example.com",
        )

        assert render_data.total_links == 0
        assert len(render_data.groups) == 0
