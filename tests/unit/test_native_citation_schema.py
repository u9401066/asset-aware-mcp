"""Native discovery exposes citation display inputs without accepting proof objects."""

import pytest
from jsonschema import Draft202012Validator

from src.application.native_schema import request_schema
from src.domain.citation_format import resolve_citation_format
from src.domain.native_assets import NativeDocumentRequest


def request(contract):
    return {
        "op": "export_wiki",
        "asset_id": "file_" + "a" * 32,
        "output_dir": "wiki",
        "citation_contract": contract,
    }


@pytest.mark.parametrize(
    "contract",
    [
        {"preset": "source"},
        {"preset": "author-year"},
        {"preset": "numeric"},
        {
            "inline_template": "{title} / {locator}",
            "reference_template": "{source_id}",
            "required_fields": ["title"],
        },
    ],
)
def test_native_citation_schema_and_runtime_preserve_valid_json(contract):
    data = request(contract)
    schema = request_schema("export_wiki")
    Draft202012Validator(schema).validate(data)
    parsed = NativeDocumentRequest.model_validate(data)
    expected = resolve_citation_format(contract)
    assert (
        resolve_citation_format(parsed.citation_contract.model_dump(mode="json"))
        == expected
    )
    assert {"CitationFormatContract", "CitationFormatPreset"} <= schema["$defs"].keys()
    assert {"inline_template", "reference_template"} <= set(
        schema["$defs"]["CitationFormatContract"]["required"]
    )


@pytest.mark.parametrize(
    "contract",
    [
        {"source_page_reference": {"revision": "b" * 64}},
        {"preset": "source", "source_page_reference": {}},
        {"preset": "source", "inline_template": "{title}"},
        {"preset": "unknown"},
        {"inline_template": "{title}"},
        {
            "inline_template": "{title}",
            "reference_template": "{source_id}",
            "proof": {"valid": True},
        },
    ],
)
def test_native_schema_rejects_invented_provenance_and_incomplete_formats(contract):
    data = request(contract)
    assert list(Draft202012Validator(request_schema("export_wiki")).iter_errors(data))
    with pytest.raises(ValueError):
        NativeDocumentRequest.model_validate(data)
