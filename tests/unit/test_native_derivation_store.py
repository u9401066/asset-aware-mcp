"""Ledger metadata rejects tampering, stale writers and interrupted publications."""

import json
from copy import deepcopy

import pytest

from src.domain.native_derivation import NativeDerivationLedger
from src.infrastructure.native_file_io import operation_lock
from tests.native_derivation_helpers import pair, read_ledger, record, service_at
from tests.native_workbook_helpers import _call


@pytest.mark.parametrize(
    "failure",
    [
        "record_hash",
        "target_asset",
        "inactive_retraction",
        "duplicate_record",
        "symlink",
        "missing_asset",
        "too_many_events",
    ],
)
def test_bad_ledger_is_not_reinterpreted_as_empty(tmp_path, failure):
    service = service_at(tmp_path)
    asset, claim = pair(service)
    result = record(service, asset, claim)
    path = tmp_path / "store" / asset["asset_id"] / "derivations.json"
    ledger = json.loads(path.read_text())
    if failure == "record_hash":
        ledger["events"][0]["derivation"]["activity"] = "Forged"
    elif failure == "target_asset":
        ledger["asset_id"] = claim["sources"][0]["asset_id"]
    elif failure == "inactive_retraction":
        ledger["events"].append(
            {
                "kind": "retract",
                "derivation_id": "0" * 64,
                "agent": "reviewer",
                "reason": "invalid",
            }
        )
    elif failure == "duplicate_record":
        ledger["events"] *= 2
    elif failure == "too_many_events":
        ledger["events"] *= 1001
    elif failure == "missing_asset":
        (path.parent / "asset.json").unlink()
    else:
        saved = path.with_suffix(".saved")
        path.rename(saved)
        try:
            path.symlink_to(saved)
        except OSError:
            pytest.skip("Platform cannot create symlinks")
    if failure not in {"symlink", "missing_asset"}:
        path.write_text(json.dumps(ledger))
    with pytest.raises((ValueError, FileNotFoundError)):
        _call(
            service,
            op="read_derivations",
            asset_id=asset["asset_id"],
            derivations_sha256=result["derivations_sha256"],
        )


@pytest.mark.parametrize("failure", ["locked", "replace_failure", "byte_limit"])
def test_failed_append_preserves_prior_ledger(tmp_path, monkeypatch, failure):
    from pathlib import Path

    import src.infrastructure.native_derivation_store as storage

    service = service_at(tmp_path)
    asset, claim = pair(service)
    record(service, asset, claim)
    path = tmp_path / "store" / asset["asset_id"] / "derivations.json"
    before = path.read_bytes()
    changed = {**claim, "activity": "Second activity"}
    if failure == "locked":
        with operation_lock(path.parent), pytest.raises(ValueError, match="busy"):
            record(service, asset, changed)
    else:
        if failure == "replace_failure":

            def broken_replace(self, target):
                raise OSError("Interrupted before replacement")

            monkeypatch.setattr(Path, "replace", broken_replace)
        else:
            monkeypatch.setattr(storage, "MAX_DERIVATION_BYTES", len(before) + 1)
        with pytest.raises((OSError, ValueError)):
            record(service, asset, changed)
    assert path.read_bytes() == before
    assert not list(path.parent.glob(".native-stage-*"))


def test_unknown_or_retracted_record_cannot_be_reused(tmp_path):
    service = service_at(tmp_path)
    asset, claim = pair(service)
    first = record(service, asset, claim)
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
    with pytest.raises(ValueError, match="already exists"):
        record(service, asset, claim)
    fixed = deepcopy(claim)
    fixed["supersedes"] = first["derivation_id"]
    with pytest.raises(ValueError, match="inactive"):
        record(service, asset, fixed)
    ledger, _ = read_ledger(service, asset["asset_id"])
    assert len(NativeDerivationLedger.model_validate(ledger).events) == 2
