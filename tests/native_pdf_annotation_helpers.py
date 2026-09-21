"""Complete annotation readback helpers, shared by service and SDK regressions."""

from __future__ import annotations

import hashlib
import json

from tests.native_workbook_helpers import _call


def complete(service, **fields):
    chunks, offset, digest = [], 0, None
    while True:
        page = _call(service, **fields, text_offset=offset, text_limit=777)[
            "annotation"
        ]
        assert page["excerpt_char_range"][0] == offset
        assert digest is None or digest == page["text_sha256"]
        digest = page["text_sha256"]
        chunks.append(page["text_excerpt"])
        offset = page["next_text_offset"]
        if offset is None:
            break
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == digest
    return json.loads(text)


def catalog(service, asset):
    return complete(
        service,
        op="read_pdf_annotations",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
    )


def read(service, asset, locator=None):
    if locator is None:
        locator = catalog(service, asset)["catalog"]["annotations"][0]["locator"]
    return complete(
        service,
        op="read_pdf_annotation",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        pdf_annotation_locator=locator,
    )


def update(service, asset, edits):
    return _call(
        service,
        op="update_pdf_annotations",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        pdf_annotations_update={"edits": edits},
    )
