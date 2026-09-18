"""Bind citation display to evidence without changing its canonical reference."""

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.citation_format import CitationFormatContract, CitationMetadata


def citation_markdown(value: str) -> str:
    """Render citation text without introducing note headings, links or HTML."""
    text = " ".join(value.splitlines())
    text = html.escape(text, quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!|~-])", r"\\\1", text)


def render_citation(
    contract: CitationFormatContract,
    metadata: CitationMetadata,
    *,
    source_id: str,
    title: str,
    locator: dict[str, Any],
    asset_id: str = "",
    span_id: str = "",
    citation_key: str = "",
) -> dict[str, str]:
    """Authoritative locator values never come from caller bibliographic metadata."""
    page = locator.get("page")
    section = " / ".join(str(x) for x in locator.get("section_hierarchy", []))
    location: list[str] = []
    if page is not None:
        location.append(f"p. {page}")
    if section:
        location.append(section)
    sheet, cell = locator.get("sheet"), locator.get("cell")
    if sheet is not None and cell is not None:
        escaped_sheet = str(sheet).replace("'", "''")
        location.append(f"'{escaped_sheet}'!{cell}")
    line_range = locator.get("line_range")
    if line_range and all(x is not None for x in line_range):
        location.append(f"lines {line_range[0] + 1}-{line_range[1]}")
    values = {
        key: str(value) if value is not None else ""
        for key, value in metadata.model_dump().items()
    }
    values.update(
        source_id=source_id,
        asset_id=asset_id,
        span_id=span_id,
        citation_key=citation_key,
        title=metadata.title or title,
        page=str(page) if page is not None else "",
        section=section,
        locator=", ".join(location),
    )
    return contract.render(values)


def format_evidence_bundle(
    payload: dict[str, Any],
    contract: CitationFormatContract,
    metadata: CitationMetadata,
    *,
    title: str,
) -> None:
    """Attach display fields only after every entry renders successfully."""
    presentations = [
        render_citation(
            contract,
            metadata,
            source_id=entry["doc_id"],
            title=title,
            locator=entry,
            asset_id=entry.get("asset_id", ""),
            span_id=entry["span_id"],
            citation_key=payload.get("citation_key", ""),
        )
        for entry in payload["entries"]
    ]
    payload["citation_format"] = {
        "contract": contract.model_dump(mode="json"),
        "contract_sha256": contract.contract_sha256,
        "metadata": metadata.model_dump(mode="json", exclude_none=True),
        "metadata_origin": "caller_supplied",
    }
    for entry, presentation in zip(payload["entries"], presentations, strict=True):
        entry["citation_presentation"] = presentation
