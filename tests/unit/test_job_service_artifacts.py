from __future__ import annotations

from unittest.mock import MagicMock

from src.application.document_readiness_service import DocumentReadinessService
from src.application.job_service import JobService
from src.domain.entities import DocumentManifest, IngestResult


def test_document_result_payload_discovers_pdf_readiness_artifacts(tmp_path):
    """Completed ingest payloads should expose audit artifacts for job status."""
    doc_dir = tmp_path / "doc_123"
    doc_dir.mkdir()
    for name in (
        "doc_123_manifest.json",
        "doc_123_full.md",
        "blocks.json",
        "segmentation.json",
        "citation_index.jsonl",
        "citation_index.status.json",
        "ai_safety_report.json",
        "native_structure.json",
        "segmentation_coverage.json",
        "accessibility_report.json",
    ):
        (doc_dir / name).write_text("{}", encoding="utf-8")

    document_service = MagicMock()
    document_service.repository.get_doc_dir.return_value = doc_dir
    manifest = DocumentManifest(
        doc_id="doc_123",
        filename="paper.pdf",
        manifest_path=str(doc_dir / "doc_123_manifest.json"),
        markdown_path=str(doc_dir / "doc_123_full.md"),
    )
    result = IngestResult(
        doc_id="doc_123",
        filename="paper.pdf",
        backend="pymupdf",
        manifest=manifest,
    )

    payload = JobService(job_store=MagicMock())._document_result_payload(
        "paper.pdf",
        result,
        document_service=document_service,
    )

    assert payload["artifacts"]["ai_safety_report"].endswith("ai_safety_report.json")
    assert payload["artifacts"]["native_structure"].endswith("native_structure.json")
    assert payload["artifacts"]["segmentation_coverage"].endswith(
        "segmentation_coverage.json"
    )
    assert payload["artifacts"]["accessibility_report"].endswith(
        "accessibility_report.json"
    )
    assert payload["audit_artifacts_available"] is True


def test_document_readiness_ignores_manifest_paths_outside_base_dir(tmp_path):
    """Read-only artifact discovery must not trust escaped manifest paths."""
    base_dir = tmp_path / "data"
    doc_dir = base_dir / "doc_123"
    doc_dir.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "doc_123_full.md").write_text("SECRET-SENTINEL", encoding="utf-8")
    (doc_dir / "doc_123_manifest.json").write_text("{}", encoding="utf-8")
    manifest = DocumentManifest(
        doc_id="doc_123",
        filename="paper.pdf",
        manifest_path=str(outside / "doc_123_manifest.json"),
        markdown_path=str(outside / "doc_123_full.md"),
    )
    repository = MagicMock()
    repository.base_dir = base_dir
    repository.load_manifest.return_value = manifest

    payload = DocumentReadinessService(repository).build_payload("doc_123")

    assert payload["artifacts"]["manifest"] == str(doc_dir / "doc_123_manifest.json")
    assert payload["artifacts"]["markdown"] is None
    assert payload["capabilities"]["has_markdown"] is False


def test_document_readiness_blocks_unavailable_audit_artifact(tmp_path):
    """Cached audit artifacts with failed statuses must not make a document ready."""
    doc_dir = tmp_path / "doc_123"
    doc_dir.mkdir()
    for name in (
        "doc_123_manifest.json",
        "doc_123_full.md",
        "blocks.json",
        "citation_index.jsonl",
        "citation_index.status.json",
    ):
        (doc_dir / name).write_text("{}", encoding="utf-8")
    (doc_dir / "segmentation.json").write_text(
        '{"source_revision_id":"rev-new","locator_source_sha256":"loc-new"}',
        encoding="utf-8",
    )
    (doc_dir / "native_structure.json").write_text(
        '{"status":"ok","doc_id":"doc_123"}',
        encoding="utf-8",
    )
    for name in ("segmentation_coverage", "accessibility_report"):
        (doc_dir / f"{name}.json").write_text(
            '{"status":"ok","doc_id":"doc_123",'
            '"source_revision_id":"rev-new","locator_source_sha256":"loc-new"}',
            encoding="utf-8",
        )
    (doc_dir / "ai_safety_report.json").write_text(
        '{"status":"unavailable","doc_id":"doc_123"}',
        encoding="utf-8",
    )
    manifest = DocumentManifest(
        doc_id="doc_123",
        filename="paper.pdf",
        manifest_path=str(doc_dir / "doc_123_manifest.json"),
        markdown_path=str(doc_dir / "doc_123_full.md"),
    )
    repository = MagicMock()
    repository.load_manifest.return_value = manifest

    payload = DocumentReadinessService(repository).build_payload("doc_123")

    assert payload["status"] == "needs_attention"
    assert payload["missing_audits"] == []
    assert payload["invalid_audits"] == ["ai_safety_report"]
    assert "invalid_ai_safety_report" in payload["blockers"]
    assert payload["audit_artifacts"]["ai_safety_report"]["reason"] == (
        "status_unavailable"
    )


def test_document_readiness_blocks_stale_segmentation_audit_artifact(tmp_path):
    """Coverage/accessibility audits should match the current segmentation identity."""
    doc_dir = tmp_path / "doc_123"
    doc_dir.mkdir()
    for name in (
        "doc_123_manifest.json",
        "doc_123_full.md",
        "blocks.json",
        "citation_index.jsonl",
        "citation_index.status.json",
    ):
        (doc_dir / name).write_text("{}", encoding="utf-8")
    for name in ("ai_safety_report", "native_structure"):
        (doc_dir / f"{name}.json").write_text(
            '{"status":"ok","doc_id":"doc_123"}',
            encoding="utf-8",
        )
    (doc_dir / "accessibility_report.json").write_text(
        '{"status":"ok","doc_id":"doc_123",'
        '"source_revision_id":"rev-new","locator_source_sha256":"loc-new"}',
        encoding="utf-8",
    )
    (doc_dir / "segmentation.json").write_text(
        '{"source_revision_id":"rev-new","locator_source_sha256":"loc-new"}',
        encoding="utf-8",
    )
    (doc_dir / "segmentation_coverage.json").write_text(
        '{"status":"ok","doc_id":"doc_123","source_revision_id":"rev-old",'
        '"locator_source_sha256":"loc-new"}',
        encoding="utf-8",
    )
    manifest = DocumentManifest(
        doc_id="doc_123",
        filename="paper.pdf",
        manifest_path=str(doc_dir / "doc_123_manifest.json"),
        markdown_path=str(doc_dir / "doc_123_full.md"),
    )
    repository = MagicMock()
    repository.load_manifest.return_value = manifest

    payload = DocumentReadinessService(repository).build_payload("doc_123")

    assert payload["invalid_audits"] == ["segmentation_coverage"]
    assert "invalid_segmentation_coverage" in payload["blockers"]
    assert payload["audit_artifacts"]["segmentation_coverage"]["reason"] == (
        "stale_source_revision_id"
    )
