from __future__ import annotations

from typing import Any

import fitz
import pytest

from src.application.document_service import DocumentService
from src.application.knowledge_service import KnowledgeService
from src.infrastructure.file_storage import FileStorage
from src.infrastructure.pdf_extractor import PyMuPDFExtractor
from src.presentation.tools import document_tools, knowledge_tools


class RecordingKnowledgeGraph:
    def __init__(self) -> None:
        self.inserted: list[tuple[str, str]] = []
        self.last_doc_id = ""

    @property
    def is_available(self) -> bool:
        return True

    async def insert(self, doc_id: str, text: str) -> None:
        self.last_doc_id = doc_id
        self.inserted.append((doc_id, text))

    async def extract_entities(self, _text: str, limit: int = 5) -> list[str]:
        return ["Remimazolam", "IL-6", "TNF-alpha"][:limit]

    async def query(
        self,
        _query: str,
        mode: str = "hybrid",
        *,
        user_prompt: str | None = None,
        include_references: bool = False,
    ) -> str:
        return f"Found Remimazolam in {self.last_doc_id}."

    async def query_structured(
        self,
        query: str,
        mode: str = "hybrid",
        *,
        user_prompt: str | None = None,
        include_references: bool = True,
    ) -> dict[str, Any]:
        return {
            "success": True,
            "status": "success",
            "query": query,
            "mode": mode,
            "answer": f"Found Remimazolam in {self.last_doc_id}.",
            "references": [{"doc_id": self.last_doc_id}],
            "counts": {"references": 1},
            "retrieval": {"entities": [], "relationships": [], "chunks": []},
            "metadata": {},
            "llm_response": {"content": "ok", "is_streaming": False},
        }

    async def query_data(
        self,
        query: str,
        mode: str = "hybrid",
        *,
        user_prompt: str | None = None,
    ) -> dict[str, Any]:
        return await self.query_structured(query, mode, user_prompt=user_prompt)

    async def delete_document(
        self,
        doc_id: str,
        *,
        delete_llm_cache: bool = False,
    ) -> dict[str, Any]:
        return {"status": "success", "doc_id": doc_id}

    async def export_graph(
        self,
        format: str = "summary",
        limit: int = 50,
        entity_types: list[str] | None = None,
    ) -> dict[str, object]:
        return {
            "format": "json",
            "nodes": [{"id": "Remimazolam", "type": "DRUG"}],
            "edges": [],
        }


def _write_pdf(path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "Remimazolam sedation evidence. IL-6 and TNF-alpha were monitored.",
    )
    doc.save(path)
    doc.close()


@pytest.mark.asyncio
async def test_pdf_ingest_kg_verified_evidence_returns_foam_links(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    pdf_path = tmp_path / "kg-smoke.pdf"
    _write_pdf(pdf_path)

    repository = FileStorage(base_dir=tmp_path / "data")
    knowledge_graph = RecordingKnowledgeGraph()
    service = DocumentService(
        repository=repository,
        pdf_extractor=PyMuPDFExtractor(),
        knowledge_graph=knowledge_graph,
    )

    results = await service.ingest(
        [str(pdf_path)],
        use_marker=False,
        extract_figures=False,
        index_knowledge_graph=True,
    )
    result = results[0]

    assert result.success, result.error
    assert knowledge_graph.inserted
    assert knowledge_graph.inserted[0][0] == result.doc_id

    manifest = await service.get_manifest(result.doc_id)
    assert manifest is not None
    assert manifest.lightrag_entities == ["Remimazolam", "IL-6", "TNF-alpha"]

    monkeypatch.setattr(document_tools, "repository", repository)
    bundle = await document_tools.citation_bundle(
        result.doc_id,
        query="Remimazolam",
        include_verification=True,
        output_format="json",
    )
    assert bundle["success"] is True
    assert bundle["entries"][0]["foam"]["wikilink"].startswith(
        f"[[{result.doc_id}#^spn-"
    )

    monkeypatch.setattr(
        knowledge_tools,
        "knowledge_service",
        KnowledgeService(knowledge_graph),
    )
    kg_result = await knowledge_tools.consult_knowledge_graph(
        "Remimazolam",
        verify_references=True,
    )

    assert kg_result["verified_evidence"]["success"] is True
    assert kg_result["foam_links"][0].startswith(f"[[{result.doc_id}#^spn-")
