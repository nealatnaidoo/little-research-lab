"""
Tests for RichText Service (E4.1, E4.2).

Test assertions:
- TA-0019: Schema validation (allowed nodes/attrs)
- TA-0021: Sanitizer strips disallowed tags/attrs
- TA-0022: Link sanitization (forbidden protocols, rel attrs)
"""

from __future__ import annotations

import pytest

from src.components.richtext import (
    RichTextConfig,
    RichTextService,
    build_link_rel,
    count_links,
    is_safe_url,
    sanitize_document,
    sanitize_html,
    sanitize_url,
    validate_mark_type,
    validate_node_type,
    validate_rich_text,
    validate_schema,
    validate_size,
)

# --- Fixtures ---


@pytest.fixture
def config() -> RichTextConfig:
    """Default rich text configuration."""
    return RichTextConfig()


@pytest.fixture
def service(config: RichTextConfig) -> RichTextService:
    """Rich text service with default config."""
    return RichTextService(config)


@pytest.fixture
def simple_doc() -> dict:
    """Simple valid document."""
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Hello, world!"}]}],
    }


@pytest.fixture
def doc_with_link() -> dict:
    """Document with a link."""
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "Click here",
                        "marks": [{"type": "link", "attrs": {"href": "https://example.com"}}],
                    }
                ],
            }
        ],
    }


@pytest.fixture
def doc_with_image() -> dict:
    """Document with an image."""
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "image",
                        "attrs": {"src": "https://example.com/image.png", "alt": "Test image"},
                    }
                ],
            }
        ],
    }


# --- TA-0019: Schema Validation ---


class TestSchemaValidation:
    """Test TA-0019: Schema validates allowed nodes/attrs."""

    def test_valid_paragraph(self, config: RichTextConfig) -> None:
        """Paragraph node type is allowed."""
        assert validate_node_type("paragraph", config) is True

    def test_valid_heading(self, config: RichTextConfig) -> None:
        """Heading node type is allowed."""
        assert validate_node_type("heading", config) is True

    def test_valid_blockquote(self, config: RichTextConfig) -> None:
        """Blockquote node type is allowed."""
        assert validate_node_type("blockquote", config) is True

    def test_valid_lists(self, config: RichTextConfig) -> None:
        """List node types are allowed."""
        assert validate_node_type("bulletList", config) is True
        assert validate_node_type("orderedList", config) is True
        assert validate_node_type("listItem", config) is True

    def test_valid_code_block(self, config: RichTextConfig) -> None:
        """Code block node type is allowed."""
        assert validate_node_type("codeBlock", config) is True

    def test_valid_image(self, config: RichTextConfig) -> None:
        """Image node type is allowed."""
        assert validate_node_type("image", config) is True

    def test_invalid_node_type(self, config: RichTextConfig) -> None:
        """Invalid node types are rejected."""
        assert validate_node_type("script", config) is False
        assert validate_node_type("iframe", config) is False
        assert validate_node_type("form", config) is False

    def test_valid_marks(self, config: RichTextConfig) -> None:
        """Valid mark types are allowed."""
        assert validate_mark_type("bold", config) is True
        assert validate_mark_type("strong", config) is True
        assert validate_mark_type("italic", config) is True
        assert validate_mark_type("em", config) is True
        assert validate_mark_type("code", config) is True
        assert validate_mark_type("link", config) is True

    def test_invalid_mark_type(self, config: RichTextConfig) -> None:
        """Invalid mark types are rejected."""
        assert validate_mark_type("script", config) is False
        assert validate_mark_type("style", config) is False

    def test_validate_simple_doc(self, simple_doc: dict, config: RichTextConfig) -> None:
        """Simple document passes validation."""
        errors = validate_schema(simple_doc, config)
        assert len(errors) == 0

    def test_validate_doc_with_invalid_node(self, config: RichTextConfig) -> None:
        """Document with invalid node type fails validation."""
        doc = {"type": "doc", "content": [{"type": "script", "content": []}]}
        errors = validate_schema(doc, config)
        assert len(errors) > 0
        assert any(e.code == "invalid_node_type" for e in errors)

    def test_validate_doc_with_invalid_mark(self, config: RichTextConfig) -> None:
        """Document with invalid mark type fails validation."""
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "test", "marks": [{"type": "script"}]}],
                }
            ],
        }
        errors = validate_schema(doc, config)
        assert len(errors) > 0
        assert any(e.code == "invalid_mark_type" for e in errors)

    def test_validate_doc_with_invalid_attr(self, config: RichTextConfig) -> None:
        """Document with invalid attribute fails validation."""
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "image",
                    "attrs": {
                        "src": "test.png",
                        "onclick": "alert('xss')",  # Invalid attr
                    },
                }
            ],
        }
        errors = validate_schema(doc, config)
        assert len(errors) > 0
        assert any(e.code == "invalid_attribute" for e in errors)


# --- TA-0021: Sanitizer Strips Disallowed Content ---


class TestSanitizerStripping:
    """Test TA-0021: Sanitizer strips disallowed tags/attrs."""

    def test_strip_disallowed_node(self, config: RichTextConfig) -> None:
        """Disallowed nodes are stripped."""
        doc = {
            "type": "doc",
            "content": [
                {"type": "script", "content": []},
                {"type": "paragraph", "content": [{"type": "text", "text": "ok"}]},
            ],
        }
        sanitized, errors = sanitize_document(doc, config)

        # Script node should be stripped
        content_types = [c["type"] for c in sanitized.get("content", [])]
        assert "script" not in content_types
        assert "paragraph" in content_types
        assert any(e.code == "stripped_node" for e in errors)

    def test_strip_disallowed_mark(self, config: RichTextConfig) -> None:
        """Disallowed marks are stripped."""
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "test",
                            "marks": [
                                {"type": "bold"},
                                {"type": "script"},  # Invalid
                            ],
                        }
                    ],
                }
            ],
        }
        sanitized, errors = sanitize_document(doc, config)

        # Get the text node marks
        text_node = sanitized["content"][0]["content"][0]
        mark_types = [m["type"] for m in text_node.get("marks", [])]

        assert "bold" in mark_types
        assert "script" not in mark_types
        assert any(e.code == "stripped_mark" for e in errors)

    def test_strip_disallowed_attribute(self, config: RichTextConfig) -> None:
        """Disallowed attributes are stripped."""
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "image",
                    "attrs": {
                        "src": "test.png",
                        "alt": "Test",
                        "onclick": "alert('xss')",  # Should be stripped
                    },
                }
            ],
        }
        sanitized, errors = sanitize_document(doc, config)

        img_attrs = sanitized["content"][0].get("attrs", {})
        assert "src" in img_attrs
        assert "alt" in img_attrs
        assert "onclick" not in img_attrs
        assert any(e.code == "stripped_attribute" for e in errors)

    def test_html_strip_disallowed_tag(self, config: RichTextConfig) -> None:
        """HTML sanitizer strips disallowed tags."""
        html = '<p>Hello</p><script>alert("xss")</script><p>World</p>'
        sanitized, errors = sanitize_html(html, config)

        assert "<script>" not in sanitized
        assert "</script>" not in sanitized
        assert "<p>" in sanitized
        assert any(e.code == "stripped_tag" for e in errors)

    def test_html_strip_disallowed_attr(self, config: RichTextConfig) -> None:
        """HTML sanitizer strips disallowed attributes."""
        html = '<img src="test.png" onclick="alert()">'
        sanitized, errors = sanitize_html(html, config)

        assert "onclick" not in sanitized
        assert "src=" in sanitized
        assert any(e.code == "stripped_attribute" for e in errors)


# --- TA-0022: Link Sanitization ---


class TestLinkSanitization:
    """Test TA-0022: Link sanitization (forbidden protocols, rel attrs)."""

    def test_safe_https_url(self, config: RichTextConfig) -> None:
        """HTTPS URLs are safe."""
        assert is_safe_url("https://example.com", config) is True

    def test_safe_http_url(self, config: RichTextConfig) -> None:
        """HTTP URLs are safe."""
        assert is_safe_url("http://example.com", config) is True

    def test_safe_relative_url(self, config: RichTextConfig) -> None:
        """Relative URLs are safe."""
        assert is_safe_url("/path/to/page", config) is True
        assert is_safe_url("page.html", config) is True

    def test_unsafe_javascript_url(self, config: RichTextConfig) -> None:
        """javascript: URLs are unsafe."""
        assert is_safe_url("javascript:alert('xss')", config) is False
        assert is_safe_url("JAVASCRIPT:alert()", config) is False
        assert is_safe_url("  javascript:void(0)", config) is False

    def test_unsafe_data_url(self, config: RichTextConfig) -> None:
        """data: URLs are unsafe."""
        assert is_safe_url("data:text/html,<script>", config) is False
        assert is_safe_url("DATA:text/html,test", config) is False

    def test_sanitize_url_returns_none_for_unsafe(self, config: RichTextConfig) -> None:
        """sanitize_url returns None for unsafe URLs."""
        assert sanitize_url("javascript:alert()", config) is None
        assert sanitize_url("data:text/html,test", config) is None

    def test_sanitize_url_strips_whitespace(self, config: RichTextConfig) -> None:
        """sanitize_url strips whitespace."""
        result = sanitize_url("  https://example.com  ", config)
        assert result == "https://example.com"

    def test_link_rel_attributes_added(self, config: RichTextConfig) -> None:
        """Link rel attributes are added correctly."""
        rel = build_link_rel(config)
        assert "noopener" in rel
        assert "noreferrer" in rel

    def test_link_rel_no_ugc_by_default(self, config: RichTextConfig) -> None:
        """UGC is not added by default."""
        rel = build_link_rel(config)
        assert "ugc" not in rel

    def test_link_rel_with_ugc(self) -> None:
        """UGC is added when configured."""
        config = RichTextConfig(add_ugc=True)
        rel = build_link_rel(config)
        assert "ugc" in rel

    def test_sanitize_link_in_document(self, config: RichTextConfig) -> None:
        """Links in documents get rel attributes."""
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Link",
                            "marks": [{"type": "link", "attrs": {"href": "https://example.com"}}],
                        }
                    ],
                }
            ],
        }
        sanitized, _ = sanitize_document(doc, config)

        link_mark = sanitized["content"][0]["content"][0]["marks"][0]
        assert link_mark["attrs"]["rel"] == "noopener noreferrer"

    def test_sanitize_unsafe_link_removed(self, config: RichTextConfig) -> None:
        """Links with unsafe URLs are removed."""
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Link",
                            "marks": [{"type": "link", "attrs": {"href": "javascript:alert()"}}],
                        }
                    ],
                }
            ],
        }
        sanitized, errors = sanitize_document(doc, config)

        text_node = sanitized["content"][0]["content"][0]
        marks = text_node.get("marks", [])
        assert len(marks) == 0  # Link mark should be stripped
        assert any(e.code == "unsafe_url" for e in errors)

    def test_sanitize_html_link_adds_rel(self, config: RichTextConfig) -> None:
        """HTML sanitizer adds rel to links."""
        html = '<a href="https://example.com">Link</a>'
        sanitized, _ = sanitize_html(html, config)

        assert 'rel="noopener noreferrer"' in sanitized

    def test_sanitize_html_unsafe_link_removed(self, config: RichTextConfig) -> None:
        """HTML sanitizer removes unsafe links."""
        html = '<a href="javascript:alert()">Evil</a>'
        sanitized, errors = sanitize_html(html, config)

        assert "<a" not in sanitized
        assert any(e.code == "unsafe_url" for e in errors)


# --- Size and Limit Validation ---


class TestSizeValidation:
    """Test size and limit validation."""

    def test_small_doc_passes(self, simple_doc: dict, config: RichTextConfig) -> None:
        """Small document passes size validation."""
        errors = validate_size(simple_doc, config)
        assert len(errors) == 0

    def test_large_doc_fails(self) -> None:
        """Document exceeding size limit fails."""
        config = RichTextConfig(max_json_bytes=100)
        doc = {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "x" * 200}]}],
        }
        errors = validate_size(doc, config)
        assert len(errors) > 0
        assert any(e.code == "document_too_large" for e in errors)

    def test_count_links(self) -> None:
        """Link counting works correctly."""
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Link1",
                            "marks": [{"type": "link", "attrs": {"href": "a"}}],
                        },
                        {"type": "text", "text": " "},
                        {
                            "type": "text",
                            "text": "Link2",
                            "marks": [{"type": "link", "attrs": {"href": "b"}}],
                        },
                    ],
                }
            ],
        }
        assert count_links(doc) == 2

    def test_max_links_exceeded(self) -> None:
        """Document with too many links fails validation."""
        config = RichTextConfig(max_links_per_doc=2)
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "L1",
                            "marks": [{"type": "link", "attrs": {"href": "a"}}],
                        },
                        {
                            "type": "text",
                            "text": "L2",
                            "marks": [{"type": "link", "attrs": {"href": "b"}}],
                        },
                        {
                            "type": "text",
                            "text": "L3",
                            "marks": [{"type": "link", "attrs": {"href": "c"}}],
                        },
                    ],
                }
            ],
        }
        errors = validate_rich_text(doc, config)
        assert any(e.code == "max_links_exceeded" for e in errors)


# --- Service Tests ---


class TestRichTextService:
    """Test RichTextService class."""

    def test_service_creation(self, service: RichTextService) -> None:
        """Service can be created."""
        assert service is not None
        assert service.config is not None

    def test_service_validate(self, service: RichTextService, simple_doc: dict) -> None:
        """Service.validate works."""
        errors = service.validate(simple_doc)
        assert len(errors) == 0

    def test_service_sanitize(self, service: RichTextService, doc_with_link: dict) -> None:
        """Service.sanitize works."""
        sanitized, errors = service.sanitize(doc_with_link)
        assert sanitized is not None
        assert sanitized["type"] == "doc"

    def test_service_validate_and_sanitize(
        self,
        service: RichTextService,
        simple_doc: dict,
    ) -> None:
        """Service.validate_and_sanitize works."""
        result, errors = service.validate_and_sanitize(simple_doc)
        assert result is not None

    def test_service_sanitize_html(self, service: RichTextService) -> None:
        """Service.sanitize_html works."""
        html = "<p>Hello</p><script>bad</script>"
        sanitized, errors = service.sanitize_html(html)
        assert "<script>" not in sanitized

    def test_service_is_safe_url(self, service: RichTextService) -> None:
        """Service.is_safe_url works."""
        assert service.is_safe_url("https://example.com") is True
        assert service.is_safe_url("javascript:alert()") is False

    def test_service_count_links(self, service: RichTextService, doc_with_link: dict) -> None:
        """Service.count_links works."""
        count = service.count_links(doc_with_link)
        assert count == 1


# --- Edge Cases ---


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_document(self, config: RichTextConfig) -> None:
        """Empty document is valid."""
        doc = {"type": "doc", "content": []}
        errors = validate_schema(doc, config)
        assert len(errors) == 0

    def test_empty_html(self, config: RichTextConfig) -> None:
        """Empty HTML is handled."""
        sanitized, errors = sanitize_html("", config)
        assert sanitized == ""
        assert len(errors) == 0

    def test_deeply_nested_document(self, config: RichTextConfig) -> None:
        """Deeply nested document is handled."""
        doc = {"type": "doc", "content": []}
        current = doc["content"]
        for _ in range(10):
            node = {"type": "paragraph", "content": []}
            current.append(node)
            current = node["content"]
        current.append({"type": "text", "text": "deep"})

        errors = validate_schema(doc, config)
        # Should not crash; may or may not have errors depending on nesting rules
        assert isinstance(errors, list)

    def test_text_with_multiple_marks(self, config: RichTextConfig) -> None:
        """Text with multiple marks is handled."""
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Bold italic link",
                            "marks": [
                                {"type": "bold"},
                                {"type": "italic"},
                                {"type": "link", "attrs": {"href": "https://example.com"}},
                            ],
                        }
                    ],
                }
            ],
        }
        errors = validate_schema(doc, config)
        assert len(errors) == 0

    def test_image_with_all_allowed_attrs(self, config: RichTextConfig) -> None:
        """Image with all allowed attrs is valid."""
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "image",
                    "attrs": {
                        "src": "https://example.com/img.png",
                        "alt": "Alt text",
                        "title": "Title",
                        "width": "100",
                        "height": "100",
                    },
                }
            ],
        }
        errors = validate_schema(doc, config)
        assert len(errors) == 0

    def test_heading_with_level(self, config: RichTextConfig) -> None:
        """Heading with level attribute is valid."""
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Heading"}],
                }
            ],
        }
        sanitized, errors = sanitize_document(doc, config)
        # Level should be preserved
        assert sanitized["content"][0]["attrs"]["level"] == 2


# --- Integration-like Tests ---


class TestIntegration:
    """Integration-like tests combining multiple features."""

    def test_full_document_workflow(self, service: RichTextService) -> None:
        """Full document validation and sanitization workflow."""
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 1},
                    "content": [{"type": "text", "text": "Title"}],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Normal text with "},
                        {"type": "text", "text": "bold", "marks": [{"type": "bold"}]},
                        {"type": "text", "text": " and "},
                        {
                            "type": "text",
                            "text": "link",
                            "marks": [{"type": "link", "attrs": {"href": "https://example.com"}}],
                        },
                        {"type": "text", "text": "."},
                    ],
                },
                {
                    "type": "blockquote",
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "Quote"}]}
                    ],
                },
            ],
        }

        result, errors = service.validate_and_sanitize(doc)
        assert result is not None
        # Link should have rel added
        link_text = result["content"][1]["content"][3]
        assert "rel" in link_text["marks"][0]["attrs"]

    def test_xss_prevention(self, service: RichTextService) -> None:
        """XSS attempts are blocked."""
        # Test various XSS vectors
        xss_docs = [
            # javascript: in link
            {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "click",
                                "marks": [
                                    {"type": "link", "attrs": {"href": "javascript:alert(1)"}}
                                ],
                            }
                        ],
                    }
                ],
            },
            # data: in image
            {
                "type": "doc",
                "content": [
                    {"type": "image", "attrs": {"src": "data:text/html,<script>alert(1)</script>"}}
                ],
            },
            # Script node
            {"type": "doc", "content": [{"type": "script", "content": []}]},
        ]

        for doc in xss_docs:
            result, errors = service.validate_and_sanitize(doc)
            # Should either be sanitized or have errors
            assert len(errors) > 0 or (result and "script" not in str(result))
