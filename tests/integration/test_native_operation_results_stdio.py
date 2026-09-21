"""SDK2 process restarts retain complete receipts and exact Wiki snapshots."""

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.integration.test_native_delimited_stdio import complete, native


async def snapshot(client, asset, output):
    response = await native(
        client,
        op="export_wiki",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        output_dir=str(output),
    )
    assert response["success"], response
    folder = Path(response["output_dir"])
    return {
        str(p.relative_to(folder)): p.read_bytes()
        for p in folder.rglob("*")
        if p.is_file()
    }


def legacy_metadata(path):
    record = json.loads(path.read_bytes())
    for index, entry in enumerate(record["history"]):
        ref = entry.pop("result_ref")
        if ref is not None:
            result_path = path.parent / "results" / (ref["sha256"] + ".json")
            raw = result_path.read_bytes()
            assert (
                len(raw) == ref["size_bytes"]
                and hashlib.sha256(raw).hexdigest() == ref["sha256"]
            )
            blob = json.loads(raw)
            assert (
                blob["history_index"] == index
                and blob["asset_id"] == record["asset_id"]
            )
            entry["result"] = blob["result"]
            result_path.unlink()
    record["schema_version"] = "native-file-asset-v1"
    raw = json.dumps(record, ensure_ascii=False).encode()
    path.write_bytes(raw)
    return raw


@pytest.mark.timeout(120)
async def test_receipts_and_wiki_equal_across_storage_migration_and_three_processes(
    tmp_path,
):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        env={
            **os.environ,
            "DATA_DIR": str(tmp_path / "data"),
            "ENABLE_LIGHTRAG": "false",
            "ASSET_AWARE_DISABLE_DOTENV": "true",
        },
    )
    async with Client(stdio_client(params)) as client:
        created = await native(
            client,
            op="create_delimited",
            delimited_create={"rows": [["007", "完整😀"]]},
        )
        assert created["success"], created
        original = created["asset"]
        changed = await native(
            client,
            op="update_delimited",
            asset_id=original["asset_id"],
            expected_revision=original["revision"],
            delimited_update={
                "operation": "insert_rows",
                "index": 1,
                "rows": [["-0.50", "換行\r\n內容"]],
                "record_separator": "\n",
            },
        )
        assert changed["success"], changed
        current = changed["asset"]
        requests = [
            {
                "op": "read_delimited",
                "asset_id": a["asset_id"],
                "revision": a["revision"],
            }
            for a in [original, current]
        ]
        records = [await complete(client, **r) for r in requests]
        assert all(r["operation_result"]["changes"] for r in records)
        snapshots = [
            await snapshot(client, a, tmp_path / "before") for a in [original, current]
        ]
    path = tmp_path / "data" / "native-assets" / current["asset_id"] / "asset.json"
    legacy = legacy_metadata(path)
    async with Client(stdio_client(params)) as client:
        assert [await complete(client, **r) for r in requests] == records
        assert path.read_bytes() == legacy
        assert [
            await snapshot(client, a, tmp_path / "legacy") for a in [original, current]
        ] == snapshots
        archived = await native(
            client,
            op="archive",
            asset_id=current["asset_id"],
            expected_revision=current["revision"],
        )
        assert archived["success"], archived
    assert json.loads(path.read_bytes())["schema_version"] == "native-file-asset-v2"
    async with Client(stdio_client(params)) as client:
        assert [await complete(client, **r) for r in requests] == records
        assert [
            await snapshot(client, a, tmp_path / "after") for a in [original, current]
        ] == snapshots
        record = json.loads(path.read_bytes())
        ref = record["history"][-1]["result_ref"]
        (path.parent / "results" / (ref["sha256"] + ".json")).write_bytes(b"{}")
        failed = await native(client, **requests[-1])
        assert not failed["success"] and "operation_result" not in failed
        assert await complete(client, **requests[0]) == records[0]
