"""Citation-ready evidence span models and builders."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

LOCATOR_VERSION = "citation-span-v1"
CRAAP_VERSION = "craap-v1"
SpanKind = Literal["block", "sentence", "line"]
CraapStatus = Literal["unassessed", "partial", "supported", "needs_review"]


class CraapDimension(BaseModel):
    """One conservative CRAAP quality dimension for a citation span."""

    status: CraapStatus = Field(
        "unassessed",
        description="Assessment state; partial means the system has evidence but no final judgement.",
    )
    score: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Optional normalized score. Empty avoids false precision.",
    )
    rationale: str = Field("", description="Human-readable assessment rationale")
    evidence: list[str] = Field(default_factory=list)


class CraapAssessment(BaseModel):
    """CRAAP assessment scaffold carried with citation-ready spans."""

    assessment_version: str = Field(CRAAP_VERSION)
    currency: CraapDimension = Field(default_factory=CraapDimension)
    relevance: CraapDimension = Field(default_factory=CraapDimension)
    authority: CraapDimension = Field(default_factory=CraapDimension)
    accuracy: CraapDimension = Field(default_factory=CraapDimension)
    purpose: CraapDimension = Field(default_factory=CraapDimension)


class EvidenceSpan(BaseModel):
    """A verifiable text span that can be cited at sentence/line granularity."""

    span_id: str = Field(..., description="Stable evidence span identifier")
    doc_id: str = Field(..., description="Document identifier")
    source_revision_id: str = Field(
        ..., description="Hash of the canonical markdown used for locator offsets"
    )
    locator_version: str = Field(
        LOCATOR_VERSION, description="Version of the locator/indexing algorithm"
    )
    span_kind: SpanKind = Field(..., description="Granularity of this span")
    block_id: str = Field("", description="Source layout block identifier")
    asset_id: str = Field("", description="Linked asset identifier when available")
    source_type: str = Field("text", description="text/table/figure/section")
    page: int | None = Field(None, description="1-indexed source page")
    bbox: list[float] = Field(default_factory=list, description="Source bbox")
    section_hierarchy: list[str] = Field(default_factory=list)
    line_start: int | None = Field(None, description="0-based start line")
    line_end: int | None = Field(None, description="0-based exclusive end line")
    char_start: int | None = Field(None, description="0-based character start")
    char_end: int | None = Field(None, description="0-based exclusive character end")
    byte_start: int | None = Field(None, description="UTF-8 byte start")
    byte_end: int | None = Field(None, description="UTF-8 byte end")
    text: str = Field("", description="Exact canonical text for this span")
    text_sha256: str = Field("", description="Hash of exact text")
    normalized_text_sha256: str = Field("", description="Hash of normalized text")
    context_before: str = Field("", description="Short context before the span")
    context_after: str = Field("", description="Short context after the span")
    extraction_backend: str = Field("", description="marker/pymupdf/etc.")
    craap: CraapAssessment = Field(default_factory=CraapAssessment)

    @classmethod
    def create(
        cls,
        *,
        doc_id: str,
        source_revision_id: str,
        span_kind: SpanKind,
        text: str,
        block_id: str = "",
        asset_id: str = "",
        source_type: str = "text",
        page: int | None = None,
        bbox: list[float] | None = None,
        section_hierarchy: list[str] | None = None,
        line_start: int | None = None,
        line_end: int | None = None,
        char_start: int | None = None,
        char_end: int | None = None,
        markdown: str = "",
        extraction_backend: str = "",
    ) -> EvidenceSpan:
        """Create a span with stable hashes and context fields."""
        exact_hash = _sha256(text)
        normalized_hash = _sha256(_normalize_text(text))
        seed = "|".join(
            [
                doc_id,
                source_revision_id[:16],
                block_id,
                span_kind,
                str(char_start),
                str(char_end),
                exact_hash[:16],
            ]
        )
        byte_start = byte_end = None
        if char_start is not None and char_end is not None and markdown:
            byte_start = len(markdown[:char_start].encode("utf-8"))
            byte_end = len(markdown[:char_end].encode("utf-8"))

        return cls(
            span_id=f"spn_{_sha256(seed)[:16]}",
            doc_id=doc_id,
            source_revision_id=source_revision_id,
            span_kind=span_kind,
            block_id=block_id,
            asset_id=asset_id,
            source_type=source_type,
            page=page,
            bbox=bbox or [],
            section_hierarchy=section_hierarchy or [],
            line_start=line_start,
            line_end=line_end,
            char_start=char_start,
            char_end=char_end,
            byte_start=byte_start,
            byte_end=byte_end,
            text=text,
            text_sha256=exact_hash,
            normalized_text_sha256=normalized_hash,
            context_before=_context(markdown, char_start, before=True),
            context_after=_context(markdown, char_end, before=False),
            extraction_backend=extraction_backend,
            craap=build_initial_craap_assessment(
                source_type=source_type,
                extraction_backend=extraction_backend,
                has_exact_locator=char_start is not None and char_end is not None,
            ),
        )


def build_evidence_spans(
    *,
    doc_id: str,
    markdown: str,
    blocks: list[dict[str, Any]],
    source_backend: str,
) -> list[EvidenceSpan]:
    """Build citation-ready spans from canonical markdown and block metadata."""
    source_revision_id = _sha256(markdown)
    line_offsets, line_count = _line_offsets(markdown)
    spans: list[EvidenceSpan] = []
    seen: set[str] = set()

    for block in blocks:
        metadata = block.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        line_start = metadata.get("line_start")
        line_end = metadata.get("line_end")
        if not isinstance(line_start, int) or not isinstance(line_end, int):
            line_start = line_end = None

        char_start: int | None = None
        char_end: int | None = None
        text = str(block.get("text") or "")
        if (
            line_start is not None
            and line_end is not None
            and 0 <= line_start <= line_end <= line_count
        ):
            raw_start = line_offsets[line_start]
            raw_end = line_offsets[line_end]
            raw_text = markdown[raw_start:raw_end]
            trimmed_start, trimmed_end = _trimmed_range(raw_text)
            char_start = raw_start + trimmed_start
            char_end = raw_start + trimmed_end
            text = markdown[char_start:char_end]

        if not text.strip():
            continue

        block_id = str(block.get("block_id") or "")
        source_type = _source_type(block)
        page = _coerce_page(block.get("page"))
        bbox = _coerce_bbox(block.get("bbox"))
        section_hierarchy = _section_hierarchy(block.get("section_hierarchy"))
        _append_unique(
            spans,
            seen,
            EvidenceSpan.create(
                doc_id=doc_id,
                source_revision_id=source_revision_id,
                span_kind="block",
                text=text,
                block_id=block_id,
                source_type=source_type,
                page=page,
                bbox=bbox,
                section_hierarchy=section_hierarchy,
                line_start=line_start,
                line_end=line_end,
                char_start=char_start,
                char_end=char_end,
                markdown=markdown,
                extraction_backend=source_backend,
            ),
        )

        for kind, unit_text, unit_start, unit_end in _iter_child_units(
            text,
            char_start,
            str(block.get("block_type") or ""),
        ):
            _append_unique(
                spans,
                seen,
                EvidenceSpan.create(
                    doc_id=doc_id,
                    source_revision_id=source_revision_id,
                    span_kind=kind,
                    text=unit_text,
                    block_id=block_id,
                    source_type=source_type,
                    page=page,
                    bbox=bbox,
                    section_hierarchy=section_hierarchy,
                    line_start=line_start,
                    line_end=line_end,
                    char_start=unit_start,
                    char_end=unit_end,
                    markdown=markdown,
                    extraction_backend=source_backend,
                ),
            )

    return spans


def build_initial_craap_assessment(
    *,
    source_type: str,
    extraction_backend: str,
    has_exact_locator: bool,
) -> CraapAssessment:
    """Build a conservative CRAAP scaffold without inventing source quality."""
    authority_evidence = [f"source_type={source_type}"]
    if extraction_backend:
        authority_evidence.append(f"extraction_backend={extraction_backend}")

    accuracy_evidence = ["exact_text_sha256 recorded"]
    if has_exact_locator:
        accuracy_evidence.append("canonical char/byte locator recorded")

    return CraapAssessment(
        currency=CraapDimension(
            status="unassessed",
            rationale=(
                "Publication or source revision date is not yet captured; "
                "assess freshness before relying on time-sensitive claims."
            ),
        ),
        relevance=CraapDimension(
            status="unassessed",
            rationale=(
                "Relevance is query-dependent and should be assessed against the "
                "specific citation use case."
            ),
        ),
        authority=CraapDimension(
            status="partial",
            rationale=(
                "Extraction provenance is recorded, but author/publisher authority "
                "metadata is not yet captured."
            ),
            evidence=authority_evidence,
        ),
        accuracy=CraapDimension(
            status="partial",
            rationale=(
                "The quoted text can be integrity-checked against hashes and "
                "locators; factual correctness still requires source review."
            ),
            evidence=accuracy_evidence,
        ),
        purpose=CraapDimension(
            status="unassessed",
            rationale=(
                "The source intent, audience, and bias are not inferable from the "
                "span alone."
            ),
        ),
    )


def _append_unique(
    spans: list[EvidenceSpan], seen: set[str], span: EvidenceSpan
) -> None:
    if span.span_id in seen:
        return
    seen.add(span.span_id)
    spans.append(span)


def _iter_child_units(
    text: str,
    absolute_start: int | None,
    block_type: str,
) -> list[tuple[SpanKind, str, int | None, int | None]]:
    if block_type.lower() == "table" or "|" in text:
        return list(_iter_line_units(text, absolute_start))
    return list(_iter_sentence_units(text, absolute_start))


def _iter_line_units(
    text: str,
    absolute_start: int | None,
) -> list[tuple[SpanKind, str, int | None, int | None]]:
    units: list[tuple[SpanKind, str, int | None, int | None]] = []
    offset = 0
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.strip()
        if line and not set(line) <= {"|", "-", ":", " "}:
            start_delta = len(raw_line) - len(raw_line.lstrip())
            end_delta = len(raw_line.rstrip())
            start = (
                None
                if absolute_start is None
                else absolute_start + offset + start_delta
            )
            end = (
                None if absolute_start is None else absolute_start + offset + end_delta
            )
            units.append(("line", line, start, end))
        offset += len(raw_line)
    return units


def _iter_sentence_units(
    text: str,
    absolute_start: int | None,
) -> list[tuple[SpanKind, str, int | None, int | None]]:
    units: list[tuple[SpanKind, str, int | None, int | None]] = []
    sentence_re = re.compile(r"[^.!?。！？\n]+(?:[.!?。！？]+|$)")
    for match in sentence_re.finditer(text):
        sentence = match.group()
        stripped = sentence.strip()
        if len(stripped) < 8:
            continue
        start_delta = match.start() + len(sentence) - len(sentence.lstrip())
        end_delta = match.start() + len(sentence.rstrip())
        start = None if absolute_start is None else absolute_start + start_delta
        end = None if absolute_start is None else absolute_start + end_delta
        units.append(("sentence", stripped, start, end))
    return units


def _line_offsets(markdown: str) -> tuple[list[int], int]:
    offsets: list[int] = []
    position = 0
    for line in markdown.splitlines(keepends=True):
        offsets.append(position)
        position += len(line)
    offsets.append(len(markdown))
    return offsets, len(offsets) - 1


def _trimmed_range(text: str) -> tuple[int, int]:
    start = len(text) - len(text.lstrip())
    end = len(text.rstrip())
    return (start, max(start, end))


def _source_type(block: dict[str, Any]) -> str:
    block_type = str(block.get("block_type") or "").strip().lower()
    if "table" in block_type:
        return "table"
    if block_type in {"figure", "picture", "image"}:
        return "figure"
    if "section" in block_type or block_type == "title":
        return "section"
    return "text"


def _section_hierarchy(value: object) -> list[str]:
    if not isinstance(value, dict):
        return []
    return [
        str(title)
        for _, title in sorted(value.items(), key=lambda item: str(item[0]))
        if str(title).strip()
    ]


def _coerce_bbox(value: object) -> list[float]:
    if not isinstance(value, list) or len(value) != 4:
        return []
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError):
        return []


def _coerce_page(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        page = value
    elif isinstance(value, float):
        page = int(value)
    elif isinstance(value, str):
        try:
            page = int(value)
        except ValueError:
            return None
    else:
        return None
    return page if page > 0 else None


def _context(markdown: str, offset: int | None, *, before: bool) -> str:
    if not markdown or offset is None:
        return ""
    if before:
        return markdown[max(0, offset - 120) : offset]
    return markdown[offset : min(len(markdown), offset + 120)]


def _normalize_text(text: str) -> str:
    return " ".join(text.split()).strip().lower()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
