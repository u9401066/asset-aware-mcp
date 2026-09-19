"""Independent reconstruction of complete, pinned native and A2T trace reads."""

import json

from tests.codex_native_pdf.trace import canonical, digest, payload
from tests.codex_pdf.trace import require


def read_events(calls):
    buffers = {}
    for index, call in enumerate(calls):
        if call["tool"] != "document":
            continue
        args = call["arguments"]["native_request"]
        if args["op"] not in {"read_workbook", "read_table_workspace"}:
            continue
        result = payload(call)
        workspace = args["op"] == "read_table_workspace"
        identity = result["table_id"] if workspace else args["asset_id"]
        revision = result["table_sha256"] if workspace else result["inspected_revision"]
        requested = args.get("table_sha256" if workspace else "revision")
        if not workspace and requested is None:
            continue
        start, end = result["excerpt_char_range"]
        require(
            (workspace and start == 0 and requested is None) or requested == revision,
            "Read lacks a consistent revision pin",
        )
        key = (args["op"], identity, revision, result["text_sha256"])
        if start == 0:
            buffers[key] = ""
        require(
            start == args.get("text_offset", 0) == len(buffers.get(key, "")),
            "Noncontiguous structural workspace read",
        )
        buffers[key] += result["text_excerpt"]
        require(end == len(buffers[key]), "Structural excerpt range mismatch")
        if result["next_text_offset"] is not None:
            continue
        require(
            digest(buffers[key].encode()) == key[3], "Structural read hash mismatch"
        )
        record = json.loads(buffers[key])
        if workspace:
            require(
                record["table"]["id"] == identity
                and digest(canonical(record["table"])) == revision,
                "Frozen workspace hash mismatch",
            )
        else:
            require(
                record["asset_id"] == identity and record["revision"] == revision,
                "Workbook binding mismatch",
            )
        yield index, args, record, revision
