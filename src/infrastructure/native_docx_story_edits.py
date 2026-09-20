"""Checked mutations inside one shared native Word header/footer definition."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from lxml import etree

from src.domain.native_asset_models import NativeEditResult
from src.domain.native_docx_stories import (
    STORY_REVIEW,
    DocxStoryUpdate,
    StoryDelete,
    StoryInsert,
    StoryTextEdit,
)
from src.infrastructure.native_docx_builder import build_blocks
from src.infrastructure.native_docx_stories import W, node_paths, read_story
from src.infrastructure.native_docx_structure import (
    DEPENDENCY_TAGS,
    canonical,
    field_depths,
)
from src.infrastructure.native_docx_structure_checks import check_blocks
from src.infrastructure.native_docx_workspace import checked_docx
from src.infrastructure.native_ooxml import xml_bytes

SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def locate(root: etree._Element, path: list[int]) -> etree._Element:
    node = root
    for index in path:
        if index >= len(node):
            raise ValueError("Word story text path does not exist")
        node = node[index]
    return node


def editable_text(root: etree._Element, node: etree._Element) -> None:
    if node.tag != W + "t":
        raise ValueError("Story set_text must address an existing w:t node")
    editable_context(root, node)


def editable_context(root: etree._Element, node: etree._Element) -> None:
    """Reject edits inside computed, revised or externally bound native content."""
    depth = 0
    for current, _ in node_paths(root):
        if current.tag == W + "fldChar":
            kind = current.get(W + "fldCharType")
            if kind == "begin":
                depth += 1
            elif kind == "end":
                depth -= 1
        if current is node:
            if depth:
                raise ValueError("Word field result requires a field-aware edit")
            break
    for parent in node.iterancestors():
        if parent.tag in {
            W + n for n in ("fldSimple", "ins", "del", "moveFrom", "moveTo")
        }:
            raise ValueError("Word field/revision text requires a dedicated edit")
        if parent.tag == W + "sdt":
            pr = parent.find(W + "sdtPr")
            if pr is not None and (
                pr.find(W + "lock") is not None
                or pr.find(W + "dataBinding") is not None
            ):
                raise ValueError(
                    "Bound or locked story content control cannot be edited"
                )


def apply(
    root: etree._Element, edit: StoryTextEdit | StoryInsert | StoryDelete
) -> dict[str, Any]:
    before = deepcopy(root)
    field_depths(root)
    if isinstance(edit, StoryTextEdit):
        node = locate(root, edit.path)
        editable_text(root, node)
        original = node.text or ""
        if original != edit.text:
            node.text = edit.text
            if edit.text[:1].isspace() or edit.text[-1:].isspace():
                node.set(SPACE, "preserve")
        restored = deepcopy(root)
        target, baseline = locate(restored, edit.path), locate(before, edit.path)
        target.text = baseline.text
        if SPACE in baseline.attrib:
            target.set(SPACE, baseline.attrib[SPACE])
        else:
            target.attrib.pop(SPACE, None)
        if canonical(restored) != canonical(before) or (node.text or "") != edit.text:
            raise ValueError("Story text readback/preservation check failed")
        return {
            "op": edit.op,
            "path": edit.path,
            "before": original,
            "after": node.text or "",
        }
    if edit.index > len(root):
        raise ValueError("Story block index exceeds its current tree")
    depths = field_depths(root)
    if depths[edit.index]:
        raise ValueError("Story block edit crosses a field boundary")
    if isinstance(edit, StoryInsert):
        blocks = build_blocks(edit.blocks)
        for index, block in enumerate(blocks, edit.index):
            root.insert(index, block)
        check_blocks(list(root)[edit.index : edit.index + len(blocks)], edit.blocks)
        restored = deepcopy(root)
        for _ in blocks:
            restored.remove(restored[edit.index])
        receipt = {
            "op": edit.op,
            "index": edit.index,
            "count": len(blocks),
            "inserted_xml": [etree.tostring(n, encoding="unicode") for n in blocks],
        }
    else:
        end = edit.index + edit.count
        if end > len(root):
            raise ValueError("Story deletion exceeds current blocks")
        targets = list(root)[edit.index : end]
        if depths[end] or any(
            n.tag not in {W + "p", W + "tbl"}
            or any(child.tag in DEPENDENCY_TAGS for child in n.iter())
            for n in targets
        ):
            raise ValueError("Story deletion has field/range/relationship dependencies")
        for node in targets:
            root.remove(node)
        if not any(n.tag in {W + "p", W + "tbl", W + "sdt"} for n in root):
            raise ValueError("Story deletion must retain a content block")
        restored = deepcopy(root)
        for index, node in enumerate(targets, edit.index):
            restored.insert(index, deepcopy(node))
        receipt = {
            "op": edit.op,
            "index": edit.index,
            "count": edit.count,
            "deleted_xml": [etree.tostring(n, encoding="unicode") for n in targets],
        }
    if canonical(restored) != canonical(before):
        raise ValueError("Story edit changed unrelated native XML")
    field_depths(root)
    return receipt


def edit_story(data: bytes, request: DocxStoryUpdate) -> tuple[bytes, NativeEditResult]:
    package = checked_docx(data, for_edit=True)
    original = read_story(package, request.part)
    root = package.xml(request.part)
    receipts = [apply(root, edit) for edit in request.edits]
    same = canonical(root) == canonical(package.xml(request.part))
    updated = data if same else package.replace({request.part: xml_bytes(root)})
    after = checked_docx(updated, for_edit=True)
    record = read_story(after, request.part)
    if (
        canonical(after.xml(request.part)) != canonical(root)
        or record["bindings"] != original["bindings"]
    ):
        raise ValueError("Serialized story readback differs from the requested edit")
    if after.parts.keys() != package.parts.keys() or any(
        after.parts[p] != value
        for p, value in package.parts.items()
        if p != request.part
    ):
        raise ValueError("Story edit modified unrelated package parts")
    return updated, NativeEditResult(
        changed_parts=[] if same else [request.part],
        preserved_parts=len(package.parts) - int(not same),
        changes=receipts,
        checks=[
            "story_reference",
            "shared_definition_scope",
            "native_text_and_block_readback",
            "untouched_story_xml",
            "unchanged_section_bindings",
            "package_inventory",
            "unrelated_part_bytes",
        ],
        review_required=STORY_REVIEW,
    )
