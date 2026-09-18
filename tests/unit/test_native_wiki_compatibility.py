"""The DOCX projection must not alter v1.2 native spreadsheet artifact bytes."""

from src.application.native_evidence_service import attach_native_evidence
from src.application.native_wiki_format import NativeWikiContent, digest
from src.domain.citation_format import CitationMetadata, resolve_citation_format


def test_v1_2_spreadsheet_projection_retains_exact_artifact_hashes():
    source = b"legacy native source fixture"
    identity = {
        "asset_id": "file_" + "a" * 32,
        "revision": digest(source),
        "name": "legacy.xlsx",
        "format": "xlsx",
        "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    content = NativeWikiContent(
        identity, resolve_citation_format({"preset": "source"}), CitationMetadata()
    )
    cell = {
        "sheet": "Sheet1",
        "cell": "A1",
        "kind": "string",
        "value": "保留原有證據",
        "style_index": 0,
        "locator": {
            "sheet_id": "1",
            "part": "xl/worksheets/sheet1.xml",
            "kind": "worksheet",
            "cell": "A1",
        },
    }
    attach_native_evidence(cell, identity["asset_id"], identity["revision"])
    content.add_cell(cell)
    prefix = "native-d1ad85ca1f5cdbfcd3568292f9f148d4b710997c10ca0f1ad6fd7eb52e5a0a47"
    key = "aff316c529188c73b035e9fa6780f872df538a107bb6c383c4409591ab073cf9"
    assert content.prefix == prefix
    assert {name: digest(data) for name, data in content.finish(source).items()} == {
        f"{prefix}-cell-{key}.md": "71ba2200fdd8466208932082af0b6a0d942b3e9b42a146e19b22182faba62391",
        f"{prefix}.xlsx": "3a64aca1a65f71e490c76cdc7d788c9e0e63aaae4b9ad3b1990f5fabb02a6eed",
        "records.jsonl": "f383b5d350c0562396c305b0e0c334ca5fffc02586070e77a9c60a17eaa809a3",
        f"{prefix}-index.md": "6154c822b1fafe5ebac00fe2063177f68d651e67b17c81f713dc11acf153689e",
        "manifest.json": "3b75b923e43d8d2365898632293a58f587c56f4fe96b783bf1d6f4d4086461cf",
    }
