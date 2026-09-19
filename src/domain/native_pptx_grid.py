"""Sequential, revision-bound row/column edits for native presentation tables."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from src.domain.native_pptx import NativePptxReference, PptxModel
from src.domain.native_pptx_table import (  # noqa: TC001 -- Pydantic runtime schema
    Dimension,
    NativePptxTableCellCreate,
)


class GridPosition(PptxModel):
    axis: Literal["row", "column"]
    index: int = Field(ge=0, le=100)


class NativePptxGridInsert(GridPosition):
    op: Literal["insert"]
    sizes: list[Dimension] = Field(min_length=1, max_length=100)
    cells: (
        list[
            Annotated[
                list[NativePptxTableCellCreate], Field(min_length=1, max_length=100)
            ]
        ]
        | None
    ) = Field(default=None, min_length=1, max_length=100)


class NativePptxGridDelete(GridPosition):
    op: Literal["delete"]
    count: int = Field(ge=1, le=100)


class NativePptxGridResize(GridPosition):
    op: Literal["resize"]
    sizes: list[Dimension] = Field(min_length=1, max_length=100)


GridEdit = Annotated[
    NativePptxGridInsert | NativePptxGridDelete | NativePptxGridResize,
    Field(discriminator="op"),
]


class NativePptxTableGridEdit(PptxModel):
    reference: NativePptxReference
    edits: list[GridEdit] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def bounded_input(self) -> NativePptxTableGridEdit:
        cells = runs = size = 0
        for edit in self.edits:
            if isinstance(edit, NativePptxGridInsert) and edit.cells:
                for row in edit.cells:
                    cells += len(row)
                    for cell in row:
                        for paragraph in cell.paragraphs:
                            runs += len(paragraph)
                            size += sum(len(run.text.encode()) for run in paragraph)
        if cells > 10_000 or runs > 20_000 or size > 4 * 1024 * 1024:
            raise ValueError(
                "Grid input exceeds 10,000 cells, 20,000 runs or 4 MiB text"
            )
        return self
