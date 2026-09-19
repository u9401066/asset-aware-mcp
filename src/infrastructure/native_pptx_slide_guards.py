"""Reject unresolved slide dependencies and preserve metadata outside explicit edits."""

from __future__ import annotations

import posixpath
from typing import TYPE_CHECKING

from lxml import etree

from src.infrastructure.native_ooxml import (
    DOC_REL_NS,
    relationship_target,
    relationships_path,
)
from src.infrastructure.native_pptx_package import NS, native_id

if TYPE_CHECKING:
    from src.infrastructure.native_pptx_package import NativePptxPackage


def owner_of_relationships(name: str) -> str:
    if name == "_rels/.rels":
        return ""
    directory, filename = posixpath.split(name)
    if posixpath.basename(directory) != "_rels" or not filename.endswith(".rels"):
        raise ValueError("Unsupported relationship part location")
    return posixpath.join(posixpath.dirname(directory), filename[:-5])


def structure_guard(package: NativePptxPackage) -> None:
    package.check_editable()
    roots = [package.presentation]
    for kind, target in package.relationships(package.main_part).values():
        if kind in {f"{DOC_REL_NS}/presProps", f"{DOC_REL_NS}/viewProps"}:
            if not target:
                raise ValueError("External presentation settings are unsupported")
            roots.append(package.xml(target))
    if any(
        isinstance(node.tag, str)
        and etree.QName(node).localname in {"sectionLst", "sldRg"}
        for root in roots
        for node in root.iter()
    ):
        raise ValueError(
            "Sections and index-based slide ranges require a structure-aware workflow"
        )


def deletion_guard(package: NativePptxPackage, selected: list[dict[str, str]]) -> None:
    removed = {s["part"] for s in selected}
    slide_list = package.presentation.find("p:sldIdLst", NS)
    assert slide_list is not None
    nodes = [
        n
        for n in slide_list
        if native_id(n.get("id", "")) in {s["slide_id"] for s in selected}
    ]
    relation_ids = {n.get(f"{{{DOC_REL_NS}}}id") for n in nodes}
    for node in package.presentation.iter():
        if node in nodes:
            continue
        if any(
            k.startswith("{" + DOC_REL_NS + "}") and v in relation_ids
            for k, v in node.attrib.items()
        ):
            raise ValueError(
                "Slide is referenced by a custom show or other presentation metadata"
            )
    notes: dict[str, set[str]] = {}
    for slide in package.slides:
        for region, part in package.slide_regions(slide):
            if region == "notes":
                notes.setdefault(part, set()).add(slide["part"])
    allowed_owners = removed | {n for n, owners in notes.items() if owners <= removed}
    for name in package.parts:
        if not name.endswith(".rels"):
            continue
        owner = owner_of_relationships(name)
        package.relationships(
            owner
        )  # Validate all IDs and targets before using raw XML.
        for relation in package.xml(name):
            if relation.get("TargetMode") == "External":
                continue
            if relationship_target(owner, relation.get("Target", "")) not in removed:
                continue
            if owner in allowed_owners:
                continue
            if owner == package.main_part and relation.get("Id") in relation_ids:
                continue
            raise ValueError(
                "Slide has an incoming relationship from a retained package part"
            )


def slide_nodes(
    package: NativePptxPackage,
) -> tuple[etree._Element, list[etree._Element]]:
    lists = package.presentation.findall("p:sldIdLst", NS)
    if len(lists) > 1:
        raise ValueError("Ambiguous presentation slide list")
    if not lists:
        node = etree.Element(f"{{{NS['p']}}}sldIdLst")
        # Schema order: masters, notes masters, handout masters, slides, sizes, ...
        index = 0
        for index, child in enumerate(package.presentation):  # noqa: B007 -- insertion boundary after loop
            if child.tag not in {
                f"{{{NS['p']}}}{n}"
                for n in ("sldMasterIdLst", "notesMasterIdLst", "handoutMasterIdLst")
            }:
                break
        else:
            index = len(package.presentation)
        package.presentation.insert(index, node)
    else:
        node = lists[0]
    if any(child.tag != f"{{{NS['p']}}}sldId" for child in node):
        raise ValueError("Unsupported content in slide list")
    return node, list(node)


def relationship_ids(package: NativePptxPackage) -> tuple[str, etree._Element]:
    path = relationships_path(package.main_part)
    package.relationships(package.main_part)
    return path, package.xml(path)
