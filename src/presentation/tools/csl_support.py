"""Bounded CSL operations exposed through the existing evidence MCP tool."""

from __future__ import annotations

import asyncio
from typing import Any

from src.application.csl_citation_service import citation_page
from src.domain.csl_citations import CslDocument
from src.presentation.dependencies import csl_citation_service


async def csl_operation(
    operation: str,
    document: dict[str, Any] | None,
    wiki_root: str,
    offset: int,
    limit: int,
    expected: str | None,
) -> dict[str, Any]:
    try:
        if operation == "csl_contract":
            if document is not None or wiki_root:
                raise ValueError(
                    "csl_contract does not accept citation_document or wiki_root"
                )
            result = await asyncio.to_thread(csl_citation_service.contract)
            return citation_page(result, offset, limit, expected)
        if document is None:
            raise ValueError("render_citations requires citation_document")
        parsed = CslDocument.model_validate(document)
        # Validate paging before rendering or publishing any files.
        citation_page({}, offset, limit, None)
        result, publication = await asyncio.to_thread(
            csl_citation_service.render, parsed, wiki_root, expected
        )
        page = citation_page(result, offset, limit, expected)
        if publication is not None:
            page["publication"] = publication
            if not publication["success"]:
                page["success"] = False
        return page
    except (OSError, ValueError) as exc:
        return {"success": False, "error": str(exc)[:2000]}
