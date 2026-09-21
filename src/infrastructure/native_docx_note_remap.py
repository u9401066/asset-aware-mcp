"""Explicit, simultaneous note ID corrections; no hidden preview substitutions."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.infrastructure.native_docx_notes import catalog, digest, note_id
from src.infrastructure.native_docx_stories import W
from src.infrastructure.native_docx_story_edits import editable_context, locate
from src.infrastructure.native_docx_structure import canonical, field_depths
from src.infrastructure.native_docx_workspace import MAIN_PART

if TYPE_CHECKING:
    from src.domain.native_docx_notes import DocxNoteRemap
    from src.infrastructure.native_ooxml import NativeOOXMLPackage


def remap_note_ids(
    package: NativeOOXMLPackage, edit: DocxNoteRemap
) -> tuple[dict[str, etree._Element], dict[str, Any]]:
    listing = catalog(package)
    if not any(
        p["part"] == edit.part
        and p["note_kind"] == edit.note_kind
        and p["linked_from_main"]
        for p in listing["parts"]
    ):
        raise ValueError("ID remapping requires the current main-document note part")
    mapping = {item.note_id: item.new_note_id for item in edit.mappings}
    if len(mapping) != len(edit.mappings):
        raise ValueError("Duplicate old ID in native note mapping")
    root = package.xml(edit.part)
    definitions = {
        note_id(node.get(W + "id")): node
        for node in root
        if node.tag == W + edit.note_kind
    }
    for identity in mapping:
        if (
            identity not in definitions
            or definitions[identity].get(W + "type", "normal") != "normal"
        ):
            raise ValueError("Only existing normal note IDs can be remapped")
    final_ids = [mapping.get(identity, identity) for identity in definitions]
    if len(set(final_ids)) != len(final_ids):
        raise ValueError("Remapped note IDs collide with another definition")

    main = package.xml(MAIN_PART)
    original_main, original_notes = deepcopy(main), deepcopy(root)
    field_depths(main)
    changed_references, reference_spellings = [], []
    for reference in listing["references"]:
        old = reference["note_id"]
        if reference["target_part"] != edit.part or old not in mapping:
            continue
        if reference["part"] != MAIN_PART or not reference["main_body_reference"]:
            raise ValueError(
                "Mapped note has a retained reference outside the main body"
            )
        node = locate(main, reference["path"])
        editable_context(main, node)
        raw_id = node.get(W + "id")
        assert raw_id is not None
        reference_spellings.append((reference["path"], raw_id))
        if mapping[old] != old:
            node.set(W + "id", str(mapping[old]))
        changed_references.append(
            {
                "before": reference,
                "after_note_id": mapping[old],
                "after_xml": etree.tostring(node, encoding="unicode"),
            }
        )

    receipts, definition_spellings = [], []
    for old, new in mapping.items():
        node = definitions[old]
        before_hash = digest(etree.tostring(node, encoding="unicode").encode())
        raw_id = node.get(W + "id")
        assert raw_id is not None
        definition_spellings.append((root.index(node), raw_id))
        if old != new:
            node.set(W + "id", str(new))
        receipts.append(
            {
                "before": {
                    "part": edit.part,
                    "note_kind": edit.note_kind,
                    "note_id": old,
                },
                "after": {
                    "part": edit.part,
                    "note_kind": edit.note_kind,
                    "note_id": new,
                },
                "definition_before_sha256": before_hash,
                "definition_after_sha256": digest(
                    etree.tostring(node, encoding="unicode").encode()
                ),
            }
        )
    restored_notes, restored_main = deepcopy(root), deepcopy(main)
    for index, spelling in definition_spellings:
        restored_notes[index].set(W + "id", spelling)
    for path, spelling in reference_spellings:
        locate(restored_main, path).set(W + "id", spelling)
    if canonical(restored_notes) != canonical(original_notes) or canonical(
        restored_main
    ) != canonical(original_main):
        raise ValueError("Note ID remapping changed unrelated native XML")
    return {edit.part: root, MAIN_PART: main}, {
        "op": "remap_ids",
        "mappings": receipts,
        "reference_changes": changed_references,
        "preserved": "Definition order, special roles, literal content, marks, styles and all other XML.",
        "identity_policy": "New IDs apply only to this managed revision. Original references and Wikis remain historical; read complete new references before further edits.",
        "review": "Check actual rendered note bindings and numbering in the intended reader; ID remapping alone is not a visual or semantic verdict.",
    }
