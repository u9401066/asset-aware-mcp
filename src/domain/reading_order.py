"""Domain policy for explicit document reading order assignment."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.segmentation import DocumentSegment

TYPE_OFFSETS = {
    "Title": -0.30,
    "Section header": -0.20,
    "Text": 0.00,
    "List item": 0.02,
    "Formula": 0.04,
    "Picture": 0.05,
    "Table": 0.06,
    "Caption": 0.10,
    "Footnote": 0.90,
    "Page footer": 1.20,
    "Page header": -0.40,
}

NON_TEXT_TYPES = {"Picture", "Table", "Formula"}
TEXTUAL_TYPES = {"Title", "Section header", "Text", "List item", "Caption"}


@dataclass(frozen=True)
class ReadingOrderScore:
    segment_id: str
    page_number: int
    source_order: float
    adjusted_order: float
    reason: str


class ReadingOrderPolicy:
    """Assign a stable, explainable reading order to document segments."""

    version = "explicit-reading-order-v1"

    def assign(self, segments: list[DocumentSegment]) -> list[DocumentSegment]:
        ordered_segments: list[DocumentSegment] = []
        page_numbers = sorted({segment.page_number for segment in segments})

        for page_number in page_numbers:
            page_segments = [
                segment for segment in segments if segment.page_number == page_number
            ]
            page_scores = self._score_page_segments(page_segments)
            sorted_pairs = sorted(
                zip(page_segments, page_scores, strict=False),
                key=lambda item: (
                    item[1].adjusted_order,
                    self._fallback_top(item[0]),
                    self._fallback_left(item[0]),
                    item[0].segment_id,
                ),
            )

            for reading_order, (segment, score) in enumerate(sorted_pairs, start=1):
                metadata = dict(segment.metadata)
                metadata.update(
                    {
                        "reading_order_policy": self.version,
                        "reading_order_reason": score.reason,
                        "source_order": score.source_order,
                        "adjusted_order": round(score.adjusted_order, 4),
                    }
                )
                ordered_segments.append(
                    segment.model_copy(
                        update={
                            "reading_order": reading_order,
                            "metadata": metadata,
                        }
                    )
                )

        return ordered_segments

    def _score_page_segments(
        self, segments: list[DocumentSegment]
    ) -> list[ReadingOrderScore]:
        base_orders = {
            segment.segment_id: self._base_order(segment) for segment in segments
        }
        text_like = [
            segment for segment in segments if segment.segment_type in TEXTUAL_TYPES
        ]
        anchorable = [
            segment for segment in segments if segment.segment_type in NON_TEXT_TYPES
        ]

        scores: list[ReadingOrderScore] = []
        for segment in segments:
            base_order = base_orders[segment.segment_id]
            adjusted_order = base_order + TYPE_OFFSETS.get(segment.segment_type, 0.0)
            reason = "source-order"

            if segment.segment_type == "Caption":
                anchor = self._nearest_segment(segment, anchorable)
                if anchor is not None:
                    anchor_order = base_orders[anchor.segment_id]
                    adjusted_order = anchor_order + self._caption_offset(
                        anchor, segment
                    )
                    reason = f"caption-near-{anchor.segment_type.lower()}:{anchor.segment_id}"
                else:
                    reason = "caption-type-offset"
            elif segment.segment_type in NON_TEXT_TYPES:
                anchor = self._nearest_segment(segment, text_like)
                if anchor is not None:
                    text_order = base_orders[anchor.segment_id]
                    adjusted_order = min(adjusted_order, text_order + 0.05)
                    reason = f"nontext-near-text:{anchor.segment_id}"
                else:
                    reason = "nontext-type-offset"
            elif segment.segment_type in {"Footnote", "Page footer"}:
                adjusted_order = max(
                    adjusted_order,
                    self._bottom_bias(segment) + TYPE_OFFSETS[segment.segment_type],
                )
                reason = "bottom-of-page"
            elif segment.segment_type in {"Title", "Section header", "Page header"}:
                reason = "header-priority"

            scores.append(
                ReadingOrderScore(
                    segment_id=segment.segment_id,
                    page_number=segment.page_number,
                    source_order=base_order,
                    adjusted_order=adjusted_order,
                    reason=reason,
                )
            )

        return scores

    def _base_order(self, segment: DocumentSegment) -> float:
        raw_source_order = segment.metadata.get("source_order")
        if isinstance(raw_source_order, (int, float)):
            return float(raw_source_order)

        token_start = segment.metadata.get("token_order_start")
        token_end = segment.metadata.get("token_order_end")
        if isinstance(token_start, (int, float)) and isinstance(
            token_end, (int, float)
        ):
            return (float(token_start) + float(token_end)) / 2.0

        top = self._fallback_top(segment)
        left = self._fallback_left(segment)
        return (top * 1000.0) + left

    @staticmethod
    def _caption_offset(anchor: DocumentSegment, caption: DocumentSegment) -> float:
        anchor_center_y = (anchor.top or 0.0) + ((anchor.height or 0.0) / 2.0)
        caption_center_y = (caption.top or 0.0) + ((caption.height or 0.0) / 2.0)
        return 0.08 if caption_center_y >= anchor_center_y else -0.08

    def _nearest_segment(
        self,
        segment: DocumentSegment,
        candidates: list[DocumentSegment],
    ) -> DocumentSegment | None:
        if not candidates:
            return None

        center_x, center_y = self._center(segment)
        best_segment: DocumentSegment | None = None
        best_score = inf

        for candidate in candidates:
            if candidate.segment_id == segment.segment_id:
                continue
            candidate_x, candidate_y = self._center(candidate)
            vertical = abs(candidate_y - center_y)
            horizontal = abs(candidate_x - center_x)
            distance = vertical + (horizontal * 0.35)
            if distance < best_score:
                best_score = distance
                best_segment = candidate

        return best_segment

    @staticmethod
    def _center(segment: DocumentSegment) -> tuple[float, float]:
        left = segment.left or 0.0
        top = segment.top or 0.0
        width = segment.width or 0.0
        height = segment.height or 0.0
        return (left + (width / 2.0), top + (height / 2.0))

    @staticmethod
    def _fallback_top(segment: DocumentSegment) -> float:
        return float(segment.top or 0.0)

    @staticmethod
    def _fallback_left(segment: DocumentSegment) -> float:
        return float(segment.left or 0.0)

    @staticmethod
    def _bottom_bias(segment: DocumentSegment) -> float:
        top = segment.top or 0.0
        height = segment.height or 0.0
        return top + height
