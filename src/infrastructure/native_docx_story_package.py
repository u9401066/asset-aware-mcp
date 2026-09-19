"""Preserve native dependencies while adding or removing complete Word stories."""

from __future__ import annotations

import posixpath
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.infrastructure.native_docx_stories import W, read_story
from src.infrastructure.native_docx_structure import (
    DEPENDENCIES,
    canonical,
    field_depths,
)
from src.infrastructure.native_docx_workspace import MAIN_PART, checked_docx
from src.infrastructure.native_ooxml import (
    DOC_REL_NS,
    REL_NS,
    TYPE_NS,
    NativeOOXMLPackage,
    relationship_target,
    relationships_path,
    xml_bytes,
)
from src.infrastructure.native_ooxml_additions import extend_package

if TYPE_CHECKING:
    from src.domain.native_docx_story_lifecycle import StoryClone, StoryRemove

TYPES = "[Content_Types].xml"
MAIN_RELS = relationships_path(MAIN_PART)
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
HEX_IDENTITIES = {
    "{http://schemas.microsoft.com/office/word/2010/wordml}paraId",
    "{http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing}anchorId",
    "{http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing}editId",
}
CLONE_BLOCKED = {
    W + n for n in DEPENDENCIES - {"fldChar", "instrText", "fldSimple", "drawing"}
}


def write_package(package: NativeOOXMLPackage, parts: dict[str, bytes]) -> bytes:
    """Restore equal XML spelling, then use checked package inventory mutations."""
    parts = dict(parts)
    for name in parts.keys() & package.parts.keys():
        if parts[name] != package.parts[name] and name.endswith((".xml", ".rels")):
            candidate = etree.fromstring(
                parts[name], etree.XMLParser(resolve_entities=False, no_network=True)
            )
            if canonical(candidate) == canonical(package.xml(name)):
                parts[name] = package.parts[name]
    if parts == package.parts:
        return package.original
    removed = package.parts.keys() - parts.keys()
    replacements = {
        n: raw
        for n, raw in parts.items()
        if n in package.parts and raw != package.parts[n]
    }
    additions = {n: raw for n, raw in parts.items() if n not in package.parts}
    interim = package.replace(replacements, set(removed))
    result = (
        extend_package(NativeOOXMLPackage(interim), {}, additions)
        if additions
        else interim
    )
    if checked_docx(result, for_edit=True).parts != parts:
        raise ValueError("Word story package readback differs from the edit plan")
    return result


def add_type(root: etree._Element, part: str, kind: str) -> None:
    if any(n.get("PartName") == "/" + part for n in root):
        raise ValueError("New Word part content type already exists")
    etree.SubElement(
        root, "{" + TYPE_NS + "}Override", PartName="/" + part, ContentType=kind
    )


def add_relationship(root: etree._Element, kind: str, part: str) -> str:
    used = {n.get("Id") for n in root}
    index = 1
    while f"rId{index}" in used:
        index += 1
    identity = f"rId{index}"
    etree.SubElement(
        root,
        "{" + REL_NS + "}Relationship",
        Id=identity,
        Type=DOC_REL_NS + "/" + kind,
        Target=posixpath.relpath(part, posixpath.dirname(MAIN_PART)),
    )
    return identity


def require_new(package: NativeOOXMLPackage, part: str) -> None:
    names = {n.rstrip("/").casefold() for n in package.parts}
    if part.casefold() in names or relationships_path(part).casefold() in names:
        raise ValueError("New Word story part already exists or has a name collision")
    proposed = {part.casefold(), relationships_path(part).casefold()}
    for name in package.parts:
        if name.endswith(".rels"):
            owner = owner_of_relationships(name)
            if any(
                target.casefold() in proposed
                for _, target in package.relationships(owner).values()
            ):
                raise ValueError(
                    "New Word part would capture an existing dangling relationship"
                )


def require_hash(
    package: NativeOOXMLPackage, part: str, expected: str
) -> dict[str, Any]:
    record = read_story(package, part)
    if record["raw_part_sha256"] != expected:
        raise ValueError("Word story part hash differs from the supplied snapshot")
    return record


def clone_parts(
    package: NativeOOXMLPackage, edit: StoryClone
) -> tuple[dict[str, bytes], list[dict[str, str]]]:
    require_hash(package, edit.source_part, edit.source_part_sha256)
    require_new(package, edit.part)
    root = package.xml(edit.source_part)
    field_depths(root)
    if any(n.tag in CLONE_BLOCKED for n in root.iter()):
        raise ValueError(
            "Story clone has range/control/revision/embedded dependencies requiring identity-aware support"
        )
    changes = []
    used = {
        n.get("id")
        for name in package.parts
        if name.endswith(".xml")
        for n in package.xml(name).iter(WP + "docPr")
    }
    next_id = 1
    for node in root.iter(WP + "docPr"):
        while str(next_id) in used:
            next_id += 1
        value = str(next_id)
        changes.append(
            {"kind": "drawing_id", "before": node.get("id", ""), "after": value}
        )
        node.set("id", value)
        used.add(value)
    for attribute in sorted(HEX_IDENTITIES):
        occupied = {
            value.upper()
            for name in package.parts
            if name.endswith(".xml")
            for node in package.xml(name).iter()
            if (value := node.get(attribute)) is not None
        }
        next_hex = 1
        for node in root.iter():
            previous = node.get(attribute)
            if previous is None:
                continue
            while f"{next_hex:08X}" in occupied:
                next_hex += 1
            value = f"{next_hex:08X}"
            occupied.add(value)
            node.set(attribute, value)
            changes.append({"kind": attribute, "before": previous, "after": value})
    additions = {
        edit.part: xml_bytes(root) if changes else package.parts[edit.source_part]
    }
    rel_part = relationships_path(edit.source_part)
    if rel_part in package.parts:
        rels = package.xml(rel_part)
        package.relationships(edit.source_part)
        for node in rels:
            if node.get("TargetMode") == "External":
                continue
            target = relationship_target(edit.source_part, node.get("Target", ""))
            if target not in package.parts:
                raise ValueError("Cloned story has a missing relationship target")
            node.set("Target", posixpath.relpath(target, posixpath.dirname(edit.part)))
        additions[relationships_path(edit.part)] = xml_bytes(rels)
    return additions, changes


def owner_of_relationships(part: str) -> str:
    if part == "_rels/.rels":
        return ""
    folder, name = posixpath.split(part)
    if posixpath.basename(folder) != "_rels" or not name.endswith(".rels"):
        raise ValueError("Ambiguous OOXML relationships part")
    return posixpath.join(posixpath.dirname(folder), name[:-5])


def remove_parts(
    package: NativeOOXMLPackage, edit: StoryRemove
) -> tuple[dict[str, bytes], list[str]]:
    record = require_hash(package, edit.part, edit.expected_part_sha256)
    if record["bindings"]:
        raise ValueError(
            "Word story remains bound, including dormant/inherited sections"
        )
    own_rels = relationships_path(edit.part)
    removed = {edit.part, own_rels} & package.parts.keys()
    main_rels = package.xml(MAIN_RELS)
    main = package.xml(MAIN_PART)
    prune = set()
    for name in package.parts:
        if not name.endswith(".rels") or name == own_rels:
            continue
        owner = owner_of_relationships(name)
        for identity, (kind, target) in package.relationships(owner).items():
            if target not in removed:
                continue
            if (
                name != MAIN_RELS
                or kind != DOC_REL_NS + "/" + record["locator"]["story_kind"]
            ):
                raise ValueError(
                    "Retained part has an incoming relationship to the deleted story"
                )
            if any(
                value == identity
                for n in main.iter()
                for key, value in n.attrib.items()
                if key.startswith("{" + DOC_REL_NS + "}")
            ):
                raise ValueError(
                    "Story relationship is retained by native or historical XML"
                )
            prune.add(identity)
    for node in list(main_rels):
        if node.get("Id") in prune:
            main_rels.remove(node)
    types = package.xml(TYPES)
    for node in list(types):
        if node.get("PartName", "").lstrip("/") in removed:
            types.remove(node)
    retained = (
        sorted(
            {
                target
                for _, target in package.relationships(edit.part).values()
                if target and target not in removed
            }
        )
        if own_rels in package.parts
        else []
    )
    parts = {n: raw for n, raw in package.parts.items() if n not in removed}
    parts.update({MAIN_RELS: xml_bytes(main_rels), TYPES: xml_bytes(types)})
    return parts, retained
