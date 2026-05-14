"""
Unit tests for MCP presentation-layer tools.

Tests tool functions directly (without MCP transport) to validate
error handling, input validation, and response formatting.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================================
# Docx Tools
# ============================================================================


class TestKnowledgeTools:
    """Tests for knowledge_tools.py MCP functions."""

    async def test_export_knowledge_graph_disabled(self) -> None:
        """export_knowledge_graph shows error when LightRAG disabled."""
        with patch("src.presentation.tools.knowledge_tools.knowledge_graph", None):
            from src.presentation.tools.knowledge_tools import (
                export_knowledge_graph,
            )

            result = await export_knowledge_graph()
            assert "not enabled" in result.lower() or "Error" in result

    async def test_export_knowledge_graph_times_out_in_request_guard(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Slow graph export should return a bounded timeout message."""
        from src.presentation.tools import knowledge_tools

        async def slow_export(*_args, **_kwargs):
            await asyncio.sleep(3600)

        mock_graph = MagicMock()
        mock_graph.export_graph = AsyncMock(side_effect=slow_export)
        monkeypatch.setattr(knowledge_tools, "knowledge_graph", mock_graph)
        monkeypatch.setattr(
            knowledge_tools,
            "KNOWLEDGE_TOOL_TIMEOUT_SECONDS",
            0.01,
        )

        result = await knowledge_tools.export_knowledge_graph(format="summary", limit=5)

        assert "timed out" in result
        assert "limit=5" in result

    async def test_consult_knowledge_graph_reports_progress(self) -> None:
        """consult_knowledge_graph emits MCP progress when Context is injected."""
        fake_ctx = MagicMock()
        fake_ctx.report_progress = AsyncMock()
        fake_ctx.log = AsyncMock()

        with patch(
            "src.presentation.tools.knowledge_tools.knowledge_service"
        ) as mock_svc:
            mock_svc.query_structured = AsyncMock(
                return_value={"success": True, "answer": "answer", "references": []}
            )
            from src.presentation.tools.knowledge_tools import consult_knowledge_graph

            result = await consult_knowledge_graph("test", ctx=fake_ctx)

        assert result == {"success": True, "answer": "answer", "references": []}
        assert fake_ctx.report_progress.await_count >= 2

    async def test_consult_knowledge_graph_times_out_in_request_guard(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Slow LightRAG calls should return a bounded timeout record."""
        from src.presentation.tools import knowledge_tools

        async def slow_query(*_args, **_kwargs):
            await asyncio.sleep(3600)

        with patch(
            "src.presentation.tools.knowledge_tools.knowledge_service"
        ) as mock_svc:
            mock_svc.query_structured = AsyncMock(side_effect=slow_query)
            monkeypatch.setattr(
                knowledge_tools,
                "KNOWLEDGE_TOOL_TIMEOUT_SECONDS",
                0.01,
            )

            result = await knowledge_tools.consult_knowledge_graph("test")

        assert isinstance(result, dict)
        assert result["status"] == "timeout"
        assert result["query"] == "test"

    async def test_consult_knowledge_graph_forwards_new_query_options(self) -> None:
        """consult_knowledge_graph forwards include_references and user_prompt."""
        with patch(
            "src.presentation.tools.knowledge_tools.knowledge_service"
        ) as mock_svc:
            mock_svc.query_structured = AsyncMock(return_value={"success": True})
            from src.presentation.tools.knowledge_tools import consult_knowledge_graph

            result = await consult_knowledge_graph(
                "test",
                mode="mix",
                user_prompt="Summarize as bullets",
                include_references=True,
            )

        assert result == {"success": True}
        mock_svc.query_structured.assert_awaited_once_with(
            "test",
            mode="mix",
            user_prompt="Summarize as bullets",
            include_references=True,
        )

    async def test_consult_knowledge_graph_supports_data_mode(self) -> None:
        """consult_knowledge_graph can return retrieval-only structured data."""
        with patch(
            "src.presentation.tools.knowledge_tools.knowledge_service"
        ) as mock_svc:
            mock_svc.query_data = AsyncMock(
                return_value={"success": True, "answer": None}
            )
            from src.presentation.tools.knowledge_tools import consult_knowledge_graph

            result = await consult_knowledge_graph(
                "test",
                response_mode="data",
            )

        assert result == {"success": True, "answer": None}
        mock_svc.query_data.assert_awaited_once_with(
            "test",
            mode="hybrid",
            user_prompt=None,
        )

    async def test_consult_knowledge_graph_supports_text_mode(self) -> None:
        """consult_knowledge_graph can still return plain text when requested."""
        with patch(
            "src.presentation.tools.knowledge_tools.knowledge_service"
        ) as mock_svc:
            mock_svc.query = AsyncMock(return_value="plain answer")
            from src.presentation.tools.knowledge_tools import consult_knowledge_graph

            result = await consult_knowledge_graph(
                "test",
                response_mode="text",
            )

        assert result == "plain answer"
        mock_svc.query.assert_awaited_once_with(
            "test",
            mode="hybrid",
            user_prompt=None,
            include_references=False,
        )

    async def test_consult_knowledge_graph_attaches_verified_evidence(self) -> None:
        """KG answers can attach verified citation bundles for source docs."""
        with (
            patch(
                "src.presentation.tools.knowledge_tools.knowledge_service"
            ) as mock_svc,
            patch(
                "src.presentation.tools.document_tools.citation_bundle",
                new_callable=AsyncMock,
            ) as mock_bundle,
        ):
            mock_svc.query_structured = AsyncMock(
                return_value={
                    "success": True,
                    "answer": "ok",
                    "references": [{"doc_id": "doc_123"}],
                }
            )
            mock_bundle.return_value = {
                "success": True,
                "doc_id": "doc_123",
                "returned": 1,
                "matched_count": 1,
                "entries": [{"span_id": "spn_1"}],
            }
            from src.presentation.tools.knowledge_tools import consult_knowledge_graph

            result = await consult_knowledge_graph(
                "dose",
                verify_references=True,
                evidence_limit=2,
            )

        assert result["verified_evidence"]["success"] is True
        mock_svc.query_structured.assert_awaited_once_with(
            "dose",
            mode="hybrid",
            user_prompt=None,
            include_references=True,
        )
        mock_bundle.assert_awaited_once_with(
            "doc_123",
            query="dose",
            limit=2,
            include_verification=True,
            output_format="json",
        )

    async def test_consult_knowledge_graph_skips_verification_without_doc_ids(
        self,
    ) -> None:
        """KG verification should fail closed when no source doc_id is known."""
        with (
            patch(
                "src.presentation.tools.knowledge_tools.knowledge_service"
            ) as mock_svc,
            patch(
                "src.presentation.tools.document_tools.citation_bundle",
                new_callable=AsyncMock,
            ) as mock_bundle,
        ):
            mock_svc.query_structured = AsyncMock(
                return_value={
                    "success": True,
                    "answer": "KG answer without explicit source ids",
                    "references": [{"title": "missing doc id"}],
                }
            )
            from src.presentation.tools.knowledge_tools import consult_knowledge_graph

            result = await consult_knowledge_graph(
                "dose",
                verify_references=True,
            )

        assert result["verified_evidence"]["status"] == "skipped"
        assert result["foam_links"] == []
        mock_bundle.assert_not_awaited()

    async def test_consult_knowledge_graph_surfaces_verified_foam_links(self) -> None:
        """Structured KG answers should expose Foam links from verified evidence."""
        with (
            patch(
                "src.presentation.tools.knowledge_tools.knowledge_service"
            ) as mock_svc,
            patch(
                "src.presentation.tools.document_tools.citation_bundle",
                new_callable=AsyncMock,
            ) as mock_bundle,
        ):
            mock_svc.query_structured = AsyncMock(
                return_value={
                    "success": True,
                    "answer": "KG answer",
                    "references": [{"doc_id": "doc_123"}],
                }
            )
            mock_bundle.return_value = {
                "success": True,
                "doc_id": "doc_123",
                "entries": [
                    {
                        "span_id": "spn_1",
                        "foam": {
                            "wikilink": "[[doc_123#^spn-1]]",
                            "embed": "![[doc_123#^spn-1]]",
                        },
                    }
                ],
            }
            from src.presentation.tools.knowledge_tools import consult_knowledge_graph

            result = await consult_knowledge_graph(
                "dose",
                verify_references=True,
            )

        assert result["foam_links"] == ["[[doc_123#^spn-1]]"]
        assert result["verified_foam_links"] == ["[[doc_123#^spn-1]]"]
        assert result["foam_link_details"] == [
            {"link": "[[doc_123#^spn-1]]", "link_kind": "verified_evidence"}
        ]
        assert (
            result["verified_evidence"]["bundles"][0]["entries"][0]["foam"]["wikilink"]
            == "[[doc_123#^spn-1]]"
        )

    async def test_consult_knowledge_graph_text_mode_shows_verified_foam_links(
        self,
    ) -> None:
        """Text KG answers should render verified Foam links for copy/paste workflows."""
        with (
            patch(
                "src.presentation.tools.knowledge_tools.knowledge_service"
            ) as mock_svc,
            patch(
                "src.presentation.tools.document_tools.citation_bundle",
                new_callable=AsyncMock,
            ) as mock_bundle,
        ):
            mock_svc.query = AsyncMock(return_value="KG answer")
            mock_bundle.return_value = {
                "success": True,
                "doc_id": "doc_123",
                "returned": 1,
                "matched_count": 1,
                "entries": [
                    {
                        "span_id": "spn_1",
                        "page": 4,
                        "line_display": "L9-10",
                        "quote": "Evidence quote",
                        "foam": {"wikilink": "[[doc_123#^spn-1]]"},
                    }
                ],
            }
            from src.presentation.tools.knowledge_tools import consult_knowledge_graph

            result = await consult_knowledge_graph(
                "dose",
                response_mode="text",
                verify_references=True,
                doc_ids=["doc_123"],
            )

        assert isinstance(result, str)
        assert "[[doc_123#^spn-1]]" in result

    async def test_export_knowledge_graph_supports_foam_wikilink_format(self) -> None:
        """KG export should have an explicit Foam/wiki-link presentation."""
        with patch(
            "src.presentation.tools.knowledge_tools.knowledge_graph"
        ) as mock_graph:
            mock_graph.export_graph = AsyncMock(
                return_value={
                    "format": "json",
                    "nodes": [
                        {
                            "id": "Remimazolam",
                            "type": "DRUG",
                            "description": "Sedation agent",
                        },
                        {
                            "id": "Propofol",
                            "type": "DRUG",
                            "description": "Comparator",
                        },
                    ],
                    "edges": [
                        {
                            "source": "Remimazolam",
                            "target": "Propofol",
                            "keywords": "sedation comparison",
                        }
                    ],
                }
            )
            from src.presentation.tools.knowledge_tools import export_knowledge_graph

            result = await export_knowledge_graph(format="foam", limit=10)

        assert "[[Remimazolam]]" in result
        assert "[[Propofol]]" in result
        assert "[[Remimazolam]] -> [[Propofol]]" in result
        assert "Knowledge Graph Discovery Link Candidates" in result
        assert "Entity links are KG discovery links" in result
        mock_graph.export_graph.assert_awaited_once_with(format="json", limit=10)

    async def test_consult_knowledge_graph_rejects_invalid_response_mode(self) -> None:
        """consult_knowledge_graph should fail fast on invalid response_mode."""
        from src.presentation.tools.knowledge_tools import consult_knowledge_graph

        with pytest.raises(ValueError, match="response_mode must be one of"):
            await consult_knowledge_graph("test", response_mode="yaml")

    async def test_knowledge_op_routes_export(self) -> None:
        """knowledge(op='export') keeps export as an explicit operation."""
        with patch(
            "src.presentation.tools.knowledge_tools.export_knowledge_graph",
            new_callable=AsyncMock,
        ) as mock_export:
            mock_export.return_value = "graph"
            from src.presentation.tools.knowledge_tools import knowledge

            result = await knowledge("export", format="summary", limit=10)

        assert result == "graph"
        mock_export.assert_awaited_once_with("summary", 10, ctx=None)

    async def test_knowledge_op_routes_query(self) -> None:
        """knowledge(op='query') delegates to consult_knowledge_graph."""
        with patch(
            "src.presentation.tools.knowledge_tools.consult_knowledge_graph",
            new_callable=AsyncMock,
        ) as mock_consult:
            mock_consult.return_value = {"answer": "ok"}
            from src.presentation.tools.knowledge_tools import knowledge

            result = await knowledge(
                "query",
                query="dose",
                mode="mix",
                response_mode="data",
                user_prompt="brief",
                include_references=True,
            )

        assert result == {"answer": "ok"}
        mock_consult.assert_awaited_once_with(
            "dose",
            mode="mix",
            response_mode="data",
            user_prompt="brief",
            include_references=True,
            verify_references=False,
            doc_ids=None,
            evidence_limit=5,
            ctx=None,
        )

    async def test_knowledge_op_rejects_unknown_operation(self) -> None:
        """knowledge(op, ...) fails closed for unsupported operations."""
        from src.presentation.tools.knowledge_tools import knowledge

        result = await knowledge("mutate", query="test")

        assert isinstance(result, str)
        assert "Unsupported knowledge op" in result


# ============================================================================
# Server-level
# ============================================================================
