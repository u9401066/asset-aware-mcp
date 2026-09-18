"""Picture CRUD with source lineage, shared-media isolation and checked readback."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING

from lxml import etree

from src.domain.native_assets import NativeEditResult
from src.domain.native_pptx import NativePptxShapeLocator, shape_representation_sha256
from src.infrastructure.native_ooxml import DOC_REL_NS, xml_bytes
from src.infrastructure.native_pptx_package import NS, NativePptxPackage, shape_identity
from src.infrastructure.native_pptx_picture_nodes import build_picture, picture_image
from src.infrastructure.native_pptx_picture_parts import PictureParts
from src.infrastructure.native_pptx_records import shape_record
from src.infrastructure.native_pptx_shape_edit import _container, _next_id
from src.infrastructure.native_raster_image import inspect_image, preview_image

if TYPE_CHECKING:
    from src.domain.native_file_reference import NativeFileReference
    from src.domain.native_pptx_picture import (
        NativePptxPictureCreate,
        NativePptxPictureReplace,
    )


@dataclass
class PictureChange:
    locator: NativePptxShapeLocator
    expected: etree._Element
    original: etree._Element | None
    source: NativeFileReference
    media_part: str
    image_bytes: bytes


def _source(
    reference: NativeFileReference, sources: dict[str, bytes]
) -> tuple[bytes, dict]:
    data = sources[f"{reference.asset_id}:{reference.revision}"]
    if hashlib.sha256(data).hexdigest() != reference.revision:
        raise ValueError("Stale image source revision")
    return data, inspect_image(data)


def _new_picture(
    package: NativePptxPackage,
    parts: PictureParts,
    item: NativePptxPictureCreate,
    sources: dict[str, bytes],
) -> PictureChange:
    parent = _container(package, item.container)
    data, metadata = _source(item.image, sources)
    node = build_picture(item, data, metadata)
    identity = _next_id(package.roots[item.container.part])
    shape_identity(node).set("id", identity)
    relation, media = parts.embed(item.container.part, data, metadata)
    node.find("p:blipFill/a:blip", NS).set(f"{{{DOC_REL_NS}}}embed", relation)
    extension = parent.find("p:extLst", NS)
    parent.insert(
        parent.index(extension) if extension is not None else len(parent), node
    )
    locator = NativePptxShapeLocator(
        **item.container.model_dump(exclude={"group_shape_id"}), shape_id=identity
    )
    return PictureChange(locator, node, None, item.image, media, data)


def _replacement(
    package: NativePptxPackage,
    parts: PictureParts,
    item: NativePptxPictureReplace,
    sources: dict[str, bytes],
) -> PictureChange:
    ref = item.reference
    if hashlib.sha256(package.original).hexdigest() != ref.revision:
        raise ValueError("Stale presentation revision for picture replacement")
    node, blip, _, _, _ = picture_image(package, ref.locator)
    original_record = next(
        shape_record(loc, shape, parents)
        for loc, shape, parents in package.shapes()
        if loc == ref.locator.model_dump()
    )
    if shape_representation_sha256(original_record) != ref.value_sha256:
        raise ValueError("Stale picture shape representation")
    old = deepcopy(node)
    data, metadata = _source(item.image, sources)
    relation, media = parts.embed(ref.locator.part, data, metadata)
    blip.set(f"{{{DOC_REL_NS}}}embed", relation)
    return PictureChange(ref.locator, node, old, item.image, media, data)


def _verify_shapes(
    before: NativePptxPackage, after: NativePptxPackage, changes: list[PictureChange]
) -> None:
    list(after.shapes())
    for change in changes:
        actual, _, media, raw, _ = picture_image(after, change.locator)
        if media != change.media_part or raw != change.image_bytes:
            raise ValueError("Picture media read-back differs from planned exact bytes")
        if etree.tostring(actual, method="c14n") != etree.tostring(
            change.expected, method="c14n"
        ):
            raise ValueError("Picture shape changed during read-back")
        parent = actual.getparent()
        assert parent is not None
        if change.original is None:
            parent.remove(actual)
        else:
            original_blip = change.original.find("p:blipFill/a:blip", NS)
            actual_blip = actual.find("p:blipFill/a:blip", NS)
            assert original_blip is not None and actual_blip is not None
            actual_blip.set(
                f"{{{DOC_REL_NS}}}embed", original_blip.get(f"{{{DOC_REL_NS}}}embed")
            )
    for part in {c.locator.part for c in changes}:
        if etree.tostring(before.xml(part), method="c14n") != etree.tostring(
            after.roots[part], method="c14n"
        ):
            raise ValueError("Presentation XML changed outside the requested pictures")


def _finish(
    package: NativePptxPackage, parts: PictureParts, changes: list[PictureChange]
) -> tuple[bytes, NativeEditResult]:
    data, modified = parts.serialize({c.locator.part for c in changes})
    checked = NativePptxPackage(data)
    _verify_inventory(package, checked, parts, modified)
    _verify_shapes(package, checked, changes)
    return data, NativeEditResult(
        changed_parts=modified,
        preserved_parts=len(set(package.parts) - set(modified)),
        changes=[
            {
                "operation": "add_picture" if c.original is None else "replace_picture",
                "locator": c.locator.model_dump(),
                "source_reference": c.source.model_dump(),
                "media_part": c.media_part,
                "media_sha256": hashlib.sha256(c.image_bytes).hexdigest(),
                "mapping": "explicit_creation"
                if c.original is None
                else "preserve_existing",
            }
            for c in changes
        ],
        checks=[
            "source_image_revision",
            "image_format_and_resource_limits",
            "exact_embedded_image_bytes",
            "package_inventory_and_untouched_bytes",
            "relationship_and_content_type",
            "shape_readback",
            "unchanged_xml_outside_picture_plan",
        ],
        review_required=[
            "semantic_accuracy",
            "rendered_slide_layout",
            "crop_and_image_mapping",
            "group_transforms",
            "effects_and_color_profiles",
            "accessibility_alt_text",
        ],
    )


def _verify_inventory(
    before: NativePptxPackage,
    after: NativePptxPackage,
    parts: PictureParts,
    modified: list[str],
) -> None:
    if set(after.parts) != set(before.parts) | set(parts.additions):
        raise ValueError("Picture edit changed the package inventory")
    for name, raw in before.parts.items():
        if name not in modified and after.parts[name] != raw:
            raise ValueError("Picture edit changed an untouched package part")
    for name, raw in parts.additions.items():
        if after.parts[name] != raw:
            raise ValueError("Picture edit changed planned addition bytes")
    for name, root in parts.roots.items():
        if after.parts[name] != xml_bytes(root):
            raise ValueError("Picture relationship/content-type readback changed")


def add_pictures(
    data: bytes, items: list[NativePptxPictureCreate], sources: dict[str, bytes]
) -> tuple[bytes, NativeEditResult]:
    if not 1 <= len(items) <= 100:
        raise ValueError("Picture additions require 1..100 items")
    _validate_batch(items, sources)
    package = NativePptxPackage(data)
    package.check_editable()
    list(package.shapes())
    parts = PictureParts(package)
    changes = [_new_picture(package, parts, item, sources) for item in items]
    return _finish(package, parts, changes)


def replace_pictures(
    data: bytes, items: list[NativePptxPictureReplace], sources: dict[str, bytes]
) -> tuple[bytes, NativeEditResult]:
    if not 1 <= len(items) <= 100:
        raise ValueError("Picture replacements require 1..100 items")
    _validate_batch(items, sources)
    if len({item.reference.locator.model_dump_json() for item in items}) != len(items):
        raise ValueError("Duplicate picture replacement target")
    package = NativePptxPackage(data)
    package.check_editable()
    parts = PictureParts(package)
    changes = [_replacement(package, parts, item, sources) for item in items]
    return _finish(package, parts, changes)


def _validate_batch(items: list, sources: dict[str, bytes]) -> None:
    pixels, size = 0, 0
    for item in items:
        data, metadata = _source(item.image, sources)
        pixels += metadata["width_px"] * metadata["height_px"]
        size += len(data)
        if pixels > 64_000_000 or size > 32 * 1024 * 1024:
            raise ValueError("Picture batch exceeds 64 million pixels or 32 MiB")


def read_picture(
    data: bytes, locator: NativePptxShapeLocator, render_size: int | None = None
) -> dict:
    package = NativePptxPackage(data)
    node, _, part, raw, metadata = picture_image(package, locator)
    result = {
        "locator": locator.model_dump(),
        "media_part": part,
        "image": metadata,
        "image_bytes": raw,
        "mapping_xml": etree.tostring(node, encoding="unicode"),
        "preview_scope": "embedded_raster_only; slide_crop_transforms_effects_and_color_management_not_rendered",
    }
    if render_size is not None:
        result["image_png"] = preview_image(raw, render_size)
    return result
