"""
Richtext component - Rich text parsing, validation, and sanitization.

Spec refs: E4.1, E4.2
"""

# Re-exports from _impl for backwards compatibility
# Re-exports from legacy richtext service (pending full migration)
from src.core.services.richtext import (
    RichTextNode,
    count_links,
    create_rich_text_service,
    parse_attributes,
    sanitize_document,
    sanitize_html,
    sanitize_url,
    validate_link_count,
    validate_mark_attrs,
    validate_mark_type,
    validate_node_attrs,
    validate_node_type,
    validate_rich_text,
    validate_schema,
    validate_size,
)

from ._impl import (
    RichTextConfig,
    RichTextService,
    build_link_rel,
    is_safe_url,
)
from .component import (
    run,
    run_sanitize,
    run_transform,
    run_validate,
)
from .models import (
    RichTextValidationError,
    SanitizeOutput,
    SanitizeRichTextInput,
    TransformOutput,
    TransformRichTextInput,
    ValidateOutput,
    ValidateRichTextInput,
)
from .ports import RulesPort

__all__ = [
    # Entry points
    "run",
    "run_sanitize",
    "run_transform",
    "run_validate",
    # Input models
    "SanitizeRichTextInput",
    "TransformRichTextInput",
    "ValidateRichTextInput",
    # Output models
    "SanitizeOutput",
    "TransformOutput",
    "ValidateOutput",
    "RichTextValidationError",
    # Ports
    "RulesPort",
    # Legacy _impl re-exports
    "RichTextConfig",
    "RichTextService",
    "build_link_rel",
    "is_safe_url",
    # Legacy service re-exports
    "RichTextNode",
    "count_links",
    "create_rich_text_service",
    "parse_attributes",
    "sanitize_document",
    "sanitize_html",
    "sanitize_url",
    "validate_link_count",
    "validate_mark_attrs",
    "validate_mark_type",
    "validate_node_attrs",
    "validate_node_type",
    "validate_rich_text",
    "validate_schema",
    "validate_size",
]
