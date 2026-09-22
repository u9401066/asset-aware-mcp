"""ODS logical identity, compressed evidence, source guards and portable citations."""

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from src.application.csl_citation_service import CslCitationService
from src.application.native_document_service import NativeDocumentService
from src.application.native_schema import request_schema
from src.domain.csl_citations import CslDocument
from src.domain.native_assets import NativeDocumentRequest, NativeEditResult
from src.infrastructure.csl_processor import NodeCslProcessor
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_derivation_store import FileNativeDerivationRepository
from src.infrastructure.native_ods import NativeODSFileAdapter
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from src.presentation.response_limits import format_limited_json_response
from tests.native_derivation_helpers import record
from tests.native_ods_helpers import fixture, locator
from tests.native_workbook_helpers import _call
from tests.unit.test_csl_processor import document
from tests.unit.test_native_ods_dependencies import source as dependency_source


def service_at(root):
    repository = FileNativeAssetRepository(root)
    return NativeDocumentService(
        repository,
        SpreadsheetFileAdapter(),
        FileNativeWikiPublisher((root,)),
        derivations=FileNativeDerivationRepository(root, repository),
        ods=NativeODSFileAdapter(),
    )


@pytest.fixture
def service(tmp_path):
    return service_at(tmp_path / "store")


def complete(service, **request):
    chunks, offset, sha = [], 0, None
    while True:
        args = {"ods_text_sha256": sha} if sha else {}
        response = _call(
            service, **request, text_offset=offset, text_limit=4000, **args
        )
        assert "response_truncated" not in format_limited_json_response(
            title="ODS", payload=response
        )
        sha = sha or response["text_sha256"]
        assert response["text_sha256"] == sha
        assert response["excerpt_char_range"][0] == offset
        chunks.append(response["text_excerpt"])
        if response["next_text_offset"] is None:
            break
        offset = response["next_text_offset"]
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == sha
    return json.loads(text)


def cell(service, asset, row=0, column=0, name="Sheet1", index=0):
    return complete(
        service,
        op="read_ods_cell",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        ods_locator=locator(row, column, name, index).model_dump(),
    )["cell"]


def update(service, asset, ref, value="new", kind="string"):
    return _call(
        service,
        op="update_ods",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        ods_update={
            "cells": [
                {
                    "reference": ref,
                    "value": {"kind": kind, "value": value},
                    "display_policy": "replace_paragraphs_preserve_cell_style",
                }
            ]
        },
    )


def create(service):
    return _call(service, op="create_ods", ods_create={})["asset"]


def test_rename_dependencies_receipt_refs_and_wiki_survive_restart(service, tmp_path):
    source = tmp_path / "dependencies.ods"
    source.write_bytes(dependency_source().package.original)
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    asset = _call(service, op="register", source_path=str(source))["asset"]
    old_ref = cell(service, asset)["evidence"]
    request = {
        "op": "read_ods_dependencies",
        "asset_id": asset["asset_id"],
        "revision": asset["revision"],
    }
    inventory = complete(service, **request)
    assert inventory["sheets"] == ["Sheet1"] and len(inventory["dependencies"]) > 10
    wiki_request = {
        "op": "export_wiki",
        "asset_id": asset["asset_id"],
        "revision": asset["revision"],
        "output_dir": str(tmp_path / "wiki"),
    }
    old_wiki = Path(_call(service, **wiki_request)["output_dir"])
    old_files = {p.name: p.read_bytes() for p in old_wiki.iterdir()}
    rename = {
        "op": "rename_ods_table",
        "asset_id": asset["asset_id"],
        "expected_revision": asset["revision"],
        "ods_table_rename": {
            "table_index": 0,
            "table_name": "Sheet1",
            "new_name": "New 中文 O'Brien",
            "dependencies_sha256": inventory["inventory_sha256"],
        },
    }
    Draft202012Validator(request_schema("rename_ods_table")).validate(rename)
    changed = _call(service, **rename)
    assert changed["new_revision_created"] and not changed["source_written"]
    current = changed["asset"]
    receipt = complete(service, **changed["review_request"])["operation_result"]
    assert receipt["changes"][0]["operation"] == "rename_ods_table"
    assert "literal_and_dynamic_formula_references" in receipt["review_required"]
    new_inventory = complete(service, **changed["dependencies_request"])
    assert new_inventory["sheets"] == ["New 中文 O'Brien"]
    assert new_inventory["inventory_sha256"] != inventory["inventory_sha256"]
    new_ref = cell(service, current, name="New 中文 O'Brien")["evidence"]
    assert _call(service, op="verify", reference=new_ref)["valid"]
    old_verified = _call(service, op="verify", reference=old_ref)
    assert old_verified["valid"] and not old_verified["is_current_managed_revision"]
    before_failed = service.repository.load(asset["asset_id"]).model_dump()
    with pytest.raises(ValueError, match="stale"):
        _call(service, **rename)
    with pytest.raises(ValueError, match="inventory changed"):
        _call(
            service,
            **{
                **rename,
                "expected_revision": current["revision"],
                "ods_table_rename": {
                    **rename["ods_table_rename"],
                    "table_name": "New 中文 O'Brien",
                },
            },
        )
    assert service.repository.load(asset["asset_id"]).model_dump() == before_failed
    noop = _call(
        service,
        **{
            **rename,
            "expected_revision": current["revision"],
            "ods_table_rename": {
                **rename["ods_table_rename"],
                "table_name": "New 中文 O'Brien",
                "dependencies_sha256": new_inventory["inventory_sha256"],
            },
        },
    )
    assert not noop["new_revision_created"] and noop["asset"]["revision_count"] == 2
    new_wiki = Path(
        _call(service, **{**wiki_request, "revision": current["revision"]})[
            "output_dir"
        ]
    )
    assert new_wiki != old_wiki
    assert json.loads((new_wiki / "operation-result.json").read_text()) == receipt
    manifest = json.loads((new_wiki / "manifest.json").read_text())
    assert (
        new_wiki / manifest["source_attachment"]
    ).read_bytes() == service.repository.read(asset["asset_id"])
    restored = service_at(tmp_path / "store")
    assert complete(restored, **request) == inventory
    assert complete(restored, **changed["dependencies_request"]) == new_inventory
    assert (
        complete(restored, **changed["review_request"])["operation_result"] == receipt
    )
    assert _call(restored, op="verify", reference=old_ref)["valid"]
    assert _call(restored, **wiki_request)["reused"]
    assert old_files == {p.name: p.read_bytes() for p in old_wiki.iterdir()}
    assert (source.read_bytes(), source.stat().st_mtime_ns) == (original, mtime)


def test_unresolved_rename_never_commits_and_archive_still_guards(service, tmp_path):
    source = tmp_path / "unknown.ods"
    source.write_bytes(
        dependency_source(formula="unknown:=[Sheet1.A1]").package.original
    )
    asset = _call(service, op="register", source_path=str(source))["asset"]
    inventory = complete(
        service,
        op="read_ods_dependencies",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
    )
    args = {
        "op": "rename_ods_table",
        "asset_id": asset["asset_id"],
        "expected_revision": asset["revision"],
        "ods_table_rename": {
            "table_index": 0,
            "table_name": "Sheet1",
            "new_name": "Next",
            "dependencies_sha256": inventory["inventory_sha256"],
        },
    }
    before = service.repository.load(asset["asset_id"]).model_dump()
    with pytest.raises(ValueError, match="unresolved"):
        _call(service, **args)
    assert service.repository.load(asset["asset_id"]).model_dump() == before
    _call(
        service,
        op="archive",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
    )
    with pytest.raises(ValueError, match="Archived"):
        _call(service, **args)


def test_create_full_unicode_pages_noop_history_and_clear(service, tmp_path):
    asset = create(service)
    assert asset["capabilities"]["read_ods"] and asset["capabilities"]["edit_ods"]
    original = cell(service, asset)
    text = '中文"\\\n' * 2500
    edited = update(service, asset, original["evidence"], text)
    current = edited["asset"]
    value = cell(service, current)
    assert value["value_attributes"]["string-value"] == text
    assert value["display_paragraphs"] == [text]
    full = complete(service, **edited["review_request"])
    assert full["operation_result"]["changes"][0]["before"] == {
        k: v for k, v in original.items() if k != "evidence"
    }
    assert (
        "all_original_logical_cell_references_verified"
        in full["operation_result"]["checks"]
    )
    assert _call(service, op="verify", reference=value["evidence"])["valid"]
    old = _call(service, op="verify", reference=original["evidence"])
    assert old["valid"] and not old["is_current_managed_revision"]
    noop = update(service, current, value["evidence"], text)
    assert (
        not noop["new_revision_created"] and noop["operation_result"]["changes"] == []
    )
    assert noop["asset"]["revision_count"] == 2
    cleared = update(service, current, value["evidence"], None, "blank")["asset"]
    assert cell(service, cleared)["display_paragraphs"] == []
    restored = service_at(tmp_path / "store")
    assert complete(restored, **edited["review_request"]) == full
    assert _call(restored, op="verify", reference=value["evidence"])["valid"]


@pytest.mark.parametrize(
    "corruption", ["hash", "asset", "revision", "name", "index", "row", "column"]
)
def test_full_reference_tampering_rejected_before_mutation(service, corruption):
    asset = create(service)
    ref = deepcopy(cell(service, asset)["evidence"])
    if corruption == "hash":
        ref["value_sha256"] = "0" * 64
    elif corruption == "asset":
        ref["asset_id"] = create(service)["asset_id"]
    elif corruption == "revision":
        ref["revision"] = "0" * 64
    else:
        key = {"name": "table_name", "index": "table_index"}.get(corruption, corruption)
        ref["locator"][key] = "wrong" if key == "table_name" else 1
    before = service.repository.load(asset["asset_id"]).model_dump()
    with pytest.raises(ValueError):
        update(service, asset, ref)
    assert service.repository.load(asset["asset_id"]).model_dump() == before


def test_absent_and_repeated_logical_cells_have_distinct_refs_and_scoped_edit(
    service, tmp_path
):
    source = tmp_path / "compressed.ods"
    source.write_bytes(
        fixture(
            '<table:table-row table:number-rows-repeated="1000"><table:table-cell table:number-columns-repeated="300" office:value-type="string" office:string-value="old"><text:p>old</text:p></table:table-cell></table:table-row>'
        )
    )
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    asset = _call(service, op="register", source_path=str(source))["asset"]
    anchor, inside, absent = (
        cell(service, asset),
        cell(service, asset, 999, 299),
        cell(service, asset, 1001, 302),
    )
    assert len({x["evidence"]["value_sha256"] for x in [anchor, inside, absent]}) == 3
    assert not absent["present"] and absent["native_xml"] is None
    for value in [anchor, inside, absent]:
        assert _call(service, op="verify", reference=value["evidence"])["valid"]
    first = update(service, asset, inside["evidence"])["asset"]
    assert cell(service, first)["display_paragraphs"] == ["old"]
    assert cell(service, first, 999, 299)["display_paragraphs"] == ["new"]
    with pytest.raises(ValueError, match="stale"):
        update(service, asset, absent["evidence"])
    missing = cell(service, first, 1001, 302)
    last = update(service, first, missing["evidence"], "007")["asset"]
    assert cell(service, last, 1001, 302)["value_type"] == "string"
    assert (source.read_bytes(), source.stat().st_mtime_ns) == (original, mtime)
    assert service.repository.read(asset["asset_id"], asset["revision"]) == original


def test_paging_guards_duplicate_edits_archive_wrong_format_and_disabled_adapter(
    service, tmp_path
):
    asset = create(service)
    req = {
        "op": "read_ods",
        "asset_id": asset["asset_id"],
        "revision": asset["revision"],
    }
    with pytest.raises(ValueError, match="requires ods_text_sha256"):
        NativeDocumentRequest(**req, text_offset=1)
    with pytest.raises(ValueError, match="representation changed"):
        _call(service, **req, ods_text_sha256="0" * 64)
    ref = cell(service, asset)["evidence"]
    edit = {
        "reference": ref,
        "value": {"value": "x"},
        "display_policy": "replace_paragraphs_preserve_cell_style",
    }
    with pytest.raises(ValueError, match="targeted once"):
        _call(
            service,
            op="update_ods",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            ods_update={"cells": [edit, edit]},
        )
    with pytest.raises(ValueError, match="not configured"):
        _call(
            NativeDocumentService(service.repository, SpreadsheetFileAdapter()), **req
        )
    other = service.repository.create("bad.txt", b"test", "txt", "text/plain")
    with pytest.raises(ValueError, match="require an ODS"):
        _call(service, op="read_ods", asset_id=other.asset_id, revision=other.revision)
    _call(
        service,
        op="archive",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
    )
    with pytest.raises(ValueError, match="Archived"):
        update(service, asset, ref)
    assert _call(service, op="verify", reference=ref)["valid"]


@pytest.mark.parametrize(
    "operation", ["read_ods", "read_ods_cell", "read_ods_dependencies"]
)
def test_ods_inspection_and_schema_advertise_real_reader_and_continuation_guards(
    service, operation
):
    asset = create(service)
    inspected = _call(service, op="inspect", asset_id=asset["asset_id"])
    assert inspected["content"]["read_operation"] == "read_ods"
    assert inspected["content"]["representation"] == "ods_package"
    assert inspected["asset"]["capabilities"]["edit_constraints"]
    fields = {
        "op": operation,
        "asset_id": asset["asset_id"],
        "revision": asset["revision"],
    }
    if operation == "read_ods_cell":
        fields["ods_locator"] = locator().model_dump()
    validator = Draft202012Validator(request_schema(operation))
    validator.validate(fields)
    with pytest.raises(ValidationError):
        validator.validate({**fields, "text_offset": 1})
    with pytest.raises(ValidationError):
        validator.validate({**fields, "text_offset": 1, "ods_text_sha256": None})
    validator.validate({**fields, "text_offset": 1, "ods_text_sha256": "1" * 64})


def test_wiki_compressed_ranges_exact_derivation_endpoints_and_citation_locators(
    service, tmp_path
):
    source = tmp_path / "wiki.ods"
    source.write_bytes(
        fixture(
            '<table:table-row table:number-rows-repeated="1000"><table:table-cell table:number-columns-repeated="300" office:value-type="string"><text:p>evidence 中文</text:p></table:table-cell></table:table-row>'
        )
    )
    asset = _call(service, op="register", source_path=str(source))["asset"]
    endpoint = cell(service, asset, 999, 299)["evidence"]
    missing = cell(service, asset, 1001, 302)["evidence"]
    record(
        service,
        asset,
        {
            "target": endpoint,
            "sources": [missing],
            "agent": "test",
            "activity": "Exact missing cell observation",
        },
    )
    selection = _call(
        service,
        op="read_selection",
        reference=endpoint,
        selection={
            "pointer": "/display_paragraphs/0",
            "char_range": {"start": 9, "end": 11},
        },
    )
    assert _call(service, op="verify", reference=selection["evidence"])["valid"]
    request = {
        "op": "export_wiki",
        "asset_id": asset["asset_id"],
        "revision": asset["revision"],
        "output_dir": str(tmp_path / "wiki"),
        "citation_contract": {
            "inline_template": "{source_id} / {locator}",
            "reference_template": "{title} {locator}",
        },
    }
    result = _call(service, **request)
    root = Path(result["output_dir"])
    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["physical_range_count"] == 1
    assert (root / manifest["source_attachment"]).read_bytes() == source.read_bytes()
    entry = json.loads((root / "records.jsonl").read_text())
    assert entry["reference_scope"] == "logical_anchor_only"
    assert entry["repetition"]["row_count"] == 1000
    assert (
        "content.xml, table index 0 (zero-based) 'Sheet1', row 1, column 1"
        in entry["citation_presentation"]["inline"]
    )
    assert len(manifest["derivations"]["ods_cell_records"]) == 2
    for retained in manifest["derivations"]["ods_cell_records"].values():
        exact = json.loads((root / retained["record_file"]).read_text())
        assert exact["evidence"] == retained["reference"]
        assert _call(service, op="verify", reference=exact["evidence"])["valid"]
    for name, expected in manifest["files"].items():
        data = (root / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected["sha256"]
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    assert _call(service_at(tmp_path / "store"), **request)["reused"]
    assert {p.name: p.read_bytes() for p in root.iterdir()} == before


def test_csl_accepts_exact_ods_source_and_preserves_native_attachment(
    service, tmp_path
):
    if not shutil.which("node"):
        pytest.skip("CSL rendering requires optional Node.js >=20")
    asset = create(service)
    reference = cell(service, asset)["evidence"]
    raw = document().model_dump()
    raw["sources"] = {"ods": reference}
    raw["clusters"][0]["cites"][0]["source_keys"] = ["ods"]
    citations = CslCitationService(
        NodeCslProcessor(),
        service.evidence,
        FileNativeWikiPublisher((tmp_path / "store",)),
    )
    result, publication = citations.render(
        CslDocument.model_validate(raw), str(tmp_path / "citations")
    )
    source = result["sources"]["ods"]
    assert (
        source["reference"] == reference and source["semantic_support"] == "not_checked"
    )
    assert source["attachment"]["name"].endswith(".ods")
    assert (
        Path(publication["output_dir"]) / source["attachment"]["name"]
    ).read_bytes() == service.repository.read(asset["asset_id"])


def test_equal_file_revision_with_distinct_receipt_gets_distinct_wiki(
    service, tmp_path
):
    asset = create(service)
    req = {
        "op": "export_wiki",
        "asset_id": asset["asset_id"],
        "revision": asset["revision"],
        "output_dir": str(tmp_path / "wiki"),
    }
    old = _call(service, **req)
    original = service.repository.read(asset["asset_id"])
    changed = update(service, asset, cell(service, asset)["evidence"])["asset"]
    report = NativeEditResult(
        changed_parts=["content.xml"],
        preserved_parts=2,
        changes=[{"operation": "restore_fixture_bytes"}],
        checks=["test"],
    )
    service.repository.commit(asset["asset_id"], changed["revision"], original, report)
    new = _call(service, **req)
    assert old["output_dir"] != new["output_dir"]
    assert (
        json.loads((Path(new["output_dir"]) / "operation-result.json").read_text())
        == report.model_dump()
    )
    assert (
        json.loads((Path(old["output_dir"]) / "operation-result.json").read_text())
        != report.model_dump()
    )
