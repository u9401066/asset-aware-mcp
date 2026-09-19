"""Real native files, tampered references, historical revisions and portable wikis."""

import hashlib
import json
from copy import deepcopy

import pytest
from docx import Document

from src.presentation.response_limits import format_limited_json_response
from tests.native_derivation_helpers import pair, record, service_at
from tests.native_workbook_helpers import _call
from tests.unit.test_native_derivation_endpoints import endpoint
from tests.unit.test_native_derivation_wiki import export


def read(service, reference, selection=None, limit=100):
    chunks, offset, sha, evidence = [], 0, None, None
    while True:
        extra = {"selection": selection} if selection is not None else {}
        result = _call(
            service,
            op="read_selection",
            reference=reference,
            text_offset=offset,
            text_limit=limit,
            **extra,
        )
        assert "response_truncated" not in format_limited_json_response(
            title="Selection", payload=result
        )
        sha = sha or result["text_sha256"]
        evidence = evidence or result["evidence"]
        assert result["text_sha256"] == sha and result["evidence"] == evidence
        assert result["excerpt_char_range"][0] == offset
        assert not result["source_written"]
        chunks.append(result["text_excerpt"])
        if result["next_text_offset"] is None:
            break
        offset = result["next_text_offset"]
    data = "".join(chunks).encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == sha
    return json.loads(data)


@pytest.mark.parametrize("kind", ["cell", "docx", "pptx", "pdf"])
def test_complete_parent_read_selection_verify_and_tampering(tmp_path, kind):
    service = service_at(tmp_path)
    asset, parent = endpoint(service, tmp_path, kind)
    result = read(service, parent, limit=4000)
    assert "evidence" not in result["value"]
    assert result["parent"] == parent
    selected = read(service, parent, {"pointer": "/locator"}, limit=4000)
    assert selected["value"] == parent["locator"]
    ref = selected["evidence"]
    assert read(service, ref, limit=4000) == selected
    assert _call(service, op="verify", reference=ref)["valid"]
    with pytest.raises(ValueError, match="override"):
        read(service, ref, {})
    for nested in [False, True]:
        bad = deepcopy(ref)
        (bad["parent"] if nested else bad)["value_sha256"] = "f" * 64
        assert not _call(service, op="verify", reference=bad)["valid"]
        with pytest.raises(ValueError, match="integrity"):
            read(service, bad)
    _call(
        service,
        op="archive",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
    )
    assert _call(service, op="verify", reference=ref)["archived"]


def test_selection_history_derivations_wiki_and_exact_source(tmp_path):
    service = service_at(tmp_path)
    target, claim = pair(service)
    source, source_claim = pair(service)
    claim["target"] = read(service, claim["target"], {"pointer": "/value"})["evidence"]
    claim["sources"] = [
        read(
            service,
            source_claim["target"],
            {"pointer": "/value", "char_range": {"start": 0, "end": 3}},
        )["evidence"]
    ]
    result = record(service, target, claim)
    assert _call(
        service,
        op="verify_derivation",
        asset_id=target["asset_id"],
        derivation_id=result["derivation_id"],
    )["references_valid"]
    root, manifest = export(service, target, tmp_path)
    selections = manifest["derivations"]["selection_records"]
    assert len(selections) == 2
    for info in selections.values():
        saved = json.loads((root / info["record_file"]).read_text(encoding="utf-8"))
        assert saved == read(service, info["reference"])
        assert saved["value"] == "007"
    attached = next(iter(manifest["derivations"]["source_attachments"].values()))
    assert (root / attached["attachment"]).read_bytes() == service.repository.read(
        source["asset_id"], source["revision"]
    )
    old_files = {p.name: p.read_bytes() for p in root.iterdir()}
    _call(
        service,
        op="update",
        asset_id=target["asset_id"],
        expected_revision=target["revision"],
        edits=[{"sheet": "Sheet1", "cell": "A1", "value": "008"}],
    )
    proof = _call(service, op="verify", reference=claim["target"])
    assert proof["valid"] and not proof["is_current_managed_revision"]
    assert read(service, claim["target"])["value"] == "007"
    _, current = export(service, target, tmp_path)
    assert current["derivations"]["active_ids_for_revision"] == []
    assert "selection_records" not in current["derivations"]
    assert {p.name: p.read_bytes() for p in root.iterdir()} == old_files


def test_same_text_at_different_offsets_is_not_substitutable(tmp_path):
    service = service_at(tmp_path)
    asset = _call(
        service,
        op="create",
        workbook={"edits": [{"sheet": "Sheet1", "cell": "A1", "value": "007 007"}]},
    )["asset"]
    parent = _call(
        service, op="read_cell", asset_id=asset["asset_id"], sheet="Sheet1", cell="A1"
    )["cell"]["evidence"]
    ref = read(
        service, parent, {"pointer": "/value", "char_range": {"start": 0, "end": 3}}
    )["evidence"]
    ref["selector"]["char_range"] = {"start": 4, "end": 7}
    assert not _call(service, op="verify", reference=ref)["valid"]


def test_opaque_files_and_unconfigured_formats_fail(tmp_path):
    service = service_at(tmp_path)
    asset, _ = pair(service)
    with pytest.raises(ValueError, match="parsed native"):
        read(service, asset["file_reference"])
    _, ref = endpoint(service, tmp_path, "pdf")
    service.evidence.pdfs = None
    with pytest.raises(ValueError, match="configured"):
        read(service, ref)
    contract = _call(service, op="contract", for_op="read_selection")
    assert "read_selection" in contract["operations"]
    assert "read_selection" not in contract["formats"]["other"]


def test_escaped_long_content_pages_fit_transport(tmp_path):
    service = service_at(tmp_path)
    text = '\\"\t\n研😀' * 3000
    asset = _call(
        service,
        op="create",
        workbook={"edits": [{"sheet": "Sheet1", "cell": "A1", "value": text}]},
    )["asset"]
    parent = _call(
        service, op="read_cell", asset_id=asset["asset_id"], sheet="Sheet1", cell="A1"
    )["cell"]["evidence"]
    assert read(service, parent, {"pointer": "/value"}, limit=4000)["value"] == text


def test_docx_unicode_span_retains_parsed_context_and_exact_source(tmp_path):
    path = tmp_path / "unicode.docx"
    document = Document()
    document.add_paragraph("前研😀e\u0301後")
    document.save(path)
    original, mtime = path.read_bytes(), path.stat().st_mtime_ns
    service = service_at(tmp_path)
    asset = _call(service, op="register", source_path=str(path))["asset"]
    block = _call(service, op="read_docx", asset_id=asset["asset_id"])["blocks"][0]
    parent = _call(
        service, op="read_docx_block", asset_id=asset["asset_id"], block_id=block["id"]
    )["block"]["evidence"]
    selected = read(
        service,
        parent,
        {"pointer": "/representation/text", "char_range": {"start": 1, "end": 4}},
    )
    assert selected["value"] == "研😀e"
    assert selected["text_context"]["utf8_byte_range"] == [3, 11]
    assert selected["text_context"]["prefix"] == "前"
    assert selected["text_context"]["suffix"] == "\u0301後"
    assert _call(service, op="verify", reference=selected["evidence"])["valid"]
    assert path.read_bytes() == original and path.stat().st_mtime_ns == mtime
