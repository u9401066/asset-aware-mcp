"""Deterministic, citation-ready agent asset bundle export."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.application.agent_asset_bundle_format import (
    BUNDLE_VERSION,
    DEFAULT_MAX_BUNDLE_OUTPUT_BYTES,
    DEFAULT_MAX_BUNDLE_RECORDS,
    DEFAULT_MAX_BUNDLE_SPANS,
    AgentAssetBundleLimitError,
    BundleOutputBudget,
    canonical_json,
    counts,
    sha256_text,
    write_bundle,
)
from src.application.agent_asset_record_builder import (
    AgentAssetRecordBuilder,
    AssetRefFactory,
    SpanRefFactory,
)
from src.application.citation_index_service import CitationIndexService
from src.application.output_paths import resolve_document_output_dir

if TYPE_CHECKING:
    from src.application.segmentation_service import SegmentationService
    from src.domain.repositories import DocumentRepository


class AgentAssetBundleService:
    """Export one ingested document as a portable agent/Foam asset bundle."""

    def __init__(
        self,
        repository: DocumentRepository,
        segmentation_service: SegmentationService,
        *,
        max_spans: int = DEFAULT_MAX_BUNDLE_SPANS,
        max_records: int = DEFAULT_MAX_BUNDLE_RECORDS,
        max_output_bytes: int = DEFAULT_MAX_BUNDLE_OUTPUT_BYTES,
    ) -> None:
        if max_spans <= 0:
            raise ValueError("max bundle spans must be > 0")
        if max_records <= 0:
            raise ValueError("max bundle records must be > 0")
        if max_output_bytes <= 0:
            raise ValueError("max bundle output bytes must be > 0")
        self.repository = repository
        self.segmentation_service = segmentation_service
        self.max_spans = max_spans
        self.max_records = max_records
        self.max_output_bytes = max_output_bytes

    async def export(
        self,
        doc_id: str,
        *,
        output_dir: str | None,
        span_ref_factory: SpanRefFactory,
        asset_ref_factory: AssetRefFactory,
    ) -> dict[str, Any]:
        manifest = self.repository.load_manifest(doc_id)
        if manifest is None:
            return {"success": False, "doc_id": doc_id, "error": "Document not found"}

        doc_dir = self.repository.get_doc_dir(doc_id).resolve()
        target = resolve_document_output_dir(
            doc_dir,
            output_dir,
            default_name="agent-assets",
            create=False,
        )
        if target == doc_dir:
            raise ValueError(
                "Agent asset output must be a child of the document directory"
            )
        self._validate_target_is_not_source(target, doc_dir, manifest)
        self._validate_existing_target(target, doc_id)
        target.parent.mkdir(parents=True, exist_ok=True)

        first_segmentation = (
            await self.segmentation_service.export_document_segmentation(doc_id)
        )
        first_source_identity = self._source_identity(manifest, first_segmentation)
        spans = sorted(
            CitationIndexService(self.repository).load_or_rebuild(doc_id),
            key=lambda item: (item.block_id, item.char_start or -1, item.span_id),
        )
        if len(spans) > self.max_spans:
            raise AgentAssetBundleLimitError("spans", len(spans), self.max_spans)
        # Re-read the canonical artifacts after citation rebuild. This prevents a
        # concurrent edit from mixing one source revision's segmentation with
        # another revision's evidence refs in a bundle advertised as citation-ready.
        segmentation = await self.segmentation_service.export_document_segmentation(
            doc_id
        )
        current_manifest = self.repository.load_manifest(doc_id)
        if current_manifest is None:
            raise ValueError(
                "Document source artifacts changed during agent asset export; retry "
                "after the document is stable"
            )
        source_identity = self._source_identity(current_manifest, segmentation)
        if source_identity != first_source_identity:
            raise ValueError(
                "Document source artifacts changed during agent asset export; retry "
                "after the document is stable"
            )
        self._validate_target_is_not_source(target, doc_dir, current_manifest)
        self._validate_evidence_provenance(spans, source_identity)

        stage = Path(
            tempfile.mkdtemp(prefix=f".{target.name}.staging-", dir=target.parent)
        )
        output_budget = BundleOutputBudget(self.max_output_bytes)
        try:
            records = AgentAssetRecordBuilder(
                span_ref_factory,
                asset_ref_factory,
                max_records=self.max_records,
                output_budget=output_budget,
            ).build(
                current_manifest,
                segmentation,
                spans,
                source_identity,
                stage,
                doc_dir,
            )
            write_bundle(
                stage,
                current_manifest,
                source_identity,
                records,
                output_budget,
            )
            self._replace_target(stage, target)
        except Exception:
            if stage.exists():
                shutil.rmtree(stage)
            raise

        return {
            "success": True,
            "operation": "export_assets",
            "bundle_version": BUNDLE_VERSION,
            "doc_id": doc_id,
            "output_dir": str(target),
            "manifest_path": str(target / "manifest.json"),
            "assets_path": str(target / "assets.jsonl"),
            "foam_index_path": str(target / "index.md"),
            "foam_subtree": {
                "portable": True,
                "root": str(target),
                "index": str(target / "index.md"),
                "notes": str(target / "notes"),
            },
            "asset_count": len(records),
            "counts": counts(records),
        }

    @staticmethod
    def _validate_existing_target(target: Path, doc_id: str) -> None:
        if not target.exists():
            return
        if not target.is_dir():
            raise ValueError(
                f"Agent asset output exists and is not a directory: {target}"
            )
        marker = target / "manifest.json"
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Refusing to replace non-bundle output directory: {target}"
            ) from exc
        if (
            payload.get("bundle_version") != BUNDLE_VERSION
            or payload.get("doc_id") != doc_id
        ):
            raise ValueError(f"Refusing to replace non-matching bundle: {target}")

    @classmethod
    def _validate_target_is_not_source(
        cls,
        target: Path,
        doc_dir: Path,
        manifest: Any,
    ) -> None:
        """Reject output trees that overlap canonical or referenced artifacts."""
        protected: set[Path] = {
            doc_dir / "images",
            doc_dir / "assets",
            doc_dir / "pages",
            doc_dir / ".backups",
            doc_dir / f"{manifest.doc_id}_manifest.json",
            doc_dir / f"{manifest.doc_id}_full.md",
            doc_dir / "blocks.json",
            doc_dir / "citation_index.jsonl",
            doc_dir / "citation_index.status.json",
            doc_dir / "segmentation.json",
            doc_dir / "original.pdf",
            doc_dir / "original.doc",
            doc_dir / "original.docx",
            doc_dir / "original.docm",
            doc_dir / "original.odt",
            doc_dir / "original.ods",
            doc_dir / "original.pptx",
            doc_dir / "original.txt",
            doc_dir / "original.xlsx",
            doc_dir / "selected_pages.pdf",
            doc_dir / "ocr_processed.pdf",
        }
        for raw_path in (
            getattr(manifest, "manifest_path", ""),
            getattr(manifest, "markdown_path", ""),
        ):
            if raw_path:
                protected.add(cls._document_path(doc_dir, raw_path))
        for figure in getattr(getattr(manifest, "assets", None), "figures", []):
            if getattr(figure, "path", ""):
                protected.add(cls._document_path(doc_dir, figure.path))

        target = target.resolve()
        for protected_path in protected:
            protected_path = protected_path.resolve()
            if (
                target == protected_path
                or target in protected_path.parents
                or protected_path in target.parents
            ):
                raise ValueError(
                    "Agent asset output must not overlap protected document "
                    f"artifacts: {protected_path}"
                )

    @staticmethod
    def _document_path(doc_dir: Path, raw_path: str | Path) -> Path:
        path = Path(raw_path)
        return path if path.is_absolute() else doc_dir / path

    @staticmethod
    def _source_identity(manifest: Any, segmentation: Any) -> dict[str, Any]:
        suffix = Path(str(manifest.filename)).suffix.lower()
        source_sha256 = str(manifest.source_pdf_sha256 or "").lower()
        if re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None:
            raise ValueError(
                "Document manifest is missing a valid source SHA-256; re-ingest "
                "the source before exporting citation-ready agent assets"
            )
        media_types = {
            ".csv": "text/csv",
            ".doc": "application/msword",
            ".docx": (
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            ".html": "text/html",
            ".htm": "text/html",
            ".md": "text/markdown",
            ".markdown": "text/markdown",
            ".pdf": "application/pdf",
            ".pptx": (
                "application/vnd.openxmlformats-officedocument."
                "presentationml.presentation"
            ),
            ".txt": "text/plain",
            ".xlsx": (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        }
        identity = {
            "doc_id": manifest.doc_id,
            "filename": manifest.filename,
            "title": manifest.title,
            "source_engine": manifest.source_engine,
            # The persisted field predates mixed-format ingest, but contains the
            # original input digest. Keep that implementation detail out of v1.
            "source_sha256": source_sha256,
            "source_kind": suffix.lstrip(".") or "document",
            "source_media_type": media_types.get(suffix, "application/octet-stream"),
            "selected_page_map": list(manifest.selected_page_map),
            "canonical_markdown_sha256": segmentation.source_revision_id,
            "locator_version": segmentation.locator_version,
            "locator_source_sha256": segmentation.locator_source_sha256,
        }
        identity["identity_sha256"] = sha256_text(canonical_json(identity))
        return identity

    @staticmethod
    def _validate_evidence_provenance(
        spans: list[Any], source_identity: dict[str, Any]
    ) -> None:
        """Fail closed if evidence refs do not describe this exact snapshot."""
        expected_revision = source_identity["canonical_markdown_sha256"]
        expected_locator_version = source_identity["locator_version"]
        expected_locator_source = source_identity["locator_source_sha256"]
        doc_id = source_identity["doc_id"]
        if any(
            span.doc_id != doc_id
            or span.source_revision_id != expected_revision
            or span.locator_version != expected_locator_version
            or span.locator_source_sha256 != expected_locator_source
            for span in spans
        ):
            raise ValueError(
                "Citation index could not be aligned with the current document "
                "revision and locator metadata"
            )

    @staticmethod
    def _replace_target(stage: Path, target: Path) -> None:
        backup: Path | None = None
        if target.exists():
            backup = target.with_name(f".{target.name}.backup-{uuid.uuid4().hex}")
            target.replace(backup)
        try:
            stage.replace(target)
        except Exception:
            if backup is not None and backup.exists() and not target.exists():
                backup.replace(target)
            raise
        if backup is not None and backup.exists():
            shutil.rmtree(backup)
