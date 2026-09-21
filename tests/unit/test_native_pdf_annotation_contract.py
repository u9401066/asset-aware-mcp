"""Discoverable annotation schemas describe kind-specific geometry and full references."""

import hashlib
import json

import pytest
from jsonschema import Draft202012Validator

from src.application.native_document_contract import native_document_contract
from src.application.native_schema import request_schema
from src.domain.native_assets import NativeDocumentRequest
from src.domain.native_pdf_annotations import PdfAnnotationAppearance
from src.presentation.response_limits import format_limited_json_response


@pytest.mark.parametrize(
    "value,valid",
    [
        ({"kind": "Text", "point": [0.1, 0.2]}, True),
        ({"kind": "Text"}, False),
        ({"kind": "Text", "point": None}, False),
        ({"kind": "Text", "point": [0.1, 0.2], "text": "unused"}, False),
        ({"kind": "Text", "point": [True, 0.2]}, False),
        ({"kind": "FreeText", "rect": [0.1, 0.2, 0.8, 0.6], "text": "批註"}, True),
        ({"kind": "FreeText", "rect": [0.1, 0.2, 0.8, 0.6], "point": None}, False),
        ({"kind": "Line", "vertices": [[0.1, 0.2], [0.4, 0.6]]}, True),
        ({"kind": "Line", "vertices": [[0.1, 0.2]]}, False),
        ({"kind": "Polygon", "vertices": [[0.1, 0.2], [0.4, 0.6]]}, False),
        ({"kind": "Highlight", "quads": []}, False),
        (
            {"kind": "Highlight", "quads": [[0.1, 0.1, 0.8, 0.1, 0.1, 0.2, 0.8, 0.2]]},
            True,
        ),
    ],
)
def test_appearance_schema_matches_supported_fields(value, valid):
    validator = Draft202012Validator(PdfAnnotationAppearance.model_json_schema())
    assert validator.is_valid(value) == valid
    if valid:
        PdfAnnotationAppearance.model_validate(value)
    else:
        with pytest.raises(ValueError):
            PdfAnnotationAppearance.model_validate(value)


def test_annotation_contract_and_selected_schema_are_complete_and_bounded():
    request = NativeDocumentRequest(for_op="update_pdf_annotations")
    contract = native_document_contract(request, pdf_enabled=True)
    assert contract["pdf_annotations_enabled"]
    assert {
        "read_pdf_annotations",
        "read_pdf_annotation",
        "update_pdf_annotations",
    } <= set(contract["formats"]["pdf"])
    assert "response_truncated" not in format_limited_json_response(
        title="Native", payload=contract
    )
    chunks, offset = [], 0
    while True:
        page = native_document_contract(
            NativeDocumentRequest.model_validate(
                {
                    **contract["contract_request"],
                    "text_offset": offset,
                    "text_limit": 731,
                }
            ),
            pdf_enabled=True,
        )
        assert page["text_sha256"] == contract["contract_sha256"]
        chunks.append(page["text_excerpt"])
        offset = page["next_text_offset"]
        if offset is None:
            break
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == contract["contract_sha256"]
    assert "replace_appearance" in json.loads(text)["pdf_annotations_policy"]
    schema = request_schema("update_pdf_annotations")
    assert "PdfAnnotationAppearance" in schema["$defs"]
    assert schema["$defs"]["PdfAnnotationAppearance"]["oneOf"]
    assert set(schema["properties"]) == {
        "op",
        "asset_id",
        "expected_revision",
        "pdf_annotations_update",
    }
    Draft202012Validator.check_schema(schema)
    assert not native_document_contract(pdf_enabled=False)["pdf_annotations_enabled"]
