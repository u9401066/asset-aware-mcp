"""Read and validate DrawingML table grids while retaining original XML nodes."""

from __future__ import annotations

from dataclasses import dataclass

from lxml import etree

from src.infrastructure.native_pptx_package import A_NS, NS

Rectangle = tuple[int, int, int, int]
MERGE_KEYS = ("rowSpan", "gridSpan", "hMerge", "vMerge")


def merge_flags(cell: etree._Element) -> dict[str, str]:
    result = {}
    for name in MERGE_KEYS:
        value = cell.get(name)
        if value is None:
            continue
        if name.endswith("Span"):
            if not value.isascii() or not value.isdigit() or not 1 <= int(value) <= 100:
                raise ValueError("Invalid table merge span")
            if int(value) > 1:
                result[name] = str(int(value))
        elif value in {"1", "true"}:
            result[name] = "1"
        elif value not in {"0", "false"}:
            raise ValueError("Invalid table merge flag")
    return result


def rectangle_flags(
    rectangles: list[Rectangle],
) -> dict[tuple[int, int], dict[str, str]]:
    result = {}
    for r, c, end_r, end_c in rectangles:
        for row in range(r, end_r + 1):
            for col in range(c, end_c + 1):
                if (row, col) in result:
                    raise ValueError("Overlapping table merges")
                flags = {}
                if row == r and end_r > r:
                    flags["rowSpan"] = str(end_r - r + 1)
                if col == c and end_c > c:
                    flags["gridSpan"] = str(end_c - c + 1)
                if row > r:
                    flags["vMerge"] = "1"
                if col > c:
                    flags["hMerge"] = "1"
                result[row, col] = flags
    return result


def sizes(nodes: list[etree._Element], attribute: str) -> list[int]:
    values = []
    for node in nodes:
        value = node.get(attribute, "")
        if (
            not value.isascii()
            or not value.isdigit()
            or not 1 <= int(value) <= 100_000_000
        ):
            raise ValueError("Table dimensions must be positive bounded EMU")
        values.append(int(value))
    if sum(values) > 100_000_000:
        raise ValueError("Table grid total exceeds 100,000,000 EMU")
    return values


@dataclass
class TableGrid:
    table: etree._Element
    grid: etree._Element
    rows: list[etree._Element]
    columns: list[etree._Element]
    cells: list[list[etree._Element]]
    merges: list[Rectangle]

    @classmethod
    def read(cls, shape: etree._Element) -> TableGrid:
        tables = shape.findall("a:graphic/a:graphicData/a:tbl", NS)
        if len(tables) != 1:
            raise ValueError("Grid editing requires one native DrawingML table")
        table = tables[0]
        grids = table.findall("a:tblGrid", NS)
        if len(grids) != 1:
            raise ValueError("Table requires exactly one grid")
        rows = table.findall("a:tr", NS)
        columns = grids[0].findall("a:gridCol", NS)
        if not 1 <= len(rows) <= 100 or not 1 <= len(columns) <= 100:
            raise ValueError("Table grid requires 1..100 rows and columns")
        cells = [row.findall("a:tc", NS) for row in rows]
        if any(len(row) != len(columns) for row in cells):
            raise ValueError("Ragged table grid")
        sizes(rows, "h")
        sizes(columns, "w")
        merges = []
        for r, row in enumerate(cells):
            for c, cell in enumerate(row):
                flags = merge_flags(cell)
                if flags.get("hMerge") or flags.get("vMerge"):
                    continue
                height, width = (
                    int(flags.get("rowSpan", 1)),
                    int(flags.get("gridSpan", 1)),
                )
                if height == width == 1:
                    continue
                if r + height > len(rows) or c + width > len(columns):
                    raise ValueError("Table merge extends outside the grid")
                merges.append((r, c, r + height - 1, c + width - 1))
        flags_by_cell = rectangle_flags(merges)
        if any(
            merge_flags(cell) != flags_by_cell.get((r, c), {})
            for r, row in enumerate(cells)
            for c, cell in enumerate(row)
        ):
            raise ValueError("Inconsistent table merge topology")
        if (
            len(table.findall(".//a:r", NS)) > 20_000
            or sum(
                len((node.text or "").encode()) for node in table.findall(".//a:t", NS)
            )
            > 4 * 1024 * 1024
        ):
            raise ValueError("Table exceeds 20,000 runs or 4 MiB text")
        return cls(table, grids[0], rows, columns, cells, merges)

    def write(self) -> None:
        flags = rectangle_flags(self.merges)
        for r, row in enumerate(self.cells):
            for c, cell in enumerate(row):
                desired = flags.get((r, c), {})
                if merge_flags(cell) != desired:
                    for name in MERGE_KEYS:
                        cell.attrib.pop(name, None)
                    cell.attrib.update(desired)
        replace_children(self.grid, "gridCol", self.columns)
        for node, cells in zip(self.rows, self.cells, strict=True):
            replace_children(node, "tc", cells)
        replace_children(self.table, "tr", self.rows)


def replace_children(
    parent: etree._Element, name: str, nodes: list[etree._Element]
) -> None:
    old = parent.findall(f"a:{name}", NS)
    extension = parent.find("a:extLst", NS)
    index = (
        parent.index(old[0])
        if old
        else (parent.index(extension) if extension is not None else len(parent))
    )
    for node in old:
        parent.remove(node)
    for offset, node in enumerate(nodes):
        parent.insert(index + offset, node)


def new_node(name: str, attribute: str, value: int) -> etree._Element:
    return etree.Element(f"{{{A_NS}}}{name}", {attribute: str(value)})
