"""Atomic Word story creation, cloning, binding, unlinking and checked deletion."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from docx.oxml import parse_xml
from lxml import etree

from src.domain.native_asset_models import NativeEditResult
from src.domain.native_docx_stories import STORY_REVIEW
from src.domain.native_docx_story_lifecycle import (
    DocxStoryStructure,
    StoryBind,
    StoryClone,
    StoryCreate,
    StoryEvenPages,
    StoryFirstPage,
    StoryRemove,
    StoryStructureEdit,
)
from src.infrastructure.native_docx_builder import build_blocks
from src.infrastructure.native_docx_stories import (
    KINDS,
    R,
    W,
    catalog,
    onoff,
    story_parts,
)
from src.infrastructure.native_docx_story_package import (
    MAIN_RELS,
    TYPES,
    add_relationship,
    add_type,
    clone_parts,
    remove_parts,
    require_new,
    write_package,
)
from src.infrastructure.native_docx_structure import body_of, canonical
from src.infrastructure.native_docx_structure_checks import check_blocks
from src.infrastructure.native_docx_workspace import MAIN_PART, checked_docx
from src.infrastructure.native_ooxml import DOC_REL_NS, NativeOOXMLPackage, xml_bytes


def sections(main: etree._Element) -> list[etree._Element]:
    body = body_of(main)
    nodes = main.xpath(
        ".//w:sectPr[not(ancestor::w:sectPrChange) and not(ancestor::w:del)]",
        namespaces={"w": W[1:-1]},
    )
    for node in nodes:
        parent = node.getparent()
        if parent is body:
            continue
        if (
            parent is None
            or parent.tag != W + "pPr"
            or parent.getparent() is None
            or parent.getparent().tag != W + "p"
            or parent.getparent().getparent() is not body
        ):
            raise ValueError("Section structure is not a direct Word body section")
    return list(nodes)


def section_at(main: etree._Element, index: int) -> etree._Element:
    items = sections(main)
    if index >= len(items):
        raise ValueError("Word section index does not exist")
    return items[index]


def binding_parts(package: NativeOOXMLPackage, edit: StoryBind) -> dict[str, bytes]:
    main = package.xml(MAIN_PART)
    section = section_at(main, edit.section_index)
    kind = edit.story_kind + "Reference"
    matches = [
        n for n in section.findall(W + kind) if n.get(W + "type") == edit.variant
    ]
    if len(matches) > 1:
        raise ValueError("Ambiguous section story reference")
    current = matches[0] if matches else None
    rels = package.xml(MAIN_RELS)
    original_section = deepcopy(section)
    original_index = list(section).index(current) if current is not None else None
    if edit.part is None:
        if current is not None:
            section.remove(current)
    else:
        if story_parts(package).get(edit.part) != edit.story_kind:
            raise ValueError("Story binding kind and destination part disagree")
        mapping = package.relationships(MAIN_PART)
        if current is not None and mapping.get(current.get(R + "id", "")) == (
            DOC_REL_NS + "/" + edit.story_kind,
            edit.part,
        ):
            return dict(package.parts)
        identity = next(
            (
                key
                for key, value in mapping.items()
                if value == (DOC_REL_NS + "/" + edit.story_kind, edit.part)
            ),
            None,
        )
        identity = identity or add_relationship(rels, edit.story_kind, edit.part)
        if current is None:
            current = etree.Element(W + kind)
            current.set(W + "type", edit.variant)
            index = 0
            while index < len(section) and section[index].tag in {
                W + "headerReference",
                W + "footerReference",
            }:
                index += 1
            section.insert(index, current)
        current.set(R + "id", identity)
    restored = deepcopy(section)
    for node in list(restored):
        if node.tag == W + kind and node.get(W + "type") == edit.variant:
            restored.remove(node)
    if original_index is not None:
        restored.insert(original_index, deepcopy(original_section[original_index]))
    if canonical(restored) != canonical(original_section):
        raise ValueError("Binding edit modified unrelated section XML")
    return {**package.parts, MAIN_PART: xml_bytes(main), MAIN_RELS: xml_bytes(rels)}


def set_flag(root: etree._Element, tag: str, enabled: bool) -> None:
    matches = root.findall(W + tag)
    if len(matches) > 1:
        raise ValueError("Ambiguous Word first/even-page setting")
    if matches:
        node = matches[0]
    elif not enabled:
        return
    elif tag == "titlePg":
        node = etree.Element(W + tag)
        successors = {
            W + n
            for n in [
                "textDirection",
                "bidi",
                "rtlGutter",
                "docGrid",
                "printerSettings",
                "sectPrChange",
            ]
        }
        index = next((i for i, n in enumerate(root) if n.tag in successors), len(root))
        root.insert(index, node)
    else:
        # The already checked settings XML uses python-docx's native schema order.
        typed = parse_xml(xml_bytes(root))
        typed.get_or_add_evenAndOddHeaders()
        index = next(i for i, n in enumerate(typed) if n.tag == W + tag)
        node = etree.Element(W + tag)
        root.insert(index, node)
    if onoff(node) != enabled:
        node.set(W + "val", "1" if enabled else "0")


def flag_parts(
    package: NativeOOXMLPackage, edit: StoryFirstPage | StoryEvenPages
) -> dict[str, bytes]:
    parts = dict(package.parts)
    if isinstance(edit, StoryFirstPage):
        main = package.xml(MAIN_PART)
        set_flag(section_at(main, edit.section_index), "titlePg", edit.enabled)
        parts[MAIN_PART] = xml_bytes(main)
    else:
        candidates = [
            target
            for kind, target in package.relationships(MAIN_PART).values()
            if kind == DOC_REL_NS + "/settings"
        ]
        if len(candidates) > 1:
            raise ValueError("Ambiguous Word settings relationship")
        if not candidates and not edit.enabled:
            return parts
        part = candidates[0] if candidates else "word/settings.xml"
        if candidates:
            root = package.xml(part)
        else:
            require_new(package, part)
            root = etree.Element(W + "settings", nsmap={"w": W[1:-1]})
            rels, types = package.xml(MAIN_RELS), package.xml(TYPES)
            add_relationship(rels, "settings", part)
            add_type(
                types,
                part,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml",
            )
            parts.update({MAIN_RELS: xml_bytes(rels), TYPES: xml_bytes(types)})
        if root.tag != W + "settings":
            raise ValueError("Word settings relationship has an unexpected root")
        set_flag(root, "evenAndOddHeaders", edit.enabled)
        parts[part] = xml_bytes(root)
    return parts


def apply_one(
    package: NativeOOXMLPackage, edit: StoryStructureEdit
) -> tuple[bytes, dict[str, Any]]:
    receipt: dict[str, Any] = edit.model_dump()
    if isinstance(edit, (StoryCreate, StoryClone)):
        require_new(package, edit.part)
        if isinstance(edit, StoryCreate):
            root = etree.Element(
                W + ("hdr" if edit.story_kind == "header" else "ftr"),
                nsmap={"w": W[1:-1], "r": R[1:-1]},
            )
            root.extend(build_blocks(edit.blocks))
            check_blocks(list(root), edit.blocks)
            additions = {edit.part: xml_bytes(root)}
            kind: str = edit.story_kind
        else:
            additions, remaps = clone_parts(package, edit)
            kind = story_parts(package)[edit.source_part]
            receipt["identity_repairs"] = remaps
        types = package.xml(TYPES)
        add_type(types, edit.part, next(t for t, k in KINDS.items() if k == kind))
        parts = {**package.parts, **additions, TYPES: xml_bytes(types)}
    elif isinstance(edit, StoryBind):
        parts = binding_parts(package, edit)
    elif isinstance(edit, StoryRemove):
        parts, retained = remove_parts(package, edit)
        receipt["retained_dependencies"] = retained
    else:
        parts = flag_parts(package, edit)
    result = write_package(package, parts)
    after_package = checked_docx(result)
    before, after = catalog(package), catalog(after_package)
    if isinstance(edit, StoryCreate):
        check_blocks(list(after_package.xml(edit.part)), edit.blocks)
    if isinstance(edit, (StoryCreate, StoryClone)) and any(
        after_package.parts[name] != raw for name, raw in additions.items()
    ):
        raise ValueError("Created/cloned story readback differs from native intent")
    if isinstance(edit, StoryBind):
        slot = next(
            item
            for item in after["sections"][edit.section_index]["bindings"]
            if item["story_kind"] == edit.story_kind and item["variant"] == edit.variant
        )
        if slot["declared"] != (edit.part is not None) or (
            edit.part is not None and slot["part"] != edit.part
        ):
            raise ValueError("Story binding readback differs from requested intent")
    if (
        isinstance(edit, StoryFirstPage)
        and after["sections"][edit.section_index]["different_first_page"]
        != edit.enabled
    ):
        raise ValueError("First-page setting readback differs from requested intent")
    if (
        isinstance(edit, StoryEvenPages)
        and after["even_and_odd_headers"] != edit.enabled
    ):
        raise ValueError("Even-page setting readback differs from requested intent")
    receipt["before_catalog"] = before
    receipt["after_catalog"] = after
    receipt["changed_parts"] = sorted(
        n
        for n in package.parts.keys() | parts.keys()
        if package.parts.get(n) != after_package.parts.get(n)
    )
    return result, receipt


def change_structure(
    data: bytes, request: DocxStoryStructure
) -> tuple[bytes, NativeEditResult]:
    original = checked_docx(data, for_edit=True)
    initial_catalog = json.dumps(
        catalog(original), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    if (
        hashlib.sha256(initial_catalog.encode()).hexdigest()
        != request.expected_catalog_sha256
    ):
        raise ValueError("Word story catalog hash differs from the initial structure")
    sections(original.xml(MAIN_PART))
    current, receipts = data, []
    for edit in request.edits:
        current, receipt = apply_one(checked_docx(current, for_edit=True), edit)
        receipts.append(receipt)
    # A reversed edit sequence can restore the original exact bytes and history.
    current = write_package(original, checked_docx(current).parts)
    final = checked_docx(current, for_edit=True)
    changed = sorted(
        n
        for n in original.parts.keys() | final.parts.keys()
        if original.parts.get(n) != final.parts.get(n)
    )
    return current, NativeEditResult(
        changed_parts=changed,
        preserved_parts=len(original.parts.keys() & final.parts.keys() - set(changed)),
        changes=receipts,
        checks=[
            "catalog_precondition",
            "explicit_inheritance_scope",
            "native_story_structure",
            "relationship_target_preservation",
            "incoming_dependency_checks",
            "package_inventory",
            "unrelated_part_bytes",
        ],
        review_required=[
            *STORY_REVIEW,
            "following_section_inheritance",
            "first_and_even_page_behavior",
            "retained_orphan_media",
        ],
    )
