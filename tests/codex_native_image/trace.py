"""Strict call order, complete hash-paged records and actual image delivery."""

import json

from src.domain.native_image_evidence import image_catalog, image_frame_reference
from src.infrastructure.native_image_document import NativeImage
from tests.codex_docx_grid.audit import validate_receipt
from tests.codex_native_image.checks import (
    source_bytes,
    validate_preview,
    validate_workbook_read,
)
from tests.codex_native_pdf.artifacts import load_asset
from tests.codex_native_pdf.trace import canonical, digest, payload
from tests.codex_pdf.trace import call_failed, require

REQUIRED = {
    "contract",
    "contract_details",
    "schema",
    "register",
    "read_image",
    "read_image_frame",
    "render_image_frame",
    "read_image_region",
    "extract_image",
    "create_image",
    "compose_images",
    "update_image",
    "verify",
    "read_selection",
    "create",
    "read_cell",
    "read_derivations",
    "record_derivation",
    "verify_derivation",
    "publish",
    "export_wiki",
    "history",
}
MUTATIONS = {
    "extract_image",
    "create_image",
    "compose_images",
    "update_image",
    "create",
}


def policy_operations(record, for_op):
    require(
        record.get("contract_version") == "native-contract-v2"
        and record.get("for_op") == for_op
        and record.get("images_enabled") is True,
        "Incomplete image capability policy",
    )
    for key in ("image_policy", "workbook_policy"):
        require(
            isinstance(record.get(key), str) and record[key], "Missing operation policy"
        )
    advertised = {op for ops in record["formats"].values() for op in ops}
    require(MUTATIONS - {"create"} <= advertised, "Missing image mutation capabilities")
    require(set(record["operations"]) >= MUTATIONS, "Missing mutation inventory")
    # A complete global contract contains the same operation policies. The
    # independently paged schema must still be read for EACH actual mutation.
    return MUTATIONS if for_op is None else {for_op}


def calls_from(events):
    require(any(e["type"] == "turn.completed" for e in events), "Incomplete model turn")
    calls = []
    for event in events:
        if event["type"] != "item.completed":
            continue
        item = event["item"]
        require(
            item["type"] in {"agent_message", "reasoning", "plan", "mcp_tool_call"},
            "Non-MCP action",
        )
        if item["type"] != "mcp_tool_call":
            continue
        require(
            item["server"] == "asset_aware_under_test"
            and item["tool"] == "document"
            and item["arguments"]["op"] == "native",
            "Unexpected server/tool",
        )
        require(
            item["arguments"]["native_request"]["op"]
            in REQUIRED | {"inspect", "list", "read_workbook"},
            "Unexpected operation",
        )
        if not call_failed(item):
            calls.append(item)
    observed = {c["arguments"]["native_request"]["op"] for c in calls}
    require(observed >= REQUIRED, f"Incomplete workflow: {REQUIRED - observed}")
    return calls


def read_page(buffers, args, page):
    sha = page.get(
        "text_sha256", page.get("schema_sha256", page.get("derivations_sha256"))
    )
    require(isinstance(sha, str), "Missing read hash")
    key = (
        args["op"],
        args.get("asset_id"),
        args.get("revision"),
        args.get("for_op"),
        canonical(args.get("image_locator")),
        canonical(args.get("reference")),
        sha,
    )
    start, end = page["excerpt_char_range"]
    require(
        start == args.get("text_offset", 0)
        and end - start == len(page["text_excerpt"]),
        "Read range differs",
    )
    if start == 0:
        require(key not in buffers, "Abandoned earlier read")
        buffers[key] = ""
    require(
        key in buffers and len(buffers[key]) == start, "Skipped/repeated read chunk"
    )
    buffers[key] += page["text_excerpt"]
    if page["next_text_offset"] is not None:
        require(page["next_text_offset"] == end, "Invalid continuation")
        return None
    text = buffers.pop(key)
    require(digest(text.encode()) == sha, "Complete read hash differs")
    if "text_length" in page:
        require(len(text) == page["text_length"], "Incomplete read length")
    return json.loads(text)


def inspect_calls(calls, workspace, output, *, save_images=True):
    buffers, catalogs, records, policies, schemas = {}, {}, {}, set(), set()
    images, regions, verified, ledgers, cells, exports = set(), {}, set(), set(), {}, []
    selections = set()
    raw_records = {}
    pending = None
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        op = args["op"]
        if op in {
            "contract_details",
            "schema",
            "read_image",
            "read_image_frame",
            "read_derivations",
            "read_selection",
            "read_workbook",
        }:
            record = read_page(
                buffers,
                args,
                result["image"] if op.startswith("read_image") else result,
            )
            if record is None:
                continue
            if op in {"contract_details", "schema"}:
                field = (
                    "contract_sha256" if op == "contract_details" else "schema_sha256"
                )
                require(
                    args[field]
                    == result.get("text_sha256", result.get("schema_sha256")),
                    "Discovery hash not pinned",
                )
                if op == "contract_details":
                    policies.update(policy_operations(record, args.get("for_op")))
                else:
                    schemas.add(args.get("for_op"))
            elif op == "read_derivations":
                ledgers.add(digest(canonical(record)))
            elif op == "read_workbook":
                key = (args["asset_id"], args["revision"])
                validate_workbook_read(args, record, source_bytes(workspace, *key))
                validate_receipt(record, load_asset(workspace, key[0]), key[1])
            elif op == "read_selection":
                parent = canonical(record["parent"])
                require(
                    parent in regions
                    and record["selector"]["pointer"] == "/source_pixel_bounds",
                    "Selection parent or pointer differs",
                )
                require(
                    record["value"] == regions[parent]["source_pixel_bounds"],
                    "Selected source bounds differ",
                )
                require(
                    digest(
                        canonical({k: v for k, v in record.items() if k != "evidence"})
                    )
                    == record["evidence"]["value_sha256"],
                    "Selection hash differs",
                )
                selections.add(canonical(record["evidence"]))
            else:
                key = (args["asset_id"], args["revision"])
                if key not in raw_records:
                    raw = source_bytes(workspace, *key)
                    raw_records[key] = (raw, NativeImage().records(raw))
                raw, decoded = raw_records[key]
                validate_receipt(record, load_asset(workspace, key[0]), key[1])
                if op == "read_image":
                    require(
                        record["catalog"] == image_catalog(raw, decoded),
                        "Complete image catalog differs",
                    )
                    refs = [
                        image_frame_reference(r, *key).model_dump(mode="json")
                        for r in decoded
                    ]
                    require(
                        record["frame_references"] == refs, "Catalog references differ"
                    )
                    catalogs[key] = record
                    if pending == key:
                        pending = None
                else:
                    core = {
                        k: v
                        for k, v in record.items()
                        if k
                        not in {
                            "evidence",
                            "operation_result",
                            "operation_receipt_policy",
                        }
                    }
                    require(
                        core == decoded[args["image_locator"]["frame_index"]],
                        "Complete frame differs from source",
                    )
                    require(
                        image_frame_reference(core, *key).model_dump(mode="json")
                        == record["evidence"],
                        "Frame evidence differs",
                    )
                    records[canonical(record["evidence"])] = record
        elif op in {"render_image_frame", "read_image_region"}:
            ref, png = validate_preview(call, workspace)
            parent = ref.get("parent", ref)
            require(canonical(parent) in records, "Preview before full frame read")
            if op == "read_image_region":
                regions[canonical(ref)] = result["region"]
            else:
                images.add(
                    (ref["asset_id"], ref["revision"], ref["locator"]["frame_index"])
                )
            if save_images:
                (output / ("preview-" + digest(canonical(ref)) + ".png")).write_bytes(
                    png
                )
        elif op in MUTATIONS:
            require(
                op in policies and op in schemas,
                "Mutation before complete per-operation discovery",
            )
            require(pending is None, "Mutation before complete previous receipt")
            used = []
            if op == "extract_image":
                used = [args["image_extract"]["reference"]]
                require(
                    any(
                        r["parent"] == used[0]
                        and r["selector"] == args["image_extract"]["region"]
                        for r in regions.values()
                    ),
                    "Extraction before actual region preview",
                )
            elif op == "compose_images":
                used = [f["reference"] for f in args["image_compose"]["frames"]]
            elif op == "update_image":
                key = (args["asset_id"], args["expected_revision"])
                plan = args["image_update"]
                require(
                    key in catalogs
                    and plan["expected_catalog_sha256"]
                    == catalogs[key]["catalog"]["catalog_sha256"],
                    "Update before pinned catalog",
                )
                used = [
                    change[k]
                    for change in plan["frames"]
                    for k in ("before", "after")
                    if k in change
                ]
                candidate = plan["candidate"]
                require(
                    source_bytes(
                        workspace,
                        result["asset"]["asset_id"],
                        result["asset"]["revision"],
                    )
                    == source_bytes(
                        workspace, candidate["asset_id"], candidate["revision"]
                    ),
                    "Update did not commit exact candidate bytes",
                )
            for ref in used:
                require(
                    canonical(ref) in records, "Mutation before full reference read"
                )
                require(
                    (ref["asset_id"], ref["revision"], ref["locator"]["frame_index"])
                    in images,
                    "Mutation before actual input image",
                )
            if op != "create":
                pending = (result["asset"]["asset_id"], result["asset"]["revision"])
        elif op == "verify":
            require(result["valid"], "Evidence verification failed")
            if args["reference"]["schema_version"] == "native-selection-ref-v1":
                require(
                    canonical(args["reference"]) in selections,
                    "Selection verified before complete read",
                )
            verified.add(canonical(args["reference"]))
        elif op == "read_cell":
            cell = result["cell"]
            require(
                cell.get("representation_complete")
                and cell.get("next_text_offset") is None,
                "Incomplete literal cell read",
            )
            require(
                digest(cell["value_excerpt"].encode()) == cell["value_text_sha256"],
                "Cell literal hash differs",
            )
            cells[canonical(cell["evidence"])] = cell
        elif op == "record_derivation":
            require(
                args["expected_derivations_sha256"] in ledgers,
                "Append before complete ledger read",
            )
            require(
                canonical(args["derivation"]["target"]) in cells, "Target cell not read"
            )
            require(
                all(canonical(r) in regions for r in args["derivation"]["sources"]),
                "Source region not viewed",
            )
        elif op == "export_wiki":
            exports.append(result)
    require(not buffers and pending is None, "Unfinished record or receipt read")
    for key, record in catalogs.items():
        for ref in record["frame_references"]:
            require(canonical(ref) in records, "Missing complete frame")
            require(
                (*key, ref["locator"]["frame_index"]) in images,
                "Missing actual frame PNG",
            )
    return {
        "catalogs": catalogs,
        "records": records,
        "images": images,
        "regions": regions,
        "verified": verified,
        "ledgers": ledgers,
        "cells": cells,
        "exports": exports,
    }
