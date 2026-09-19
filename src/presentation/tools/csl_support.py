"""Bounded CSL operations exposed through the existing evidence MCP tool."""

from __future__ import annotations

import asyncio
from typing import Any

from src.application.csl_citation_service import citation_page
from src.domain.csl_citations import CslDocument
from src.domain.etl_evidence import EtlEvidenceReference, EtlSourceSelector
from src.presentation.dependencies import csl_citation_service, etl_evidence_service


async def etl_operation(
    operation: str,
    ref: dict[str, Any] | None,
    offset: int,
    limit: int,
    expected: str | None,
    render_size: int,
) -> dict[str, Any]:
    try:
        if ref is None:
            raise ValueError("ETL evidence operations require ref")
        citation_page({}, offset, limit, None)
        if operation == "inspect_etl_source":
            selector = EtlSourceSelector.model_validate(ref)
            result = await asyncio.to_thread(etl_evidence_service.inspect, selector)
        elif operation == "capture_etl_source":
            result = await asyncio.to_thread(
                etl_evidence_service.capture, ref, expected
            )
        else:
            parsed = EtlEvidenceReference.model_validate(ref)
            if operation == "view_etl_source":
                if offset or limit != 4000 or expected is not None:
                    raise ValueError(
                        "view_etl_source uses ref/render_size, not text paging"
                    )
                return await asyncio.to_thread(
                    etl_evidence_service.view, parsed, render_size
                )
            result = await asyncio.to_thread(etl_evidence_service.read, parsed)
        return citation_page(result, offset, limit, expected)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"success": False, "error": str(exc)[:2000]}


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
