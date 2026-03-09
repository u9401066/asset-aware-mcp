# Domain Layer - Core Business Logic

from .chunking import (
    BasicChunker,
    Chunk,
    ChunkConfig,
    ChunkingStrategy,
    DocumentType,
    PageAwareChunker,
    SemanticChunker,
    detect_document_type,
    get_chunker,
    smart_chunk,
)
from .entities import (
    DocumentAssets,
    DocumentManifest,
    DocumentSummary,
    FetchResult,
    FigureAsset,
    IngestResult,
    SectionAsset,
    TableAsset,
)
from .etl_profile import (
    ETLProfile,
    ETLProfileRegistry,
    FigureTableFilter,
    FontThresholds,
)
from .job import Job, JobProgress, JobStatus, JobSummary, JobType
from .table_entities import (
    CellCitation,
    ChangeEntry,
    ColumnDef,
    TableChangeLog,
    TableContext,
    TableDraft,
    TableSchema,
    TableTemplate,
)
from .value_objects import AssetRef, AssetType, DocId, ImageMediaType, SourceType

__all__ = [
    # Value Objects
    "AssetRef",
    "AssetType",
    # Chunking
    "BasicChunker",
    # Table Entities
    "CellCitation",
    "ChangeEntry",
    "Chunk",
    "ChunkConfig",
    "ChunkingStrategy",
    "ColumnDef",
    "DocId",
    # Entities
    "DocumentAssets",
    "DocumentManifest",
    "DocumentSummary",
    "DocumentType",
    # ETL Profile
    "ETLProfile",
    "ETLProfileRegistry",
    "FetchResult",
    "FigureAsset",
    "FigureTableFilter",
    "FontThresholds",
    "ImageMediaType",
    "IngestResult",
    # Job
    "Job",
    "JobProgress",
    "JobStatus",
    "JobSummary",
    "JobType",
    "PageAwareChunker",
    "SectionAsset",
    "SemanticChunker",
    "SourceType",
    "TableAsset",
    "TableChangeLog",
    "TableContext",
    "TableDraft",
    "TableSchema",
    "TableTemplate",
    "detect_document_type",
    "get_chunker",
    "smart_chunk",
]
