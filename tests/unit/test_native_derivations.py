"""Derivation CRUD preserves pinned proofs and separates agent claims from integrity."""

from copy import deepcopy

import pytest

from src.domain.native_assets import NativeDocumentRequest
from tests.native_derivation_helpers import pair, read_ledger, record, service_at
from tests.native_workbook_helpers import _call


@pytest.fixture
def linked(tmp_path):
    service = service_at(tmp_path)
    asset, claim = pair(service)
    return service, asset, claim


def test_record_replace_retract_and_reload_keep_file_bytes(linked, tmp_path):
    service, asset, claim = linked
    before = service.repository.read(asset["asset_id"])
    first = record(service, asset, claim)
    assert not first["source_written"] and not first["native_file_written"]
    fixed = deepcopy(claim)
    fixed["supersedes"] = first["derivation_id"]
    fixed["review"] = {
        "semantic_accuracy": "failed",
        "notes": "Transcription requires correction",
    }
    second = record(service, asset, fixed, first["derivations_sha256"])
    proof = _call(
        service,
        op="verify_derivation",
        asset_id=asset["asset_id"],
        derivation_id=first["derivation_id"],
    )
    assert not proof["active"] and proof["references_valid"]
    proof = _call(
        service,
        op="verify_derivation",
        asset_id=asset["asset_id"],
        derivation_id=second["derivation_id"],
    )
    assert proof["active"] and proof["references_valid"]
    assert proof["agent_review"]["semantic_accuracy"] == "failed"
    _call(
        service,
        op="retract_derivation",
        asset_id=asset["asset_id"],
        expected_derivations_sha256=second["derivations_sha256"],
        retraction={
            "derivation_id": second["derivation_id"],
            "agent": "reviewer",
            "reason": "Withdraw inaccurate interpretation",
        },
    )
    history, _ = read_ledger(service_at(tmp_path), asset["asset_id"], 79)
    assert [e["kind"] for e in history["events"]] == ["record", "record", "retract"]
    assert service.repository.read(asset["asset_id"]) == before
    assert len(service.repository.load(asset["asset_id"]).history) == 1


def test_new_revision_does_not_move_old_derivation(linked):
    service, asset, claim = linked
    result = record(service, asset, claim)
    _call(
        service,
        op="update",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        edits=[{"sheet": "Sheet1", "cell": "A1", "value": "008"}],
    )
    proof = _call(
        service,
        op="verify_derivation",
        asset_id=asset["asset_id"],
        derivation_id=result["derivation_id"],
    )
    assert proof["active"] and proof["references_valid"]
    assert not proof["target"]["is_current_managed_revision"]
    history, _ = read_ledger(service, asset["asset_id"])
    assert history["events"][0]["derivation"]["target"]["revision"] == asset["revision"]


@pytest.mark.parametrize(
    "failure",
    [
        "value_hash",
        "missing_revision",
        "wrong_asset",
        "duplicate_source",
        "self_source",
        "blank_agent",
        "unknown_field",
        "unknown_supersedes",
        "too_many_sources",
    ],
)
def test_bad_record_leaves_no_ledger(linked, failure, tmp_path):
    service, asset, claim = linked
    claim = deepcopy(claim)
    if failure == "value_hash":
        claim["target"]["value_sha256"] = "0" * 64
    elif failure == "missing_revision":
        claim["sources"][0]["revision"] = "0" * 64
    elif failure == "wrong_asset":
        claim["target"]["asset_id"] = claim["sources"][0]["asset_id"]
    elif failure == "duplicate_source":
        claim["sources"] *= 2
    elif failure == "self_source":
        claim["sources"] = [claim["target"]]
    elif failure == "blank_agent":
        claim["agent"] = " "
    elif failure == "unknown_field":
        claim["review"]["machine_proved_semantics"] = True
    elif failure == "unknown_supersedes":
        claim["supersedes"] = "0" * 64
    else:
        claim["sources"] *= 65
    with pytest.raises((ValueError, FileNotFoundError)):
        record(service, asset, claim)
    assert not (tmp_path / "store" / asset["asset_id"] / "derivations.json").exists()


def test_stale_pagination_and_writer_fail_without_losing_record(linked):
    service, asset, claim = linked
    _, old_hash = read_ledger(service, asset["asset_id"])
    first = record(service, asset, claim, old_hash)
    with pytest.raises(ValueError, match="Stale"):
        record(service, asset, {**claim, "activity": "Concurrent edit"}, old_hash)
    with pytest.raises(ValueError, match="changed"):
        _call(
            service,
            op="read_derivations",
            asset_id=asset["asset_id"],
            text_offset=1,
            derivations_sha256=old_hash,
        )
    with pytest.raises(ValueError, match="requires"):
        NativeDocumentRequest(
            op="read_derivations", asset_id=asset["asset_id"], text_offset=1
        )
    ledger, sha = read_ledger(service, asset["asset_id"])
    assert len(ledger["events"]) == 1 and sha == first["derivations_sha256"]


def test_corrupt_endpoint_reports_invalid_and_archived_target_blocks_changes(
    linked, tmp_path
):
    service, asset, claim = linked
    first = record(service, asset, claim)
    ref = claim["sources"][0]
    blob = tmp_path / "store" / ref["asset_id"] / "revisions" / ref["revision"]
    blob.write_bytes(b"altered source snapshot")
    proof = _call(
        service,
        op="verify_derivation",
        asset_id=asset["asset_id"],
        derivation_id=first["derivation_id"],
    )
    assert proof["active"] and not proof["references_valid"]
    _call(
        service,
        op="archive",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
    )
    with pytest.raises(ValueError, match="Archived"):
        _call(
            service,
            op="retract_derivation",
            asset_id=asset["asset_id"],
            expected_derivations_sha256=first["derivations_sha256"],
            retraction={
                "derivation_id": first["derivation_id"],
                "agent": "reviewer",
                "reason": "withdraw",
            },
        )
