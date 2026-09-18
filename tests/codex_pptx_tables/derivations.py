"""Independent ledger/trace/attachment checks for opt-in real Codex provenance runs."""

from tests.codex_native_pdf.artifacts import read_json
from tests.codex_native_pdf.trace import canonical, digest, payload
from tests.codex_pdf.trace import require


def replay(ledger):
    active, seen, replaced, retracted = {}, set(), 0, 0
    for event in ledger["events"]:
        key = event["derivation_id"]
        if event["kind"] == "record":
            claim = event["derivation"]
            require(key == digest(canonical(claim)), "Derivation digest mismatch")
            require(key not in seen, "Repeated derivation identity")
            if claim["supersedes"]:
                require(claim["supersedes"] in active, "Invalid supersession")
                del active[claim["supersedes"]]
                replaced += 1
            active[key] = event
            seen.add(key)
        else:
            require(event["kind"] == "retract" and key in active, "Invalid retraction")
            del active[key]
            retracted += 1
    require(replaced >= 1 and retracted >= 1, "Correction/retraction missing")
    require(len(active) == 1, "Expected one retained derivation")
    return active


def complete_page(result, key, chunks, *, digest_field):
    text = chunks.setdefault(key, "")
    start, end = result["excerpt_char_range"]
    # A preview followed by a fresh read from offset zero is a valid restart.
    # Discard its incomplete prefix; only the new complete hash-checked read counts.
    if start == 0:
        text = ""
    require(
        start == len(text) and end == start + len(result["text_excerpt"]),
        "Noncontiguous readback",
    )
    chunks[key] = text + result["text_excerpt"]
    if result["next_text_offset"] is not None:
        return False
    require(
        digest(chunks[key].encode()) == result[digest_field], "Readback digest mismatch"
    )
    chunks.pop(key)
    return True


def validate_trace(calls, ledger):
    prefix = {**ledger, "events": []}
    observed, available, chunks = set(), set(), {}
    proofs = {}
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        op = args["op"]
        if op in {"read_pdf_page", "read_pptx_shape"}:
            part = result["page" if op == "read_pdf_page" else "shape"]
            key = canonical(part["evidence"])
            if complete_page(part, key, chunks, digest_field="text_sha256"):
                available.add(key)
        elif op == "read_derivations":
            key = result["derivations_sha256"]
            require(
                key == digest(canonical(prefix)),
                "Read ledger differs from trace state",
            )
            if complete_page(result, key, chunks, digest_field="derivations_sha256"):
                observed.add(key)
        elif op in {"record_derivation", "retract_derivation"}:
            validate_mutation(args, result, ledger, prefix, observed, available)
        elif op == "verify_derivation":
            require(result["references_valid"], "Derivation verification failed")
            proofs[result["derivation_id"]] = result["active"]
    require(prefix == ledger, "Stored ledger differs from actual MCP mutation history")
    require(
        digest(canonical(ledger)) in observed,
        "Final ledger lacks complete readback",
    )
    active = replay(ledger)
    ids = {e["derivation_id"] for e in ledger["events"] if e["kind"] == "record"}
    require(
        set(proofs) == ids and all(proofs[i] == (i in active) for i in ids),
        "Missing/incorrect historical derivation proofs",
    )


def validate_mutation(args, result, ledger, prefix, observed, available):
    before = digest(canonical(prefix))
    require(
        args["expected_derivations_sha256"] == before and before in observed,
        "Mutation lacks full pinned ledger read",
    )
    index = len(prefix["events"])
    require(index < len(ledger["events"]), "Unexpected ledger mutation")
    event = ledger["events"][index]
    if args["op"] == "record_derivation":
        claim = args["derivation"]
        normalized = {"supersedes": None, **claim}
        normalized["review"] = {
            "semantic_accuracy": "not_checked",
            "rendered_layout": "not_checked",
            "formula_results": "not_checked",
            "notes": "",
            **claim.get("review", {}),
        }
        require(
            event["kind"] == "record" and event["derivation"] == normalized,
            "Stored assertion differs from submitted input",
        )
        require(
            all(
                canonical(ref) in available
                for ref in [claim["target"], *claim["sources"]]
            ),
            "Derivation lacks prior full endpoint readback",
        )
    else:
        require(
            event == {"kind": "retract", **args["retraction"]},
            "Retraction differs from submitted input",
        )
    prefix["events"].append(event)
    require(
        result["derivations_sha256"] == digest(canonical(prefix)),
        "Mutation result ledger hash mismatch",
    )
    require(
        result["derivation_id"] == event["derivation_id"], "Mutation result ID mismatch"
    )


def validate_derivations(workspace, source, deck, calls, records, source_suffix=None):
    ledger = read_json(
        workspace / "data" / "native-assets" / deck["asset_id"] / "derivations.json"
    )
    require(ledger["asset_id"] == deck["asset_id"], "Wrong ledger target")
    active = replay(ledger)
    for event in ledger["events"]:
        if event["kind"] != "record":
            continue
        claim = event["derivation"]
        target = claim["target"]
        require(
            target["asset_id"] == deck["asset_id"]
            and target["revision"] == deck["revision"],
            "Derivation targets wrong revision",
        )
        require(
            target["schema_version"] == "native-pptx-shape-ref-v1"
            and canonical(target) in records,
            "Missing full table reference",
        )
        require(len(claim["sources"]) == 1, "Unexpected derivation sources")
        ref = claim["sources"][0]
        require(
            ref["asset_id"] == source["asset_id"]
            and ref["revision"] == source["revision"]
            and ref["locator"]["page_index"] == 0
            and canonical(ref) in records,
            "Wrong source page evidence",
        )
        require(
            claim["review"]["rendered_layout"] == "not_checked",
            "Unsupported slide-render claim",
        )
    validate_trace(calls, ledger)
    validate_export(workspace, ledger, active, source, deck, source_suffix)
    return {
        "events": len(ledger["events"]),
        "active_assertions": len(active),
        "complete_ledger_readback": True,
        "source_attachment_exact": True,
    }


def validate_export(workspace, ledger, active, source, deck, source_suffix=None):
    manifests = list((workspace / "native-wiki").rglob("manifest.json"))
    require(len(manifests) == 1, "Expected one derivation wiki")
    root = manifests[0].parent
    manifest = read_json(manifests[0])
    info = manifest["derivations"]
    sha = digest(canonical(ledger))
    require(
        info["ledger_sha256"] == sha
        and read_json(root / info["ledger_file"]) == ledger,
        "Wiki ledger mismatch",
    )
    require(
        set(info["active_ids_for_revision"]) == set(active),
        "Wiki active assertions mismatch",
    )
    identity = {
        "asset_id": deck["asset_id"],
        "revision": deck["revision"],
        "projection": "pptx-shapes-v1",
        "derivations_sha256": sha,
    }
    require(
        manifest["snapshot_id"] == digest(canonical(identity)),
        "Wiki is not pinned to ledger digest",
    )
    attachments = list(info["source_attachments"].values())
    require(len(attachments) == 1, "Expected exact source attachment")
    if source_suffix:
        require(
            attachments[0]["attachment"].endswith(source_suffix),
            "Source extension no longer supports direct native registration",
        )
    require(
        attachments[0]["attachment"].endswith((".pdf", ".bin")),
        "Unexpected source attachment format",
    )
    require(
        (attachments[0]["asset_id"], attachments[0]["revision"])
        == (source["asset_id"], source["revision"]),
        "Wrong attached source identity",
    )
    require(
        (root / attachments[0]["attachment"]).read_bytes()
        == (workspace / "source.pdf").read_bytes(),
        "Source attachment changed",
    )
