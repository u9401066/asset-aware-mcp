"""Full field evidence survives revision changes in Wikis, derivations and CSL."""

import io
import json
import shutil
from pathlib import Path

import pikepdf
import pytest

from src.application.csl_citation_service import CslCitationService
from src.domain.csl_citations import CslDocument
from src.domain.native_asset_models import NativeEditResult
from src.infrastructure.csl_processor import NodeCslProcessor
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_derivation_helpers import pair, read_ledger, record, service_at
from tests.native_pdf_field_helpers import form_pdf
from tests.native_workbook_helpers import _call
from tests.unit.test_csl_processor import document
from tests.unit.test_native_pdf_field_service import (
    catalog,
    complete,
    hidden_edit,
    read,
    update,
)


def field_source(tmp_path, data=None):
    service = service_at(tmp_path)
    source = tmp_path / "fields.pdf"
    source.write_bytes(form_pdf() if data is None else data)
    asset = _call(service, op="register", source_path=str(source))["asset"]
    return service, asset, source


def export(service, asset, tmp_path, **extra):
    result = _call(
        service,
        op="export_wiki",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        output_dir=str(tmp_path / "wiki"),
        **extra,
    )
    root = Path(result["output_dir"])
    return root, json.loads((root / "manifest.json").read_text())


def snapshot(root):
    return {path.name: path.read_bytes() for path in root.iterdir()}


def remove(service, asset, reference):
    return update(
        service,
        asset,
        [
            {
                "op": "delete",
                "reference": reference,
                "scope": "field_subtree_and_all_widgets",
            }
        ],
    )


def test_wiki_retains_duplicate_hidden_group_and_every_widget_page(tmp_path):
    service, asset, source = field_source(tmp_path)
    root, manifest = export(
        service,
        asset,
        tmp_path,
        citation_contract={
            "name": "fields",
            "inline_template": "欄位【{locator}】",
            "reference_template": "{title} | {locator}",
        },
    )
    assert manifest["projection"].startswith("pdf-fields-v1:")
    assert manifest["field_count"] == 7
    assert (root / manifest["source_attachment"]).read_bytes() == source.read_bytes()
    assert json.loads((root / manifest["field_catalog"]).read_text()) == catalog(
        service, asset
    )
    assert json.loads((root / manifest["operation_result_file"]).read_text()) is None
    records = [
        json.loads(line)
        for line in (root / manifest["field_records"]).read_text().splitlines()
    ]
    assert len({r["note"] for r in records}) == 7
    duplicates = [r for r in records if r["qualified_name"] == "duplicate"]
    assert (
        len(duplicates) == 2 and duplicates[0]["evidence"] != duplicates[1]["evidence"]
    )
    for record_ in records:
        assert _call(service, op="verify", reference=record_["evidence"])["valid"]
        full = complete(
            service,
            op="read_pdf_field",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            pdf_field_locator=record_["locator"],
        )["field"]
        assert {key: record_[key] for key in full} == full
        loc = record_["locator"]
        physical = "/".join(str(i) for i in loc["field_path"])
        inline = record_["citation_presentation"]["inline"]
        assert f"欄位【PDF field path {physical} (zero-based)" in inline
        assert f"object {loc['object_id']} {loc['generation']}" in inline
        for link in record_["page_links"]:
            assert (root / link["note"]).is_file()
            assert (
                (root / link["preview_attachment"])
                .read_bytes()
                .startswith(b"\x89PNG\r\n\x1a\n")
            )
    hidden = next(r for r in records if r["qualified_name"] == "person.hidden")
    assert hidden["page_links"] == []
    assert "Value text: 007" in (root / hidden["note"]).read_text()
    group = next(r for r in records if r["qualified_name"] == "person")
    assert group["child_field_notes"] == [hidden["note"]]
    shared = next(r for r in records if r["qualified_name"] == "across")
    assert [link["page_index"] for link in shared["page_links"]] == [0, 2]
    for link in shared["page_links"]:
        assert link["preview_attachment"] in (root / shared["note"]).read_text()


def test_deleted_all_fields_keep_complete_receipt_and_historical_wiki(tmp_path):
    service, asset, source = field_source(tmp_path)
    root, _ = export(service, asset, tmp_path)
    original = snapshot(root)
    records = [
        complete(
            service,
            op="read_pdf_field",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            pdf_field_locator=entry["locator"],
        )["field"]
        for entry in catalog(service, asset)["fields"]
    ]
    changed = update(
        service,
        asset,
        [
            {
                "op": "delete",
                "reference": item["evidence"],
                "scope": "field_subtree_and_all_widgets",
            }
            for item in records
            if len(item["locator"]["field_path"]) == 1
        ],
    )
    response = complete(service, **changed["review_request"])
    assert response["catalog"]["field_count"] == 0
    assert response["catalog"]["acroform_present"]
    latest_root, manifest = export(service, changed["asset"], tmp_path)
    assert latest_root != root and manifest["field_count"] == 0
    assert (latest_root / "fields.jsonl").read_bytes() == b""
    receipt = json.loads((latest_root / manifest["operation_result_file"]).read_text())
    assert receipt == response["operation_result"]
    deleted = [
        r for change in receipt["changes"][:-1] for r in change["deleted_fields"]
    ]
    assert receipt["changes"][-1]["operation"] == "field_catalog_readback"
    assert receipt["changes"][-1]["after_catalog"] == response["catalog"]
    assert len(deleted) == 7
    for original_record in records:
        assert _call(service, op="verify", reference=original_record["evidence"])[
            "valid"
        ]
        assert {k: v for k, v in original_record.items() if k != "evidence"} in deleted
    assert export(service, asset, tmp_path)[0] == root
    assert snapshot(root) == original
    assert (
        source.read_bytes()
        == (
            root / json.loads(original["manifest.json"])["source_attachment"]
        ).read_bytes()
    )


def test_repeated_pdf_bytes_with_new_receipt_get_separate_wiki_and_read_hash(tmp_path):
    service, asset, source = field_source(tmp_path)
    old_root, _ = export(service, asset, tmp_path)
    old_files = snapshot(old_root)
    first = _call(
        service,
        op="read_pdf_fields",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        text_limit=79,
    )
    hidden = read(service, asset, "person.hidden")
    changed = update(service, asset, [hidden_edit(hidden, "008")])
    report = NativeEditResult(
        changed_parts=["PDF"],
        preserved_parts=0,
        changes=[{"operation": "restore_exact_fixture"}],
        checks=["fixture_bytes_retained"],
    )
    restored = service.repository.commit(
        asset["asset_id"], changed["asset"]["revision"], source.read_bytes(), report
    )
    assert restored.revision == asset["revision"]
    with pytest.raises(ValueError, match="changed"):
        _call(
            service,
            op="read_pdf_fields",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            text_offset=first["next_text_offset"],
            pdf_field_text_sha256=first["text_sha256"],
        )
    new_root, manifest = export(service, asset, tmp_path)
    assert new_root != old_root
    assert json.loads(
        (new_root / manifest["operation_result_file"]).read_text()
    ) == report.model_dump(mode="json")
    assert snapshot(old_root) == old_files
    assert _call(service, op="verify", reference=hidden["evidence"])["valid"]


@pytest.mark.parametrize("selected", [False, True])
def test_field_and_substring_derivations_keep_historical_endpoints(tmp_path, selected):
    service, pdf, source = field_source(tmp_path)
    field = read(service, pdf, "person.hidden")
    reference = field["evidence"]
    if selected:
        reference = _call(
            service,
            op="read_selection",
            reference=reference,
            selection={
                "pointer": "/inherited_entries/~1V/text",
                "char_range": {"start": 1, "end": 3},
            },
        )["evidence"]
    workbook, claim = pair(service)
    claim["sources"] = [reference]
    claim["review"] = {"notes": "Synthetic fixture; semantic support not assessed"}
    first = record(service, workbook, claim)
    second = record(
        service, pdf, {**claim, "target": reference, "sources": [claim["target"]]}
    )
    root, manifest = export(service, workbook, tmp_path)
    attachment = next(iter(manifest["derivations"]["source_attachments"].values()))
    assert (root / attachment["attachment"]).read_bytes() == source.read_bytes()
    ledger, _ = read_ledger(service, workbook["asset_id"])
    assert ledger["events"][0]["derivation"]["sources"] == [reference]
    old_files = snapshot(root)
    changed = remove(service, pdf, field["evidence"])
    for target, event in [(workbook, first), (pdf, second)]:
        check = _call(
            service,
            op="verify_derivation",
            asset_id=target["asset_id"],
            derivation_id=event["derivation_id"],
        )
        assert check["references_valid"] and check["active"]
    assert export(service, workbook, tmp_path)[0] == root
    assert snapshot(root) == old_files
    assert (
        export(service, changed["asset"], tmp_path)[1]["derivations"][
            "active_ids_for_revision"
        ]
        == []
    )


def test_csl_field_reference_keeps_original_pdf_after_deletion(tmp_path):
    if not shutil.which("node"):
        pytest.skip("CSL requires optional Node.js")
    service, pdf, source = field_source(tmp_path)
    reference = read(service, pdf, "person.hidden")["evidence"]
    raw = document().model_dump()
    raw["sources"] = {"field": reference}
    raw["clusters"][0]["cites"][0]["source_keys"] = ["field"]
    csl = CslCitationService(
        NodeCslProcessor(), service.evidence, FileNativeWikiPublisher()
    )
    doc = CslDocument.model_validate(raw)
    result, published = csl.render(doc, str(tmp_path / "citations"))
    root = Path(published["output_dir"])
    evidence = result["sources"]["field"]
    assert evidence["reference"] == reference
    assert evidence["semantic_support"] == "not_checked"
    assert (root / evidence["attachment"]["name"]).read_bytes() == source.read_bytes()
    old_files = snapshot(root)
    remove(service, pdf, reference)
    again, reused = csl.render(doc, str(tmp_path / "citations"))
    assert again == result and reused["reused"]
    assert snapshot(root) == old_files


def test_unknown_native_field_type_is_escaped_in_readable_wiki(tmp_path):
    with pikepdf.Pdf.open(io.BytesIO(form_pdf())) as pdf:
        pdf.Root.AcroForm.Fields[2].Kids[0].FT = pikepdf.Name("/<img src=x>")
        output = io.BytesIO()
        pdf.save(output)
    service, asset, _ = field_source(tmp_path, output.getvalue())
    root, _ = export(service, asset, tmp_path)
    records = [
        json.loads(line) for line in (root / "fields.jsonl").read_text().splitlines()
    ]
    hidden = next(r for r in records if r["qualified_name"] == "person.hidden")
    assert hidden["field_type"] == "/<img src=x>"
    note = (root / hidden["note"]).read_text()
    assert "<img src=x>" not in note
    assert "&lt;img src=x&gt;" in note
