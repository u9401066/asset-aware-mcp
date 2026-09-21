"""Independent audit fails closed on missing reads, pixels, crop and frame order."""

import io

import pytest
from PIL import Image

from tests.codex_native_image.checks import covers_row, validate_png, validate_stages
from tests.codex_native_image.trace import calls_from, read_page
from tests.codex_native_pdf.trace import canonical, digest
from tests.native_image_helpers import encoded, grid


def tiff(frames):
    output = io.BytesIO()
    frames[0].save(output, format="TIFF", save_all=True, append_images=frames[1:])
    return output.getvalue()


@pytest.mark.parametrize("fault", [None, "pixel", "orientation", "alpha"])
def test_preview_audit_compares_oriented_pixels_not_self_reported_hash(fault):
    data = encoded("PNG", 6)
    truth = grid().transpose(Image.Transpose.ROTATE_270).convert("RGBA")
    if fault == "pixel":
        truth.putpixel((0, 0), (1, 2, 3, 4))
    elif fault == "orientation":
        truth = truth.transpose(Image.Transpose.ROTATE_180)
    elif fault == "alpha":
        truth.putalpha(254)
    output = io.BytesIO()
    truth.save(output, format="PNG")
    if fault:
        with pytest.raises(ValueError, match="pixels/mode/geometry"):
            validate_png(data, output.getvalue(), 0, 64)
    else:
        validate_png(data, output.getvalue(), 0, 64)


@pytest.mark.parametrize("fault", [None, "order", "count", "canvas", "source"])
def test_stage_audit_rejects_wrong_frames_and_native_sample_drift(fault):
    source = grid()
    crop = source.crop((1, 1, 6, 5))
    blank = Image.new("RGBA", (4, 3), (7, 9, 11, 128))
    stages = [[source, crop], [crop, source, blank], [crop, source]]
    if fault == "order":
        stages[-1].reverse()
    elif fault == "count":
        stages[-1].append(blank)
    elif fault == "canvas":
        stages[1][-1] = blank.convert("RGB")
    elif fault == "source":
        changed = source.copy()
        changed.putpixel((0, 0), (1, 2, 3))
        stages[-1][-1] = changed
    data = [tiff(s) for s in stages]
    if fault:
        with pytest.raises(ValueError):
            validate_stages(data, source, crop)
    else:
        validate_stages(data, source, crop)


@pytest.mark.parametrize(
    "fault", [None, "skip", "hash", "offset", "continuation", "length", "restart"]
)
def test_hash_paging_audit_rejects_missing_or_modified_chunks(fault):
    value = {"metadata": "007 µg", "pixels": "deadbeef"}
    text = canonical(value).decode()
    buffers = {}
    first = {
        "text_excerpt": text[:7],
        "text_sha256": digest(text.encode()),
        "excerpt_char_range": [0, 7],
        "next_text_offset": 7,
        "text_length": len(text),
    }
    assert read_page(buffers, {"op": "read_image_frame"}, first) is None
    args = {"op": "read_image_frame", "text_offset": 7}
    last = {
        **first,
        "text_excerpt": text[7:],
        "excerpt_char_range": [7, len(text)],
        "next_text_offset": None,
    }
    if fault == "skip":
        buffers.clear()
    elif fault == "hash":
        last["text_excerpt"] = last["text_excerpt"].replace("007", "008")
    elif fault == "offset":
        args["text_offset"] = 8
    elif fault == "continuation":
        last["next_text_offset"] = len(text) + 1
    elif fault == "length":
        last["text_length"] += 1
    elif fault == "restart":
        args["text_offset"] = 0
        last = first
    if fault:
        with pytest.raises(ValueError):
            read_page(buffers, args, last)
    else:
        assert read_page(buffers, args, last) == value and not buffers


@pytest.mark.parametrize(
    "rect",
    [
        [0.2, 0.3, 0.8, 0.32],
        [0.2, 0.3, 0.6, 0.32],
        [0.2, 0.319, 0.8, 0.33],
        [0.2, 0.3, 0.8, 0.5],
    ],
)
def test_crop_audit_requires_whole_first_row_and_no_unrelated_rows(rect):
    expected = {
        "derivation": {
            "first_row_text_bounds": [0.25, 0.305, 0.71, 0.319],
            "size_px": [1000, 1400],
        }
    }
    if rect == [0.2, 0.3, 0.8, 0.32]:
        covers_row(rect, expected)
    else:
        with pytest.raises(ValueError):
            covers_row(rect, expected)


@pytest.mark.parametrize(
    "events",
    [
        [],
        [{"type": "turn.completed"}],
        [
            {"type": "turn.completed"},
            {"type": "item.completed", "item": {"type": "command_execution"}},
        ],
    ],
)
def test_audit_rejects_incomplete_workflow_and_non_mcp_actions(events):
    with pytest.raises(ValueError):
        calls_from(events)


@pytest.mark.parametrize(
    "fault", [None, "asset", "revision", "source", "sheet", "omission"]
)
def test_optional_workbook_read_still_requires_complete_source_bound_structure(fault):
    from src.infrastructure.native_workbook_structure import NativeWorkbookStructure
    from tests.codex_native_image.checks import validate_workbook_read
    from tests.native_workbook_helpers import build_workbook

    data = build_workbook()
    args = {
        "op": "read_workbook",
        "asset_id": "file_" + "a" * 32,
        "revision": digest(data),
    }
    record = {
        **NativeWorkbookStructure().read(data),
        "asset_id": args["asset_id"],
        "revision": args["revision"],
        "operation_result": None,
    }
    if fault == "asset":
        record["asset_id"] = "file_" + "b" * 32
    elif fault == "revision":
        record["revision"] = "b" * 64
    elif fault == "source":
        data += b"changed"
    elif fault == "sheet":
        record["worksheets"][0]["name"] = "wrong"
    elif fault == "omission":
        del record["defined_names"]
    if fault:
        with pytest.raises(ValueError):
            validate_workbook_read(args, record, data)
    else:
        validate_workbook_read(args, record, data)


@pytest.mark.parametrize("extra", ["read_workbook", "writeback"])
def test_optional_workbook_read_does_not_allow_unrequested_mutations(extra):
    from tests.codex_native_image.trace import REQUIRED

    events = [{"type": "turn.completed"}] + [
        {
            "type": "item.completed",
            "item": {
                "type": "mcp_tool_call",
                "status": "completed",
                "server": "asset_aware_under_test",
                "tool": "document",
                "arguments": {"op": "native", "native_request": {"op": op}},
            },
        }
        for op in [*REQUIRED, extra]
    ]
    if extra == "read_workbook":
        assert len(calls_from(events)) == len(REQUIRED) + 1
    else:
        with pytest.raises(ValueError, match="Unexpected operation"):
            calls_from(events)


@pytest.mark.parametrize(
    "fault", [None, "scope", "disabled", "policy", "inventory", "formats"]
)
def test_complete_global_policy_covers_operations_but_rejects_missing_capabilities(
    fault,
):
    from src.application.native_document_contract import native_document_contract
    from src.domain.native_assets import NativeDocumentRequest
    from tests.codex_native_image.trace import MUTATIONS, policy_operations

    response = native_document_contract(images_enabled=True)
    buffers, offset = {}, 0
    while True:
        args = {**response["contract_request"], "text_offset": offset}
        page = native_document_contract(
            NativeDocumentRequest.model_validate(args), images_enabled=True
        )
        record = read_page(buffers, args, page)
        if record is not None:
            break
        offset = page["next_text_offset"]
    if fault == "scope":
        record["for_op"] = "update_image"
    elif fault == "disabled":
        record["images_enabled"] = False
    elif fault == "policy":
        del record["image_policy"]
    elif fault == "inventory":
        record["operations"].remove("update_image")
    elif fault == "formats":
        record["formats"] = {}
    if fault:
        with pytest.raises(ValueError):
            policy_operations(record, None)
    else:
        assert policy_operations(record, None) == MUTATIONS
