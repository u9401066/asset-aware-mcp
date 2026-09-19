"""Independently reconstruct selected values and verify exact location/context."""

import json

from tests.codex_native_pdf.trace import canonical, digest, payload
from tests.codex_pdf.trace import require


def selected_records(calls, parents):
    buffers, records, available = {}, {}, set()
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        if args["op"] == "read_pdf_page":
            page = result["page"]
            key = canonical(page["evidence"])
            if page["next_text_offset"] is None and key in parents:
                available.add(key)
        elif args["op"] == "read_selection":
            key = canonical(result["evidence"])
            start, end = result["excerpt_char_range"]
            if start == 0:
                buffers[key] = ""
            require(
                start == args.get("text_offset", 0) == len(buffers.get(key, "")),
                "Noncontiguous selection read",
            )
            require(
                end == start + len(result["text_excerpt"]), "Selection range mismatch"
            )
            buffers[key] += result["text_excerpt"]
            if result["next_text_offset"] is not None:
                continue
            require(
                digest(buffers[key].encode()) == result["text_sha256"],
                "Selection page hash mismatch",
            )
            record = json.loads(buffers[key])
            require(
                record["evidence"] == result["evidence"], "Selection evidence mismatch"
            )
            verify_selected_record(record, records)
            requested = args["reference"]
            if requested["schema_version"] == "native-selection-ref-v1":
                require(
                    requested == record["evidence"] and "selection" not in args,
                    "Reread changed reference",
                )
            else:
                require(requested == record["parent"], "Wrong selection parent")
                require(
                    {"pointer": "", "char_range": None, **args.get("selection", {})}
                    == record["selector"],
                    "Wrong requested selector",
                )
            records[key] = record
            available.add(key)
        elif args["op"] == "record_derivation":
            claim = args["derivation"]
            require(
                all(
                    canonical(r) in available
                    for r in [claim["target"], *claim["sources"]]
                ),
                "Assertion precedes complete evidence read",
            )
        elif (
            args["op"] == "verify"
            and args["reference"]["schema_version"] == "native-selection-ref-v1"
        ):
            require(
                canonical(args["reference"]) in records and result["valid"],
                "Selection proof lacks complete readback",
            )
    return records


def verify_selected_record(record, records):
    ref = record["evidence"]
    core = {k: v for k, v in record.items() if k != "evidence"}
    require(
        digest(canonical(core)) == ref["value_sha256"], "Selection core hash mismatch"
    )
    require(
        ref["parent"] == record["parent"] and ref["selector"] == record["selector"],
        "Selection binding mismatch",
    )
    parent = record["parent"]
    require(
        (ref["asset_id"], ref["revision"]) == (parent["asset_id"], parent["revision"]),
        "Selection identity mismatch",
    )
    selector = record["selector"]
    if selector["pointer"] == "":
        require(selector["char_range"] is None, "Invalid complete parent selector")
        require(
            digest(canonical(record["value"])) == parent["value_sha256"],
            "Full parent hash mismatch",
        )
        require(
            record["value"]["locator"] == parent["locator"], "Parent locator mismatch"
        )
    else:
        require(
            selector == {"pointer": "/value", "char_range": {"start": 0, "end": 3}},
            "Unexpected value selector",
        )
        require(
            any(
                r["parent"] == parent
                and r["selector"]["pointer"] == ""
                and r["value"]["value"] == "007"
                for r in records.values()
            ),
            "Missing complete original cell",
        )
        require(record["value"] == "007", "Selected Count differs from scan")
        context = record["text_context"]
        require(
            context["char_range"] == [0, 3] and context["utf8_byte_range"] == [0, 3],
            "Wrong text span",
        )
        require(
            context["prefix"] == context["suffix"] == ""
            and context["source_text_length"] == 3
            and context["source_text_sha256"] == digest(b"007"),
            "Wrong text context",
        )
        require(parent["locator"]["cell"] == "B2", "Wrong native cell")
