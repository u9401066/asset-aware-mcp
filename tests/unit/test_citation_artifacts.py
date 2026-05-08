from __future__ import annotations

import json
from pathlib import Path

from src.application.citation_artifacts import (
    empty_citation_reason,
    load_citation_status,
    save_citation_status,
)


class MemoryRepository:
    def __init__(self, doc_dir: Path) -> None:
        self.doc_dir = doc_dir

    def get_doc_dir(self, _doc_id: str) -> Path:
        self.doc_dir.mkdir(parents=True, exist_ok=True)
        return self.doc_dir


def test_save_zero_citation_status_removes_stale_jsonl(tmp_path: Path) -> None:
    repository = MemoryRepository(tmp_path / "doc")
    stale_index = repository.get_doc_dir("doc") / "citation_index.jsonl"
    stale_index.write_text('{"stale": true}\n', encoding="utf-8")

    save_citation_status(
        repository,  # type: ignore[arg-type]
        "doc",
        source_backend="marker",
        found=0,
        reason="Blocks were present but did not contain citeable text.",
    )

    status = load_citation_status(repository, "doc")  # type: ignore[arg-type]
    assert status is not None
    assert status["attempted"] is True
    assert status["method"] == "marker"
    assert status["found"] == 0
    assert "citeable text" in status["reason"]
    assert not stale_index.exists()


def test_save_positive_citation_status_preserves_jsonl(tmp_path: Path) -> None:
    repository = MemoryRepository(tmp_path / "doc")
    index_path = repository.get_doc_dir("doc") / "citation_index.jsonl"
    index_path.write_text('{"span_id": "span_1"}\n', encoding="utf-8")

    save_citation_status(
        repository,  # type: ignore[arg-type]
        "doc",
        source_backend="pymupdf",
        found=1,
    )

    assert index_path.exists()
    status_path = repository.get_doc_dir("doc") / "citation_index.status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["found"] == 1
    assert status["reason"] == ""


def test_empty_citation_reason_distinguishes_empty_and_textless_blocks() -> None:
    assert empty_citation_reason([]).startswith("No blocks")
    assert "citeable text" in empty_citation_reason(
        [{"block_id": "mk_1", "block_type": "MarkdownOutput", "text": ""}]
    )
