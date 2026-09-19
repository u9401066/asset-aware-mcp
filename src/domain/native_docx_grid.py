"""Explicit sequential Word layout-grid operations bound to a complete block ref."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from src.domain.native_asset_models import (
    NativeDocxBlockReference,  # noqa: TC001 -- Pydantic schema
)
from src.domain.native_docx_structure import (
    DocxModel,
    NativeDocxCell,
    NativeDocxMerge,
    Twips,
)


class DocxGridPosition(DocxModel):
    axis: Literal["row", "column"]
    index: int = Field(ge=0, le=100)


class DocxGridInsert(DocxGridPosition):
    op: Literal["insert"]
    sizes_twips: list[Twips] = Field(min_length=1, max_length=100)
    cells: (
        list[Annotated[list[NativeDocxCell], Field(min_length=1, max_length=100)]]
        | None
    ) = Field(default=None, min_length=1, max_length=100)


class DocxGridDelete(DocxGridPosition):
    op: Literal["delete"]
    count: int = Field(ge=1, le=100)


class DocxGridResize(DocxGridPosition):
    op: Literal["resize"]
    sizes_twips: list[Twips] = Field(min_length=1, max_length=100)


class DocxGridMerge(NativeDocxMerge):
    op: Literal["merge"]
    content_policy: Literal["require_empty", "append_blocks"]

    @model_validator(mode="after")
    def rectangle(self) -> DocxGridMerge:
        if self.end_row < self.row or self.end_column < self.column:
            raise ValueError("DOCX merge rectangle must be ordered")
        if (self.row, self.column) == (self.end_row, self.end_column):
            raise ValueError("DOCX merge needs at least two cells")
        return self


class DocxGridSplit(DocxModel):
    op: Literal["split"]
    row: int = Field(ge=0, le=99)
    column: int = Field(ge=0, le=99)


DocxGridEdit = Annotated[
    DocxGridInsert | DocxGridDelete | DocxGridResize | DocxGridMerge | DocxGridSplit,
    Field(discriminator="op"),
]


class NativeDocxTableGridEdit(DocxModel):
    reference: NativeDocxBlockReference
    edits: list[DocxGridEdit] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def bounded_input(self) -> NativeDocxTableGridEdit:
        cells = paragraphs = runs = size = 0
        for edit in self.edits:
            if isinstance(edit, DocxGridInsert) and edit.cells:
                for row in edit.cells:
                    cells += len(row)
                    for cell in row:
                        paragraphs += len(cell.paragraphs)
                        for paragraph in cell.paragraphs:
                            runs += len(paragraph.runs)
                            size += sum(
                                len(run.text.encode()) for run in paragraph.runs
                            )
        if cells > 10_000 or max(runs, paragraphs) > 20_000 or size > 4 * 1024 * 1024:
            raise ValueError("DOCX grid input exceeds cell/component/text budget")
        return self
