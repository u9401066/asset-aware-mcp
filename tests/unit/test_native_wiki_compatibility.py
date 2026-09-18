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


def test_v1_3_docx_projection_retains_exact_artifact_hashes():
    from src.application.native_docx_records import docx_block_record
    from src.application.native_docx_wiki import NativeDocxWikiContent

    source = b"legacy DOCX fixture"
    identity = {
        "asset_id": "file_" + "b" * 32,
        "revision": digest(source),
        "name": "legacy.docx",
        "format": "docx",
        "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    content = NativeDocxWikiContent(
        identity, resolve_citation_format({"preset": "source"}), CitationMetadata()
    )
    content.add_parts(
        {"word/document.xml": b"<legacy/>", "word/media/image1.png": b"legacy picture"}
    )
    content.add_block(
        docx_block_record(
            {
                "id": "p1",
                "block_type": "paragraph",
                "text": "舊版證據",
                "metadata": {"source_part": "word/document.xml"},
            },
            identity["asset_id"],
            identity["revision"],
        )
    )
    prefix = "native-5c77011e7254748890d5b3b67218207acec01bfae6b5363e93145a4026ce3620"
    # Digests derived from the released v1.3.0 projection/citation implementation.
    assert {name: digest(data) for name, data in content.finish(source).items()} == {
        f"{prefix}-part-c282ade051eceddc2d15ed2e9d196ce2201d69784a25c7f95861529f4111a092.xml": "5a03abff11092902665004cbbf25c0016edda9ba5c76ff5d15e6d54a929e1125",
        f"{prefix}-part-4c2f1947f657aa158155c6b6278129a2063f05e9dec5c6ac6d5a1e868ec1b8ef.png": "2ce519eca47c19ac63f0ac7f5f23cc6a0171f59b408f879e7087b1673ee9196e",
        f"{prefix}-block-cc3ecb7d8fee8fac0ecbe110fae16e4b695dfeba4edbbad0d1d30086d9c14ef0.md": "7f31c655a3b7f8fcca0197040e054812a3d9310dc82ada6adf520e89917ff568",
        f"{prefix}.docx": "99373c8da38be88e8cdbbde85c975f7fb91c3708d66ac41451aa18df56e68cfa",
        "records.jsonl": "df954cc940a35bd1c4023129c14cc203b4a4f3ae3d715a2062689710b474bd64",
        f"{prefix}-index.md": "63b1030b9b584fd642370b5985cefe31511652fd1d13fe2bccbab2605168b6a4",
        "manifest.json": "7f0b04750abee397bcc818dfa4104fc7ddfb03e1cd71b1e738f9d9914cf4e5c0",
    }
