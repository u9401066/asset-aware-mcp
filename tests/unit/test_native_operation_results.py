"""Complete native result history survives bounded metadata and process restarts."""

import hashlib
import json

import pytest

from src.domain.native_asset_models import NativeEditResult, NativeFileAsset
from src.infrastructure import native_operation_results as blobs
from src.infrastructure.native_asset_store import FileNativeAssetRepository


def receipt(value="before"):
    return NativeEditResult(
        changed_parts=["payload"],
        preserved_parts=3,
        changes=[{"before": value, "after": "完整😀", "nested": [None, False, 0]}],
        checks=["exact_bytes"],
        repairs=["recorded_repair"],
        review_required=["semantic_accuracy", "rendered_layout"],
    )


def metadata(repository, asset):
    return repository.root / asset.asset_id / "asset.json"


def blob_path(repository, asset, entry=None):
    entry = entry or asset.history[-1]
    return (
        repository.root
        / asset.asset_id
        / "results"
        / (entry.result_ref.sha256 + ".json")
    )


@pytest.fixture
def stored(tmp_path):
    repository = FileNativeAssetRepository(tmp_path / "assets")
    asset = repository.create(
        "data.bin", b"old", "opaque", "application/octet-stream", result=receipt()
    )
    return repository, asset


def as_legacy(repository, asset):
    record = asset.model_dump(mode="json")
    record["schema_version"] = "native-file-asset-v1"
    for entry, saved in zip(asset.history, record["history"], strict=True):
        complete = repository.read_result(asset.asset_id, entry)
        saved.pop("result_ref")
        saved["result"] = complete.model_dump(mode="json") if complete else None
    raw = json.dumps(record, ensure_ascii=False, indent=2).encode()
    metadata(repository, asset).write_bytes(raw)
    for path in (repository.root / asset.asset_id / "results").glob("*.json"):
        path.unlink()
    return raw


def test_large_unicode_result_history_survives_restart_without_growing_metadata(
    tmp_path,
):
    repository = FileNativeAssetRepository(tmp_path / "assets")
    asset = repository.create(
        "data.bin", b"initial", "opaque", "application/octet-stream"
    )
    complete = "完整回執😀" * 400000
    results = []
    for index in range(3):
        result = NativeEditResult(
            changed_parts=["payload"],
            preserved_parts=0,
            changes=[{"index": index, "before": complete, "after": complete[::-1]}],
            checks=["source_bytes_checked"],
            repairs=["explicit_repair"],
            review_required=["semantic_accuracy", "rendered_layout"],
        )
        asset = repository.commit(
            asset.asset_id, asset.revision, str(index).encode(), result
        )
        results.append(result)
    metadata = tmp_path / "assets" / asset.asset_id / "asset.json"
    assert metadata.stat().st_size < 64 * 1024
    restarted = FileNativeAssetRepository(tmp_path / "assets")
    loaded = restarted.load(asset.asset_id)
    assert len(loaded.history) == 4
    for entry, expected in zip(loaded.history[1:], results, strict=True):
        actual = restarted.read_result(asset.asset_id, entry)
        assert actual is not None and actual.model_dump() == expected.model_dump()
    assert restarted.read(asset.asset_id) == b"2"


def test_legacy_reads_are_readonly_and_successful_commit_retains_all_results(stored):
    repository, asset = stored
    original = as_legacy(repository, asset)
    path = metadata(repository, asset)
    original_stat = path.stat()
    loaded = repository.load(asset.asset_id)
    assert repository.read_result(asset.asset_id, loaded.history[0]) == receipt()
    assert repository.list_assets(0, 10) == [loaded]
    assert (
        path.read_bytes() == original
        and path.stat().st_mtime_ns == original_stat.st_mtime_ns
    )
    current = repository.commit(
        asset.asset_id, asset.revision, b"new", receipt("second")
    )
    restarted = FileNativeAssetRepository(repository.root)
    assert current.schema_version == "native-file-asset-v2"
    assert all(
        entry.result is None and entry.result_ref is not None
        for entry in current.history
    )
    assert [
        restarted.read_result(asset.asset_id, entry) for entry in current.history
    ] == [receipt(), receipt("second")]
    assert restarted.read(asset.asset_id, asset.revision) == b"old"


def test_metadata_failure_does_not_publish_migration_or_partial_history(
    stored, monkeypatch
):
    from src.infrastructure import native_asset_store

    repository, asset = stored
    original = as_legacy(repository, asset)
    write = native_asset_store._write_atomic

    def fail(path, data, *, limit):
        if path.name == "asset.json":
            raise OSError("metadata failure")
        write(path, data, limit=limit)

    with monkeypatch.context() as patch:
        patch.setattr(native_asset_store, "_write_atomic", fail)
        with pytest.raises(OSError, match="metadata failure"):
            repository.commit(asset.asset_id, asset.revision, b"new", receipt("next"))
    assert metadata(repository, asset).read_bytes() == original
    assert repository.read(asset.asset_id) == b"old"
    loaded = repository.load(asset.asset_id)
    assert repository.read_result(asset.asset_id, loaded.history[0]) == receipt()
    retried = repository.commit(asset.asset_id, asset.revision, b"new", receipt("next"))
    assert len(retried.history) == 2
    assert repository.read_result(asset.asset_id, retried.history[-1]) == receipt(
        "next"
    )


def test_stale_commit_and_noop_leave_metadata_and_blobs_unchanged(stored):
    repository, asset = stored
    before = metadata(repository, asset).read_bytes()
    retained = blob_path(repository, asset).read_bytes()
    with pytest.raises(ValueError, match="Stale"):
        repository.commit(asset.asset_id, "0" * 64, b"new", receipt("rejected"))
    noop = repository.commit(asset.asset_id, asset.revision, b"old", receipt("ignored"))
    assert noop == asset
    assert metadata(repository, asset).read_bytes() == before
    assert blob_path(repository, asset).read_bytes() == retained


def test_same_file_revision_keeps_distinct_historical_receipts(stored):
    repository, initial = stored
    changed = repository.commit(
        initial.asset_id, initial.revision, b"next", receipt("next")
    )
    reverted = repository.commit(
        initial.asset_id, changed.revision, b"old", receipt("reverted")
    )
    assert reverted.revision == initial.revision
    assert repository.read_result(initial.asset_id, reverted.history[0]) == receipt()
    assert repository.read_result(initial.asset_id, reverted.history[-1]) == receipt(
        "reverted"
    )
    assert reverted.history[0].result_ref != reverted.history[-1].result_ref


@pytest.mark.parametrize("damage", ["missing", "same_size", "shorter", "longer"])
def test_corrupt_results_fail_when_selected_without_hydrating_other_history(
    stored, damage
):
    repository, initial = stored
    current = repository.commit(
        initial.asset_id, initial.revision, b"new", receipt("new")
    )
    path = blob_path(repository, initial)
    raw = path.read_bytes()
    if damage == "missing":
        path.unlink()
    else:
        path.write_bytes(
            {
                "same_size": raw.replace(b"exact_bytes", b"false_bytes"),
                "shorter": raw[:-1],
                "longer": raw + b" ",
            }[damage]
        )
    # Discovery and an unrelated, intact receipt remain available without reading
    # every archive. The selected broken receipt must never become a null report.
    assert repository.load(initial.asset_id) == current
    assert repository.list_assets(0, 10) == [current]
    assert repository.read_result(initial.asset_id, current.history[-1]) == receipt(
        "new"
    )
    with pytest.raises(ValueError):
        repository.read_result(initial.asset_id, current.history[0])


@pytest.mark.parametrize(
    "field,value",
    [
        ("asset_id", "file_" + "0" * 32),
        ("history_index", 1),
        ("revision", "0" * 64),
        ("parent_revision", "1" * 64),
        ("operation", "forged"),
    ],
)
def test_valid_hash_cannot_rebind_result_to_different_history(stored, field, value):
    repository, asset = stored
    record = json.loads(blob_path(repository, asset).read_bytes())
    record[field] = value
    raw = json.dumps(
        record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    publish_replacement(repository, asset, raw)
    entry = repository.load(asset.asset_id).history[0]
    with pytest.raises(ValueError, match="binding mismatch"):
        repository.read_result(asset.asset_id, entry)


def publish_replacement(repository, asset, raw):
    digest = hashlib.sha256(raw).hexdigest()
    path = blob_path(repository, asset).with_name(digest + ".json")
    path.write_bytes(raw)
    record = asset.model_dump(mode="json")
    record["history"][0]["result_ref"].update(sha256=digest, size_bytes=len(raw))
    metadata(repository, asset).write_text(json.dumps(record))


@pytest.mark.parametrize("change", ["whitespace", "duplicate", "missing_default"])
def test_hash_valid_lossy_or_noncanonical_json_is_rejected(stored, change):
    repository, asset = stored
    raw = blob_path(repository, asset).read_bytes()
    if change == "whitespace":
        raw += b" "
    elif change == "duplicate":
        raw = raw.replace(
            b'"preserved_parts":3', b'"preserved_parts":99,"preserved_parts":3'
        )
    else:
        record = json.loads(raw)
        del record["result"]["repairs"]
        raw = json.dumps(
            record, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    publish_replacement(repository, asset, raw)
    with pytest.raises(ValueError, match="canonical complete"):
        repository.read_result(
            asset.asset_id, repository.load(asset.asset_id).history[0]
        )


@pytest.mark.parametrize("target", ["file", "directory"])
def test_result_symlinks_cannot_redirect_reads(stored, tmp_path, target):
    repository, asset = stored
    path = blob_path(repository, asset)
    external = tmp_path / "external.json"
    external.write_bytes(path.read_bytes())
    path.unlink()
    if target == "file":
        path.symlink_to(external)
    else:
        path.parent.rmdir()
        path.parent.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises((OSError, ValueError)):
        repository.read_result(asset.asset_id, asset.history[0])


def test_legacy_migration_failure_precedes_source_writeback(tmp_path, monkeypatch):
    source = tmp_path / "source.bin"
    source.write_bytes(b"source")
    repository = FileNativeAssetRepository(tmp_path / "assets")
    initial = repository.register(str(source))
    asset = repository.commit(initial.asset_id, initial.revision, b"edited", receipt())
    original = as_legacy(repository, asset)

    def fail(*args, **kwargs):
        raise OSError("result storage unavailable")

    with monkeypatch.context() as patch:
        patch.setattr(blobs, "_write_atomic", fail)
        with pytest.raises(OSError, match="result storage unavailable"):
            repository.writeback(asset.asset_id, asset.revision, initial.revision)
    assert source.read_bytes() == b"source"
    assert metadata(repository, asset).read_bytes() == original
    assert not list(tmp_path.glob(".native-backup-*"))
    assert repository.writeback(asset.asset_id, asset.revision, initial.revision)[
        "success"
    ]
    assert source.read_bytes() == b"edited"
    loaded = repository.load(asset.asset_id)
    assert repository.read_result(asset.asset_id, loaded.history[-1]) == receipt()


def test_complete_result_limit_rejects_before_metadata_publication(stored, monkeypatch):
    repository, asset = stored
    before = metadata(repository, asset).read_bytes()
    monkeypatch.setattr(blobs, "MAX_NATIVE_RESULT_BYTES", 100)
    with pytest.raises(ValueError, match="complete byte budget"):
        repository.commit(asset.asset_id, asset.revision, b"new", receipt())
    assert metadata(repository, asset).read_bytes() == before
    assert repository.read(asset.asset_id) == b"old"


@pytest.mark.parametrize("case", ["v1_ref", "v2_inline", "both"])
def test_storage_version_and_exclusive_result_contract(stored, case):
    _, asset = stored
    record = asset.model_dump(mode="json")
    if case == "v1_ref":
        record["schema_version"] = "native-file-asset-v1"
    else:
        record["history"][0]["result"] = receipt().model_dump(mode="json")
        if case == "v2_inline":
            record["history"][0]["result_ref"] = None
    with pytest.raises(ValueError):
        NativeFileAsset.model_validate(record)


def test_migration_never_overwrites_a_corrupt_existing_immutable_blob(stored):
    repository, asset = stored
    path = blob_path(repository, asset)
    raw = path.read_bytes()
    original = as_legacy(repository, asset)
    corrupt = raw.replace(b"exact_bytes", b"false_bytes")
    path.write_bytes(corrupt)
    with pytest.raises(ValueError, match="integrity failure"):
        repository.archive(asset.asset_id, asset.revision)
    assert path.read_bytes() == corrupt
    assert metadata(repository, asset).read_bytes() == original


@pytest.mark.parametrize("damage", [None, "hash", "binding", "incomplete"])
def test_independent_model_auditor_verifies_archived_result(stored, damage):
    from tests.codex_native_pdf.artifacts import archived_result

    repository, asset = stored
    path = blob_path(repository, asset)
    raw = path.read_bytes()
    if damage == "hash":
        path.write_bytes(raw.replace(b"exact_bytes", b"false_bytes"))
    elif damage:
        blob = json.loads(raw)
        if damage == "binding":
            blob["history_index"] = 5
        else:
            del blob["result"]["checks"]
        raw = json.dumps(
            blob, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        publish_replacement(repository, asset, raw)
    record = repository.load(asset.asset_id).model_dump(mode="json")
    args = (path.parent.parent, record, 0, record["history"][0])
    if damage:
        with pytest.raises(ValueError):
            archived_result(*args)
    else:
        assert archived_result(*args) == receipt().model_dump(mode="json")
