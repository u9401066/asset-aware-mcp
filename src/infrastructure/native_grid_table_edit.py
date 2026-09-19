"""Private table range/column edits and calculated-column origin maintenance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.domain.native_grid_tables import GridTableChange
from src.infrastructure.native_grid_formulas import translate_shared_formula
from src.infrastructure.native_grid_table_expansion import (
    shift_table_filters,
    table_destination,
)
from src.infrastructure.native_grid_xml import address, tag
from src.infrastructure.native_spreadsheet_reader import NS

if TYPE_CHECKING:
    from src.domain.native_grid import GridTransform, NativeTableExpansion
    from src.infrastructure.native_grid_table_state import GridTableState


@dataclass
class TableGridEdit:
    state: GridTableState
    transform: GridTransform
    expansion: NativeTableExpansion | None = None
    change: GridTableChange = field(init=False)
    headers_to_write: list[tuple[str, str]] = field(default_factory=list)
    calculated: list[tuple[etree._Element, int, int, list[int]]] = field(
        default_factory=list
    )
    receipt: dict[str, Any] = field(default_factory=dict)

    def prepare(self) -> None:
        state, transform = self.state, self.transform
        bounds, columns = state.bounds, state.columns
        after = table_destination(state, transform, self.expansion)
        self.receipt = {
            "table": state.name,
            "part": state.part,
            "before": bounds.text,
            "after": after.text if after else None,
        }
        if self.expansion is not None:
            self.receipt["explicit_expansion"] = self.expansion.model_dump()
        if after is None:
            self.change = GridTableChange(state.name, columns, None)
            return
        old_header, old_totals = state.headers, state.totals
        root = state.root
        if transform.edit.axis == "row":
            if old_header and transform.point(bounds.first_row) is None:
                root.set("headerRowCount", "0")
                for node in root.findall("s:autoFilter", NS):
                    root.remove(node)
                self.receipt["header_hidden_after_deletion"] = True
            if old_totals and transform.point(bounds.last_row) is None:
                root.set("totalsRowCount", "0")
                root.set("totalsRowShown", "0")
                for node in root.findall("s:tableColumns/s:tableColumn", NS):
                    for key in ("totalsRowFunction", "totalsRowLabel"):
                        node.attrib.pop(key, None)
                    for formula in node.findall("s:totalsRowFormula", NS):
                        node.remove(formula)
                self.receipt["totals_removed"] = True
        column_list = root.find("s:tableColumns", NS)
        assert column_list is not None
        positioned = {}
        for index, node in enumerate(
            column_list.findall("s:tableColumn", NS), bounds.first_column
        ):
            moved = transform.point(index) if transform.edit.axis == "column" else index
            if moved is not None:
                positioned[moved] = node
        if transform.edit.axis == "column" and transform.edit.operation == "insert":
            taken = {column.name.casefold() for column in columns}
            next_id = max(column.identity for column in columns) + 1
            for index in range(after.first_column, after.last_column + 1):
                if index in positioned:
                    continue
                number = index - after.first_column + 1
                while (name := f"Column{number}").casefold() in taken:
                    number += 1
                if next_id > 4_294_967_295:
                    raise ValueError("Native table column ID space is exhausted")
                positioned[index] = etree.Element(
                    tag("tableColumn"), id=str(next_id), name=name
                )
                next_id += 1
                taken.add(name.casefold())
                if state.headers:
                    self.headers_to_write.append(
                        (address(after.first_row, index), name)
                    )
        column_list[:] = [node for _, node in sorted(positioned.items())] + [
            node for node in column_list if node.tag != tag("tableColumn")
        ]
        column_list.set("count", str(len(positioned)))
        root.set("ref", after.text)
        shift_table_filters(state, transform, bounds)
        state.validate()
        self.change = GridTableChange(state.name, columns, state.columns)
        self.receipt["columns_before"] = [
            {"id": col.identity, "name": col.name} for col in columns
        ]
        self.receipt["columns_after"] = [
            {"id": col.identity, "name": col.name} for col in state.columns
        ]
        # Preserve the formula template's origin independently of the location
        # where surviving original data rows will land.
        old_origin = bounds.first_row + old_header
        new_origin = after.first_row + state.headers
        for column, node in sorted(positioned.items()):
            formula = node.find("s:calculatedColumnFormula", NS)
            if formula is None:
                continue
            source_origin, post_delta = old_origin, 0
            if transform.edit.axis == "row":
                if transform.edit.operation == "delete":
                    source_origin = new_origin + (
                        transform.edit.count if new_origin >= transform.edit.at else 0
                    )
                else:
                    moved_origin = transform.point(old_origin)
                    assert moved_origin is not None
                    post_delta = new_origin - moved_origin
            if source_origin != old_origin:
                formula.text = translate_shared_formula(
                    formula.text or "", source_origin - old_origin, 0
                )
            rows = []
            if transform.edit.axis == "row" and transform.edit.operation == "insert":
                rows = [
                    row
                    for row in range(
                        transform.edit.at, transform.edit.at + transform.edit.count
                    )
                    if new_origin <= row <= after.last_row - state.totals
                ]
            if rows and formula.get("array") in {"1", "true"}:
                raise ValueError(
                    "Array calculated columns require a dedicated insertion workflow"
                )
            self.calculated.append((formula, column, post_delta, rows))
