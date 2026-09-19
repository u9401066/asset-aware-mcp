"""Reject falsely attributed, corrupted or unreviewed whole-slide evidence."""

import base64
import copy
import io
import json

import pytest
from PIL import Image

from src.domain.native_pptx_slides import NativePptxSlideKey
from src.infrastructure.native_pptx import NativePresentation
from tests.codex_native_pdf.trace import digest
from tests.codex_pptx_tables import renders
from tests.codex_pptx_tables.slides import slide_keys
from tests.native_pptx_render_helpers import colored_deck


@pytest.fixture
def preview_history(tmp_path, monkeypatch):
    original = colored_deck()
    changed, _ = NativePresentation().reorder_slides(
        original, [NativePptxSlideKey(**key) for key in reversed(slide_keys(original))]
    )
    asset_id = "file_" + "a" * 32
    root = tmp_path / "data/native-assets" / asset_id / "revisions"
    root.mkdir(parents=True)
    image = Image.new("RGB", (64, 48), "green")
    output = io.BytesIO()
    image.save(output, "PNG")
    png = output.getvalue()
    monkeypatch.setattr(renders, "replay", lambda *_: (64, 48, image.tobytes()))
    calls = []
    for data in (original, changed):
        revision = digest(data)
        (root / revision).write_bytes(data)
        key = slide_keys(data)[0]
        metadata = {
            "inspected_revision": revision,
            "image_sha256": digest(png),
            "pptx_slide_key": key,
            "slide_index": 0,
            "rendering_scope": "static_libreoffice_slide_preview",
            "renderer": {"name": "LibreOffice Impress"},
        }
        calls.append(
            {
                "arguments": {
                    "native_request": {
                        "op": "render_pptx_slide",
                        "asset_id": asset_id,
                        "revision": revision,
                        "pptx_slide_key": key,
                        "render_size": 64,
                    }
                },
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(metadata)},
                        {"type": "image", "data": base64.b64encode(png).decode()},
                    ]
                },
            }
        )
    deck = {"asset_id": asset_id, "revision": digest(changed)}
    final = {
        "visual_review": {
            "scope": "static_libreoffice_slide_preview",
            "powerpoint_checked": False,
            "reviewed_revisions": [digest(original), digest(changed)],
            "findings": ["A static preview was inspected; no animation review."],
        }
    }
    return tmp_path, deck, calls, final


def test_independent_preview_audit_accepts_bound_pixels(preview_history):
    result = renders.validate_renders(*preview_history)
    assert result["images"] == result["revisions"] == 2
    assert result["independent_pixels_match"] is True


@pytest.mark.parametrize(
    "fault",
    ["hash", "slide", "missing_image", "powerpoint", "unseen", "history", "pixels"],
)
def test_independent_preview_audit_rejects_corruption(
    preview_history, monkeypatch, fault
):
    workspace, deck, calls, final = copy.deepcopy(preview_history)
    metadata = json.loads(calls[0]["result"]["content"][0]["text"])
    if fault == "hash":
        metadata["image_sha256"] = "0" * 64
    elif fault == "slide":
        metadata["slide_index"] = 2
    elif fault == "missing_image":
        calls[0]["result"]["content"].pop()
    elif fault == "powerpoint":
        final["visual_review"]["powerpoint_checked"] = True
    elif fault == "unseen":
        final["visual_review"]["reviewed_revisions"].append("b" * 64)
    elif fault == "history":
        calls = calls[:1]
    else:
        monkeypatch.setattr(renders, "replay", lambda *_: (64, 48, b"changed"))
    calls[0]["result"]["content"][0]["text"] = json.dumps(metadata)
    with pytest.raises(ValueError):
        renders.validate_renders(workspace, deck, calls, final)
