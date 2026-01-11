from pathlib import Path

import yaml
from pydantic import ValidationError

from src.rules.models import Rules


def load_rules(path: Path) -> Rules:
    """
    Load and validate the rules file.
    Raises FileNotFoundError if file missing.
    Raises ValidationError if schema invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Rules file not found at: {path}")

    with open(path) as f:
        content = f.read()
    
    # Robustly strip markdown code fences
    # Look for ```yaml starting block
    lines = content.splitlines()
    yaml_lines = []
    in_block = False
    found_block = False

    for line in lines:
        s_line = line.strip()
        if s_line.startswith("```yaml"):
            in_block = True
            found_block = True
            continue
        if in_block and s_line.startswith("```"):
            in_block = False
            break
        
        if in_block:
            yaml_lines.append(line)
    
    # If we found a block, use it. Otherwise assume the whole file is YAML
    # (or let yaml.safe_load fail if it's mixed content)
    if found_block:
        clean_content = "\n".join(yaml_lines)
    else:
        clean_content = content

    try:
        data = yaml.safe_load(clean_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML syntax in rules file: {e}") from e

    try:
        return Rules.model_validate(data)
    except ValidationError as e:
        # Re-raise with a clear message for the caller/logs
        raise ValueError(f"Rules validation failed:\n{e}") from e
