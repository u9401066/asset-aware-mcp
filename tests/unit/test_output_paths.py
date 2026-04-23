from __future__ import annotations

from pathlib import Path

import pytest

from src.application.output_paths import (
    resolve_document_output_dir,
    resolve_document_output_path,
)


def test_resolve_document_output_path_keeps_relative_paths_inside_doc_dir(
    tmp_path: Path,
) -> None:
    doc_dir = tmp_path / "doc_test_abc123"
    doc_dir.mkdir()

    resolved = resolve_document_output_path(
        doc_dir,
        "exports/result.pdf",
        default_name="output.pdf",
        allowed_suffixes={".pdf"},
    )

    assert resolved == doc_dir / "exports" / "result.pdf"


def test_resolve_document_output_path_rejects_parent_escape(tmp_path: Path) -> None:
    doc_dir = tmp_path / "doc_test_abc123"
    doc_dir.mkdir()

    with pytest.raises(ValueError, match="within document directory"):
        resolve_document_output_path(
            doc_dir,
            "../outside.pdf",
            default_name="output.pdf",
            allowed_suffixes={".pdf"},
        )


def test_resolve_document_output_path_rejects_wrong_suffix(tmp_path: Path) -> None:
    doc_dir = tmp_path / "doc_test_abc123"
    doc_dir.mkdir()

    with pytest.raises(ValueError, match="must use one of"):
        resolve_document_output_path(
            doc_dir,
            "output.txt",
            default_name="output.pdf",
            allowed_suffixes={".pdf"},
        )


def test_resolve_document_output_dir_rejects_parent_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Output directory must stay within"):
        resolve_document_output_dir(
            tmp_path,
            "../outside",
            default_name="doc_test_abc123",
        )
