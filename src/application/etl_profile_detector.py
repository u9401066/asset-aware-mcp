"""Heuristic ETL profile auto-detection."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def detect_profile_from_text(
    text: str,
    *,
    file_name: str = "",
    layout_hints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Recommend a built-in ETL profile from text and lightweight layout hints.

    The detector is intentionally conservative: it provides reasons and
    confidence, but does not claim the profile is authoritative.
    """
    normalized = text.lower()
    file_lower = Path(file_name).name.lower()
    hints = layout_hints or {}
    scores: dict[str, float] = {
        "default": 0.20,
        "arxiv": 0.0,
        "ieee": 0.0,
        "nature": 0.0,
        "elsevier": 0.0,
    }
    reasons: list[str] = []

    def add(profile: str, amount: float, reason: str) -> None:
        scores[profile] += amount
        reasons.append(f"{profile}: {reason}")

    if "arxiv:" in normalized or "arxiv" in file_lower:
        add("arxiv", 0.45, "arXiv identifier or filename marker")
    if re.search(r"\b(?:[ivx]{1,6})\.\s+[A-Z][A-Za-z]", text):
        add("ieee", 0.35, "Roman numeral section heading")
    if "ieee" in normalized or "transactions on" in normalized:
        add("ieee", 0.40, "IEEE venue marker")
    if "scientific reports" in normalized or re.search(r"\bnature\b", normalized):
        add("nature", 0.45, "Nature/Scientific Reports marker")
    if "elsevier" in normalized or "sciencedirect" in normalized:
        add("elsevier", 0.45, "Elsevier/ScienceDirect marker")
    if re.search(r"\bhighlights\b", normalized) and "abstract" in normalized:
        add("elsevier", 0.20, "Elsevier-style highlights section")
    if re.search(r"\b\d+\.\s+introduction\b", normalized):
        add("arxiv", 0.15, "numbered Introduction heading")
        add("elsevier", 0.10, "numbered Introduction heading")
    if bool(hints.get("two_column")):
        add("arxiv", 0.15, "two-column layout hint")
        add("ieee", 0.15, "two-column layout hint")
    if bool(hints.get("has_pdf_toc")):
        add("nature", 0.10, "PDF TOC hint")
        add("elsevier", 0.10, "PDF TOC hint")

    recommended = max(scores, key=lambda name: scores[name])
    confidence = min(0.95, max(scores[recommended], 0.05))
    candidates = [
        {"name": name, "score": round(score, 3)}
        for name, score in sorted(
            scores.items(), key=lambda item: item[1], reverse=True
        )
    ]
    if not reasons:
        reasons.append("default: no strong journal/layout markers detected")

    return {
        "recommended_profile": recommended,
        "confidence": round(confidence, 3),
        "candidates": candidates,
        "reasons": reasons,
    }


def sample_pdf_text(
    pdf_path: str,
    *,
    sample_pages: int = 3,
) -> tuple[str, dict[str, Any]]:
    """Extract a small text/layout sample from a PDF using PyMuPDF."""
    try:
        import fitz  # type: ignore[import-untyped]
    except Exception as e:  # pragma: no cover - depends on optional runtime import
        raise RuntimeError(f"PyMuPDF is required for PDF profile detection: {e}") from e

    doc = fitz.open(pdf_path)
    text_parts: list[str] = []
    two_column_votes = 0
    pages_to_read = min(max(sample_pages, 1), len(doc))
    for page_index in range(pages_to_read):
        page = doc[page_index]
        text_parts.append(page.get_text("text"))
        blocks = page.get_text("blocks")
        width = float(page.rect.width or 1)
        left = right = 0
        for block in blocks:
            if len(block) < 5:
                continue
            x0, _y0, x1, _y1, block_text = block[:5]
            if not str(block_text).strip():
                continue
            center = (float(x0) + float(x1)) / 2
            if center < width * 0.45:
                left += 1
            elif center > width * 0.55:
                right += 1
        if left >= 3 and right >= 3:
            two_column_votes += 1
    doc.close()
    return "\n".join(text_parts), {
        "sample_pages": pages_to_read,
        "two_column": two_column_votes >= max(1, pages_to_read // 2),
    }
