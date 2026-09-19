"""Materialize shared formulas and preserve complete array/data-table blocks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.native_asset_models import cell_position
from src.infrastructure.native_grid_formulas import translate_shared_formula
from src.infrastructure.native_grid_xml import Rectangle, cell_map, shift_cell
from src.infrastructure.native_spreadsheet_reader import NS

if TYPE_CHECKING:
    from lxml import etree

    from src.domain.native_grid import GridTransform


def expand_shared_formulas(root: etree._Element) -> int:
    groups: dict[int, list[tuple[str, etree._Element]]] = {}
    for location, cell in cell_map(root).items():
        formulas = cell.findall("s:f", NS)
        if len(formulas) > 1:
            raise ValueError("Cell contains multiple formula definitions")
        if formulas and formulas[0].get("t") == "shared":
            formula = formulas[0]
            index = int(formula.get("si", "-1"))
            if not 0 <= index <= 4_294_967_295:
                raise ValueError("Invalid shared formula group index")
            groups.setdefault(index, []).append((location, formula))
    plans: list[tuple[etree._Element, str]] = []
    regions: list[Rectangle] = []
    expanded_bytes = 0
    if len(groups) > 4096:
        raise ValueError("Shared formula groups exceed the inspection budget")
    for members in groups.values():
        masters = [(cell, node) for cell, node in members if node.get("ref")]
        if len(masters) != 1 or not masters[0][1].text:
            raise ValueError(
                "Shared formula group requires exactly one complete master"
            )
        anchor, master = masters[0]
        bounds = Rectangle.parse(master.get("ref", ""))
        if any(bounds.overlaps(other) for other in regions):
            raise ValueError("Shared formula master ranges overlap")
        regions.append(bounds)
        row, col = cell_position(anchor)
        for location, formula in members:
            if not bounds.contains(location):
                raise ValueError("Shared formula member is outside its master range")
            current_row, current_col = cell_position(location)
            # Followers' own text is ignored by the format; nonshared formulas in
            # the same rectangle are individual overrides and remain untouched.
            text = translate_shared_formula(
                master.text or "", current_row - row, current_col - col
            )
            expanded_bytes += len(text.encode("utf-8"))
            if len(plans) >= 20_000 or expanded_bytes > 8 * 1024 * 1024:
                raise ValueError(
                    "Expanded shared formulas exceed the inspection budget"
                )
            plans.append((formula, text))
    for formula, text in plans:
        for key in ("t", "si", "ref"):
            formula.attrib.pop(key, None)
        formula.text = text
    return len(plans)


def shift_formula_blocks(root: etree._Element, transform: GridTransform) -> int:
    updated = 0
    for location, cell in cell_map(root).items():
        formula = cell.find("s:f", NS)
        if formula is None:
            continue
        kind = formula.get("t", "normal")
        if kind not in {"normal", "array", "dataTable"}:
            raise ValueError("Formula group must be expanded before grid relocation")
        if kind == "normal":
            if any(formula.get(key) is not None for key in ("ref", "si", "r1", "r2")):
                raise ValueError("Normal formula contains ambiguous group metadata")
            continue
        bounds = Rectangle.parse(formula.get("ref", ""))
        if bounds.anchor != location:
            raise ValueError("Array/data-table master is not at its range anchor")
        first = getattr(bounds, "first_" + transform.edit.axis)
        last = getattr(bounds, "last_" + transform.edit.axis)
        at, count = transform.edit.at, transform.edit.count
        if transform.edit.operation == "insert":
            partial = first < at <= last
        else:
            end = at + count - 1
            overlaps = at <= last and end >= first
            partial = overlaps and not (at <= first and end >= last)
        if partial:
            raise ValueError(
                "Grid edit intersects only part of an array/data-table block"
            )
        shifted = bounds.shift(transform)
        if shifted is None:
            continue  # Entire block and master will be removed by the cell stage.
        if shifted != bounds:
            formula.set("ref", shifted.text)
            updated += 1
        if kind == "dataTable":
            for index in (1, 2):
                key = f"r{index}"
                value = formula.get(key)
                if value is None:
                    continue
                moved = shift_cell(value, transform)
                if moved is None:
                    formula.attrib.pop(key)
                    formula.set(f"del{index}", "1")
                    updated += 1
                elif moved != value:
                    formula.set(key, moved)
                    updated += 1
    return updated
