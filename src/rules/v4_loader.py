"""
V4 Rules Loader - Load and validate creator-publisher-v4 rules.

This module implements fail-fast validation for v4 rules files.
All required sections specified in meta.required_sections must be present.

Spec refs: Rules-first, R1
Test assertions: TA-E2.3-01
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class V4RulesValidationError(ValueError):
    """
    Raised when v4 rules validation fails.

    Includes list of missing sections for fail-fast behavior.
    """

    def __init__(self, missing_sections: list[str], message: str | None = None) -> None:
        self.missing_sections = missing_sections
        if message is None:
            message = f"Rules validation failed: missing required sections: {missing_sections}"
        super().__init__(message)


def load_v4_rules(
    path: Path,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Load and optionally validate v4 rules file.

    Args:
        path: Path to the rules YAML file.
        validate: If True, validate required sections (fail-fast). Default True.

    Returns:
        Parsed rules dictionary.

    Raises:
        FileNotFoundError: If rules file doesn't exist.
        ValueError: If YAML is invalid.
        V4RulesValidationError: If validation fails (missing sections).
    """
    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {path}")

    content = path.read_text()

    # Handle markdown-wrapped YAML files
    clean_content = _strip_markdown_fences(content)

    try:
        rules: dict[str, Any] = yaml.safe_load(clean_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML syntax: {e}") from e

    if rules is None:
        raise ValueError("Rules file is empty")

    if validate:
        validate_required_sections(rules)

    return rules


def validate_required_sections(rules: dict[str, Any]) -> None:
    """
    Validate that all required sections are present in rules.

    Implements fail-fast behavior: raises immediately if any section is missing.

    Args:
        rules: Parsed rules dictionary.

    Raises:
        V4RulesValidationError: If meta section missing or required sections missing.
    """
    # Check for meta section
    if "meta" not in rules:
        raise V4RulesValidationError(
            ["meta"],
            "Rules validation failed: missing 'meta' section",
        )

    meta = rules["meta"]

    # Check for required_sections key
    if "required_sections" not in meta:
        raise V4RulesValidationError(
            ["required_sections"],
            "Rules validation failed: missing 'required_sections' in meta",
        )

    required_sections = meta["required_sections"]

    # Find missing sections
    missing = [section for section in required_sections if section not in rules]

    if missing:
        raise V4RulesValidationError(missing)


def _strip_markdown_fences(content: str) -> str:
    """
    Strip markdown code fences from YAML content.

    Handles files like:
        ## title
        ```yaml
        key: value
        ```

    Returns the YAML content without fences.
    """
    lines = content.splitlines()
    yaml_lines = []
    in_block = False
    found_block = False

    for line in lines:
        stripped = line.strip()

        # Start of YAML block
        if stripped.startswith("```yaml"):
            in_block = True
            found_block = True
            continue

        # End of code block
        if in_block and stripped.startswith("```"):
            in_block = False
            break

        # Collect lines inside the block
        if in_block:
            yaml_lines.append(line)

    # If we found a fenced block, use it. Otherwise use the whole content.
    if found_block:
        return "\n".join(yaml_lines)
    return content


def get_v4_rules_path() -> Path:
    """
    Get the default path to the v4 rules file.

    Returns:
        Path to creator-publisher-v4_rules.yaml in project root.
    """
    # Walk up from this file to find project root
    current = Path(__file__).parent
    while current != current.parent:
        rules_path = current / "creator-publisher-v4_rules.yaml"
        if rules_path.exists():
            return rules_path
        current = current.parent

    # Fallback to relative path from src/rules
    return Path(__file__).parent.parent.parent / "creator-publisher-v4_rules.yaml"
