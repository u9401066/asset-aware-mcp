"""Accept exact candidate bytes only after exhaustive, reference-bound frame intent."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from src.domain.native_asset_models import NativeEditResult
from src.domain.native_image_evidence import image_catalog, image_frame_reference

if TYPE_CHECKING:
    from src.domain.native_image import (
        NativeImageFrameReference,
        NativeImageRevisionPlan,
    )

PIXEL_FIELDS = (
    "displayed_size_px",
    "decoded_mode",
    "decoded_bits_per_sample",
    "source_bits_per_sample",
    "decoded_pixels_sha256",
    "decoded_rgba8_sha256",
)
PRESENTATION_FIELDS = (
    "stored_size_px",
    "source_orientation",
    "frame_role",
    "duration_ms",
    "loop",
    "disposal",
    "blend",
    "disposal_extent",
)


def validate_image_candidate(
    before_data: bytes,
    after_data: bytes,
    before_records: list[dict[str, Any]],
    after_records: list[dict[str, Any]],
    plan: NativeImageRevisionPlan,
    asset_id: str,
) -> NativeEditResult:
    before_sha, after_sha = (
        hashlib.sha256(data).hexdigest() for data in (before_data, after_data)
    )
    catalog = image_catalog(before_data, before_records)
    if not after_records:
        raise ValueError("Candidate image contains no frames")
    if catalog["catalog_sha256"] != plan.expected_catalog_sha256:
        raise ValueError("Image revision plan uses a stale catalog")
    if plan.candidate.revision != after_sha:
        raise ValueError(
            "Candidate image bytes do not match their complete file reference"
        )
    if before_records[0]["format"] != after_records[0]["format"]:
        raise ValueError(
            "Image revision cannot silently change the detected file format"
        )
    seen_before: set[int] = set()
    seen_after: set[int] = set()
    changes: list[dict[str, Any]] = [
        {
            "kind": "candidate_container",
            "candidate": plan.candidate.model_dump(mode="json"),
            "source_revision": before_sha,
            "expected_catalog_sha256": plan.expected_catalog_sha256,
            "container_policy": plan.container_policy,
            "container_bytes_changed": before_data != after_data,
        }
    ]

    def check(
        reference: NativeImageFrameReference,
        records: list[dict[str, Any]],
        expected_asset: str,
        expected_revision: str,
        seen: set[int],
    ) -> dict[str, Any]:
        if (reference.asset_id, reference.revision) != (
            expected_asset,
            expected_revision,
        ):
            raise ValueError(
                "Image mapping contains a foreign or stale frame reference"
            )
        index = reference.locator.frame_index
        if index in seen or index >= len(records):
            raise ValueError("Image mapping repeats a frame or uses an invalid index")
        record = records[index]
        if (
            image_frame_reference(record, expected_asset, expected_revision)
            != reference
        ):
            raise ValueError(
                "Image mapping frame representation does not match its reference"
            )
        seen.add(index)
        return record

    for item in plan.frames:
        before = (
            check(item.before, before_records, asset_id, before_sha, seen_before)
            if item.op != "insert"
            else None
        )
        after = (
            check(
                item.after,
                after_records,
                plan.candidate.asset_id,
                after_sha,
                seen_after,
            )
            if item.op != "delete"
            else None
        )
        changed_fields = []
        if item.op == "map":
            assert before is not None and after is not None
            changed_fields = [
                key
                for key in (*PIXEL_FIELDS, *PRESENTATION_FIELDS, "metadata")
                if before[key] != after[key]
            ]
            if item.pixels == "preserve_decoded":
                if any(before[key] != after[key] for key in PIXEL_FIELDS):
                    raise ValueError(
                        "A frame declared preserve_decoded has changed pixels, mode or geometry"
                    )
                source_bits = before["source_bits_per_sample"]
                decoded_bits = before["decoded_bits_per_sample"]
                if before_data != after_data and (
                    not source_bits
                    or not decoded_bits
                    or max(source_bits) > decoded_bits
                ):
                    raise ValueError(
                        "Decoder precision cannot prove preserved source samples; declare replacement explicitly"
                    )
            if item.metadata == "preserve_decoder_metadata" and any(
                before[key] != after[key] for key in (*PRESENTATION_FIELDS, "metadata")
            ):
                raise ValueError(
                    "A frame declared preserve_decoder_metadata has changed metadata or presentation"
                )
        changes.append(
            {
                "intent": item.model_dump(mode="json"),
                "changed_fields": changed_fields,
                "before_record_sha256": item.before.value_sha256
                if item.op != "insert"
                else None,
                "after_record_sha256": item.after.value_sha256
                if item.op != "delete"
                else None,
            }
        )
    if seen_before != set(range(len(before_records))) or seen_after != set(
        range(len(after_records))
    ):
        raise ValueError(
            "Image revision plan must account for every source and candidate frame exactly once"
        )
    return NativeEditResult(
        changed_parts=[] if before_data == after_data else ["image_container"],
        preserved_parts=len(before_records) if before_data == after_data else 0,
        changes=changes,
        checks=[
            "source_and_candidate_sha256",
            "complete_frame_correspondence",
            "full_before_after_frame_references",
            "declared_decoded_pixel_preservation",
            "declared_decoder_metadata_preservation",
            "candidate_decoded_readback",
            "exact_candidate_bytes_no_reencoding",
        ],
        review_required=[
            "actual_frame_appearance",
            "meaning_and_transcription",
            "metadata_changes",
            "animation_timing_and_viewer_behavior",
            "private_container_fields",
        ],
    )
