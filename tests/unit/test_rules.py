from pathlib import Path

import pytest
import yaml

from src.rules.loader import load_rules
from src.rules.models import Rules

PROJ_ROOT = Path(__file__).parent.parent.parent
RULES_PATH = PROJ_ROOT / "research-lab-bio_rules.yaml"

def test_load_real_project_rules():
    """Verify the actual project rules file loads correctly."""
    assert RULES_PATH.exists(), "Project rules file missing!"
    rules = load_rules(RULES_PATH)
    assert isinstance(rules, Rules)
    assert rules.project.slug == "research-lab-bio"
    assert rules.auth.password_hashing.algorithm == "argon2"
    # Spot check deep nesting
    markdown_schema = rules.blocks.schemas.get("markdown")
    assert markdown_schema is not None
    assert "text" in markdown_schema.properties

def test_load_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_rules(Path("non_existent_rules.yaml"))

def test_load_invalid_yaml_raises(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("key: value: what", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid YAML"):
        load_rules(f)

def test_load_invalid_schema_raises(tmp_path):
    """Test that missing required fields raises ValidationError wrapped in ValueError."""
    bad_data = {
        "project": {"slug": "test", "rules_version": "1.0", "required_sections": []}
        # Missing all other sections
    }
    f = tmp_path / "invalid_schema.yaml"
    with open(f, "w") as file:
        yaml.dump(bad_data, file)
        
    with pytest.raises(ValueError, match="Rules validation failed"):
        load_rules(f)
