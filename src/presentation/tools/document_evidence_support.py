"""Citation, Foam, and document evidence helper functions."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from src.presentation.tools.citation_support import (
    coerce_range,
    format_line_range,
    load_citation_status,
    load_or_build_evidence_spans,
)

_FOAM_INDEX_START = "<!-- asset-aware:evidence-index:start -->"
_FOAM_INDEX_END = "<!-- asset-aware:evidence-index:end -->"
_FOAM_ASSET_INDEX_START = "<!-- asset-aware:asset-index:start -->"
_FOAM_ASSET_INDEX_END = "<!-- asset-aware:asset-index:end -->"
_ASSET_LOCATOR_VERSION = "asset-manifest-v1"


def _normalize_op(op: str) -> str:
    return op.strip().lower().replace("-", "_")


def _unsupported_document_op(kind: str, op: str, allowed: set[str]) -> str:
    allowed_ops = ", ".join(sorted(allowed))
    return f"Unsupported {kind} op `{op}`. Supported operations: {allowed_ops}."


def _missing_document_param(name: str) -> str:
    return f"Missing required parameter: {name} is required."


def _filter_evidence_spans(
    spans: list[Any],
    *,
    query: str = "",
    span_id: str = "",
    span_kinds: list[str] | None = None,
) -> list[Any]:
    filtered = spans
    if span_id:
        filtered = [span for span in filtered if span.span_id == span_id]
    if query:
        query_lower = query.lower()
        filtered = [span for span in filtered if query_lower in span.text.lower()]
    if span_kinds:
        allowed_kinds = {kind.lower() for kind in span_kinds}
        filtered = [
            span for span in filtered if span.span_kind.lower() in allowed_kinds
        ]
    return filtered


def _foam_anchor_id(span_id: str) -> str:
    """Return a Foam-safe block anchor id derived from a stable span id."""
    cleaned = re.sub(r"[^A-Za-z0-9-]+", "-", span_id.replace("_", "-")).strip("-")
    cleaned = cleaned.lower() or "span"
    if not cleaned.startswith("spn-"):
        cleaned = f"spn-{cleaned}"
    return cleaned


def _claim_anchor_id(span_id: str) -> str:
    """Return a Foam-safe claim candidate anchor derived from a span id."""
    cleaned = _foam_anchor_id(span_id)
    if cleaned.startswith("spn-"):
        cleaned = "clm-" + cleaned[4:]
    elif not cleaned.startswith("clm-"):
        cleaned = f"clm-{cleaned}"
    return cleaned


def _claim_draft_from_span_text(text: str, limit: int = 320) -> str:
    """Build a non-inventive claim draft from the exact evidence quote."""
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _foam_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _foam_frontmatter_lines(frontmatter: dict[str, Any]) -> list[str]:
    lines = ["---"]
    for key, value in frontmatter.items():
        if value is None or value == "":
            continue
        if isinstance(value, list):
            rendered = ", ".join(_foam_scalar(item) for item in value)
            lines.append(f"{key}: [{rendered}]")
        else:
            lines.append(f"{key}: {_foam_scalar(value)}")
    lines.append("---")
    return lines


def _foam_quote_lines(text: str) -> list[str]:
    lines = text.splitlines() or [""]
    return [f"> {line}" if line else ">" for line in lines]


def _foam_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9-]+", "-", value.strip().lower()).strip("-")
    return slug or "evidence"


def _foam_asset_anchor_id(asset_type: str, asset_id: str) -> str:
    prefix = "fig" if asset_type == "figure" else "tab"
    cleaned = re.sub(r"[^A-Za-z0-9-]+", "-", asset_id.replace("_", "-")).strip("-")
    cleaned = cleaned.lower() or prefix
    if not cleaned.startswith(f"{prefix}-"):
        cleaned = f"{prefix}-{cleaned}"
    return cleaned


def _resolve_foam_write_paths(
    *,
    wiki_root: str,
    output_path: str,
    index_path: str,
    doc_id: str,
    citation_key: str,
) -> tuple[Path, Path, Path]:
    if not wiki_root:
        raise ValueError("wiki_root is required for Foam file writes")
    root = Path(wiki_root).expanduser().resolve()
    default_name = _foam_slug(citation_key or doc_id)
    target = (
        Path(output_path).expanduser()
        if output_path
        else Path("evidence") / (f"{default_name}-evidence.md")
    )
    index = Path(index_path).expanduser() if index_path else Path("Evidence Index.md")
    if not target.is_absolute():
        target = root / target
    if not index.is_absolute():
        index = root / index
    target = target.resolve()
    index = index.resolve()
    for candidate in (target, index):
        if candidate != root and root not in candidate.parents:
            raise ValueError(f"Foam output path escapes wiki_root: {candidate}")
    return root, target, index


def _asset_locator_payload(
    manifest: Any,
    asset_type: str,
    asset: Any,
) -> dict[str, Any]:
    return {
        "doc_id": manifest.doc_id,
        "source_pdf_sha256": getattr(manifest, "source_pdf_sha256", ""),
        "asset_type": asset_type,
        "asset_id": asset.id,
        "page": getattr(asset, "page", None),
        "line_start": getattr(asset, "line_start", None),
        "line_end": getattr(asset, "line_end", None),
        "source_block_id": getattr(asset, "source_block_id", ""),
        "source_order": getattr(asset, "source_order", 0),
        "section_id": getattr(asset, "section_id", ""),
        "section_title": getattr(asset, "section_title", ""),
    }


def _asset_locator_sha256(manifest: Any, asset_type: str, asset: Any) -> str:
    payload = _asset_locator_payload(manifest, asset_type, asset)
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _asset_ref_from_manifest_asset(
    manifest: Any,
    asset_type: str,
    asset: Any,
) -> dict[str, Any]:
    ref: dict[str, Any] = {
        "source_type": asset_type,
        "doc_id": manifest.doc_id,
        "asset_id": asset.id,
        "page": getattr(asset, "page", None),
        "source_revision_id": getattr(manifest, "source_pdf_sha256", ""),
        "locator_version": _ASSET_LOCATOR_VERSION,
        "locator_source_sha256": _asset_locator_sha256(manifest, asset_type, asset),
        "label": getattr(asset, "caption", "") or asset.id,
        "excerpt": getattr(asset, "preview", "")
        or getattr(asset, "caption", "")
        or asset.id,
    }
    source_block_id = getattr(asset, "source_block_id", "")
    if source_block_id:
        ref["block_id"] = source_block_id
    line_start = getattr(asset, "line_start", None)
    line_end = getattr(asset, "line_end", None)
    if line_start is not None and line_end is not None:
        ref["line_range"] = [line_start, line_end]
    return ref


def _foam_entry_metadata(
    entry: dict[str, Any],
    *,
    citation_key: str = "",
) -> dict[str, Any]:
    anchor_id = _foam_anchor_id(str(entry.get("span_id") or ""))
    source_ref = citation_key.strip() or str(entry.get("doc_id") or "")
    verification = entry.get("verification") or {}
    frontmatter = {
        "title": f"Evidence {entry.get('span_id')}",
        "type": "evidence",
        "tags": ["asset-aware", "evidence"],
        "source_doc_id": entry.get("doc_id"),
        "source_revision_id": entry.get("source_revision_id"),
        "span_id": entry.get("span_id"),
        "block_id": entry.get("block_id"),
        "asset_id": entry.get("asset_id"),
        "page": entry.get("page"),
        "line_start": (entry.get("line_range") or [None, None])[0],
        "line_end": (entry.get("line_range") or [None, None])[1],
        "char_start": (entry.get("char_range") or [None, None])[0],
        "char_end": (entry.get("char_range") or [None, None])[1],
        "byte_start": (entry.get("byte_range") or [None, None])[0],
        "byte_end": (entry.get("byte_range") or [None, None])[1],
        "text_sha256": entry.get("text_sha256"),
        "locator_source_sha256": entry.get("locator_source_sha256"),
        "verified": bool(verification.get("valid")),
    }
    return {
        "anchor_id": anchor_id,
        "block_anchor": f"^{anchor_id}",
        "wikilink": f"[[{source_ref}#^{anchor_id}]]" if source_ref else "",
        "embed": f"![[{source_ref}#^{anchor_id}]]" if source_ref else "",
        "frontmatter": frontmatter,
    }


def _verify_span_ref_payload(
    ref: dict[str, Any],
    *,
    repository: Any,
) -> dict[str, Any]:
    """Verify a span AssetRef and return structured status."""
    if ref.get("source_type") != "span":
        return {
            "valid": False,
            "status": "unsupported",
            "issues": ["Only span-level AssetRef objects can be verified"],
        }

    doc_id = str(ref.get("doc_id") or "")
    span_id = str(ref.get("span_id") or "")
    if not doc_id or not span_id:
        return {
            "valid": False,
            "status": "invalid",
            "issues": ["Citation ref must include doc_id and span_id"],
        }

    spans = load_or_build_evidence_spans(repository, doc_id)
    span = next((item for item in spans if item.span_id == span_id), None)
    if span is None:
        return {
            "valid": False,
            "status": "missing",
            "doc_id": doc_id,
            "span_id": span_id,
            "issues": [f"Citation span not found: {span_id}"],
        }

    issues: list[str] = []

    def _is_missing(value: Any) -> bool:
        return value is None or value == ""

    def require_equal(field: str, expected: Any) -> None:
        if field not in ref or _is_missing(ref.get(field)):
            issues.append(f"{field} missing")
        elif ref.get(field) != expected:
            issues.append(f"{field} mismatch")

    def require_range(field: str, expected: list[int | None]) -> None:
        if field not in ref:
            issues.append(f"{field} missing")
        elif coerce_range(ref.get(field)) != expected:
            issues.append(f"{field} mismatch")

    require_equal("source_revision_id", span.source_revision_id)
    require_equal("locator_version", span.locator_version)
    if span.locator_source_sha256:
        require_equal("locator_source_sha256", span.locator_source_sha256)
    else:
        issues.append("indexed span missing locator_source_sha256")
    if span.block_id:
        require_equal("block_id", span.block_id)
    if span.page is not None:
        require_equal("page", span.page)
    if span.line_start is not None and span.line_end is not None:
        require_range("line_range", [span.line_start, span.line_end])
    if span.char_start is not None and span.char_end is not None:
        require_range("char_range", [span.char_start, span.char_end])
    if span.byte_start is not None and span.byte_end is not None:
        require_range("byte_range", [span.byte_start, span.byte_end])
    if span.bbox:
        require_equal("bbox", span.bbox)

    quote = str(ref.get("quote") or "")
    if quote and quote != span.text:
        issues.append("quote mismatch")
    text_hashes = [
        str(ref.get("quote_sha256") or ""),
        str(ref.get("text_sha256") or ""),
    ]
    if not any(text_hashes):
        issues.append("quote_sha256 or text_sha256 missing")
    elif span.text_sha256 not in text_hashes:
        issues.append("quote_sha256/text_sha256 mismatch")

    return {
        "valid": not issues,
        "status": "verified" if not issues else "mismatch",
        "doc_id": doc_id,
        "span_id": span_id,
        "page": span.page,
        "line_range": [span.line_start, span.line_end],
        "line_display": format_line_range(span.line_start, span.line_end),
        "char_range": [span.char_start, span.char_end],
        "byte_range": [span.byte_start, span.byte_end],
        "text_sha256": span.text_sha256,
        "source_revision_id": span.source_revision_id,
        "locator_version": span.locator_version,
        "locator_source_sha256": span.locator_source_sha256,
        "issues": issues,
    }


def _citation_bundle_entry(
    span: Any,
    *,
    include_verification: bool,
    repository: Any,
    asset_ref_factory: Any,
    citation_key: str = "",
) -> dict[str, Any]:
    ref = asset_ref_factory(span)
    entry: dict[str, Any] = {
        "doc_id": span.doc_id,
        "span_id": span.span_id,
        "span_kind": span.span_kind,
        "source_type": span.source_type,
        "block_id": span.block_id,
        "asset_id": span.asset_id,
        "page": span.page,
        "line_range": [span.line_start, span.line_end],
        "line_display": format_line_range(span.line_start, span.line_end),
        "char_range": [span.char_start, span.char_end],
        "byte_range": [span.byte_start, span.byte_end],
        "bbox": span.bbox,
        "source_revision_id": span.source_revision_id,
        "locator_version": span.locator_version,
        "locator_source_sha256": span.locator_source_sha256,
        "text_sha256": span.text_sha256,
        "normalized_text_sha256": span.normalized_text_sha256,
        "quote": span.text,
        "context_before": span.context_before,
        "context_after": span.context_after,
        "section_hierarchy": span.section_hierarchy,
        "extraction_backend": span.extraction_backend,
        "craap": span.craap.model_dump(exclude_none=True),
        "asset_ref": ref,
    }
    if include_verification:
        entry["verification"] = _verify_span_ref_payload(ref, repository=repository)
    entry["foam"] = _foam_entry_metadata(entry, citation_key=citation_key)
    return entry


def _format_citation_bundle(payload: dict[str, Any]) -> str:
    if not payload.get("success"):
        return str(payload.get("error") or "Citation bundle failed")

    lines = [
        f"# Citation Bundle: {payload['doc_id']}",
        "",
        f"**Bundle version:** `{payload['bundle_version']}`",
        f"**Returned:** {payload['returned']}/{payload['matched_count']} spans",
    ]
    if payload.get("query"):
        lines.append(f"**Query:** `{payload['query']}`")
    lines.append("")

    for index, entry in enumerate(payload["entries"], 1):
        verification = entry.get("verification") or {}
        status = verification.get("status", "not_verified")
        issues = verification.get("issues") or []
        quote = entry["quote"][:500] + ("..." if len(entry["quote"]) > 500 else "")
        lines.extend(
            [
                f"## Evidence {index}: `{entry['span_id']}`",
                f"- **Kind:** {entry['span_kind']}",
                f"- **Block:** `{entry['block_id']}`",
                f"- **Page:** {entry['page'] or '?'}",
                f"- **Lines:** {entry['line_display'] or '?'}",
                f"- **Chars:** {entry['char_range'][0]}-{entry['char_range'][1]}",
                f"- **SHA256:** `{entry['text_sha256']}`",
                f"- **Verification:** {status}",
            ]
        )
        if issues:
            lines.append(f"- **Issues:** {', '.join(issues)}")
        lines.extend(
            [
                "",
                f"> {quote}",
                "",
                "AssetRef:",
                "```json",
                json.dumps(entry["asset_ref"], ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )

    return "\n".join(lines)


def _format_foam_evidence_pack(payload: dict[str, Any]) -> str:
    if not payload.get("success"):
        return str(payload.get("error") or "Citation bundle failed")

    frontmatter = {
        "title": f"Evidence pack: {payload['doc_id']}",
        "type": "evidence_pack",
        "tags": ["asset-aware", "evidence", "foam"],
        "source_doc_id": payload["doc_id"],
        "bundle_version": payload["bundle_version"],
        "query": payload.get("query") or "",
        "matched_count": payload.get("matched_count", 0),
        "returned": payload.get("returned", 0),
    }
    lines = _foam_frontmatter_lines(frontmatter)
    lines.extend(
        [
            "",
            f"# Evidence Pack: {payload['doc_id']}",
            "",
        ]
    )
    if payload.get("query"):
        lines.extend([f"`query`: {payload['query']}", ""])

    for index, entry in enumerate(payload["entries"], 1):
        foam = entry.get("foam") or {}
        verification = entry.get("verification") or {}
        status = verification.get("status", "not_verified")
        issues = verification.get("issues") or []
        lines.extend(
            [
                f"## Evidence {index}: `{entry['span_id']}`",
                "",
                f"- `foam_anchor`: `{foam.get('block_anchor', '')}`",
                f"- `wikilink`: `{foam.get('wikilink', '')}`",
                f"- `embed`: `{foam.get('embed', '')}`",
                f"- `verification`: `{status}`",
                f"- `source_revision_id`: `{entry['source_revision_id']}`",
                f"- `locator_source_sha256`: `{entry['locator_source_sha256']}`",
                f"- `text_sha256`: `{entry['text_sha256']}`",
                f"- `page`: {entry['page'] or '?'}",
                f"- `lines`: {entry['line_display'] or '?'}",
                "",
            ]
        )
        if issues:
            lines.extend([f"- `issues`: {', '.join(issues)}", ""])
        lines.extend(_foam_quote_lines(str(entry.get("quote") or "")))
        lines.extend(
            [
                "",
                str(foam.get("block_anchor") or ""),
                "",
                "```json",
                json.dumps(entry["asset_ref"], ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def _claim_promotion_entry(
    span: Any,
    *,
    repository: Any,
    asset_ref_factory: Any,
    citation_key: str = "",
) -> dict[str, Any]:
    evidence = _citation_bundle_entry(
        span,
        include_verification=True,
        repository=repository,
        asset_ref_factory=asset_ref_factory,
        citation_key=citation_key,
    )
    verification = evidence.get("verification") or {}
    claim_anchor = _claim_anchor_id(span.span_id)
    source_ref = _foam_slug(citation_key or span.doc_id)
    return {
        "doc_id": span.doc_id,
        "claim_id": claim_anchor,
        "span_id": span.span_id,
        "block_id": span.block_id,
        "page": span.page,
        "line_display": format_line_range(span.line_start, span.line_end),
        "claim_text": _claim_draft_from_span_text(span.text),
        "claim_text_source": "exact_evidence_quote",
        "requires_verification": True,
        "verified": bool(verification.get("valid")),
        "promotion_status": "ready" if verification.get("valid") else "blocked",
        "verification": verification,
        "asset_ref": evidence["asset_ref"],
        "evidence": evidence,
        "foam": {
            "block_anchor": f"^{claim_anchor}",
            "wikilink": f"[[{source_ref}#^{claim_anchor}]]",
            "evidence_wikilink": (evidence.get("foam") or {}).get("wikilink", ""),
        },
    }


def _claim_promotion_payload(
    *,
    repository: Any,
    asset_ref_factory: Any,
    doc_id: str,
    query: str,
    span_id: str,
    span_kinds: list[str] | None,
    limit: int,
    citation_key: str,
) -> dict[str, Any]:
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
        return {
            "success": False,
            "doc_id": doc_id,
            "workflow_version": "claim-promotion-v1",
            "error": error,
        }

    filtered = _filter_evidence_spans(
        spans,
        query=query,
        span_id=span_id,
        span_kinds=span_kinds,
    )
    if not filtered:
        target = span_id or query
        return {
            "success": False,
            "doc_id": doc_id,
            "workflow_version": "claim-promotion-v1",
            "error": f"No evidence spans found for `{target}` in doc_id: {doc_id}",
        }

    bounded_limit = max(1, min(limit, 25))
    entries = [
        _claim_promotion_entry(
            span,
            repository=repository,
            asset_ref_factory=asset_ref_factory,
            citation_key=citation_key,
        )
        for span in filtered[:bounded_limit]
    ]
    return {
        "success": True,
        "workflow_version": "claim-promotion-v1",
        "doc_id": doc_id,
        "query": query,
        "span_id": span_id,
        "span_kinds": span_kinds or [],
        "citation_key": citation_key,
        "matched_count": len(filtered),
        "returned": len(entries),
        "verification_required": True,
        "entries": entries,
    }


def _format_claim_promotion_markdown(payload: dict[str, Any]) -> str:
    if not payload.get("success"):
        return str(payload.get("error") or "Claim promotion failed")

    lines = [
        f"# Claim Promotion Candidates: {payload['doc_id']}",
        "",
        f"**Workflow version:** `{payload['workflow_version']}`",
        f"**Returned:** {payload['returned']}/{payload['matched_count']} candidates",
        "**Rule:** Promotion is blocked unless verification is valid.",
        "",
    ]
    if payload.get("query"):
        lines.extend([f"**Query:** `{payload['query']}`", ""])

    for index, entry in enumerate(payload["entries"], 1):
        verification = entry.get("verification") or {}
        issues = verification.get("issues") or []
        lines.extend(
            [
                f"## Candidate {index}: `{entry['claim_id']}`",
                f"- **Status:** {entry['promotion_status']}",
                f"- **Verified:** {entry['verified']}",
                f"- **Span:** `{entry['span_id']}`",
                f"- **Block:** `{entry['block_id']}`",
                f"- **Page:** {entry['page'] or '?'}",
                f"- **Lines:** {entry['line_display'] or '?'}",
                f"- **Evidence link:** {(entry.get('foam') or {}).get('evidence_wikilink', '')}",
            ]
        )
        if issues:
            lines.append(f"- **Issues:** {', '.join(issues)}")
        lines.extend(["", f"> {entry['claim_text']}", ""])

    return "\n".join(lines)


def _format_foam_claim_promotion_pack(payload: dict[str, Any]) -> str:
    if not payload.get("success"):
        return str(payload.get("error") or "Claim promotion failed")

    frontmatter = {
        "title": f"Claim promotion candidates: {payload['doc_id']}",
        "type": "claim_promotion_pack",
        "tags": ["asset-aware", "evidence", "claims", "foam"],
        "source_doc_id": payload["doc_id"],
        "workflow_version": payload["workflow_version"],
        "query": payload.get("query") or "",
        "matched_count": payload.get("matched_count", 0),
        "returned": payload.get("returned", 0),
        "verification_required": True,
    }
    lines = _foam_frontmatter_lines(frontmatter)
    lines.extend(
        [
            "",
            f"# Claim Promotion Candidates: {payload['doc_id']}",
            "",
            "> Promotion is blocked unless verification is valid.",
            "",
        ]
    )

    for index, entry in enumerate(payload["entries"], 1):
        foam = entry.get("foam") or {}
        verification = entry.get("verification") or {}
        issues = verification.get("issues") or []
        lines.extend(
            [
                f"## Claim Candidate {index}: `{entry['claim_id']}`",
                "",
                f"- `foam_anchor`: `{foam.get('block_anchor', '')}`",
                f"- `wikilink`: `{foam.get('wikilink', '')}`",
                f"- `evidence`: `{foam.get('evidence_wikilink', '')}`",
                f"- `promotion_status`: `{entry['promotion_status']}`",
                f"- `verified`: `{str(entry['verified']).lower()}`",
                f"- `span_id`: `{entry['span_id']}`",
                f"- `page`: {entry['page'] or '?'}",
                f"- `lines`: {entry['line_display'] or '?'}",
                "",
                "### Claim Draft",
                "",
                f"> {entry['claim_text']}",
                "",
            ]
        )
        if issues:
            lines.extend([f"- `issues`: {', '.join(issues)}", ""])
        verification_payload = {
            "verification": verification,
            "evidence": entry.get("evidence") or {},
        }
        lines.extend(
            [
                str(foam.get("block_anchor") or ""),
                "",
                "### AssetRef",
                "",
                "```json",
                json.dumps(entry["asset_ref"], ensure_ascii=False, indent=2),
                "```",
                "",
                "### Verification Payload",
                "",
                "```json",
                json.dumps(verification_payload, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def _write_foam_claim_promotion_pack(
    payload: dict[str, Any],
    *,
    wiki_root: str,
    output_path: str,
    index_path: str,
    citation_key: str,
    update_index: bool,
    overwrite: bool,
) -> dict[str, Any]:
    blocked = [
        entry
        for entry in payload.get("entries", [])
        if not (entry.get("verification") or {}).get("valid")
    ]
    if blocked:
        return {
            "success": False,
            "doc_id": payload.get("doc_id"),
            "error": "Claim promotion write blocked: every candidate must verify first.",
            "blocked_count": len(blocked),
            "blocked_claim_ids": [entry.get("claim_id") for entry in blocked],
        }

    if not output_path:
        default_name = _foam_slug(citation_key or str(payload.get("doc_id") or "doc"))
        output_path = str(Path("evidence") / f"{default_name}-claims.md")
    root, target, index = _resolve_foam_write_paths(
        wiki_root=wiki_root,
        output_path=output_path,
        index_path=index_path,
        doc_id=str(payload.get("doc_id") or ""),
        citation_key=citation_key,
    )
    markdown = _format_foam_claim_promotion_pack(payload)
    _write_foam_text(target, markdown, overwrite=overwrite)
    index_written = False
    if update_index:
        _update_foam_index(index, payload, target)
        index_written = True
    return {
        "success": True,
        "operation": "foam_claim_promotion_write",
        "wiki_root": str(root),
        "output_path": str(target),
        "index_path": str(index) if index_written else "",
        "index_updated": index_written,
        "doc_id": payload.get("doc_id"),
        "returned": payload.get("returned", 0),
        "matched_count": payload.get("matched_count", 0),
        "wikilinks": [
            (entry.get("foam") or {}).get("wikilink", "")
            for entry in payload.get("entries", [])
        ],
    }


def _format_foam_asset_note(
    manifest: Any,
    asset_type: str,
    asset: Any,
    *,
    citation_key: str = "",
) -> tuple[str, dict[str, Any]]:
    anchor_id = _foam_asset_anchor_id(asset_type, asset.id)
    source_ref = f"{_foam_slug(citation_key or manifest.doc_id)}-{_foam_slug(asset.id)}"
    asset_ref = _asset_ref_from_manifest_asset(manifest, asset_type, asset)
    frontmatter = {
        "title": f"{asset_type.title()} {asset.id}",
        "type": f"{asset_type}_evidence",
        "tags": ["asset-aware", "evidence", asset_type],
        "source_doc_id": manifest.doc_id,
        "source_revision_id": getattr(manifest, "source_pdf_sha256", ""),
        "asset_id": asset.id,
        "page": getattr(asset, "page", None),
        "line_start": getattr(asset, "line_start", None),
        "line_end": getattr(asset, "line_end", None),
        "source_block_id": getattr(asset, "source_block_id", ""),
        "source_order": getattr(asset, "source_order", 0),
        "section_id": getattr(asset, "section_id", ""),
        "section_title": getattr(asset, "section_title", ""),
        "locator_source_sha256": asset_ref["locator_source_sha256"],
    }
    lines = _foam_frontmatter_lines(frontmatter)
    lines.extend(
        [
            "",
            f"# {asset_type.title()} Evidence: {asset.id}",
            "",
            f"- `foam_anchor`: `^{anchor_id}`",
            f"- `wikilink`: `[[{source_ref}#^{anchor_id}]]`",
            f"- `source_doc_id`: `{manifest.doc_id}`",
            f"- `asset_id`: `{asset.id}`",
            f"- `page`: {getattr(asset, 'page', None) or '?'}",
        ]
    )
    line_display = format_line_range(
        getattr(asset, "line_start", None),
        getattr(asset, "line_end", None),
    )
    if line_display:
        lines.append(f"- `lines`: {line_display}")
    section_title = getattr(asset, "section_title", "")
    if section_title:
        lines.append(f"- `section`: {section_title}")
    caption = getattr(asset, "caption", "")
    if caption:
        lines.extend(["", f"> {caption}"])
    if asset_type == "table":
        table_markdown = getattr(asset, "markdown", "")
        if table_markdown:
            lines.extend(["", "## Table", "", table_markdown])
        else:
            lines.extend(["", "## Preview", "", getattr(asset, "preview", "")])
    else:
        figure_path = getattr(asset, "path", "")
        lines.extend(
            [
                "",
                "## Figure",
                "",
                f"- `image_path`: `{figure_path}`",
                f"- `size`: {getattr(asset, 'width', 0)}x{getattr(asset, 'height', 0)}",
                f"- `format`: {getattr(asset, 'ext', '')}",
            ]
        )
    lines.extend(
        [
            "",
            f"^{anchor_id}",
            "",
            "```json",
            json.dumps(asset_ref, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    note = "\n".join(lines).rstrip() + "\n"
    meta = {
        "asset_type": asset_type,
        "asset_id": asset.id,
        "anchor": f"^{anchor_id}",
        "wikilink": f"[[{source_ref}#^{anchor_id}]]",
        "asset_ref": asset_ref,
    }
    return note, meta


def _write_foam_text(path: Path, text: str, *, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") != text and not overwrite:
        raise FileExistsError(
            f"Foam evidence file already exists: {path}. Pass overwrite=true to replace it."
        )
    path.write_text(text, encoding="utf-8")


def _foam_index_block(payload: dict[str, Any], note_path: Path) -> str:
    note_stem = note_path.stem
    lines = [
        _FOAM_INDEX_START,
        "## Asset-Aware Evidence Index",
        "",
    ]
    for entry in payload.get("entries", []):
        foam = entry.get("foam") or {}
        anchor = foam.get("block_anchor") or ""
        verification = entry.get("verification") or {}
        status = verification.get("status", "not_verified")
        line_display = entry.get("line_display") or "?"
        lines.append(
            "- "
            f"[[{note_stem}#{anchor}]] "
            f"`{entry.get('span_id', '')}` "
            f"p.{entry.get('page') or '?'} {line_display} "
            f"`{status}`"
        )
    lines.extend(["", _FOAM_INDEX_END, ""])
    return "\n".join(lines)


def _update_foam_index(
    index_path: Path, payload: dict[str, Any], note_path: Path
) -> None:
    block = _foam_index_block(payload, note_path)
    if index_path.exists():
        text = index_path.read_text(encoding="utf-8")
    else:
        text = "# Evidence Index\n\n"
    if _FOAM_INDEX_START in text and _FOAM_INDEX_END in text:
        pattern = re.compile(
            re.escape(_FOAM_INDEX_START) + r".*?" + re.escape(_FOAM_INDEX_END) + r"\n?",
            re.DOTALL,
        )
        text = pattern.sub(block, text)
    else:
        text = text.rstrip() + "\n\n" + block
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(text, encoding="utf-8")


def _foam_asset_index_block(asset_notes: list[dict[str, Any]]) -> str:
    lines = [
        _FOAM_ASSET_INDEX_START,
        "## Asset-Aware Table/Figure Index",
        "",
    ]
    for item in asset_notes:
        lines.append(
            "- "
            f"{item['wikilink']} "
            f"`{item['asset_type']}` "
            f"`{item['asset_id']}` "
            f"p.{item.get('page') or '?'}"
        )
    lines.extend(["", _FOAM_ASSET_INDEX_END, ""])
    return "\n".join(lines)


def _update_foam_asset_index(
    index_path: Path, asset_notes: list[dict[str, Any]]
) -> None:
    block = _foam_asset_index_block(asset_notes)
    if index_path.exists():
        text = index_path.read_text(encoding="utf-8")
    else:
        text = "# Evidence Index\n\n"
    if _FOAM_ASSET_INDEX_START in text and _FOAM_ASSET_INDEX_END in text:
        pattern = re.compile(
            re.escape(_FOAM_ASSET_INDEX_START)
            + r".*?"
            + re.escape(_FOAM_ASSET_INDEX_END)
            + r"\n?",
            re.DOTALL,
        )
        text = pattern.sub(block, text)
    else:
        text = text.rstrip() + "\n\n" + block
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(text, encoding="utf-8")


def _write_foam_evidence_pack(
    payload: dict[str, Any],
    *,
    wiki_root: str,
    output_path: str,
    index_path: str,
    citation_key: str,
    update_index: bool,
    overwrite: bool,
) -> dict[str, Any]:
    root, target, index = _resolve_foam_write_paths(
        wiki_root=wiki_root,
        output_path=output_path,
        index_path=index_path,
        doc_id=str(payload.get("doc_id") or ""),
        citation_key=citation_key,
    )
    markdown = _format_foam_evidence_pack(payload)
    _write_foam_text(target, markdown, overwrite=overwrite)
    index_written = False
    if update_index:
        _update_foam_index(index, payload, target)
        index_written = True
    return {
        "success": True,
        "operation": "foam_write",
        "wiki_root": str(root),
        "output_path": str(target),
        "index_path": str(index) if index_written else "",
        "index_updated": index_written,
        "doc_id": payload.get("doc_id"),
        "returned": payload.get("returned", 0),
        "matched_count": payload.get("matched_count", 0),
        "wikilinks": [
            (entry.get("foam") or {}).get("wikilink", "")
            for entry in payload.get("entries", [])
        ],
    }


def _selected_manifest_assets(
    manifest: Any,
    asset_type: str | None,
    asset_id: str,
) -> list[tuple[str, Any]]:
    requested = (asset_type or "all").lower()
    selected: list[tuple[str, Any]] = []
    if requested in {"all", "table", "tables"}:
        for table in manifest.assets.tables:
            if asset_id in {"", "all", table.id}:
                selected.append(("table", table))
    if requested in {"all", "figure", "figures"}:
        for figure in manifest.assets.figures:
            if asset_id in {"", "all", figure.id}:
                selected.append(("figure", figure))
    return selected


async def _write_foam_asset_notes(
    document_service: Any,
    doc_id: str,
    *,
    asset_type: str | None,
    asset_id: str,
    wiki_root: str,
    output_dir: str,
    index_path: str,
    citation_key: str,
    update_index: bool,
    overwrite: bool,
    response_format: str,
) -> Any:
    if not wiki_root:
        return _missing_document_param("wiki_root")
    manifest = await document_service.get_manifest(doc_id)
    if manifest is None:
        return {"success": False, "doc_id": doc_id, "error": "Document not found"}
    root = Path(wiki_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    output_base = Path(output_dir or "assets")
    if output_base.is_absolute():
        output_base = output_base.resolve()
    else:
        output_base = (root / output_base).resolve()
    if output_base != root and root not in output_base.parents:
        return {
            "success": False,
            "doc_id": doc_id,
            "error": f"Foam asset output path escapes wiki_root: {output_base}",
        }
    selected = _selected_manifest_assets(manifest, asset_type, asset_id)
    if not selected:
        return {
            "success": False,
            "doc_id": doc_id,
            "error": "No matching table/figure assets found",
        }
    written: list[dict[str, Any]] = []
    for kind, asset in selected:
        note, meta = _format_foam_asset_note(
            manifest,
            kind,
            asset,
            citation_key=citation_key,
        )
        filename = f"{_foam_slug(citation_key or doc_id)}-{_foam_slug(asset.id)}.md"
        target = output_base / filename
        try:
            _write_foam_text(target, note, overwrite=overwrite)
        except FileExistsError as exc:
            return {"success": False, "doc_id": doc_id, "error": str(exc)}
        meta.update(
            {
                "path": str(target),
                "page": getattr(asset, "page", None),
            }
        )
        written.append(meta)
    resolved_index = (
        Path(index_path).expanduser() if index_path else Path("Evidence Index.md")
    )
    if not resolved_index.is_absolute():
        resolved_index = root / resolved_index
    resolved_index = resolved_index.resolve()
    if resolved_index != root and root not in resolved_index.parents:
        return {
            "success": False,
            "doc_id": doc_id,
            "error": f"Foam index path escapes wiki_root: {resolved_index}",
        }
    if update_index:
        _update_foam_asset_index(resolved_index, written)
    payload = {
        "success": True,
        "operation": "foam_asset_notes",
        "doc_id": doc_id,
        "wiki_root": str(root),
        "output_dir": str(output_base),
        "index_path": str(resolved_index) if update_index else "",
        "index_updated": update_index,
        "written": written,
        "written_count": len(written),
    }
    if response_format == "json":
        return payload
    lines = [
        f"✅ Wrote {len(written)} Foam asset notes",
        f"- **doc_id:** `{doc_id}`",
        f"- **output_dir:** `{output_base}`",
    ]
    if update_index:
        lines.append(f"- **index_path:** `{resolved_index}`")
    for item in written:
        lines.append(f"- {item['wikilink']} -> `{item['path']}`")
    return "\n".join(lines)


def _extract_json_fences(text: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for match in re.finditer(r"```json\s*(.*?)```", text, re.DOTALL | re.IGNORECASE):
        try:
            data = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            objects.append(data)
    return objects


def _foam_note_index(wiki_root: Path) -> dict[str, Path]:
    notes: dict[str, Path] = {}
    for path in wiki_root.rglob("*.md"):
        notes[path.stem] = path
        rel_no_suffix = path.relative_to(wiki_root).with_suffix("").as_posix()
        notes[rel_no_suffix] = path
    return notes


def _verify_asset_ref_payload(
    ref: dict[str, Any],
    *,
    repository: Any,
) -> dict[str, Any]:
    source_type = str(ref.get("source_type") or "")
    if source_type == "span":
        return _verify_span_ref_payload(ref, repository=repository)
    if source_type not in {"table", "figure"}:
        return {
            "valid": False,
            "status": "unsupported",
            "issues": ["Only span/table/figure AssetRef objects can be health-checked"],
        }
    doc_id = str(ref.get("doc_id") or "")
    asset_id = str(ref.get("asset_id") or "")
    if not doc_id or not asset_id:
        return {
            "valid": False,
            "status": "invalid",
            "issues": ["Asset ref must include doc_id and asset_id"],
        }
    manifest = repository.load_manifest(doc_id)
    if manifest is None:
        return {
            "valid": False,
            "status": "missing",
            "doc_id": doc_id,
            "asset_id": asset_id,
            "issues": [f"Document manifest not found: {doc_id}"],
        }
    asset = (
        manifest.assets.find_table(asset_id)
        if source_type == "table"
        else manifest.assets.find_figure(asset_id)
    )
    if asset is None:
        return {
            "valid": False,
            "status": "missing",
            "doc_id": doc_id,
            "asset_id": asset_id,
            "issues": [f"{source_type} asset not found: {asset_id}"],
        }
    issues: list[str] = []
    if "source_revision_id" in ref and ref.get("source_revision_id") != getattr(
        manifest, "source_pdf_sha256", ""
    ):
        issues.append("source_revision_id mismatch")
    if (
        ref.get("locator_version")
        and ref.get("locator_version") != _ASSET_LOCATOR_VERSION
    ):
        issues.append("locator_version mismatch")
    expected_locator = _asset_locator_sha256(manifest, source_type, asset)
    if (
        "locator_source_sha256" in ref
        and ref.get("locator_source_sha256") != expected_locator
    ):
        issues.append("locator_source_sha256 mismatch")
    if "page" in ref and ref.get("page") != getattr(asset, "page", None):
        issues.append("page mismatch")
    if "block_id" in ref and ref.get("block_id") != getattr(
        asset, "source_block_id", ""
    ):
        issues.append("source_block_id mismatch")
    if "line_range" in ref and coerce_range(ref.get("line_range")) != [
        getattr(asset, "line_start", None),
        getattr(asset, "line_end", None),
    ]:
        issues.append("line_range mismatch")
    return {
        "valid": not issues,
        "status": "verified" if not issues else "mismatch",
        "doc_id": doc_id,
        "asset_id": asset_id,
        "source_type": source_type,
        "page": getattr(asset, "page", None),
        "line_range": [
            getattr(asset, "line_start", None),
            getattr(asset, "line_end", None),
        ],
        "source_revision_id": getattr(manifest, "source_pdf_sha256", ""),
        "locator_version": _ASSET_LOCATOR_VERSION,
        "locator_source_sha256": expected_locator,
        "issues": issues,
    }


def _audit_foam_wiki_health(
    wiki_root: str,
    *,
    output_format: str,
    repository: Any,
) -> Any:
    if not wiki_root:
        return _missing_document_param("wiki_root")
    root = Path(wiki_root).expanduser().resolve()
    if not root.exists():
        return {
            "success": False,
            "error": f"wiki_root does not exist: {root}",
        }
    note_index = _foam_note_index(root)
    files = sorted(root.rglob("*.md"))
    asset_ref_results: list[dict[str, Any]] = []
    wikilink_issues: list[dict[str, str]] = []
    anchors_by_file: dict[Path, set[str]] = {}

    for path in files:
        text = path.read_text(encoding="utf-8")
        anchors_by_file[path] = set(
            re.findall(r"(?m)(\^[A-Za-z0-9][A-Za-z0-9-]*)\s*$", text)
        )

    for path in files:
        text = path.read_text(encoding="utf-8")
        for ref in _extract_json_fences(text):
            if ref.get("source_type") not in {"span", "table", "figure"}:
                continue
            verification = _verify_asset_ref_payload(ref, repository=repository)
            asset_ref_results.append(
                {
                    "file": str(path.relative_to(root)),
                    "span_id": ref.get("span_id", ""),
                    "asset_id": ref.get("asset_id", ""),
                    "source_type": ref.get("source_type", ""),
                    "doc_id": ref.get("doc_id", ""),
                    "status": verification.get("status", "unknown"),
                    "valid": bool(verification.get("valid")),
                    "issues": verification.get("issues") or [],
                }
            )

        for match in re.finditer(r"!?\[\[([^#\]|]+)#(\^[A-Za-z0-9][^\]|]+)", text):
            target_name = match.group(1).strip()
            anchor = match.group(2).strip()
            target_path = note_index.get(target_name)
            if target_path is None:
                wikilink_issues.append(
                    {
                        "file": str(path.relative_to(root)),
                        "wikilink": match.group(0),
                        "issue": "target note missing",
                    }
                )
            elif anchor not in anchors_by_file.get(target_path, set()):
                wikilink_issues.append(
                    {
                        "file": str(path.relative_to(root)),
                        "wikilink": match.group(0),
                        "issue": "target anchor missing",
                    }
                )

    invalid_refs = [item for item in asset_ref_results if not item["valid"]]
    payload = {
        "success": True,
        "operation": "foam_health",
        "wiki_root": str(root),
        "files_scanned": len(files),
        "asset_refs": len(asset_ref_results),
        "span_asset_refs": len(
            [item for item in asset_ref_results if item["source_type"] == "span"]
        ),
        "valid_refs": len(asset_ref_results) - len(invalid_refs),
        "invalid_refs": len(invalid_refs),
        "wikilink_issues": len(wikilink_issues),
        "asset_ref_results": asset_ref_results,
        "wikilink_issue_details": wikilink_issues,
    }
    if output_format == "json":
        return payload

    lines = [
        "# Foam Citation Health",
        "",
        f"- **files_scanned:** {payload['files_scanned']}",
        f"- **span_asset_refs:** {payload['span_asset_refs']}",
        f"- **valid_refs:** {payload['valid_refs']}",
        f"- **invalid_refs:** {payload['invalid_refs']}",
        f"- **wikilink_issues:** {payload['wikilink_issues']}",
    ]
    if invalid_refs:
        lines.extend(["", "## Invalid AssetRefs"])
        for item in invalid_refs:
            lines.append(
                f"- `{item['file']}` `{item['span_id']}`: "
                f"{', '.join(item['issues']) or item['status']}"
            )
    if wikilink_issues:
        lines.extend(["", "## Wikilink Issues"])
        for item in wikilink_issues:
            lines.append(f"- `{item['file']}` {item['wikilink']}: {item['issue']}")
    return "\n".join(lines)
