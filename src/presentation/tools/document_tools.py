"""
Document Tools - ETL + 文件管理 MCP 工具

包含：
- parse_pdf_structure: Marker 結構化解析
- search_source_location: 來源位置搜尋
- ingest_documents: PDF 文件攝入
- list_documents: 列出所有文件
- delete_document: 刪除已攝入的 PDF 文件及本地 artifacts
- convert_pdf_to_docx: 將 PDF 內容層重建為 DOCX
- convert_pdf_to_pptx: 將 PDF Markdown 重建為可編輯 PPTX
- inspect_document_manifest: 查看文件 Manifest
- fetch_document_asset: 擷取文件資產
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.types import ImageContent, TextContent

from src.application.document_readiness_service import (
    AI_READINESS_ARTIFACTS,
    AI_READINESS_REQUIRED_AUDITS,
    DocumentReadinessService,
)
from src.application.document_service import normalize_page_ranges
from src.application.output_paths import (
    resolve_document_output_path,
)
from src.domain.marker_errors import MarkerBackendUnavailable
from src.infrastructure.structured_extractor import is_structured_engine
from src.presentation.dependencies import (
    asset_service,
    document_service,
    docx_service,
    get_marker_extractor,
    job_service,
    layout_visualizer,
    pdf_extractor,
    pdf_report_service,
    repository,
    segmentation_service,
    structural_pointer_service,
)
from src.presentation.mcp_app import mcp
from src.presentation.mcp_context import (
    create_subrange_progress_callback,
    log_message,
    report_progress,
)
from src.presentation.response_limits import (
    format_limited_json_response,
    format_limited_text_response,
    format_omitted_image_response,
    image_exceeds_response_limit,
    max_text_response_chars,
    text_sha256,
)
from src.presentation.tools.citation_support import (
    asset_ref_from_span,
    display_line_range,
    format_line_range,
    load_citation_status,
    load_or_build_evidence_spans,
)
from src.presentation.tools.conversion_job_support import (
    conversion_result_payload,
    create_conversion_job_response,
)
from src.presentation.tools.document_evidence_support import (
    _audit_foam_wiki_health,
    _citation_bundle_entry,
    _claim_promotion_payload,
    _filter_evidence_spans,
    _format_citation_bundle,
    _format_claim_promotion_markdown,
    _format_foam_claim_promotion_pack,
    _format_foam_evidence_pack,
    _missing_document_param,
    _normalize_op,
    _unsupported_document_op,
    _verify_span_ref_payload,
    _write_foam_asset_notes,
    _write_foam_claim_promotion_pack,
    _write_foam_evidence_pack,
)
from src.presentation.tools.mixed_ingest_support import (
    build_mixed_ingest_handler,
    format_counts,
    is_mixed_or_non_pdf_batch,
)


class MarkerPDFExtractor:
    """Lazy proxy for Marker availability checks used by MCP tools/tests."""

    @staticmethod
    def require_backend_available() -> None:
        from src.infrastructure.marker_adapter import MarkerPDFExtractor as _Marker

        _Marker.require_backend_available()


JSON_TEXT_FIELD_MAX_CHARS = 1_000
JSON_ARTIFACT_INLINE_MAX_CHARS = 1_200


def _truncate_json_text_field(container: dict[str, Any], key: str) -> bool:
    value = container.get(key)
    if not isinstance(value, str) or len(value) <= JSON_TEXT_FIELD_MAX_CHARS:
        return False
    container[f"{key}_chars"] = len(value)
    container[f"{key}_sha256"] = text_sha256(value)
    container[f"{key}_truncated"] = True
    container[key] = value[:JSON_TEXT_FIELD_MAX_CHARS]
    return True


def _bounded_evidence_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Preserve JSON contract while bounding large quote/context fields."""
    bounded = deepcopy(payload)
    original_json = json.dumps(payload, ensure_ascii=False, default=str)
    truncated = False
    for entry in bounded.get("entries", []):
        if not isinstance(entry, dict):
            continue
        for key in ("quote", "context_before", "context_after", "claim_text"):
            truncated = _truncate_json_text_field(entry, key) or truncated
        asset_ref = entry.get("asset_ref")
        if isinstance(asset_ref, dict):
            truncated = _truncate_json_text_field(asset_ref, "quote") or truncated
            truncated = _truncate_json_text_field(asset_ref, "excerpt") or truncated
        evidence = entry.get("evidence")
        if isinstance(evidence, dict):
            for key in ("quote", "context_before", "context_after"):
                truncated = _truncate_json_text_field(evidence, key) or truncated
            nested_ref = evidence.get("asset_ref")
            if isinstance(nested_ref, dict):
                truncated = _truncate_json_text_field(nested_ref, "quote") or truncated
    if truncated:
        bounded["response_truncated"] = True
        bounded["content_chars"] = len(original_json)
        bounded["sha256"] = text_sha256(original_json)
    limit = max_text_response_chars()
    entries = bounded.get("entries")
    if limit > 0 and isinstance(entries, list):
        for keep in (3, 1):
            bounded_json = json.dumps(
                bounded, ensure_ascii=False, indent=2, default=str
            )
            if len(bounded_json) <= limit:
                break
            if len(entries) <= keep:
                continue
            bounded["entries"] = entries[:keep]
            bounded["entries_omitted"] = max(0, len(entries) - keep)
            bounded["response_truncated"] = True
            bounded.setdefault("content_chars", len(original_json))
            bounded.setdefault("sha256", text_sha256(original_json))
        bounded_json = json.dumps(bounded, ensure_ascii=False, indent=2, default=str)
        if len(bounded_json) > limit:
            for entry in bounded.get("entries", []):
                if not isinstance(entry, dict):
                    continue
                entry.pop("craap", None)
                asset_ref = entry.get("asset_ref")
                if isinstance(asset_ref, dict):
                    asset_ref.pop("craap", None)
                foam = entry.get("foam")
                if isinstance(foam, dict):
                    foam.pop("frontmatter", None)
                verification = entry.get("verification")
                if isinstance(verification, dict):
                    entry["verification"] = {
                        "valid": verification.get("valid"),
                        "status": verification.get("status"),
                        "issues": verification.get("issues") or [],
                    }
            bounded["response_truncated"] = True
            bounded.setdefault("content_chars", len(original_json))
            bounded.setdefault("sha256", text_sha256(original_json))
    return bounded


if TYPE_CHECKING:
    from mcp.server.fastmcp import Context
else:
    Context = Any


def _should_force_background_ingest(
    file_paths: list[str],
    *,
    use_marker: bool,
    ocr_enabled: bool,
    page_ranges: list[str] | None,
) -> tuple[bool, str]:
    """Decide whether sync ingestion should become a background job.

    Cline/stdio MCP requests have a finite request timeout. Even small PyMuPDF
    ingests can hit document-level extractor timeouts on Windows when the MCP
    server is launched through stdio, so the presentation layer should return a
    job id immediately and let callers poll with get_job_status.
    """
    return True, (
        "PDF ingestion runs in the background worker to avoid MCP stdio "
        "request timeouts"
    )


def _ingest_job_parameters(
    *,
    use_marker: bool,
    ocr_enabled: bool,
    ocr_language: str,
    rotate_pages: bool,
    deskew: bool,
    marker_max_pages_per_chunk: int,
    extract_figures: bool,
    index_knowledge_graph: bool,
    page_ranges: list[str] | None,
    operation: str = "ingest_documents",
    require_marker: bool = False,
) -> dict[str, Any]:
    from src.presentation import dependencies

    return {
        "operation": operation,
        "use_marker": use_marker,
        "require_marker": require_marker,
        "ocr_enabled": ocr_enabled,
        "ocr_language": ocr_language,
        "rotate_pages": rotate_pages,
        "deskew": deskew,
        "marker_max_pages_per_chunk": marker_max_pages_per_chunk,
        "extract_figures": extract_figures,
        "index_knowledge_graph": index_knowledge_graph,
        "page_ranges": page_ranges or [],
        "etl_profile": dependencies.etl_profile.name,
    }


async def _create_ingest_job_response(
    file_paths: list[str],
    *,
    use_marker: bool,
    ocr_enabled: bool,
    ocr_language: str,
    rotate_pages: bool,
    deskew: bool,
    marker_max_pages_per_chunk: int,
    extract_figures: bool,
    index_knowledge_graph: bool,
    page_ranges: list[str] | None,
    ctx: Context | None,
    forced_reason: str = "",
    title: str = "ETL Job Created",
    operation: str = "ingest_documents",
    require_marker: bool = False,
) -> str:
    await report_progress(ctx, 20, message="Creating background ETL job")
    try:
        job = await job_service.create_ingest_job(
            file_paths,
            parameters=_ingest_job_parameters(
                use_marker=use_marker,
                ocr_enabled=ocr_enabled,
                ocr_language=ocr_language,
                rotate_pages=rotate_pages,
                deskew=deskew,
                marker_max_pages_per_chunk=marker_max_pages_per_chunk,
                extract_figures=extract_figures,
                index_knowledge_graph=index_knowledge_graph,
                page_ranges=page_ranges,
                operation=operation,
                require_marker=require_marker,
            ),
        )
    except RuntimeError as e:
        await log_message(ctx, "error", f"ingest_documents job creation failed: {e}")
        return f"# ??Could Not Create ETL Job\n\n{e!s}"

    await report_progress(ctx, 100, message=f"Created job {job.job_id}")
    await log_message(ctx, "info", f"ingest_documents job created: {job.job_id}")

    backend_note = " (Marker)" if use_marker else ""
    lines = [
        f"# ?? {title}{backend_note}",
        "",
        f"**Job ID:** `{job.job_id}`",
        f"**Files:** {len(file_paths)}",
        f"**Backend:** {'Marker (structured)' if use_marker else 'PyMuPDF (fast)'}",
        f"**Estimated Time:** ~{job.estimated_duration_seconds or 10}s",
        "**Status:** accepted_async",
        f"**Reason:** {forced_reason or 'async_mode=true'}",
        f'**Next:** get_job_status("{job.job_id}")',
        "",
        "```json",
        json.dumps(
            {
                "status": "accepted_async",
                "reason": forced_reason or "async_mode=true",
                "job_id": job.job_id,
                "next": f'get_job_status("{job.job_id}")',
            },
            ensure_ascii=False,
            indent=2,
        ),
        "```",
    ]
    if forced_reason:
        lines.append(f"**Background Reason:** {forced_reason}")
    lines.extend(
        [
            "",
            f'Use `get_job_status("{job.job_id}")` to check progress.',
            f'Use `cancel_job("{job.job_id}")` if the job is no longer needed.',
            "Or use `list_jobs()` to see all active jobs.",
        ]
    )
    return "\n".join(lines)


@mcp.tool()
async def parse_pdf_structure(
    pdf_path: str,
    output_dir: str | None = None,
    async_mode: bool = True,
    ocr_enabled: bool = False,
    ocr_language: str = "eng",
    rotate_pages: bool = False,
    deskew: bool = False,
    marker_max_pages_per_chunk: int = 0,
    extract_figures: bool = True,
    page_ranges: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Create a background Marker parse job for a PDF."""
    pdf_file = Path(pdf_path)

    await log_message(ctx, "info", f"parse_pdf_structure start: {pdf_path}")
    await report_progress(ctx, 5, message=f"Validating {pdf_file.name}")

    if not pdf_file.exists():
        return f"❌ File not found: {pdf_path}"

    try:
        if page_ranges:
            total_page_count = pdf_extractor.get_page_count(pdf_file)
            normalize_page_ranges(page_ranges, total_page_count)
    except Exception as e:
        await log_message(ctx, "error", f"parse_pdf_structure invalid input: {e}")
        return f"❌ Invalid PDF or page range: {e!s}"

    try:
        MarkerPDFExtractor.require_backend_available()
    except MarkerBackendUnavailable as e:
        await log_message(ctx, "error", f"parse_pdf_structure marker unavailable: {e}")
        return (
            "# Marker Backend Not Available\n\n"
            f"{e!s}\n\n"
            "Use `ingest_documents(..., use_marker=False)` for the secure "
            "PyMuPDF backend, or install a compatible Marker runtime before "
            "requesting structure parsing."
        )

    if not async_mode:
        await log_message(
            ctx,
            "warning",
            "parse_pdf_structure forcing background job despite async_mode=False",
        )

    response = await _create_ingest_job_response(
        [pdf_path],
        use_marker=True,
        ocr_enabled=ocr_enabled,
        ocr_language=ocr_language,
        rotate_pages=rotate_pages,
        deskew=deskew,
        marker_max_pages_per_chunk=marker_max_pages_per_chunk,
        extract_figures=extract_figures,
        index_knowledge_graph=False,
        page_ranges=page_ranges,
        ctx=ctx,
        forced_reason=(
            "parse_pdf_structure uses Marker and is always routed through the "
            "background job system to avoid MCP stdio request timeouts"
        ),
        title="PDF Structure Parse Job Created",
        operation="parse_pdf_structure",
        require_marker=True,
    )
    if output_dir:
        response += (
            "\n\n**Note:** `output_dir` is ignored for background parses; artifacts "
            "are written under the configured data directory."
        )
    return response


@mcp.tool()
async def search_source_location(
    doc_id: str,
    query: str,
    block_types: list[str] | None = None,
) -> str:
    """
    搜尋文件中的來源位置（頁碼 + bbox）。

    用於驗證答案來源時，精確定位內容在原始 PDF 的位置。

    Args:
        doc_id: 文件 ID
        query: 搜尋關鍵字
        block_types: 限制搜尋的區塊類型（Text, Table, Figure, SectionHeader）

    Returns:
        匹配的區塊列表，包含頁碼和位置
    """
    try:
        blocks_data = repository.load_blocks(doc_id)
    except ValueError as e:
        return f"❌ Invalid doc_id: {e!s}"

    if blocks_data is None:
        return (
            f"❌ Blocks not found for doc_id: {doc_id}. "
            "Run `ingest_documents` with `use_marker=True` first."
        )

    try:
        if block_types:
            blocks_data = [b for b in blocks_data if b.get("block_type") in block_types]

        query_lower = query.lower()
        matches = []
        for block in blocks_data:
            text = block.get("text", "").lower()
            if query_lower in text:
                matches.append(
                    {
                        "block_id": block.get("block_id"),
                        "block_type": block.get("block_type"),
                        "page": block.get("page"),
                        "bbox": block.get("bbox"),
                        "section": block.get("section_hierarchy"),
                        "snippet": block.get("text", "")[:150] + "...",
                    }
                )

        if not matches:
            return f"No matches found for '{query}' in doc_id: {doc_id}"

        lines = [
            f"# 🔍 Source Locations for '{query}'",
            "",
            f"**Found:** {len(matches)} matches",
            "",
        ]

        for i, m in enumerate(matches[:10], 1):
            lines.append(f"## Match {i}")
            lines.append(f"- **Block:** `{m['block_id']}` ({m['block_type']})")
            lines.append(f"- **Page:** {m['page']}")
            if m.get("bbox"):
                lines.append(f"- **BBox:** {m['bbox']}")
            if m.get("section"):
                lines.append(f"- **Section:** {m['section']}")
            lines.append(f"- **Snippet:** _{m['snippet']}_")
            lines.append("")

        if len(matches) > 10:
            lines.append(f"_...and {len(matches) - 10} more matches_")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Search failed: {e!s}"


@mcp.tool()
async def find_evidence_spans(
    doc_id: str,
    query: str = "",
    span_id: str = "",
    span_kinds: list[str] | None = None,
    limit: int = 10,
) -> str:
    """
    Search citation-ready evidence spans with exact locator metadata.

    Returns span-level AssetRef JSON that can be passed to table_cite.
    """
    spans = load_or_build_evidence_spans(repository, doc_id)
    if not spans:
        status = load_citation_status(repository, doc_id) or {}
        reason = str(status.get("reason") or "").strip()
        if reason:
            return (
                f"No citation-ready evidence spans found for doc_id: {doc_id}. {reason}"
            )
        return (
            f"Citation index not found for doc_id: {doc_id}. "
            "Run ingest_documents again or ensure blocks.json/full markdown exist."
        )

    spans = _filter_evidence_spans(
        spans,
        query=query,
        span_id=span_id,
        span_kinds=span_kinds,
    )

    if not spans:
        target = span_id or query
        return f"No evidence spans found for `{target}` in doc_id: {doc_id}"

    lines = [
        f"# Evidence Spans: {doc_id}",
        "",
        f"**Found:** {len(spans)}",
        "",
    ]
    for index, span in enumerate(spans[: max(1, min(limit, 50))], 1):
        line_range = format_line_range(span.line_start, span.line_end)
        char_range = (
            f"{span.char_start}-{span.char_end}"
            if span.char_start is not None and span.char_end is not None
            else "?"
        )
        quote = span.text[:500] + ("..." if len(span.text) > 500 else "")
        lines.extend(
            [
                f"## Span {index}: `{span.span_id}`",
                f"- **Kind:** {span.span_kind}",
                f"- **Block:** `{span.block_id}`",
                f"- **Page:** {span.page or '?'}",
                f"- **Lines:** {line_range or '?'}",
                f"- **Chars:** {char_range}",
                f"- **SHA256:** `{span.text_sha256}`",
                (
                    "- **CRAAP:** "
                    f"currency={span.craap.currency.status}, "
                    f"relevance={span.craap.relevance.status}, "
                    f"authority={span.craap.authority.status}, "
                    f"accuracy={span.craap.accuracy.status}, "
                    f"purpose={span.craap.purpose.status}"
                ),
                "",
                f"> {quote}",
                "",
                "AssetRef:",
                "```json",
                json.dumps(asset_ref_from_span(span), ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )

    if len(spans) > limit:
        lines.append(f"_...and {len(spans) - limit} more spans_")

    return "\n".join(lines)


@mcp.tool()
async def verify_citation_ref(ref: dict[str, Any]) -> str:
    """Verify a span-level AssetRef against the persisted citation index."""
    payload = _verify_span_ref_payload(ref, repository=repository)
    issues = payload.get("issues") or []
    doc_id = str(payload.get("doc_id") or ref.get("doc_id") or "")
    span_id = str(payload.get("span_id") or ref.get("span_id") or "")
    if payload.get("status") == "unsupported":
        return "❌ Only span-level AssetRef objects can be verified by this tool."
    if payload.get("status") == "invalid":
        return "❌ Citation ref must include doc_id and span_id."
    if payload.get("status") == "missing":
        return f"❌ Citation span not found: {span_id}"

    status = (
        "✅ Citation ref verified"
        if payload.get("valid")
        else "⚠️ Citation ref mismatch"
    )
    lines = [
        status,
        f"- **doc_id:** `{doc_id}`",
        f"- **span_id:** `{span_id}`",
        f"- **page:** {payload.get('page') or '?'}",
        f"- **lines:** {payload.get('line_display') or '?'}",
        f"- **char_range:** {payload.get('char_range', ['?', '?'])[0]}-{payload.get('char_range', ['?', '?'])[1]}",
        f"- **text_sha256:** `{payload.get('text_sha256', '')}`",
    ]
    if issues:
        lines.append(f"- **issues:** {', '.join(issues)}")
    return "\n".join(lines)


@mcp.tool()
async def citation_bundle(
    doc_id: str,
    query: str = "",
    span_id: str = "",
    span_kinds: list[str] | None = None,
    limit: int = 10,
    include_verification: bool = True,
    output_format: str = "markdown",
    citation_key: str = "",
    wiki_root: str = "",
    output_path: str = "",
    index_path: str = "",
    update_index: bool = True,
    overwrite: bool = False,
) -> Any:
    """
    Export citation-ready evidence spans as a verified bundle.

    Each entry carries AssetRef, exact quote/hash, locator metadata, context,
    conservative CRAAP scaffold, optional verification status, and Foam anchor
    metadata. Use output_format="foam" for a Foam-compatible evidence pack.
    Pass wiki_root to write the pack and optionally update an index note.
    """
    spans = load_or_build_evidence_spans(repository, doc_id)
    if not spans:
        status = load_citation_status(repository, doc_id) or {}
        reason = str(status.get("reason") or "").strip()
        error = (
            f"No citation-ready evidence spans found for doc_id: {doc_id}. {reason}"
            if reason
            else (
                f"Citation index not found for doc_id: {doc_id}. "
                "Run ingest_documents again or ensure blocks.json/full markdown exist."
            )
        )
        payload = {
            "success": False,
            "doc_id": doc_id,
            "bundle_version": "citation-bundle-v1",
            "error": error,
        }
        if output_format == "json":
            return payload
        return error

    filtered = _filter_evidence_spans(
        spans,
        query=query,
        span_id=span_id,
        span_kinds=span_kinds,
    )
    if not filtered:
        target = span_id or query
        payload = {
            "success": False,
            "doc_id": doc_id,
            "bundle_version": "citation-bundle-v1",
            "error": f"No evidence spans found for `{target}` in doc_id: {doc_id}",
        }
        if output_format == "json":
            return payload
        return str(payload["error"])

    bounded_limit = max(1, min(limit, 50))
    entries = [
        _citation_bundle_entry(
            span,
            include_verification=include_verification,
            repository=repository,
            asset_ref_factory=asset_ref_from_span,
            citation_key=citation_key,
        )
        for span in filtered[:bounded_limit]
    ]
    payload = {
        "success": True,
        "bundle_version": "citation-bundle-v1",
        "doc_id": doc_id,
        "query": query,
        "span_id": span_id,
        "span_kinds": span_kinds or [],
        "citation_key": citation_key,
        "matched_count": len(filtered),
        "returned": len(entries),
        "entries": entries,
    }
    if wiki_root or output_path:
        if output_format != "foam":
            return {
                "success": False,
                "doc_id": doc_id,
                "error": "Foam file writes require output_format='foam'",
            }
        try:
            return _write_foam_evidence_pack(
                payload,
                wiki_root=wiki_root,
                output_path=output_path,
                index_path=index_path,
                citation_key=citation_key,
                update_index=update_index,
                overwrite=overwrite,
            )
        except (FileExistsError, ValueError) as exc:
            return {"success": False, "doc_id": doc_id, "error": str(exc)}
    if output_format == "json":
        bounded_payload = _bounded_evidence_payload(payload)
        return format_limited_json_response(
            title=f"Citation Bundle: {doc_id}",
            payload=bounded_payload,
            guidance="write a Foam evidence pack to disk for full quotes",
        )
    if output_format == "foam":
        return format_limited_text_response(
            title=f"Foam Evidence Pack: {doc_id}",
            text=_format_foam_evidence_pack(payload),
            language="markdown",
            guidance="pass wiki_root/output_path to write the full evidence pack",
        )
    return _format_citation_bundle(payload)


async def _ingest_mixed_document_batch(
    file_paths: list[str],
    *,
    use_marker: bool = False,
    ocr_enabled: bool = False,
    ocr_language: str = "eng",
    rotate_pages: bool = False,
    deskew: bool = False,
    marker_max_pages_per_chunk: int = 0,
    extract_figures: bool = True,
    index_knowledge_graph: bool = False,
    page_ranges: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Ingest a mixed PDF + DOCX/DOC/ODT/ODS batch as one background job.

    Not a public MCP tool: `document(op="auto"/"ingest"/"import")` calls this
    automatically when `file_paths` contains anything other than PDFs, so
    agents get one job_id and one `get_job_status` progress stream for a
    heterogeneous batch without needing a separate tool name to remember.
    """
    await log_message(
        ctx,
        "info",
        f"ingest_mixed_document_batch start: files={len(file_paths)}",
    )
    await report_progress(ctx, 5, message="Queueing mixed-format ingest batch")

    handler = build_mixed_ingest_handler(
        file_paths,
        document_service=document_service,
        docx_service=docx_service,
        use_marker=use_marker,
        ocr_enabled=ocr_enabled,
        ocr_language=ocr_language,
        rotate_pages=rotate_pages,
        deskew=deskew,
        marker_max_pages_per_chunk=marker_max_pages_per_chunk,
        extract_figures=extract_figures,
        index_knowledge_graph=index_knowledge_graph,
        page_ranges=page_ranges,
    )

    try:
        job = await job_service.create_conversion_job(
            operation="ingest_mixed_batch",
            input_files=file_paths,
            parameters={"use_marker": use_marker, "ocr_enabled": ocr_enabled},
            handler=handler,
            total_steps=max(len(file_paths), 1),
            estimated_duration_seconds=len(file_paths) * 10,
        )
    except RuntimeError as e:
        await log_message(ctx, "error", f"ingest_mixed_document_batch rejected: {e}")
        return (
            "# ❌ Could Not Create Mixed-Format Ingest Job\n\n"
            f"{e!s}\n\n"
            "Use `list_jobs(active_only=True)` to inspect running work, then retry."
        )

    await report_progress(ctx, 100, message=f"Queued mixed ingest job {job.job_id}")
    await log_message(
        ctx, "info", f"ingest_mixed_document_batch job created: {job.job_id}"
    )

    counts = format_counts(file_paths)
    breakdown = ", ".join(f"{count} {fmt}" for fmt, count in sorted(counts.items()))
    return "\n".join(
        [
            "# Mixed-Format Ingest Job Created",
            "",
            "✅ Ingestion is running in the background.",
            f"- **job_id:** `{job.job_id}`",
            f"- **files:** {len(file_paths)} ({breakdown})",
            f"- **estimated_duration_seconds:** {job.estimated_duration_seconds}",
            "",
            f'Check progress with `get_job_status("{job.job_id}")`.',
        ]
    )


@mcp.tool()
async def ingest_documents(
    file_paths: list[str],
    async_mode: bool = True,
    use_marker: bool = False,
    ocr_enabled: bool = False,
    ocr_language: str = "eng",
    rotate_pages: bool = False,
    deskew: bool = False,
    marker_max_pages_per_chunk: int = 0,
    extract_figures: bool = True,
    index_knowledge_graph: bool = False,
    page_ranges: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """
    Process PDF files and create Document Manifests.

    ETL Pipeline:
    1. Extract text (to markdown) and images
    2. Generate structured Document Manifest
    3. Index in LightRAG (if enabled)

    Args:
        file_paths: List of absolute paths to PDF files
        async_mode: Kept for backwards compatibility. PDF ingestion is routed
                   to a background job from the MCP tool layer to keep stdio
                   clients responsive.
        use_marker: If True, use Marker for structured parsing (slower but more accurate).
                   Produces blocks.json with bbox/coordinates for precise source tracking.
                   Default False uses PyMuPDF (faster but less structured).
        marker_max_pages_per_chunk: When using Marker, split PDFs into fixed-size page chunks.
                                    Set 0 to use the safe automatic strategy.
        extract_figures: When using Marker, control whether image crops are extracted and saved.
                         Disable this first for image-heavy textbooks to reduce memory pressure.
        page_ranges: 1-indexed inclusive page ranges applied to every input file, e.g. ["1-50", "120-160"].

    Returns:
        Job ID for tracking progress with `get_job_status`.

    Example:
        # Async (recommended for large files):
        ingest_documents(["/papers/study1.pdf"])
        # Then check status:
        get_job_status("job_xxx")

        # With Marker for precise source tracking:
        ingest_documents(["/papers/textbook.pdf"], use_marker=True)
    """
    await log_message(
        ctx,
        "info",
        f"ingest_documents start: files={len(file_paths)} use_marker={use_marker} async_mode={async_mode}",
    )
    await report_progress(ctx, 5, message="Validating ingest request")

    if async_mode:
        return await _create_ingest_job_response(
            file_paths,
            use_marker=use_marker,
            ocr_enabled=ocr_enabled,
            ocr_language=ocr_language,
            rotate_pages=rotate_pages,
            deskew=deskew,
            marker_max_pages_per_chunk=marker_max_pages_per_chunk,
            extract_figures=extract_figures,
            index_knowledge_graph=index_knowledge_graph,
            page_ranges=page_ranges,
            ctx=ctx,
        )
    else:
        should_force, reason = _should_force_background_ingest(
            file_paths,
            use_marker=use_marker,
            ocr_enabled=ocr_enabled,
            page_ranges=page_ranges,
        )
        if should_force:
            await log_message(
                ctx,
                "warning",
                f"ingest_documents forcing background job: {reason}",
            )
            return await _create_ingest_job_response(
                file_paths,
                use_marker=use_marker,
                ocr_enabled=ocr_enabled,
                ocr_language=ocr_language,
                rotate_pages=rotate_pages,
                deskew=deskew,
                marker_max_pages_per_chunk=marker_max_pages_per_chunk,
                extract_figures=extract_figures,
                index_knowledge_graph=index_knowledge_graph,
                page_ranges=page_ranges,
                ctx=ctx,
                forced_reason=reason,
            )

        # Lazy-load Marker only for explicitly allowed synchronous Marker work.
        if use_marker and document_service.marker_extractor is None:
            try:
                document_service.marker_extractor = get_marker_extractor()
            except RuntimeError as e:
                return (
                    "# ❌ Marker Backend Not Available\n\n"
                    f"{e!s}\n\n"
                    "Use default PyMuPDF mode, or install the optional Marker dependency first."
                )

        await report_progress(ctx, 15, message="Starting synchronous ingestion")
        results = await document_service.ingest(
            file_paths,
            use_marker=use_marker,
            progress_callback=create_subrange_progress_callback(ctx, 15, 95),
            ocr_enabled=ocr_enabled,
            ocr_language=ocr_language,
            rotate_pages=rotate_pages,
            deskew=deskew,
            marker_max_pages_per_chunk=marker_max_pages_per_chunk,
            extract_figures=extract_figures,
            index_knowledge_graph=index_knowledge_graph,
            page_ranges=page_ranges,
        )
        await report_progress(ctx, 100, message="Synchronous ingestion finished")
        await log_message(ctx, "info", "ingest_documents sync completed")

        backend_label = "Marker" if use_marker else "PyMuPDF"
        output_lines = [f"# Ingestion Results ({backend_label})\n"]
        success_count = sum(1 for r in results if r.success)
        output_lines.append(f"**Processed:** {success_count}/{len(results)} files\n")
        if ocr_enabled:
            output_lines.append(
                f"**OCR:** enabled ({ocr_language}, rotate_pages={rotate_pages}, deskew={deskew})\n"
            )
        if use_marker:
            output_lines.append(
                f"**Marker chunk size:** {marker_max_pages_per_chunk or 'auto'}\n"
            )
            output_lines.append(
                f"**Extract figures:** {'yes' if extract_figures else 'no'}\n"
            )
        if page_ranges:
            output_lines.append(f"**Page ranges:** {', '.join(page_ranges)}\n")

        for result in results:
            if result.success:
                output_lines.append(f"\n## ✅ {result.filename}")
                output_lines.append(f"- **doc_id:** `{result.doc_id}`")
                output_lines.append(f"- **title:** {result.title or 'N/A'}")
                output_lines.append(f"- **backend:** {result.backend}")
                output_lines.append(f"- **pages:** {result.pages_processed}")
                output_lines.append(f"- **tables:** {result.tables_found}")
                output_lines.append(f"- **figures:** {result.figures_found}")
                output_lines.append(f"- **sections:** {result.sections_found}")
                output_lines.append(
                    f"- **time:** {result.processing_time_seconds:.2f}s"
                )
                if is_structured_engine(result.backend):
                    output_lines.append("- **blocks.json:** ✅ Created")
                for warning in result.warnings:
                    output_lines.append(f"- **warning:** {warning}")
            else:
                output_lines.append(f"\n## ❌ {result.filename}")
                output_lines.append(f"- **error:** {result.error}")

        return "\n".join(output_lines)


@mcp.tool()
async def list_documents() -> str:
    """
    List all processed documents with summaries.

    Returns:
        List of documents with doc_id, title, and asset counts
    """
    documents = await document_service.list_documents()

    if not documents:
        return "No documents found. Use `ingest_documents` to process PDF files."

    output_lines = [f"# Documents ({len(documents)} total)\n"]

    for doc in documents:
        output_lines.append(f"## {doc.title or doc.filename}")
        output_lines.append(f"- **doc_id:** `{doc.doc_id}`")
        output_lines.append(f"- **filename:** {doc.filename}")
        output_lines.append(f"- **tables:** {doc.table_count}")
        output_lines.append(f"- **figures:** {doc.figure_count}")
        output_lines.append(f"- **sections:** {doc.section_count}")
        output_lines.append(f"- **text_quality:** {doc.text_quality_status}")
        if doc.ocr_recommended:
            output_lines.append("- **ocr_recommended:** yes")
        output_lines.append(f"- **ingested:** {doc.ingested_at}")
        output_lines.extend(_format_next_actions(doc.doc_id))
        output_lines.append("")

    return format_limited_text_response(
        title="Documents List",
        text="\n".join(output_lines),
        language="markdown",
        guidance="inspect a specific document manifest for details",
    )


@mcp.tool()
async def delete_document(doc_id: str) -> str:
    """
    刪除已攝入的 PDF 文件及其本地 artifacts。

    會移除 data/{doc_id}/ 下的 manifest、markdown、images、blocks.json 等檔案。
    若啟用了 LightRAG，會一併嘗試刪除對應的知識圖譜文件索引。
    """
    result = await document_service.delete_document(doc_id)
    if not result.get("success"):
        return f"❌ 刪除失敗：{result.get('error', '未知錯誤')}"

    lines = [
        "✅ PDF 文件已刪除",
        f"- **doc_id**: `{result.get('doc_id', '')}`",
        f"- **filename**: {result.get('filename', '')}",
    ]
    if "knowledge_graph_status" in result:
        lines.append(
            f"- **knowledge_graph**: {result.get('knowledge_graph_status', 'unknown')}"
        )
    for warning in result.get("warnings", []):
        lines.append(f"- **warning**: {warning}")
    return "\n".join(lines)


@mcp.tool()
async def convert_pdf_to_docx(
    doc_id: str,
    output_path: str | None = None,
    mode: str = "content",
    async_mode: bool = True,
    ctx: Context | None = None,
) -> str:
    """
    將已攝入的 PDF 文件轉為 DOCX。

    轉換範圍：
    - `content`：內容層重建。根據 PDF ETL 的 Markdown/表格/圖片生成可讀 DOCX。
    - `fidelity`：目前不支援，因為 PDF ETL 並非版面可逆。
    - `async_mode`：預設建立背景 conversion job；設為 False 可沿用同步回傳。
    """
    await log_message(ctx, "info", f"convert_pdf_to_docx start: {doc_id}")
    if async_mode:
        parameters = {
            "operation": "pdf_to_docx",
            "source": doc_id,
            "target_format": "docx",
            "output_path": output_path,
            "mode": mode,
        }

        async def handler(progress: Any) -> dict[str, Any]:
            await progress.report(
                step=2,
                phase="Converting",
                message=f"Converting {doc_id} to DOCX",
            )
            result = await document_service.convert_pdf_to_docx(
                doc_id,
                output_path,
                mode=mode,
            )
            await progress.report(
                step=3,
                phase="Packaging",
                message=f"Finalizing DOCX conversion for {doc_id}",
            )
            return conversion_result_payload(
                result,
                operation="pdf_to_docx",
                source=doc_id,
                target_format="docx",
            )

        return await create_conversion_job_response(
            job_service,
            operation="pdf_to_docx",
            source=doc_id,
            target_format="docx",
            parameters=parameters,
            handler=handler,
            ctx=ctx,
        )

    await report_progress(ctx, 10, message=f"Converting {doc_id} to DOCX")
    result = await document_service.convert_pdf_to_docx(
        doc_id,
        output_path,
        mode=mode,
    )
    if not result.get("success"):
        await log_message(ctx, "error", f"convert_pdf_to_docx failed: {doc_id}")
        return f"❌ 轉換失敗：{result.get('error', '未知錯誤')}"

    await report_progress(ctx, 100, message=f"Finished DOCX conversion for {doc_id}")
    await log_message(ctx, "info", f"convert_pdf_to_docx complete: {doc_id}")

    return "\n".join(
        [
            "✅ PDF → DOCX 轉換成功",
            f"- **doc_id**: `{result.get('doc_id', '')}`",
            f"- **mode**: {result.get('mode', mode)}",
            f"- **output_path**: `{result.get('output_path', '')}`",
            f"- **figures_embedded**: {result.get('figures_embedded', 0)}",
            f"- **tables_found**: {result.get('tables_found', 0)}",
        ]
    )


@mcp.tool()
async def convert_pdf_to_pptx(
    doc_id: str,
    output_path: str | None = None,
    mode: str = "content",
    async_mode: bool = True,
    ctx: Context | None = None,
) -> str:
    """
    將已攝入的 PDF 文件轉為 PPTX。

    轉換範圍：
    - `content`：依據 PDF ETL 的 Markdown/圖像生成可編輯投影片。
    - `async_mode`：預設建立背景 conversion job；設為 False 可沿用同步回傳。
    """
    await log_message(ctx, "info", f"convert_pdf_to_pptx start: {doc_id}")
    if async_mode:
        parameters = {
            "operation": "pdf_to_pptx",
            "source": doc_id,
            "target_format": "pptx",
            "output_path": output_path,
            "mode": mode,
        }

        async def handler(progress: Any) -> dict[str, Any]:
            await progress.report(
                step=2,
                phase="Converting",
                message=f"Converting {doc_id} to PPTX",
            )
            result = await document_service.convert_pdf_to_pptx(
                doc_id,
                output_path,
                mode=mode,
            )
            await progress.report(
                step=3,
                phase="Packaging",
                message=f"Finalizing PPTX conversion for {doc_id}",
            )
            return conversion_result_payload(
                result,
                operation="pdf_to_pptx",
                source=doc_id,
                target_format="pptx",
            )

        return await create_conversion_job_response(
            job_service,
            operation="pdf_to_pptx",
            source=doc_id,
            target_format="pptx",
            parameters=parameters,
            handler=handler,
            ctx=ctx,
        )

    await report_progress(ctx, 10, message=f"Converting {doc_id} to PPTX")
    result = await document_service.convert_pdf_to_pptx(
        doc_id,
        output_path,
        mode=mode,
    )
    if not result.get("success"):
        await log_message(ctx, "error", f"convert_pdf_to_pptx failed: {doc_id}")
        return f"❌ 轉換失敗：{result.get('error', '未知錯誤')}"

    await report_progress(ctx, 100, message=f"Finished PPTX conversion for {doc_id}")
    await log_message(ctx, "info", f"convert_pdf_to_pptx complete: {doc_id}")

    return "\n".join(
        [
            "✅ PDF → PPTX 轉換成功",
            f"- **doc_id**: `{result.get('doc_id', '')}`",
            f"- **mode**: {result.get('mode', mode)}",
            f"- **output_path**: `{result.get('output_path', '')}`",
            f"- **slides_created**: {result.get('slides_created', 0)}",
            f"- **figure_slides**: {result.get('figure_slides', 0)}",
        ]
    )


@mcp.tool()
async def inspect_document_manifest(doc_id: str) -> str:
    """
    Get detailed Document Manifest for precise asset retrieval.

    The manifest contains:
    - Document metadata (title, pages, etc.)
    - Tables list with IDs and descriptions
    - Figures list with IDs, page numbers, and dimensions
    - Sections list with IDs and titles
    - LightRAG entities (if indexed)

    Use this to discover available assets before fetching.

    Args:
        doc_id: Document identifier from ingest_documents or list_documents

    Returns:
        Structured manifest in markdown format
    """
    manifest = await document_service.get_manifest(doc_id)

    if not manifest:
        return f"Document not found: `{doc_id}`"

    output_lines = [f"# Document Manifest: {manifest.title or manifest.filename}\n"]
    output_lines.append(f"**doc_id:** `{manifest.doc_id}`")
    output_lines.append(f"**pages:** {manifest.page_count}")
    output_lines.append(f"**text_quality:** {manifest.text_quality_status}")
    output_lines.append(f"**visible_text_chars:** {manifest.visible_text_chars}")
    output_lines.append(f"**visible_text_lines:** {manifest.visible_text_lines}")
    output_lines.append(f"**repeated_line_ratio:** {manifest.repeated_line_ratio:.2f}")
    output_lines.append(
        f"**ocr_recommended:** {'yes' if manifest.ocr_recommended else 'no'}"
    )
    if manifest.text_quality_reason:
        output_lines.append(f"**text_quality_reason:** {manifest.text_quality_reason}")
    output_lines.append(f"**source_engine:** {manifest.source_engine}")
    output_lines.append(f"**ingested:** {manifest.ingested_at}")

    # Tables section
    output_lines.append(f"\n## Tables ({len(manifest.assets.tables)})")
    if manifest.assets.tables:
        for table in manifest.assets.tables:
            output_lines.append(f"\n### `{table.id}` (page {table.page})")
            output_lines.append(f"_{table.caption}_")
            output_lines.append(f"Rows: {table.row_count}, Cols: {table.col_count}")
    else:
        output_lines.append("_No tables found_")

    # Figures section
    output_lines.append(f"\n## Figures ({len(manifest.assets.figures)})")
    if manifest.assets.figures:
        for fig in manifest.assets.figures:
            output_lines.append(f"\n### `{fig.id}` (page {fig.page})")
            if fig.caption:
                output_lines.append(f"_{fig.caption}_")
            output_lines.append(f"Size: {fig.width}×{fig.height} ({fig.ext})")
    else:
        output_lines.append("_No figures found_")

    # Sections section
    output_lines.append(f"\n## Sections ({len(manifest.assets.sections)})")
    if manifest.assets.sections:
        for sec in manifest.assets.sections:
            indent = "  " * (sec.level - 1) if sec.level > 1 else ""
            output_lines.append(
                f"{indent}- `{sec.id}`: {sec.title} ({display_line_range(sec.start_line, sec.end_line)})"
            )
    else:
        output_lines.append("_No sections found_")

    # LightRAG entities
    if manifest.lightrag_entities:
        output_lines.append(
            f"\n## Knowledge Graph Entities ({len(manifest.lightrag_entities)})"
        )
        output_lines.append(", ".join(manifest.lightrag_entities[:20]))
        if len(manifest.lightrag_entities) > 20:
            output_lines.append(f"... and {len(manifest.lightrag_entities) - 20} more")

    output_lines.extend(["", "## Next Actions"])
    output_lines.extend(_format_next_actions(doc_id))

    return format_limited_text_response(
        title=f"Document Manifest: {doc_id}",
        text="\n".join(output_lines),
        source_path=manifest.manifest_path,
        language="markdown",
        guidance="use document resources or fetch specific assets by id",
    )


@mcp.tool()
async def export_document_segmentation(
    doc_id: str,
    page: int | None = None,
    limit: int | None = None,
    output_path: str | None = None,
    ctx: Context | None = None,
) -> str:
    """匯出整合 manifest、blocks、assets、reading order 的 segmentation schema。"""
    await log_message(ctx, "info", f"export_document_segmentation start: {doc_id}")
    await report_progress(ctx, 10, message=f"Loading manifest for {doc_id}")

    (
        target,
        segmentation,
    ) = await segmentation_service.build_and_save_document_segmentation(
        doc_id,
        output_path=output_path,
        page=page,
        limit=limit,
    )

    await report_progress(ctx, 100, message=f"Segmentation exported for {doc_id}")
    await log_message(ctx, "info", f"export_document_segmentation complete: {doc_id}")

    summary_lines = [
        "# Unified Segmentation Export",
        "",
        f"**doc_id:** `{segmentation.doc_id}`",
        f"**backend:** {segmentation.source_backend}",
        f"**reading_order_policy:** {segmentation.reading_order_policy}",
        f"**segments:** {len(segmentation.segments)}",
        f"**pages:** {segmentation.page_count}",
        f"**output:** `{target}`",
        "",
        "## Segment Counts by Page",
    ]
    for page_number, count in segmentation.page_count_summary().items():
        summary_lines.append(f"- Page {page_number}: {count}")

    preview_segments = segmentation.segments[:5]
    if preview_segments:
        summary_lines.extend(["", "## Preview"])
        for segment in preview_segments:
            summary_lines.append(
                f"- #{segment.reading_order} P{segment.page_number} {segment.segment_type}"
                f" [{segment.segment_id}]"
            )

    return "\n".join(summary_lines)


@mcp.tool()
async def visualize_document_layout(
    doc_id: str,
    page: int = 1,
    show_labels: bool = True,
    include_reading_order: bool = True,
    output_path: str | None = None,
    ctx: Context | None = None,
) -> list[TextContent | ImageContent]:
    """產生 PDF page overlay，直接檢查 block bbox、類型與 reading order。"""
    await log_message(
        ctx, "info", f"visualize_document_layout start: {doc_id} page={page}"
    )
    await report_progress(
        ctx, 10, message=f"Loading segmentation for {doc_id} page {page}"
    )

    segmentation = await segmentation_service.export_document_segmentation(
        doc_id, page=page
    )
    await report_progress(
        ctx, 55, message=f"Rendering layout overlay for {doc_id} page {page}"
    )
    doc_dir = repository.get_doc_dir(doc_id)
    safe_output_path = None
    if output_path:
        try:
            safe_output_path = str(
                resolve_document_output_path(
                    doc_dir,
                    output_path,
                    default_name=f"layout_page_{page}.png",
                    allowed_suffixes={".png"},
                )
            )
        except ValueError as e:
            return [TextContent(type="text", text=f"❌ {e!s}")]
    overlay = layout_visualizer.render_page_overlay(
        doc_dir,
        segmentation,
        page,
        show_labels=show_labels,
        include_reading_order=include_reading_order,
        output_path=safe_output_path,
    )

    await report_progress(
        ctx, 100, message=f"Layout overlay ready for {doc_id} page {page}"
    )
    await log_message(
        ctx, "info", f"visualize_document_layout complete: {doc_id} page={page}"
    )

    summary = [
        f"## Layout Overlay: {doc_id}",
        f"**Page:** {page}",
        f"**Segments:** {len(segmentation.segments)}",
        f"**Image Size:** {overlay.width}×{overlay.height}",
    ]
    if overlay.output_path:
        summary.append(f"**Saved To:** {overlay.output_path}")

    if image_exceeds_response_limit(overlay.image_base64):
        summary.extend(
            [
                "",
                format_omitted_image_response(
                    title=f"Layout Overlay: {doc_id}/page-{page}",
                    data=overlay.image_base64,
                    mime_type="image/png",
                    source_path=overlay.output_path,
                    guidance="pass output_path to persist the overlay, or reduce page/image size",
                ),
            ]
        )
        return [TextContent(type="text", text="\n".join(summary))]

    return [
        TextContent(type="text", text="\n".join(summary)),
        ImageContent(type="image", data=overlay.image_base64, mimeType="image/png"),
    ]


async def _export_pdf_ai_safety_report(
    doc_id: str,
    output_path: str | None = None,
    ctx: Context | None = None,
) -> str:
    await log_message(ctx, "info", f"pdf ai safety audit start: {doc_id}")
    await report_progress(ctx, 10, message=f"Auditing PDF safety for {doc_id}")
    try:
        target, report = pdf_report_service.build_and_save_ai_safety_report(
            doc_id,
            output_path=output_path,
        )
    except Exception as exc:
        return f"??{exc!s}"
    await report_progress(ctx, 100, message=f"PDF safety audit exported for {doc_id}")
    return _format_json_artifact_summary(
        title="PDF AI Safety Audit",
        doc_id=doc_id,
        target=target,
        report=report,
        preview_key="",
    )


async def _export_pdf_native_structure_report(
    doc_id: str,
    output_path: str | None = None,
    ctx: Context | None = None,
) -> str:
    await log_message(ctx, "info", f"pdf native structure audit start: {doc_id}")
    await report_progress(
        ctx, 10, message=f"Extracting native PDF structure for {doc_id}"
    )
    try:
        target, report = pdf_report_service.build_and_save_native_structure_report(
            doc_id,
            output_path=output_path,
        )
    except Exception as exc:
        return f"??{exc!s}"
    await report_progress(
        ctx, 100, message=f"Native PDF structure exported for {doc_id}"
    )
    return _format_json_artifact_summary(
        title="Native PDF Structure",
        doc_id=doc_id,
        target=target,
        report=report,
        preview_key="outline",
    )


async def _export_segmentation_coverage_report(
    doc_id: str,
    output_path: str | None = None,
    ctx: Context | None = None,
) -> str:
    await log_message(ctx, "info", f"segmentation coverage audit start: {doc_id}")
    await report_progress(
        ctx, 10, message=f"Measuring segmentation coverage for {doc_id}"
    )
    try:
        (
            target,
            report,
        ) = await pdf_report_service.build_and_save_segmentation_coverage_report(
            doc_id,
            segmentation_service,
            output_path=output_path,
        )
    except Exception as exc:
        return f"??{exc!s}"
    await report_progress(ctx, 100, message=f"Coverage audit exported for {doc_id}")
    return _format_json_artifact_summary(
        title="Segmentation Coverage Audit",
        doc_id=doc_id,
        target=target,
        report=report,
        preview_key="issues",
    )


async def _export_pdf_accessibility_report(
    doc_id: str,
    output_path: str | None = None,
    ctx: Context | None = None,
) -> str:
    await log_message(ctx, "info", f"pdf accessibility audit start: {doc_id}")
    await report_progress(
        ctx, 10, message=f"Measuring accessibility readiness for {doc_id}"
    )
    try:
        target, report = await pdf_report_service.build_and_save_accessibility_report(
            doc_id,
            segmentation_service,
            output_path=output_path,
        )
    except Exception as exc:
        return f"??{exc!s}"
    await report_progress(
        ctx, 100, message=f"Accessibility report exported for {doc_id}"
    )
    return _format_json_artifact_summary(
        title="PDF Accessibility Readiness",
        doc_id=doc_id,
        target=target,
        report=report,
        preview_key="issues",
    )


async def _build_structural_pointer_index(
    doc_id: str,
    output_path: str | None = None,
    ctx: Context | None = None,
) -> str:
    await log_message(ctx, "info", f"structural pointer index start: {doc_id}")
    await report_progress(
        ctx, 10, message=f"Building structural pointer index for {doc_id}"
    )
    try:
        target, report = await structural_pointer_service.build_and_save_pointer_index(
            doc_id,
            output_path=output_path,
        )
    except Exception as exc:
        return f"??{exc!s}"
    await report_progress(
        ctx, 100, message=f"Structural pointer index exported for {doc_id}"
    )
    return _format_json_artifact_summary(
        title="Structural Pointer Index",
        doc_id=doc_id,
        target=target,
        report=report,
        preview_key="preview",
    )


async def _structural_retrieve(
    doc_id: str,
    query: str,
    *,
    limit: int | None = None,
    refresh: bool = False,
    ctx: Context | None = None,
) -> Any:
    if not query.strip():
        return '??`query` is required for document(op="structural_retrieve").'
    await log_message(ctx, "info", f"structural retrieve start: {doc_id}")
    await report_progress(ctx, 10, message=f"Searching section pointers for {doc_id}")
    try:
        payload = await structural_pointer_service.retrieve(
            doc_id,
            query,
            limit=limit or 5,
            refresh=refresh,
        )
    except Exception as exc:
        return f"??{exc!s}"
    await report_progress(
        ctx, 100, message=f"Structural retrieval complete for {doc_id}"
    )
    return format_limited_json_response(
        title=f"Structural Retrieval: {doc_id}",
        payload=payload,
        guidance="use evidence(op='find') on returned evidence_span_ids for exact quotes",
    )


async def _compare_documents_structural(
    doc_id: str,
    doc_b_id: str,
    *,
    criteria: str,
    output_path: str | None = None,
    limit: int | None = None,
    refresh: bool = False,
    ctx: Context | None = None,
) -> str:
    await log_message(ctx, "info", f"document comparison start: {doc_id} vs {doc_b_id}")
    await report_progress(
        ctx, 10, message=f"Comparing structural pointers: {doc_id} vs {doc_b_id}"
    )
    try:
        (
            target,
            bundle,
        ) = await structural_pointer_service.build_and_save_comparison_bundle(
            doc_id,
            doc_b_id,
            criteria=criteria,
            output_path=output_path,
            max_sections=limit or 10,
            refresh=refresh,
        )
    except Exception as exc:
        return f"??{exc!s}"
    await report_progress(ctx, 100, message="Document comparison bundle exported")
    return _format_json_artifact_summary(
        title="Document Structural Comparison",
        doc_id=doc_id,
        target=target,
        report=bundle,
        preview_key="pairs",
    )


def _format_json_artifact_summary(
    *,
    title: str,
    doc_id: str,
    target: Path,
    report: dict[str, Any],
    preview_key: str,
) -> str:
    lines = [
        f"# {title}",
        "",
        f"**doc_id:** `{doc_id}`",
        f"**status:** {report.get('status', 'ok')}",
        f"**schema:** {report.get('schema_version', '')}",
        f"**output:** `{target}`",
    ]
    summary = report.get("summary")
    if isinstance(summary, dict):
        lines.extend(["", "## Summary"])
        for key, value in summary.items():
            if isinstance(value, (dict, list)):
                value = _bounded_inline_json(value)
            lines.append(f"- **{key}:** {value}")
    metrics = report.get("metrics")
    if isinstance(metrics, dict):
        lines.extend(["", "## Metrics"])
        for key, value in metrics.items():
            if isinstance(value, (dict, list)):
                value = _bounded_inline_json(value)
            lines.append(f"- **{key}:** {value}")
    preview = report.get(preview_key)
    if isinstance(preview, list) and preview:
        lines.extend(["", "## Preview"])
        for item in preview[:5]:
            lines.append(f"- `{_bounded_inline_json(item)}`")
        if len(preview) > 5:
            lines.append(f"- ... {len(preview) - 5} more")
    return "\n".join(lines)


def _bounded_inline_json(
    value: Any,
    *,
    max_chars: int = JSON_ARTIFACT_INLINE_MAX_CHARS,
) -> str:
    bounded = _bound_inline_json_value(value)
    raw = json.dumps(bounded, ensure_ascii=False, default=str)
    if len(raw) <= max_chars:
        return raw
    summary = {
        "response_truncated": True,
        "content_chars": len(raw),
        "sha256": text_sha256(raw),
        "preview": raw[:max_chars],
    }
    return json.dumps(summary, ensure_ascii=False, default=str)


def _bound_inline_json_value(
    value: Any,
    *,
    depth: int = 0,
    max_depth: int = 4,
    max_items: int = 25,
    max_string_chars: int = 1_000,
) -> Any:
    if isinstance(value, str):
        if len(value) <= max_string_chars:
            return value
        return {
            "text_truncated": True,
            "chars": len(value),
            "sha256": text_sha256(value),
            "preview": value[:max_string_chars],
        }
    if depth >= max_depth:
        return str(type(value).__name__)
    if isinstance(value, dict):
        items = list(value.items())
        bounded = {
            str(key): _bound_inline_json_value(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                max_items=max_items,
                max_string_chars=max_string_chars,
            )
            for key, item in items[:max_items]
        }
        if len(items) > max_items:
            bounded["_omitted_items"] = len(items) - max_items
        return bounded
    if isinstance(value, list | tuple):
        bounded_items = [
            _bound_inline_json_value(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                max_items=max_items,
                max_string_chars=max_string_chars,
            )
            for item in list(value)[:max_items]
        ]
        if len(value) > max_items:
            bounded_items.append({"_omitted_items": len(value) - max_items})
        return bounded_items
    return value


def _readiness_service() -> DocumentReadinessService:
    return DocumentReadinessService(repository)


def _facade_next_actions(
    doc_id: str,
    *,
    capabilities: dict[str, bool] | None = None,
    ocr_recommended: bool = False,
) -> list[str]:
    actions = [f'document(op="inspect", doc_id="{doc_id}")']
    if capabilities is None or not all(
        capabilities.get(name, False)
        for name in (
            "has_ai_safety_report",
            "has_native_structure",
            "has_coverage_report",
            "has_accessibility_report",
        )
    ):
        actions.append(f'document(op="audit", doc_id="{doc_id}")')
    actions.append(f'document(op="prepare_ai", doc_id="{doc_id}")')
    if capabilities is None or not capabilities.get("has_section_pointer_index", False):
        actions.append(f'document(op="pointer_index", doc_id="{doc_id}")')
    if capabilities is None or not capabilities.get("has_segmentation", False):
        actions.append(f'document(op="export_segmentation", doc_id="{doc_id}")')
    actions.append(f'document_asset(op="tree", doc_id="{doc_id}")')
    actions.append(f'evidence(op="find", doc_id="{doc_id}", query="...")')
    if ocr_recommended:
        actions.append('document(op="ocr", pdf_path="...")')
    return actions


def _format_next_actions(doc_id: str) -> list[str]:
    return [f"- **next:** `{action}`" for action in _facade_next_actions(doc_id)]


def _audit_report_failed(report_text: str) -> bool:
    stripped = report_text.lstrip()
    lowered = stripped.lower()
    if stripped.startswith("??") or lowered.startswith("error:"):
        return True
    failed_statuses = ("unavailable", "skipped", "failed", "error")
    return any(f"**status:** {status}" in lowered for status in failed_statuses)


async def _run_document_readiness_audit(
    doc_id: str,
    output_path: str | None = None,
    ctx: Context | None = None,
    refresh: bool = False,
) -> str:
    if output_path:
        return (
            'document(op="audit") writes multiple reports; omit output_path or '
            "run a specific audit op with output_path."
        )

    readiness = _readiness_service().build_payload(doc_id)
    missing_audits = set(readiness.get("missing_audits", []))
    invalid_audits = set(readiness.get("invalid_audits", []))
    audits_to_run = (
        set(AI_READINESS_REQUIRED_AUDITS)
        if refresh
        else set(missing_audits).union(invalid_audits)
    )
    artifacts = {
        str(name): str(path)
        for name, path in readiness.get("artifacts", {}).items()
        if path
    }
    audit_steps = [
        ("ai_safety_report", "PDF AI Safety Audit", _export_pdf_ai_safety_report),
        (
            "native_structure",
            "Native PDF Structure",
            _export_pdf_native_structure_report,
        ),
        (
            "segmentation_coverage",
            "Segmentation Coverage Audit",
            _export_segmentation_coverage_report,
        ),
        (
            "accessibility_report",
            "PDF Accessibility Readiness",
            _export_pdf_accessibility_report,
        ),
    ]
    report_sections: list[tuple[str, str]] = []
    for name, title, runner in audit_steps:
        if name not in audits_to_run:
            cached_path = artifacts.get(name, "")
            cached_line = f"- {name}: cached"
            if cached_path:
                cached_line = f"{cached_line} `{cached_path}`"
            report_sections.append((name, f"## {title}\n\n{cached_line}"))
            continue
        report_sections.append(
            (
                name,
                await runner(
                    doc_id=doc_id,
                    output_path=None,
                    ctx=ctx,
                ),
            )
        )
    failed_reports = [
        name
        for name, report_text in report_sections
        if _audit_report_failed(report_text)
    ]
    status = "cached" if not audits_to_run else "warning" if failed_reports else "ok"
    sections = [
        "# Document AI Readiness Audit",
        "",
        f"**doc_id:** `{doc_id}`",
        f"**status:** {status}",
    ]
    if failed_reports:
        sections.extend(
            [
                "",
                "## Failed Reports",
                f"- failed_reports: {', '.join(failed_reports)}",
            ]
        )
    sections.extend(report_text for _name, report_text in report_sections)
    sections.extend(["", "## Next Actions"])
    sections.extend(f"- `{action}`" for action in _facade_next_actions(doc_id))
    return format_limited_text_response(
        title=f"Document AI Readiness Audit: {doc_id}",
        text="\n\n".join(sections),
        language="markdown",
        guidance='use document(op="prepare_ai", doc_id=...) for a compact readiness state',
    )


async def _prepare_document_for_ai(
    doc_id: str,
    ctx: Context | None = None,
    output_format: str = "markdown",
) -> Any:
    del ctx
    readiness_payload = _readiness_service().build_payload(doc_id)
    if _normalize_op(output_format) == "json":
        return readiness_payload

    capabilities = readiness_payload["capabilities"]
    artifacts = readiness_payload["artifacts"]
    blockers = readiness_payload["blockers"]
    warnings = readiness_payload["warnings"]
    lines = [
        "# Document AI Readiness",
        "",
        f"**doc_id:** `{doc_id}`",
        f"**status:** {readiness_payload['status']}",
        f"**text_quality:** {readiness_payload['text_quality']}",
        f"**ocr_recommended:** {'yes' if readiness_payload['ocr_recommended'] else 'no'}",
        "",
        "## Capabilities",
    ]
    for name, enabled in capabilities.items():
        lines.append(f"- {name}: {'yes' if enabled else 'no'}")

    lines.extend(["", "## Artifacts"])
    for name, _template in AI_READINESS_ARTIFACTS:
        path = artifacts.get(name)
        if path:
            lines.append(f"- {name}: `{path}`")
        else:
            lines.append(f"- {name}: missing")

    if blockers:
        lines.extend(["", "## Blockers"])
        lines.extend(f"- {blocker}" for blocker in blockers)

    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)

    lines.extend(["", "## Next Actions"])
    next_actions = readiness_payload["next_actions"]
    lines.extend(f"- `{action}`" for action in next_actions)
    lines.extend(
        [
            "",
            "## Readiness JSON",
            "```json",
            json.dumps(readiness_payload, ensure_ascii=False, indent=2),
            "```",
        ]
    )
    source_path = artifacts.get("manifest")
    return format_limited_text_response(
        title=f"Document AI Readiness: {doc_id}",
        text="\n".join(lines),
        source_path=source_path,
        language="markdown",
        guidance='run document(op="audit", doc_id=...) to generate missing readiness artifacts',
    )


@mcp.tool()
async def ocr_pdf_document(
    pdf_path: str,
    output_path: str | None = None,
    language: str = "eng",
    rotate_pages: bool = False,
    deskew: bool = False,
    ctx: Context | None = None,
) -> str:
    """Create a background OCR ingest job instead of blocking the MCP request."""
    pdf_file = Path(pdf_path)
    await log_message(ctx, "info", f"ocr_pdf_document start: {pdf_path}")
    await report_progress(ctx, 10, message=f"Creating OCR job for {pdf_file.name}")

    if not pdf_file.exists():
        return f"❌ File not found: {pdf_path}"

    response = await _create_ingest_job_response(
        [pdf_path],
        use_marker=False,
        ocr_enabled=True,
        ocr_language=language,
        rotate_pages=rotate_pages,
        deskew=deskew,
        marker_max_pages_per_chunk=0,
        extract_figures=True,
        index_knowledge_graph=False,
        page_ranges=None,
        ctx=ctx,
        forced_reason=(
            "OCR preprocessing can spawn long-running OCR engines, so it is "
            "always routed through the background job system"
        ),
        title="OCR Job Created",
        operation="ocr_pdf_document",
    )
    if output_path:
        response += (
            "\n\n**Note:** `output_path` is ignored for background OCR; the OCR "
            "artifact is saved as `ocr_processed.pdf` inside the created document "
            "artifact directory."
        )
    return response


@mcp.tool()
async def fetch_document_asset(
    doc_id: str,
    asset_type: str,
    asset_id: str = "full",
    max_size: int | None = None,
    max_chars: int | None = None,
    ctx: Context | None = None,
) -> list[TextContent | ImageContent]:
    """
    Fetch specific content from a document with precision.

    Asset Types:
    - "table": Returns table as markdown (with page number)
    - "figure": Returns image as base64 with page number for verification
    - "section": Returns section text content
    - "full_text": Returns entire document as markdown

    Args:
        doc_id: Document identifier
        asset_type: One of "table", "figure", "section", "full_text"
        asset_id: Asset ID from manifest (e.g., "tab_1", "fig_1_1", "sec_methods")
                  Use "full" for full_text type
        max_size: Maximum image dimension (longest edge) for figures.
                  - None (default): Use default 1024px
                  - 0: Return original size (no resize)
                  - N: Resize to Npx longest edge (e.g., 512, 768, 2048)

    Returns:
        For figures: ImageContent that vision AI can directly analyze
        For others: TextContent in markdown format

    Example:
        # Get Table 1 from document
        fetch_document_asset("abc123", "table", "tab_1")

        # Get figure with default resize (1024px)
        fetch_document_asset("abc123", "figure", "fig_2_1")

        # Get figure at specific size (512px for smaller context)
        fetch_document_asset("abc123", "figure", "fig_2_1", max_size=512)

        # Get original image (no resize)
        fetch_document_asset("abc123", "figure", "fig_2_1", max_size=0)
    """
    await log_message(
        ctx, "info", f"fetch_document_asset start: {doc_id} {asset_type}:{asset_id}"
    )
    await report_progress(
        ctx, 10, message=f"Fetching {asset_type} {asset_id} from {doc_id}"
    )
    result = await asset_service.fetch_asset(
        doc_id, asset_type, asset_id, max_size=max_size
    )

    if not result.success:
        await log_message(ctx, "error", f"fetch_document_asset failed: {result.error}")
        return [TextContent(type="text", text=f"Error: {result.error}")]

    if result.image_base64:
        await report_progress(
            ctx, 100, message=f"Fetched {asset_type} {asset_id} from {doc_id}"
        )
        source_path = None
        try:
            manifest = repository.load_manifest(doc_id)
            figure = manifest.assets.find_figure(asset_id) if manifest else None
            source_path = getattr(figure, "path", None) if figure else None
        except Exception:
            source_path = None
        metadata_lines = [
            f"## Figure: {result.asset_id}",
            f"**Page:** {result.page or 'Unknown'}",
            f"**Size:** {result.width}×{result.height}",
            f"**Format:** {result.image_media_type}",
        ]
        line_range = format_line_range(result.line_start, result.line_end)
        if line_range:
            metadata_lines.append(f"**Line Range:** {line_range}")
        if result.section_title:
            metadata_lines.append(f"**Section:** {result.section_title}")
        if result.source_block_id:
            metadata_lines.append(f"**Source Block:** {result.source_block_id}")
        if image_exceeds_response_limit(result.image_base64):
            metadata_lines.extend(
                [
                    "",
                    format_omitted_image_response(
                        title=f"Figure Image: {doc_id}/{asset_id}",
                        data=result.image_base64,
                        mime_type=result.image_media_type or "image/png",
                        source_path=source_path,
                        guidance="retry with a smaller max_size or open the artifact path directly",
                    ),
                ]
            )
            return [TextContent(type="text", text="\n".join(metadata_lines))]
        return [
            TextContent(type="text", text="\n".join(metadata_lines)),
            ImageContent(
                type="image",
                data=result.image_base64,
                mimeType=result.image_media_type or "image/png",
            ),
        ]
    else:
        await report_progress(
            ctx, 100, message=f"Fetched {asset_type} {asset_id} from {doc_id}"
        )
        lines = [f"## {asset_type.title()}: {result.asset_id}"]
        if result.page:
            lines.append(f"**Page:** {result.page}")
        line_range = format_line_range(result.line_start, result.line_end)
        if line_range:
            lines.append(f"**Line Range:** {line_range}")
        if result.section_title:
            lines.append(f"**Section:** {result.section_title}")
        if result.source_block_id:
            lines.append(f"**Source Block:** {result.source_block_id}")
        lines.append("")
        lines.append(result.text_content or "")
        source_path = None
        try:
            doc_dir = repository.get_doc_dir(doc_id)
            source_path = doc_dir / f"{doc_id}_full.md"
        except Exception:
            source_path = None
        text = format_limited_text_response(
            title=f"{asset_type}: {result.asset_id}",
            text="\n".join(lines),
            source_path=source_path,
            max_chars=max_chars,
            language="markdown",
            guidance="use a section/table asset_id or evidence span query for a smaller read",
        )
        return [TextContent(type="text", text=text)]


@mcp.tool()
async def document(
    op: str,
    file_paths: list[str] | None = None,
    pdf_path: str | None = None,
    doc_id: str | None = None,
    output_dir: str | None = None,
    output_path: str | None = None,
    async_mode: bool = True,
    use_marker: bool = False,
    ocr_enabled: bool = False,
    ocr_language: str = "eng",
    rotate_pages: bool = False,
    deskew: bool = False,
    page: int | None = None,
    limit: int | None = None,
    show_labels: bool = True,
    include_reading_order: bool = True,
    marker_max_pages_per_chunk: int = 0,
    extract_figures: bool = True,
    index_knowledge_graph: bool = False,
    page_ranges: list[str] | None = None,
    output_format: str = "markdown",
    refresh: bool = False,
    query: str = "",
    criteria: str = "",
    doc_b_id: str | None = None,
    ctx: Context | None = None,
) -> Any:
    """
    Consolidated PDF document entrypoint.

    Existing document tools stay registered and keep their original contracts.
    """
    operation = _normalize_op(op)
    if operation == "auto":
        if doc_id and file_paths:
            return (
                'Choose either doc_id or file_paths for document(op="auto"), not both.'
            )
        if doc_id:
            return await _prepare_document_for_ai(
                doc_id=doc_id,
                ctx=ctx,
                output_format=output_format,
            )
        if file_paths:
            if is_mixed_or_non_pdf_batch(file_paths):
                return await _ingest_mixed_document_batch(
                    file_paths,
                    use_marker=use_marker,
                    ocr_enabled=ocr_enabled,
                    ocr_language=ocr_language,
                    rotate_pages=rotate_pages,
                    deskew=deskew,
                    marker_max_pages_per_chunk=marker_max_pages_per_chunk,
                    extract_figures=extract_figures,
                    index_knowledge_graph=index_knowledge_graph,
                    page_ranges=page_ranges,
                    ctx=ctx,
                )
            return await ingest_documents(
                file_paths,
                async_mode=async_mode,
                use_marker=use_marker,
                ocr_enabled=ocr_enabled,
                ocr_language=ocr_language,
                rotate_pages=rotate_pages,
                deskew=deskew,
                marker_max_pages_per_chunk=marker_max_pages_per_chunk,
                extract_figures=extract_figures,
                index_knowledge_graph=index_knowledge_graph,
                page_ranges=page_ranges,
                ctx=ctx,
            )
        return _missing_document_param("doc_id or file_paths")
    if operation in {"ingest", "import"}:
        if not file_paths:
            return _missing_document_param("file_paths")
        if is_mixed_or_non_pdf_batch(file_paths):
            return await _ingest_mixed_document_batch(
                file_paths,
                use_marker=use_marker,
                ocr_enabled=ocr_enabled,
                ocr_language=ocr_language,
                rotate_pages=rotate_pages,
                deskew=deskew,
                marker_max_pages_per_chunk=marker_max_pages_per_chunk,
                extract_figures=extract_figures,
                index_knowledge_graph=index_knowledge_graph,
                page_ranges=page_ranges,
                ctx=ctx,
            )
        return await ingest_documents(
            file_paths,
            async_mode=async_mode,
            use_marker=use_marker,
            ocr_enabled=ocr_enabled,
            ocr_language=ocr_language,
            rotate_pages=rotate_pages,
            deskew=deskew,
            marker_max_pages_per_chunk=marker_max_pages_per_chunk,
            extract_figures=extract_figures,
            index_knowledge_graph=index_knowledge_graph,
            page_ranges=page_ranges,
            ctx=ctx,
        )
    if operation == "parse":
        source_pdf = pdf_path or (file_paths[0] if file_paths else None)
        if not source_pdf:
            return _missing_document_param("pdf_path")
        return await parse_pdf_structure(
            source_pdf,
            output_dir=output_dir,
            async_mode=async_mode,
            ocr_enabled=ocr_enabled,
            ocr_language=ocr_language,
            rotate_pages=rotate_pages,
            deskew=deskew,
            marker_max_pages_per_chunk=marker_max_pages_per_chunk,
            extract_figures=extract_figures,
            page_ranges=page_ranges,
            ctx=ctx,
        )
    if operation == "list":
        return await list_documents()
    if operation == "delete":
        if not doc_id:
            return _missing_document_param("doc_id")
        return await delete_document(doc_id)
    if operation == "inspect":
        if not doc_id:
            return _missing_document_param("doc_id")
        return await inspect_document_manifest(doc_id)
    if operation in {"prepare_ai", "readiness", "ai_ready"}:
        if not doc_id:
            return _missing_document_param("doc_id")
        return await _prepare_document_for_ai(
            doc_id=doc_id,
            ctx=ctx,
            output_format=output_format,
        )
    if operation == "ocr":
        source_pdf = pdf_path or (file_paths[0] if file_paths else None)
        if not source_pdf:
            return _missing_document_param("pdf_path")
        return await ocr_pdf_document(
            pdf_path=source_pdf,
            output_path=output_path,
            language=ocr_language,
            rotate_pages=rotate_pages,
            deskew=deskew,
            ctx=ctx,
        )
    if operation in {"export_segmentation", "segmentation"}:
        if not doc_id:
            return _missing_document_param("doc_id")
        return await export_document_segmentation(
            doc_id=doc_id,
            page=page,
            limit=limit,
            output_path=output_path,
            ctx=ctx,
        )
    if operation in {"layout", "visualize_layout"}:
        if not doc_id:
            return _missing_document_param("doc_id")
        return await visualize_document_layout(
            doc_id=doc_id,
            page=1 if page is None else page,
            show_labels=show_labels,
            include_reading_order=include_reading_order,
            output_path=output_path,
            ctx=ctx,
        )
    if operation in {"safety", "safety_audit", "ai_safety"}:
        if not doc_id:
            return _missing_document_param("doc_id")
        return await _export_pdf_ai_safety_report(
            doc_id=doc_id,
            output_path=output_path,
            ctx=ctx,
        )
    if operation in {"structure", "native_structure"}:
        if not doc_id:
            return _missing_document_param("doc_id")
        return await _export_pdf_native_structure_report(
            doc_id=doc_id,
            output_path=output_path,
            ctx=ctx,
        )
    if operation in {"coverage", "segmentation_coverage"}:
        if not doc_id:
            return _missing_document_param("doc_id")
        return await _export_segmentation_coverage_report(
            doc_id=doc_id,
            output_path=output_path,
            ctx=ctx,
        )
    if operation in {"accessibility", "accessibility_report"}:
        if not doc_id:
            return _missing_document_param("doc_id")
        return await _export_pdf_accessibility_report(
            doc_id=doc_id,
            output_path=output_path,
            ctx=ctx,
        )
    if operation in {"pointer_index", "section_pointer_index", "proxy_pointer"}:
        if not doc_id:
            return _missing_document_param("doc_id")
        return await _build_structural_pointer_index(
            doc_id=doc_id,
            output_path=output_path,
            ctx=ctx,
        )
    if operation in {"structural_retrieve", "retrieve", "search"}:
        if not doc_id:
            return _missing_document_param("doc_id")
        return await _structural_retrieve(
            doc_id=doc_id,
            query=query,
            limit=limit,
            refresh=refresh,
            ctx=ctx,
        )
    if operation in {"compare", "comparison"}:
        if not doc_id:
            return _missing_document_param("doc_id")
        if not doc_b_id:
            return _missing_document_param("doc_b_id")
        return await _compare_documents_structural(
            doc_id=doc_id,
            doc_b_id=doc_b_id,
            criteria=criteria or query,
            output_path=output_path,
            limit=limit,
            refresh=refresh,
            ctx=ctx,
        )
    if operation in {"audit", "readiness_audit"}:
        if not doc_id:
            return _missing_document_param("doc_id")
        return await _run_document_readiness_audit(
            doc_id=doc_id,
            output_path=output_path,
            ctx=ctx,
            refresh=refresh,
        )

    return _unsupported_document_op(
        "document",
        op,
        {
            "accessibility",
            "ai_safety",
            "audit",
            "auto",
            "coverage",
            "delete",
            "export_segmentation",
            "ingest",
            "inspect",
            "layout",
            "list",
            "ocr",
            "parse",
            "pointer_index",
            "prepare_ai",
            "proxy_pointer",
            "safety",
            "safety_audit",
            "search",
            "segmentation",
            "segmentation_coverage",
            "structure",
            "structural_retrieve",
            "native_structure",
            "visualize_layout",
            "compare",
            "comparison",
        },
    )


@mcp.tool()
async def document_asset(
    op: str,
    doc_id: str | None = None,
    asset_type: str | None = None,
    asset_id: str = "full",
    max_size: int | None = None,
    max_chars: int | None = None,
    path: str | None = None,
    query: str | None = None,
    max_depth: int | None = None,
    response_format: str = "tree",
    include_children: bool = True,
    block_types: list[str] | None = None,
    limit: int | None = None,
    fuzzy: bool = True,
    wiki_root: str = "",
    output_dir: str = "assets",
    index_path: str = "",
    citation_key: str = "",
    update_index: bool = True,
    overwrite: bool = False,
    ctx: Context | None = None,
) -> Any:
    """Consolidated document asset and section entrypoint."""
    operation = _normalize_op(op)
    if not doc_id:
        return _missing_document_param("doc_id")

    if operation == "get":
        if not asset_type:
            return _missing_document_param("asset_type")
        return await fetch_document_asset(
            doc_id,
            asset_type,
            asset_id,
            max_size=max_size,
            max_chars=max_chars,
            ctx=ctx,
        )
    if operation in {"foam_notes", "asset_notes"}:
        return await _write_foam_asset_notes(
            document_service,
            doc_id,
            asset_type=asset_type,
            asset_id=asset_id,
            wiki_root=wiki_root,
            output_dir=output_dir,
            index_path=index_path,
            citation_key=citation_key,
            update_index=update_index,
            overwrite=overwrite,
            response_format=response_format,
        )

    from src.presentation.tools import section_tools

    if operation in {"tree", "list"}:
        return await section_tools.list_section_tree(
            doc_id,
            max_depth,
            response_format,
        )
    if operation == "detail":
        if not path:
            return _missing_document_param("path")
        return await section_tools.get_section_detail(doc_id, path)
    if operation in {"blocks", "list_blocks"}:
        if not path:
            return _missing_document_param("path")
        return await section_tools.get_section_blocks(
            doc_id,
            path,
            include_children,
            block_types,
            limit,
        )
    if operation == "search":
        if not query:
            return _missing_document_param("query")
        return await section_tools.search_sections(doc_id, query, fuzzy)

    return _unsupported_document_op(
        "document_asset",
        op,
        {
            "asset_notes",
            "blocks",
            "detail",
            "foam_notes",
            "get",
            "list",
            "search",
            "tree",
        },
    )


@mcp.tool()
async def evidence(
    op: str,
    doc_id: str | None = None,
    query: str = "",
    span_id: str = "",
    span_kinds: list[str] | None = None,
    limit: int = 10,
    ref: dict[str, Any] | None = None,
    block_types: list[str] | None = None,
    output_format: str = "markdown",
    citation_key: str = "",
    wiki_root: str = "",
    output_path: str = "",
    index_path: str = "",
    update_index: bool = True,
    overwrite: bool = False,
) -> Any:
    """Consolidated citation evidence entrypoint."""
    operation = _normalize_op(op)
    if operation == "find":
        if not doc_id:
            return _missing_document_param("doc_id")
        return await find_evidence_spans(
            doc_id,
            query=query,
            span_id=span_id,
            span_kinds=span_kinds,
            limit=limit,
        )
    if operation == "verify":
        if ref is None:
            return _missing_document_param("ref")
        return await verify_citation_ref(ref)
    if operation == "bundle":
        if not doc_id:
            return _missing_document_param("doc_id")
        return await citation_bundle(
            doc_id,
            query=query,
            span_id=span_id,
            span_kinds=span_kinds,
            limit=limit,
            include_verification=True,
            output_format=output_format,
            citation_key=citation_key,
            wiki_root=wiki_root,
            output_path=output_path,
            index_path=index_path,
            update_index=update_index,
            overwrite=overwrite,
        )
    if operation in {"claim_promotion", "claims", "promote_claims"}:
        if not doc_id:
            return _missing_document_param("doc_id")
        payload = _claim_promotion_payload(
            repository=repository,
            asset_ref_factory=asset_ref_from_span,
            doc_id=doc_id,
            query=query,
            span_id=span_id,
            span_kinds=span_kinds,
            limit=limit,
            citation_key=citation_key,
        )
        if wiki_root or output_path:
            if output_format != "foam":
                return {
                    "success": False,
                    "doc_id": doc_id,
                    "error": "Foam claim writes require output_format='foam'",
                }
            if not payload.get("success"):
                return payload
            try:
                return _write_foam_claim_promotion_pack(
                    payload,
                    wiki_root=wiki_root,
                    output_path=output_path,
                    index_path=index_path,
                    citation_key=citation_key,
                    update_index=update_index,
                    overwrite=overwrite,
                )
            except (FileExistsError, ValueError) as exc:
                return {"success": False, "doc_id": doc_id, "error": str(exc)}
        if output_format == "json":
            bounded_payload = _bounded_evidence_payload(payload)
            return format_limited_json_response(
                title=f"Claim Promotion: {doc_id}",
                payload=bounded_payload,
                guidance="write a Foam claim pack to disk for full verification payloads",
            )
        if output_format == "foam":
            return format_limited_text_response(
                title=f"Foam Claim Promotion Pack: {doc_id}",
                text=_format_foam_claim_promotion_pack(payload),
                language="markdown",
                guidance="pass wiki_root/output_path to write the full claim pack",
            )
        return _format_claim_promotion_markdown(payload)
    if operation in {"health", "foam_health", "wiki_health"}:
        result = _audit_foam_wiki_health(
            wiki_root,
            output_format=output_format,
            repository=repository,
        )
        if isinstance(result, dict):
            return format_limited_json_response(
                title="Foam Wiki Health",
                payload=result,
                guidance="audit a narrower wiki root or inspect saved notes directly",
            )
        return format_limited_text_response(
            title="Foam Wiki Health",
            text=str(result),
            language="markdown",
            guidance="audit a narrower wiki root or inspect saved notes directly",
        )
    if operation in {"locate", "search_location"}:
        if not doc_id:
            return _missing_document_param("doc_id")
        if not query:
            return _missing_document_param("query")
        return await search_source_location(doc_id, query, block_types=block_types)

    return _unsupported_document_op(
        "evidence",
        op,
        {"bundle", "claim_promotion", "find", "health", "locate", "verify"},
    )


@mcp.tool()
async def convert_document(
    source: str,
    target_format: str,
    source_format: str = "auto",
    output_path: str | None = None,
    mode: str = "content",
    md_text: str | None = None,
    async_mode: bool = True,
    ctx: Context | None = None,
) -> Any:
    """
    Consolidated document conversion entrypoint.

    Dispatches to the existing conversion tools so each source family keeps its
    established output-path containment policy.
    """
    source_kind = source_format.strip().lower().replace("markdown", "md")
    target = target_format.strip().lower().lstrip(".")
    if source_kind == "auto":
        suffix = Path(source).suffix.lower()
        if suffix in {".md", ".markdown"}:
            source_kind = "md"
        elif suffix == ".pdf":
            source_kind = "pdf"
        elif suffix in {".doc", ".docx", ".odt", ".ods"} or target in {
            "doc",
            "odt",
            "pdf",
        }:
            source_kind = "docx"
        else:
            source_kind = "pdf"

    if source_kind == "pdf":
        if target == "docx":
            return await convert_pdf_to_docx(
                source,
                output_path=output_path,
                mode=mode,
                async_mode=async_mode,
                ctx=ctx,
            )
        if target == "pptx":
            return await convert_pdf_to_pptx(
                source,
                output_path=output_path,
                mode=mode,
                async_mode=async_mode,
                ctx=ctx,
            )
    elif source_kind == "docx":
        from src.presentation.tools import docx_tools

        if target == "doc":
            return await docx_tools.convert_docx_to_doc(
                source,
                output_path=output_path,
                mode=mode,
                async_mode=async_mode,
                ctx=ctx,
            )
        if target == "pdf":
            return await docx_tools.convert_docx_to_pdf(
                source,
                output_path=output_path,
                mode=mode,
                async_mode=async_mode,
                ctx=ctx,
            )
        if target == "odt":
            return await docx_tools.convert_docx_to_odt(
                source,
                output_path=output_path,
                mode=mode,
                async_mode=async_mode,
                ctx=ctx,
            )
    elif source_kind == "md":
        from src.presentation.tools import docx_tools

        if target in {"doc", "docx", "odt", "pdf"}:
            return await docx_tools.export_markdown(
                md_path=source if md_text is None else None,
                md_text=md_text,
                output_path=output_path,
                output_format=target,
                async_mode=async_mode,
                ctx=ctx,
            )

    return (
        f"Unsupported conversion: {source_kind} -> {target}. "
        "Supported conversions: pdf->docx/pptx, docx->doc/pdf/odt, "
        "markdown->doc/docx/odt/pdf."
    )
