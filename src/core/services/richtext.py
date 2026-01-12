"""
RichText Service (E4.1, E4.2) - Rich text schema and sanitizer.

Handles rich text validation, sanitization, and transformation.

Spec refs: E4.1, E4.2, TA-0019, TA-0021, TA-0022
Test assertions:
- TA-0019: Schema validation (allowed nodes/attrs)
- TA-0021: Sanitizer strips disallowed tags/attrs
- TA-0022: Link sanitization (forbidden protocols, rel attrs)

Key behaviors:
- Validates rich text JSON against allowed schema
- Sanitizes HTML content, stripping dangerous elements
- Adds security attributes to links (noopener, noreferrer)
- Blocks forbidden protocols (javascript:, data:)
- Enforces limits (max links, max JSON size)
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from typing import Any

# --- Configuration ---


@dataclass(frozen=True)
class RichTextConfig:
    """Rich text configuration from rules."""

    # Allowed HTML tags
    allow_tags: frozenset[str] = field(
        default_factory=lambda: frozenset(
            [
                "p",
                "h1",
                "h2",
                "h3",
                "blockquote",
                "ul",
                "ol",
                "li",
                "strong",
                "em",
                "code",
                "pre",
                "a",
                "img",
            ]
        )
    )

    # Allowed attributes per tag
    allow_attrs: dict[str, frozenset[str]] = field(
        default_factory=lambda: {
            "a": frozenset(["href", "title"]),
            "img": frozenset(["src", "alt", "title", "width", "height"]),
        }
    )

    # Link rel attributes to add
    add_noopener: bool = True
    add_noreferrer: bool = True
    add_ugc: bool = False

    # Forbidden protocols in URLs
    forbid_protocols: frozenset[str] = field(
        default_factory=lambda: frozenset(
            [
                "javascript:",
                "data:",
            ]
        )
    )

    # Limits
    max_links_per_doc: int = 500
    max_json_bytes: int = 400_000


# Default configuration
DEFAULT_CONFIG = RichTextConfig()


# --- Validation Errors ---


@dataclass
class RichTextValidationError:
    """Rich text validation error."""

    code: str
    message: str
    path: str | None = None


# --- Rich Text Node Schema ---


@dataclass
class RichTextNode:
    """
    A node in the rich text document tree.

    Represents a ProseMirror-style document node.
    """

    type: str
    attrs: dict[str, Any] = field(default_factory=dict)
    content: list[RichTextNode] = field(default_factory=list)
    text: str | None = None
    marks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"type": self.type}
        if self.attrs:
            result["attrs"] = self.attrs
        if self.content:
            result["content"] = [node.to_dict() for node in self.content]
        if self.text is not None:
            result["text"] = self.text
        if self.marks:
            result["marks"] = self.marks
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RichTextNode:
        """Create from dictionary."""
        content = [cls.from_dict(child) for child in data.get("content", [])]
        return cls(
            type=data.get("type", ""),
            attrs=data.get("attrs", {}),
            content=content,
            text=data.get("text"),
            marks=data.get("marks", []),
        )


# --- Schema Validation (TA-0019) ---

# Map node types to allowed HTML tags
NODE_TYPE_TO_TAG: dict[str, str] = {
    "doc": "doc",  # Root node, not an HTML tag
    "paragraph": "p",
    "heading": "h1",  # Actual level from attrs
    "blockquote": "blockquote",
    "bulletList": "ul",
    "orderedList": "ol",
    "listItem": "li",
    "codeBlock": "pre",
    "image": "img",
    "hardBreak": "br",
    "text": "text",  # Text node, not an HTML tag
}

# Mark types to HTML tags
MARK_TYPE_TO_TAG: dict[str, str] = {
    "bold": "strong",
    "strong": "strong",
    "italic": "em",
    "em": "em",
    "code": "code",
    "link": "a",
}


def validate_node_type(
    node_type: str,
    config: RichTextConfig = DEFAULT_CONFIG,
) -> bool:
    """Check if node type is allowed."""
    if node_type in ("doc", "text", "hardBreak"):
        return True

    tag = NODE_TYPE_TO_TAG.get(node_type)
    if tag and tag in config.allow_tags:
        return True

    # Check heading levels
    if node_type == "heading":
        return any(f"h{i}" in config.allow_tags for i in range(1, 7))

    return False


def validate_mark_type(
    mark_type: str,
    config: RichTextConfig = DEFAULT_CONFIG,
) -> bool:
    """Check if mark type is allowed."""
    tag = MARK_TYPE_TO_TAG.get(mark_type)
    return tag is not None and tag in config.allow_tags


def validate_node_attrs(
    node_type: str,
    attrs: dict[str, Any],
    config: RichTextConfig = DEFAULT_CONFIG,
) -> list[str]:
    """
    Validate node attributes.

    Returns list of disallowed attribute names.
    """
    tag = NODE_TYPE_TO_TAG.get(node_type)
    if not tag:
        return []

    allowed = config.allow_attrs.get(tag, frozenset())
    disallowed = [key for key in attrs if key not in allowed]
    return disallowed


def validate_mark_attrs(
    mark_type: str,
    attrs: dict[str, Any],
    config: RichTextConfig = DEFAULT_CONFIG,
) -> list[str]:
    """
    Validate mark attributes.

    Returns list of disallowed attribute names.
    """
    tag = MARK_TYPE_TO_TAG.get(mark_type)
    if not tag:
        return []

    allowed = config.allow_attrs.get(tag, frozenset())
    disallowed = [key for key in attrs if key not in allowed]
    return disallowed


def validate_schema(
    doc: dict[str, Any],
    config: RichTextConfig = DEFAULT_CONFIG,
) -> list[RichTextValidationError]:
    """
    Validate document against schema (TA-0019).

    Checks:
    - All node types are allowed
    - All mark types are allowed
    - All attributes are allowed for their tags
    """
    errors: list[RichTextValidationError] = []

    def validate_node(node: dict[str, Any], path: str) -> None:
        node_type = node.get("type", "")

        # Check node type
        if not validate_node_type(node_type, config):
            errors.append(
                RichTextValidationError(
                    code="invalid_node_type",
                    message=f"Node type '{node_type}' is not allowed",
                    path=path,
                )
            )

        # Check node attributes
        attrs = node.get("attrs", {})
        disallowed = validate_node_attrs(node_type, attrs, config)
        for attr in disallowed:
            errors.append(
                RichTextValidationError(
                    code="invalid_attribute",
                    message=f"Attribute '{attr}' not allowed on '{node_type}'",
                    path=f"{path}.attrs.{attr}",
                )
            )

        # Check marks on text nodes
        for i, mark in enumerate(node.get("marks", [])):
            mark_type = mark.get("type", "")
            mark_path = f"{path}.marks[{i}]"

            if not validate_mark_type(mark_type, config):
                errors.append(
                    RichTextValidationError(
                        code="invalid_mark_type",
                        message=f"Mark type '{mark_type}' is not allowed",
                        path=mark_path,
                    )
                )

            mark_attrs = mark.get("attrs", {})
            disallowed_marks = validate_mark_attrs(mark_type, mark_attrs, config)
            for attr in disallowed_marks:
                errors.append(
                    RichTextValidationError(
                        code="invalid_attribute",
                        message=f"Attribute '{attr}' not allowed on mark '{mark_type}'",
                        path=f"{mark_path}.attrs.{attr}",
                    )
                )

        # Recurse into content
        for i, child in enumerate(node.get("content", [])):
            validate_node(child, f"{path}.content[{i}]")

    validate_node(doc, "doc")
    return errors


# --- Link Sanitization (TA-0022) ---


def is_safe_url(url: str, config: RichTextConfig = DEFAULT_CONFIG) -> bool:
    """
    Check if URL is safe (no forbidden protocols).

    Returns True if URL is safe, False if it uses a forbidden protocol.
    """
    if not url:
        return True

    url_lower = url.lower().strip()

    # Check for forbidden protocols
    for protocol in config.forbid_protocols:
        if url_lower.startswith(protocol):
            return False

    return True


def sanitize_url(url: str, config: RichTextConfig = DEFAULT_CONFIG) -> str | None:
    """
    Sanitize URL, returning None if unsafe.

    Returns sanitized URL or None if forbidden protocol detected.
    """
    if not is_safe_url(url, config):
        return None

    # Basic URL normalization
    return url.strip()


def build_link_rel(config: RichTextConfig = DEFAULT_CONFIG) -> str:
    """Build rel attribute value for links."""
    parts = []
    if config.add_noopener:
        parts.append("noopener")
    if config.add_noreferrer:
        parts.append("noreferrer")
    if config.add_ugc:
        parts.append("ugc")
    return " ".join(parts)


# --- HTML Sanitizer (TA-0021) ---

# Regex patterns for HTML parsing
TAG_PATTERN = re.compile(r"<(/?)(\w+)([^>]*)>", re.IGNORECASE)
ATTR_PATTERN = re.compile(r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|(\S+))', re.IGNORECASE)


def parse_attributes(attr_string: str) -> dict[str, str]:
    """Parse HTML attributes from a string."""
    attrs = {}
    for match in ATTR_PATTERN.finditer(attr_string):
        name = match.group(1).lower()
        value = match.group(2) or match.group(3) or match.group(4) or ""
        attrs[name] = value
    return attrs


def sanitize_html(
    html_content: str,
    config: RichTextConfig = DEFAULT_CONFIG,
) -> tuple[str, list[RichTextValidationError]]:
    """
    Sanitize HTML content (TA-0021).

    Strips disallowed tags and attributes.
    Adds security attributes to links.
    Blocks forbidden protocols.

    Returns:
        Tuple of (sanitized_html, list of errors/warnings)
    """
    errors: list[RichTextValidationError] = []
    link_count = 0

    def process_tag(match: re.Match[str]) -> str:
        nonlocal link_count

        is_closing = bool(match.group(1))
        tag_name = match.group(2).lower()
        attr_string = match.group(3)

        # Check if tag is allowed
        if tag_name not in config.allow_tags:
            errors.append(
                RichTextValidationError(
                    code="stripped_tag",
                    message=f"Tag '{tag_name}' was stripped",
                )
            )
            return ""

        if is_closing:
            return f"</{tag_name}>"

        # Parse and filter attributes
        attrs = parse_attributes(attr_string)
        allowed_attrs = config.allow_attrs.get(tag_name, frozenset())

        filtered_attrs: dict[str, str] = {}
        for name, value in attrs.items():
            if name in allowed_attrs:
                filtered_attrs[name] = value
            else:
                errors.append(
                    RichTextValidationError(
                        code="stripped_attribute",
                        message=f"Attribute '{name}' stripped from '{tag_name}'",
                    )
                )

        # Special handling for links
        if tag_name == "a":
            link_count += 1

            # Check link limit
            if link_count > config.max_links_per_doc:
                errors.append(
                    RichTextValidationError(
                        code="max_links_exceeded",
                        message=f"Maximum {config.max_links_per_doc} links allowed",
                    )
                )
                return ""

            # Sanitize href
            href = filtered_attrs.get("href", "")
            sanitized_href = sanitize_url(href, config)
            if sanitized_href is None:
                errors.append(
                    RichTextValidationError(
                        code="unsafe_url",
                        message=f"Unsafe URL protocol in href: {href[:50]}",
                    )
                )
                return ""
            filtered_attrs["href"] = sanitized_href

            # Add rel attributes
            rel = build_link_rel(config)
            if rel:
                filtered_attrs["rel"] = rel

        # Special handling for images
        if tag_name == "img":
            src = filtered_attrs.get("src", "")
            sanitized_src = sanitize_url(src, config)
            if sanitized_src is None:
                errors.append(
                    RichTextValidationError(
                        code="unsafe_url",
                        message=f"Unsafe URL protocol in src: {src[:50]}",
                    )
                )
                return ""
            filtered_attrs["src"] = sanitized_src

        # Rebuild tag
        if filtered_attrs:
            attr_parts = [
                f'{name}="{html.escape(value)}"' for name, value in filtered_attrs.items()
            ]
            return f"<{tag_name} {' '.join(attr_parts)}>"
        return f"<{tag_name}>"

    sanitized = TAG_PATTERN.sub(process_tag, html_content)
    return sanitized, errors


# --- Document Sanitization ---


def sanitize_document(
    doc: dict[str, Any],
    config: RichTextConfig = DEFAULT_CONFIG,
) -> tuple[dict[str, Any], list[RichTextValidationError]]:
    """
    Sanitize a rich text document.

    Removes disallowed nodes, marks, and attributes.
    Sanitizes URLs in links and images.

    Returns:
        Tuple of (sanitized_doc, list of errors)
    """
    errors: list[RichTextValidationError] = []
    link_count = 0

    def sanitize_node(node: dict[str, Any], path: str) -> dict[str, Any] | None:
        nonlocal link_count

        node_type = node.get("type", "")

        # Check node type
        if not validate_node_type(node_type, config):
            errors.append(
                RichTextValidationError(
                    code="stripped_node",
                    message=f"Node type '{node_type}' was stripped",
                    path=path,
                )
            )
            return None

        result: dict[str, Any] = {"type": node_type}

        # Copy and filter attributes
        attrs = node.get("attrs", {})
        if attrs:
            tag = NODE_TYPE_TO_TAG.get(node_type)
            allowed = config.allow_attrs.get(tag, frozenset()) if tag else frozenset()

            filtered_attrs = {}
            for key, value in attrs.items():
                if key in allowed or key == "level":  # Allow level for headings
                    filtered_attrs[key] = value
                else:
                    errors.append(
                        RichTextValidationError(
                            code="stripped_attribute",
                            message=f"Attribute '{key}' stripped from '{node_type}'",
                            path=f"{path}.attrs.{key}",
                        )
                    )

            # Sanitize URLs in images
            if node_type == "image" and "src" in filtered_attrs:
                src = filtered_attrs["src"]
                sanitized = sanitize_url(src, config)
                if sanitized is None:
                    errors.append(
                        RichTextValidationError(
                            code="unsafe_url",
                            message="Unsafe URL in image src",
                            path=f"{path}.attrs.src",
                        )
                    )
                    return None
                filtered_attrs["src"] = sanitized

            if filtered_attrs:
                result["attrs"] = filtered_attrs

        # Copy text
        if node.get("text") is not None:
            result["text"] = node["text"]

        # Sanitize marks
        marks = node.get("marks", [])
        if marks:
            sanitized_marks = []
            for i, mark in enumerate(marks):
                mark_type = mark.get("type", "")
                mark_path = f"{path}.marks[{i}]"

                if not validate_mark_type(mark_type, config):
                    errors.append(
                        RichTextValidationError(
                            code="stripped_mark",
                            message=f"Mark type '{mark_type}' was stripped",
                            path=mark_path,
                        )
                    )
                    continue

                sanitized_mark: dict[str, Any] = {"type": mark_type}

                # Handle link marks specially
                if mark_type == "link":
                    link_count += 1
                    if link_count > config.max_links_per_doc:
                        errors.append(
                            RichTextValidationError(
                                code="max_links_exceeded",
                                message=f"Maximum {config.max_links_per_doc} links exceeded",
                                path=mark_path,
                            )
                        )
                        continue

                    mark_attrs = mark.get("attrs", {})
                    href = mark_attrs.get("href", "")
                    sanitized_href = sanitize_url(href, config)
                    if sanitized_href is None:
                        errors.append(
                            RichTextValidationError(
                                code="unsafe_url",
                                message="Unsafe URL in link href",
                                path=f"{mark_path}.attrs.href",
                            )
                        )
                        continue

                    # Build sanitized attrs with rel
                    new_attrs: dict[str, str] = {"href": sanitized_href}
                    if "title" in mark_attrs:
                        new_attrs["title"] = mark_attrs["title"]
                    rel = build_link_rel(config)
                    if rel:
                        new_attrs["rel"] = rel
                    sanitized_mark["attrs"] = new_attrs
                else:
                    # Copy other mark attrs
                    mark_attrs = mark.get("attrs", {})
                    if mark_attrs:
                        tag = MARK_TYPE_TO_TAG.get(mark_type)
                        allowed = config.allow_attrs.get(tag, frozenset()) if tag else frozenset()
                        filtered = {k: v for k, v in mark_attrs.items() if k in allowed}
                        if filtered:
                            sanitized_mark["attrs"] = filtered

                sanitized_marks.append(sanitized_mark)

            if sanitized_marks:
                result["marks"] = sanitized_marks

        # Recurse into content
        content = node.get("content", [])
        if content:
            sanitized_content = []
            for i, child in enumerate(content):
                sanitized_child = sanitize_node(child, f"{path}.content[{i}]")
                if sanitized_child:
                    sanitized_content.append(sanitized_child)
            if sanitized_content:
                result["content"] = sanitized_content

        return result

    sanitized = sanitize_node(doc, "doc")
    return sanitized or {"type": "doc", "content": []}, errors


# --- Size Validation ---


def validate_size(
    doc: dict[str, Any],
    config: RichTextConfig = DEFAULT_CONFIG,
) -> list[RichTextValidationError]:
    """Validate document size."""
    errors: list[RichTextValidationError] = []

    try:
        json_bytes = len(json.dumps(doc).encode("utf-8"))
        if json_bytes > config.max_json_bytes:
            errors.append(
                RichTextValidationError(
                    code="document_too_large",
                    message=f"Document {json_bytes}B exceeds limit {config.max_json_bytes}B",
                )
            )
    except (TypeError, ValueError) as e:
        errors.append(
            RichTextValidationError(
                code="invalid_json",
                message=f"Cannot serialize document: {e}",
            )
        )

    return errors


# --- Link Counting ---


def count_links(doc: dict[str, Any]) -> int:
    """Count links in document."""
    count = 0

    def count_node(node: dict[str, Any]) -> None:
        nonlocal count

        # Count link marks
        for mark in node.get("marks", []):
            if mark.get("type") == "link":
                count += 1

        # Recurse
        for child in node.get("content", []):
            count_node(child)

    count_node(doc)
    return count


def validate_link_count(
    doc: dict[str, Any],
    config: RichTextConfig = DEFAULT_CONFIG,
) -> list[RichTextValidationError]:
    """Validate link count."""
    errors: list[RichTextValidationError] = []

    link_count = count_links(doc)
    if link_count > config.max_links_per_doc:
        errors.append(
            RichTextValidationError(
                code="max_links_exceeded",
                message=f"Document has {link_count} links, max is {config.max_links_per_doc}",
            )
        )

    return errors


# --- Main Validation Entry Point ---


def validate_rich_text(
    doc: dict[str, Any],
    config: RichTextConfig = DEFAULT_CONFIG,
) -> list[RichTextValidationError]:
    """
    Validate rich text document.

    Performs all validations:
    - Schema validation (TA-0019)
    - Size validation
    - Link count validation
    """
    errors: list[RichTextValidationError] = []

    # Size validation
    errors.extend(validate_size(doc, config))

    # Schema validation
    errors.extend(validate_schema(doc, config))

    # Link count validation
    errors.extend(validate_link_count(doc, config))

    return errors


# --- Service Class ---


class RichTextService:
    """
    Rich text service (E4.1, E4.2).

    Provides validation and sanitization for rich text content.
    """

    def __init__(self, config: RichTextConfig | None = None) -> None:
        """Initialize with optional configuration."""
        self._config = config or DEFAULT_CONFIG

    @property
    def config(self) -> RichTextConfig:
        """Get configuration."""
        return self._config

    def validate(self, doc: dict[str, Any]) -> list[RichTextValidationError]:
        """Validate document against schema and limits."""
        return validate_rich_text(doc, self._config)

    def sanitize(
        self,
        doc: dict[str, Any],
    ) -> tuple[dict[str, Any], list[RichTextValidationError]]:
        """Sanitize document, removing disallowed content."""
        return sanitize_document(doc, self._config)

    def validate_and_sanitize(
        self,
        doc: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, list[RichTextValidationError]]:
        """
        Validate and sanitize document.

        Returns sanitized document if valid, None if critical errors.
        """
        # First check size
        size_errors = validate_size(doc, self._config)
        if any(e.code == "document_too_large" for e in size_errors):
            return None, size_errors

        # Sanitize (this also validates)
        sanitized, errors = self.sanitize(doc)

        # Check for critical errors after sanitization
        final_errors = validate_rich_text(sanitized, self._config)

        all_errors = errors + [e for e in final_errors if e not in errors]

        # If there are critical errors, return None
        critical_codes = {"document_too_large", "invalid_json"}
        if any(e.code in critical_codes for e in all_errors):
            return None, all_errors

        return sanitized, all_errors

    def sanitize_html(
        self,
        html_content: str,
    ) -> tuple[str, list[RichTextValidationError]]:
        """Sanitize raw HTML content."""
        return sanitize_html(html_content, self._config)

    def is_safe_url(self, url: str) -> bool:
        """Check if URL is safe."""
        return is_safe_url(url, self._config)

    def count_links(self, doc: dict[str, Any]) -> int:
        """Count links in document."""
        return count_links(doc)


# --- Factory ---


def create_rich_text_service(
    config: RichTextConfig | None = None,
) -> RichTextService:
    """Create a RichTextService with optional configuration."""
    return RichTextService(config=config)
