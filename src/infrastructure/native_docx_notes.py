"""Read actual footnote/endnote parts, native IDs and all body-side references."""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.infrastructure.native_docx_stories import W, node_paths
from src.infrastructure.native_docx_workspace import MAIN_PART, checked_docx
from src.infrastructure.native_ooxml import DOC_REL_NS, TYPE_NS, relationships_path

if TYPE_CHECKING:
    from collections.abc import Iterator

    from src.domain.native_asset_models import NativeEditResult
    from src.domain.native_docx_notes import (
        DocxNoteLocator,
        DocxNotesUpdate,
        DocxNoteUpdate,
    )
    from src.infrastructure.native_ooxml import NativeOOXMLPackage

TYPES = {
    f"application/vnd.openxmlformats-officedocument.wordprocessingml.{kind}s+xml": kind
    for kind in ("footnote", "endnote")
}
ROLES = {"normal", "separator", "continuationSeparator", "continuationNotice"}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def note_id(raw: str | None) -> int:
    if raw is None or re.fullmatch(r"[+-]?[0-9]+", raw) is None:
        raise ValueError("Invalid native Word note ID")
    value = int(raw)
    if not -(2**31) <= value < 2**31:
        raise ValueError("Native Word note ID exceeds signed 32-bit range")
    return value


def native_tree(root: etree._Element) -> dict[str, Any]:
    nodes = list(node_paths(root))
    if len(nodes) > 100_000 or max((len(path) for _, path in nodes), default=0) > 64:
        raise ValueError("Word note tree exceeds element/depth budgets")
    texts: list[dict[str, Any]] = [
        {
            "path": path,
            "text": node.text or "",
            "text_sha256": digest((node.text or "").encode()),
        }
        for node, path in nodes
        if node.tag == W + "t"
    ]
    if sum(len(n["text"].encode()) for n in texts) > 4 * 1024 * 1024:
        raise ValueError("Word note tree exceeds text budget")
    return {
        "xml": etree.tostring(root, encoding="unicode"),
        "text": "\n".join(n["text"] for n in texts),
        "text_nodes": texts,
        "blocks": [
            {"index": i, "tag": n.tag if isinstance(n.tag, str) else "#non-element"}
            for i, n in enumerate(root)
        ],
    }


def inventory(package: NativeOOXMLPackage) -> dict[str, str]:
    overrides, defaults = {}, {}
    for node in package.xml("[Content_Types].xml"):
        if node.tag == "{" + TYPE_NS + "}Override":
            key = node.get("PartName", "").removeprefix("/")
            if not key or key in overrides:
                raise ValueError("Ambiguous Word note content types")
            overrides[key] = node.get("ContentType", "")
        elif node.tag == "{" + TYPE_NS + "}Default":
            key = node.get("Extension", "")
            if not key or key in defaults:
                raise ValueError("Ambiguous Word note default content types")
            defaults[key] = node.get("ContentType", "")
    result = {}
    for part in package.parts.keys() | overrides.keys():
        kind = TYPES.get(overrides.get(part, defaults.get(part.rpartition(".")[2], "")))
        if kind:
            if part not in package.parts or package.xml(part).tag != W + kind + "s":
                raise ValueError("Word note content type and native part disagree")
            result[part] = kind
    if len(result) > 2000:
        raise ValueError("Word note parts exceed inventory budget")
    return result


def linked_notes(
    package: NativeOOXMLPackage, owner: str, parts: dict[str, str]
) -> dict[str, str]:
    linked: dict[str, str] = {}
    if relationships_path(owner) not in package.parts:
        return linked
    for rel, target in package.relationships(owner).values():
        for kind in ("footnote", "endnote"):
            if rel == DOC_REL_NS + "/" + kind + "s":
                if kind in linked or parts.get(target) != kind:
                    raise ValueError(
                        "Ambiguous or missing native Word note relationship"
                    )
                linked[kind] = target
    return linked


def catalog(package: NativeOOXMLPackage) -> dict[str, Any]:
    parts = inventory(package)
    linked = linked_notes(package, MAIN_PART, parts)
    notes, identities = [], {}
    for part, kind in sorted(parts.items()):
        for index, node in enumerate(package.xml(part)):
            if not isinstance(node.tag, str):
                continue
            if node.tag != W + kind:
                raise ValueError("Unknown child in native Word note inventory")
            identity, role = note_id(node.get(W + "id")), node.get(W + "type", "normal")
            if (part, identity) in identities or role not in ROLES:
                raise ValueError("Duplicate note ID or unsupported native note role")
            identities[part, identity] = role
            text = etree.tostring(node, encoding="unicode")
            notes.append(
                {
                    "locator": {"part": part, "note_kind": kind, "note_id": identity},
                    "note_type": role,
                    "part_child_index": index,
                    "note_xml_sha256": digest(text.encode()),
                }
            )
    if len(notes) > 20_000:
        raise ValueError("Native Word note count exceeds budget")
    references = []
    for part in sorted(package.parts):
        if not part.endswith(".xml"):
            continue
        owner_links = None
        for node, path in node_paths(package.xml(part)):
            if node.tag not in {W + "footnoteReference", W + "endnoteReference"}:
                continue
            kind = node.tag[len(W) :].removesuffix("Reference")
            identity = note_id(node.get(W + "id"))
            if owner_links is None:
                owner_links = linked_notes(package, part, parts)
            target = owner_links.get(kind)
            # Read all XML occurrences, including dormant/revision branches. They
            # are dependencies, not assertions about displayed numbering.
            references.append(
                {
                    "part": part,
                    "path": path,
                    "note_kind": kind,
                    "note_id": identity,
                    "target_part": target,
                    "relationship_owner": part,
                    "main_body_reference": part == MAIN_PART
                    and W + "body" in {n.tag for n in node.iterancestors()}
                    and W + "txbxContent" not in {n.tag for n in node.iterancestors()},
                    "resolved_normal_note": identities.get((target or "", identity))
                    == "normal",
                    "xml": etree.tostring(node, encoding="unicode"),
                    "custom_mark_follows": node.get(W + "customMarkFollows"),
                }
            )
    if len(references) > 20_000:
        raise ValueError("Native note reference count exceeds budget")
    main = package.xml(MAIN_PART)
    return {
        "schema_version": "native-docx-notes-v1",
        "parts": [
            {
                "part": p,
                "note_kind": k,
                "linked_from_main": linked.get(k) == p,
                "raw_part_sha256": digest(package.parts[p]),
            }
            for p, k in sorted(parts.items())
        ],
        "notes": notes,
        "references": references,
        "body": {
            "part": MAIN_PART,
            "raw_part_sha256": digest(package.parts[MAIN_PART]),
            **native_tree(main),
        },
        "scope": "Native definitions, special roles and all literal reference occurrences. IDs are not rendered numbers. Body paths address the complete document XML; text offsets are Unicode code points. Literal XML includes field caches and revision/alternate branches. Agent checks actual numbering, placement and meaning.",
    }


def read_note(
    package: NativeOOXMLPackage,
    locator: DocxNoteLocator,
    *,
    listing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if listing is None:
        listing = catalog(package)
    entry = next(
        (n for n in listing["notes"] if n["locator"] == locator.model_dump()), None
    )
    if entry is None:
        raise ValueError("Native Word note identity does not exist")
    root = package.xml(locator.part)[entry["part_child_index"]]
    return note_record(
        package,
        entry,
        root,
        matching_references(listing, locator.part, locator.note_id),
    )


def matching_references(
    listing: dict[str, Any], part: str, identity: int
) -> list[dict[str, Any]]:
    return [
        r
        for r in listing["references"]
        if r["target_part"] == part and r["note_id"] == identity
    ]


def note_record(
    package: NativeOOXMLPackage,
    entry: dict[str, Any],
    root: etree._Element,
    references: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "native-docx-note-v1",
        **entry,
        **(
            metadata
            if metadata is not None
            else part_metadata(package, entry["locator"]["part"])
        ),
        **native_tree(root),
        "references": references,
        "text_scope": "Literal w:t text, including field caches/revision branches; native XML retains marks and other content. Not evaluated numbering, reading order or bibliography.",
    }


def part_metadata(package: NativeOOXMLPackage, part: str) -> dict[str, Any]:
    rels = relationships_path(part)
    return {
        "raw_part_sha256": digest(package.parts[part]),
        "relationships_xml": etree.tostring(package.xml(rels), encoding="unicode")
        if rels in package.parts
        else None,
    }


class NativeDocxNotes:
    def decompose(self, data: bytes) -> Iterator[dict[str, Any]]:
        package = checked_docx(data)
        listing = catalog(package)
        roots = {p["part"]: package.xml(p["part"]) for p in listing["parts"]}
        metadata = {part: part_metadata(package, part) for part in roots}
        references: dict[tuple[str, int], list[dict[str, Any]]] = {}
        for item in listing["references"]:
            references.setdefault((item["target_part"], item["note_id"]), []).append(
                item
            )
        for entry in listing["notes"]:
            loc = entry["locator"]
            yield note_record(
                package,
                entry,
                roots[loc["part"]][entry["part_child_index"]],
                references.get((loc["part"], loc["note_id"]), []),
                metadata[loc["part"]],
            )

    def inspect(self, data: bytes) -> dict[str, Any]:
        return catalog(checked_docx(data))

    def read(self, data: bytes, locator: DocxNoteLocator) -> dict[str, Any]:
        return read_note(checked_docx(data), locator)

    def edit(
        self, data: bytes, request: DocxNoteUpdate
    ) -> tuple[bytes, NativeEditResult]:
        from src.infrastructure.native_docx_note_edits import edit_note

        return edit_note(data, request)

    def change_structure(
        self, data: bytes, request: DocxNotesUpdate
    ) -> tuple[bytes, NativeEditResult]:
        from src.infrastructure.native_docx_note_lifecycle import change_notes

        return change_notes(data, request)
