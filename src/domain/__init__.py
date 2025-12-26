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
from .job import Job, JobProgress, JobStatus, JobSummary, JobType
from .value_objects import AssetType, DocId, ImageMediaType

__all__ = [
    # Chunking
    "BasicChunker",
    "Chunk",
    "ChunkConfig",
    "ChunkingStrategy",
    "DocumentType",
    "PageAwareChunker",
    "SemanticChunker",
    "detect_document_type",
    "get_chunker",
    "smart_chunk",
    # Entities
    "DocumentAssets",
    "DocumentManifest",
    "DocumentSummary",
    "FetchResult",
    "FigureAsset",
    "IngestResult",
    "SectionAsset",
    "TableAsset",
    # Job
    "Job",
    "JobProgress",
    "JobStatus",
    "JobSummary",
    "JobType",
    # Value Objects
    "AssetType",
    "DocId",
    "ImageMediaType",
]
