"""
Richtext component - Rich text parsing, validation, and sanitization.

Spec refs: E4.1, E4.2
"""

# Re-exports from _impl for backwards compatibility
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
]
