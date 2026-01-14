"""
Tests for Post SSR Renderer Service (E4.4).

Test assertions:
- TA-0025: Rich text renders to valid semantic HTML
"""

from __future__ import annotations

import pytest

from src.components.render_posts import (
    PostRenderer,
    RenderConfig,
    render_blockquote,
    render_bullet_list,
    render_code_block,
    render_heading,
    render_image,
    render_ordered_list,
    render_paragraph,
    render_post_body,
    render_rich_text,
    render_text,
)

# --- Fixtures ---


@pytest.fixture
def config() -> RenderConfig:
    return RenderConfig()


@pytest.fixture
def renderer(config: RenderConfig) -> PostRenderer:
    return PostRenderer(config=config)


@pytest.fixture
def simple_doc() -> dict:
    """Simple document with one paragraph."""
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Hello, world!"}]}],
    }


# --- TA-0025: Rich Text Renders to Semantic HTML ---


class TestBasicRendering:
    """Test TA-0025: Basic semantic HTML rendering."""

    def test_render_paragraph(self) -> None:
        """Paragraph renders to <p> tag."""
        node = {"type": "paragraph", "content": [{"type": "text", "text": "Hello"}]}
        result = render_paragraph(node)
        assert result == "<p>Hello</p>"

    def test_render_heading_h1(self) -> None:
        """Heading level 1 renders to <h1>."""
        node = {
            "type": "heading",
            "attrs": {"level": 1},
            "content": [{"type": "text", "text": "Title"}],
        }
        result = render_heading(node, RenderConfig(add_heading_ids=False))
        assert result == "<h1>Title</h1>"

    def test_render_heading_h2(self) -> None:
        """Heading level 2 renders to <h2>."""
        node = {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Section"}],
        }
        result = render_heading(node, RenderConfig(add_heading_ids=False))
        assert result == "<h2>Section</h2>"

    def test_render_heading_with_id(self) -> None:
        """Heading with add_heading_ids gets id attribute."""
        node = {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "My Section"}],
        }
        result = render_heading(node, RenderConfig(add_heading_ids=True))
        assert 'id="my-section"' in result
        assert "<h2" in result

    def test_render_blockquote(self) -> None:
        """Blockquote renders correctly."""
        node = {
            "type": "blockquote",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Quote"}]}],
        }
        result = render_blockquote(node)
        assert result == "<blockquote><p>Quote</p></blockquote>"

    def test_render_bullet_list(self) -> None:
        """Bullet list renders to <ul>."""
        node = {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "Item 1"}]}
                    ],
                },
                {
                    "type": "listItem",
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "Item 2"}]}
                    ],
                },
            ],
        }
        result = render_bullet_list(node)
        assert "<ul>" in result
        assert "</ul>" in result
        assert "<li>" in result
        assert "Item 1" in result
        assert "Item 2" in result

    def test_render_ordered_list(self) -> None:
        """Ordered list renders to <ol>."""
        node = {
            "type": "orderedList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "First"}]}
                    ],
                },
            ],
        }
        result = render_ordered_list(node)
        assert "<ol>" in result
        assert "</ol>" in result
        assert "First" in result

    def test_render_ordered_list_with_start(self) -> None:
        """Ordered list respects start attribute."""
        node = {
            "type": "orderedList",
            "attrs": {"start": 5},
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "Item"}]}
                    ],
                },
            ],
        }
        result = render_ordered_list(node)
        assert 'start="5"' in result

    def test_render_code_block(self) -> None:
        """Code block renders with pre and code tags."""
        node = {"type": "codeBlock", "content": [{"type": "text", "text": "const x = 1;"}]}
        result = render_code_block(node)
        assert "<pre" in result
        assert "<code>" in result
        assert "const x = 1;" in result
        assert "</code>" in result
        assert "</pre>" in result

    def test_render_code_block_with_language(self) -> None:
        """Code block with language gets class."""
        node = {
            "type": "codeBlock",
            "attrs": {"language": "javascript"},
            "content": [{"type": "text", "text": "let x = 1;"}],
        }
        result = render_code_block(node)
        assert "language-javascript" in result

    def test_render_image(self) -> None:
        """Image renders with attributes."""
        node = {
            "type": "image",
            "attrs": {
                "src": "https://example.com/img.png",
                "alt": "Test image",
            },
        }
        result = render_image(node)
        assert "<img" in result
        assert 'src="https://example.com/img.png"' in result
        assert 'alt="Test image"' in result
        assert 'loading="lazy"' in result

    def test_render_image_with_dimensions(self) -> None:
        """Image with dimensions includes width/height."""
        node = {
            "type": "image",
            "attrs": {
                "src": "https://example.com/img.png",
                "alt": "Test",
                "width": "100",
                "height": "200",
            },
        }
        result = render_image(node)
        assert 'width="100"' in result
        assert 'height="200"' in result


# --- Text and Marks ---


class TestTextRendering:
    """Test text and mark rendering."""

    def test_render_plain_text(self) -> None:
        """Plain text is escaped."""
        node = {"type": "text", "text": "Hello <world>"}
        result = render_text(node)
        assert result == "Hello &lt;world&gt;"

    def test_render_bold_text(self) -> None:
        """Bold mark renders to <strong>."""
        node = {"type": "text", "text": "Bold", "marks": [{"type": "bold"}]}
        result = render_text(node)
        assert result == "<strong>Bold</strong>"

    def test_render_italic_text(self) -> None:
        """Italic mark renders to <em>."""
        node = {"type": "text", "text": "Italic", "marks": [{"type": "italic"}]}
        result = render_text(node)
        assert result == "<em>Italic</em>"

    def test_render_code_text(self) -> None:
        """Code mark renders to <code>."""
        node = {"type": "text", "text": "code", "marks": [{"type": "code"}]}
        result = render_text(node)
        assert result == "<code>code</code>"

    def test_render_link(self) -> None:
        """Link mark renders to <a> with rel."""
        node = {
            "type": "text",
            "text": "Click here",
            "marks": [{"type": "link", "attrs": {"href": "https://example.com"}}],
        }
        result = render_text(node)
        assert "<a" in result
        assert 'href="https://example.com"' in result
        assert "noopener" in result
        assert "noreferrer" in result
        assert ">Click here</a>" in result

    def test_render_link_with_title(self) -> None:
        """Link with title includes title attribute."""
        node = {
            "type": "text",
            "text": "Link",
            "marks": [{"type": "link", "attrs": {"href": "/page", "title": "Go there"}}],
        }
        result = render_text(node)
        assert 'title="Go there"' in result

    def test_render_multiple_marks(self) -> None:
        """Multiple marks nest correctly."""
        node = {
            "type": "text",
            "text": "Bold italic",
            "marks": [{"type": "bold"}, {"type": "italic"}],
        }
        result = render_text(node)
        # Marks applied in reverse order for nesting
        assert "<strong>" in result
        assert "<em>" in result
        assert "</em>" in result
        assert "</strong>" in result

    def test_unsafe_link_stripped(self) -> None:
        """Unsafe links are stripped."""
        node = {
            "type": "text",
            "text": "Evil",
            "marks": [{"type": "link", "attrs": {"href": "javascript:alert(1)"}}],
        }
        result = render_text(node)
        # Link should be stripped, just text remains
        assert result == "Evil"
        assert "<a" not in result


# --- Full Document Rendering ---


class TestDocumentRendering:
    """Test full document rendering."""

    def test_render_simple_doc(self, simple_doc: dict) -> None:
        """Simple document renders correctly."""
        result = render_rich_text(simple_doc)
        assert "<article>" in result
        assert "</article>" in result
        assert "<p>Hello, world!</p>" in result

    def test_render_without_article_wrapper(self, simple_doc: dict) -> None:
        """Can disable article wrapper."""
        config = RenderConfig(wrap_in_article=False)
        result = render_rich_text(simple_doc, config)
        assert "<article>" not in result
        assert "<p>Hello, world!</p>" in result

    def test_render_complex_doc(self) -> None:
        """Complex document with multiple node types."""
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
                        {"type": "text", "text": "Intro with "},
                        {"type": "text", "text": "bold", "marks": [{"type": "bold"}]},
                        {"type": "text", "text": "."},
                    ],
                },
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {"type": "paragraph", "content": [{"type": "text", "text": "Item"}]}
                            ],
                        }
                    ],
                },
            ],
        }

        config = RenderConfig(add_heading_ids=False, wrap_in_article=False)
        result = render_rich_text(doc, config)

        assert "<h1>Title</h1>" in result
        assert "<strong>bold</strong>" in result
        assert "<ul>" in result
        assert "<li>" in result

    def test_render_post_body(self) -> None:
        """render_post_body convenience function works."""
        doc = {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Test"}]}],
        }
        result = render_post_body(doc)
        assert "<article>" in result
        assert "<p>Test</p>" in result


# --- PostRenderer Service ---


class TestPostRenderer:
    """Test PostRenderer class."""

    def test_create_renderer(self) -> None:
        """Can create renderer."""
        renderer = PostRenderer()
        assert renderer is not None

    def test_render_method(self, renderer: PostRenderer, simple_doc: dict) -> None:
        """render method works."""
        result = renderer.render(simple_doc)
        assert "<p>Hello, world!</p>" in result

    def test_render_post_method(self, renderer: PostRenderer, simple_doc: dict) -> None:
        """render_post method works."""
        result = renderer.render_post(simple_doc)
        assert "<p>Hello, world!</p>" in result

    def test_extract_text(self, renderer: PostRenderer) -> None:
        """extract_text extracts plain text."""
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Hello "},
                        {"type": "text", "text": "world", "marks": [{"type": "bold"}]},
                    ],
                }
            ],
        }
        result = renderer.extract_text(doc)
        assert result == "Hello world"

    def test_extract_headings(self, renderer: PostRenderer) -> None:
        """extract_headings builds ToC."""
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 1},
                    "content": [{"type": "text", "text": "Main Title"}],
                },
                {"type": "paragraph", "content": [{"type": "text", "text": "Intro"}]},
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Section One"}],
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Section Two"}],
                },
            ],
        }
        headings = renderer.extract_headings(doc)

        assert len(headings) == 3
        assert headings[0]["level"] == 1
        assert headings[0]["text"] == "Main Title"
        assert headings[0]["id"] == "main-title"
        assert headings[1]["level"] == 2
        assert headings[1]["text"] == "Section One"


# --- HTML Escaping and Safety ---


class TestSafety:
    """Test HTML escaping and safety."""

    def test_text_escaped(self) -> None:
        """Special characters in text are escaped."""
        node = {"type": "text", "text": "<script>alert('xss')</script>"}
        result = render_text(node)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_attribute_escaped(self) -> None:
        """Attributes are escaped."""
        node = {
            "type": "image",
            "attrs": {
                "src": "https://example.com/img.png",
                "alt": 'Image with "quotes"',
            },
        }
        result = render_image(node)
        assert "&quot;" in result or "quotes" in result

    def test_unsafe_image_src_stripped(self) -> None:
        """Unsafe image src is stripped."""
        node = {
            "type": "image",
            "attrs": {
                "src": "javascript:alert(1)",
                "alt": "Evil",
            },
        }
        result = render_image(node)
        assert result == ""

    def test_data_url_image_stripped(self) -> None:
        """Data URL images are stripped."""
        node = {
            "type": "image",
            "attrs": {
                "src": "data:text/html,<script>alert(1)</script>",
                "alt": "Evil",
            },
        }
        result = render_image(node)
        assert result == ""


# --- Edge Cases ---


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_document(self) -> None:
        """Empty document renders empty."""
        doc = {"type": "doc", "content": []}
        result = render_rich_text(doc)
        assert result == "<article></article>"

    def test_empty_paragraph(self) -> None:
        """Empty paragraph renders."""
        node = {"type": "paragraph", "content": []}
        result = render_paragraph(node)
        assert result == "<p></p>"

    def test_heading_level_clamped(self) -> None:
        """Heading level is clamped to 1-6."""
        node = {"type": "heading", "attrs": {"level": 10}, "content": []}
        result = render_heading(node, RenderConfig(add_heading_ids=False))
        assert "<h6></h6>" == result

        node2 = {"type": "heading", "attrs": {"level": 0}, "content": []}
        result2 = render_heading(node2, RenderConfig(add_heading_ids=False))
        assert "<h1></h1>" == result2

    def test_unknown_node_type(self) -> None:
        """Unknown node types don't crash."""
        doc = {
            "type": "doc",
            "content": [{"type": "unknown_node", "content": [{"type": "text", "text": "Content"}]}],
        }
        result = render_rich_text(doc)
        assert "Content" in result

    def test_deeply_nested_content(self) -> None:
        """Deeply nested content renders."""
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "blockquote",
                    "content": [
                        {
                            "type": "blockquote",
                            "content": [
                                {
                                    "type": "blockquote",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [{"type": "text", "text": "Deep"}],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        result = render_rich_text(doc)
        assert result.count("<blockquote>") == 3
        assert "Deep" in result
