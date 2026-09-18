"""Typed native table creation with explicit grid geometry and merge semantics."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from src.domain.native_pptx import (
    NativePptxRunCreate,
    NativePptxShapeContainer,
    NativePptxTextBoxCreate,
    PptxModel,
    xml_text,
)

Dimension = Annotated[int, Field(ge=1, le=100_000_000)]
Color = Annotated[str, Field(pattern=r"^[0-9A-Fa-f]{6}$")]


class NativePptxTableCellCreate(PptxModel):
    paragraphs: list[list[NativePptxRunCreate]] = Field(
        default_factory=lambda: [[NativePptxRunCreate(text="")]],
        min_length=1,
        max_length=100,
    )
    alignment: Literal["left", "center", "right"] = "left"
    vertical_anchor: Literal["top", "middle", "bottom"] = "middle"
    margin: int = Field(default=91440, ge=0, le=100_000_000)
    fill_rgb: Color | None = None
    text_rgb: Color | None = None

    @field_validator("paragraphs")
    @classmethod
    def bounded_runs(
        cls, value: list[list[NativePptxRunCreate]]
    ) -> list[list[NativePptxRunCreate]]:
        return NativePptxTextBoxCreate.bounded_runs(value)


class NativePptxTableMerge(PptxModel):
    row: int = Field(ge=0, le=99)
    column: int = Field(ge=0, le=99)
    end_row: int = Field(ge=0, le=99)
    end_column: int = Field(ge=0, le=99)


class NativePptxTableCreate(PptxModel):
    left: int = Field(ge=0, le=100_000_000)
    top: int = Field(ge=0, le=100_000_000)
    column_widths: list[Dimension] = Field(min_length=1, max_length=100)
    row_heights: list[Dimension] = Field(min_length=1, max_length=100)
    cells: list[
        Annotated[list[NativePptxTableCellCreate], Field(min_length=1, max_length=100)]
    ] = Field(min_length=1, max_length=100)
    merges: list[NativePptxTableMerge] = Field(default_factory=list, max_length=5000)
    name: str = Field(default="Table", min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    first_row: bool = True
    last_row: bool = False
    first_column: bool = False
    last_column: bool = False
    row_banding: bool = True
    column_banding: bool = False

    @field_validator("name", "description")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return xml_text(value)

    @model_validator(mode="after")
    def validate_grid(self) -> NativePptxTableCreate:
        rows, columns = len(self.row_heights), len(self.column_widths)
        if len(self.cells) != rows or any(len(row) != columns for row in self.cells):
            raise ValueError("Table cells must match row_heights and column_widths")
        if max(sum(self.row_heights), sum(self.column_widths)) > 100_000_000:
            raise ValueError("Table total width/height exceeds 100,000,000 EMU")
        covered = merge_map(self)
        empty = NativePptxTableCellCreate()
        for (row, column), origin in covered.items():
            if (row, column) != origin and self.cells[row][column] != empty:
                raise ValueError(
                    "Merged covered cells must be empty with default formatting"
                )
        return self


class NativePptxTableAddition(PptxModel):
    container: NativePptxShapeContainer
    table: NativePptxTableCreate


def merge_map(table: NativePptxTableCreate) -> dict[tuple[int, int], tuple[int, int]]:
    occupied = {}
    for merge in table.merges:
        if not (
            merge.row <= merge.end_row < len(table.row_heights)
            and merge.column <= merge.end_column < len(table.column_widths)
        ):
            raise ValueError("Table merge rectangle is reversed or outside the grid")
        if (merge.row, merge.column) == (merge.end_row, merge.end_column):
            raise ValueError("Table merge must span at least two cells")
        for row in range(merge.row, merge.end_row + 1):
            for column in range(merge.column, merge.end_column + 1):
                if (row, column) in occupied:
                    raise ValueError("Table merge rectangles overlap")
                occupied[row, column] = merge.row, merge.column
    return occupied


def validate_table_additions(items: list[NativePptxTableAddition]) -> None:
    count = runs = size = 0
    for item in items:
        for row in item.table.cells:
            count += len(row)
            for cell in row:
                for paragraph in cell.paragraphs:
                    runs += len(paragraph)
                    size += sum(len(run.text.encode("utf-8")) for run in paragraph)
    if count > 10_000 or runs > 20_000 or size > 4 * 1024 * 1024:
        raise ValueError("Table batch exceeds 10,000 cells, 20,000 runs or 4 MiB text")
