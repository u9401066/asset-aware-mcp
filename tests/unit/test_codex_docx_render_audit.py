"""Delivered page images, full page coverage and historical review cannot be faked."""

from __future__ import annotations

import base64
import io
import json

import pytest
from PIL import Image

from tests.codex_docx_structure import renders
from tests.codex_native_pdf.trace import digest


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "revision",
        "index",
        "image",
        "pixels",
        "count",
        "continuation",
        "incomplete",
        "history",
        "word",
        "claimed",
        "findings",
    ],
)
def test_page_auditor_rejects_false_review(tmp_path, monkeypatch, fault):
    workspace = tmp_path / "workspace"
    root = workspace / "data/native-assets/file_test/revisions"
    root.mkdir(parents=True)
    revisions = [digest(data) for data in (b"final", b"historical")]
    for revision, data in zip(revisions, (b"final", b"historical"), strict=True):
        (root / revision).write_bytes(data)
    image = Image.new("RGB", (2, 2), "red")
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    png = stream.getvalue()
    monkeypatch.setattr(renders, "replay", lambda *_: (2, 2, 2, image.tobytes()))
    calls, pages = [], []
    for revision in revisions:
        for index in range(2):
            args = {
                "op": "render_docx_page",
                "asset_id": "file_test",
                "revision": revision,
                "docx_page_index": index,
            }
            result = {
                "inspected_revision": revision,
                "page_index": index,
                "docx_page_index": index,
                "image_sha256": digest(png),
                "page_count": 2,
                "next_page_index": 1 if index == 0 else None,
                "renderer": {"name": "LibreOffice Writer", "version": "test"},
                "rendering_scope": "static_libreoffice_document_page_preview",
            }
            content = [
                {"type": "text", "text": json.dumps(result)},
                {"type": "image", "data": base64.b64encode(png).decode()},
            ]
            calls.append(
                {"arguments": {"native_request": args}, "result": {"content": content}}
            )
            pages.append({"revision": revision, "page_index": index})
    review = {
        "scope": "static_libreoffice_document_page_preview",
        "word_checked": False,
        "reviewed_pages": pages,
        "findings": ["Synthetic page is red"],
    }
    first = json.loads(calls[0]["result"]["content"][0]["text"])
    replacements = {
        "revision": ("inspected_revision", "wrong"),
        "index": ("page_index", 1),
        "count": ("page_count", 1),
        "continuation": ("next_page_index", None),
    }
    if fault in replacements:
        key, value = replacements[fault]
        first[key] = value
        calls[0]["result"]["content"][0]["text"] = json.dumps(first)
    if fault == "image":
        calls[0]["result"]["content"].pop()
    if fault == "pixels":
        monkeypatch.setattr(renders, "replay", lambda *_: (2, 2, 2, b"0" * 12))
    if fault == "incomplete":
        calls.pop()
    if fault == "word":
        review["word_checked"] = True
    if fault == "claimed":
        pages.pop()
    if fault == "findings":
        review["findings"] = []
    historical = {"wrong"} if fault == "history" else {revisions[1]}
    args = (
        workspace,
        {"asset_id": "file_test", "revision": revisions[0]},
        calls,
        {"visual_review": review},
        historical,
    )
    if fault:
        with pytest.raises(ValueError):
            renders.validate_renders(*args)
    else:
        assert renders.validate_renders(*args)["images"] == 4
