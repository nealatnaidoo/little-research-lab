"""
Richtext component - Rich text parsing, validation, and sanitization.

Spec refs: E4.1, E4.2
Test assertions: TA-0019, TA-0021, TA-0022

Provides schema validation and safe HTML transformation.

Invariants:
- I1: Only whitelisted node types allowed
- I2: Only whitelisted marks allowed
- I3: URLs sanitized and validated
- I4: No script content in output
- I5: Nested depth limited
"""

from __future__ import annotations

from ._impl import (
    DEFAULT_CONFIG,
    RichTextConfig,
    RichTextService,
    sanitize_document,
    validate_rich_text,
)
from ._impl import (
    RichTextValidationError as LegacyError,
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


def _convert_errors(
    legacy_errors: list[LegacyError],
) -> list[RichTextValidationError]:
    """Convert legacy errors to component errors."""
    return [
        RichTextValidationError(
            code=e.code,
            message=e.message,
            path=e.path,
        )
        for e in legacy_errors
    ]


def _build_config(rules: RulesPort | None) -> RichTextConfig:
    """Build rich text config from rules port."""
    if rules is None:
        return DEFAULT_CONFIG

    link_rel = rules.get_link_rel_config()
    return RichTextConfig(
        allow_tags=rules.get_allowed_tags(),
        allow_attrs=rules.get_allowed_attrs(),
        forbid_protocols=rules.get_forbidden_protocols(),
        max_links_per_doc=rules.get_max_links(),
        max_json_bytes=rules.get_max_json_bytes(),
        add_noopener=link_rel.get("noopener", True),
        add_noreferrer=link_rel.get("noreferrer", True),
        add_ugc=link_rel.get("ugc", False),
    )


# --- Component Entry Points ---


def run_validate(
    inp: ValidateRichTextInput,
    *,
    rules: RulesPort | None = None,
) -> ValidateOutput:
    """
    Validate rich text document against schema (TA-0019).

    Args:
        inp: Input containing the document to validate.
        rules: Optional rules port for configuration.

    Returns:
        ValidateOutput with validation result.
    """
    config = _build_config(rules)
    legacy_errors = validate_rich_text(inp.document, config)
    errors = _convert_errors(legacy_errors)

    return ValidateOutput(
        is_valid=len(errors) == 0,
        errors=errors,
        success=True,
    )


def run_sanitize(
    inp: SanitizeRichTextInput,
    *,
    rules: RulesPort | None = None,
) -> SanitizeOutput:
    """
    Sanitize rich text document (TA-0021).

    Removes disallowed nodes, marks, and attributes.
    Sanitizes URLs in links and images.

    Args:
        inp: Input containing the document to sanitize.
        rules: Optional rules port for configuration.

    Returns:
        SanitizeOutput with sanitized document.
    """
    config = _build_config(rules)
    sanitized_doc, legacy_errors = sanitize_document(inp.document, config)
    errors = _convert_errors(legacy_errors)

    return SanitizeOutput(
        document=sanitized_doc,
        errors=errors,
        success=True,
    )


def run_transform(
    inp: TransformRichTextInput,
    *,
    rules: RulesPort | None = None,
) -> TransformOutput:
    """
    Transform rich text document - validate and sanitize (TA-0021, TA-0022).

    Performs full validation and sanitization.

    Args:
        inp: Input containing the document to transform.
        rules: Optional rules port for configuration.

    Returns:
        TransformOutput with transformed document.
    """
    config = _build_config(rules)
    service = RichTextService(config)

    sanitized_doc, legacy_errors = service.validate_and_sanitize(inp.document)
    errors = _convert_errors(legacy_errors)

    if sanitized_doc is None:
        return TransformOutput(
            document=None,
            errors=errors,
            success=False,
        )

    return TransformOutput(
        document=sanitized_doc,
        errors=errors,
        success=True,
    )


def run(
    inp: ValidateRichTextInput | SanitizeRichTextInput | TransformRichTextInput,
    *,
    rules: RulesPort | None = None,
) -> ValidateOutput | SanitizeOutput | TransformOutput:
    """
    Main entry point for the richtext component.

    Dispatches to appropriate handler based on input type.

    Args:
        inp: Input object determining the operation.
        rules: Optional rules port for configuration.

    Returns:
        Appropriate output object based on input type.
    """
    if isinstance(inp, ValidateRichTextInput):
        return run_validate(inp, rules=rules)
    elif isinstance(inp, SanitizeRichTextInput):
        return run_sanitize(inp, rules=rules)
    elif isinstance(inp, TransformRichTextInput):
        return run_transform(inp, rules=rules)
    else:
        raise ValueError(f"Unknown input type: {type(inp)}")
