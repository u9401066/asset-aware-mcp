import hashlib
import json

import pytest
from jsonschema import Draft202012Validator

from src.application.native_document_contract import native_document_contract
from src.application.native_schema import request_schema
from src.domain.native_assets import NativeDocumentRequest
from src.presentation.response_limits import format_limited_json_response


def test_enabled_image_contract_and_complete_selected_schema_are_bounded():
    request = NativeDocumentRequest(for_op="update_image")
    contract = native_document_contract(
        request,
        images_enabled=True,
        pdf_enabled=True,
        docx_enabled=True,
        pptx_enabled=True,
    )
    assert contract["images_enabled"]
    assert "update_image" in contract["formats"]["tiff"]
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
                    "text_limit": 1000,
                }
            ),
            images_enabled=True,
            pdf_enabled=True,
            docx_enabled=True,
            pptx_enabled=True,
        )
        assert page["text_sha256"] == contract["contract_sha256"]
        chunks.append(page["text_excerpt"])
        offset = page["next_text_offset"]
        if offset is None:
            break
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == contract["contract_sha256"]
    assert "candidate" in json.loads(text)["image_policy"]
    schema = request_schema("update_image")
    assert schema["$defs"]["NativeImageRevisionPlan"]["properties"]["frames"]["items"][
        "oneOf"
    ]
    assert set(schema["properties"]) == {
        "op",
        "asset_id",
        "expected_revision",
        "image_update",
    }


@pytest.mark.parametrize(
    "fields,valid",
    [
        (
            {
                "op": "create_image",
                "image_create": {
                    "name": "new.png",
                    "width": 2,
                    "height": 3,
                    "rgba": [0, 0, 0, 255],
                },
            },
            True,
        ),
        (
            {
                "op": "create_image",
                "image_create": {
                    "name": "new.png",
                    "width": True,
                    "height": 3,
                    "rgba": [0, 0, 0, 255],
                },
            },
            False,
        ),
        ({"op": "read_image", "asset_id": "file_" + "a" * 32}, False),
        (
            {
                "op": "read_image",
                "asset_id": "file_" + "a" * 32,
                "revision": "a" * 64,
                "image_region": {"rect": [0.0, 0.0, 1.0, 1.0]},
            },
            False,
        ),
    ],
)
def test_image_operation_schema_matches_required_fields_and_strict_types(fields, valid):
    assert Draft202012Validator(request_schema(fields["op"])).is_valid(fields) == valid
    if valid:
        NativeDocumentRequest.model_validate(fields)
    else:
        with pytest.raises(ValueError):
            NativeDocumentRequest.model_validate(fields)
