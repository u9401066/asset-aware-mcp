"""Table-aware cell writes preserving existing native cell/run formatting."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.infrastructure.native_grid_cells import GridCellWriter
from src.infrastructure.native_grid_xml import Rectangle, cell_map, tag
from src.infrastructure.native_spreadsheet_guards import NativeCellGuards
from src.infrastructure.native_spreadsheet_reader import NS, XML_SPACE, _encode_text

if TYPE_CHECKING:
    from src.infrastructure.native_workbook_plan import WorkbookPlan


class TableCellWriter:
    def __init__(self, plan: WorkbookPlan, part: str, sheet: str):
        self.book, self.root, self.sheet = plan.book, plan.roots[part], sheet
        self.writer = GridCellWriter(self.root)
        self.original_cells = cell_map(self.book._sheet(sheet))
        self.guards = NativeCellGuards(self.book)
        self.changed: dict[str, dict[str, Any]] = {}
        self.expected: dict[str, bytes] = {}
        self.style_sources: dict[str, str] = {}
        self.receipt_bytes = 0
        self.merges = [
            Rectangle.parse(node.get("ref", ""))
            for node in self.root.findall("s:mergeCells/s:mergeCell", NS)
        ]

    def value(self, location: str) -> dict[str, Any]:
        return self.book._value(self.writer.cells.get(location))

    def write(
        self,
        location: str,
        kind: str,
        value: str | None,
        *,
        runs: list[str] | None = None,
        allow_rich_clear: bool = False,
    ) -> None:
        if len(self.changed) >= 20_000 and location not in self.changed:
            raise ValueError("Table cell edits exceed the 20000-cell budget")
        self.guards.check_structure(self.root, location, self.sheet)
        if any(bounds.contains(location) for bounds in self.merges):
            raise ValueError("Merged Table cells require a merge-aware edit")
        existing = self.writer.cells.get(location)
        before = self.value(location)
        if existing is not None:
            if set(existing.attrib) - {"r", "s", "t"}:
                raise ValueError("Table cell metadata requires a dedicated edit")
            if any(
                child.tag not in {tag("f"), tag("v"), tag("is")} for child in existing
            ):
                raise ValueError("Unknown Table cell features require a dedicated edit")
            formulas = existing.findall("s:f", NS)
            if len(formulas) > 1 or any(set(f.attrib) - {"t", "ca"} for f in formulas):
                raise ValueError("Unsupported Table cell formula metadata")
        text_root = self._text(existing) if before["kind"] == "string" else None
        rich = text_root is not None and bool(text_root.findall("s:r", NS))
        if (
            rich
            and (kind != "string" or runs is None)
            and not (kind == "blank" and allow_rich_clear)
        ):
            raise ValueError("Rich Table text requires explicit run-aware editing")
        if runs is not None and not rich:
            raise ValueError("header_runs requires an existing rich header")
        cell = self.writer.empty(location)
        if location in self.style_sources:
            template = self.writer.cells.get(self.style_sources[location])
            style = template.get("s") if template is not None else None
            if style is None:
                cell.attrib.pop("s", None)
            else:
                cell.set("s", style)
        if kind == "string":
            assert value is not None
            cell.set("t", "inlineStr")
            if rich:
                assert text_root is not None and runs is not None
                content = deepcopy(text_root)
                content.tag = tag("is")
                nodes = content.findall("s:r", NS)
                if len(nodes) != len(runs):
                    raise ValueError("Header run count changed")
                for node, text in zip(nodes, runs, strict=True):
                    item = node.find("s:t", NS)
                    assert item is not None
                    item.text = _encode_text(text)
                    item.set(XML_SPACE, "preserve")
                cell.append(content)
            else:
                item = etree.SubElement(etree.SubElement(cell, tag("is")), tag("t"))
                item.text = _encode_text(value)
                item.set(XML_SPACE, "preserve")
        elif kind == "formula":
            assert value is not None and value.startswith("=")
            etree.SubElement(cell, tag("f")).text = value[1:]
        elif kind != "blank":
            raise ValueError("Unsupported Table cell value kind")
        if existing is not None:
            # The explicit Table request authorizes replacing this payload only.
            existing[:] = []
            existing.attrib.pop("t", None)
        self.writer.put(cell)
        previous_size = (
            len(json.dumps(self.changed[location], ensure_ascii=False).encode("utf-8"))
            if location in self.changed
            else 0
        )
        self.changed[location] = {
            "before": self.book._value(self.original_cells.get(location)),
            "after": self.book._value(cell),
        }
        self.expected[location] = etree.tostring(cell, method="c14n", exclusive=True)
        self.receipt_bytes += (
            len(json.dumps(self.changed[location], ensure_ascii=False).encode("utf-8"))
            - previous_size
        )
        if self.receipt_bytes > 8 * 1024 * 1024:
            raise ValueError("Table cell receipt exceeds the 8 MiB readback budget")

    def _text(self, cell: etree._Element | None) -> etree._Element:
        assert cell is not None
        if cell.get("t") == "s":
            root = self.book.shared_strings[int(cell.findtext("s:v", namespaces=NS))]
        else:
            root = cell.find("s:is", NS)
            assert root is not None
        if root.attrib or any(node.tag not in {tag("t"), tag("r")} for node in root):
            raise ValueError("Phonetic/extended Table text needs a dedicated edit")
        runs = root.findall("s:r", NS)
        if runs and root.find("s:t", NS) is not None:
            raise ValueError("Mixed plain/rich Table text is ambiguous")
        if not runs and len(root.findall("s:t", NS)) != 1:
            raise ValueError("Ambiguous plain Table text")
        for run in runs:
            if (
                run.attrib
                or len(run.findall("s:t", NS)) != 1
                or len(run.findall("s:rPr", NS)) > 1
                or any(child.tag not in {tag("t"), tag("rPr")} for child in run)
            ):
                raise ValueError("Unsupported rich Table text structure")
        return root
