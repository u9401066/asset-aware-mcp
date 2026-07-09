"""Application service for citation index rebuilding and validation."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from src.application.citation_artifacts import (
    empty_citation_reason,
    save_citation_status,
)
from src.domain.citation import (
    LOCATOR_VERSION,
    EvidenceSpan,
    blocks_locator_sha256,
    build_evidence_spans,
)

if TYPE_CHECKING:
    from src.domain.repositories import DocumentRepository


class CitationIndexService:
    """Load persisted evidence spans, rebuilding stale citation indexes if needed."""

    def __init__(self, repository: DocumentRepository):
        self.repository = repository

    def load_or_rebuild(self, doc_id: str) -> list[EvidenceSpan]:
        spans = self.repository.load_citation_index(doc_id)
        markdown = self.repository.load_markdown(doc_id)
        blocks = self.repository.load_blocks(doc_id)
        markdown = markdown if isinstance(markdown, str) else ""

        if spans and not markdown:
            return []
        if spans and markdown and blocks is not None:
            source_revision_id = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
            locator_source_sha256 = blocks_locator_sha256(blocks)
            if all(
                span.source_revision_id == source_revision_id
                and span.locator_version == LOCATOR_VERSION
                and span.locator_source_sha256 == locator_source_sha256
                for span in spans
            ):
                return spans

        if not markdown or blocks is None:
            return []

        source_backend = self._resolve_source_backend(doc_id)
        spans = build_evidence_spans(
            doc_id=doc_id,
            markdown=markdown,
            blocks=blocks,
            source_backend=source_backend,
        )
        if spans:
            self.repository.save_citation_index(doc_id, spans)
            save_citation_status(
                self.repository,
                doc_id,
                source_backend=source_backend,
                found=len(spans),
            )
        else:
            save_citation_status(
                self.repository,
                doc_id,
                source_backend=source_backend,
                found=0,
                reason=empty_citation_reason(blocks),
            )
        return spans

    def _resolve_source_backend(self, doc_id: str) -> str:
        """Best-effort lookup of the real engine that produced this document.

        Falls back to "unknown" when the manifest is missing, hasn't recorded
        a source engine (e.g. documents ingested before that field existed),
        or the repository is a test double whose attributes auto-vivify to
        non-string mocks instead of raising/returning ``None``.
        """
        manifest = self.repository.load_manifest(doc_id)
        source_engine = getattr(manifest, "source_engine", None)
        if isinstance(source_engine, str) and source_engine:
            return source_engine
        return "unknown"
