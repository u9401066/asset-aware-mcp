"""Repository-facing document operations for :mod:`document_service`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.output_paths import resolve_document_output_path

if TYPE_CHECKING:
    from pathlib import Path

    from src.domain.entities import DocumentManifest, DocumentSummary
    from src.domain.repositories import DocumentRepository, KnowledgeGraphInterface


class DocumentRepositoryOperationsMixin:
    """Small public operations kept out of the PDF ingest implementation."""

    if TYPE_CHECKING:
        repository: DocumentRepository
        knowledge_graph: KnowledgeGraphInterface | None

        def _build_docx_from_markdown(
            self,
            markdown: str,
            manifest: DocumentManifest,
            output_path: Path,
        ) -> None: ...

        def _build_pptx_from_markdown(
            self,
            markdown: str,
            manifest: DocumentManifest,
            output_path: Path,
        ) -> dict[str, Any]: ...

    async def list_documents(self) -> list[DocumentSummary]:
        """List all processed documents."""
        return self.repository.list_documents()

    async def get_manifest(self, doc_id: str) -> DocumentManifest | None:
        """Get manifest for a specific document."""
        return self.repository.load_manifest(doc_id)

    async def document_exists(self, doc_id: str) -> bool:
        """Check if a document exists."""
        return self.repository.document_exists(doc_id)

    async def delete_document(self, doc_id: str) -> dict[str, Any]:
        """Delete a stored PDF document and its local artifacts."""
        manifest = self.repository.load_manifest(doc_id)
        if manifest is None:
            return {"success": False, "error": f"Document not found: {doc_id}"}

        deleted = self.repository.delete_document(doc_id)
        if not deleted:
            return {
                "success": False,
                "error": f"Failed to delete document directory for {doc_id}",
            }

        warnings: list[str] = []
        knowledge_graph_status: str | None = None
        if self.knowledge_graph and self.knowledge_graph.is_available:
            try:
                kg_result = await self.knowledge_graph.delete_document(doc_id)
                knowledge_graph_status = str(kg_result.get("status", "unknown"))
                if knowledge_graph_status not in {"success", "not_found"}:
                    warnings.append(
                        "Knowledge graph deletion did not complete successfully; "
                        "local artifacts were deleted first."
                    )
            except Exception as exc:
                warnings.append(
                    "Knowledge graph deletion failed; local artifacts were deleted first. "
                    f"Reason: {exc}"
                )

        result = {
            "success": True,
            "doc_id": doc_id,
            "filename": manifest.filename,
            "warnings": warnings,
        }
        if knowledge_graph_status is not None:
            result["knowledge_graph_status"] = knowledge_graph_status
        return result

    async def convert_pdf_to_docx(
        self,
        doc_id: str,
        output_path: str | None = None,
        *,
        mode: str = "content",
    ) -> dict[str, Any]:
        """
        Convert an ingested PDF document to DOCX.

        Supported modes:
        - ``content``: rebuild a readable DOCX from extracted markdown and figures.
        - ``fidelity``: currently unsupported because PDF ETL is not layout-reversible.
        """
        if mode != "content":
            return {
                "success": False,
                "error": (
                    "PDF → DOCX currently supports content mode only. "
                    "Layout-fidelity reconstruction is not available."
                ),
            }

        manifest = self.repository.load_manifest(doc_id)
        if manifest is None:
            return {"success": False, "error": f"Document not found: {doc_id}"}

        markdown = self.repository.load_markdown(doc_id)
        if markdown is None:
            return {
                "success": False,
                "error": f"Markdown content not found for {doc_id}",
            }

        doc_dir = self.repository.get_doc_dir(doc_id)
        try:
            out_path = resolve_document_output_path(
                doc_dir,
                output_path,
                default_name="converted_from_pdf.docx",
                allowed_suffixes={".docx"},
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}

        try:
            self._build_docx_from_markdown(markdown, manifest, out_path)
        except Exception as e:
            return {"success": False, "error": str(e)}

        return {
            "success": True,
            "doc_id": doc_id,
            "output_path": str(out_path),
            "mode": mode,
            "figures_embedded": len(manifest.assets.figures),
            "tables_found": len(manifest.assets.tables),
        }

    async def convert_pdf_to_pptx(
        self,
        doc_id: str,
        output_path: str | None = None,
        *,
        mode: str = "content",
    ) -> dict[str, Any]:
        """
        Convert an ingested PDF document to PPTX slides.

        Supported modes:
        - ``content``: slide-oriented rendering from extracted markdown + figures.
        """
        if mode != "content":
            return {
                "success": False,
                "error": (
                    "PDF → PPTX currently supports content mode only. "
                    "Layout-fidelity reconstruction is not available."
                ),
            }

        manifest = self.repository.load_manifest(doc_id)
        if manifest is None:
            return {"success": False, "error": f"Document not found: {doc_id}"}

        markdown = self.repository.load_markdown(doc_id)
        if markdown is None:
            return {
                "success": False,
                "error": f"Markdown content not found for {doc_id}",
            }

        doc_dir = self.repository.get_doc_dir(doc_id)
        try:
            out_path = resolve_document_output_path(
                doc_dir,
                output_path,
                default_name="converted_from_pdf.pptx",
                allowed_suffixes={".pptx"},
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}

        try:
            build_stats = self._build_pptx_from_markdown(markdown, manifest, out_path)
        except Exception as e:
            return {"success": False, "error": str(e)}

        return {
            "success": True,
            "doc_id": doc_id,
            "output_path": str(out_path),
            "mode": mode,
            "slides_created": build_stats.get("total_slides", 0),
            "figure_slides": build_stats.get("figure_slides", 0),
        }
