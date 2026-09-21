"""Annotation references survive deletion in derivation ledgers and CSL exports."""

import json
import shutil
from pathlib import Path

import pytest

from src.application.csl_citation_service import CslCitationService
from src.domain.csl_citations import CslDocument
from src.infrastructure.csl_processor import NodeCslProcessor
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_derivation_helpers import pair, read_ledger, record, service_at
from tests.native_pdf_annotation_helpers import read, update
from tests.native_pdf_helpers import build_pdf
from tests.native_workbook_helpers import _call
from tests.unit.test_csl_processor import document


def annotation_source(tmp_path):
    service = service_at(tmp_path)
    path = tmp_path / "comments.pdf"
    path.write_bytes(build_pdf())
    asset = _call(service, op="register", source_path=str(path))["asset"]
    return service, asset, path, read(service, asset)["evidence"]


def remove(service, asset, reference):
    return update(
        service,
        asset,
        [
            {
                "op": "delete",
                "reference": reference,
                "scope": "annotation_and_owned_popup",
            }
        ],
    )


def test_annotation_source_and_target_derivations_keep_historical_endpoints(tmp_path):
    service, pdf, path, reference = annotation_source(tmp_path)
    workbook, claim = pair(service)
    claim["sources"] = [reference]
    claim["review"] = {"notes": "Synthetic test; semantic support not reviewed"}
    first = record(service, workbook, claim)
    reverse = {**claim, "target": reference, "sources": [claim["target"]]}
    second = record(service, pdf, reverse)
    exported = _call(
        service,
        op="export_wiki",
        asset_id=workbook["asset_id"],
        output_dir=str(tmp_path / "wiki"),
    )
    root = Path(exported["output_dir"])
    manifest = json.loads((root / "manifest.json").read_text())
    attachment = next(iter(manifest["derivations"]["source_attachments"].values()))
    assert (root / attachment["attachment"]).read_bytes() == path.read_bytes()
    ledger, _ = read_ledger(service, workbook["asset_id"])
    assert ledger["events"][0]["derivation"]["sources"] == [reference]
    original = {p.name: p.read_bytes() for p in root.iterdir()}
    remove(service, pdf, reference)
    for target, result in [(workbook, first), (pdf, second)]:
        checked = _call(
            service,
            op="verify_derivation",
            asset_id=target["asset_id"],
            derivation_id=result["derivation_id"],
        )
        assert checked["references_valid"] and checked["active"]
    assert _call(
        service,
        op="export_wiki",
        asset_id=workbook["asset_id"],
        output_dir=str(tmp_path / "wiki"),
    )["output_dir"] == str(root)
    assert original == {p.name: p.read_bytes() for p in root.iterdir()}
    current = _call(
        service,
        op="export_wiki",
        asset_id=pdf["asset_id"],
        output_dir=str(tmp_path / "wiki"),
    )
    current_manifest = json.loads(
        (Path(current["output_dir"]) / "manifest.json").read_text()
    )
    assert current_manifest["derivations"]["active_ids_for_revision"] == []


def test_csl_accepts_annotation_reference_and_retains_exact_historical_pdf(tmp_path):
    if not shutil.which("node"):
        pytest.skip("CSL requires optional Node.js")
    service, pdf, path, reference = annotation_source(tmp_path)
    raw = document().model_dump()
    raw["sources"] = {"comment": reference}
    raw["clusters"][0]["cites"][0]["source_keys"] = ["comment"]
    csl = CslCitationService(
        NodeCslProcessor(), service.evidence, FileNativeWikiPublisher()
    )
    doc = CslDocument.model_validate(raw)
    result, published = csl.render(doc, str(tmp_path / "citations"))
    root = Path(published["output_dir"])
    source = result["sources"]["comment"]
    assert source["reference"] == reference
    assert source["semantic_support"] == "not_checked"
    assert (root / source["attachment"]["name"]).read_bytes() == path.read_bytes()
    original = {p.name: p.read_bytes() for p in root.iterdir()}
    remove(service, pdf, reference)
    again, reused = csl.render(doc, str(tmp_path / "citations"))
    assert again == result and reused["reused"]
    assert original == {p.name: p.read_bytes() for p in root.iterdir()}
