"""SDK2: scanned PDF evidence to native CSV, exact CRUD, history and Wiki."""

import csv
import hashlib
import io
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.codex_pdf.fixtures import build_pdf
from tests.integration.test_native_derivation_stdio import ledger_read
from tests.integration.test_native_pdf_regions_stdio import native
from tests.native_pdf_helpers import page_reference


async def complete(client, **request):
    chunks, offset, sha = [], 0, None
    while True:
        response = await native(client, **request, text_offset=offset, text_limit=4000)
        assert response["success"] and "response_truncated" not in response, response
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


async def cell(client, asset, row, column, **kwargs):
    return await complete(
        client,
        op="read_delimited_cell",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        delimited_row=row,
        delimited_column=column,
        **kwargs,
    )


@pytest.mark.timeout(120)
async def test_native_delimited_evidence_crud_and_portable_snapshots_over_sdk2(
    tmp_path,
):
    source = tmp_path / "scan.pdf"
    build_pdf(source, "scanned")
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        env={
            **os.environ,
            "DATA_DIR": str(tmp_path / "data"),
            "ENABLE_LIGHTRAG": "false",
            "ASSET_AWARE_DISABLE_DOTENV": "true",
            "ASSET_AWARE_MCP_TOOL_SURFACE": "balanced",
        },
    )
    async with Client(stdio_client(params)) as client:
        contract = await native(client, op="contract", for_op="update_delimited")
        assert contract["delimited_enabled"] and "response_truncated" not in contract
        pdf = (await native(client, op="register", source_path=str(source)))["asset"]
        page = page_reference(original, 0, pdf["asset_id"]).model_dump(mode="json")
        region = await native(
            client,
            op="read_pdf_region",
            reference=page,
            pdf_region={"rect": [145 / 612, 185 / 792, 225 / 612, 230 / 792]},
            render_size=160,
        )
        source_ref = region["region"]["evidence"]
        created = await native(
            client,
            op="create_delimited",
            delimited_create={
                "name": "counts.csv",
                "rows": [["Count", "note"], ["007", "line\r\nnext"]],
                "bom": True,
            },
        )
        assert created["success"]
        asset = created["asset"]
        assert (await complete(client, **created["review_request"]))["row_lengths"] == [
            2,
            2,
        ]
        old = await cell(client, asset, 1, 0)
        _, sha = await ledger_read(client, asset["asset_id"])
        claim = await native(
            client,
            op="record_derivation",
            asset_id=asset["asset_id"],
            expected_derivations_sha256=sha,
            derivation={
                "target": old["evidence"],
                "sources": [source_ref],
                "agent": "SDK2 fixture",
                "activity": "Known fixture transcription; not a model OCR verdict",
                "review": {
                    "semantic_accuracy": "not_checked",
                    "formula_results": "not_applicable",
                },
            },
        )
        assert claim["success"]
        _, sha = await ledger_read(client, asset["asset_id"])
        current = asset
        for change in [
            {
                "operation": "set_cells",
                "cells": [{"reference": old["evidence"], "value": "008"}],
            },
            {
                "operation": "insert_rows",
                "index": 1,
                "rows": [["012", "new"]],
                "record_separator": "\n",
            },
            {
                "operation": "insert_column",
                "index": 1,
                "values": ["unit", "mg/L", "mg/L"],
            },
            {"operation": "delete_rows", "index": 1, "count": 1},
            {"operation": "delete_columns", "index": 1, "count": 1},
        ]:
            changed = await native(
                client,
                op="update_delimited",
                asset_id=asset["asset_id"],
                expected_revision=current["revision"],
                delimited_update=change,
            )
            assert changed["success"], changed
            current = changed["asset"]
            receipt = await complete(client, **changed["review_request"])
            assert (
                receipt["operation_result"]["changes"][0]["operation"]
                == change["operation"]
            )
        assert current["revision_count"] == 6
        assert (await cell(client, current, 1, 0))["value"] == "008"
        assert (await cell(client, current, 1, 1))["value"] == "line\r\nnext"
        proof = await native(client, op="verify", reference=old["evidence"])
        assert proof["valid"] and not proof["is_current_managed_revision"]
        stale = await native(
            client,
            op="update_delimited",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            delimited_update={"operation": "delete_rows", "index": 0, "count": 1},
        )
        assert not stale["success"]
        for revision, active in [
            (asset["revision"], True),
            (current["revision"], False),
        ]:
            wiki = await native(
                client,
                op="export_wiki",
                asset_id=asset["asset_id"],
                revision=revision,
                output_dir=str(tmp_path / "wiki"),
                derivations_sha256=sha,
                citation_contract={
                    "inline_template": "{source_id} / {locator}",
                    "reference_template": "{title}",
                },
            )
            assert wiki["success"], wiki
            root = Path(wiki["output_dir"])
            manifest = json.loads((root / "manifest.json").read_text())
            assert bool(manifest["derivations"]["active_ids_for_revision"]) == active
            if active:
                saved = next(iter(manifest["derivations"]["region_records"].values()))
                assert (
                    json.loads((root / saved["record_file"]).read_text())["evidence"]
                    == source_ref
                )
        output = tmp_path / "verified.csv"
        result = await native(
            client,
            op="publish",
            asset_id=asset["asset_id"],
            expected_revision=current["revision"],
            output_path=str(output),
        )
        assert result["success"]
        assert (
            output.read_bytes() == b'\xef\xbb\xbfCount,note\r\n008,"line\r\nnext"\r\n'
        )
        assert list(
            csv.reader(io.StringIO(output.read_bytes().decode("utf-8-sig"), newline=""))
        ) == [["Count", "note"], ["008", "line\r\nnext"]]
        # Non-default encoding/dialect reaches the production child process too.
        tsv = await native(
            client,
            op="create_delimited",
            delimited_create={
                "name": "中文.tsv",
                "dialect": {"delimiter": "\t", "encoding": "cp950"},
                "rows": [["研究", "007"]],
            },
        )
        assert tsv["success"]
        field = await cell(
            client,
            tsv["asset"],
            0,
            0,
            delimited_dialect={"delimiter": "\t", "encoding": "cp950"},
        )
        assert field["value"] == "研究"
        assert (await native(client, op="verify", reference=field["evidence"]))["valid"]
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
