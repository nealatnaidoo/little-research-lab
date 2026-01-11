from uuid import uuid4

import pytest

from src.domain.blocks import BlockValidator
from src.domain.entities import ContentBlock
from src.rules.models import BlockProperty, BlockSchema, BlocksRules


@pytest.fixture
def mock_rules():
    # Construct minimal rules manually to strictly control constraints in tests
    # Using explicit models instead of loading file
    return BlocksRules(
        allowed_types=["markdown", "image"],
        max_blocks_per_item=10,
        schemas={
            "markdown": BlockSchema(
                required=["text"],
                properties={
                    "text": BlockProperty(type="string", min=5, max=100)
                }
            ),
            "image": BlockSchema(
                required=["asset_id"],
                properties={
                    "asset_id": BlockProperty(type="uuid"),
                    "caption": BlockProperty(type="string", max=20)
                }
            )
        }
    )

@pytest.fixture
def validator(mock_rules):
    return BlockValidator(mock_rules)

def test_validate_valid_markdown(validator):
    block = ContentBlock(
        block_type="markdown",
        data_json={"text": "Hello World"}
    )
    # Should not raise
    validator.validate(block)

def test_validate_invalid_type(validator):
    block = ContentBlock(
        block_type="chart", # Not in allowed_types fixture
        data_json={}
    )
    with pytest.raises(ValueError, match="not allowed"):
        validator.validate(block)

def test_validate_missing_required(validator):
    block = ContentBlock(
        block_type="markdown",
        data_json={} # Missing 'text'
    )
    with pytest.raises(ValueError, match="Missing required field"):
        validator.validate(block)

def test_validate_string_too_short(validator):
    block = ContentBlock(
        block_type="markdown",
        data_json={"text": "Hi"} # min 5
    )
    with pytest.raises(ValueError, match="too short"):
        validator.validate(block)

def test_validate_invalid_uuid(validator):
    block = ContentBlock(
        block_type="image",
        data_json={"asset_id": "not-a-uuid"}
    )
    with pytest.raises(ValueError, match="valid UUID"):
        validator.validate(block)

def test_validate_valid_uuid_string(validator):
    uid = str(uuid4())
    block = ContentBlock(
        block_type="image",
        data_json={"asset_id": uid}
    )
    validator.validate(block)
