from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.application.structural_pointer_service import (
    DOCUMENT_COMPARISON_SCHEMA_VERSION,
    SECTION_POINTER_SCHEMA_VERSION,
    StructuralPointerService,
)
from src.domain.citation import EvidenceSpan
from src.domain.entities import DocumentManifest
from src.domain.segmentation import DocumentSegment, DocumentSegmentation


class _Repo:
    def __init__(self, root: Path, manifests: dict[str, DocumentManifest]):
        self.root = root
        self.manifests = manifests
        self.markdown: dict[str, str] = {}
        self.spans: dict[str, list[EvidenceSpan]] = {}

    def get_doc_dir(self, doc_id: str) -> Path:
        path = self.root / doc_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load_manifest(self, doc_id: str) -> DocumentManifest | None:
        return self.manifests.get(doc_id)

    def load_markdown(self, doc_id: str) -> str:
        return self.markdown.get(doc_id, "")

    def load_citation_index(self, doc_id: str) -> list[EvidenceSpan]:
        return self.spans.get(doc_id, [])


class _Segmentation:
    def __init__(self, segmentations: dict[str, DocumentSegmentation]):
        self.segmentations = segmentations

    async def export_document_segmentation(self, doc_id: str) -> DocumentSegmentation:
        return self.segmentations[doc_id]


def _manifest(doc_id: str) -> DocumentManifest:
    return DocumentManifest(
        doc_id=doc_id,
        filename=f"{doc_id}.pdf",
        title=f"{doc_id} title",
        page_count=2,
    )


def _segmentation(doc_id: str, text: str, section: str) -> DocumentSegmentation:
    return DocumentSegmentation(
        doc_id=doc_id,
        filename=f"{doc_id}.pdf",
        title=f"{doc_id} title",
        page_count=2,
        source_backend="pymupdf",
        source_revision_id=f"{doc_id}-rev",
        locator_version="citation-span-v1",
        locator_source_sha256=f"{doc_id}-locator",
        segments=[
            DocumentSegment(
                segment_id=f"{doc_id}_seg_1",
                segment_type="Text",
                page_number=1,
                text=text,
                reading_order=1,
                line_start=0,
                line_end=2,
                char_start=0,
                char_end=len(text),
                byte_start=0,
                byte_end=len(text.encode("utf-8")),
                source_revision_id=f"{doc_id}-rev",
                locator_version="citation-span-v1",
                locator_source_sha256=f"{doc_id}-locator",
                section_hierarchy=["Methods", section],
                source_backend="pymupdf",
            ),
            DocumentSegment(
                segment_id=f"{doc_id}_fig_1",
                segment_type="Picture",
                page_number=1,
                text="Figure caption",
                asset_id="fig_1",
                reading_order=2,
                line_start=2,
                line_end=3,
                source_revision_id=f"{doc_id}-rev",
                locator_version="citation-span-v1",
                locator_source_sha256=f"{doc_id}-locator",
                section_hierarchy=["Methods", section],
                source_backend="pymupdf",
            ),
        ],
    )


@pytest.mark.asyncio
async def test_structural_pointer_index_links_assets_and_evidence(tmp_path: Path):
    repo = _Repo(tmp_path, {"doc_a": _manifest("doc_a")})
    repo.markdown["doc_a"] = "Remimazolam reduced sedation time.\nMore details.\nFig.\n"
    repo.spans["doc_a"] = [
        EvidenceSpan.create(
            doc_id="doc_a",
            source_revision_id="doc_a-rev",
            span_kind="block",
            text="Remimazolam reduced sedation time.",
            section_hierarchy=["Methods", "Sedation"],
            line_start=0,
            line_end=1,
            char_start=0,
            char_end=34,
            markdown=repo.markdown["doc_a"],
            locator_source_sha256="doc_a-locator",
        )
    ]
    service = StructuralPointerService(
        repo,
        _Segmentation(
            {
                "doc_a": _segmentation(
                    "doc_a", "Remimazolam reduced sedation time.", "Sedation"
                )
            }
        ),
    )

    target, summary = await service.build_and_save_pointer_index("doc_a")

    records = [
        json.loads(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert summary["schema_version"] == SECTION_POINTER_SCHEMA_VERSION
    assert summary["metrics"]["pointer_count"] == 1
    assert records[0]["pointer_id"].startswith("ptr_")
    assert records[0]["breadcrumb"] == "Methods > Sedation"
    assert records[0]["line_start"] == 0
    assert records[0]["line_end"] == 3
    assert records[0]["char_start"] == 0
    assert records[0]["byte_start"] == 0
    assert records[0]["locator_status"] == "complete"
    assert records[0]["asset_ids"] == ["fig_1"]
    assert records[0]["evidence_span_ids"] == [repo.spans["doc_a"][0].span_id]


@pytest.mark.asyncio
async def test_structural_retrieve_materializes_section_preview(tmp_path: Path):
    repo = _Repo(tmp_path, {"doc_a": _manifest("doc_a")})
    repo.markdown["doc_a"] = "# Methods\nRemimazolam protocol\nOutcome data\n"
    service = StructuralPointerService(
        repo,
        _Segmentation(
            {"doc_a": _segmentation("doc_a", "Remimazolam protocol", "Protocol")}
        ),
    )

    payload = await service.retrieve("doc_a", "protocol", refresh=True)

    assert payload["result_count"] == 1
    assert payload["results"][0]["breadcrumb"] == "Methods > Protocol"
    assert "Remimazolam protocol" in payload["results"][0]["content_preview"]


@pytest.mark.asyncio
async def test_structural_retrieve_ignores_manifest_markdown_path_outside_doc_dir(
    tmp_path: Path,
) -> None:
    manifest = _manifest("doc_a")
    outside = tmp_path / "outside_secret.md"
    outside.write_text("SECRET-SENTINEL\n", encoding="utf-8")
    manifest.markdown_path = str(outside)
    repo = _Repo(tmp_path, {"doc_a": manifest})
    doc_dir = repo.get_doc_dir("doc_a")
    (doc_dir / "doc_a_full.md").write_text("Safe markdown preview\n", encoding="utf-8")
    service = StructuralPointerService(
        repo,
        _Segmentation(
            {"doc_a": _segmentation("doc_a", "Safe markdown preview", "Safe")}
        ),
    )

    payload = await service.retrieve("doc_a", "safe", refresh=True)

    preview = payload["results"][0]["content_preview"]
    assert "Safe markdown preview" in preview
    assert "SECRET-SENTINEL" not in preview


@pytest.mark.asyncio
async def test_structural_retrieve_rejects_manifest_json_as_markdown_path(
    tmp_path: Path,
) -> None:
    manifest = _manifest("doc_a")
    repo = _Repo(tmp_path, {"doc_a": manifest})
    doc_dir = repo.get_doc_dir("doc_a")
    (doc_dir / "doc_a_manifest.json").write_text("SECRET-SENTINEL\n", encoding="utf-8")
    manifest.markdown_path = str(doc_dir / "doc_a_manifest.json")
    repo.markdown["doc_a"] = "Safe fallback markdown\n"
    service = StructuralPointerService(
        repo,
        _Segmentation(
            {"doc_a": _segmentation("doc_a", "Safe fallback markdown", "Safe")}
        ),
    )

    payload = await service.retrieve("doc_a", "safe", refresh=True)

    preview = payload["results"][0]["content_preview"]
    assert "Safe fallback markdown" in preview
    assert "SECRET-SENTINEL" not in preview


@pytest.mark.asyncio
async def test_structural_pointer_rejects_stale_evidence_span_identity(
    tmp_path: Path,
) -> None:
    repo = _Repo(tmp_path, {"doc_a": _manifest("doc_a")})
    repo.markdown["doc_a"] = "Remimazolam reduced sedation time.\n"
    repo.spans["doc_a"] = [
        EvidenceSpan.create(
            doc_id="doc_a",
            source_revision_id="old-rev",
            span_kind="block",
            text="Remimazolam reduced sedation time.",
            section_hierarchy=["Methods", "Sedation"],
            line_start=0,
            line_end=1,
            markdown=repo.markdown["doc_a"],
            locator_source_sha256="old-locator",
        )
    ]
    service = StructuralPointerService(
        repo,
        _Segmentation(
            {
                "doc_a": _segmentation(
                    "doc_a", "Remimazolam reduced sedation time.", "Sedation"
                )
            }
        ),
    )

    target, _summary = await service.build_and_save_pointer_index("doc_a")

    record = json.loads(target.read_text(encoding="utf-8").splitlines()[0])
    assert record["evidence_span_ids"] == []


@pytest.mark.asyncio
async def test_structural_pointer_rejects_missing_current_locator_identity(
    tmp_path: Path,
) -> None:
    repo = _Repo(tmp_path, {"doc_a": _manifest("doc_a")})
    repo.markdown["doc_a"] = "Remimazolam reduced sedation time.\n"
    repo.spans["doc_a"] = [
        EvidenceSpan.create(
            doc_id="doc_a",
            source_revision_id="doc_a-rev",
            span_kind="block",
            text="Remimazolam reduced sedation time.",
            section_hierarchy=["Methods", "Sedation"],
            line_start=0,
            line_end=1,
            markdown=repo.markdown["doc_a"],
            locator_source_sha256="doc_a-locator",
        )
    ]
    segmentation = _segmentation(
        "doc_a", "Remimazolam reduced sedation time.", "Sedation"
    )
    segmentation.source_revision_id = ""
    segmentation.locator_source_sha256 = ""
    for segment in segmentation.segments:
        segment.source_revision_id = ""
        segment.locator_source_sha256 = ""
    service = StructuralPointerService(repo, _Segmentation({"doc_a": segmentation}))

    target, _summary = await service.build_and_save_pointer_index("doc_a")

    record = json.loads(target.read_text(encoding="utf-8").splitlines()[0])
    assert record["evidence_span_ids"] == []


@pytest.mark.asyncio
async def test_structural_retrieve_reports_stale_pointer_index_without_writing(
    tmp_path: Path,
) -> None:
    repo = _Repo(tmp_path, {"doc_a": _manifest("doc_a")})
    initial = _segmentation("doc_a", "Alpha sedation protocol", "Old")
    segmentations = {"doc_a": initial}
    service = StructuralPointerService(repo, _Segmentation(segmentations))
    await service.build_and_save_pointer_index("doc_a")
    replacement = _segmentation("doc_a", "Beta discharge process", "New")
    replacement.source_revision_id = "doc_a-rev-2"
    replacement.locator_source_sha256 = "doc_a-locator-2"
    for segment in replacement.segments:
        segment.source_revision_id = "doc_a-rev-2"
        segment.locator_source_sha256 = "doc_a-locator-2"
    segmentations["doc_a"] = replacement

    payload = await service.retrieve("doc_a", "Beta", refresh=False)

    assert payload["status"] == "needs_pointer_index"
    assert payload["result_count"] == 0
    assert payload["blockers"] == ["missing_or_stale_section_pointer_index"]


@pytest.mark.asyncio
async def test_structural_compare_rebuilds_stale_pointer_index_when_writing(
    tmp_path: Path,
) -> None:
    repo = _Repo(tmp_path, {"doc_a": _manifest("doc_a"), "doc_b": _manifest("doc_b")})
    segmentations = {
        "doc_a": _segmentation("doc_a", "Alpha sedation protocol", "Old"),
        "doc_b": _segmentation("doc_b", "Beta discharge process", "Other"),
    }
    service = StructuralPointerService(repo, _Segmentation(segmentations))
    await service.build_and_save_pointer_index("doc_a")
    replacement = _segmentation("doc_a", "Beta sedation process", "New")
    replacement.source_revision_id = "doc_a-rev-2"
    replacement.locator_source_sha256 = "doc_a-locator-2"
    for segment in replacement.segments:
        segment.source_revision_id = "doc_a-rev-2"
        segment.locator_source_sha256 = "doc_a-locator-2"
    segmentations["doc_a"] = replacement

    _target, bundle = await service.build_and_save_comparison_bundle(
        "doc_a",
        "doc_b",
        criteria="Beta",
    )

    assert bundle["pairs"][0]["left_pointer"]["breadcrumb"] == "Methods > New"


@pytest.mark.asyncio
async def test_structural_pointer_large_section_preview_is_bounded(tmp_path: Path):
    repo = _Repo(tmp_path, {"doc_a": _manifest("doc_a")})
    service = StructuralPointerService(
        repo,
        _Segmentation({"doc_a": _segmentation("doc_a", "A" * 50_000, "Huge")}),
    )

    target, _summary = await service.build_and_save_pointer_index("doc_a")

    record = json.loads(target.read_text(encoding="utf-8").splitlines()[0])
    assert len(record["text_preview"]) < 1400
    assert record["content_sha256"]


@pytest.mark.asyncio
async def test_structural_pointer_load_skips_oversized_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _Repo(tmp_path, {"doc_a": _manifest("doc_a")})
    doc_dir = repo.get_doc_dir("doc_a")
    repo.manifests["doc_a"].manifest_path = str(doc_dir / "doc_a_manifest.json")
    (doc_dir / "doc_a_manifest.json").write_text("{}", encoding="utf-8")
    (doc_dir / "section_pointer_index.jsonl").write_text(
        '{"schema_version":"section-pointer-index-v1"}\n' * 20,
        encoding="utf-8",
    )
    monkeypatch.setenv("ASSET_AWARE_STRUCTURAL_POINTER_INDEX_MAX_BYTES", "16")
    service = StructuralPointerService(
        repo,
        _Segmentation(
            {"doc_a": _segmentation("doc_a", "Remimazolam protocol", "Protocol")}
        ),
    )

    payload = await service.retrieve("doc_a", "protocol", refresh=False)

    assert payload["status"] == "needs_pointer_index"
    assert payload["result_count"] == 0


@pytest.mark.asyncio
async def test_structural_retrieve_supports_cjk_query(tmp_path: Path):
    repo = _Repo(tmp_path, {"doc_a": _manifest("doc_a")})
    repo.markdown["doc_a"] = "鎮靜方案與劑量\n"
    service = StructuralPointerService(
        repo,
        _Segmentation({"doc_a": _segmentation("doc_a", "鎮靜方案與劑量", "鎮靜")}),
    )

    payload = await service.retrieve("doc_a", "鎮靜", refresh=True)

    assert payload["result_count"] == 1
    assert payload["results"][0]["breadcrumb"] == "Methods > 鎮靜"


@pytest.mark.asyncio
async def test_structural_comparison_bundle_tracks_unmatched_pairs(tmp_path: Path):
    repo = _Repo(tmp_path, {"doc_a": _manifest("doc_a"), "doc_b": _manifest("doc_b")})
    repo.markdown["doc_a"] = "Alpha sedation protocol\n"
    repo.markdown["doc_b"] = "Different discharge process\n"
    service = StructuralPointerService(
        repo,
        _Segmentation(
            {
                "doc_a": _segmentation("doc_a", "Alpha sedation protocol", "Sedation"),
                "doc_b": _segmentation(
                    "doc_b", "Different discharge process", "Discharge"
                ),
            }
        ),
    )

    target, bundle = await service.build_and_save_comparison_bundle(
        "doc_a",
        "doc_b",
        criteria="sedation protocol",
        refresh=True,
    )

    persisted = json.loads(target.read_text(encoding="utf-8"))
    assert bundle["schema_version"] == DOCUMENT_COMPARISON_SCHEMA_VERSION
    assert persisted["summary"]["selected_pairs"] == 1
    assert persisted["pairs"][0]["left_pointer"]["doc_id"] == "doc_a"
    assert persisted["pairs"][0]["status"] in {"candidate", "unmatched"}
    assert persisted["pairs"][0]["rating"] in {
        "needs_review",
        "missing_counterpart",
    }


@pytest.mark.asyncio
async def test_structural_comparison_requires_criteria(tmp_path: Path):
    repo = _Repo(tmp_path, {"doc_a": _manifest("doc_a"), "doc_b": _manifest("doc_b")})
    service = StructuralPointerService(
        repo,
        _Segmentation(
            {
                "doc_a": _segmentation("doc_a", "Alpha", "A"),
                "doc_b": _segmentation("doc_b", "Beta", "B"),
            }
        ),
    )

    with pytest.raises(ValueError, match="criteria"):
        await service.build_and_save_comparison_bundle(
            "doc_a",
            "doc_b",
            criteria="",
        )
