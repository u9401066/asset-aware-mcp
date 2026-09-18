"""Scoped shape-tree CRUD preserving unrelated XML and every package member."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING

from lxml import etree

from src.domain.native_assets import NativeEditResult
from src.domain.native_pptx import (
    NativePptxShapeLocator,
    shape_representation_sha256,
    validate_shape_additions,
)
from src.infrastructure.native_ooxml import xml_bytes
from src.infrastructure.native_pptx_package import (
    A_NS,
    NS,
    NativePptxPackage,
    native_id,
    shape_identity,
)
from src.infrastructure.native_pptx_records import shape_record
from src.infrastructure.native_pptx_shape_builder import build_textboxes

if TYPE_CHECKING:
    from collections.abc import Iterator

    from src.domain.native_pptx import (
        NativePptxReference,
        NativePptxShapeContainer,
        NativePptxShapeCreate,
    )
    from src.domain.native_pptx_table import NativePptxTableAddition


@dataclass
class ShapeChange:
    locator: NativePptxShapeLocator
    parent_id: str | None
    index: int
    node: etree._Element
    removed_count: int = 0


def _parent(root: etree._Element, group_id: str | None) -> etree._Element:
    if group_id is None:
        tree = root.find("p:cSld/p:spTree", NS)
        if tree is None:
            raise ValueError("Missing presentation shape tree")
        return tree
    for group in root.findall(".//p:grpSp", NS):
        if native_id(shape_identity(group).get("id", "")) == group_id:
            return group
    raise ValueError("Presentation group container does not resolve")


def _container(
    package: NativePptxPackage, locator: NativePptxShapeContainer
) -> etree._Element:
    slide = next((s for s in package.slides if s["slide_id"] == locator.slide_id), None)
    if slide is None or (locator.region, locator.part) not in package.slide_regions(
        slide
    ):
        raise ValueError(
            "Presentation container does not match slide/region relationships"
        )
    parent = _parent(
        package.shape_root(locator.part, locator.region), locator.group_shape_id
    )
    if locator.group_shape_id is not None:
        for kind in ("ext", "chExt"):
            extent = parent.find(f"p:grpSpPr/a:xfrm/a:{kind}", NS)
            if extent is None or any(
                int(extent.get(axis, "0")) <= 0 for axis in ("cx", "cy")
            ):
                raise ValueError(
                    "Group needs nonzero extents before adding local-coordinate shapes"
                )
    return parent


def _shape_references(root: etree._Element) -> Iterator[tuple[etree._Element, str]]:
    for node in root.iter():
        for attribute, value in node.attrib.items():
            name = etree.QName(attribute).localname.lower()
            connection = (
                node.tag in {f"{{{A_NS}}}stCxn", f"{{{A_NS}}}endCxn"} and name == "id"
            )
            if (
                (connection or name in {"spid", "shapeid"})
                and value.isascii()
                and value.isdigit()
            ):
                yield node, native_id(value)


def _next_id(root: etree._Element) -> str:
    values = [
        int(native_id(node.get("id", ""))) for node in root.findall(".//p:cNvPr", NS)
    ]
    values.extend(int(value) for _, value in _shape_references(root))
    identity = max(values, default=0) + 1
    if identity > 4294967295:
        raise ValueError("Presentation shape identity space is exhausted")
    return str(identity)


def _append_shape(
    package: NativePptxPackage,
    item: NativePptxShapeCreate | NativePptxTableAddition,
    node: etree._Element,
    *,
    name: str | None = None,
) -> ShapeChange:
    parent = _container(package, item.container)
    root = package.roots[item.container.part]
    identity = _next_id(root)
    props = shape_identity(node)
    props.set("id", identity)
    props.set("name", name if name is not None else f"TextBox {identity}")
    extension = parent.find("p:extLst", NS)
    index = parent.index(extension) if extension is not None else len(parent)
    parent.insert(index, node)
    locator = NativePptxShapeLocator(
        **item.container.model_dump(exclude={"group_shape_id"}), shape_id=identity
    )
    return ShapeChange(locator, item.container.group_shape_id, index, node)


def _deletions(
    package: NativePptxPackage, references: list[NativePptxReference]
) -> list[ShapeChange]:
    records = {
        NativePptxShapeLocator.model_validate(locator).model_dump_json(): (
            locator,
            node,
            parents,
        )
        for locator, node, parents in package.shapes()
    }
    changes, selected = [], set()
    for reference in references:
        key = reference.locator.model_dump_json()
        if key in selected or key not in records:
            raise ValueError("Duplicate or unresolved presentation shape deletion")
        selected.add(key)
        locator, node, parents = records[key]
        if (
            shape_representation_sha256(shape_record(locator, node, parents))
            != reference.value_sha256
        ):
            raise ValueError("Stale presentation shape representation")
        parent = node.getparent()
        assert parent is not None
        changes.append(
            ShapeChange(
                reference.locator,
                parents[-1] if parents else None,
                parent.index(node),
                node,
                len(node.findall(".//p:cNvPr", NS)),
            )
        )
    nodes = {change.node for change in changes}
    if any(any(parent in nodes for parent in node.iterancestors()) for node in nodes):
        raise ValueError("Overlapping ancestor/descendant shape deletions")
    return changes


def _remove_shapes(package: NativePptxPackage, changes: list[ShapeChange]) -> None:
    removed: dict[str, set[str]] = {}
    for change in changes:
        removed.setdefault(change.locator.part, set()).update(
            native_id(node.get("id", ""))
            for node in change.node.findall(".//p:cNvPr", NS)
        )
        parent = change.node.getparent()
        assert parent is not None
        parent.remove(change.node)
    for part, identities in removed.items():
        if any(
            identity in identities
            for _, identity in _shape_references(package.roots[part])
        ):
            raise ValueError(
                "Surviving shape reference prevents deletion; review connectors/timing/build dependencies"
            )


def _verify_changes(
    before: NativePptxPackage,
    after: NativePptxPackage,
    changes: list[ShapeChange],
    deleting: bool,
) -> None:
    list(after.shapes())  # Validate all component identities and aggregate limits.
    for change in sorted(
        changes, key=lambda c: (c.locator.part, c.parent_id or "", c.index)
    ):
        root = after.roots[change.locator.part]
        parent = _parent(root, change.parent_id)
        if deleting:
            removed = {
                native_id(n.get("id", ""))
                for n in change.node.findall(".//p:cNvPr", NS)
            }
            remaining = {
                native_id(n.get("id", "")) for n in root.findall(".//p:cNvPr", NS)
            }
            if removed & remaining:
                raise ValueError("Deleted presentation shape survived read-back")
            parent.insert(change.index, deepcopy(change.node))
        else:
            actual = after.locate(change.locator)
            if etree.tostring(actual, method="c14n") != etree.tostring(
                change.node, method="c14n"
            ):
                raise ValueError("Added presentation shape differs on read-back")
            parent.remove(actual)
    for part in {change.locator.part for change in changes}:
        if etree.tostring(before.xml(part), method="c14n") != etree.tostring(
            after.roots[part], method="c14n"
        ):
            raise ValueError("Presentation changed outside requested shape nodes")


def _finish(
    package: NativePptxPackage, changes: list[ShapeChange], deleting: bool
) -> tuple[bytes, NativeEditResult]:
    changed = sorted({change.locator.part for change in changes})
    updated = package.replace(
        {part: xml_bytes(package.roots[part]) for part in changed}
    )
    checked = NativePptxPackage(updated)
    if set(checked.parts) != set(package.parts) or any(
        checked.parts[name] != data
        for name, data in package.parts.items()
        if name not in changed
    ):
        raise ValueError("Presentation package changed outside planned parts")
    _verify_changes(package, checked, changes, deleting)
    return updated, NativeEditResult(
        changed_parts=changed,
        preserved_parts=len(package.parts) - len(changed),
        changes=[
            {
                "operation": "delete_shape" if deleting else "add_shape",
                "locator": change.locator.model_dump(),
                "removed_components": change.removed_count,
            }
            for change in changes
        ],
        checks=[
            "shape_identity_preconditions",
            "known_shape_reference_dependencies",
            "exact_package_inventory",
            "untouched_part_bytes",
            "shape_read_back",
            "unchanged_xml_outside_shape_nodes",
        ],
        review_required=[
            "semantic_accuracy",
            "rendered_layout",
            "z_order",
            "text_overflow",
            "inherited_formatting",
            "unmodeled_shape_dependencies",
        ],
    )


def add_shapes(
    data: bytes, additions: list[NativePptxShapeCreate]
) -> tuple[bytes, NativeEditResult]:
    if not 1 <= len(additions) <= 100:
        raise ValueError("Presentation shape additions require 1..100 textboxes")
    validate_shape_additions(additions)
    package = NativePptxPackage(data)
    package.check_editable()
    list(package.shapes())
    changes = [
        _append_shape(package, item, node)
        for item, node in zip(additions, build_textboxes(additions), strict=True)
    ]
    return _finish(package, changes, False)


def delete_shapes(
    data: bytes, references: list[NativePptxReference]
) -> tuple[bytes, NativeEditResult]:
    if not 1 <= len(references) <= 100:
        raise ValueError("Presentation shape deletions require 1..100 references")
    package = NativePptxPackage(data)
    package.check_editable()
    changes = _deletions(package, references)
    _remove_shapes(package, changes)
    return _finish(package, changes, True)
