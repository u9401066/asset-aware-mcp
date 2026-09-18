"""Every native reference family participates in verified derivation assertions."""

import pytest

from src.domain.native_derivation import NativeDerivation
from src.presentation.response_limits import format_limited_json_response
from tests.native_derivation_helpers import pair, read_ledger, record, service_at
from tests.native_docx_helpers import build_docx
from tests.native_pdf_helpers import build_pdf
from tests.native_pptx_helpers import build_presentation
from tests.native_workbook_helpers import _call


def endpoint(service, tmp_path, kind):
    if kind == "cell":
        asset, claim = pair(service)
        return asset, claim["target"]
    data = {
        "file": b"opaque",
        "docx": build_docx,
        "pdf": build_pdf,
        "pptx": build_presentation,
    }[kind]
    path = tmp_path / f"endpoint.{kind}"
    path.write_bytes(data() if callable(data) else data)
    asset = _call(service, op="register", source_path=str(path))["asset"]
    if kind == "file":
        return asset, asset["file_reference"]
    if kind == "docx":
        blocks = _call(service, op="read_docx", asset_id=asset["asset_id"])["blocks"]
        record = _call(
            service,
            op="read_docx_block",
            asset_id=asset["asset_id"],
            block_id=blocks[0]["id"],
        )["block"]
    elif kind == "pdf":
        pages = _call(service, op="read_pdf", asset_id=asset["asset_id"])["pages"]
        record = _call(
            service,
            op="read_pdf_page",
            asset_id=asset["asset_id"],
            pdf_locator=pages[0]["locator"],
        )["page"]
    else:
        shapes = _call(service, op="read_pptx", asset_id=asset["asset_id"])["shapes"]
        record = _call(
            service,
            op="read_pptx_shape",
            asset_id=asset["asset_id"],
            pptx_locator=shapes[0]["locator"],
        )["shape"]
    return asset, record["evidence"]


@pytest.mark.parametrize("kind", ["file", "cell", "docx", "pdf", "pptx"])
def test_target_and_source_endpoint_verifiers(tmp_path, kind):
    service = service_at(tmp_path)
    target, ref = endpoint(service, tmp_path, kind)
    other, claim = pair(service)
    claim["target"] = ref
    result = record(service, target, claim)
    proof = _call(
        service,
        op="verify_derivation",
        asset_id=target["asset_id"],
        derivation_id=result["derivation_id"],
    )
    assert proof["references_valid"]
    reverse = {**claim, "target": other["file_reference"], "sources": [ref]}
    result = record(service, other, reverse)
    assert _call(
        service,
        op="verify_derivation",
        asset_id=other["asset_id"],
        derivation_id=result["derivation_id"],
    )["references_valid"]


def test_large_review_and_multiple_sources_remain_retrievable(tmp_path):
    service = service_at(tmp_path)
    target, claim = pair(service)
    sources = [
        service.repository.create(
            f"source-{i}.bin", bytes([i]), "bin", "application/octet-stream"
        )
        for i in range(64)
    ]
    claim["sources"] = [
        _call(service, op="inspect", asset_id=a.asset_id)["asset"]["file_reference"]
        for a in sources
    ]
    claim["review"]["notes"] = "\x01" * 4096
    result = record(service, target, claim)
    read, _ = read_ledger(service, target["asset_id"], 4000)
    assert read["events"][0]["derivation"]["review"]["notes"] == "\x01" * 4096
    checked, offset = [], 0
    while True:
        proof = _call(
            service,
            op="verify_derivation",
            asset_id=target["asset_id"],
            derivation_id=result["derivation_id"],
            derivations_sha256=result["derivations_sha256"],
            offset=offset,
            limit=1000,
        )
        assert "response_truncated" not in format_limited_json_response(
            title="Proof", payload=proof
        )
        assert proof["references_valid"]
        checked.extend(proof["sources"])
        if proof["next_offset"] is None:
            break
        offset = proof["next_offset"]
    assert len(checked) == 64
    assert len(NativeDerivation.model_validate(claim).sources) == 64
