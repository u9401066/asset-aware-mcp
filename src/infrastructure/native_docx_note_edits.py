"""Checked content edits inside one note, preserving marks and sibling definitions."""

from __future__ import annotations

from copy import deepcopy

from src.domain.native_asset_models import NativeEditResult
from src.domain.native_docx_notes import NOTE_REVIEW, DocxNoteUpdate
from src.infrastructure.native_docx_notes import read_note
from src.infrastructure.native_docx_stories import W
from src.infrastructure.native_docx_story_edits import apply
from src.infrastructure.native_docx_structure import canonical
from src.infrastructure.native_docx_workspace import checked_docx
from src.infrastructure.native_ooxml import xml_bytes


def edit_note(data: bytes, request: DocxNoteUpdate) -> tuple[bytes, NativeEditResult]:
    package = checked_docx(data, for_edit=True)
    before = read_note(package, request.locator)
    if before["note_type"] != "normal":
        raise ValueError("Special note separators require a layout-specific edit")
    part = request.locator.part
    root = package.xml(part)
    note = root[before["part_child_index"]]
    marks = [
        canonical(n)
        for n in note.iter()
        if n.tag in {W + "footnoteRef", W + "endnoteRef"}
    ]
    changes = []
    for edit in request.edits:
        changes.append(apply(note, edit))
        if marks != [
            canonical(n)
            for n in note.iter()
            if n.tag in {W + "footnoteRef", W + "endnoteRef"}
        ]:
            raise ValueError(
                "Note content edits must preserve every native reference mark"
            )
    restored = deepcopy(root)
    restored.replace(
        restored[before["part_child_index"]],
        deepcopy(package.xml(part)[before["part_child_index"]]),
    )
    if canonical(restored) != canonical(package.xml(part)):
        raise ValueError("Note content edit changed another native definition")
    same = canonical(root) == canonical(package.xml(part))
    updated = data if same else package.replace({part: xml_bytes(root)})
    after = checked_docx(updated, for_edit=True)
    if canonical(after.xml(part)) != canonical(root):
        raise ValueError("Serialized note content differs from the edit plan")
    if read_note(after, request.locator)["references"] != before["references"]:
        raise ValueError("Note content edit changed native reference bindings")
    if after.parts.keys() != package.parts.keys() or any(
        after.parts[k] != v for k, v in package.parts.items() if k != part
    ):
        raise ValueError("Note content edit changed unrelated package parts")
    return updated, NativeEditResult(
        changed_parts=[] if same else [part],
        preserved_parts=len(package.parts) - int(not same),
        changes=changes,
        checks=[
            "native_note_identity",
            "native_reference_marks",
            "unchanged_sibling_definitions",
            "complete_native_readback",
            "unrelated_part_bytes",
        ],
        review_required=NOTE_REVIEW,
    )
