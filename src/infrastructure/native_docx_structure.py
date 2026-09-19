"""Word body mutations that preserve all unrelated native package contents."""

from __future__ import annotations

import io
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Literal

from docx import Document
from lxml import etree

from src.domain.native_assets import NativeEditResult
from src.domain.native_docx_structure import MAX_COMPONENTS
from src.infrastructure.native_docx_builder import build_blocks, build_document
from src.infrastructure.native_docx_structure_checks import check_blocks, require
from src.infrastructure.native_docx_workspace import MAIN_PART, WORD_NS, checked_docx
from src.infrastructure.native_ooxml import DOC_REL_NS, xml_bytes

if TYPE_CHECKING:
    from src.domain.native_docx_grid import NativeDocxTableGridEdit
    from src.domain.native_docx_structure import NativeDocxBlock, NativeDocxCreate
    from src.infrastructure.native_ooxml import NativeOOXMLPackage

W = "{" + WORD_NS + "}"
DEPENDENCIES = {
    "sectPr",
    "bookmarkStart",
    "bookmarkEnd",
    "commentRangeStart",
    "commentRangeEnd",
    "commentReference",
    "permStart",
    "permEnd",
    "moveFromRangeStart",
    "moveFromRangeEnd",
    "moveToRangeStart",
    "moveToRangeEnd",
    "customXmlInsRangeStart",
    "customXmlInsRangeEnd",
    "customXmlDelRangeStart",
    "customXmlDelRangeEnd",
    "customXmlMoveFromRangeStart",
    "customXmlMoveFromRangeEnd",
    "customXmlMoveToRangeStart",
    "customXmlMoveToRangeEnd",
    "ins",
    "del",
    "moveFrom",
    "moveTo",
    "sdt",
    "customXml",
    "altChunk",
    "footnoteReference",
    "endnoteReference",
    "fldChar",
    "instrText",
    "fldSimple",
    "drawing",
    "pict",
    "object",
}
DEPENDENCY_TAGS = {W + name for name in DEPENDENCIES}


def body_of(root: etree._Element) -> etree._Element:
    bodies = root.findall(W + "body")
    if len(bodies) != 1:
        raise ValueError("DOCX requires one unambiguous document body")
    body = bodies[0]
    sections = body.findall(W + "sectPr")
    if len(sections) > 1 or (sections and body[-1] is not sections[0]):
        raise ValueError("DOCX final section properties are ambiguous or misplaced")
    if len(body) > MAX_COMPONENTS + 1:
        raise ValueError("DOCX body exceeds its block limit")
    counts = {W + name: 0 for name in ("p", "r", "tc")}
    size = 0
    for node in body.iter():
        if node.tag in counts:
            counts[node.tag] += 1
        if node.tag == W + "t":
            size += len((node.text or "").encode("utf-8"))
    if (
        max(counts.values()) > MAX_COMPONENTS
        or counts[W + "tc"] > 10_000
        or size > 4 * 1024 * 1024
    ):
        raise ValueError("DOCX body exceeds component or text budgets")
    return body


def field_depths(body: etree._Element) -> list[int]:
    depth, result = 0, [0]
    for child in body:
        for field in child.iter(W + "fldChar"):
            kind = field.get(W + "fldCharType")
            if kind == "begin":
                depth += 1
            elif kind == "end":
                depth -= 1
            elif kind != "separate" or depth == 0:
                raise ValueError("DOCX contains ambiguous field boundaries")
            if depth < 0:
                raise ValueError("DOCX contains unmatched field boundaries")
        result.append(depth)
    if depth:
        raise ValueError("DOCX contains unclosed field boundaries")
    return result


def canonical(root: etree._Element) -> bytes:
    return bytes(etree.tostring(root, method="c14n", exclusive=True))


def finish(
    package: NativeOOXMLPackage,
    root: etree._Element,
    positions: list[int],
    blocks: list[NativeDocxBlock] | None,
) -> tuple[bytes, NativeEditResult]:
    data = package.replace({MAIN_PART: xml_bytes(root)})
    after = checked_docx(data, for_edit=True)
    require(after.parts.keys() == package.parts.keys(), "package inventory")
    require(
        all(
            after.parts[name] == value
            for name, value in package.parts.items()
            if name != MAIN_PART
        ),
        "unrelated part bytes",
    )
    restored = after.xml(MAIN_PART)
    body = body_of(restored)
    original = package.xml(MAIN_PART)
    original_body = body_of(original)
    if blocks is not None:
        check_blocks([body[position] for position in positions], blocks)
        for position in reversed(positions):
            body.remove(body[position])
    else:
        for position in positions:
            body.insert(position, deepcopy(original_body[position]))
    require(canonical(restored) == canonical(original), "untouched document XML")
    return data, NativeEditResult(
        changed_parts=[MAIN_PART],
        preserved_parts=len(package.parts) - 1,
        changes=[
            {
                "operation": "insert_blocks" if blocks is not None else "delete_blocks",
                "body_positions": positions,
            }
        ],
        checks=[
            "source_revision",
            "block_reference_binding",
            "body_and_field_boundaries",
            "serialized_structure",
            "untouched_document_xml",
            "package_inventory",
            "unrelated_part_bytes",
        ],
        review_required=[
            "semantic_accuracy",
            "rendered_layout",
            "page_flow",
            "inherited_formatting",
            "fields_and_viewer_caches",
        ],
    )


class NativeDocxStructure:
    def read_table(self, data: bytes, chain: list[dict[str, Any]]) -> dict[str, Any]:
        from src.infrastructure.native_docx_grid import read_table

        return read_table(data, chain)

    def edit_table(
        self, data: bytes, chain: list[dict[str, Any]], request: NativeDocxTableGridEdit
    ) -> tuple[bytes, NativeEditResult]:
        from src.infrastructure.native_docx_grid import edit_table

        return edit_table(data, chain, request)

    def create(self, request: NativeDocxCreate) -> bytes:
        data = build_document(request)
        package = checked_docx(data, for_edit=True)
        body = body_of(package.xml(MAIN_PART))
        check_blocks(
            [node for node in body if node.tag != W + "sectPr"], request.blocks
        )
        reopened = Document(io.BytesIO(data))
        section = reopened.sections[0]
        width, height = section.page_width, section.page_height
        require(
            width is not None
            and height is not None
            and width.twips == request.page_width_twips
            and height.twips == request.page_height_twips,
            "page dimensions",
        )
        for name in ("top", "bottom", "left", "right"):
            require(
                getattr(section, name + "_margin").twips
                == getattr(request, f"margin_{name}_twips"),
                "page margin",
            )
        require(reopened.core_properties.author == request.author, "document author")
        return data

    def insert(
        self,
        data: bytes,
        blocks: list[NativeDocxBlock],
        position: int | Literal["start", "end"],
    ) -> tuple[bytes, NativeEditResult]:
        package = checked_docx(data, for_edit=True)
        root = package.xml(MAIN_PART)
        body = body_of(root)
        end = len(body) - int(bool(len(body) and body[-1].tag == W + "sectPr"))
        index = (
            {"start": 0, "end": end}[position]
            if isinstance(position, str)
            else position
        )
        if not blocks or not 0 <= index <= end:
            raise ValueError("DOCX insertion position or block batch is invalid")
        if field_depths(body)[index]:
            raise ValueError(
                "DOCX insertion inside a field requires a field-aware workflow"
            )
        generated = build_blocks(blocks)
        for node in generated:
            if any(
                key.startswith("{" + DOC_REL_NS + "}")
                for child in node.iter()
                for key in child.attrib
            ):
                raise ValueError("New DOCX blocks introduced unsupported relationships")
        for offset, node in enumerate(generated):
            body.insert(index + offset, node)
        body_of(root)
        return finish(package, root, list(range(index, index + len(blocks))), blocks)

    def delete(
        self, data: bytes, positions: list[int]
    ) -> tuple[bytes, NativeEditResult]:
        package = checked_docx(data, for_edit=True)
        root = package.xml(MAIN_PART)
        body = body_of(root)
        if (
            not positions
            or len(set(positions)) != len(positions)
            or any(not 0 <= index < len(body) for index in positions)
        ):
            raise ValueError("DOCX deletion has duplicate or missing body positions")
        depths = field_depths(body)
        for index in positions:
            target = body[index]
            if target.tag not in {W + "p", W + "tbl"}:
                raise ValueError(
                    "Only complete top-level DOCX paragraphs/tables can be deleted"
                )
            if (
                depths[index]
                or depths[index + 1]
                or any(node.tag in DEPENDENCY_TAGS for node in target.iter())
            ):
                raise ValueError(
                    "DOCX deletion affects section, range, field or embedded-content dependencies"
                )
        for index in sorted(positions, reverse=True):
            body.remove(body[index])
        return finish(package, root, sorted(positions), None)
