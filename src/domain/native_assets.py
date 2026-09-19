"""Native file identity, typed edits and preservation results, without file IO."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from src.domain.citation_format import (  # noqa: TC001 -- Pydantic runtime schema
    CitationFormatContract,
    CitationFormatPreset,
    CitationMetadata,
)
from src.domain.native_asset_models import (
    ASSET_ID_PATTERN,
    MAX_NATIVE_BYTES,
    MAX_NATIVE_CELLS,
    SHA256_PATTERN,
    NativeAssetRepository,
    NativeAssetRevision,
    NativeCellEdit,
    NativeCellLocator,
    NativeCellReference,
    NativeDocxBlockLocator,
    NativeDocxBlockReference,
    NativeEditResult,
    NativeFileAsset,
    NativeModel,
    NativeSource,
    NativeSpreadsheetAdapter,
    NativeWorkbookCreate,
    cell_position,
    validate_sheet_name,
)
from src.domain.native_delimited import (  # noqa: TC001 -- Pydantic runtime models
    NativeDelimitedCreate,
    NativeDelimitedDialect,
    NativeDelimitedReference,
    NativeDelimitedUpdate,
)
from src.domain.native_derivation import (  # noqa: TC001 -- Pydantic schema
    NativeDerivation,
    NativeDerivationRetraction,
)
from src.domain.native_docx import NativeDocxEdit  # noqa: TC001 -- Pydantic schema
from src.domain.native_docx_grid import (
    NativeDocxTableGridEdit,  # noqa: TC001 -- Pydantic schema
)
from src.domain.native_docx_structure import (  # noqa: TC001 -- Pydantic schema
    NativeDocxCreate,
    NativeDocxInsert,
)
from src.domain.native_file_reference import (
    NativeFileReference,  # noqa: TC001 -- Pydantic schema
)
from src.domain.native_grid import NativeGridUpdate  # noqa: TC001 -- Pydantic schema
from src.domain.native_layout import (
    NativeLayoutUpdate,  # noqa: TC001 -- Pydantic schema
)
from src.domain.native_operations import (
    NativeOperation,
    operation_fields,
)
from src.domain.native_pdf import (  # noqa: TC001 -- Pydantic runtime models
    NativePdfCreate,
    NativePdfInsert,
    NativePdfPageEdit,
    NativePdfPageLocator,
    NativePdfReference,
)
from src.domain.native_pdf_region import (  # noqa: TC001 -- Pydantic runtime models
    NativePdfRegionReference,
    NativePdfRegionSelector,
)
from src.domain.native_pptx import (
    NativePptxReference,
    NativePptxShapeCreate,
    NativePptxShapeLocator,
    NativePptxTextEdit,
    NativePresentationCreate,
    validate_shape_additions,
)
from src.domain.native_pptx_grid import (
    NativePptxTableGridEdit,  # noqa: TC001 -- Pydantic schema
)
from src.domain.native_pptx_picture import (  # noqa: TC001 -- Pydantic schema
    NativePptxPictureCreate,
    NativePptxPictureReplace,
)
from src.domain.native_pptx_slides import (  # noqa: TC001 -- Pydantic schema
    NativePptxSlideInsert,
    NativePptxSlideKey,
)
from src.domain.native_pptx_table import (
    NativePptxTableAddition,
    validate_table_additions,
)
from src.domain.native_rendition import NativeWorkbookRendition  # noqa: TC001 -- schema
from src.domain.native_selection import (  # noqa: TC001 -- Pydantic schema
    NativeSelectionReference,
    NativeSelectionSelector,
)
from src.domain.native_table_create import NativeTableCreate  # noqa: TC001 -- schema
from src.domain.native_table_edit import NativeTableUpdate  # noqa: TC001 -- schema
from src.domain.native_table_workspace import (  # noqa: TC001 -- Pydantic schema
    NativeTableProjection,
    NativeTableWorkbookCreate,
)
from src.domain.native_workbook import (  # noqa: TC001 -- Pydantic schema
    NativeWorksheetInsert,
    NativeWorksheetKey,
    NativeWorksheetRename,
)

__all__ = [
    "ASSET_ID_PATTERN",
    "MAX_NATIVE_BYTES",
    "MAX_NATIVE_CELLS",
    "SHA256_PATTERN",
    "NativeAssetRepository",
    "NativeAssetRevision",
    "NativeCellEdit",
    "NativeCellLocator",
    "NativeCellReference",
    "NativeDocumentRequest",
    "NativeDocxBlockLocator",
    "NativeDocxBlockReference",
    "NativeEditResult",
    "NativeFileAsset",
    "NativeModel",
    "NativeSource",
    "NativeSpreadsheetAdapter",
    "NativeWorkbookCreate",
    "cell_position",
    "validate_sheet_name",
]


class NativeDocumentRequest(NativeModel):
    op: NativeOperation = "contract"
    for_op: NativeOperation | None = None
    schema_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    source_path: str | None = Field(default=None, min_length=1, max_length=4096)
    asset_id: str | None = Field(default=None, pattern=ASSET_ID_PATTERN)
    revision: str | None = Field(default=None, pattern=SHA256_PATTERN)
    expected_revision: str | None = Field(default=None, pattern=SHA256_PATTERN)
    expected_source_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    derivation: NativeDerivation | None = None
    retraction: NativeDerivationRetraction | None = None
    derivation_id: str | None = Field(default=None, pattern=SHA256_PATTERN)
    derivations_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    expected_derivations_sha256: str | None = Field(
        default=None, pattern=SHA256_PATTERN
    )
    output_path: str | None = Field(default=None, min_length=1, max_length=4096)
    output_dir: str | None = Field(default=None, min_length=1, max_length=4096)
    citation_contract: CitationFormatContract | CitationFormatPreset | None = Field(
        default=None,
        description="Citation display only: select a preset or supply inline/reference templates. Source references and proof objects are not formatting fields.",
    )
    citation_metadata: CitationMetadata | None = None
    table_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,128}$")
    table_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    expected_table_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    table_projection: NativeTableProjection | None = None
    table_workbook: NativeTableWorkbookCreate | None = None
    workspace_reference: NativeFileReference | None = None
    workbook: NativeWorkbookCreate | None = None
    workbook_rendition: NativeWorkbookRendition | None = None
    workbook_view: Literal["structure", "references"] = "structure"
    worksheet_insert: NativeWorksheetInsert | None = None
    worksheet_grid: NativeGridUpdate | None = None
    worksheet_layout: NativeLayoutUpdate | None = None
    worksheet_key: NativeWorksheetKey | None = None
    table_update: NativeTableUpdate | None = None
    table_create: NativeTableCreate | None = None
    worksheet_rename: NativeWorksheetRename | None = None
    worksheet_keys: list[NativeWorksheetKey] = Field(
        default_factory=list, max_length=32
    )
    worksheet_order: list[NativeWorksheetKey] = Field(
        default_factory=list, max_length=256
    )
    allow_3d_membership_change: bool = Field(default=False, strict=True)
    delimited_create: NativeDelimitedCreate | None = None
    delimited_dialect: NativeDelimitedDialect | None = None
    delimited_row: int | None = Field(default=None, ge=0, lt=20_000, strict=True)
    delimited_column: int | None = Field(default=None, ge=0, lt=20_000, strict=True)
    delimited_update: NativeDelimitedUpdate | None = None
    docx_edit: NativeDocxEdit | None = None
    docx_create: NativeDocxCreate | None = None
    docx_page_index: int | None = Field(default=None, ge=0, lt=2000, strict=True)
    docx_insert: NativeDocxInsert | None = None
    docx_table_reference: NativeDocxBlockReference | None = None
    docx_table_grid: NativeDocxTableGridEdit | None = None
    docx_block_refs: list[NativeDocxBlockReference] = Field(
        default_factory=list, max_length=100
    )
    presentation: NativePresentationCreate | None = None
    pdf_create: NativePdfCreate | None = None
    pdf_insert: NativePdfInsert | None = None
    pdf_locator: NativePdfPageLocator | None = None
    pdf_edits: list[NativePdfPageEdit] = Field(default_factory=list, max_length=100)
    pdf_page_refs: list[NativePdfReference] = Field(
        default_factory=list, max_length=100
    )
    pdf_order: list[NativePdfReference] = Field(default_factory=list, max_length=2000)
    pdf_region: NativePdfRegionSelector | None = None
    render_size: int = Field(default=1024, ge=64, le=2048)
    pptx_tables: list[NativePptxTableAddition] = Field(
        default_factory=list, max_length=100
    )
    pptx_slide_insert: NativePptxSlideInsert | None = None
    pptx_slide_key: NativePptxSlideKey | None = None
    pptx_slide_keys: list[NativePptxSlideKey] = Field(
        default_factory=list, max_length=100
    )
    pptx_slide_order: list[NativePptxSlideKey] = Field(
        default_factory=list, max_length=2000
    )
    pptx_table_grid: NativePptxTableGridEdit | None = None
    pptx_locator: NativePptxShapeLocator | None = None
    pptx_pictures: list[NativePptxPictureCreate] = Field(
        default_factory=list, max_length=100
    )
    pptx_picture_edits: list[NativePptxPictureReplace] = Field(
        default_factory=list, max_length=100
    )
    pptx_edits: list[NativePptxTextEdit] = Field(default_factory=list, max_length=1000)
    pptx_shapes: list[NativePptxShapeCreate] = Field(
        default_factory=list, max_length=100
    )
    pptx_shape_refs: list[NativePptxReference] = Field(
        default_factory=list, max_length=100
    )
    reference: (
        NativeCellReference
        | NativeDocxBlockReference
        | NativePptxReference
        | NativePdfReference
        | NativePdfRegionReference
        | NativeDelimitedReference
        | NativeFileReference
        | NativeSelectionReference
        | None
    ) = None
    selection: NativeSelectionSelector | None = None
    edits: list[NativeCellEdit] = Field(
        default_factory=list, max_length=MAX_NATIVE_CELLS
    )
    sheet: str | None = Field(default=None, min_length=1, max_length=31)
    cell: str | None = Field(default=None, min_length=2, max_length=10)
    block_id: str | None = Field(default=None, pattern=r"^[a-z]+[0-9]+$", max_length=64)
    text_offset: int = Field(default=0, ge=0)
    text_limit: int = Field(default=2000, ge=1, le=4000)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=1000)

    @field_validator("cell")
    @classmethod
    def validate_optional_cell(cls, value: str | None) -> str | None:
        if value is not None:
            cell_position(value)
        return value

    @field_validator("pptx_tables")
    @classmethod
    def bounded_tables(
        cls, value: list[NativePptxTableAddition]
    ) -> list[NativePptxTableAddition]:
        validate_table_additions(value)
        return value

    @field_validator("pptx_shapes")
    @classmethod
    def validate_pptx_shapes(
        cls, value: list[NativePptxShapeCreate]
    ) -> list[NativePptxShapeCreate]:
        return validate_shape_additions(value)

    @model_validator(mode="after")
    def validate_operation(self) -> NativeDocumentRequest:
        fields = operation_fields(self.op)
        required, optional = fields.required, fields.optional
        missing = [
            name
            for name in required
            if (value := getattr(self, name)) is None
            or (isinstance(value, (str, list, dict)) and not value)
        ]
        if missing:
            raise ValueError(
                "Missing native operation fields: " + ", ".join(sorted(missing))
            )
        unused = self.model_fields_set - required - optional - {"op"}
        if unused:
            raise ValueError(
                "Fields not used by this native operation: " + ", ".join(sorted(unused))
            )
        if (
            self.op == "read_table_workspace"
            and self.text_offset
            and not self.table_sha256
        ):
            raise ValueError("Workspace continuation requires table_sha256")
        if self.op == "schema" and self.text_offset and not self.schema_sha256:
            raise ValueError(
                "Schema continuation requires schema_sha256 from the first page"
            )
        if (
            self.op == "read_derivations"
            and self.text_offset
            and not self.derivations_sha256
        ):
            raise ValueError("Derivation continuation requires derivations_sha256")
        if (
            self.op == "verify_derivation"
            and self.offset
            and not self.derivations_sha256
        ):
            raise ValueError(
                "Derivation verification continuation requires derivations_sha256"
            )
        return self
