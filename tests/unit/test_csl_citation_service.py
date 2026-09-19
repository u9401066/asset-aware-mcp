"""Citation display preserves exact native revisions, portable evidence and notes."""

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from src.application.csl_citation_service import (
    CslCitationService,
    canonical,
    citation_page,
    digest,
)
from src.application.native_document_service import NativeDocumentService
from src.domain.csl_citations import CslDocument
from src.infrastructure.csl_processor import NodeCslProcessor
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_workbook_helpers import _call
from tests.unit.test_csl_processor import document


@pytest.fixture
def context(tmp_path):
    if not shutil.which("node"):
        pytest.skip("CSL rendering requires optional Node.js >=20")
    store = FileNativeAssetRepository(tmp_path / "store")
    publisher = FileNativeWikiPublisher((tmp_path / "store",))
    native = NativeDocumentService(store, SpreadsheetFileAdapter(), publisher)
    asset = _call(
        native,
        op="create",
        workbook={
            "name": "Evidence.xlsx",
            "sheets": ["Data"],
            "edits": [{"sheet": "Data", "cell": "A1", "value": "007"}],
        },
    )["asset"]
    cell = _call(
        native,
        op="read_cell",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        sheet="Data",
        cell="A1",
    )
    raw = document().model_dump()
    raw["sources"] = {"measured": cell["cell"]["evidence"]}
    raw["clusters"][0]["cites"][0]["source_keys"] = ["measured"]
    return (
        native,
        asset,
        CslCitationService(NodeCslProcessor(), native.evidence, publisher),
        CslDocument.model_validate(raw),
    )


def test_wiki_is_complete_reusable_and_historical_after_native_edit(context, tmp_path):
    native, asset, service, doc = context
    original = native.repository.read(asset["asset_id"], asset["revision"])
    preview, publication = service.render(doc)
    assert publication is None
    result, publication = service.render(
        doc, str(tmp_path / "wiki"), digest(canonical(preview))
    )
    assert preview == result and publication["success"]
    root = Path(publication["output_dir"])
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    for name, record in manifest["files"].items():
        value = (root / name).read_bytes()
        assert digest(value) == record["sha256"] and len(value) == record["size_bytes"]
    assert json.loads((root / "citations.json").read_text(encoding="utf-8")) == result
    source = result["sources"]["measured"]
    assert source["reference"] == doc.sources["measured"]
    assert (root / source["attachment"]["name"]).read_bytes() == original
    assert source["semantic_support"] == "not_checked"
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    _call(
        native,
        op="update",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        edits=[{"sheet": "Data", "cell": "A1", "value": "Changed"}],
    )
    old, reused = service.render(doc, str(tmp_path / "wiki"))
    assert old == result and reused["reused"]
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}
    assert "<i>Alpha</i>" in (root / manifest["index_note"]).read_text(encoding="utf-8")
    preview_html = (root / "references.html").read_text(encoding="utf-8")
    assert "Content-Security-Policy" in preview_html
    assert "text-indent:-2em" in preview_html and "<i>Alpha</i>" in preview_html


def test_stale_expected_hash_and_bad_source_never_publish(context, tmp_path):
    _, _, service, doc = context
    root = tmp_path / "wiki"
    with pytest.raises(ValueError, match="no wiki was published"):
        service.render(doc, str(root), "0" * 64)
    assert not root.exists()
    raw = deepcopy(doc.model_dump())
    raw["sources"]["measured"]["value_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="failed verification"):
        service.render(CslDocument.model_validate(raw), str(root))
    assert not root.exists()


def test_changed_style_gets_new_snapshot_and_curated_content_is_preserved(
    context, tmp_path
):
    _, _, service, doc = context
    root = str(tmp_path / "wiki")
    old, publication = service.render(doc, root)
    index = next(Path(publication["output_dir"]).glob("*-index.md"))
    index.write_text("Human curation\n", encoding="utf-8")
    with pytest.raises(ValueError, match="existing notes preserved"):
        service.render(doc, root)
    raw = doc.model_dump()
    raw["style"] = "vancouver"
    new, changed = service.render(CslDocument.model_validate(raw), root)
    assert changed["output_dir"] != publication["output_dir"]
    assert new["sources"] == old["sources"]
    assert index.read_text(encoding="utf-8") == "Human curation\n"


def test_missing_bibliographic_fields_are_reported_without_fabrication(context):
    _, _, service, doc = context
    raw = doc.model_dump()
    raw["items"][0].pop("issued")
    raw["items"][0].pop("author")
    result, _ = service.render(CslDocument.model_validate(raw))
    assert result["missing_metadata"] == [{"id": "a", "fields": ["author", "issued"]}]
    assert "author" not in result["document"]["items"][0]
    assert "n.d." in result["bibliography"][0]["text"]


def test_paging_preserves_complete_unicode_and_detects_changed_content():
    value = {"text": '中文\n"\\' * 5000}
    offset, parts, sha = 0, [], None
    while True:
        page = citation_page(value, offset, 8000, sha)
        sha = sha or page["text_sha256"]
        assert page["excerpt_char_range"][0] == offset
        assert len(json.dumps(page, ensure_ascii=False)) < 9000
        parts.append(page["text_excerpt"])
        if page["next_text_offset"] is None:
            break
        offset = page["next_text_offset"]
    data = "".join(parts)
    assert hashlib.sha256(data.encode()).hexdigest() == sha
    assert json.loads(data) == value
    with pytest.raises(ValueError, match="changed"):
        citation_page({"text": "Changed"}, 0, 4000, sha)
