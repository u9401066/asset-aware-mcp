"""Native CSV boundaries, historical evidence, source handoff and portable Wiki."""

import csv
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from src.application.native_document_service import NativeDocumentService
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_delimited import NativeDelimited
from src.infrastructure.native_derivation_store import FileNativeDerivationRepository
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from src.presentation.response_limits import format_limited_json_response
from tests.native_derivation_helpers import read_ledger, record
from tests.native_workbook_helpers import _call


@pytest.fixture
def service(tmp_path):
    limit = csv.field_size_limit()
    root = tmp_path / "store"
    repository = FileNativeAssetRepository(root)
    try:
        yield NativeDocumentService(
            repository,
            SpreadsheetFileAdapter(),
            FileNativeWikiPublisher((root,)),
            derivations=FileNativeDerivationRepository(root, repository),
            delimited=NativeDelimited(),
        )
    finally:
        csv.field_size_limit(limit)


def complete(service, **request):
    chunks, offset, sha = [], 0, None
    while True:
        response = _call(service, **request, text_offset=offset, text_limit=4000)
        assert "response_truncated" not in format_limited_json_response(
            title="CSV", payload=response
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


def cell(service, asset, row=0, column=0, **kwargs):
    return complete(
        service,
        op="read_delimited_cell",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        delimited_row=row,
        delimited_column=column,
        **kwargs,
    )


def update(service, asset, **change):
    return _call(
        service,
        op="update_delimited",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        delimited_update=change,
    )


def test_complete_large_field_noop_and_tampered_foreign_stale_references(
    service, tmp_path
):
    value = '中文"\\\n\x00' * 1500
    created = _call(
        service,
        op="create_delimited",
        delimited_create={"rows": [[value, "007"], [], ["tail"]]},
    )
    asset = created["asset"]
    assert (
        asset["capabilities"]["read_delimited"]
        and asset["capabilities"]["edit_delimited"]
    )
    assert complete(service, **created["review_request"])["row_lengths"] == [2, 0, 1]
    field = cell(service, asset)
    assert field["value"] == value
    assert _call(service, op="verify", reference=field["evidence"])["valid"]
    before = service.repository.read(asset["asset_id"])
    noop = update(
        service,
        asset,
        operation="set_cells",
        cells=[{"reference": field["evidence"], "value": value}],
    )
    assert not noop["new_revision_created"]
    assert noop["operation_result"]["changes"][0]["patches"] == []
    assert len(service.repository.load(asset["asset_id"]).history) == 1
    other = _call(
        service,
        op="create_delimited",
        delimited_create={"rows": [[value, "007"], [], ["tail"]]},
    )["asset"]
    assert other["revision"] == asset["revision"]
    foreign = cell(service, other)["evidence"]
    for ref in (foreign, {**field["evidence"], "value_sha256": "0" * 64}):
        with pytest.raises(ValueError):
            update(
                service,
                asset,
                operation="set_cells",
                cells=[{"reference": ref, "value": "wrong"}],
            )
    assert service.repository.read(asset["asset_id"]) == before
    changed = update(
        service,
        asset,
        operation="set_cells",
        cells=[{"reference": field["evidence"], "value": "new"}],
    )
    assert cell(service, changed["asset"])["value"] == "new"
    proof = _call(service, op="verify", reference=field["evidence"])
    assert proof["valid"] and not proof["is_current_managed_revision"]
    with pytest.raises(ValueError, match="stale"):
        update(service, asset, operation="delete_rows", index=0, count=1)
    archived = _call(
        service,
        op="archive",
        asset_id=asset["asset_id"],
        expected_revision=changed["asset"]["revision"],
    )["asset"]
    assert not archived["capabilities"]["edit_delimited"]
    with pytest.raises(ValueError, match="Archived"):
        update(service, archived, operation="delete_rows", index=0, count=1)
    assert cell(service, asset)["value"] == value


def test_source_refresh_writeback_backups_and_exact_native_splices(service, tmp_path):
    source = tmp_path / "human.csv"
    original = b'"code",note\r\n"007","line\nnext"\n'
    source.write_bytes(original)
    original_mtime = source.stat().st_mtime_ns
    asset = _call(service, op="register", source_path=str(source))["asset"]
    old = cell(service, asset, 1)["evidence"]
    changed = update(
        service,
        asset,
        operation="set_cells",
        cells=[{"reference": old, "value": "008"}],
    )["asset"]
    expected = original.replace(b'"007"', b'"008"')
    assert service.repository.read(asset["asset_id"]) == expected
    assert (
        source.read_bytes() == original and source.stat().st_mtime_ns == original_mtime
    )
    published = tmp_path / "out.csv"
    _call(
        service,
        op="publish",
        asset_id=asset["asset_id"],
        expected_revision=changed["revision"],
        output_path=str(published),
    )
    assert published.read_bytes() == expected
    # A human edit cannot silently discard the staged revision.
    external = original.replace(b'"007"', b'"009"')
    source.write_bytes(external)
    with pytest.raises(ValueError):
        _call(
            service,
            op="refresh",
            asset_id=asset["asset_id"],
            expected_revision=changed["revision"],
            expected_source_sha256=asset["revision"],
        )
    with pytest.raises(ValueError):
        _call(
            service,
            op="writeback",
            asset_id=asset["asset_id"],
            expected_revision=changed["revision"],
            expected_source_sha256=asset["revision"],
        )
    assert source.read_bytes() == external
    # A separately registered human version can be refreshed before managed edits.
    human = _call(service, op="register", source_path=str(source))["asset"]
    source.write_bytes(original)
    refreshed = _call(
        service,
        op="refresh",
        asset_id=human["asset_id"],
        expected_revision=human["revision"],
        expected_source_sha256=human["revision"],
    )["asset"]
    assert cell(service, refreshed, 1)["value"] == "007"
    ref = cell(service, refreshed, 1)["evidence"]
    corrected = update(
        service,
        refreshed,
        operation="set_cells",
        cells=[{"reference": ref, "value": "008"}],
    )["asset"]
    result = _call(
        service,
        op="writeback",
        asset_id=human["asset_id"],
        expected_revision=corrected["revision"],
        expected_source_sha256=refreshed["revision"],
    )
    assert source.read_bytes() == expected
    assert Path(result["backup_path"]).read_bytes() == original


def test_ragged_structure_receipts_and_repeated_revision_do_not_relocate_evidence(
    service,
):
    created = _call(
        service,
        op="create_delimited",
        delimited_create={
            "name": "ragged.tsv",
            "rows": [["007", "x"], [], ["tail"]],
            "final_separator": False,
        },
    )
    asset = created["asset"]
    original = service.repository.read(asset["asset_id"])
    ref = cell(service, asset)["evidence"]
    inserted = update(
        service,
        asset,
        operation="insert_rows",
        index=0,
        rows=[["前", "頭"]],
        record_separator="\n",
    )
    assert cell(service, inserted["asset"], 1)["value"] == "007"
    receipt = complete(service, **inserted["review_request"])["operation_result"]
    assert receipt["changes"][0]["patches"][0]["byte_range"] == [0, 0]
    removed = update(
        service, inserted["asset"], operation="delete_rows", index=0, count=1
    )
    assert removed["asset"]["revision"] == asset["revision"]
    assert removed["asset"]["revision_count"] == 3
    assert service.repository.read(asset["asset_id"]) == original
    assert (
        complete(service, **removed["review_request"])["operation_result"]["changes"][
            0
        ]["operation"]
        == "delete_rows"
    )
    assert _call(service, op="verify", reference=ref)["valid"]
    with pytest.raises(ValueError):
        update(
            service,
            removed["asset"],
            operation="insert_column",
            index=1,
            values=["a", "b", "c"],
        )
    column = update(
        service,
        removed["asset"],
        operation="insert_column",
        index=0,
        values=["a", "b", "c"],
    )
    assert cell(service, column["asset"], 1)["value"] == "b"
    assert complete(service, **column["review_request"])["row_lengths"] == [3, 1, 2]


def test_dialect_bound_wiki_selection_derivation_and_curated_notes(service, tmp_path):
    source = tmp_path / "ambiguous.csv"
    source.write_bytes(b"a;b,c\r\n007;x,y\n")
    asset = _call(service, op="register", source_path=str(source))["asset"]
    first = cell(service, asset)
    semi = {"delimiter": ";"}
    field = cell(service, asset, 1, delimited_dialect=semi)
    assert field["value"] == "007"
    selected = complete(
        service,
        op="read_selection",
        reference=field["evidence"],
        selection={"pointer": "/value", "char_range": {"start": 1, "end": 3}},
    )
    assert selected["value"] == "07"
    assert _call(service, op="verify", reference=selected["evidence"])["valid"]
    tampered = deepcopy(field["evidence"])
    tampered["dialect"]["delimiter"] = ","
    assert not _call(service, op="verify", reference=tampered)["valid"]
    claim = {
        "target": field["evidence"],
        "sources": [first["evidence"]],
        "agent": "unit fixture",
        "activity": "Explicit interpretation test",
        "review": {"notes": "No semantic claim"},
    }
    record(service, asset, claim)
    _, sha = read_ledger(service, asset["asset_id"])
    root = tmp_path / "wiki"
    root.mkdir()
    curated = root / "human.md"
    curated.write_text("curated [[notes]]")
    options = {
        "op": "export_wiki",
        "asset_id": asset["asset_id"],
        "revision": asset["revision"],
        "output_dir": str(root),
        "derivations_sha256": sha,
        "citation_contract": {
            "inline_template": "{source_id} :: {locator}",
            "reference_template": "{title}",
        },
    }
    default = _call(service, **options)
    other = _call(service, **options, delimited_dialect=semi)
    assert default["output_dir"] != other["output_dir"]
    snapshot = Path(other["output_dir"])
    manifest = json.loads((snapshot / "manifest.json").read_text())
    assert manifest["dialect"]["delimiter"] == ";"
    assert (
        snapshot / manifest["source_attachment"]
    ).read_bytes() == source.read_bytes()
    records = [
        json.loads(line)
        for line in (snapshot / "records.jsonl").read_text().splitlines()
    ]
    target = next(r for r in records if r["evidence"] == field["evidence"])
    assert "row 2, column 1; bytes [" in target["citation_presentation"]["inline"]
    before = {p.name: p.read_bytes() for p in snapshot.iterdir()}
    assert _call(service, **options, delimited_dialect=semi)["reused"]
    assert before == {p.name: p.read_bytes() for p in snapshot.iterdir()}
    assert curated.read_text() == "curated [[notes]]"
    changed = _call(
        service,
        op="update_delimited",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        delimited_dialect=semi,
        delimited_update={
            "operation": "set_cells",
            "cells": [{"reference": field["evidence"], "value": "008"}],
        },
    )["asset"]
    newest = _call(
        service, **{**options, "revision": changed["revision"]}, delimited_dialect=semi
    )
    manifest = json.loads((Path(newest["output_dir"]) / "manifest.json").read_text())
    assert manifest["derivations"]["active_ids_for_revision"] == []
    assert _call(service, op="verify", reference=field["evidence"])["valid"]
