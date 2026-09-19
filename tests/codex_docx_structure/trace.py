"""Audit tool restrictions, complete DFM reads and references before mutations."""

from tests.codex_native_pdf.trace import canonical, digest, payload
from tests.codex_pdf.trace import call_failed, require


def calls_from(events):
    require(any(e["type"] == "turn.completed" for e in events), "Incomplete Codex turn")
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
            "Unexpected tool/server",
        )
        if not call_failed(item):
            calls.append(item)
    observed = {c["arguments"]["native_request"]["op"] for c in calls}
    require(
        {
            "contract",
            "register",
            "read_pdf_page",
            "render_pdf_page",
            "create_docx",
            "read_docx",
            "update_docx",
            "add_docx_blocks",
            "delete_docx_blocks",
            "verify",
            "publish",
            "export_wiki",
            "history",
        }
        <= observed,
        "Incomplete DOCX workflow",
    )
    require("writeback" not in observed, "Unexpected source writeback")
    return calls


def validate_reads(calls, target, source, pdf_records):
    buffers, complete, references, proofs = {}, set(), set(pdf_records), set()
    block_pages = {}
    for call in calls:
        args = call["arguments"]["native_request"]
        result = payload(call)
        operation = args["op"]
        if result.get("asset", {}).get("file_reference"):
            references.add(canonical(result["asset"]["file_reference"]))
        if operation == "read_docx":
            key = (args["asset_id"], result["inspected_revision"])
            require(args.get("revision") == key[1], "Unpinned DFM read")
            dfm = result["dfm"]
            start, end = dfm["excerpt_char_range"]
            require(start == args.get("text_offset", 0), "DFM offset mismatch")
            require(end - start == len(dfm["text_excerpt"]), "DFM range mismatch")
            hash_key = (*key, dfm["text_sha256"])
            if start == 0:
                buffers[hash_key] = ""
            require(len(buffers.get(hash_key, "")) == start, "Missing DFM chunk")
            buffers[hash_key] += dfm["text_excerpt"]
            if dfm["next_text_offset"] is None:
                text = buffers.pop(hash_key)
                require(
                    len(text) == dfm["text_length"]
                    and digest(text.encode()) == hash_key[2],
                    "DFM content hash differs",
                )
                complete.add(key)
            else:
                require(dfm["next_text_offset"] == end, "Bad DFM continuation")
            page = block_pages.setdefault(key, set())
            page.update(
                range(
                    args.get("offset", 0), args.get("offset", 0) + len(result["blocks"])
                )
            )
            if result["next_offset"] is None:
                require(page == set(range(result["block_count"])), "Missing blocks")
            references.update(canonical(b["evidence"]) for b in result["blocks"])
        if operation in {"update_docx", "add_docx_blocks", "delete_docx_blocks"}:
            key = (args["asset_id"], args["expected_revision"])
            require(key in complete, "Mutation precedes complete DFM read")
            refs = args.get("docx_block_refs", [])
            if args.get("docx_insert", {}).get("anchor"):
                refs = [*refs, args["docx_insert"]["anchor"]]
            for reference in refs:
                require(canonical(reference) in references, "Unseen block reference")
                require(
                    (reference["asset_id"], reference["revision"]) == key,
                    "Stale structural reference",
                )
        if operation == "verify":
            reference = args["reference"]
            require(canonical(reference) in references, "Unseen proof reference")
            require(result.get("valid") is True, "Invalid evidence proof")
            if reference["schema_version"] == "native-file-ref-v1":
                continue
            if reference["asset_id"] == source["asset_id"]:
                proofs.add("source")
            elif reference["asset_id"] == target["asset_id"]:
                require(not result["is_current_managed_revision"], "Expected old proof")
                proofs.add(canonical(reference))
    require(not buffers, "Incomplete final DFM chunks")
    require(len(proofs) >= 3 and "source" in proofs, "Missing historical/source proofs")
    require(
        {(target["asset_id"], h["sha256"]) for h in target["history"]} <= complete,
        "A managed DOCX revision lacks complete DFM readback",
    )
    return len(complete)
