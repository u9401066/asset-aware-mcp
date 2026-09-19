"""Transition Table totals roles while retaining exact data and explicit cell intent."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from src.domain.native_grid_tables import GridTableChange
from src.domain.native_table_edit import NativeTableColumnEdit, NativeTotalsEdit
from src.infrastructure.native_grid_structured import rewrite_structured_formula
from src.infrastructure.native_grid_xml import Rectangle, address
from src.infrastructure.native_spreadsheet_reader import NS, _decode_text
from src.infrastructure.native_table_columns import scalar_formula, update_totals
from src.infrastructure.native_table_detached_formulas import freeze_totals_formula

if TYPE_CHECKING:
    from lxml import etree

    from src.domain.native_table_edit import NativeTableUpdate
    from src.infrastructure.native_grid_table_state import GridTableState
    from src.infrastructure.native_table_cells import TableCellWriter
    from src.infrastructure.native_workbook_plan import WorkbookPlan


def totals_definition(column: etree._Element) -> NativeTotalsEdit:
    formula = scalar_formula(column, "totalsRowFormula")
    function = column.get("totalsRowFunction")
    label = column.get("totalsRowLabel")
    if label is not None and (formula is not None or function not in {None, "none"}):
        raise ValueError("Conflicting hidden totals label/function definitions")
    if formula is not None:
        if function not in {None, "custom"}:
            raise ValueError("Conflicting hidden custom totals formula")
        return NativeTotalsEdit(kind="formula", value="=" + (formula.text or ""))
    if function == "custom":
        raise ValueError("Hidden custom totals formula is missing")
    if function not in {None, "none"}:
        return NativeTotalsEdit(kind="function", value=function)
    if label is not None:
        return NativeTotalsEdit(kind="label", value=_decode_text(label))
    return NativeTotalsEdit(kind="blank")


def clear_definition(column: etree._Element) -> None:
    for key in ("totalsRowFunction", "totalsRowLabel"):
        column.attrib.pop(key, None)
    for node in column.findall("s:totalsRowFormula", NS):
        column.remove(node)


class TableTotalsTransition:
    def __init__(
        self,
        plan: WorkbookPlan,
        states: list[GridTableState],
        state: GridTableState,
        request: NativeTableUpdate,
        writer: TableCellWriter,
    ):
        self.plan, self.states, self.state = plan, states, state
        self.request, self.writer = request, writer
        self.before = state.bounds
        self.footprint = self.before
        self.receipt: dict[str, Any] | None = None
        if request.totals_row is not None:
            self._check_filters()

    def _check_filters(self) -> None:
        state = self.state
        data_end = self.before.last_row - state.totals
        expected = replace(self.before, last_row=data_end)
        filters = state.root.findall("s:autoFilter", NS)
        if (
            len(filters) > 1
            or (not state.headers and filters)
            or any(Rectangle.parse(node.get("ref", "")) != expected for node in filters)
        ):
            raise ValueError(
                "Totals transition requires the Table filter to match its data extent"
            )
        for node in state.root.xpath(
            ".//s:sortState | .//s:sortCondition", namespaces=NS
        ):
            bounds = Rectangle.parse(node.get("ref", ""))
            if not expected.contains(bounds.anchor) or not expected.contains(
                address(bounds.last_row, bounds.last_column)
            ):
                raise ValueError(
                    "Table sort ranges must stay within unchanged header/data rows"
                )

    def add(self) -> None:
        change, state, writer = self.request.totals_row, self.state, self.writer
        if change is None or change.action != "add":
            return
        if state.totals:
            raise ValueError("Table already has a totals row")
        after = replace(self.before, last_row=self.before.last_row + 1)
        row = after.last_row
        extension = Rectangle(row, after.first_column, row, after.last_column)
        if row > 1_048_576:
            raise ValueError("Totals row would exceed the worksheet boundary")
        if any(
            s is not state
            and s.worksheet == state.worksheet
            and s.bounds.overlaps(extension)
            for s in self.states
        ):
            raise ValueError("Totals row overlaps another Table")
        for node in writer.root.xpath(
            "s:mergeCells/s:mergeCell | s:autoFilter", namespaces=NS
        ):
            if Rectangle.parse(node.get("ref", "")).overlaps(extension):
                raise ValueError(
                    "Totals row overlaps merged cells or a worksheet AutoFilter"
                )
        edits = {c.column_id: c for c in self.request.columns}
        columns = state.root.findall("s:tableColumns/s:tableColumn", NS)
        if (
            change.cell_styles == "last_data_row"
            and self.before.last_row < self.before.first_row + state.headers
        ):
            raise ValueError("Cell-style inheritance requires an existing data row")
        for position in range(after.first_column, after.last_column + 1):
            location = address(row, position)
            writer.guards.check_structure(writer.root, location, writer.sheet)
            if writer.value(location)["kind"] != "blank":
                raise ValueError(
                    "Adding totals requires blank cells below the Table; insert a worksheet row explicitly if needed"
                )
            if change.cell_styles == "last_data_row":
                writer.style_sources[location] = address(self.before.last_row, position)
        state.root.set("ref", after.text)
        state.root.set("totalsRowCount", "1")
        state.root.set("totalsRowShown", "1")
        for position, node in enumerate(columns, after.first_column):
            identity = int(node.get("id", "0"))
            if identity in edits and edits[identity].totals is not None:
                continue
            intent = (
                totals_definition(node)
                if change.reuse_definitions
                else NativeTotalsEdit(kind="blank")
            )
            if intent.kind == "formula" and intent.value is not None:
                rewrite_structured_formula(
                    intent.value,
                    [
                        GridTableChange(name, state.columns, state.columns)
                        for name in {
                            name.casefold(): name
                            for name in (state.name, state.root.get("name", ""))
                            if name
                        }.values()
                    ],
                    table_context=state.name,
                )
            edit = NativeTableColumnEdit(
                column_id=identity,
                expected_name=_decode_text(node.get("name", "")),
                totals=intent,
            )
            update_totals(state, node, position, edit, writer)
        self.footprint = after
        self._record("add")

    def remove(self) -> None:
        change, state, writer = self.request.totals_row, self.state, self.writer
        if change is None or change.action != "remove":
            return
        if not state.totals:
            raise ValueError("Table has no totals row to remove")
        if self.before.last_row == self.before.first_row:
            raise ValueError("Removing totals would leave no Table range")
        row = self.before.last_row
        for position in range(self.before.first_column, self.before.last_column + 1):
            location = address(row, position)
            writer.guards.check_structure(writer.root, location, writer.sheet)
            if any(bounds.contains(location) for bounds in writer.merges):
                raise ValueError("Merged Table cells require a merge-aware edit")
            if change.cells == "clear":
                writer.write(location, "blank", None, allow_rich_clear=True)
            else:
                value = writer.value(location)
                if value["kind"] == "formula":
                    formula = freeze_totals_formula(value["value"], state, writer.sheet)
                    if formula != value["value"]:
                        writer.write(location, "formula", formula)
        state.root.set("ref", replace(self.before, last_row=row - 1).text)
        state.root.set("totalsRowCount", "0")
        state.root.set("totalsRowShown", "0")
        if not change.retain_definitions:
            for node in state.root.findall("s:tableColumns/s:tableColumn", NS):
                clear_definition(node)
        self._record("remove")

    def _record(self, action: str) -> None:
        self.receipt = {
            "action": action,
            "before_ref": self.before.text,
            "after_ref": self.state.bounds.text,
            "worksheet_rows_moved": False,
            "intent": self.request.totals_row.model_dump()
            if self.request.totals_row
            else None,
            "retained_formula_policy": "Own Table references in kept totals cells become explicit pre-removal absolute ranges; other workbook formulas retain structured references.",
        }
