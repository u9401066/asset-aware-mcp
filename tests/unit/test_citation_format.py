"""Citation styles cannot rewrite evidence, fabricate metadata or execute code."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path

import pytest

from src.application.citation_format_service import format_evidence_bundle
from src.domain.citation_format import (
    CitationFormatContract,
    CitationMetadata,
    resolve_citation_format,
)
from src.domain.entities import DocumentAssets, DocumentManifest
from src.infrastructure.file_storage import FileStorage


@pytest.mark.parametrize(
    "template",
    [
        "{authors.__class__}",
        "{authors[0]}",
        "{authors!r}",
        "{authors:>1000000}",
        "{}",
        "{0}",
        "{unknown}",
        "{authors",
    ],
)
def test_rejects_expressions_and_unknown_fields(template: str) -> None:
    with pytest.raises(ValueError):
        CitationFormatContract(inline_template=template, reference_template="{title}")


def test_custom_unicode_and_literal_braces_preserve_evidence() -> None:
    entry = {
        "doc_id": "doc_policy",
        "span_id": "spn_1",
        "page": 3,
        "line_range": [4, 6],
        "quote": "政策原文。",
        "asset_ref": {"quote_sha256": "canonical", "source_revision_id": "rev"},
    }
    before = deepcopy(entry)
    payload = {"entries": [entry]}
    contract = CitationFormatContract(
        name="內部政策",
        inline_template="【{source_id}／第{page}頁】",
        reference_template="{{內部}} {title}",
    )
    format_evidence_bundle(payload, contract, CitationMetadata(), title="政策")
    assert entry["citation_presentation"]["inline"] == "【doc_policy／第3頁】"
    assert entry["citation_presentation"]["reference"] == "{內部} 政策"
    assert {k: entry[k] for k in before} == before
    assert payload["citation_format"]["contract_sha256"] == contract.contract_sha256


def test_missing_metadata_does_not_partially_mutate_bundle() -> None:
    payload = {
        "entries": [
            {"doc_id": "doc_a", "span_id": "one", "page": 1},
            {"doc_id": "doc_a", "span_id": "two", "page": None},
        ]
    }
    before = deepcopy(payload)
    contract = CitationFormatContract(
        inline_template="{page}", reference_template="{title}"
    )
    with pytest.raises(ValueError, match="Missing citation metadata: page"):
        format_evidence_bundle(payload, contract, CitationMetadata(), title="Report")
    assert payload == before


def test_numeric_citations_use_stable_caller_number() -> None:
    contract = resolve_citation_format({"preset": "numeric"})
    payload = {"entries": [{"doc_id": "doc_a", "span_id": "spn_1", "page": 1}]}
    with pytest.raises(ValueError, match="reference_number"):
        format_evidence_bundle(payload, contract, CitationMetadata(), title="Report")
    format_evidence_bundle(
        payload, contract, CitationMetadata(reference_number=42), title="Report"
    )
    assert payload["entries"][0]["citation_presentation"]["inline"] == "[42]"


def test_repeated_substitutions_are_bounded_before_render() -> None:
    contract = CitationFormatContract(
        inline_template="{title}" * 100,
        reference_template="{title}",
    )
    with pytest.raises(ValueError, match="character limit"):
        contract.render({"title": "x" * 1024})


@pytest.mark.parametrize(
    "data",
    [
        {"page": 99},
        {"source_id": "forged"},
        {"quote_sha256": "forged"},
        {"reference_number": 0},
        {"reference_number": True},
    ],
)
def test_metadata_rejects_locator_overrides(data: dict) -> None:
    with pytest.raises(ValueError):
        CitationMetadata.model_validate(data)


@pytest.mark.parametrize(
    "data",
    [
        {"preset": "missing"},
        {"preset": []},
        {"preset": "source", "inline_template": "ignored?"},
    ],
)
def test_invalid_preset_selectors_fail(data: dict) -> None:
    with pytest.raises(ValueError):
        resolve_citation_format(data)


@pytest.fixture
def evidence_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FileStorage:
    from src.presentation.tools import document_tools

    repo = FileStorage(tmp_path / "data")
    repo.save_manifest(
        DocumentManifest(
            doc_id="doc_policy",
            filename="policy.pdf",
            title="政策",
            assets=DocumentAssets(),
        )
    )
    repo.save_markdown("doc_policy", "核准期限為三十日。\n")
    repo.save_blocks(
        "doc_policy",
        [
            {
                "block_id": "blk_1",
                "block_type": "Text",
                "page": 3,
                "text": "核准期限為三十日。",
                "metadata": {"line_start": 0, "line_end": 1},
            }
        ],
    )
    monkeypatch.setattr(document_tools, "repository", repo)
    return repo


async def test_mcp_formatting_and_foam_write_preserve_verified_ref(
    evidence_repo: FileStorage,
    tmp_path: Path,
) -> None:
    from src.presentation.tools.document_tools import evidence

    contract = {
        "inline_template": "【{source_id} 第{page}頁】",
        "reference_template": "{title}",
    }
    baseline = await evidence(
        op="bundle", doc_id="doc_policy", output_format="json", span_kinds=["block"]
    )
    formatted = await evidence(
        op="bundle",
        doc_id="doc_policy",
        output_format="json",
        span_kinds=["block"],
        citation_contract=contract,
    )
    assert formatted["success"]
    assert formatted["entries"][0]["asset_ref"] == baseline["entries"][0]["asset_ref"]
    assert formatted["entries"][0]["verification"]["valid"]
    assert (
        formatted["entries"][0]["citation_presentation"]["inline"]
        == "【doc_policy 第3頁】"
    )
    wiki = tmp_path / "wiki"
    result = await evidence(
        op="bundle",
        doc_id="doc_policy",
        output_format="foam",
        span_kinds=["block"],
        citation_contract=contract,
        wiki_root=str(wiki),
    )
    assert result["success"]
    notes = [p.read_text() for p in wiki.rglob("*.md")]
    assert any(r"Citation: 【doc\_policy 第3頁】" in text for text in notes)
    assert any(
        "citation-format-v1" in text and "quote_sha256" in text for text in notes
    )
    assert hashlib.sha256("核准期限為三十日。".encode()).hexdigest() in "\n".join(notes)


async def test_missing_bibliography_creates_no_wiki(
    evidence_repo: FileStorage,
    tmp_path: Path,
) -> None:
    from src.presentation.tools.document_tools import evidence

    wiki = tmp_path / "wiki"
    result = await evidence(
        op="bundle",
        doc_id="doc_policy",
        output_format="foam",
        wiki_root=str(wiki),
        citation_contract={"preset": "author-year"},
    )
    assert not result["success"]
    assert "authors" in result["error"] and "year" in result["error"]
    assert not wiki.exists()


async def test_contract_discovery_needs_no_document() -> None:
    from src.presentation.tools.document_tools import evidence

    result = await evidence(op="contract", citation_contract={"preset": "numeric"})
    assert result["success"]
    assert result["selected"]["name"] == "numeric"
    assert result["schema"]["additionalProperties"] is False


async def test_multiline_citation_is_text_not_new_wiki_structure(
    evidence_repo: FileStorage, tmp_path: Path
) -> None:
    from src.presentation.tools.document_tools import evidence

    title = "Title\n# Extra heading\n[[unrelated-note]] <b>content</b>"
    result = await evidence(
        op="bundle",
        doc_id="doc_policy",
        output_format="foam",
        span_kinds=["block"],
        citation_contract={
            "inline_template": "{title}",
            "reference_template": "{title}",
        },
        citation_metadata={"title": title},
        wiki_root=str(tmp_path / "wiki"),
    )
    assert result["success"]
    note = Path(result["output_path"]).read_text()
    body = note.split("---", 2)[-1]
    assert len([line for line in body.splitlines() if line.startswith("# ")]) == 1
    assert "[[unrelated-note]]" not in body
    assert "<b>content</b>" not in body
    assert "&lt;b&gt;content&lt;/b&gt;" in body
