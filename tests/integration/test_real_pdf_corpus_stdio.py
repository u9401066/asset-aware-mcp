"""Explicit local public corpus: actual SDK2 and native process workers, no LLM."""

import base64
import hashlib
import os
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.codex_delimited.audit import check_field
from tests.codex_pdf.fixtures import server_environment
from tests.integration.test_native_delimited_stdio import cell, complete
from tests.integration.test_native_derivation_stdio import ledger_read
from tests.integration.test_native_pdf_regions_stdio import native, unwrap
from tests.integration.test_native_pdf_stdio import read_page
from tests.real_pdf.checks import expected_revisions
from tests.real_pdf.corpus import cases, check_source
from tests.real_pdf.raster import region_image


@pytest.mark.timeout(300)
@pytest.mark.parametrize("case", cases(), ids=lambda c: c["id"])
async def test_original_public_pdf_regions_csv_crud_and_wiki_over_sdk2(tmp_path, case):
    directory = os.environ.get("ASSET_AWARE_REAL_PDF_CORPUS")
    if not directory:
        pytest.skip("Opt in with ASSET_AWARE_REAL_PDF_CORPUS; never download in pytest")
    data = check_source(Path(directory) / case["filename"], case)
    source = tmp_path / "source.pdf"
    source.write_bytes(data)
    mtime = source.stat().st_mtime_ns
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        env={
            **os.environ,
            **server_environment(tmp_path / "data"),
            "TMPDIR": str(tmp_path),
        },
    )
    truth = expected_revisions(case)
    async with Client(stdio_client(params)) as client:
        pdf = (await native(client, op="register", source_path=str(source)))["asset"]
        assert pdf["revision"] == case["sha256"]
        regions, parents = [], []
        for page in case["pages"]:
            listing = await native(
                client,
                op="read_pdf",
                asset_id=pdf["asset_id"],
                revision=pdf["revision"],
                offset=page["index"],
                limit=1,
            )
            assert listing["success"], listing
            assert listing["metadata"]["page_count"] == case["page_count"]
            parent = await read_page(client, pdf, listing["pages"][0]["locator"])
            parents.append(parent["evidence"])
            if case["kind"] == "scan_with_ocr":
                checks = listing["metadata"]["parser_checks"]
                assert checks == parent["parser_checks"]
                assert checks[0]["verified_stream_count"] == 359
                assert checks[0]["declaration_count"] == 718
                assert checks[0]["source_bytes_preserved"]
            x0, y0, x1, y1 = page["content_bounds"]
            response = await client.call_tool(
                "document",
                {
                    "op": "native",
                    "native_request": {
                        "op": "read_pdf_region",
                        "reference": parent["evidence"],
                        "pdf_region": {
                            "rect": [x0 - 0.02, y0 - 0.02, x1 + 0.02, y1 + 0.02]
                        },
                        "render_size": 768,
                    },
                },
            )
            result = unwrap(response)
            assert result["success"], result
            images = [b for b in response.content if b.type == "image"]
            assert len(images) == 1
            ref = result["region"]["evidence"]
            region_image(tmp_path, ref, result, 768, base64.b64decode(images[0].data))
            assert (await native(client, op="verify", reference=ref))["valid"]
            regions.append(ref)
        if case["kind"] == "scan_with_ocr":
            copied = await native(
                client,
                op="create_pdf",
                pdf_create={
                    "name": "selected-pages.pdf",
                    "pages": [{"reference": ref} for ref in parents],
                },
            )
            assert copied["success"], copied
            assert (
                "canonicalized_equal_duplicate_stream_lengths"
                in copied["operation_result"]["repairs"]
            )
            selected = copied["asset"]
            listing = await native(
                client,
                op="read_pdf",
                asset_id=selected["asset_id"],
                revision=selected["revision"],
            )
            assert listing["success"] and listing["metadata"]["page_count"] == 2
            assert "parser_checks" not in listing["metadata"]
            assert (await native(client, op="verify", reference=parents[0]))["valid"]
        created = await native(
            client,
            op="create_delimited",
            delimited_create={
                "name": "table.csv",
                "rows": [case["columns"], *case["rows"]],
                "bom": True,
            },
        )
        assert created["success"], created
        asset = created["asset"]
        await complete(client, **created["review_request"])
        fields = {}
        for r, row in enumerate([case["columns"], *case["rows"]]):
            for c, value in enumerate(row):
                record = await cell(client, asset, r, c)
                assert record["value"] == value
                check_field(record, truth[0])
                fields[r, c] = record
        for page, region in zip(case["pages"], regions, strict=True):
            _, sha = await ledger_read(client, asset["asset_id"])
            claim = await native(
                client,
                op="record_derivation",
                asset_id=asset["asset_id"],
                expected_derivations_sha256=sha,
                derivation={
                    "target": fields[page["first_row"], 1]["evidence"],
                    "sources": [region],
                    "agent": "SDK2 real corpus",
                    "activity": "Pinned public corpus oracle; not an Agent visual review",
                    "review": {
                        "semantic_accuracy": "not_checked",
                        "formula_results": "not_applicable",
                    },
                },
            )
            assert claim["success"], claim
        count, width = len(case["rows"]) + 1, len(case["columns"])
        old = fields[1, 1]["evidence"]
        changes = [
            {
                "operation": "set_cells",
                "cells": [{"reference": old, "value": "__review__"}],
            },
            None,
            {
                "operation": "insert_rows",
                "index": count,
                "rows": [["temporary"] * width],
                "record_separator": "\r\n",
            },
            {
                "operation": "insert_column",
                "index": width,
                "values": ["Review", *(["checked"] * count)],
            },
            {"operation": "delete_rows", "index": count, "count": 1},
            {"operation": "delete_columns", "index": width, "count": 1},
        ]
        for i, change in enumerate(changes, 1):
            if change is None:
                changed = await cell(client, asset, 1, 1)
                proof = await native(client, op="verify", reference=old)
                assert proof["valid"] and not proof["is_current_managed_revision"]
                change = {
                    "operation": "set_cells",
                    "cells": [
                        {"reference": changed["evidence"], "value": case["rows"][0][1]}
                    ],
                }
            updated = await native(
                client,
                op="update_delimited",
                asset_id=asset["asset_id"],
                expected_revision=asset["revision"],
                delimited_update=change,
            )
            assert updated["success"], updated
            asset = updated["asset"]
            receipt = await complete(client, **updated["review_request"])
            assert (
                receipt["operation_result"]["changes"][0]["operation"]
                == change["operation"]
            )
            assert asset["revision"] == hashlib.sha256(truth[i]).hexdigest()
            stored = (
                tmp_path
                / "data"
                / "native-assets"
                / asset["asset_id"]
                / "revisions"
                / asset["revision"]
            )
            assert stored.read_bytes() == truth[i]
        _, sha = await ledger_read(client, asset["asset_id"])
        wiki = await native(
            client,
            op="export_wiki",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            derivations_sha256=sha,
            output_dir=str(tmp_path / "native-wiki"),
        )
        assert wiki["success"], wiki
        assert (await cell(client, asset, 1, 1))["value"] == case["rows"][0][1]
    assert source.read_bytes() == data and source.stat().st_mtime_ns == mtime
