import hashlib
import io

import pytest
from PIL import Image
from pydantic import ValidationError

from src.domain.native_file_reference import NativeFileReference
from src.domain.native_image import (
    NativeImageFrameDelete,
    NativeImageFrameInsert,
    NativeImageFrameMap,
    NativeImageRevisionPlan,
)
from src.domain.native_image_evidence import image_catalog, image_frame_reference
from src.infrastructure.native_image_document import NativeImage
from tests.native_image_helpers import encoded

SOURCE_ID, CANDIDATE_ID = "file_" + "a" * 32, "file_" + "b" * 32


def references(data, asset_id):
    records = NativeImage().records(data)
    revision = hashlib.sha256(data).hexdigest()
    return records, [image_frame_reference(r, asset_id, revision) for r in records]


def plan_for(before, after, maps):
    records, _ = references(before, SOURCE_ID)
    return NativeImageRevisionPlan(
        candidate=NativeFileReference(
            asset_id=CANDIDATE_ID, revision=hashlib.sha256(after).hexdigest()
        ),
        expected_catalog_sha256=image_catalog(before, records)["catalog_sha256"],
        frames=maps,
        container_policy="accept_exact_candidate_bytes",
    )


def test_candidate_preservation_and_explicit_pixel_metadata_replacement():
    before, after = encoded(), encoded(orientation=6)
    _, old = references(before, SOURCE_ID)
    _, new = references(after, CANDIDATE_ID)
    mapping = NativeImageFrameMap(before=old[0], after=new[0])
    request = plan_for(before, after, [mapping])
    with pytest.raises(ValueError, match="changed pixels"):
        NativeImage().accept_candidate(before, after, request, SOURCE_ID)
    mapping.pixels = "replace"
    with pytest.raises(ValueError, match="changed metadata"):
        NativeImage().accept_candidate(before, after, request, SOURCE_ID)
    mapping.metadata = "replace"
    output, result = NativeImage().accept_candidate(before, after, request, SOURCE_ID)
    assert output == after  # Exact external editor output, never re-encoded.
    assert result.changes[0]["candidate"] == request.candidate.model_dump(mode="json")
    assert result.changes[1]["changed_fields"]


def test_same_bytes_noop_retains_complete_mapping_and_no_changed_parts():
    before = encoded()
    _, old = references(before, SOURCE_ID)
    _, new = references(before, CANDIDATE_ID)
    request = plan_for(
        before, before, [NativeImageFrameMap(before=old[0], after=new[0])]
    )
    output, result = NativeImage().accept_candidate(before, before, request, SOURCE_ID)
    assert output == before and result.changed_parts == []
    assert result.changes[1]["changed_fields"] == []


@pytest.mark.parametrize(
    "damage",
    [
        "catalog",
        "candidate",
        "before_hash",
        "after_hash",
        "foreign",
        "missing",
        "duplicate",
    ],
)
def test_forged_or_incomplete_candidate_plans_reject(damage):
    data = encoded()
    _, old = references(data, SOURCE_ID)
    _, new = references(data, CANDIDATE_ID)
    request = plan_for(data, data, [NativeImageFrameMap(before=old[0], after=new[0])])
    if damage == "catalog":
        request.expected_catalog_sha256 = "0" * 64
    elif damage == "candidate":
        request.candidate.revision = "0" * 64
    elif damage == "before_hash":
        old[0].value_sha256 = "0" * 64
    elif damage == "after_hash":
        new[0].value_sha256 = "0" * 64
    elif damage == "foreign":
        old[0].asset_id = CANDIDATE_ID
    elif damage == "missing":
        request.frames = [NativeImageFrameDelete(before=old[0])]
    elif damage == "duplicate":
        request.frames.append(request.frames[0])
    with pytest.raises(ValueError):
        NativeImage().accept_candidate(data, data, request, SOURCE_ID)


def test_complete_frame_deletion_insertion_and_order_are_explicit():
    def tiff(colors):
        pages = [Image.new("RGB", (4, 3), color) for color in colors]
        output = io.BytesIO()
        pages[0].save(output, format="TIFF", save_all=True, append_images=pages[1:])
        return output.getvalue()

    before, after = tiff(["red", "green"]), tiff(["blue", "red"])
    _, old = references(before, SOURCE_ID)
    _, new = references(after, CANDIDATE_ID)
    request = plan_for(
        before,
        after,
        [
            NativeImageFrameDelete(before=old[1]),
            NativeImageFrameInsert(after=new[0]),
            NativeImageFrameMap(before=old[0], after=new[1], metadata="replace"),
        ],
    )
    output, result = NativeImage().accept_candidate(before, after, request, SOURCE_ID)
    assert output == after and len(result.changes) == 4
    assert result.changes[-1]["intent"]["pixels"] == "preserve_decoded"


def test_candidate_format_change_is_not_an_in_place_conversion():
    before, after = encoded(), encoded("JPEG")
    _, old = references(before, SOURCE_ID)
    _, new = references(after, CANDIDATE_ID)
    request = plan_for(
        before,
        after,
        [
            NativeImageFrameMap(
                before=old[0], after=new[0], pixels="replace", metadata="replace"
            )
        ],
    )
    with pytest.raises(ValueError, match="file format"):
        NativeImage().accept_candidate(before, after, request, SOURCE_ID)


def test_unused_intent_fields_and_implicit_container_acceptance_are_rejected():
    _, refs = references(encoded(), SOURCE_ID)
    with pytest.raises(ValidationError):
        NativeImageFrameDelete(before=refs[0], pixels="replace")
    raw = plan_for(
        encoded(), encoded(), [NativeImageFrameMap(before=refs[0], after=refs[0])]
    ).model_dump()
    raw.pop("container_policy")
    with pytest.raises(ValidationError):
        NativeImageRevisionPlan.model_validate(raw)
