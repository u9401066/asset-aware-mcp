"""Hash-complete native raster reads for service and actual SDK2 tests."""

import hashlib
import json

from tests.native_workbook_helpers import _call


def complete(service, **fields):
    chunks, offset, digest = [], 0, None
    while True:
        page = _call(service, **fields, text_offset=offset, text_limit=733)["image"]
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
        service, op="read_image", asset_id=asset["asset_id"], revision=asset["revision"]
    )


def frame(service, asset, index=0):
    return complete(
        service,
        op="read_image_frame",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        image_locator={"frame_index": index},
    )


def update(service, asset, candidate, mappings):
    return _call(
        service,
        op="update_image",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        image_update={
            "candidate": candidate["file_reference"],
            "expected_catalog_sha256": catalog(service, asset)["catalog"][
                "catalog_sha256"
            ],
            "frames": mappings,
            "container_policy": "accept_exact_candidate_bytes",
        },
    )
