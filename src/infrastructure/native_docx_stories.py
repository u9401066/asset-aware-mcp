"""Complete header/footer definitions selected by relationships, never filenames."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.infrastructure.native_docx_workspace import MAIN_PART, WORD_NS, checked_docx
from src.infrastructure.native_ooxml import (
    DOC_REL_NS,
    TYPE_NS,
    relationships_path,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from src.domain.native_asset_models import NativeEditResult
    from src.domain.native_docx_stories import DocxStoryUpdate
    from src.infrastructure.native_ooxml import NativeOOXMLPackage

W, R = "{" + WORD_NS + "}", "{" + DOC_REL_NS + "}"
KINDS = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml": "header",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml": "footer",
}


def onoff(node: etree._Element | None) -> bool | None:
    if node is None:
        return False
    return {
        "1": True,
        "true": True,
        "on": True,
        "0": False,
        "false": False,
        "off": False,
    }.get(node.get(W + "val", "true"))


def story_parts(package: NativeOOXMLPackage) -> dict[str, str]:
    overrides: dict[str, str] = {}
    defaults: dict[str, str] = {}
    for item in package.xml("[Content_Types].xml"):
        if item.tag == "{" + TYPE_NS + "}Override":
            name = item.get("PartName", "").removeprefix("/")
            if not name or name in overrides:
                raise ValueError("Ambiguous Word part content type")
            overrides[name] = item.get("ContentType", "")
        elif item.tag == "{" + TYPE_NS + "}Default":
            extension = item.get("Extension", "")
            if not extension or extension in defaults:
                raise ValueError("Ambiguous Word default content type")
            defaults[extension] = item.get("ContentType", "")
    result: dict[str, str] = {}
    for name in package.parts.keys() | overrides.keys():
        kind = KINDS.get(overrides.get(name, defaults.get(name.rpartition(".")[2], "")))
        if kind is None:
            continue
        if name not in package.parts:
            raise ValueError("Missing Word story part")
        expected = "hdr" if kind == "header" else "ftr"
        if package.xml(name).tag != W + expected:
            raise ValueError("Word story content type and root disagree")
        result[name] = kind
    if len(result) > 2000:
        raise ValueError("Word story inventory exceeds 2000 parts")
    return result


def catalog(package: NativeOOXMLPackage) -> dict[str, Any]:
    parts = story_parts(package)
    rels = package.relationships(MAIN_PART)
    for kind, target in rels.values():
        if kind in {DOC_REL_NS + "/header", DOC_REL_NS + "/footer"} and (
            not target or parts.get(target) != kind.rsplit("/", 1)[1]
        ):
            raise ValueError(
                "Header/footer relationship has no matching internal story"
            )
    even: bool | None = False
    settings = [
        target for kind, target in rels.values() if kind == DOC_REL_NS + "/settings"
    ]
    if len(settings) > 1:
        raise ValueError("Ambiguous Word settings relationship")
    if settings:
        even = onoff(package.xml(settings[0]).find(W + "evenAndOddHeaders"))
    main = package.xml(MAIN_PART)
    sections = main.xpath(
        ".//w:sectPr[not(ancestor::w:sectPrChange) and not(ancestor::w:del)]",
        namespaces={"w": WORD_NS},
    )
    if len(sections) > 2000:
        raise ValueError("Word section inventory exceeds 2000 sections")
    definitions: dict[tuple[str, str], tuple[str, int]] = {}
    records, uses = [], []
    for index, section in enumerate(sections):
        first = onoff(section.find(W + "titlePg"))
        direct = {}
        for kind in ("header", "footer"):
            for item in section.findall(W + kind + "Reference"):
                variant = item.get(W + "type")
                identity = item.get(R + "id")
                if (
                    variant not in {"default", "first", "even"}
                    or (kind, variant) in direct
                ):
                    raise ValueError("Ambiguous header/footer variant in section")
                relationship = rels.get(identity or "")
                if (
                    relationship is None
                    or relationship[0] != DOC_REL_NS + "/" + kind
                    or parts.get(relationship[1]) != kind
                ):
                    raise ValueError("Section header/footer reference is invalid")
                direct[kind, variant] = relationship[1]
                definitions[kind, variant] = relationship[1], index
        bound = []
        for kind in ("header", "footer"):
            for variant in ("default", "first", "even"):
                defined_part, owner = definitions.get((kind, variant), (None, None))
                value = {
                    "section_index": index,
                    "story_kind": kind,
                    "variant": variant,
                    "part": defined_part,
                    "declared": (kind, variant) in direct,
                    "inherited_from": owner if owner != index else None,
                    "enabled": first
                    if variant == "first"
                    else even
                    if variant == "even"
                    else True,
                }
                bound.append(value)
                if defined_part:
                    uses.append(value)
        records.append(
            {"section_index": index, "different_first_page": first, "bindings": bound}
        )
    return {
        "schema_version": "native-docx-stories-v1",
        "even_and_odd_headers": even,
        "sections": records,
        "stories": [
            {
                "locator": {"part": part, "story_kind": kind},
                "bindings": [u for u in uses if u["part"] == part],
            }
            for part, kind in sorted(parts.items())
        ],
        "scope": "Existing header/footer definitions, including dormant and unbound parts. Bindings describe section definitions, not actual page placement; default is the fallback slot. Unknown on/off values are null. Legacy DFM header/footer fields are abbreviated projections; use this catalog for exact bindings.",
    }


def node_paths(root: etree._Element) -> Iterator[tuple[etree._Element, list[int]]]:
    pending: list[tuple[etree._Element, list[int]]] = [(root, [])]
    while pending:
        node, path = pending.pop()
        yield node, path
        pending.extend(
            (child, [*path, i]) for i, child in reversed(list(enumerate(node)))
        )


def read_story(package: NativeOOXMLPackage, part: str) -> dict[str, Any]:
    listing = catalog(package)
    entry = next((e for e in listing["stories"] if e["locator"]["part"] == part), None)
    if entry is None:
        raise ValueError("Word story part is not a declared header or footer")
    root = package.xml(part)
    nodes = list(node_paths(root))
    if len(nodes) > 100_000 or max((len(path) for _, path in nodes), default=0) > 64:
        raise ValueError("Word story exceeds element/depth budgets")
    text: list[dict[str, Any]] = [
        {"path": path, "text": node.text or ""}
        for node, path in nodes
        if node.tag == W + "t"
    ]
    if sum(len(n["text"].encode()) for n in text) > 4 * 1024 * 1024:
        raise ValueError("Word story exceeds its text budget")
    relationships = relationships_path(part)
    return {
        "schema_version": "native-docx-story-v1",
        **entry,
        "raw_part_sha256": hashlib.sha256(package.parts[part]).hexdigest(),
        "xml": etree.tostring(root, encoding="unicode"),
        "text": "\n".join(n["text"] for n in text),
        "text_nodes": text,
        "blocks": [
            {
                "index": i,
                "tag": node.tag
                if isinstance(node.tag, str)
                else "#comment"
                if isinstance(node, etree._Comment)
                else "#processing-instruction",
            }
            for i, node in enumerate(root)
        ],
        "relationships_xml": etree.tostring(
            package.xml(relationships), encoding="unicode"
        )
        if relationships in package.parts
        else None,
        "text_scope": "Literal w:t nodes, including field caches and alternate/revision branches. XML retains all other content. This is not an evaluated reading order or field result.",
    }


class NativeDocxStories:
    def inspect(self, data: bytes) -> dict[str, Any]:
        return catalog(checked_docx(data))

    def read(self, data: bytes, part: str) -> dict[str, Any]:
        return read_story(checked_docx(data), part)

    def edit(
        self, data: bytes, request: DocxStoryUpdate
    ) -> tuple[bytes, NativeEditResult]:
        from src.infrastructure.native_docx_story_edits import edit_story

        return edit_story(data, request)
