"""Direct Word row properties; no content rewriting or computed-style inference."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.infrastructure.native_docx_grid_model import (
    TR_ORDER,
    W,
    WordGrid,
    header,
    integer,
    one,
    prop,
    set_value,
)

if TYPE_CHECKING:
    from src.domain.native_docx_grid import DocxGridHeaderRows, DocxGridRowLayout


def _preserved(grid: WordGrid, indices: range, names: set[str]) -> bytes:
    table = deepcopy(grid.table)
    rows = table.findall(W + "tr")
    for index in indices:
        row = rows[index]
        pr = one(row, "trPr")
        if pr is None:
            continue
        for child in list(pr):
            if child.tag in {W + name for name in names}:
                pr.remove(child)
        if len(pr) == 0 and not pr.attrib and not pr.text:
            row.remove(pr)
    return bytes(etree.tostring(table, method="c14n", exclusive=True))


def _checked(grid: WordGrid, indices: range, names: set[str], before: bytes) -> None:
    if _preserved(grid, indices, names) != before:
        raise ValueError("Row layout changed native content or unrelated properties")


def layout_state(row: etree._Element) -> dict[str, Any]:
    pr = one(row, "trPr")
    split = one(pr, "cantSplit") if pr is not None else None
    raw = split.get(W + "val", "true") if split is not None else None
    policy = {
        None: "inherit",
        "1": "prevent",
        "true": "prevent",
        "on": "prevent",
        "0": "allow",
        "false": "allow",
        "off": "allow",
    }.get(raw, "unknown")
    return {
        "heights": [
            {
                "value_twips": integer(node, "val", 0),
                "rule": node.get(W + "hRule", "auto"),
            }
            for node in row.findall(W + "trPr/" + W + "trHeight")
        ],
        "split": policy,
        "split_raw_value": raw,
    }


def header_prefix(grid: WordGrid) -> int:
    return next(
        (i for i, row in enumerate(grid.rows) if not header(row)), len(grid.rows)
    )


def _editable(row: etree._Element) -> None:
    pr = one(row, "trPr")
    if pr is not None and any(
        child.tag in {W + "trPrChange", W + "ins", W + "del"} for child in pr
    ):
        raise ValueError(
            "Row layout has tracked properties requiring revision-aware editing"
        )


def _set(row: etree._Element, name: str, attrs: dict[str, str] | None) -> None:
    pr = one(row, "trPr")
    nodes = pr.findall(W + name) if pr is not None else []
    if attrs is None:
        if pr is not None:
            for node in nodes:
                pr.remove(node)
        return
    if len(nodes) > 1:
        # Explicit replacement of this direct property coalesces its declarations.
        # Do not discard extension attributes/children while normalizing them.
        if any(
            set(node.attrib) - {W + key for key in attrs} or len(node) for node in nodes
        ):
            raise ValueError(
                "Multiple row layout properties contain unmodeled extensions"
            )
        assert pr is not None
        for node in nodes[1:]:
            pr.remove(node)
    set_value(prop(row, "trPr"), name, attrs, TR_ORDER)


def set_headers(grid: WordGrid, edit: DocxGridHeaderRows) -> dict[str, Any]:
    if edit.count > len(grid.rows):
        raise ValueError("Header row count exceeds the current table")
    for region in grid.regions:
        if region.row < edit.count < region.bottom:
            raise ValueError("Header prefix cuts through an existing vertical merge")
    before = [i for i, row in enumerate(grid.rows) if header(row)]
    indices, names = range(len(grid.rows)), {"tblHeader"}
    preserved = _preserved(grid, indices, names)
    for i, row in enumerate(grid.rows):
        wanted = i < edit.count
        if header(row) != wanted:
            _editable(row)
            _set(row, "tblHeader", {"val": "1" if wanted else "0"})
    after = [i for i, row in enumerate(grid.rows) if header(row)]
    if after != list(range(edit.count)):
        raise ValueError("Requested repeated-header prefix did not survive readback")
    _checked(grid, indices, names, preserved)
    return {
        "op": edit.op,
        "before": before,
        "after": after,
        "repeat_header_prefix_length": header_prefix(grid),
        "checks": ["row_layout_readback", "untouched_table_content_and_properties"],
    }


def set_rows(grid: WordGrid, edit: DocxGridRowLayout) -> dict[str, Any]:
    if edit.index + edit.count > len(grid.rows):
        raise ValueError("Row layout range exceeds the current table")
    rows = grid.rows[edit.index : edit.index + edit.count]
    indices = range(edit.index, edit.index + edit.count)
    names = ({"trHeight"} if edit.height is not None else set()) | (
        {"cantSplit"} if edit.split is not None else set()
    )
    preserved = _preserved(grid, indices, names)
    before = [layout_state(row) for row in rows]
    for row in rows:
        _editable(row)
        if edit.height is not None:
            rule = edit.height.rule
            attrs = (
                None
                if rule == "inherit"
                else {
                    "val": str(edit.height.value_twips or 0),
                    "hRule": "atLeast" if rule == "at_least" else rule,
                }
            )
            _set(row, "trHeight", attrs)
        if edit.split is not None:
            _set(
                row,
                "cantSplit",
                None
                if edit.split == "inherit"
                else {"val": "1" if edit.split == "prevent" else "0"},
            )
    _checked(grid, indices, names, preserved)
    after = [layout_state(row) for row in rows]
    for state in after:
        if edit.split is not None and state["split"] != edit.split:
            raise ValueError("Requested row split policy did not survive readback")
        if edit.height is not None:
            expected = (
                []
                if edit.height.rule == "inherit"
                else [
                    {
                        "value_twips": edit.height.value_twips or 0,
                        "rule": "atLeast"
                        if edit.height.rule == "at_least"
                        else edit.height.rule,
                    }
                ]
            )
            if state["heights"] != expected:
                raise ValueError("Requested row height did not survive readback")
    return {
        "op": edit.op,
        "index": edit.index,
        "count": edit.count,
        "before": before,
        "after": after,
        "checks": ["row_layout_readback", "untouched_table_content_and_properties"],
    }
