"""Rewrite active native grid references using explicit worksheet ownership."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from typing import TYPE_CHECKING, Any

from lxml import etree
from openpyxl.formula.tokenizer import Token

from src.domain.native_asset_models import cell_position
from src.infrastructure.native_grid_formulas import rewrite_grid_formula
from src.infrastructure.native_grid_xml import Rectangle, cell_map, tag
from src.infrastructure.native_ooxml import DOC_REL_NS, relationships_path
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_workbook_formulas import formula_tokens
from src.infrastructure.native_workbook_references import (
    FORMULA_NAMES,
    FORMULA_NAMESPACES,
    WorkbookReferenceField,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from src.domain.native_grid import GridTransform
    from src.infrastructure.native_workbook_package import NativeWorkbookPackage

CHART_NS = "http://schemas.openxmlformats.org/drawingml/2006/chart"


def formula_fields(part: str, root: etree._Element) -> Iterator[WorkbookReferenceField]:
    for node in root.iter():
        if not isinstance(node.tag, str):
            continue
        name = etree.QName(node)
        known_namespace = name.namespace in FORMULA_NAMESPACES or bool(
            name.namespace
            and name.namespace.startswith(
                "http://schemas.microsoft.com/office/drawing/"
            )
        )
        if name.localname in FORMULA_NAMES and known_namespace:
            yield WorkbookReferenceField(part, node, "formula")
        elif node.tag == tag("cfvo") and node.get("type") == "formula":
            yield WorkbookReferenceField(part, node, "formula", "val")
        elif node.tag == tag("hyperlink") and node.get("location") is not None:
            yield WorkbookReferenceField(part, node, "hyperlink_location", "location")


class GridReferences:
    def __init__(self, book: NativeWorkbookPackage, roots: dict[str, etree._Element]):
        self.book, self.roots = book, roots
        self.owners: dict[str, set[str]] = {}
        for sheet in book.entries:
            pending, visited = [sheet["key"]["part"]], set()
            while pending:
                part = pending.pop()
                if part in visited:
                    continue
                visited.add(part)
                self.owners.setdefault(part, set()).add(sheet["name"])
                if relationships_path(part) in book.package.parts:
                    pending.extend(
                        target
                        for _, target in book.package.relationships(part).values()
                        if target
                    )

    def owner(self, field: WorkbookReferenceField) -> str | None:
        if field.node.tag == tag("definedName"):
            value = field.node.get("localSheetId")
            if value is None:
                return None
            index = int(value)
            if not 0 <= index < len(self.book.entries):
                raise ValueError("Defined-name scope is outside the worksheet registry")
            return str(self.book.entries[index]["name"])
        owners = self.owners.get(field.part, set())
        return next(iter(owners)) if len(owners) == 1 else None

    def rewrite(self, target: str, transform: GridTransform) -> dict[str, Any]:
        plans = []
        total = count = errors = 0
        for part, root in self.roots.items():
            for field in formula_fields(part, root):
                total += len(field.text.encode("utf-8"))
                count += 1
                if count > 20_000 or total > 8 * 1024 * 1024:
                    raise ValueError(
                        "Grid formula references exceed the inspection budget"
                    )
                original = field.formula()
                updated, replacements = rewrite_grid_formula(
                    original,
                    transform,
                    owner=self.owner(field),
                    target=target,
                    sheets=[sheet["name"] for sheet in self.book.entries],
                )
                if replacements:
                    errors += max(0, _ref_errors(updated) - _ref_errors(original))
                    if field.kind == "hyperlink_location" and field.text.startswith(
                        "#"
                    ):
                        updated = "#" + updated
                    plans.append((field, updated, replacements))
        # Validate every field before changing any one of them. The package plan
        # remains private until the complete structural edit passes read-back.
        changed: dict[str, int] = {}
        chart_caches = 0
        for field, updated, replacements in plans:
            field.set(updated)
            changed[field.part] = changed.get(field.part, 0) + replacements
            if field.node.tag == f"{{{CHART_NS}}}f":
                parent = field.node.getparent()
                if parent is not None:
                    for cache in list(parent):
                        if cache.tag in {
                            f"{{{CHART_NS}}}numCache",
                            f"{{{CHART_NS}}}strCache",
                        }:
                            parent.remove(cache)
                            chart_caches += 1
        return {
            "rewritten_references": changed,
            "new_ref_errors": errors,
            "stale_chart_caches_removed": chart_caches,
        }

    def shift_sources(self, target: str, transform: GridTransform) -> dict[str, int]:
        changes: dict[str, int] = {}
        for part, root in self.roots.items():
            for node in root.xpath(
                ".//s:worksheetSource | .//s:dataRef", namespaces=NS
            ):
                if (
                    node.get("sheet", "").casefold() != target.casefold()
                    or node.get("ref") is None
                ):
                    continue
                rid = node.get(f"{{{DOC_REL_NS}}}id")
                if rid:
                    relations = self.book.package.relationships(part)
                    if rid not in relations:
                        raise ValueError("Source range relationship is missing")
                    if not relations[rid][1]:
                        continue  # External workbook source has another grid.
                before = Rectangle.parse(node.get("ref", ""))
                after = before.shift(transform, clip=True)
                if after is None:
                    raise ValueError(
                        "Grid edit deletes a pivot/consolidation source range"
                    )
                if node.tag == tag("worksheetSource") and (
                    after.last_column - after.first_column
                    != before.last_column - before.first_column
                ):
                    raise ValueError(
                        "Pivot source column changes require matching cache field identities"
                    )
                if (
                    node.tag == tag("worksheetSource")
                    and transform.edit.axis == "row"
                    and transform.point(before.first_row) is None
                ):
                    raise ValueError(
                        "Pivot header deletion requires matching cache field identities"
                    )
                if after != before:
                    node.set("ref", after.text)
                    changes[part] = changes.get(part, 0) + 1
                    if root.tag == tag("pivotCacheDefinition"):
                        root.set("invalid", "1")
                        root.set("refreshOnLoad", "1")
        return changes


def clear_formula_caches(roots: dict[str, etree._Element]) -> int:
    count = 0
    for root in roots.values():
        if root.tag != tag("worksheet"):
            continue
        for cell in _cached_cells(root):
            for cached in cell.findall("s:v", NS):
                cell.remove(cached)
                count += 1
            if cell.get("t") in {"str", "b", "e", "n"}:
                cell.attrib.pop("t")
    return count


def _cached_cells(root: etree._Element) -> list[etree._Element]:
    cells = cell_map(root)
    affected = {}
    blocks = []
    by_row: dict[int, dict[int, etree._Element]] = {}
    for location, cell in cells.items():
        row, col = cell_position(location)
        by_row.setdefault(row, {})[col] = cell
        formula = cell.find("s:f", NS)
        if formula is None:
            continue
        affected[location] = cell
        if formula.get("t") in {"array", "dataTable"}:
            blocks.append(Rectangle.parse(formula.get("ref", "")))
    if len(blocks) > 4096:
        raise ValueError("Formula block caches exceed the inspection budget")
    rows = sorted(by_row)
    columns = {row: sorted(values) for row, values in by_row.items()}
    inspected = 0
    for bounds in blocks:
        for row in rows[
            bisect_left(rows, bounds.first_row) : bisect_right(rows, bounds.last_row)
        ]:
            values = columns[row]
            for col in values[
                bisect_left(values, bounds.first_column) : bisect_right(
                    values, bounds.last_column
                )
            ]:
                inspected += 1
                if inspected > 200_000:
                    raise ValueError(
                        "Formula block cache cells exceed the inspection budget"
                    )
                cell = by_row[row][col]
                affected[cell.get("r", "")] = cell
    return list(affected.values())


def _ref_errors(text: str) -> int:
    return sum(
        value == "#REF!" and (kind, subtype) == (Token.OPERAND, Token.ERROR)
        for _, _, value, kind, subtype in formula_tokens(text)
    )
