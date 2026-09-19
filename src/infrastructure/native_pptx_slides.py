"""Slide-list CRUD retaining source parts and checking serialized structure."""

from __future__ import annotations

import posixpath
from copy import deepcopy
from typing import TYPE_CHECKING

from lxml import etree

from src.domain.native_assets import NativeEditResult
from src.domain.native_pptx_slides import MAX_SLIDES
from src.infrastructure.native_ooxml import (
    DOC_REL_NS,
    REL_NS,
    TYPE_NS,
    relationships_path,
    xml_bytes,
)
from src.infrastructure.native_ooxml_additions import extend_package
from src.infrastructure.native_pptx_layouts import layouts
from src.infrastructure.native_pptx_package import (
    NS,
    P_NS,
    NativePptxPackage,
    native_id,
)
from src.infrastructure.native_pptx_slide_builder import build_slides
from src.infrastructure.native_pptx_slide_guards import (
    deletion_guard,
    owner_of_relationships,
    relationship_ids,
    slide_nodes,
    structure_guard,
)

if TYPE_CHECKING:
    from src.domain.native_pptx_slides import NativePptxSlideInsert, NativePptxSlideKey


SLIDE_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"


def _selected(
    package: NativePptxPackage, keys: list[NativePptxSlideKey]
) -> list[dict[str, str]]:
    values = [k.model_dump() for k in keys]
    if (
        not values
        or len({k.slide_id for k in keys}) != len(keys)
        or any(v not in package.slides for v in values)
    ):
        raise ValueError("Duplicate, missing or mismatched slide identities")
    return values


def _rid(root: etree._Element) -> str:
    used = {node.get("Id") for node in root}
    for index in range(1, len(used) + 2):
        if f"rId{index}" not in used:
            return f"rId{index}"
    raise ValueError("Relationship identity space exhausted")


def _properties(package: NativePptxPackage, count: int, notes: int) -> dict[str, bytes]:
    result = {}
    kind = f"{DOC_REL_NS}/extended-properties"
    for rel_kind, part in package.relationships("").values():
        if rel_kind != kind:
            continue
        if not part:
            raise ValueError("External extended properties unsupported")
        root = package.xml(part)
        ns = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
        for name, value in (("Slides", count), ("Notes", notes)):
            nodes = root.findall(f"{{{ns}}}{name}")
            if len(nodes) > 1 or any(len(n) for n in nodes):
                raise ValueError("Ambiguous presentation count properties")
            if nodes:
                nodes[0].text = str(value)
        if xml_bytes(root) != package.parts[part]:
            result[part] = xml_bytes(root)
    return result


def _finish(
    package: NativePptxPackage,
    expected: list[dict[str, str]],
    replacements: dict[str, bytes],
    additions: dict[str, bytes],
    operation: str,
    affected: list[dict[str, str]],
) -> tuple[bytes, NativeEditResult]:
    if len(expected) > MAX_SLIDES:
        raise ValueError("Presentation structure exceeds 2,000 slides")
    notes = sum(
        len(package.slide_regions(s)) > 1 for s in package.slides if s in expected
    )
    replacements.update(_properties(package, len(expected), notes))
    replacements = {
        p: raw for p, raw in replacements.items() if raw != package.parts[p]
    }
    if not replacements and not additions:
        data = package.original
    else:
        data = extend_package(package, replacements, additions)
    after = NativePptxPackage(data)
    if after.slides != expected:
        raise ValueError("Presentation slide ordering differs on read-back")
    list(after.shapes())
    for part in additions:
        if not part.endswith(".rels"):
            continue
        owner = posixpath.join(
            posixpath.dirname(posixpath.dirname(part)), posixpath.basename(part)[:-5]
        )
        for _, target in after.relationships(owner).values():
            if target and target not in after.parts:
                raise ValueError("New slide relationship does not resolve")
    restored = deepcopy(after.presentation)
    original = package.xml(package.main_part)
    new_list, old_list = (
        restored.find("p:sldIdLst", NS),
        original.find("p:sldIdLst", NS),
    )
    if new_list is not None:
        if old_list is None:
            restored.remove(new_list)
        else:
            restored.replace(new_list, deepcopy(old_list))
    if etree.tostring(restored, method="c14n") != etree.tostring(
        original, method="c14n"
    ):
        raise ValueError("Presentation metadata changed outside the slide list")
    return data, NativeEditResult(
        changed_parts=sorted(set(replacements) | set(additions)),
        preserved_parts=len(package.parts) - len(replacements),
        changes=[
            {"operation": operation, "slides": affected, "slide_count": len(expected)}
        ],
        checks=[
            "revision_bound_slide_identities",
            "known_slide_dependencies",
            "destination_layout_relationships",
            "serialized_slide_order",
            "untouched_part_bytes",
            "presentation_xml_outside_slide_list",
            "bounded_component_inventory",
        ],
        review_required=[
            "slide_order_meaning",
            "rendered_layout",
            "inherited_formatting",
            "unmodeled_slide_dependencies",
            "cached_document_properties",
        ],
    )


def add_slides(
    data: bytes, request: NativePptxSlideInsert
) -> tuple[bytes, NativeEditResult]:
    package = NativePptxPackage(data)
    structure_guard(package)
    if (
        request.index > len(package.slides)
        or len(package.slides) + len(request.slides) > MAX_SLIDES
    ):
        raise ValueError("Slide insertion boundary or count exceeds current structure")
    layout_roots = {part: root for _, part, root in layouts(package)}
    roots = build_slides(data, request, layout_roots)
    target, _ = slide_nodes(package)
    rel_path, rels = relationship_ids(package)
    types = package.xml("[Content_Types].xml")
    reserved = set(package.parts)
    reserved.update(item.get("PartName", "").lstrip("/") for item in types)
    for name in package.parts:
        if name.endswith(".rels"):
            reserved.update(
                target
                for _, target in package.relationships(
                    owner_of_relationships(name)
                ).values()
                if target
            )
    additions: dict[str, bytes] = {}
    created = []
    identity = max((int(s["slide_id"]) for s in package.slides), default=255)
    for offset, (item, root) in enumerate(zip(request.slides, roots, strict=True)):
        identity = max(identity + 1, 256)
        if identity > 2147483647:
            raise ValueError("Presentation slide identity space exhausted")
        index = 1
        while True:
            part = posixpath.join(
                posixpath.dirname(package.main_part),
                "slides",
                f"nativeSlide{index}.xml",
            )
            if (
                part not in reserved
                and part not in additions
                and relationships_path(part) not in reserved
            ):
                break
            index += 1
        rid = _rid(rels)
        etree.SubElement(
            rels,
            f"{{{REL_NS}}}Relationship",
            Id=rid,
            Type=f"{DOC_REL_NS}/slide",
            Target=posixpath.relpath(part, posixpath.dirname(package.main_part)),
        )
        node = etree.Element(f"{{{P_NS}}}sldId", id=str(identity))
        node.set(f"{{{DOC_REL_NS}}}id", rid)
        target.insert(request.index + offset, node)
        slide_rels = etree.Element(f"{{{REL_NS}}}Relationships", nsmap={None: REL_NS})
        etree.SubElement(
            slide_rels,
            f"{{{REL_NS}}}Relationship",
            Id="rId1",
            Type=f"{DOC_REL_NS}/slideLayout",
            Target=posixpath.relpath(item.layout_part, posixpath.dirname(part)),
        )
        additions[part] = xml_bytes(root)
        additions[relationships_path(part)] = xml_bytes(slide_rels)
        etree.SubElement(
            types, f"{{{TYPE_NS}}}Override", PartName="/" + part, ContentType=SLIDE_TYPE
        )
        created.append({"slide_id": str(identity), "part": part})
    expected = (
        package.slides[: request.index] + created + package.slides[request.index :]
    )
    return _finish(
        package,
        expected,
        {
            package.main_part: xml_bytes(package.presentation),
            rel_path: xml_bytes(rels),
            "[Content_Types].xml": xml_bytes(types),
        },
        additions,
        "add_slides",
        created,
    )


def delete_slides(
    data: bytes, keys: list[NativePptxSlideKey]
) -> tuple[bytes, NativeEditResult]:
    if not 1 <= len(keys) <= 100:
        raise ValueError("Slide deletion requires 1..100 identities")
    package = NativePptxPackage(data)
    structure_guard(package)
    selected = _selected(package, keys)
    deletion_guard(package, selected)
    target, nodes = slide_nodes(package)
    rel_path, rels = relationship_ids(package)
    identities = {s["slide_id"] for s in selected}
    removed_rids = set()
    for node in nodes:
        if native_id(node.get("id", "")) in identities:
            removed_rids.add(node.get(f"{{{DOC_REL_NS}}}id"))
            target.remove(node)
    for relation in list(rels):
        if relation.get("Id") in removed_rids:
            rels.remove(relation)
    expected = [s for s in package.slides if s not in selected]
    return _finish(
        package,
        expected,
        {package.main_part: xml_bytes(package.presentation), rel_path: xml_bytes(rels)},
        {},
        "delete_slides_retaining_parts",
        selected,
    )


def reorder_slides(
    data: bytes, keys: list[NativePptxSlideKey]
) -> tuple[bytes, NativeEditResult]:
    package = NativePptxPackage(data)
    structure_guard(package)
    selected = _selected(package, keys)
    if len(selected) != len(package.slides):
        raise ValueError("Slide order must be a complete permutation")
    target, nodes = slide_nodes(package)
    by_id = {native_id(n.get("id", "")): n for n in nodes}
    for node in nodes:
        target.remove(node)
    for key in keys:
        target.append(by_id[key.slide_id])
    return _finish(
        package,
        selected,
        {package.main_part: xml_bytes(package.presentation)},
        {},
        "reorder_slides",
        selected,
    )
