from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from src.application.pdf_report_service import (
    PdfArtifactReportService,
    _bounded_json_dump,
)
from src.application.segmentation_service import SegmentationService
from src.domain.entities import DocumentAssets, DocumentManifest, FigureAsset


class _FakeExtractor:
    def audit_ai_safety(self, pdf_path: Path) -> dict[str, object]:
        return {
            "schema_version": "pdf-ai-safety-v1",
            "status": "warning",
            "issues": [{"reason": "prompt_injection_text", "page": 1}],
        }

    def extract_native_structure(self, pdf_path: Path) -> dict[str, object]:
        return {
            "schema_version": "pdf-native-structure-v1",
            "backend": "pymupdf",
            "outline": [{"level": 1, "title": "Intro", "page": 1}],
            "pages": [{"page": 1, "width": 300.0, "height": 220.0}],
            "capabilities": {"outline": True},
        }


def _manifest(doc_dir: Path) -> DocumentManifest:
    return DocumentManifest(
        doc_id="doc_test",
        filename="sample.pdf",
        title="Sample",
        page_count=1,
        source_pdf_sha256="sourcehash",
        markdown_path=str(doc_dir / "doc_test_full.md"),
        assets=DocumentAssets(),
    )


def _repository(doc_dir: Path) -> MagicMock:
    repository = MagicMock()
    repository.get_doc_dir.return_value = doc_dir
    repository.load_manifest.return_value = _manifest(doc_dir)
    repository.load_markdown.return_value = "Visible paragraph\n"
    repository.load_blocks.return_value = None
    return repository


def test_pdf_report_service_writes_safety_and_structure_reports(tmp_path: Path) -> None:
    doc_dir = tmp_path / "doc_test"
    doc_dir.mkdir()
    (doc_dir / "original.pdf").write_bytes(b"%PDF-1.4\n")
    repository = _repository(doc_dir)
    service = PdfArtifactReportService(repository, _FakeExtractor())

    safety_path, safety = service.build_and_save_ai_safety_report("doc_test")
    structure_path, structure = service.build_and_save_native_structure_report(
        "doc_test"
    )

    assert safety_path.name == "ai_safety_report.json"
    assert structure_path.name == "native_structure.json"
    assert safety["doc_id"] == "doc_test"
    assert safety["source_pdf_sha256"] == "sourcehash"
    assert structure["filename"] == "sample.pdf"
    assert json.loads(safety_path.read_text(encoding="utf-8"))["status"] == "warning"
    assert (
        json.loads(structure_path.read_text(encoding="utf-8"))["outline"][0]["title"]
        == "Intro"
    )


def test_pdf_report_service_rejects_reserved_core_artifact_output(
    tmp_path: Path,
) -> None:
    doc_dir = tmp_path / "doc_test"
    doc_dir.mkdir()
    (doc_dir / "original.pdf").write_bytes(b"%PDF-1.4\n")
    service = PdfArtifactReportService(_repository(doc_dir), _FakeExtractor())

    try:
        service.build_and_save_ai_safety_report(
            "doc_test",
            output_path="segmentation.json",
        )
    except ValueError as exc:
        assert "reserved document files" in str(exc)
    else:
        raise AssertionError("reserved output path should be rejected")


def test_pdf_report_service_marks_missing_extractor_capability_unavailable(
    tmp_path: Path,
) -> None:
    doc_dir = tmp_path / "doc_test"
    doc_dir.mkdir()
    (doc_dir / "original.pdf").write_bytes(b"%PDF-1.4\n")
    service = PdfArtifactReportService(_repository(doc_dir), object())

    _target, report = service.build_and_save_ai_safety_report("doc_test")

    assert report["status"] == "unavailable"
    assert "audit_ai_safety" in report["reason"]


def test_bounded_json_dump_hard_caps_large_issue_strings(
    monkeypatch,
) -> None:
    monkeypatch.setenv("ASSET_AWARE_PDF_REPORT_MAX_BYTES", "1024")
    report = {
        "schema_version": "pdf-ai-safety-v1",
        "status": "warning",
        "doc_id": "doc_test",
        "summary": {"issue_count": 1},
        "issues": [{"reason": "prompt_injection_text", "text_preview": "X" * 50_000}],
    }

    payload = _bounded_json_dump(report)
    parsed = json.loads(payload)

    assert len(payload.encode("utf-8")) <= 1024
    assert parsed["truncated"] is True


def test_bounded_json_dump_hard_caps_large_minimal_metadata(monkeypatch) -> None:
    """Fallback reports must stay below the byte cap even when metadata is huge."""
    monkeypatch.setenv("ASSET_AWARE_PDF_REPORT_MAX_BYTES", "1024")
    report = {
        "schema_version": "pdf-native-structure-v1",
        "status": "ok",
        "doc_id": "doc_test",
        "filename": "paper.pdf",
        "selected_page_map": [
            {"source": index, "selected": index} for index in range(500)
        ],
        "metrics": {"pages_with_segments": list(range(500))},
        "pages": [{"page": index, "text": "X" * 1000} for index in range(500)],
    }

    payload = _bounded_json_dump(report)
    parsed = json.loads(payload)

    assert len(payload.encode("utf-8")) <= 1024
    assert parsed["truncated"] is True
    assert parsed["summary"]["reason"] == "max_report_bytes"


def test_bounded_json_dump_prebounds_native_report_before_serializing(
    monkeypatch,
) -> None:
    """Huge native reports should be reduced before the first JSON serialization."""
    import src.application.pdf_report_service as pdf_report_service

    monkeypatch.setenv("ASSET_AWARE_PDF_REPORT_MAX_BYTES", "1024")
    report = {
        "schema_version": "pdf-native-structure-v1",
        "status": "ok",
        "doc_id": "doc_test",
        "pages": [{"page": index, "text": "X" * 1000} for index in range(500)],
        "outline": [{"level": 1, "title": f"Heading {index}"} for index in range(500)],
    }
    real_dumps = pdf_report_service.json.dumps

    def guarded_dumps(value, *args, **kwargs):
        if value is report:
            raise AssertionError("raw native report should be prebounded first")
        return real_dumps(value, *args, **kwargs)

    monkeypatch.setattr(pdf_report_service.json, "dumps", guarded_dumps)

    payload = _bounded_json_dump(report)
    parsed = json.loads(payload)

    assert len(payload.encode("utf-8")) <= 1024
    assert parsed["truncated"] is True


def test_bounded_json_dump_truncates_nested_strings_before_first_serialization(
    monkeypatch,
) -> None:
    monkeypatch.setenv("ASSET_AWARE_PDF_REPORT_MAX_BYTES", "2048")
    report = {
        "schema_version": "pdf-native-structure-v1",
        "status": "ok",
        "doc_id": "doc_test",
        "metadata": {"producer": "X" * 200_000},
        "pages": [{"page": 1, "text": "Y" * 200_000}],
    }

    payload = _bounded_json_dump(report)
    parsed = json.loads(payload)

    assert len(payload.encode("utf-8")) <= 2048
    assert parsed["truncated"] is True


async def test_pdf_report_service_writes_segmentation_coverage_report(
    tmp_path: Path,
) -> None:
    doc_dir = tmp_path / "doc_test"
    doc_dir.mkdir()
    (doc_dir / "doc_test_full.md").write_text("Visible paragraph\n", encoding="utf-8")
    (doc_dir / "blocks.json").write_text(
        json.dumps(
            [
                {
                    "block_id": "blk_1",
                    "block_type": "Text",
                    "page": 1,
                    "text": "Visible paragraph",
                    "bbox": [10, 20, 120, 40],
                    "section_hierarchy": {},
                    "metadata": {
                        "line_start": 0,
                        "line_end": 1,
                        "source_order": 1,
                        "source_backend": "pymupdf",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    repository = _repository(doc_dir)
    report_service = PdfArtifactReportService(repository, _FakeExtractor())
    segmentation_service = SegmentationService(repository)

    target, report = await report_service.build_and_save_segmentation_coverage_report(
        "doc_test", segmentation_service
    )

    assert target.name == "segmentation_coverage.json"
    assert report["schema_version"] == "segmentation-coverage-v1"
    assert report["status"] == "ok"
    assert report["metrics"]["segment_count"] == 1
    assert report["metrics"]["bbox_coverage_ratio"] == 1.0
    assert report["metrics"]["line_span_coverage_ratio"] == 1.0
    assert (
        json.loads(target.read_text(encoding="utf-8"))["metrics"][
            "reading_order_gap_pages"
        ]
        == []
    )


async def test_pdf_report_service_writes_accessibility_report(tmp_path: Path) -> None:
    doc_dir = tmp_path / "doc_test"
    doc_dir.mkdir()
    (doc_dir / "doc_test_full.md").write_text("Captioned figure\n", encoding="utf-8")
    manifest = _manifest(doc_dir)
    manifest.assets.figures.append(
        FigureAsset(
            id="fig_1",
            page=1,
            path=str(doc_dir / "images" / "fig_1.png"),
            caption="",
            figure_bbox=[],
            caption_bbox=[],
        )
    )
    repository = _repository(doc_dir)
    repository.load_manifest.return_value = manifest
    repository.load_blocks.return_value = [
        {
            "block_id": "fig_blk",
            "block_type": "Picture",
            "page": 1,
            "text": "Captioned figure",
            "bbox": [0, 0, 20, 20],
            "section_hierarchy": {"1": "Results"},
            "metadata": {
                "line_start": 0,
                "line_end": 1,
                "source_order": 1,
                "source_backend": "pymupdf",
            },
        }
    ]
    report_service = PdfArtifactReportService(repository, _FakeExtractor())
    segmentation_service = SegmentationService(repository)

    target, report = await report_service.build_and_save_accessibility_report(
        "doc_test",
        segmentation_service,
    )

    assert target.name == "accessibility_report.json"
    assert report["schema_version"] == "pdf-accessibility-v1"
    assert report["status"] == "warning"
    assert report["metrics"]["figure_count"] == 1
    assert report["metrics"]["figure_caption_coverage_ratio"] == 0.0
    assert {"severity": "warning", "reason": "missing_figure_captions"} in report[
        "issues"
    ]
