"""Resolve destination layouts through all masters, without assuming layout indices."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from src.infrastructure.native_ooxml import DOC_REL_NS
from src.infrastructure.native_pptx_package import (
    NS,
    P_NS,
    NativePptxPackage,
    native_id,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from lxml import etree


LATENT_PLACEHOLDERS = {"dt", "ftr", "sldNum"}


def placeholders(root: etree._Element) -> list[etree._Element]:
    tree = root.find("p:cSld/p:spTree", NS)
    if tree is None:
        raise ValueError("Missing layout shape tree")
    identities = [native_id(n.get("id", "")) for n in tree.findall(".//p:cNvPr", NS)]
    if len(identities) != len(set(identities)):
        raise ValueError("Duplicate layout shape identity")
    result = []
    for child in tree:
        found = child.findall(".//p:ph", NS)
        if not found:
            continue
        expected = child.find("p:nvSpPr/p:nvPr/p:ph", NS)
        if child.tag != f"{{{P_NS}}}sp" or len(found) != 1 or expected is None:
            raise ValueError("Unsupported layout placeholder structure")
        if expected.get("type", "obj") not in LATENT_PLACEHOLDERS:
            result.append(deepcopy(child))
    return result


def layouts(package: NativePptxPackage) -> Iterator[tuple[str, str, etree._Element]]:
    rels = package.relationships(package.main_part)
    seen_masters: set[str] = set()
    seen_layouts: set[str] = set()
    for master in package.presentation.findall("p:sldMasterIdLst/p:sldMasterId", NS):
        kind, part = rels.get(master.get(f"{{{DOC_REL_NS}}}id", ""), ("", ""))
        if kind != f"{DOC_REL_NS}/slideMaster" or not part or part in seen_masters:
            raise ValueError("Invalid or duplicate presentation master")
        seen_masters.add(part)
        root = package.xml(part)
        if root.tag != f"{{{P_NS}}}sldMaster":
            raise ValueError("Unexpected slide master root")
        targets = package.relationships(part)
        for layout in root.findall("p:sldLayoutIdLst/p:sldLayoutId", NS):
            kind, target = targets.get(layout.get(f"{{{DOC_REL_NS}}}id", ""), ("", ""))
            if (
                kind != f"{DOC_REL_NS}/slideLayout"
                or not target
                or target in seen_layouts
            ):
                raise ValueError("Invalid or duplicate slide layout")
            if max(len(part), len(target)) > 1024:
                raise ValueError("Layout identity exceeds supported path length")
            seen_layouts.add(target)
            node = package.xml(target)
            back = [
                p
                for k, p in package.relationships(target).values()
                if k == f"{DOC_REL_NS}/slideMaster"
            ]
            if node.tag != f"{{{P_NS}}}sldLayout" or back != [part]:
                raise ValueError("Slide layout does not resolve to its owning master")
            yield part, target, node


def read_layouts(data: bytes) -> list[dict[str, Any]]:
    package = NativePptxPackage(data)
    result = []
    for master, part, root in layouts(package):
        common = root.find("p:cSld", NS)
        result.append(
            {
                "part": part,
                "master_part": master,
                "name": (common.get("name", "") if common is not None else "")[:160],
                "type": root.get("type", "")[:80] or None,
                "placeholder_count": len(root.findall(".//p:ph", NS)),
                "insertion_policy": "clone ordinary shape placeholders; inherit date/footer/slide-number",
            }
        )
    return result
