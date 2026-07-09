"""
Unit tests for MCP presentation-layer tools.

Tests tool functions directly (without MCP transport) to validate
error handling, input validation, and response formatting.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.entities import FetchResult
from src.domain.value_objects import AssetType

# ============================================================================
# Docx Tools
# ============================================================================


class TestDocumentTools:
    """Tests for document_tools.py MCP functions."""

    async def test_list_documents_empty(self) -> None:
        """list_documents returns help message when empty."""
        with patch(
            "src.presentation.tools.document_tools.document_service"
        ) as mock_svc:
            mock_svc.list_documents = AsyncMock(return_value=[])
            from src.presentation.tools.document_tools import list_documents

            result = await list_documents()
            assert "ingest_documents" in result

    async def test_list_documents_shows_facade_next_actions(self) -> None:
        """list_documents guides agents toward facade ops instead of legacy direct tools."""
        from src.domain.entities import DocumentSummary

        with patch(
            "src.presentation.tools.document_tools.document_service"
        ) as mock_svc:
            mock_svc.list_documents = AsyncMock(
                return_value=[
                    DocumentSummary(
                        doc_id="doc_123",
                        filename="paper.pdf",
                        title="Paper",
                        page_count=2,
                    )
                ]
            )
            from src.presentation.tools.document_tools import list_documents

            result = await list_documents()

        assert 'document(op="inspect", doc_id="doc_123")' in result
        assert 'document(op="prepare_ai", doc_id="doc_123")' in result

    async def test_parse_pdf_structure_file_not_found(self) -> None:
        """parse_pdf_structure returns error for missing file."""
        from src.presentation.tools.document_tools import parse_pdf_structure

        result = await parse_pdf_structure("/nonexistent/file.pdf")
        assert "❌" in result

    async def test_parse_pdf_structure_reports_missing_marker_backend(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """parse_pdf_structure reports a missing Marker backend before queuing."""
        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.domain.marker_errors import MarkerBackendUnavailable
        from src.presentation.tools import document_tools

        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            side_effect=AssertionError("Marker jobs require a backend")
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        monkeypatch.setattr(
            document_tools.MarkerPDFExtractor,
            "require_backend_available",
            MagicMock(side_effect=MarkerBackendUnavailable("marker missing")),
        )

        result = await document_tools.parse_pdf_structure(
            str(pdf_path),
            async_mode=False,
        )

        assert "Marker Backend Not Available" in result
        assert "use_marker=False" in result
        mock_jobs.create_ingest_job.assert_not_awaited()

    async def test_parse_pdf_structure_sync_mode_still_returns_background_job(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """parse_pdf_structure async_mode=False returns a job after Marker preflight."""
        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.presentation.tools import document_tools

        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(
                job_id="job_sync_parse", estimated_duration_seconds=10
            )
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        monkeypatch.setattr(
            document_tools.MarkerPDFExtractor,
            "require_backend_available",
            MagicMock(),
        )

        result = await document_tools.parse_pdf_structure(
            str(pdf_path),
            async_mode=False,
        )

        assert "job_sync_parse" in result
        mock_jobs.create_ingest_job.assert_awaited_once()
        _, kwargs = mock_jobs.create_ingest_job.await_args
        assert kwargs["parameters"]["operation"] == "parse_pdf_structure"
        assert kwargs["parameters"]["require_marker"] is True

    async def test_parse_pdf_structure_reports_marker_resource_limit(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """parse_pdf_structure reports ignored output_dir instead of running inline."""
        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.presentation.tools import document_tools

        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(
                job_id="job_output_dir", estimated_duration_seconds=10
            )
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        monkeypatch.setattr(
            document_tools.MarkerPDFExtractor,
            "require_backend_available",
            MagicMock(),
        )

        result = await document_tools.parse_pdf_structure(
            str(pdf_path),
            output_dir=str(tmp_path / "custom"),
        )

        assert "job_output_dir" in result
        assert "`output_dir` is ignored" in result

    async def test_parse_pdf_structure_reports_invalid_page_range_before_work(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.presentation.tools import document_tools

        monkeypatch.setattr(document_tools.pdf_extractor, "get_page_count", lambda _: 1)

        result = await document_tools.parse_pdf_structure(
            str(pdf_path),
            page_ranges=["2"],
            async_mode=False,
        )

        assert "Invalid PDF or page range" in result

    async def test_parse_pdf_structure_defaults_to_background_marker_job(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """parse_pdf_structure must return quickly instead of loading Marker inline."""
        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.presentation.tools import document_tools

        monkeypatch.setattr(
            document_tools,
            "get_marker_extractor",
            MagicMock(side_effect=AssertionError("Marker should load in the job")),
        )
        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(job_id="job_parse", estimated_duration_seconds=10)
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        monkeypatch.setattr(
            document_tools.MarkerPDFExtractor,
            "require_backend_available",
            MagicMock(),
        )

        result = await document_tools.parse_pdf_structure(str(pdf_path))

        assert "job_parse" in result
        mock_jobs.create_ingest_job.assert_awaited_once()
        args, kwargs = mock_jobs.create_ingest_job.await_args
        assert args[0] == [str(pdf_path)]
        assert kwargs["parameters"]["use_marker"] is True
        assert kwargs["parameters"]["operation"] == "parse_pdf_structure"
        assert kwargs["parameters"]["require_marker"] is True
        assert kwargs["parameters"]["page_ranges"] == []

    async def test_document_ocr_facade_routes_to_direct(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """document(op='ocr') should preserve the direct OCR tool contract."""
        from src.presentation.tools import document_tools

        async def fake_ocr(**kwargs):
            return {"success": True, "kwargs": kwargs}

        monkeypatch.setattr(document_tools, "ocr_pdf_document", fake_ocr)

        result = await document_tools.document(
            op="ocr",
            pdf_path="scan.pdf",
            output_path="scan.md",
            ocr_language="chi_tra",
            rotate_pages=True,
            deskew=True,
        )

        assert result["success"] is True
        assert result["kwargs"] == {
            "pdf_path": "scan.pdf",
            "output_path": "scan.md",
            "language": "chi_tra",
            "rotate_pages": True,
            "deskew": True,
            "ctx": None,
        }

    async def test_document_export_segmentation_facade_routes_to_direct(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """document(op='export_segmentation') should route to the direct tool."""
        from src.presentation.tools import document_tools

        async def fake_export(**kwargs):
            return {"success": True, "kwargs": kwargs}

        monkeypatch.setattr(document_tools, "export_document_segmentation", fake_export)

        result = await document_tools.document(
            op="export_segmentation",
            doc_id="doc_1",
            page=2,
            limit=10,
            output_path="segmentation.json",
        )

        assert result["success"] is True
        assert result["kwargs"] == {
            "doc_id": "doc_1",
            "page": 2,
            "limit": 10,
            "output_path": "segmentation.json",
            "ctx": None,
        }

    async def test_document_visualize_layout_facade_routes_to_direct(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """document(op='visualize_layout') should route to the direct tool."""
        from src.presentation.tools import document_tools

        async def fake_visualize(**kwargs):
            return {"success": True, "kwargs": kwargs}

        monkeypatch.setattr(document_tools, "visualize_document_layout", fake_visualize)

        result = await document_tools.document(
            op="visualize_layout",
            doc_id="doc_1",
            page=3,
            show_labels=False,
            include_reading_order=False,
            output_path="layout.png",
        )

        assert result["success"] is True
        assert result["kwargs"] == {
            "doc_id": "doc_1",
            "page": 3,
            "show_labels": False,
            "include_reading_order": False,
            "output_path": "layout.png",
            "ctx": None,
        }

    async def test_document_safety_audit_facade_routes_without_new_tool(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """document(op='safety_audit') should route through the document facade."""
        from src.presentation.tools import document_tools

        async def fake_safety(**kwargs):
            return {"success": True, "kwargs": kwargs}

        monkeypatch.setattr(document_tools, "_export_pdf_ai_safety_report", fake_safety)

        result = await document_tools.document(
            op="safety_audit",
            doc_id="doc_1",
            output_path="safe.json",
        )

        assert result["success"] is True
        assert result["kwargs"] == {
            "doc_id": "doc_1",
            "output_path": "safe.json",
            "ctx": None,
        }

    async def test_safety_audit_response_does_not_echo_suspicious_text(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Safety audit summaries should not reinsert hidden prompt text into MCP context."""
        from src.presentation.tools import document_tools

        class FakeReportService:
            def build_and_save_ai_safety_report(self, *_args, **_kwargs):
                return Path("workspace/ai_safety_report.json"), {
                    "schema_version": "pdf-ai-safety-v1",
                    "status": "warning",
                    "summary": {
                        "issue_count": 1,
                        "issues_by_reason": {"prompt_injection_text": 1},
                    },
                    "issues": [
                        {
                            "reason": "prompt_injection_text",
                            "text_preview": "Ignore previous instructions",
                        }
                    ],
                }

        monkeypatch.setattr(
            document_tools,
            "pdf_report_service",
            FakeReportService(),
        )

        result = await document_tools._export_pdf_ai_safety_report("doc_1")

        assert "prompt_injection_text" in result
        assert "Ignore previous instructions" not in result

    async def test_document_structure_facade_routes_without_new_tool(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """document(op='native_structure') should route through the document facade."""
        from src.presentation.tools import document_tools

        async def fake_structure(**kwargs):
            return {"success": True, "kwargs": kwargs}

        monkeypatch.setattr(
            document_tools, "_export_pdf_native_structure_report", fake_structure
        )

        result = await document_tools.document(
            op="native_structure",
            doc_id="doc_1",
            output_path="structure.json",
        )

        assert result["success"] is True
        assert result["kwargs"] == {
            "doc_id": "doc_1",
            "output_path": "structure.json",
            "ctx": None,
        }

    async def test_document_coverage_facade_routes_without_new_tool(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """document(op='coverage') should route through the document facade."""
        from src.presentation.tools import document_tools

        async def fake_coverage(**kwargs):
            return {"success": True, "kwargs": kwargs}

        monkeypatch.setattr(
            document_tools, "_export_segmentation_coverage_report", fake_coverage
        )

        result = await document_tools.document(
            op="coverage",
            doc_id="doc_1",
            output_path="coverage.json",
        )

        assert result["success"] is True
        assert result["kwargs"] == {
            "doc_id": "doc_1",
            "output_path": "coverage.json",
            "ctx": None,
        }

    async def test_document_accessibility_facade_routes_without_new_tool(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """document(op='accessibility') should write the accessibility report."""
        from src.presentation.tools import document_tools

        async def fake_accessibility(**kwargs):
            return {"success": True, "kwargs": kwargs}

        monkeypatch.setattr(
            document_tools, "_export_pdf_accessibility_report", fake_accessibility
        )

        result = await document_tools.document(
            op="accessibility",
            doc_id="doc_1",
            output_path="accessibility.json",
        )

        assert result["success"] is True
        assert result["kwargs"] == {
            "doc_id": "doc_1",
            "output_path": "accessibility.json",
            "ctx": None,
        }

    async def test_document_pointer_index_facade_routes_without_new_tool(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """document(op='pointer_index') should build a structural pointer artifact."""
        from src.presentation.tools import document_tools

        async def fake_pointer(**kwargs):
            return {"success": True, "kwargs": kwargs}

        monkeypatch.setattr(
            document_tools, "_build_structural_pointer_index", fake_pointer
        )

        result = await document_tools.document(
            op="pointer_index",
            doc_id="doc_1",
            output_path="section_pointer_index.jsonl",
        )

        assert result["success"] is True
        assert result["kwargs"] == {
            "doc_id": "doc_1",
            "output_path": "section_pointer_index.jsonl",
            "ctx": None,
        }

    async def test_document_structural_retrieve_facade_routes_without_new_tool(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """document(op='structural_retrieve') should query section pointers."""
        from src.presentation.tools import document_tools

        async def fake_retrieve(**kwargs):
            return {"success": True, "kwargs": kwargs}

        monkeypatch.setattr(document_tools, "_structural_retrieve", fake_retrieve)

        result = await document_tools.document(
            op="structural_retrieve",
            doc_id="doc_1",
            query="methods",
            limit=3,
            refresh=True,
        )

        assert result["success"] is True
        assert result["kwargs"] == {
            "doc_id": "doc_1",
            "query": "methods",
            "limit": 3,
            "refresh": True,
            "ctx": None,
        }

    async def test_document_compare_facade_requires_second_doc(
        self,
    ) -> None:
        """document(op='compare') should fail closed without doc_b_id."""
        from src.presentation.tools import document_tools

        result = await document_tools.document(
            op="compare",
            doc_id="doc_a",
            criteria="sedation",
        )

        assert "doc_b_id" in result

    async def test_document_structural_retrieve_facade_fails_closed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """document(op='structural_retrieve') should return errors as text."""
        from src.presentation.tools import document_tools

        mock_service = MagicMock()
        mock_service.retrieve = AsyncMock(side_effect=RuntimeError("boom"))
        monkeypatch.setattr(document_tools, "structural_pointer_service", mock_service)

        result = await document_tools.document(
            op="structural_retrieve",
            doc_id="doc_1",
            query="sedation",
        )

        assert "boom" in result

    async def test_document_audit_facade_runs_all_pdf_readiness_reports(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """document(op='audit', refresh=True) rebuilds readiness reports."""
        from src.presentation.tools import document_tools

        calls: list[tuple[str, dict[str, object]]] = []

        async def fake_safety(**kwargs):
            calls.append(("safety", kwargs))
            return "# PDF AI Safety Audit\n\n**output:** `safe.json`"

        async def fake_structure(**kwargs):
            calls.append(("structure", kwargs))
            return "# Native PDF Structure\n\n**output:** `structure.json`"

        async def fake_coverage(**kwargs):
            calls.append(("coverage", kwargs))
            return "# Segmentation Coverage Audit\n\n**output:** `coverage.json`"

        async def fake_accessibility(**kwargs):
            calls.append(("accessibility", kwargs))
            return "# PDF Accessibility Readiness\n\n**output:** `accessibility.json`"

        monkeypatch.setattr(document_tools, "_export_pdf_ai_safety_report", fake_safety)
        monkeypatch.setattr(
            document_tools, "_export_pdf_native_structure_report", fake_structure
        )
        monkeypatch.setattr(
            document_tools, "_export_segmentation_coverage_report", fake_coverage
        )
        monkeypatch.setattr(
            document_tools, "_export_pdf_accessibility_report", fake_accessibility
        )

        result = await document_tools.document(op="audit", doc_id="doc_1", refresh=True)

        assert "# Document AI Readiness Audit" in result
        assert "PDF AI Safety Audit" in result
        assert "Native PDF Structure" in result
        assert "Segmentation Coverage Audit" in result
        assert "PDF Accessibility Readiness" in result
        assert [name for name, _kwargs in calls] == [
            "safety",
            "structure",
            "coverage",
            "accessibility",
        ]
        assert all(kwargs["doc_id"] == "doc_1" for _name, kwargs in calls)
        assert all(kwargs["output_path"] is None for _name, kwargs in calls)

    async def test_document_audit_skips_existing_artifacts_by_default(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """document(op='audit') should reuse current audit artifacts unless refreshed."""
        from src.domain.entities import DocumentManifest
        from src.presentation.tools import document_tools

        doc_dir = tmp_path / "doc_1"
        doc_dir.mkdir()
        (doc_dir / "doc_1_manifest.json").write_text("{}", encoding="utf-8")
        (doc_dir / "segmentation.json").write_text(
            '{"source_revision_id":"rev-1","locator_source_sha256":"loc-1"}',
            encoding="utf-8",
        )
        for name in ("ai_safety_report", "native_structure"):
            (doc_dir / f"{name}.json").write_text(
                '{"status":"ok","doc_id":"doc_1"}',
                encoding="utf-8",
            )
        for name in ("segmentation_coverage", "accessibility_report"):
            (doc_dir / f"{name}.json").write_text(
                '{"status":"ok","doc_id":"doc_1",'
                '"source_revision_id":"rev-1","locator_source_sha256":"loc-1"}',
                encoding="utf-8",
            )
        manifest = DocumentManifest(
            doc_id="doc_1",
            filename="paper.pdf",
            title="Paper",
            page_count=3,
            manifest_path=str(doc_dir / "doc_1_manifest.json"),
        )
        mock_repo = MagicMock()
        mock_repo.load_manifest.return_value = manifest
        mock_repo.get_doc_dir.side_effect = AssertionError(
            "readiness discovery must not create document directories"
        )
        mock_safety = AsyncMock(return_value="# PDF AI Safety Audit")
        mock_structure = AsyncMock(return_value="# Native PDF Structure")
        mock_coverage = AsyncMock(return_value="# Segmentation Coverage")
        mock_accessibility = AsyncMock(return_value="# Accessibility")
        monkeypatch.setattr(document_tools, "repository", mock_repo)
        monkeypatch.setattr(document_tools, "_export_pdf_ai_safety_report", mock_safety)
        monkeypatch.setattr(
            document_tools, "_export_pdf_native_structure_report", mock_structure
        )
        monkeypatch.setattr(
            document_tools, "_export_segmentation_coverage_report", mock_coverage
        )
        monkeypatch.setattr(
            document_tools, "_export_pdf_accessibility_report", mock_accessibility
        )

        result = await document_tools.document(op="audit", doc_id="doc_1")

        assert "**status:** cached" in result
        assert "ai_safety_report: cached" in result
        mock_safety.assert_not_awaited()
        mock_structure.assert_not_awaited()
        mock_coverage.assert_not_awaited()
        mock_accessibility.assert_not_awaited()

    async def test_document_audit_reruns_invalid_cached_artifact(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Invalid cached audit reports should be refreshed by default."""
        from src.domain.entities import DocumentManifest
        from src.presentation.tools import document_tools

        doc_dir = tmp_path / "doc_1"
        doc_dir.mkdir()
        for name in ("doc_1_manifest.json", "doc_1_full.md", "blocks.json"):
            (doc_dir / name).write_text("{}", encoding="utf-8")
        (doc_dir / "segmentation.json").write_text(
            '{"source_revision_id":"rev-1","locator_source_sha256":"loc-1"}',
            encoding="utf-8",
        )
        (doc_dir / "native_structure.json").write_text(
            '{"status":"ok","doc_id":"doc_1"}',
            encoding="utf-8",
        )
        for name in ("segmentation_coverage", "accessibility_report"):
            (doc_dir / f"{name}.json").write_text(
                '{"status":"ok","doc_id":"doc_1",'
                '"source_revision_id":"rev-1","locator_source_sha256":"loc-1"}',
                encoding="utf-8",
            )
        (doc_dir / "ai_safety_report.json").write_text(
            '{"status":"skipped"}',
            encoding="utf-8",
        )
        manifest = DocumentManifest(
            doc_id="doc_1",
            filename="paper.pdf",
            title="Paper",
            page_count=3,
            manifest_path=str(doc_dir / "doc_1_manifest.json"),
            markdown_path=str(doc_dir / "doc_1_full.md"),
        )
        mock_repo = MagicMock()
        mock_repo.load_manifest.return_value = manifest
        mock_repo.get_doc_dir.side_effect = AssertionError(
            "readiness discovery must not create document directories"
        )
        mock_safety = AsyncMock(return_value="# PDF AI Safety Audit")
        mock_structure = AsyncMock(return_value="# Native PDF Structure")
        mock_coverage = AsyncMock(return_value="# Segmentation Coverage")
        mock_accessibility = AsyncMock(return_value="# Accessibility")
        monkeypatch.setattr(document_tools, "repository", mock_repo)
        monkeypatch.setattr(document_tools, "_export_pdf_ai_safety_report", mock_safety)
        monkeypatch.setattr(
            document_tools, "_export_pdf_native_structure_report", mock_structure
        )
        monkeypatch.setattr(
            document_tools, "_export_segmentation_coverage_report", mock_coverage
        )
        monkeypatch.setattr(
            document_tools, "_export_pdf_accessibility_report", mock_accessibility
        )

        result = await document_tools.document(op="audit", doc_id="doc_1")

        assert "**status:** ok" in result
        mock_safety.assert_awaited_once()
        mock_structure.assert_not_awaited()
        mock_coverage.assert_not_awaited()
        mock_accessibility.assert_not_awaited()

    async def test_inspect_document_manifest_shows_source_engine(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """inspect_document_manifest must surface which engine parsed the doc.

        Regression coverage for the multi-engine provenance work: agents
        need to see source_engine (pymupdf/pymupdf4llm/docling/mineru[:sub])
        when inspecting an already-ingested document, not just at ingest time.
        """
        from src.domain.entities import DocumentManifest
        from src.presentation.tools import document_tools

        manifest = DocumentManifest(
            doc_id="doc_1",
            filename="paper.pdf",
            title="Paper",
            page_count=3,
            source_engine="docling",
        )
        mock_service = MagicMock()
        mock_service.get_manifest = AsyncMock(return_value=manifest)
        monkeypatch.setattr(document_tools, "document_service", mock_service)

        result = await document_tools.inspect_document_manifest("doc_1")

        assert "**source_engine:** docling" in result

    async def test_document_audit_reports_partial_failure_status(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """document(op='audit') should not hide failed child reports."""
        from src.presentation.tools import document_tools

        async def fake_safety(**_kwargs):
            return "# PDF AI Safety Audit\n\n**output:** `safe.json`"

        async def fake_structure(**_kwargs):
            return "??native structure failed"

        async def fake_coverage(**_kwargs):
            return "# Segmentation Coverage Audit\n\n**output:** `coverage.json`"

        async def fake_accessibility(**_kwargs):
            return "# PDF Accessibility Readiness\n\n**status:** unavailable"

        monkeypatch.setattr(document_tools, "_export_pdf_ai_safety_report", fake_safety)
        monkeypatch.setattr(
            document_tools, "_export_pdf_native_structure_report", fake_structure
        )
        monkeypatch.setattr(
            document_tools, "_export_segmentation_coverage_report", fake_coverage
        )
        monkeypatch.setattr(
            document_tools, "_export_pdf_accessibility_report", fake_accessibility
        )

        result = await document_tools.document(op="audit", doc_id="doc_1")

        assert "**status:** warning" in result
        assert "failed_reports" in result
        assert "native_structure" in result
        assert "accessibility_report" in result

    async def test_json_artifact_summary_bounds_preview_items(
        self, tmp_path: Path
    ) -> None:
        """Large native report previews should not be inlined unbounded."""
        from src.presentation.tools import document_tools

        result = document_tools._format_json_artifact_summary(
            title="Native PDF Structure",
            doc_id="doc_1",
            target=tmp_path / "native_structure.json",
            report={
                "status": "ok",
                "schema_version": "pdf-native-structure-v1",
                "metrics": {"outline": ["A" * 5_000]},
                "preview": [{"text": "B" * 5_000}],
            },
            preview_key="preview",
        )

        assert "text_truncated" in result
        assert "sha256:" in result
        assert "A" * 2_000 not in result
        assert "B" * 2_000 not in result

    async def test_document_prepare_ai_reports_artifacts_and_next_actions(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """document(op='prepare_ai') returns bounded readiness state for agents."""
        from src.domain.entities import DocumentManifest
        from src.presentation.tools import document_tools

        doc_dir = tmp_path / "doc_1"
        doc_dir.mkdir()
        for name in (
            "doc_1_manifest.json",
            "doc_1_full.md",
            "blocks.json",
            "segmentation.json",
            "citation_index.jsonl",
            "ai_safety_report.json",
        ):
            (doc_dir / name).write_text("{}", encoding="utf-8")
        manifest = DocumentManifest(
            doc_id="doc_1",
            filename="paper.pdf",
            title="Paper",
            page_count=3,
            text_quality_status="ok",
            manifest_path=str(doc_dir / "doc_1_manifest.json"),
            markdown_path=str(doc_dir / "doc_1_full.md"),
        )

        mock_service = MagicMock()
        mock_service.get_manifest = AsyncMock(return_value=manifest)
        mock_repo = MagicMock()
        mock_repo.get_doc_dir.return_value = doc_dir
        mock_repo.load_manifest.return_value = manifest
        monkeypatch.setattr(document_tools, "document_service", mock_service)
        monkeypatch.setattr(document_tools, "repository", mock_repo)

        result = await document_tools.document(op="prepare_ai", doc_id="doc_1")

        assert "# Document AI Readiness" in result
        assert "**status:** needs_attention" in result
        assert "has_ai_safety_report: yes" in result
        assert "has_native_structure: no" in result
        assert "has_coverage_report: no" in result
        assert "ai_safety_report: `" in result
        assert 'document(op="audit", doc_id="doc_1")' in result
        assert 'evidence(op="find", doc_id="doc_1", query="...")' in result
        match = re.search(r"```json\n(.*?)\n```", result, flags=re.DOTALL)
        assert match is not None
        payload = json.loads(match.group(1))
        assert payload["schema_version"] == "document-readiness-v2"
        assert payload["doc_id"] == "doc_1"
        assert payload["status"] == "needs_attention"
        assert payload["capabilities"]["has_ai_safety_report"] is True
        assert "missing_native_structure" in payload["blockers"]
        assert 'document(op="audit", doc_id="doc_1")' in payload["next_actions"]

    async def test_document_prepare_ai_json_reports_multiple_blockers(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """JSON readiness should expose blockers without requiring Markdown parsing."""
        from src.domain.entities import DocumentManifest
        from src.presentation.tools import document_tools

        doc_dir = tmp_path / "doc_1"
        doc_dir.mkdir()
        for name in ("doc_1_manifest.json", "doc_1_full.md", "blocks.json"):
            (doc_dir / name).write_text("{}", encoding="utf-8")
        manifest = DocumentManifest(
            doc_id="doc_1",
            filename="paper.pdf",
            title="Paper",
            page_count=3,
            text_quality_status="low_text",
            ocr_recommended=True,
            manifest_path=str(doc_dir / "doc_1_manifest.json"),
            markdown_path=str(doc_dir / "doc_1_full.md"),
        )
        mock_repo = MagicMock()
        mock_repo.load_manifest.return_value = manifest
        mock_repo.get_doc_dir.side_effect = AssertionError(
            "prepare_ai JSON must inspect artifacts read-only"
        )
        monkeypatch.setattr(document_tools, "repository", mock_repo)

        payload = await document_tools.document(
            op="prepare_ai",
            doc_id="doc_1",
            output_format="json",
        )

        assert isinstance(payload, dict)
        assert payload["schema_version"] == "document-readiness-v2"
        assert payload["status"] == "needs_attention"
        assert "ocr_recommended" in payload["blockers"]
        assert "missing_ai_safety_report" in payload["blockers"]
        assert "missing_native_structure" in payload["blockers"]
        assert "missing_segmentation_coverage" in payload["blockers"]
        assert "missing_citation_index" in payload["warnings"]

    async def test_document_prepare_ai_json_blocks_invalid_cached_audit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """prepare_ai JSON should expose invalid cached audit artifacts directly."""
        from src.domain.entities import DocumentManifest
        from src.presentation.tools import document_tools

        doc_dir = tmp_path / "doc_1"
        doc_dir.mkdir()
        for name in (
            "doc_1_manifest.json",
            "doc_1_full.md",
            "blocks.json",
            "citation_index.jsonl",
            "citation_index.status.json",
        ):
            (doc_dir / name).write_text("{}", encoding="utf-8")
        (doc_dir / "segmentation.json").write_text(
            '{"source_revision_id":"rev-1","locator_source_sha256":"loc-1"}',
            encoding="utf-8",
        )
        (doc_dir / "native_structure.json").write_text(
            '{"status":"ok","doc_id":"doc_1"}',
            encoding="utf-8",
        )
        for name in ("segmentation_coverage", "accessibility_report"):
            (doc_dir / f"{name}.json").write_text(
                '{"status":"ok","doc_id":"doc_1",'
                '"source_revision_id":"rev-1","locator_source_sha256":"loc-1"}',
                encoding="utf-8",
            )
        (doc_dir / "ai_safety_report.json").write_text(
            '{"status":"unavailable"}',
            encoding="utf-8",
        )
        manifest = DocumentManifest(
            doc_id="doc_1",
            filename="paper.pdf",
            title="Paper",
            page_count=3,
            manifest_path=str(doc_dir / "doc_1_manifest.json"),
            markdown_path=str(doc_dir / "doc_1_full.md"),
        )
        mock_repo = MagicMock()
        mock_repo.load_manifest.return_value = manifest
        mock_repo.get_doc_dir.side_effect = AssertionError(
            "prepare_ai JSON must inspect artifacts read-only"
        )
        monkeypatch.setattr(document_tools, "repository", mock_repo)

        payload = await document_tools.document(
            op="prepare_ai",
            doc_id="doc_1",
            output_format="json",
        )

        assert payload["status"] == "needs_attention"
        assert payload["invalid_audits"] == ["ai_safety_report"]
        assert "invalid_ai_safety_report" in payload["blockers"]
        assert 'document(op="audit", doc_id="doc_1")' in payload["next_actions"]

    async def test_document_auto_routes_doc_id_to_prepare_ai(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """document(op='auto', doc_id=...) should choose the readiness path."""
        from src.presentation.tools import document_tools

        async def fake_prepare_ai(**kwargs):
            return {"success": True, "kwargs": kwargs}

        monkeypatch.setattr(document_tools, "_prepare_document_for_ai", fake_prepare_ai)

        result = await document_tools.document(op="auto", doc_id="doc_1")

        assert result["success"] is True
        assert result["kwargs"] == {
            "doc_id": "doc_1",
            "ctx": None,
            "output_format": "markdown",
        }

    async def test_document_auto_routes_file_paths_to_ingest(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """document(op='auto', file_paths=...) should keep ingest job semantics."""
        from src.presentation.tools import document_tools

        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")
        mock_ingest = AsyncMock(return_value="job created")
        monkeypatch.setattr(document_tools, "ingest_documents", mock_ingest)

        result = await document_tools.document(
            op="auto",
            file_paths=[str(pdf_path)],
            async_mode=True,
            use_marker=False,
        )

        assert result == "job created"
        mock_ingest.assert_awaited_once()
        args, kwargs = mock_ingest.await_args
        assert args[0] == [str(pdf_path)]
        assert kwargs["async_mode"] is True

    async def test_document_auto_routes_mixed_batch_to_mixed_ingest(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A batch containing a non-PDF file must route to the mixed handler.

        Regression coverage: `ingest_documents` only understands PDFs, so a
        mixed PDF+DOCX file_paths list must not be silently mis-ingested as
        if every path were a PDF.
        """
        from src.presentation.tools import document_tools

        mock_ingest_documents = AsyncMock(
            side_effect=AssertionError("mixed batches must not use ingest_documents")
        )
        mock_mixed_batch = AsyncMock(return_value="mixed job created")
        monkeypatch.setattr(document_tools, "ingest_documents", mock_ingest_documents)
        monkeypatch.setattr(
            document_tools, "_ingest_mixed_document_batch", mock_mixed_batch
        )

        result = await document_tools.document(
            op="auto",
            file_paths=["/papers/study.pdf", "/reports/summary.docx"],
        )

        assert result == "mixed job created"
        mock_mixed_batch.assert_awaited_once()
        mock_ingest_documents.assert_not_awaited()
        args, _kwargs = mock_mixed_batch.await_args
        assert args[0] == ["/papers/study.pdf", "/reports/summary.docx"]

    async def test_document_auto_rejects_conflicting_inputs(self) -> None:
        """document(op='auto') should not guess when doc_id and file_paths conflict."""
        from src.presentation.tools.document_tools import document

        result = await document("auto", doc_id="doc_1", file_paths=["paper.pdf"])

        assert "Choose either doc_id or file_paths" in result

    async def test_fetch_document_asset_large_full_text_returns_preview(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Large full_text payloads should be capped before returning to Cline."""
        from src.presentation.tools import document_tools

        large_text = "# Full Text\n\n" + ("B" * 80_000)
        mock_assets = MagicMock()
        mock_assets.fetch_asset = AsyncMock(
            return_value=FetchResult(
                doc_id="doc_big",
                asset_type=AssetType.FULL_TEXT,
                asset_id="full",
                success=True,
                text_content=large_text,
                line_start=0,
                line_end=1,
                line_source="document",
            )
        )
        monkeypatch.setattr(document_tools, "asset_service", mock_assets)
        monkeypatch.setattr(
            document_tools.repository,
            "get_doc_dir",
            lambda doc_id: Path("/data") / doc_id,
        )

        result = await document_tools.fetch_document_asset(
            "doc_big",
            "full_text",
            "full",
        )

        assert len(result) == 1
        text = result[0].text
        assert len(text) < 20_000
        assert "full_text" in text
        assert "sha256:" in text
        assert "B" * 30_000 not in text

    async def test_fetch_document_asset_large_figure_base64_returns_pointer(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Huge figure base64 payloads should be omitted from MCP image responses."""
        from src.presentation.tools import document_tools

        mock_assets = MagicMock()
        mock_assets.fetch_asset = AsyncMock(
            return_value=FetchResult(
                doc_id="doc_fig",
                asset_type=AssetType.FIGURE,
                asset_id="fig_1",
                success=True,
                image_base64="A" * 900_000,
                image_media_type="image/png",
                text_content="Page 1 | huge figure",
                page=1,
                width=6000,
                height=4000,
            )
        )
        monkeypatch.setattr(document_tools, "asset_service", mock_assets)

        result = await document_tools.fetch_document_asset(
            "doc_fig",
            "figure",
            "fig_1",
            max_size=0,
        )

        assert len(result) == 1
        text = result[0].text
        assert len(text) < 20_000
        assert "image_base64_chars" in text
        assert "sha256:" in text
        assert "A" * 30_000 not in text

    async def test_search_source_location_no_blocks(self) -> None:
        """search_source_location returns error when blocks.json missing."""
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_blocks.return_value = None
            from src.presentation.tools.document_tools import (
                search_source_location,
            )

            result = await search_source_location("doc_123", "test query")
            assert "❌" in result

    async def test_find_evidence_spans_returns_span_asset_ref(self) -> None:
        """find_evidence_spans returns citation-ready span refs."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "x" * 40 + "Needle guidance reduced complications."
        blocks = [
            {
                "block_id": "blk_1",
                "block_type": "Text",
                "page": 2,
                "text": "Needle guidance reduced complications.",
                "metadata": {"line_start": 5, "line_end": 6},
            }
        ]

        span = EvidenceSpan.create(
            doc_id="doc_123",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text="Needle guidance reduced complications.",
            block_id="blk_1",
            page=2,
            line_start=5,
            line_end=6,
            char_start=40,
            char_end=78,
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import find_evidence_spans

            result = await find_evidence_spans("doc_123", "reduced")

        assert span.span_id in result
        assert "AssetRef" in result
        assert '"source_type": "span"' in result
        assert '"char_range"' in result

    async def test_find_evidence_spans_rebuilds_stale_citation_index(self) -> None:
        """find_evidence_spans rebuilds cached spans when markdown changed."""
        from src.domain.citation import EvidenceSpan

        markdown = "New exact evidence sentence.\n"
        old_span = EvidenceSpan.create(
            doc_id="doc_123",
            source_revision_id=hashlib.sha256(b"old markdown").hexdigest(),
            span_kind="sentence",
            text="Old cached sentence.",
            block_id="blk_old",
        )
        blocks = [
            {
                "block_id": "blk_1",
                "block_type": "Text",
                "page": 1,
                "text": "New exact evidence sentence.",
                "metadata": {"line_start": 0, "line_end": 1},
            }
        ]
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [old_span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import find_evidence_spans

            result = await find_evidence_spans("doc_123", "New exact")

        assert "New exact evidence sentence." in result
        mock_repo.save_citation_index.assert_called_once()
        saved_spans = mock_repo.save_citation_index.call_args.args[1]
        assert saved_spans
        assert (
            saved_spans[0].source_revision_id
            == hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        )

    async def test_find_evidence_spans_reports_empty_blocks_without_zero_byte_index(
        self, tmp_path: Path
    ) -> None:
        """Empty MarkerOutput blocks should not recreate a 0-byte citation index."""
        blocks = [
            {
                "block_id": "mk_1",
                "block_type": "MarkdownOutput",
                "page": 1,
                "text": "",
            }
        ]
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = []
            mock_repo.load_markdown.return_value = "# Abstract\n\nBody"
            mock_repo.load_blocks.return_value = blocks
            mock_repo.get_doc_dir.return_value = tmp_path
            from src.presentation.tools.document_tools import find_evidence_spans

            result = await find_evidence_spans("doc_empty")

        assert "No citation-ready evidence spans" in result
        assert "did not contain citeable text" in result
        assert not (tmp_path / "citation_index.jsonl").exists()
        status = json.loads(
            (tmp_path / "citation_index.status.json").read_text(encoding="utf-8")
        )
        assert status["found"] == 0
        mock_repo.save_citation_index.assert_not_called()

    async def test_verify_citation_ref_detects_valid_span(self) -> None:
        """verify_citation_ref validates quote hash and source revision."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "Exact quote for verification."
        blocks = [
            {
                "block_id": "blk_1",
                "block_type": "Text",
                "page": 1,
                "text": markdown,
                "metadata": {"line_start": 0, "line_end": 1},
            }
        ]

        span = EvidenceSpan.create(
            doc_id="doc_123",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text="Exact quote for verification.",
            block_id="blk_1",
            page=1,
            line_start=0,
            line_end=1,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        ref = {
            "source_type": "span",
            "doc_id": "doc_123",
            "span_id": span.span_id,
            "source_revision_id": span.source_revision_id,
            "locator_version": span.locator_version,
            "locator_source_sha256": span.locator_source_sha256,
            "block_id": span.block_id,
            "page": span.page,
            "line_range": [span.line_start, span.line_end],
            "char_range": [span.char_start, span.char_end],
            "byte_range": [span.byte_start, span.byte_end],
            "quote": span.text,
            "quote_sha256": span.text_sha256,
        }
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import verify_citation_ref

            result = await verify_citation_ref(ref)

        assert "verified" in result
        assert span.span_id in result

    async def test_verify_citation_ref_rejects_stripped_locator_ref(self) -> None:
        """Citation verification must fail closed when locator/hash fields are absent."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "Exact quote for verification."
        blocks = [
            {
                "block_id": "blk_1",
                "block_type": "Text",
                "page": 1,
                "text": markdown,
                "metadata": {"line_start": 0, "line_end": 1},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_123",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text=markdown,
            block_id="blk_1",
            page=1,
            line_start=0,
            line_end=1,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        ref = {
            "source_type": "span",
            "doc_id": "doc_123",
            "span_id": span.span_id,
            "source_revision_id": span.source_revision_id,
            "locator_version": span.locator_version,
        }
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import verify_citation_ref

            result = await verify_citation_ref(ref)

        assert "mismatch" in result.lower()
        assert "locator_source_sha256 missing" in result
        assert "quote_sha256 or text_sha256 missing" in result

    async def test_verify_citation_ref_detects_locator_mismatch(self) -> None:
        """verify_citation_ref rejects stale or fabricated locator fields."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "0123456789Exact quote for verification."
        blocks = [
            {
                "block_id": "blk_1",
                "block_type": "Text",
                "page": 1,
                "text": "Exact quote for verification.",
                "metadata": {"line_start": 2, "line_end": 3},
            }
        ]

        span = EvidenceSpan.create(
            doc_id="doc_123",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text="Exact quote for verification.",
            block_id="blk_1",
            page=1,
            line_start=2,
            line_end=3,
            char_start=10,
            char_end=39,
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        ref = {
            "source_type": "span",
            "doc_id": "doc_123",
            "span_id": span.span_id,
            "source_revision_id": span.source_revision_id,
            "locator_version": "citation-span-v0",
            "locator_source_sha256": span.locator_source_sha256,
            "block_id": "wrong_block",
            "page": 9,
            "line_range": [20, 21],
            "char_range": [0, 4],
            "byte_range": [0, 4],
            "quote": span.text,
            "quote_sha256": span.text_sha256,
        }
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import verify_citation_ref

            result = await verify_citation_ref(ref)

        assert "mismatch" in result.lower()
        assert "locator_version mismatch" in result
        assert "block_id mismatch" in result
        assert "page mismatch" in result
        assert "line_range mismatch" in result
        assert "char_range mismatch" in result
        assert "byte_range mismatch" in result

    async def test_citation_bundle_exports_verified_entries(self) -> None:
        """citation_bundle returns AssetRefs plus structured verification."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "Stable evidence for bundle export."
        blocks = [
            {
                "block_id": "blk_1",
                "block_type": "Text",
                "page": 3,
                "text": markdown,
                "metadata": {"line_start": 1, "line_end": 2},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_123",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text=markdown,
            block_id="blk_1",
            page=3,
            line_start=1,
            line_end=2,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import citation_bundle

            result = await citation_bundle(
                "doc_123",
                query="bundle",
                output_format="json",
            )

        assert result["success"] is True
        assert result["entries"][0]["asset_ref"]["span_id"] == span.span_id
        assert result["entries"][0]["verification"]["valid"] is True
        assert result["entries"][0]["locator_source_sha256"]
        assert result["entries"][0]["foam"]["block_anchor"].startswith("^spn-")
        assert result["entries"][0]["foam"]["wikilink"].startswith("[[doc_123#^spn-")

    async def test_citation_bundle_large_json_payload_returns_bounded_record(
        self,
    ) -> None:
        """Large citation JSON payloads should not inline full quotes/context."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "A" * 90_000
        blocks = [
            {
                "block_id": "blk_big",
                "block_type": "Text",
                "page": 3,
                "text": markdown,
                "metadata": {"line_start": 1, "line_end": 300},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_big",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="block",
            text=markdown,
            block_id="blk_big",
            page=3,
            line_start=1,
            line_end=300,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import citation_bundle

            result = await citation_bundle(
                "doc_big",
                output_format="json",
            )

        assert result["success"] is True
        assert result["response_truncated"] is True
        assert result["sha256"].startswith("sha256:")
        assert len(json.dumps(result)) < 20_000
        assert "A" * 30_000 not in json.dumps(result)

    async def test_citation_bundle_exports_foam_evidence_pack(self) -> None:
        """citation_bundle(output_format='foam') returns Foam-ready anchors."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "Stable evidence for Foam promotion."
        blocks = [
            {
                "block_id": "blk_foam",
                "block_type": "Text",
                "page": 4,
                "text": markdown,
                "metadata": {"line_start": 2, "line_end": 3},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_foam",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text=markdown,
            block_id="blk_foam",
            page=4,
            line_start=2,
            line_end=3,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import citation_bundle

            result = await citation_bundle(
                "doc_foam",
                query="Foam",
                output_format="foam",
                citation_key="paper-key",
            )

        assert result.startswith("---\n")
        assert 'type: "evidence_pack"' in result
        assert "[[paper-key#^spn-" in result
        assert "![[paper-key#^spn-" in result
        assert "^spn-" in result
        assert span.source_revision_id in result
        assert span.text_sha256 in result
        assert '"source_type": "span"' in result

    async def test_citation_bundle_writes_foam_pack_and_index(
        self, tmp_path: Path
    ) -> None:
        """citation_bundle can persist a Foam evidence pack and index block."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "Writable Foam evidence."
        blocks = [
            {
                "block_id": "blk_write",
                "block_type": "Text",
                "page": 2,
                "text": markdown,
                "metadata": {"line_start": 0, "line_end": 1},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_write",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text=markdown,
            block_id="blk_write",
            page=2,
            line_start=0,
            line_end=1,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import citation_bundle

            result = await citation_bundle(
                "doc_write",
                output_format="foam",
                citation_key="paper-key",
                wiki_root=str(tmp_path),
                output_path="evidence/paper-key.md",
                index_path="Evidence Index.md",
                overwrite=True,
            )

        note_path = tmp_path / "evidence" / "paper-key.md"
        index_path = tmp_path / "Evidence Index.md"
        assert result["success"] is True
        assert Path(result["output_path"]) == note_path
        assert note_path.exists()
        assert index_path.exists()
        assert "[[paper-key#^spn-" in note_path.read_text(encoding="utf-8")
        assert "[[paper-key#^spn-" in index_path.read_text(encoding="utf-8")

    async def test_evidence_claim_promotion_returns_verified_candidates(self) -> None:
        """Claim promotion proposes exact-quote candidates with forced verification."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "Claim-worthy evidence reduces uncertainty."
        blocks = [
            {
                "block_id": "blk_claim",
                "block_type": "Text",
                "page": 3,
                "text": markdown,
                "metadata": {"line_start": 1, "line_end": 2},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_claim",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text=markdown,
            block_id="blk_claim",
            page=3,
            line_start=1,
            line_end=2,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import evidence

            result = await evidence(
                op="claim_promotion",
                doc_id="doc_claim",
                query="uncertainty",
                output_format="json",
                citation_key="paper-key",
            )

        assert result["success"] is True
        assert result["verification_required"] is True
        assert result["entries"][0]["promotion_status"] == "ready"
        assert result["entries"][0]["verified"] is True
        assert result["entries"][0]["claim_text"] == markdown
        assert result["entries"][0]["asset_ref"]["span_id"] == span.span_id
        assert result["entries"][0]["foam"]["block_anchor"].startswith("^clm-")

    async def test_evidence_claim_promotion_writes_verified_foam_pack(
        self, tmp_path: Path
    ) -> None:
        """Claim promotion writes Foam only after verification succeeds."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "Verified claim evidence belongs in the wiki."
        blocks = [
            {
                "block_id": "blk_claim_write",
                "block_type": "Text",
                "page": 5,
                "text": markdown,
                "metadata": {"line_start": 4, "line_end": 5},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_claim_write",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text=markdown,
            block_id="blk_claim_write",
            page=5,
            line_start=4,
            line_end=5,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import evidence

            result = await evidence(
                op="promote_claims",
                doc_id="doc_claim_write",
                output_format="foam",
                citation_key="paper-key",
                wiki_root=str(tmp_path),
                output_path="claims/paper-key-claims.md",
                index_path="Evidence Index.md",
                overwrite=True,
            )

        note_path = tmp_path / "claims" / "paper-key-claims.md"
        assert result["success"] is True
        assert Path(result["output_path"]) == note_path
        note_text = note_path.read_text(encoding="utf-8")
        assert 'type: "claim_promotion_pack"' in note_text
        assert "^clm-" in note_text
        assert "Verified claim evidence belongs in the wiki" in note_text
        assert "### Verification Payload" in note_text
        assert '"verification": {' in note_text
        assert '"valid": true' in note_text
        assert '"status": "verified"' in note_text
        assert "[[paper-key-claims#^clm-" in (tmp_path / "Evidence Index.md").read_text(
            encoding="utf-8"
        )

    async def test_evidence_claim_promotion_blocks_unverified_foam_write(
        self, tmp_path: Path
    ) -> None:
        """Foam writes are blocked if the candidate AssetRef fails verification."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256
        from src.presentation.tools.citation_support import asset_ref_from_span

        markdown = "Stale claim evidence should not be promoted."
        blocks = [
            {
                "block_id": "blk_claim_block",
                "block_type": "Text",
                "page": 1,
                "text": markdown,
                "metadata": {"line_start": 0, "line_end": 1},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_claim_block",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text=markdown,
            block_id="blk_claim_block",
            page=1,
            line_start=0,
            line_end=1,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        bad_ref = asset_ref_from_span(span)
        bad_ref["locator_version"] = "citation-span-v0"

        with (
            patch("src.presentation.tools.document_tools.repository") as mock_repo,
            patch(
                "src.presentation.tools.document_tools.asset_ref_from_span",
                return_value=bad_ref,
            ),
        ):
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import evidence

            result = await evidence(
                op="claims",
                doc_id="doc_claim_block",
                output_format="foam",
                wiki_root=str(tmp_path),
                overwrite=True,
            )

        assert result["success"] is False
        assert result["blocked_count"] == 1
        assert "verify first" in result["error"]

    async def test_evidence_health_validates_foam_asset_refs(
        self, tmp_path: Path
    ) -> None:
        """evidence(op='health') verifies embedded AssetRefs and Foam anchors."""
        from src.domain.citation import EvidenceSpan, blocks_locator_sha256

        markdown = "Healthy Foam evidence."
        blocks = [
            {
                "block_id": "blk_health",
                "block_type": "Text",
                "page": 1,
                "text": markdown,
                "metadata": {"line_start": 0, "line_end": 1},
            }
        ]
        span = EvidenceSpan.create(
            doc_id="doc_health",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text=markdown,
            block_id="blk_health",
            page=1,
            line_start=0,
            line_end=1,
            char_start=0,
            char_end=len(markdown),
            markdown=markdown,
            locator_source_sha256=blocks_locator_sha256(blocks),
        )
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import citation_bundle, evidence

            await citation_bundle(
                "doc_health",
                output_format="foam",
                citation_key="paper-key",
                wiki_root=str(tmp_path),
                output_path="paper-key.md",
                overwrite=True,
            )
            result = await evidence(
                "health",
                wiki_root=str(tmp_path),
                output_format="json",
            )

        assert result["success"] is True
        assert result["files_scanned"] >= 1
        assert result["span_asset_refs"] == 1
        assert result["valid_refs"] == 1
        assert result["invalid_refs"] == 0
        assert result["wikilink_issues"] == 0

    async def test_find_evidence_spans_rebuilds_when_blocks_metadata_changes(
        self,
    ) -> None:
        """find_evidence_spans rebuilds cached spans when block locators drift."""
        from src.domain.citation import EvidenceSpan

        markdown = "Stable evidence sentence.\n"
        old_span = EvidenceSpan.create(
            doc_id="doc_123",
            source_revision_id=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            span_kind="sentence",
            text="Stable evidence sentence.",
            block_id="blk_1",
            page=9,
            line_start=99,
            line_end=100,
        )
        old_span.locator_source_sha256 = "old-blocks-hash"
        blocks = [
            {
                "block_id": "blk_1",
                "block_type": "Text",
                "page": 1,
                "text": "Stable evidence sentence.",
                "metadata": {"line_start": 0, "line_end": 1},
            }
        ]
        with patch("src.presentation.tools.document_tools.repository") as mock_repo:
            mock_repo.load_citation_index.return_value = [old_span]
            mock_repo.load_markdown.return_value = markdown
            mock_repo.load_blocks.return_value = blocks
            from src.presentation.tools.document_tools import find_evidence_spans

            result = await find_evidence_spans("doc_123", "Stable evidence")

        assert "**Page:** 1" in result
        mock_repo.save_citation_index.assert_called_once()

    async def test_delete_document_success(self) -> None:
        """delete_document returns formatted summary on success."""
        with patch(
            "src.presentation.tools.document_tools.document_service"
        ) as mock_svc:
            mock_svc.delete_document = AsyncMock(
                return_value={
                    "success": True,
                    "doc_id": "doc_123",
                    "filename": "paper.pdf",
                    "warnings": ["kg not removed"],
                }
            )
            from src.presentation.tools.document_tools import delete_document

            result = await delete_document("doc_123")
            assert "✅" in result
            assert "paper.pdf" in result
            assert "warning" in result

    async def test_convert_pdf_to_docx_success(self) -> None:
        """convert_pdf_to_docx returns output summary on success."""
        with patch(
            "src.presentation.tools.document_tools.document_service"
        ) as mock_svc:
            mock_svc.convert_pdf_to_docx = AsyncMock(
                return_value={
                    "success": True,
                    "doc_id": "doc_123",
                    "mode": "content",
                    "output_path": "/workspace/converted.docx",
                    "figures_embedded": 2,
                    "tables_found": 1,
                }
            )
            from src.presentation.tools.document_tools import convert_pdf_to_docx

            result = await convert_pdf_to_docx("doc_123", async_mode=False)
            assert "✅" in result
            assert "converted.docx" in result

    async def test_convert_pdf_to_pptx_success(self) -> None:
        """convert_pdf_to_pptx returns output summary on success."""
        with patch(
            "src.presentation.tools.document_tools.document_service"
        ) as mock_svc:
            mock_svc.convert_pdf_to_pptx = AsyncMock(
                return_value={
                    "success": True,
                    "doc_id": "doc_123",
                    "mode": "content",
                    "output_path": "/workspace/converted.pptx",
                    "slides_created": 5,
                    "figure_slides": 2,
                }
            )
            from src.presentation.tools.document_tools import convert_pdf_to_pptx

            result = await convert_pdf_to_pptx("doc_123", async_mode=False)
            assert "✅" in result
            assert "converted.pptx" in result

    async def test_convert_pdf_to_docx_defaults_to_background_job(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Conversion defaults to a background job and does not run inline."""
        from src.presentation.tools import document_tools

        mock_jobs = MagicMock()
        mock_jobs.create_conversion_job = AsyncMock(
            return_value=MagicMock(
                job_id="job_convert_docx",
                estimated_duration_seconds=20,
            )
        )
        mock_service = MagicMock()
        mock_service.convert_pdf_to_docx = AsyncMock(
            side_effect=AssertionError("conversion should run inside the job")
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        monkeypatch.setattr(document_tools, "document_service", mock_service)

        result = await document_tools.convert_pdf_to_docx("doc_123")

        assert "job_convert_docx" in result
        mock_jobs.create_conversion_job.assert_awaited_once()
        _, kwargs = mock_jobs.create_conversion_job.await_args
        assert kwargs["operation"] == "pdf_to_docx"
        assert kwargs["parameters"]["target_format"] == "docx"
        assert callable(kwargs["handler"])
        mock_service.convert_pdf_to_docx.assert_not_awaited()

    async def test_ingest_documents_sync_forces_background_job_and_reports_progress(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """A sync MCP PDF ingest request should not run ETL in the request."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")
        fake_ctx = MagicMock()
        fake_ctx.report_progress = AsyncMock()
        fake_ctx.log = AsyncMock()

        from src.presentation.tools import document_tools

        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(job_id="job_sync_pdf", estimated_duration_seconds=10)
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        mock_service = MagicMock()
        mock_service.ingest = AsyncMock(
            side_effect=AssertionError("MCP sync PDF ingest must use a job")
        )
        monkeypatch.setattr(document_tools, "document_service", mock_service)

        result = await document_tools.ingest_documents(
            [str(pdf_path)], async_mode=False, ctx=fake_ctx
        )

        assert "job_sync_pdf" in result
        assert "background worker" in result
        mock_jobs.create_ingest_job.assert_awaited_once()
        _, kwargs = mock_jobs.create_ingest_job.await_args
        assert kwargs["parameters"]["operation"] == "ingest_documents"
        assert kwargs["parameters"]["use_marker"] is False
        assert kwargs["parameters"]["page_ranges"] == []
        mock_service.ingest.assert_not_awaited()
        assert fake_ctx.report_progress.await_count >= 3
        assert fake_ctx.log.await_count >= 2

    async def test_ingest_documents_sync_pdf_with_figures_reports_async_acceptance(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Sync PyMuPDF PDF + figure extraction must fail safe into a job."""
        pdf_path = tmp_path / "figures.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.presentation.tools import document_tools

        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(job_id="job_figures", estimated_duration_seconds=10)
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        mock_service = MagicMock()
        mock_service.ingest = AsyncMock(
            side_effect=AssertionError("figure extraction must run in the job")
        )
        monkeypatch.setattr(document_tools, "document_service", mock_service)

        result = await document_tools.ingest_documents(
            [str(pdf_path)],
            async_mode=False,
            use_marker=False,
            extract_figures=True,
        )

        assert "job_figures" in result
        assert "accepted_async" in result
        assert "reason" in result
        assert "next" in result
        mock_jobs.create_ingest_job.assert_awaited_once()
        _, kwargs = mock_jobs.create_ingest_job.await_args
        assert kwargs["parameters"]["extract_figures"] is True
        assert kwargs["parameters"]["index_knowledge_graph"] is False
        mock_service.ingest.assert_not_awaited()

    async def test_ingest_documents_sync_marker_is_forced_to_background_job(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A sync Marker request should become a job before any model load."""
        from src.presentation.tools import document_tools

        monkeypatch.setattr(
            document_tools,
            "get_marker_extractor",
            MagicMock(side_effect=AssertionError("Marker should load in the job")),
        )
        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(job_id="job_marker", estimated_duration_seconds=10)
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)

        result = await document_tools.ingest_documents(
            ["workspace/test.pdf"],
            async_mode=False,
            use_marker=True,
        )

        assert "job_marker" in result
        mock_jobs.create_ingest_job.assert_awaited_once()

    async def test_ingest_documents_async_marker_does_not_load_marker_in_request(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Async Marker job creation must not block on Marker model loading."""
        from src.presentation.tools import document_tools

        monkeypatch.setattr(
            document_tools,
            "get_marker_extractor",
            MagicMock(side_effect=AssertionError("Marker should load in the job")),
        )
        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(
                job_id="job_async_marker", estimated_duration_seconds=10
            )
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)

        result = await document_tools.ingest_documents(
            ["workspace/test.pdf"],
            async_mode=True,
            use_marker=True,
        )

        assert "job_async_marker" in result
        mock_jobs.create_ingest_job.assert_awaited_once()

    async def test_ingest_documents_sync_pdf_skips_page_count_before_background_job(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The sync MCP path should not probe PDF pages before job creation."""
        from src.presentation.tools import document_tools

        page_count = MagicMock(
            side_effect=AssertionError("page counting belongs in the job")
        )
        monkeypatch.setattr(
            document_tools.pdf_extractor,
            "get_page_count",
            page_count,
        )
        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(
                job_id="job_no_page_probe", estimated_duration_seconds=10
            )
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        mock_service = MagicMock()
        mock_service.ingest = AsyncMock(
            side_effect=AssertionError("uncountable PDFs should not run synchronously")
        )
        monkeypatch.setattr(document_tools, "document_service", mock_service)

        result = await document_tools.ingest_documents(
            ["workspace/test.pdf"],
            async_mode=False,
        )

        assert "job_no_page_probe" in result
        mock_jobs.create_ingest_job.assert_awaited_once()
        page_count.assert_not_called()

    async def test_ingest_documents_sync_pdf_never_counts_pages_in_request(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Sync PDF ingest should skip page-count probes and create a job."""
        pdf_path = tmp_path / "small.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.presentation.tools import document_tools

        page_count = MagicMock(
            side_effect=AssertionError("page counting belongs in the job")
        )
        monkeypatch.setattr(document_tools.pdf_extractor, "get_page_count", page_count)
        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(job_id="job_sync_pdf", estimated_duration_seconds=10)
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        mock_service = MagicMock()
        mock_service.ingest = AsyncMock(
            side_effect=AssertionError("PDFs should not run synchronously")
        )
        monkeypatch.setattr(document_tools, "document_service", mock_service)

        result = await document_tools.ingest_documents(
            [str(pdf_path)],
            async_mode=False,
        )

        assert "job_sync_pdf" in result
        mock_jobs.create_ingest_job.assert_awaited_once()
        page_count.assert_not_called()

    async def test_ingest_documents_sync_lightrag_does_not_inline_indexing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """LightRAG indexing stays out of the synchronous MCP request path."""
        pdf_path = tmp_path / "kg.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        from src.presentation.tools import document_tools

        monkeypatch.setattr(
            document_tools.pdf_extractor,
            "get_page_count",
            MagicMock(return_value=1),
        )
        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(job_id="job_lightrag", estimated_duration_seconds=10)
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)
        mock_service = MagicMock()
        mock_service.knowledge_graph = MagicMock(is_available=True)
        mock_service.ingest = AsyncMock(
            side_effect=AssertionError("LightRAG should run in the job")
        )
        monkeypatch.setattr(document_tools, "document_service", mock_service)

        result = await document_tools.ingest_documents(
            [str(pdf_path)],
            async_mode=False,
        )

        assert "job_lightrag" in result
        mock_jobs.create_ingest_job.assert_awaited_once()

    async def test_ingest_documents_async_passes_use_marker_to_job(self) -> None:
        """ingest_documents async job preserves Marker tuning parameters."""
        with (
            patch("src.presentation.tools.document_tools.job_service") as mock_jobs,
            patch(
                "src.presentation.tools.document_tools.get_marker_extractor"
            ) as mock_marker,
        ):
            mock_jobs.create_ingest_job = AsyncMock(
                return_value=MagicMock(job_id="job_123", estimated_duration_seconds=10)
            )
            mock_marker.return_value = MagicMock()
            from src.presentation.tools.document_tools import ingest_documents

            result = await ingest_documents(
                ["workspace/test.pdf"],
                async_mode=True,
                use_marker=True,
                marker_max_pages_per_chunk=200,
                extract_figures=False,
                page_ranges=["1-50", "100-120"],
            )

        assert "job_123" in result
        _, kwargs = mock_jobs.create_ingest_job.await_args
        assert kwargs["parameters"] == {
            "use_marker": True,
            "ocr_enabled": False,
            "ocr_language": "eng",
            "rotate_pages": False,
            "deskew": False,
            "marker_max_pages_per_chunk": 200,
            "extract_figures": False,
            "index_knowledge_graph": False,
            "page_ranges": ["1-50", "100-120"],
            "operation": "ingest_documents",
            "require_marker": False,
            "etl_profile": "default",
        }

    async def test_ingest_documents_async_passes_ocr_params_to_job(self) -> None:
        """ingest_documents async job preserves OCR parameters."""
        with patch("src.presentation.tools.document_tools.job_service") as mock_jobs:
            mock_jobs.create_ingest_job = AsyncMock(
                return_value=MagicMock(job_id="job_ocr", estimated_duration_seconds=10)
            )
            from src.presentation.tools.document_tools import ingest_documents

            result = await ingest_documents(
                ["workspace/test.pdf"],
                async_mode=True,
                ocr_enabled=True,
                ocr_language="chi_tra",
                rotate_pages=True,
                deskew=True,
            )

        assert "job_ocr" in result
        _, kwargs = mock_jobs.create_ingest_job.await_args
        assert kwargs["parameters"] == {
            "use_marker": False,
            "ocr_enabled": True,
            "ocr_language": "chi_tra",
            "rotate_pages": True,
            "deskew": True,
            "marker_max_pages_per_chunk": 0,
            "extract_figures": True,
            "index_knowledge_graph": False,
            "page_ranges": [],
            "operation": "ingest_documents",
            "require_marker": False,
            "etl_profile": "default",
        }

    async def test_ingest_documents_async_reports_job_creation_limit(self) -> None:
        """ingest_documents returns an MCP error instead of raising when job queue is full."""
        with patch("src.presentation.tools.document_tools.job_service") as mock_jobs:
            mock_jobs.create_ingest_job = AsyncMock(
                side_effect=RuntimeError("Too many concurrent jobs")
            )
            from src.presentation.tools.document_tools import ingest_documents

            result = await ingest_documents(["workspace/test.pdf"], async_mode=True)

        assert "Could Not Create ETL Job" in result
        assert "Too many concurrent jobs" in result

    async def test_export_document_segmentation_success(self) -> None:
        """export_document_segmentation writes schema summary."""
        segmentation = MagicMock(
            doc_id="doc_123",
            source_backend="marker",
            segments=[
                MagicMock(
                    reading_order=1,
                    page_number=1,
                    segment_type="Text",
                    segment_id="seg_1",
                )
            ],
            page_count=3,
        )
        segmentation.page_count_summary.return_value = {1: 1}

        with patch(
            "src.presentation.tools.document_tools.segmentation_service"
        ) as mock_seg:
            mock_seg.build_and_save_document_segmentation = AsyncMock(
                return_value=(Path("workspace/segmentation.json"), segmentation)
            )
            from src.presentation.tools.document_tools import (
                export_document_segmentation,
            )

            result = await export_document_segmentation("doc_123")

        assert "Unified Segmentation Export" in result
        assert "segmentation.json" in result

    async def test_export_document_segmentation_reuses_saved_result(self) -> None:
        """Segmentation export should not rebuild the same large payload twice."""
        segmentation = MagicMock(
            doc_id="doc_big",
            source_backend="pymupdf",
            segments=[],
            page_count=10,
        )
        segmentation.page_count_summary.return_value = {}

        with patch(
            "src.presentation.tools.document_tools.segmentation_service"
        ) as mock_seg:
            mock_seg.build_and_save_document_segmentation = AsyncMock(
                return_value=(Path("workspace/segmentation.json"), segmentation)
            )
            mock_seg.export_document_segmentation = AsyncMock(
                side_effect=AssertionError("segmentation was rebuilt")
            )
            from src.presentation.tools.document_tools import (
                export_document_segmentation,
            )

            result = await export_document_segmentation("doc_big")

        assert "Unified Segmentation Export" in result
        mock_seg.build_and_save_document_segmentation.assert_awaited_once()
        mock_seg.export_document_segmentation.assert_not_called()

    async def test_visualize_document_layout_returns_overlay(self) -> None:
        """visualize_document_layout returns text and image payload."""
        segmentation = MagicMock(segments=[MagicMock()], doc_id="doc_123")
        overlay = MagicMock(
            image_base64="ZmFrZQ==",
            width=1200,
            height=1600,
            output_path="workspace/layout.png",
        )

        with (
            patch(
                "src.presentation.tools.document_tools.segmentation_service"
            ) as mock_seg,
            patch(
                "src.presentation.tools.document_tools.layout_visualizer"
            ) as mock_visualizer,
            patch("src.presentation.tools.document_tools.repository") as mock_repo,
        ):
            mock_seg.export_document_segmentation = AsyncMock(return_value=segmentation)
            mock_visualizer.render_page_overlay.return_value = overlay
            mock_repo.get_doc_dir.return_value = Path("workspace/doc_123")
            from src.presentation.tools.document_tools import visualize_document_layout

            result = await visualize_document_layout("doc_123", page=1)

        assert len(result) == 2
        assert result[0].type == "text"
        assert result[1].type == "image"

    async def test_ocr_pdf_document_success(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """ocr_pdf_document returns a background OCR job instead of blocking."""
        pdf_path = tmp_path / "sample.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        from src.presentation.tools import document_tools

        mock_jobs = MagicMock()
        mock_jobs.create_ingest_job = AsyncMock(
            return_value=MagicMock(job_id="job_ocr_doc", estimated_duration_seconds=10)
        )
        monkeypatch.setattr(document_tools, "job_service", mock_jobs)

        result = await document_tools.ocr_pdf_document(
            str(pdf_path),
            language="eng",
            rotate_pages=True,
        )

        assert "job_ocr_doc" in result
        _, kwargs = mock_jobs.create_ingest_job.await_args
        assert kwargs["parameters"]["operation"] == "ocr_pdf_document"
        assert kwargs["parameters"]["ocr_enabled"] is True
        assert kwargs["parameters"]["rotate_pages"] is True

    async def test_fetch_document_asset_reports_context_progress(self) -> None:
        """fetch_document_asset emits MCP progress when Context is injected."""
        fake_ctx = MagicMock()
        fake_ctx.report_progress = AsyncMock()
        fake_ctx.log = AsyncMock()

        with patch(
            "src.presentation.tools.document_tools.asset_service"
        ) as mock_assets:
            mock_assets.fetch_asset = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    image_base64=None,
                    asset_id="sec_1",
                    page=1,
                    line_start=0,
                    line_end=3,
                    section_title="Introduction",
                    source_block_id="blk_0001",
                    text_content="section text",
                )
            )
            from src.presentation.tools.document_tools import fetch_document_asset

            result = await fetch_document_asset(
                "doc_123",
                "section",
                "sec_1",
                ctx=fake_ctx,
            )

        assert result[0].type == "text"
        assert "Line Range:" in result[0].text
        assert "L1-3" in result[0].text
        assert fake_ctx.report_progress.await_count >= 2

    async def test_fetch_document_asset_full_text_uses_tool_layer(self) -> None:
        """Smoke the full_text fetch path agents rely on after PDF ingest."""
        with patch(
            "src.presentation.tools.document_tools.asset_service"
        ) as mock_assets:
            mock_assets.fetch_asset = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    image_base64=None,
                    asset_id="full",
                    page=None,
                    line_start=0,
                    line_end=2,
                    section_title=None,
                    source_block_id=None,
                    text_content="# Paper\n\nBody text",
                )
            )
            from src.presentation.tools.document_tools import fetch_document_asset

            result = await fetch_document_asset("doc_pdf", "full_text")

        assert result[0].type == "text"
        assert "## Full_Text: full" in result[0].text
        assert "# Paper" in result[0].text
        mock_assets.fetch_asset.assert_awaited_once_with(
            "doc_pdf",
            "full_text",
            "full",
            max_size=None,
        )

    async def test_document_op_routes_list(self) -> None:
        """document(op, ...) exposes PDF document CRUD through one entrypoint."""
        with patch(
            "src.presentation.tools.document_tools.list_documents",
            new_callable=AsyncMock,
        ) as mock_list:
            mock_list.return_value = "documents"
            from src.presentation.tools.document_tools import document

            result = await document("list")

        assert result == "documents"
        mock_list.assert_awaited_once_with()

    async def test_document_op_rejects_unknown_operation(self) -> None:
        """document(op, ...) fails closed for unsupported operations."""
        from src.presentation.tools.document_tools import document

        result = await document("compress")

        assert "Unsupported document op" in result

    async def test_document_op_routes_delete(self) -> None:
        """document(op='delete') delegates to the legacy delete tool."""
        with patch(
            "src.presentation.tools.document_tools.delete_document",
            new_callable=AsyncMock,
        ) as mock_delete:
            mock_delete.return_value = "deleted"
            from src.presentation.tools.document_tools import document

            result = await document("delete", doc_id="doc_123")

        assert result == "deleted"
        mock_delete.assert_awaited_once_with("doc_123")

    async def test_document_asset_op_routes_get(self) -> None:
        """document_asset(op='get') delegates to the legacy precise asset fetcher."""
        payload = [MagicMock(type="text", text="asset")]
        with patch(
            "src.presentation.tools.document_tools.fetch_document_asset",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = payload
            from src.presentation.tools.document_tools import document_asset

            result = await document_asset(
                "get",
                doc_id="doc_123",
                asset_type="section",
                asset_id="sec_1",
                max_size=512,
            )

        assert result == payload
        mock_fetch.assert_awaited_once_with(
            "doc_123",
            "section",
            "sec_1",
            max_size=512,
            max_chars=None,
            ctx=None,
        )

    async def test_document_asset_op_rejects_missing_get_type(self) -> None:
        """document_asset(op='get') requires an asset_type."""
        from src.presentation.tools.document_tools import document_asset

        result = await document_asset("get", doc_id="doc_123", asset_id="sec_1")

        assert isinstance(result, str)
        assert "asset_type is required" in result

    async def test_document_asset_writes_table_and_figure_foam_notes(
        self, tmp_path: Path
    ) -> None:
        """document_asset(op='foam_notes') writes table/figure evidence notes."""
        from src.domain.entities import (
            DocumentAssets,
            DocumentManifest,
            FigureAsset,
            TableAsset,
        )

        manifest = DocumentManifest(
            doc_id="doc_assets",
            filename="paper.pdf",
            source_pdf_sha256="pdf-hash",
            assets=DocumentAssets(
                tables=[
                    TableAsset(
                        id="tab_1",
                        page=2,
                        markdown="| A | B |\n| --- | --- |\n| x | y |",
                        row_count=1,
                        col_count=2,
                        source_block_id="blk_tab",
                        source_order=3,
                        line_start=10,
                        line_end=13,
                        section_title="Results",
                    )
                ],
                figures=[
                    FigureAsset(
                        id="fig_1_1",
                        page=3,
                        path=str(tmp_path / "fig.png"),
                        caption="Workflow diagram",
                        width=640,
                        height=480,
                        source_block_id="blk_fig",
                        source_order=4,
                        line_start=20,
                        line_end=21,
                        section_title="Methods",
                    )
                ],
            ),
        )
        with patch(
            "src.presentation.tools.document_tools.document_service"
        ) as mock_service:
            mock_service.get_manifest = AsyncMock(return_value=manifest)
            from src.presentation.tools.document_tools import document_asset

            result = await document_asset(
                "foam_notes",
                doc_id="doc_assets",
                asset_type="all",
                asset_id="all",
                wiki_root=str(tmp_path),
                output_dir="assets",
                index_path="Evidence Index.md",
                citation_key="paper-key",
                response_format="json",
                overwrite=True,
            )

        assert result["success"] is True
        assert result["written_count"] == 2
        note_texts = [
            Path(item["path"]).read_text(encoding="utf-8") for item in result["written"]
        ]
        assert any('type: "table_evidence"' in text for text in note_texts)
        assert any('type: "figure_evidence"' in text for text in note_texts)
        assert any('"source_type": "table"' in text for text in note_texts)
        assert any('"source_type": "figure"' in text for text in note_texts)
        index_text = (tmp_path / "Evidence Index.md").read_text(encoding="utf-8")
        assert "[[paper-key-tab-1#^tab-" in index_text
        assert "[[paper-key-fig-1-1#^fig-" in index_text

    async def test_evidence_health_validates_table_and_figure_asset_refs(
        self, tmp_path: Path
    ) -> None:
        """Foam health verifies table/figure AssetRefs against the manifest."""
        from src.domain.entities import (
            DocumentAssets,
            DocumentManifest,
            FigureAsset,
            TableAsset,
        )

        manifest = DocumentManifest(
            doc_id="doc_assets",
            filename="paper.pdf",
            source_pdf_sha256="pdf-hash",
            assets=DocumentAssets(
                tables=[
                    TableAsset(
                        id="tab_1",
                        page=2,
                        markdown="| A | B |\n| --- | --- |\n| x | y |",
                        source_block_id="blk_tab",
                        source_order=3,
                        line_start=10,
                        line_end=13,
                    )
                ],
                figures=[
                    FigureAsset(
                        id="fig_1_1",
                        page=3,
                        path=str(tmp_path / "fig.png"),
                        caption="Workflow diagram",
                        width=640,
                        height=480,
                        source_block_id="blk_fig",
                        source_order=4,
                        line_start=20,
                        line_end=21,
                    )
                ],
            ),
        )
        with (
            patch("src.presentation.tools.document_tools.document_service") as mock_svc,
            patch("src.presentation.tools.document_tools.repository") as mock_repo,
        ):
            mock_svc.get_manifest = AsyncMock(return_value=manifest)
            mock_repo.load_manifest.return_value = manifest
            from src.presentation.tools.document_tools import document_asset, evidence

            await document_asset(
                "foam_notes",
                doc_id="doc_assets",
                asset_type="all",
                asset_id="all",
                wiki_root=str(tmp_path),
                output_dir="assets",
                citation_key="paper-key",
                response_format="json",
                overwrite=True,
            )
            result = await evidence(
                "health",
                wiki_root=str(tmp_path),
                output_format="json",
            )

        assert result["success"] is True
        assert result["asset_refs"] == 2
        assert result["valid_refs"] == 2
        assert result["invalid_refs"] == 0
        assert result["wikilink_issues"] == 0

    async def test_evidence_op_routes_find(self) -> None:
        """evidence(op='find') keeps citation span lookup behind one entrypoint."""
        with patch(
            "src.presentation.tools.document_tools.find_evidence_spans",
            new_callable=AsyncMock,
        ) as mock_find:
            mock_find.return_value = "spans"
            from src.presentation.tools.document_tools import evidence

            result = await evidence("find", doc_id="doc_123", query="dose", limit=3)

        assert result == "spans"
        mock_find.assert_awaited_once_with(
            "doc_123",
            query="dose",
            span_id="",
            span_kinds=None,
            limit=3,
        )

    async def test_convert_document_routes_pdf_to_docx(self) -> None:
        """convert_document routes PDF document conversions through one entrypoint."""
        with patch(
            "src.presentation.tools.document_tools.convert_pdf_to_docx",
            new_callable=AsyncMock,
        ) as mock_convert:
            mock_convert.return_value = "converted"
            from src.presentation.tools.document_tools import convert_document

            result = await convert_document(
                "doc_123",
                "docx",
                source_format="pdf",
                output_path="out.docx",
                mode="content",
            )

        assert result == "converted"
        mock_convert.assert_awaited_once_with(
            "doc_123",
            output_path="out.docx",
            mode="content",
            async_mode=True,
            ctx=None,
        )

    async def test_convert_document_rejects_unsupported_pair(self) -> None:
        """convert_document fails closed for unsupported source/target pairs."""
        from src.presentation.tools.document_tools import convert_document

        result = await convert_document("doc_123", "xlsx", source_format="pdf")

        assert "Unsupported conversion" in result

    async def test_convert_document_auto_uses_source_extension_first(self) -> None:
        """Auto source detection must not treat a PDF path as a DOCX doc_id."""
        with patch(
            "src.presentation.tools.docx_tools.convert_docx_to_doc",
            new_callable=AsyncMock,
        ) as mock_convert:
            from src.presentation.tools.document_tools import convert_document

            result = await convert_document("paper.pdf", "doc")

        assert "Unsupported conversion" in result
        mock_convert.assert_not_awaited()

    async def test_convert_document_routes_docx_to_pdf(self) -> None:
        """convert_document preserves DOCX conversion output-path handling."""
        with patch(
            "src.presentation.tools.docx_tools.convert_docx_to_pdf",
            new_callable=AsyncMock,
        ) as mock_convert:
            mock_convert.return_value = "pdf"
            from src.presentation.tools.document_tools import convert_document

            result = await convert_document(
                "docx_123",
                "pdf",
                source_format="docx",
                output_path="out.pdf",
                mode="fidelity",
            )

        assert result == "pdf"
        mock_convert.assert_awaited_once_with(
            "docx_123",
            output_path="out.pdf",
            mode="fidelity",
            async_mode=True,
            ctx=None,
        )

    async def test_convert_document_routes_markdown_to_docx(self) -> None:
        """convert_document routes Markdown exports without changing export roots."""
        with patch(
            "src.presentation.tools.docx_tools.export_markdown",
            new_callable=AsyncMock,
        ) as mock_export:
            mock_export.return_value = "docx"
            from src.presentation.tools.document_tools import convert_document

            result = await convert_document(
                "notes.md",
                "docx",
                source_format="markdown",
                output_path="notes.docx",
            )

        assert result == "docx"
        mock_export.assert_awaited_once_with(
            md_path="notes.md",
            md_text=None,
            output_path="notes.docx",
            output_format="docx",
            async_mode=True,
            ctx=None,
        )

    async def test_document_asset_op_routes_section_tree(self) -> None:
        """document_asset(op='tree') keeps section-tree affordances available."""
        with patch(
            "src.presentation.tools.section_tools.list_section_tree",
            new_callable=AsyncMock,
        ) as mock_tree:
            mock_tree.return_value = "tree"
            from src.presentation.tools.document_tools import document_asset

            result = await document_asset(
                "tree",
                doc_id="doc_123",
                max_depth=2,
                response_format="flat",
            )

        assert result == "tree"
        mock_tree.assert_awaited_once_with("doc_123", 2, "flat")

    async def test_document_asset_op_routes_section_blocks(self) -> None:
        """document_asset(op='blocks') preserves include_children and block filters."""
        with patch(
            "src.presentation.tools.section_tools.get_section_blocks",
            new_callable=AsyncMock,
        ) as mock_blocks:
            mock_blocks.return_value = "blocks"
            from src.presentation.tools.document_tools import document_asset

            result = await document_asset(
                "blocks",
                doc_id="doc_123",
                path="Intro",
                include_children=False,
                block_types=["Table"],
                limit=5,
            )

        assert result == "blocks"
        mock_blocks.assert_awaited_once_with(
            "doc_123",
            "Intro",
            False,
            ["Table"],
            5,
        )

    async def test_evidence_op_routes_locate(self) -> None:
        """evidence(op='locate') keeps source-location search available."""
        with patch(
            "src.presentation.tools.document_tools.search_source_location",
            new_callable=AsyncMock,
        ) as mock_locate:
            mock_locate.return_value = "locations"
            from src.presentation.tools.document_tools import evidence

            result = await evidence(
                "locate",
                doc_id="doc_123",
                query="needle",
                block_types=["Text"],
            )

        assert result == "locations"
        mock_locate.assert_awaited_once_with(
            "doc_123",
            "needle",
            block_types=["Text"],
        )

    async def test_evidence_op_routes_bundle_foam_options(self) -> None:
        """evidence(op='bundle') preserves Foam bundle options."""
        with patch(
            "src.presentation.tools.document_tools.citation_bundle",
            new_callable=AsyncMock,
        ) as mock_bundle:
            mock_bundle.return_value = "foam pack"
            from src.presentation.tools.document_tools import evidence

            result = await evidence(
                "bundle",
                doc_id="doc_123",
                query="dose",
                output_format="foam",
                citation_key="paper-key",
                limit=2,
            )

        assert result == "foam pack"
        mock_bundle.assert_awaited_once_with(
            "doc_123",
            query="dose",
            span_id="",
            span_kinds=None,
            limit=2,
            include_verification=True,
            output_format="foam",
            citation_key="paper-key",
            wiki_root="",
            output_path="",
            index_path="",
            update_index=True,
            overwrite=False,
        )

    async def test_evidence_op_routes_health(self) -> None:
        """evidence(op='health') audits a Foam wiki root."""
        from src.presentation.tools.document_tools import evidence

        result = await evidence(
            "health", wiki_root="/missing/wiki", output_format="json"
        )

        assert result["success"] is False
        assert "wiki_root does not exist" in result["error"]

    async def test_evidence_op_routes_verify(self) -> None:
        """evidence(op='verify') delegates AssetRef verification unchanged."""
        ref = {"source_type": "span", "doc_id": "doc_123", "span_id": "span_1"}
        with patch(
            "src.presentation.tools.document_tools.verify_citation_ref",
            new_callable=AsyncMock,
        ) as mock_verify:
            mock_verify.return_value = "verified"
            from src.presentation.tools.document_tools import evidence

            result = await evidence("verify", ref=ref)

        assert result == "verified"
        mock_verify.assert_awaited_once_with(ref)


# ============================================================================
# Table Tools
# ============================================================================
