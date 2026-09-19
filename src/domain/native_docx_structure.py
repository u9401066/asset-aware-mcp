"""Typed Word block creation and reference-bound structural edits."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.domain.native_asset_models import (
    NativeDocxBlockReference,  # noqa: TC001 -- Pydantic schema
)

if TYPE_CHECKING:
    from src.domain.native_asset_models import NativeEditResult

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
MAX_COMPONENTS = 20_000
Twips = Annotated[int, Field(ge=1, le=31680)]
Spacing = Annotated[int, Field(ge=0, le=31680)]
Color = Annotated[str, Field(pattern=r"^[0-9A-Fa-f]{6}$")]


def xml_text(value: str) -> str:
    if re.search(r"[\x00-\x08\x0b-\x1f\ud800-\udfff\ufffe\uffff]", value):
        raise ValueError(
            "DOCX text contains invalid XML characters or a carriage return"
        )
    return value


class DocxModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class NativeDocxRun(DocxModel):
    text: str = Field(max_length=8000)
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    font_size_pt: float | None = Field(default=None, ge=1, le=400, multiple_of=0.5)
    font_name: str | None = Field(default=None, min_length=1, max_length=200)
    color_rgb: Color | None = None

    @field_validator("text", "font_name")
    @classmethod
    def text_fields(cls, value: str | None) -> str | None:
        return xml_text(value) if value is not None else None


class NativeDocxParagraph(DocxModel):
    kind: Literal["paragraph"] = "paragraph"
    runs: list[NativeDocxRun] = Field(default_factory=list, max_length=100)
    alignment: Literal["left", "center", "right", "justify"] | None = None
    outline_level: int | None = Field(default=None, ge=0, le=8)
    space_before_twips: Spacing | None = None
    space_after_twips: Spacing | None = None
    keep_with_next: bool | None = None
    page_break_before: bool | None = None


class NativeDocxCell(DocxModel):
    paragraphs: list[NativeDocxParagraph] = Field(
        default_factory=lambda: [NativeDocxParagraph()], min_length=1, max_length=100
    )
    vertical_alignment: Literal["top", "center", "bottom"] = "top"
    fill_rgb: Color | None = None


class NativeDocxMerge(DocxModel):
    row: int = Field(ge=0, le=99)
    column: int = Field(ge=0, le=99)
    end_row: int = Field(ge=0, le=99)
    end_column: int = Field(ge=0, le=99)


class NativeDocxTable(DocxModel):
    kind: Literal["table"] = "table"
    column_widths_twips: list[Twips] = Field(min_length=1, max_length=100)
    cells: list[
        Annotated[list[NativeDocxCell], Field(min_length=1, max_length=100)]
    ] = Field(min_length=1, max_length=100)
    row_heights_twips: list[Twips] | None = Field(
        default=None, min_length=1, max_length=100
    )
    merges: list[NativeDocxMerge] = Field(default_factory=list, max_length=5000)
    alignment: Literal["left", "center", "right"] = "left"
    borders: bool = True
    repeat_header: bool = False

    @model_validator(mode="after")
    def rectangular(self) -> NativeDocxTable:
        columns = len(self.column_widths_twips)
        if any(len(row) != columns for row in self.cells):
            raise ValueError("DOCX cells must match column_widths_twips")
        if sum(self.column_widths_twips) > 31680:
            raise ValueError("DOCX table width exceeds 31,680 twips")
        if self.row_heights_twips is not None and len(self.row_heights_twips) != len(
            self.cells
        ):
            raise ValueError("DOCX row heights must match cell rows")
        empty = NativeDocxCell()
        for (row, column), anchor in merged_cells(self).items():
            if (row, column) != anchor and self.cells[row][column] != empty:
                raise ValueError(
                    "Covered DOCX cells must be empty with default formatting"
                )
        return self


def merged_cells(table: NativeDocxTable) -> dict[tuple[int, int], tuple[int, int]]:
    result = {}
    for merge in table.merges:
        if not (
            merge.row <= merge.end_row < len(table.cells)
            and merge.column <= merge.end_column < len(table.column_widths_twips)
        ):
            raise ValueError("DOCX merge rectangle is reversed or outside the grid")
        if (merge.row, merge.column) == (merge.end_row, merge.end_column):
            raise ValueError("DOCX merge must cover at least two cells")
        if table.repeat_header and merge.row == 0 < merge.end_row:
            raise ValueError("A repeated header cannot merge into a non-header row")
        for row in range(merge.row, merge.end_row + 1):
            for column in range(merge.column, merge.end_column + 1):
                if (row, column) in result:
                    raise ValueError("DOCX merge rectangles overlap")
                result[row, column] = merge.row, merge.column
    return result


NativeDocxBlock = Annotated[
    NativeDocxParagraph | NativeDocxTable, Field(discriminator="kind")
]


def bounded_blocks(blocks: list[NativeDocxBlock]) -> list[NativeDocxBlock]:
    cells = runs = size = paragraphs = 0
    for block in blocks:
        if isinstance(block, NativeDocxParagraph):
            items = [block]
        else:
            cells += sum(len(row) for row in block.cells)
            items = [p for row in block.cells for cell in row for p in cell.paragraphs]
        paragraphs += len(items)
        for paragraph in items:
            runs += len(paragraph.runs)
            size += sum(len(run.text.encode("utf-8")) for run in paragraph.runs)
    if (
        cells > 10_000
        or max(runs, paragraphs, len(blocks)) > MAX_COMPONENTS
        or size > 4 * 1024 * 1024
    ):
        raise ValueError(
            "DOCX batch exceeds 10,000 cells, 20,000 components or 4 MiB text"
        )
    return blocks


class NativeDocxCreate(DocxModel):
    name: str = Field(min_length=1, max_length=200)
    author: str = Field(default="", max_length=255)
    blocks: list[NativeDocxBlock] = Field(
        default_factory=list, max_length=MAX_COMPONENTS
    )
    page_width_twips: Twips = 12240
    page_height_twips: Twips = 15840
    margin_top_twips: Spacing = 1440
    margin_bottom_twips: Spacing = 1440
    margin_left_twips: Spacing = 1440
    margin_right_twips: Spacing = 1440

    @field_validator("name", "author")
    @classmethod
    def text_fields(cls, value: str) -> str:
        return xml_text(value)

    @field_validator("blocks")
    @classmethod
    def budget(cls, value: list[NativeDocxBlock]) -> list[NativeDocxBlock]:
        return bounded_blocks(value)

    @model_validator(mode="after")
    def usable_page(self) -> NativeDocxCreate:
        if (
            self.margin_left_twips + self.margin_right_twips >= self.page_width_twips
            or self.margin_top_twips + self.margin_bottom_twips
            >= self.page_height_twips
        ):
            raise ValueError("DOCX margins leave no usable page area")
        return self


class NativeDocxInsert(DocxModel):
    position: Literal["start", "end", "before", "after"]
    anchor: NativeDocxBlockReference | None = None
    blocks: list[NativeDocxBlock] = Field(min_length=1, max_length=100)

    @field_validator("blocks")
    @classmethod
    def budget(cls, value: list[NativeDocxBlock]) -> list[NativeDocxBlock]:
        return bounded_blocks(value)

    @model_validator(mode="after")
    def anchored(self) -> NativeDocxInsert:
        if (self.position in {"before", "after"}) != (self.anchor is not None):
            raise ValueError(
                "Only before/after insertion requires a current block anchor"
            )
        return self


class NativeDocxStructureAdapter(Protocol):
    def create(self, request: NativeDocxCreate) -> bytes: ...
    def insert(
        self,
        data: bytes,
        blocks: list[NativeDocxBlock],
        position: int | Literal["start", "end"],
    ) -> tuple[bytes, NativeEditResult]: ...
    def delete(
        self, data: bytes, positions: list[int]
    ) -> tuple[bytes, NativeEditResult]: ...
