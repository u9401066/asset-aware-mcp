"""The live-model auditor rejects missing evidence and independently wrong files."""

from __future__ import annotations

import base64
import copy
import io
import json

import pymupdf
import pytest
from PIL import Image

from tests.codex_native_pdf.artifacts import validate_pdf, validate_transcription
from tests.codex_native_pdf.trace import (
    canonical,
    complete_records,
    completed_calls,
    digest,
    validate_images,
    validate_reference_use,
)
from tests.codex_pdf.fixtures import build_pdf


def call(op, result, **args):
    return {
        "server": "asset_aware_under_test",
        "tool": "document",
        "status": "completed",
        "arguments": {"op": "native", "native_request": {"op": op, **args}},
        "result": {"content": [{"type": "text", "text": json.dumps(result)}]},
    }


def readbacks():
    record = {
        "locator": {"page_index": 0, "object_id": 3, "generation": 0},
        "text": "µg/mL",
    }
    ref = {
        "asset_id": "file_" + "a" * 32,
        "revision": "b" * 64,
        "locator": record["locator"],
        "value_sha256": digest(canonical(record)),
    }
    record["evidence"] = ref
    text = canonical(record).decode()
    calls = []
    for start in range(0, len(text), 100):
        end = min(start + 100, len(text))
        calls.append(
            call(
                "read_pdf_page",
                {
                    "asset_id": ref["asset_id"],
                    "inspected_revision": ref["revision"],
                    "page": {
                        "evidence": ref,
                        "text_excerpt": text[start:end],
                        "excerpt_char_range": [start, end],
                        "text_sha256": digest(text.encode()),
                        "text_length": len(text),
                        "next_text_offset": end if end < len(text) else None,
                    },
                },
                text_offset=start,
            )
        )
    return calls, ref


@pytest.mark.parametrize(
    "failure", [None, "last_chunk", "first_chunk", "hash", "identity"]
)
def test_complete_page_readback_audit(failure):
    calls, ref = readbacks()
    if failure in {"last_chunk", "first_chunk"}:
        calls.pop(-1 if failure == "last_chunk" else 0)
    elif failure:
        item = calls[-1]["result"]["content"][0]
        result = json.loads(item["text"])
        if failure == "hash":
            result["page"]["text_excerpt"] = "x" + result["page"]["text_excerpt"][1:]
        else:
            result["asset_id"] = "file_" + "c" * 32
        item["text"] = json.dumps(result)
    if failure:
        with pytest.raises(ValueError):
            complete_records(calls)
    else:
        assert canonical(ref) in complete_records(calls)


def test_mutation_cannot_use_future_readback():
    calls, ref = readbacks()
    mutation = call("delete_pdf_pages", {"success": True}, pdf_page_refs=[ref])
    with pytest.raises(ValueError, match="without complete"):
        validate_reference_use([mutation, *calls], complete_records(calls), {}, {})


@pytest.mark.parametrize("failure", [None, "missing", "hash"])
def test_actual_image_delivery_audit(failure):
    image = io.BytesIO()
    Image.new("RGB", (2, 2), "white").save(image, "PNG")
    raw = image.getvalue()
    assets = [{"asset_id": name, "revision": name * 64} for name in ("a", "b")]
    calls = []
    for asset in assets:
        for index in range(3):
            item = call(
                "render_pdf_page",
                {
                    **asset,
                    "inspected_revision": asset["revision"],
                    "locator": {"page_index": index},
                    "image_sha256": digest(raw),
                },
            )
            item["result"]["content"].append(
                {"type": "image", "data": base64.b64encode(raw).decode()}
            )
            calls.append(item)
    if failure == "missing":
        calls[-1]["result"]["content"].pop()
    elif failure == "hash":
        calls[-1]["result"]["content"][0]["text"] = calls[-1]["result"]["content"][0][
            "text"
        ].replace(digest(raw), "0" * 64)
    if failure:
        with pytest.raises(ValueError):
            validate_images(calls, *assets)
    else:
        assert validate_images(calls, *assets) == 6


@pytest.mark.parametrize("failure", [None, "rotation", "order", "pixels"])
def test_independent_pdf_pixels(tmp_path, failure):
    source = tmp_path / "source.pdf"
    target = tmp_path / "verified.pdf"
    build_pdf(source, "scanned")
    with pymupdf.open(source) as pdf:
        if failure != "rotation":
            pdf[2].set_rotation(180)
        if failure == "order":
            pdf.select([1, 0, 2])
        if failure == "pixels":
            pdf[0].draw_rect(pymupdf.Rect(1, 1, 30, 30), fill=(1, 0, 0))
        pdf.save(target)
    args = (
        tmp_path,
        {"revision": digest(target.read_bytes())},
        {"exported_pdf": str(target)},
    )
    if failure:
        with pytest.raises(ValueError):
            validate_pdf(*args)
    else:
        validate_pdf(*args)


def test_exact_unicode_and_leading_zero_transcription():
    expected = [{"Count": "003", "Unit": "µg/mL"}]
    validate_transcription(copy.deepcopy(expected), expected)
    for bad in ([{"Count": "003", "Unit": "μg/mL"}], [{"Count": "3", "Unit": "µg/mL"}]):
        with pytest.raises(ValueError, match="exact source truth"):
            validate_transcription(bad, expected)


def test_agent_prose_and_other_tools_cannot_prove_workflow():
    events = [
        {"type": "turn.completed"},
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "All done"},
        },
    ]
    with pytest.raises(ValueError, match="Missing"):
        completed_calls(events)
    events[-1]["item"]["type"] = "command_execution"
    with pytest.raises(ValueError, match="Non-MCP"):
        completed_calls(events)
