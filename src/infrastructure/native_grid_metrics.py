"""Explicit OOXML row/column dimensions for 96-DPI drawing-anchor reconstruction."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, Literal

from src.domain.native_grid_geometry import GridAxisMetrics
from src.infrastructure.native_ooxml import DOC_REL_NS
from src.infrastructure.native_spreadsheet_reader import NS

if TYPE_CHECKING:
    from lxml import etree

    from src.domain.native_grid import NativeGridUpdate
    from src.infrastructure.native_workbook_plan import WorkbookPlan

EMU_PER_PIXEL = 9525
DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _number(value: str | float, maximum: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Invalid worksheet dimension") from exc
    if not number.is_finite() or not 0 <= number <= Decimal(maximum):
        raise ValueError("Worksheet dimension exceeds supported grid metrics")
    return number


def _width_pixels(value: str, digit: int) -> int:
    width = _number(value, "255")
    return int((256 * width + 128 // digit) / 256 * digit)


class GridMetrics:
    def __init__(self, plan: WorkbookPlan, request: NativeGridUpdate):
        self.plan, self.request = plan, request
        self.calibri = self._normal_calibri()

    def _normal_calibri(self) -> bool:
        styles = [
            target
            for kind, target in self.plan.book.rels.values()
            if kind == f"{DOC_REL_NS}/styles"
        ]
        if len(styles) != 1:
            return False
        root = self.plan.roots[styles[0]]
        normal = root.xpath('./s:cellStyles/s:cellStyle[@builtinId="0"]', namespaces=NS)
        if len(normal) != 1:
            return False
        style_index = int(normal[0].get("xfId", "-1"))
        xfs = root.findall("s:cellStyleXfs/s:xf", NS)
        if not 0 <= style_index < len(xfs):
            raise ValueError("Normal style has an invalid format index")
        font_index = int(xfs[style_index].get("fontId", "0"))
        fonts = root.findall("s:fonts/s:font", NS)
        if not 0 <= font_index < len(fonts):
            raise ValueError("Normal style has an invalid font index")
        font = fonts[font_index]
        name, size = font.find("s:name", NS), font.find("s:sz", NS)
        if (
            name is None
            or size is None
            or name.get("val", "").casefold() != "calibri"
            or _number(size.get("val", "0"), "409.5") != 11
        ):
            return False
        if any(
            node is not None and node.get("val", "1") not in {"0", "false"}
            for node in [
                font.find(f"s:{key}", NS) for key in ("b", "i", "condense", "extend")
            ]
        ):
            return False
        scheme = font.find("s:scheme", NS)
        if scheme is not None and scheme.get("val") not in {None, "none"}:
            kind = scheme.get("val", "")
            if kind not in {"minor", "major"}:
                return False
            themes = [
                target
                for rel, target in self.plan.book.rels.values()
                if rel == f"{DOC_REL_NS}/theme"
            ]
            if len(themes) != 1:
                return False
            face = self.plan.roots[themes[0]].find(
                f".//{{{DRAWING_NS}}}fontScheme/{{{DRAWING_NS}}}{kind}Font/{{{DRAWING_NS}}}latin"
            )
            if face is None or face.get("typeface", "").casefold() != "calibri":
                return False
        return True

    def axis(
        self, root: etree._Element, axis: Literal["row", "column"]
    ) -> tuple[GridAxisMetrics, dict[str, Any]]:
        formatting = root.find("s:sheetFormatPr", NS)
        attrs = dict(formatting.attrib) if formatting is not None else {}
        if axis == "row":
            height = self.request.default_row_height_points
            origin = (
                "caller_default_row_height"
                if height is not None
                else "stored_default_row_height"
            )
            if height is None:
                height = attrs.get("defaultRowHeight")
            if height is None:
                if not self.calibri:
                    raise ValueError(
                        "Drawing geometry needs an explicit default_row_height_points"
                    )
                height, origin = 15.0, "Calibri11_default_row_height"
            points = _number(height, "409.5")
            default = int(points * 4 / 3) * EMU_PER_PIXEL
            if attrs.get("zeroHeight") in {"1", "true"}:
                default = 0
            values = {}
            for row in root.findall("s:sheetData/s:row", NS):
                index = int(row.get("r", "0")) - 1
                if index in values:
                    raise ValueError("Duplicate drawing row dimension")
                size = (
                    int(_number(row.get("ht", str(points)), "409.5") * 4 / 3)
                    * EMU_PER_PIXEL
                )
                values[index] = 0 if row.get("hidden") in {"1", "true"} else size
            return GridAxisMetrics(1_048_576, default, tuple(values.items())), {
                "axis": "row",
                "dpi": 96,
                "basis": origin,
                "default_points": str(points),
            }
        digit = self.request.column_digit_width or (7 if self.calibri else None)
        if digit is None:
            raise ValueError(
                "Drawing geometry needs an explicit column_digit_width for this Normal font"
            )
        default_pixels = self.request.default_column_pixels
        origin = "caller_default_column_pixels"
        if default_pixels is None and attrs.get("defaultColWidth") is not None:
            default_pixels = _width_pixels(attrs["defaultColWidth"], digit)
            origin = "stored_default_column_width"
        if default_pixels is None:
            if not self.calibri or digit != 7 or attrs.get("baseColWidth", "8") != "8":
                raise ValueError(
                    "Drawing geometry needs an explicit default_column_pixels"
                )
            default_pixels, origin = 64, "Calibri11_96dpi_default_column"
        values = {}
        for column in root.findall("s:cols/s:col", NS):
            first, last = int(column.get("min", "0")), int(column.get("max", "0"))
            if not 1 <= first <= last <= 16_384:
                raise ValueError("Invalid drawing column dimension interval")
            width = column.get("width")
            pixels = (
                _width_pixels(width, digit) if width is not None else default_pixels
            )
            if column.get("hidden") in {"1", "true"}:
                pixels = 0
            for index in range(first - 1, last):
                if index in values:
                    raise ValueError("Overlapping drawing column dimensions")
                values[index] = pixels * EMU_PER_PIXEL
        return GridAxisMetrics(
            16_384, default_pixels * EMU_PER_PIXEL, tuple(values.items())
        ), {
            "axis": "column",
            "dpi": 96,
            "digit_width_pixels": digit,
            "default_column_pixels": default_pixels,
            "basis": origin,
            "font_basis": "caller_digit_width"
            if self.request.column_digit_width is not None
            else "Calibri11_Normal_and_theme",
        }
