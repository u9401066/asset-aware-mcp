"""Persistence helpers for citation index sidecar artifacts."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.repositories import DocumentRepository


def save_citation_status(
    repository: DocumentRepository,
    doc_id: str,
    *,
    source_backend: str,
    found: int,
    reason: str = "",
) -> None:
    """Persist extraction status separately from JSONL evidence spans."""
    doc_dir = repository.get_doc_dir(doc_id)
    (doc_dir / "citation_index.status.json").write_text(
        json.dumps(
            {
                "attempted": True,
                "method": source_backend,
                "found": found,
                "reason": reason,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if found == 0:
        remove_citation_index(repository, doc_id)


def load_citation_status(
    repository: DocumentRepository,
    doc_id: str,
) -> dict[str, Any] | None:
    """Load citation extraction status if present."""
    try:
        status_path = repository.get_doc_dir(doc_id) / "citation_index.status.json"
        if not status_path.exists():
            return None
        status = json.loads(status_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return status if isinstance(status, dict) else None


def remove_citation_index(repository: DocumentRepository, doc_id: str) -> None:
    """Remove stale/empty JSONL evidence index files."""
    index_path = repository.get_doc_dir(doc_id) / "citation_index.jsonl"
    index_path.unlink(missing_ok=True)


def empty_citation_reason(blocks_data: list[dict[str, Any]]) -> str:
    """Explain why a block collection could not produce evidence spans."""
    if not blocks_data:
        return "No blocks were available for citation extraction."
    if not any(str(block.get("text") or "").strip() for block in blocks_data):
        return "Blocks were present but did not contain citeable text."
    return (
        "Blocks did not include enough stable line/character locator metadata "
        "to build citation spans."
    )
