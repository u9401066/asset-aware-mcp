"""Failure and concurrency boundaries for managed DOCX revisions."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from lxml import etree

from src.application.dfm_integrity import (
    DfmIntegrityChecker,
    IntegrityIssue,
    IntegrityReport,
)
from src.application.native_document_contract import native_document_contract
from src.domain.native_assets import NativeDocumentRequest
from src.domain.native_docx import NativeDocxEdit
from src.infrastructure import native_docx_workspace
from src.infrastructure.native_ooxml import DOC_REL_NS, REL_NS, NativeOOXMLPackage
from src.presentation.response_limits import format_limited_json_response
from tests.native_docx_helpers import call, read_dfm, replace_parts
from tests.native_docx_helpers import native_docx as native_docx


@pytest.mark.parametrize("stage", ["pre_save", "post_save"])
def test_existing_dfm_integrity_failure_prevents_commit_and_cleans_workspace(
    native_docx, tmp_path: Path, monkeypatch, stage: str
) -> None:
    service, asset, source = native_docx
    original = source.read_bytes()
    text = read_dfm(service, asset).replace("原始段落", "修訂段落")
    private = tmp_path / "private"
    private.mkdir()
    monkeypatch.setattr(
        native_docx_workspace,
        "TemporaryDirectory",
        partial(TemporaryDirectory, dir=private),
    )

    def reject(*args, **kwargs):
        report = IntegrityReport()
        report.add(
            IntegrityIssue("error", stage, "Detected unexpected document mutation")
        )
        return report

    monkeypatch.setattr(DfmIntegrityChecker, f"check_{stage}", reject)
    with pytest.raises(ValueError, match="integrity check failed"):
        call(
            service,
            op="update_docx",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            docx_edit={"dfm_text": text},
        )
    assert service.repository.load(asset["asset_id"]).revision == asset["revision"]
    assert source.read_bytes() == original
    assert list(private.iterdir()) == []


def test_concurrent_managed_edit_cannot_be_overwritten_after_dfm_validation(
    native_docx, monkeypatch
) -> None:
    service, asset, _ = native_docx
    bridge = service.docx
    assert bridge is not None
    edit = bridge.edit
    text = read_dfm(service, asset)
    competing_revision = None

    def interleave(data, asset_id, revision, request):
        nonlocal competing_revision
        candidate = edit(data, asset_id, revision, request)
        other, report, _ = edit(
            data,
            asset_id,
            revision,
            NativeDocxEdit(dfm_text=text.replace("原始段落", "另一作者")),
        )
        competing_revision = service.repository.commit(
            asset_id, revision, other, report
        ).revision
        return candidate

    monkeypatch.setattr(bridge, "edit", interleave)
    with pytest.raises(ValueError, match="Stale"):
        call(
            service,
            op="update_docx",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            docx_edit={"dfm_text": text.replace("原始段落", "延遲回覆")},
        )
    assert service.repository.load(asset["asset_id"]).revision == competing_revision
    current = dict(asset, revision=competing_revision)
    assert "另一作者" in read_dfm(service, current)
    assert len(service.repository.load(asset["asset_id"]).history) == 2


def test_native_docx_table_shape_change_reuses_existing_guard(native_docx) -> None:
    service, asset, _ = native_docx
    dfm = read_dfm(service, asset)
    changed = dfm.replace("| Drug | Old value |", "| Drug | Old value | Extra |")
    assert changed != dfm
    with pytest.raises(ValueError, match=r"integrity|structural"):
        call(
            service,
            op="update_docx",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            docx_edit={"dfm_text": changed},
        )
    assert service.repository.load(asset["asset_id"]).revision == asset["revision"]


@pytest.mark.parametrize(
    "payload",
    [
        {"op": "read_docx", "asset_id": "file_" + "a" * 32, "sheet": "Sheet1"},
        {
            "op": "update_docx",
            "asset_id": "file_" + "a" * 32,
            "expected_revision": "a" * 64,
        },
        {
            "op": "read_cell",
            "asset_id": "file_" + "a" * 32,
            "sheet": "S",
            "cell": "A1",
            "docx_edit": {"dfm_text": "wrong"},
        },
    ],
)
def test_native_docx_fields_do_not_leak_across_operations(payload: dict) -> None:
    with pytest.raises(ValueError):
        NativeDocumentRequest.model_validate(payload)


def test_extended_native_contract_fits_default_response_without_losing_input_fields(
    monkeypatch,
) -> None:
    monkeypatch.delenv("ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS", raising=False)
    contract = native_document_contract(docx_enabled=True)
    response = format_limited_json_response(title="Native contract", payload=contract)
    assert "response_truncated" not in response
    assert "update_docx" in response["schema"]["properties"]["op"]["enum"]
    definitions = response["schema"]["$defs"]
    assert "title" in definitions["CitationMetadata"]["properties"]
    assert definitions["NativeDocxEdit"]["properties"]["dfm_text"]["maxLength"] > 0


@pytest.mark.parametrize("kind", ["signature", "protection"])
def test_relocated_signature_or_protection_parts_are_not_bypassed(
    native_docx, kind: str
) -> None:
    service, _, source = native_docx
    package = NativeOOXMLPackage(source.read_bytes())
    if kind == "signature":
        part = "_rels/.rels"
        rels = package.xml(part)
        etree.SubElement(
            rels,
            f"{{{REL_NS}}}Relationship",
            Id="nativeSig",
            Type=f"{REL_NS}/digital-signature/origin",
            Target="signatures/origin",
        )
        replacements = {part: etree.tostring(rels), "signatures/origin": b""}
    else:
        part = "word/_rels/document.xml.rels"
        rels = package.xml(part)
        for item in rels:
            if item.get("Type") == f"{DOC_REL_NS}/settings":
                item.set("Target", "custom-settings.xml")
        settings = package.xml("word/settings.xml")
        etree.SubElement(
            settings, f"{{{native_docx_workspace.WORD_NS}}}documentProtection"
        )
        replacements = {
            part: etree.tostring(rels),
            "word/custom-settings.xml": etree.tostring(settings),
        }
    source.write_bytes(replace_parts(source.read_bytes(), replacements))
    asset = call(service, op="register", source_path=str(source))["asset"]
    with pytest.raises(ValueError, match=r"signed|Protected"):
        call(
            service,
            op="update_docx",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            docx_edit={"dfm_text": read_dfm(service, asset)},
        )
    assert service.repository.load(asset["asset_id"]).revision == asset["revision"]
