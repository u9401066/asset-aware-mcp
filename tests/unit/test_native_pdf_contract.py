"""Discovery expresses exclusive page sources and rejects coercive geometry."""

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from src.domain.native_pdf import NativePdfPageEdit, NativePdfPageInput

REF = {
    "asset_id": "file_" + "a" * 32,
    "revision": "b" * 64,
    "locator": {"page_index": 0, "object_id": 3, "generation": 0},
    "value_sha256": "c" * 64,
}


@pytest.mark.parametrize(
    "value,valid",
    [
        ({}, False),
        ({"blank": None}, False),
        ({"blank": {}, "reference": REF}, False),
        ({"blank": {}}, True),
        ({"reference": REF}, True),
        ({"blank": None, "reference": REF}, True),
    ],
)
def test_page_source_discovery_matches_runtime(value, valid):
    validator = Draft202012Validator(NativePdfPageInput.model_json_schema())
    assert validator.is_valid(value) == valid
    if valid:
        NativePdfPageInput.model_validate(value)
    else:
        with pytest.raises(ValidationError):
            NativePdfPageInput.model_validate(value)


@pytest.mark.parametrize(
    "value,valid",
    [
        ({}, False),
        ({"rotation": None}, False),
        ({"rotation": 0}, True),
        ({"crop_box": [0, 0, 10, 10]}, True),
    ],
)
def test_geometry_discovery_requires_an_operation(value, valid):
    value = {"reference": REF, **value}
    validator = Draft202012Validator(NativePdfPageEdit.model_json_schema())
    assert validator.is_valid(value) == valid
    if valid:
        NativePdfPageEdit.model_validate(value)
    else:
        with pytest.raises(ValidationError):
            NativePdfPageEdit.model_validate(value)


@pytest.mark.parametrize("value", [False, True, 90.0, "90"])
def test_rotation_is_not_coerced(value):
    with pytest.raises(ValidationError, match="integer"):
        NativePdfPageEdit(reference=REF, rotation=value)
