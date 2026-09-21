"""Atomic native note definition creation/removal with exact body-side anchors."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from lxml import etree

from src.domain.native_asset_models import NativeEditResult
from src.domain.native_docx_notes import (
    NOTE_REVIEW,
    DocxNoteCreate,
    DocxNoteDelete,
    DocxNoteLocator,
    DocxNoteRemap,
    DocxNotesUpdate,
)
from src.infrastructure.native_docx_builder import build_blocks
from src.infrastructure.native_docx_note_anchors import insert_anchor, marker_run
from src.infrastructure.native_docx_note_remap import remap_note_ids
from src.infrastructure.native_docx_notes import (
    TYPES,
    catalog,
    digest,
    note_id,
    read_note,
)
from src.infrastructure.native_docx_stories import W
from src.infrastructure.native_docx_story_edits import editable_context, locate
from src.infrastructure.native_docx_story_package import (
    MAIN_RELS,
    add_relationship,
    add_type,
    require_new,
    write_package,
)
from src.infrastructure.native_docx_story_package import (
    TYPES as CONTENT_TYPES,
)
from src.infrastructure.native_docx_structure import (
    DEPENDENCIES,
    canonical,
    field_depths,
)
from src.infrastructure.native_docx_structure_checks import check_blocks
from src.infrastructure.native_docx_workspace import MAIN_PART, checked_docx
from src.infrastructure.native_ooxml import NativeOOXMLPackage, xml_bytes

DELETE_BLOCKED = {
    W + n
    for n in DEPENDENCIES
    - {"fldChar", "instrText", "fldSimple", "drawing", "pict", "object"}
}


def catalog_hash(value: dict[str, Any]) -> str:
    return digest(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    )


def create_note(
    package: NativeOOXMLPackage, edit: DocxNoteCreate
) -> tuple[dict[str, etree._Element], dict[str, Any]]:
    before = catalog(package)
    linked = [
        p
        for p in before["parts"]
        if p["note_kind"] == edit.note_kind and p["linked_from_main"]
    ]
    changes: dict[str, etree._Element] = {}
    if linked:
        if linked[0]["part"] != edit.part:
            raise ValueError("New note must use the current main-document note part")
        root = package.xml(edit.part)
    else:
        if (
            re.fullmatch(r"word/(?:[A-Za-z0-9-]+/)*[A-Za-z0-9_-]+\.xml", edit.part)
            is None
        ):
            raise ValueError("New note part needs a bounded ASCII Word XML path")
        require_new(package, edit.part)
        root = etree.Element(W + edit.note_kind + "s", nsmap={"w": W[1:-1]})
        for special_id, role in [(-1, "separator"), (0, "continuationSeparator")]:
            special = etree.SubElement(
                root, W + edit.note_kind, {W + "id": str(special_id), W + "type": role}
            )
            run = etree.SubElement(etree.SubElement(special, W + "p"), W + "r")
            etree.SubElement(run, W + role)
        rels, types = package.xml(MAIN_RELS), package.xml(CONTENT_TYPES)
        add_relationship(rels, edit.note_kind + "s", edit.part)
        add_type(
            types, edit.part, next(t for t, k in TYPES.items() if k == edit.note_kind)
        )
        changes[MAIN_RELS], changes[CONTENT_TYPES] = rels, types
    used = {note_id(n.get(W + "id")) for n in root if n.tag == W + edit.note_kind}
    used.update(
        r["note_id"] for r in before["references"] if r["note_kind"] == edit.note_kind
    )
    identity = edit.note_id
    if identity is None:
        identity = 1
        while identity in used:
            identity += 1
    if identity in used or identity >= 2**31:
        raise ValueError("New native note ID is occupied or out of range")
    main = package.xml(MAIN_PART)
    anchor = insert_anchor(main, edit.anchor, edit.note_kind, identity)
    original_definitions = deepcopy(root)
    # Place the new definition before the next existing body reference. Some
    # Writer versions pair definition order with body order even though OOXML
    # identities are explicit. Existing IDs and sibling order stay untouched.
    reference = locate(main, anchor["reference_path"])
    body_refs = list(main.iter(W + edit.note_kind + "Reference"))
    following_ids = [
        note_id(n.get(W + "id")) for n in body_refs[body_refs.index(reference) + 1 :]
    ]
    definitions = {
        note_id(n.get(W + "id")): n
        for n in root
        if n.tag == W + edit.note_kind and n.get(W + "type", "normal") == "normal"
    }
    next_definition = next(
        (definitions[i] for i in following_ids if i in definitions), None
    )
    insertion_index = (
        root.index(next_definition) if next_definition is not None else len(root)
    )
    blocks = build_blocks(edit.blocks)
    check_blocks(blocks, edit.blocks)
    note = etree.Element(W + edit.note_kind, {W + "id": str(identity)})
    root.insert(insertion_index, note)
    note.extend(blocks)
    added_paragraph = note[0].tag != W + "p"
    if added_paragraph:
        note.insert(0, etree.Element(W + "p"))
    first = note[0]
    marker = marker_run(edit.note_kind)
    first.insert(1 if len(first) and first[0].tag == W + "pPr" else 0, marker)
    restored = deepcopy(note)
    if added_paragraph:
        restored.remove(restored[0])
    else:
        paragraph = restored[0]
        paragraph.remove(
            paragraph[1 if len(paragraph) and paragraph[0].tag == W + "pPr" else 0]
        )
    check_blocks(list(restored), edit.blocks)
    restored_definitions = deepcopy(root)
    restored_definitions.remove(restored_definitions[insertion_index])
    if canonical(restored_definitions) != canonical(original_definitions):
        raise ValueError("New note changed existing definitions or their order")
    changes[edit.part], changes[MAIN_PART] = root, main
    locator = {"part": edit.part, "note_kind": edit.note_kind, "note_id": identity}
    return changes, {
        "op": "create",
        "created_note": locator,
        "anchor": anchor,
        "note_xml": etree.tostring(note, encoding="unicode"),
        "generated_marker_paragraph": added_paragraph,
        "definition_insertion_index": insertion_index,
        "definition_order_policy": "Insert before the next existing body reference; preserve existing IDs and sibling order. Agent reviews renderer numbering and bindings.",
        "automatic_numbering": "Native note ID is distinct from the viewer's displayed number; original numbering settings are unchanged.",
    }


def delete_note(
    package: NativeOOXMLPackage, edit: DocxNoteDelete
) -> tuple[dict[str, etree._Element], dict[str, Any]]:
    before = read_note(package, edit.locator)
    if (
        before["note_type"] != "normal"
        or before["note_xml_sha256"] != edit.expected_note_sha256
    ):
        raise ValueError("Note role or exact definition hash differs")
    root = package.xml(edit.locator.part)
    original_root = deepcopy(root)
    note = root[before["part_child_index"]]
    if any(n.tag in DELETE_BLOCKED for n in note.iter()):
        raise ValueError("Note deletion has range/control/revision dependencies")
    field_depths(note)
    root.remove(note)
    restored_root = deepcopy(root)
    restored_root.insert(before["part_child_index"], deepcopy(note))
    if canonical(restored_root) != canonical(original_root):
        raise ValueError("Note removal changed another native definition")
    main = package.xml(MAIN_PART)
    original_main = deepcopy(main)
    field_depths(main)
    removed = []
    # Resolve all nodes before removal; their original paths remain receipt data.
    targets = []
    for reference in before["references"]:
        if reference["part"] != MAIN_PART or not reference["main_body_reference"]:
            raise ValueError("Note has a retained reference outside the main body")
        node = locate(main, reference["path"])
        if W + "body" not in {n.tag for n in node.iterancestors()}:
            raise ValueError("Note reference is outside the main body")
        editable_context(main, node)
        parent = node.getparent()
        assert parent is not None
        targets.append((parent, node, parent.index(node)))
        removed.append(reference)
    for parent, node, _ in targets:
        parent.remove(node)
    restored_main = deepcopy(main)
    # Ascending original paths restore preceding siblings before later indices.
    for reference in sorted(removed, key=lambda r: r["path"]):
        path = reference["path"]
        restored_parent = locate(restored_main, path[:-1])
        restored_parent.insert(path[-1], deepcopy(locate(original_main, path)))
    if canonical(restored_main) != canonical(original_main):
        raise ValueError("Note removal changed unrelated main-document XML")
    return {edit.locator.part: root, MAIN_PART: main}, {
        "op": "delete",
        "deleted_note": edit.locator.model_dump(),
        "deleted_note_xml": before["xml"],
        "removed_references": removed,
        "literal_body_text": "preserved; custom literal marks may remain and need explicit Agent correction",
        "retained_container_and_relationships": True,
        "retained_media": "Orphan targets are retained; this is not secure erasure.",
    }


def change_notes(
    data: bytes, request: DocxNotesUpdate
) -> tuple[bytes, NativeEditResult]:
    original = checked_docx(data, for_edit=True)
    initial = catalog(original)
    if catalog_hash(initial) != request.expected_catalog_sha256:
        raise ValueError("Native note catalog hash changed; inspect complete notes")
    if any(not r["resolved_normal_note"] for r in initial["references"]):
        raise ValueError("Native note references contain unresolved or special targets")
    current, receipts = data, []
    for edit in request.edits:
        package = checked_docx(current, for_edit=True)
        before = catalog(package)
        if isinstance(edit, DocxNoteCreate):
            roots, receipt = create_note(package, edit)
        elif isinstance(edit, DocxNoteRemap):
            roots, receipt = remap_note_ids(package, edit)
        else:
            roots, receipt = delete_note(package, edit)
        expected = {part: canonical(root) for part, root in roots.items()}
        values = {**package.parts, **{p: xml_bytes(n) for p, n in roots.items()}}
        current = write_package(package, values)
        after_package = checked_docx(current, for_edit=True)
        if any(
            canonical(after_package.xml(part)) != value
            for part, value in expected.items()
        ):
            raise ValueError(
                "Serialized note structure differs from planned native XML"
            )
        if any(
            after_package.parts[p] != raw
            for p, raw in package.parts.items()
            if p not in roots
        ):
            raise ValueError("Note structure edit changed unrelated package parts")
        after = catalog(after_package)
        if any(not r["resolved_normal_note"] for r in after["references"]):
            raise ValueError("Note structure edit created an unresolved reference")
        if isinstance(edit, DocxNoteCreate):
            created = read_note(
                after_package, DocxNoteLocator.model_validate(receipt["created_note"])
            )
            if (
                len(created["references"]) != 1
                or created["references"][0]["path"]
                != receipt["anchor"]["reference_path"]
                or created["references"][0]["part"] != MAIN_PART
                or created["xml"] != receipt["note_xml"]
            ):
                raise ValueError("Created note definition or body reference differs")
        receipts.append(
            {
                **receipt,
                "catalog_before_sha256": catalog_hash(before),
                "catalog_after_sha256": catalog_hash(after),
            }
        )
    final = checked_docx(current, for_edit=True)
    changed = sorted(
        p
        for p in original.parts.keys() | final.parts.keys()
        if original.parts.get(p) != final.parts.get(p)
    )
    return current, NativeEditResult(
        changed_parts=changed,
        preserved_parts=sum(p not in changed for p in original.parts),
        changes=receipts,
        checks=[
            "revision_bound_catalog",
            "native_ids_and_roles",
            "exact_unicode_anchor",
            "native_run_preservation",
            "reference_graph",
            "serialized_native_readback",
            "unrelated_part_bytes",
        ],
        review_required=NOTE_REVIEW,
    )
