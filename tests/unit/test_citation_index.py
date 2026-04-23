from __future__ import annotations

import hashlib

from src.domain.citation import build_evidence_spans
from src.domain.value_objects import AssetRef


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
        quote="Beta finding needs follow-up.",
        craap={"assessment_version": "craap-v1", "accuracy": {"status": "partial"}},
    )

    data = ref.to_dict()
    restored = AssetRef.from_dict(data)

    assert data["source_type"] == "span"
    assert data["quote_sha256"] == ref.quote_sha256
    assert data["craap"]["assessment_version"] == "craap-v1"
    assert restored == ref
    assert "find_evidence_spans" in restored.access_path
