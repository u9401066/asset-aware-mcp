from __future__ import annotations

import hashlib
from unittest.mock import MagicMock

from src.application.citation_index_service import CitationIndexService
from src.domain.citation import build_evidence_spans
from src.domain.entities import DocumentAssets, DocumentManifest
from src.domain.value_objects import AssetRef
from src.presentation.tools.citation_support import asset_ref_from_span


def test_build_evidence_spans_records_sentence_offsets_and_hashes() -> None:
    markdown = (
        "<!-- Page 1 -->\n"
        "# Results\n\n"
        "Alpha finding is clinically important. Beta finding needs follow-up.\n"
    )
    block = {
        "block_id": "blk_1",
        "block_type": "Text",
        "page": 1,
        "text": "fallback should not be used",
        "bbox": [1, 2, 3, 4],
        "section_hierarchy": {"1": "Results"},
        "metadata": {"line_start": 3, "line_end": 4},
    }

    spans = build_evidence_spans(
        doc_id="doc_results_abc123",
        markdown=markdown,
        blocks=[block],
        source_backend="marker",
    )

    sentence = next(
        span for span in spans if span.span_kind == "sentence" and "Beta" in span.text
    )
    assert sentence.text == "Beta finding needs follow-up."
    assert sentence.char_start is not None
    assert sentence.char_end is not None
    assert markdown[sentence.char_start : sentence.char_end] == sentence.text
    assert sentence.byte_start == len(markdown[: sentence.char_start].encode("utf-8"))
    assert (
        sentence.text_sha256
        == hashlib.sha256(sentence.text.encode("utf-8")).hexdigest()
    )
    assert sentence.bbox == [1.0, 2.0, 3.0, 4.0]
    assert sentence.section_hierarchy == ["Results"]
    assert sentence.craap.assessment_version == "craap-v1"
    assert sentence.craap.currency.status == "unassessed"
    assert sentence.craap.accuracy.status == "partial"
    assert "canonical char/byte locator recorded" in sentence.craap.accuracy.evidence


def test_span_asset_ref_round_trips_exact_locator_metadata() -> None:
    ref = AssetRef(
        source_type="span",
        doc_id="doc_results_abc123",
        span_id="spn_123",
        block_id="blk_1",
        page=1,
        line_range=(3, 4),
        char_range=(42, 71),
        byte_range=(42, 71),
        bbox=(1.0, 2.0, 3.0, 4.0),
        source_revision_id="rev",
        locator_version="citation-span-v1",
        locator_source_sha256="blocks-hash",
        quote="Beta finding needs follow-up.",
        craap={"assessment_version": "craap-v1", "accuracy": {"status": "partial"}},
    )

    data = ref.to_dict()
    restored = AssetRef.from_dict(data)

    assert data["source_type"] == "span"
    assert data["quote_sha256"] == ref.quote_sha256
    assert data["locator_source_sha256"] == "blocks-hash"
    assert data["craap"]["assessment_version"] == "craap-v1"
    assert restored == ref
    assert "find_evidence_spans" in restored.access_path


def test_asset_ref_from_evidence_span_preserves_locator_source_hash() -> None:
    spans = build_evidence_spans(
        doc_id="doc_results_abc123",
        markdown="Alpha finding.\n",
        blocks=[
            {
                "block_id": "blk_1",
                "block_type": "Text",
                "page": 1,
                "text": "Alpha finding.",
                "metadata": {"line_start": 0, "line_end": 1},
            }
        ],
        source_backend="marker",
    )
    span = next(item for item in spans if item.span_kind == "sentence")

    ref_data = asset_ref_from_span(span)
    restored = AssetRef.from_dict(ref_data).to_dict()

    assert restored["locator_source_sha256"] == span.locator_source_sha256


def test_load_or_rebuild_attributes_spans_to_the_real_source_engine() -> None:
    """Regression: rebuilding a citation index must not hardcode "unknown"

    when the manifest already records which engine produced the document.
    """
    manifest = DocumentManifest(
        doc_id="doc_mineru",
        filename="paper.pdf",
        title="Paper",
        page_count=1,
        markdown_path="workspace/doc_mineru_full.md",
        source_engine="mineru:pipeline",
        assets=DocumentAssets(figures=[], tables=[], sections=[]),
    )
    blocks = [
        {
            "block_id": "blk_1",
            "block_type": "Text",
            "page": 1,
            "text": "Alpha finding is clinically important.",
            "metadata": {"line_start": 0, "line_end": 1},
        }
    ]

    repository = MagicMock()
    repository.load_citation_index.return_value = []
    repository.load_markdown.return_value = "Alpha finding is clinically important.\n"
    repository.load_blocks.return_value = blocks
    repository.load_manifest.return_value = manifest

    spans = CitationIndexService(repository).load_or_rebuild("doc_mineru")

    assert spans
    assert all(span.extraction_backend == "mineru:pipeline" for span in spans)
    repository.save_citation_index.assert_called_once()


def test_load_or_rebuild_falls_back_to_unknown_without_a_manifest() -> None:
    """A missing/mock-only manifest must degrade to "unknown", not leak a

    non-string (e.g. MagicMock) value into the pydantic-typed
    EvidenceSpan.extraction_backend field.
    """
    repository = MagicMock()
    repository.load_citation_index.return_value = []
    repository.load_markdown.return_value = "Alpha finding is clinically important.\n"
    repository.load_blocks.return_value = [
        {
            "block_id": "blk_1",
            "block_type": "Text",
            "page": 1,
            "text": "Alpha finding is clinically important.",
            "metadata": {"line_start": 0, "line_end": 1},
        }
    ]
    repository.load_manifest.return_value = None

    spans = CitationIndexService(repository).load_or_rebuild("doc_unknown")

    assert spans
    assert all(span.extraction_backend == "unknown" for span in spans)
