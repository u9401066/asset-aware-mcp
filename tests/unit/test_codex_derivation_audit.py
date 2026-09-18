"""The opt-in auditor rejects forged history and incomplete chronological readback."""

from copy import deepcopy

import pytest

from tests.codex_native_pdf.trace import canonical, digest
from tests.codex_pptx_tables.derivations import complete_page, replay, validate_mutation


def history():
    first = {
        "target": {"id": "target"},
        "sources": [{"id": "source"}],
        "agent": "test",
        "activity": "transcribe",
        "review": {},
        "supersedes": None,
    }
    first_id = digest(canonical(first))
    second = {**first, "supersedes": first_id, "activity": "correct"}
    second_id = digest(canonical(second))
    temporary = {**first, "activity": "temporary"}
    temporary_id = digest(canonical(temporary))
    return {
        "schema_version": "native-derivations-v1",
        "asset_id": "target",
        "events": [
            {"kind": "record", "derivation_id": first_id, "derivation": first},
            {"kind": "record", "derivation_id": second_id, "derivation": second},
            {"kind": "record", "derivation_id": temporary_id, "derivation": temporary},
            {
                "kind": "retract",
                "derivation_id": temporary_id,
                "agent": "test",
                "reason": "withdraw",
            },
        ],
    }


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "hash",
        "missing_retraction",
        "unknown_retraction",
        "duplicate",
        "wrong_supersession",
    ],
)
def test_ledger_replay_requires_real_correction_and_retraction(failure):
    ledger = history()
    if failure == "hash":
        ledger["events"][0]["derivation"]["agent"] = "forged"
    elif failure == "missing_retraction":
        ledger["events"].pop()
    elif failure == "unknown_retraction":
        ledger["events"][-1]["derivation_id"] = "0" * 64
    elif failure == "duplicate":
        ledger["events"].insert(1, deepcopy(ledger["events"][0]))
    elif failure == "wrong_supersession":
        ledger["events"][1]["derivation"]["supersedes"] = "0" * 64
        ledger["events"][1]["derivation_id"] = digest(
            canonical(ledger["events"][1]["derivation"])
        )
    if failure:
        with pytest.raises(ValueError):
            replay(ledger)
    else:
        assert set(replay(ledger)) == {ledger["events"][1]["derivation_id"]}


@pytest.mark.parametrize("failure", [None, "gap", "wrong_hash"])
def test_full_readback_cannot_skip_or_mix_chunks(failure):
    text = '{"source":"007"}'
    sha = digest(text.encode())
    chunks = {}
    assert not complete_page(
        {
            "excerpt_char_range": [0, 5],
            "text_excerpt": text[:5],
            "next_text_offset": 5,
            "sha": sha,
        },
        "key",
        chunks,
        digest_field="sha",
    )
    result = {
        "excerpt_char_range": [5, len(text)],
        "text_excerpt": text[5:],
        "next_text_offset": None,
        "sha": sha,
    }
    if failure == "gap":
        result["excerpt_char_range"][0] = 6
    elif failure == "wrong_hash":
        result["sha"] = "0" * 64
    if failure:
        with pytest.raises(ValueError):
            complete_page(result, "key", chunks, digest_field="sha")
    else:
        assert complete_page(result, "key", chunks, digest_field="sha")


def test_mutation_requires_prior_complete_ledger_not_just_correct_hash():
    ledger = history()
    prefix = {**ledger, "events": []}
    before = digest(canonical(prefix))
    with pytest.raises(ValueError, match="full pinned ledger"):
        validate_mutation(
            {"expected_derivations_sha256": before}, {}, ledger, prefix, set(), set()
        )


@pytest.mark.parametrize("failure", [None, "missing_endpoint_read", "response_hash"])
def test_record_trace_binds_endpoints_input_and_response(failure):
    claim = history()["events"][0]["derivation"]
    claim["review"] = {
        "semantic_accuracy": "not_checked",
        "rendered_layout": "not_checked",
        "formula_results": "not_checked",
        "notes": "",
    }
    event = {
        "kind": "record",
        "derivation_id": digest(canonical(claim)),
        "derivation": claim,
    }
    prefix = {
        "schema_version": "native-derivations-v1",
        "asset_id": "target",
        "events": [],
    }
    ledger = {**prefix, "events": [event]}
    before = digest(canonical(prefix))
    args = {
        "op": "record_derivation",
        "expected_derivations_sha256": before,
        "derivation": claim,
    }
    response = {
        "derivation_id": event["derivation_id"],
        "derivations_sha256": digest(canonical(ledger)),
    }
    available = {canonical(claim["target"]), canonical(claim["sources"][0])}
    if failure == "missing_endpoint_read":
        available.clear()
    elif failure == "response_hash":
        response["derivations_sha256"] = "0" * 64
    if failure:
        with pytest.raises(ValueError):
            validate_mutation(args, response, ledger, prefix, {before}, available)
    else:
        validate_mutation(args, response, ledger, prefix, {before}, available)
        assert prefix == ledger


@pytest.mark.parametrize(
    "case", ["repeat_preview", "restart_larger", "bad_restarted_hash"]
)
def test_preview_then_restart_requires_a_new_complete_verified_read(case):
    text = '{"source":"007"}'
    sha = digest(text.encode())
    chunks = {}
    first = {
        "excerpt_char_range": [0, 5],
        "text_excerpt": text[:5],
        "next_text_offset": 5,
        "sha": sha,
    }
    assert not complete_page(first, "key", chunks, digest_field="sha")
    size = 8 if case == "restart_larger" else 5
    restart = {
        "excerpt_char_range": [0, size],
        "text_excerpt": text[:size],
        "next_text_offset": size,
        "sha": sha,
    }
    assert not complete_page(restart, "key", chunks, digest_field="sha")
    final = {
        "excerpt_char_range": [size, len(text)],
        "text_excerpt": text[size:],
        "next_text_offset": None,
        "sha": sha,
    }
    if case == "bad_restarted_hash":
        final["text_excerpt"] = final["text_excerpt"].replace("007", "008")
        with pytest.raises(ValueError, match="digest"):
            complete_page(final, "key", chunks, digest_field="sha")
    else:
        assert complete_page(final, "key", chunks, digest_field="sha")
