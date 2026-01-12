import json
from typing import Any
from uuid import UUID

from src.domain.entities import ContentBlock
from src.rules.models import BlockProperty, BlocksRules


class BlockValidator:
    def __init__(self, rules: BlocksRules):
        self.rules = rules

    def validate(self, block: ContentBlock) -> None:
        """
        Validate a ContentBlock against strict schema rules.

        Raises:
            ValueError: If validation fails.
        """
        # 1. Check allowed type
        if block.block_type not in self.rules.allowed_types:
            raise ValueError(f"Block type '{block.block_type}' is not allowed.")

        # 2. Get schema for this type
        # schemas is a dict[str, BlockSchema], so use .get()
        schema = self.rules.schemas.get(block.block_type)
        if not schema:
            return

        # 3. Check required fields
        for req_field in schema.required:
            if req_field not in block.data_json:
                msg = f"Missing required field '{req_field}' for block type '{block.block_type}'."
                raise ValueError(msg)

        # 4. Check field constraints
        for field, props in schema.properties.items():
            if field in block.data_json:
                value = block.data_json[field]
                self._validate_field(field, value, props)

    def _validate_field(self, field_name: str, value: Any, props: BlockProperty) -> None:
        # Check Type
        expected_type = props.type
        if expected_type == "string":
            if not isinstance(value, str):
                raise ValueError(f"Field '{field_name}' must be a string.")
            # Min/Max length
            if props.min is not None and len(value) < props.min:
                raise ValueError(f"Field '{field_name}' too short (min {props.min}).")
            if props.max is not None and len(value) > props.max:
                raise ValueError(f"Field '{field_name}' too long (max {props.max}).")

        elif expected_type == "int":
            if not isinstance(value, int) or isinstance(value, bool):  # bool is int in python
                raise ValueError(f"Field '{field_name}' must be an integer.")
            if props.min is not None and value < props.min:
                raise ValueError(f"Field '{field_name}' too small (min {props.min}).")
            if props.max is not None and value > props.max:
                raise ValueError(f"Field '{field_name}' too large (max {props.max}).")

        elif expected_type == "uuid":
            # Can be string representation or actual UUID object?
            # data_json usually comes from API as generic JSON, so strings.
            try:
                if isinstance(value, UUID):
                    pass
                else:
                    UUID(str(value))
            except ValueError as e:
                msg = f"Field '{field_name}' must be a valid UUID."
                raise ValueError(msg) from e

        elif expected_type == "object":
            if not isinstance(value, dict):
                raise ValueError(f"Field '{field_name}' must be an object/dict.")
            # Max bytes check
            if props.max_bytes is not None:
                # Estimate size by dumping to JSON
                size = len(json.dumps(value))
                if size > props.max_bytes:
                    msg = f"Field '{field_name}' exceeds size limit ({size} > {props.max_bytes})."
                    raise ValueError(msg)
