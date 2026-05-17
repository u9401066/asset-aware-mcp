"""Structural pointer artifacts for citation-ready document retrieval.

This service borrows the useful part of Proxy-Pointer RAG: index a small,
searchable proxy, then materialize the source section through a stable pointer.
The contract stays local-first and provenance-heavy so it can feed MCP tools,
A2T tables, and Foam notes without treating a breadcrumb as evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

from src.application.output_paths import resolve_document_output_path

SECTION_POINTER_SCHEMA_VERSION = "section-pointer-index-v1"
DOCUMENT_COMPARISON_SCHEMA_VERSION = "document-comparison-bundle-v1"
SECTION_POINTER_INDEX_NAME = "section_pointer_index.jsonl"

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_PREVIEW_CHARS = 1200
_CONTEXT_CHARS = 4000
STRUCTURAL_POINTER_MARKDOWN_MAX_BYTES_ENV = (
    "ASSET_AWARE_STRUCTURAL_POINTER_MARKDOWN_MAX_BYTES"
)
DEFAULT_STRUCTURAL_POINTER_MARKDOWN_MAX_BYTES = 2 * 1024 * 1024
STRUCTURAL_POINTER_INDEX_MAX_BYTES_ENV = (
    "ASSET_AWARE_STRUCTURAL_POINTER_INDEX_MAX_BYTES"
)
STRUCTURAL_POINTER_INDEX_MAX_RECORDS_ENV = (
    "ASSET_AWARE_STRUCTURAL_POINTER_INDEX_MAX_RECORDS"
)
DEFAULT_STRUCTURAL_POINTER_INDEX_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_STRUCTURAL_POINTER_INDEX_MAX_RECORDS = 50_000


class StructuralPointerService:
    """Build and query document section-pointer artifacts."""

    def __init__(self, repository: Any, segmentation_service: Any):
        self.repository = repository
        self.segmentation_service = segmentation_service

    async def build_and_save_pointer_index(
        self,
        doc_id: str,
        *,
        output_path: str | None = None,
    ) -> tuple[Path, dict[str, Any]]:
        manifest = self.repository.load_manifest(doc_id)
        if manifest is None:
            raise ValueError(f"Document not found: {doc_id}")
        doc_dir = self.repository.get_doc_dir(doc_id)
        segmentation = await self.segmentation_service.export_document_segmentation(
            doc_id
        )
        markdown = self._load_markdown_bounded(doc_id, doc_dir)
        spans = self.repository.load_citation_index(doc_id)
        records = self._build_records(
            manifest=manifest,
            segmentation=segmentation,
            spans=spans,
        )
        target = resolve_document_output_path(
            doc_dir,
            output_path,
            default_name=SECTION_POINTER_INDEX_NAME,
            allowed_suffixes={".jsonl"},
            reserved_names=_reserved_pointer_names(doc_id),
        )
        payload = "\n".join(
            json.dumps(record, ensure_ascii=False) for record in records
        )
        if payload:
            payload += "\n"
        target.write_text(payload, encoding="utf-8")
        return target, self._summary(
            doc_id=doc_id,
            manifest=manifest,
            segmentation=segmentation,
            records=records,
            target=target,
            markdown=markdown,
        )

    def load_pointer_index(self, doc_id: str) -> list[dict[str, Any]]:
        doc_dir = self._existing_doc_dir(doc_id)
        if doc_dir is None:
            return []
        path = doc_dir / SECTION_POINTER_INDEX_NAME
        if not path.exists():
            return []
        try:
            if path.stat().st_size > _pointer_index_max_bytes():
                return []
        except OSError:
            return []
        records: list[dict[str, Any]] = []
        max_records = _pointer_index_max_records()
        try:
            with path.open("r", encoding="utf-8") as handle:
                for raw_line in handle:
                    if len(records) >= max_records:
                        break
                    if not raw_line.strip():
                        continue
                    try:
                        item = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(item, dict):
                        records.append(item)
        except OSError:
            return []
        return records

    def _existing_doc_dir(self, doc_id: str) -> Path | None:
        manifest = self.repository.load_manifest(doc_id)
        raw_paths = [
            getattr(manifest, "manifest_path", "") if manifest is not None else "",
            getattr(manifest, "markdown_path", "") if manifest is not None else "",
        ]
        for raw_path in raw_paths:
            if not raw_path:
                continue
            try:
                candidate = Path(raw_path).expanduser().resolve()
            except (OSError, TypeError):
                continue
            doc_dir = candidate.parent if candidate.suffix else candidate
            if doc_dir.exists() and doc_dir.name == doc_id:
                return doc_dir
        repository_attrs = getattr(self.repository, "__dict__", {})
        for attr in ("base_dir", "root"):
            base_dir = repository_attrs.get(attr) if repository_attrs else None
            if not isinstance(base_dir, str | os.PathLike):
                continue
            try:
                root = Path(base_dir).expanduser().resolve()
                candidate = (root / doc_id).resolve()
                candidate.relative_to(root)
            except (OSError, ValueError):
                continue
            if candidate.exists():
                return candidate
        return None

    def _load_markdown_bounded(self, doc_id: str, doc_dir: Path) -> str:
        """Load canonical markdown only when it is small enough for previews."""
        candidates = [doc_dir / f"{doc_id}_full.md"]
        manifest = self.repository.load_manifest(doc_id)
        manifest_path = getattr(manifest, "markdown_path", "") if manifest else ""
        if manifest_path:
            safe_manifest_path = self._safe_manifest_artifact_path(
                doc_id,
                doc_dir,
                manifest_path,
            )
            if safe_manifest_path is not None:
                candidates.insert(0, safe_manifest_path)
        max_bytes = _markdown_max_bytes()
        for path in candidates:
            if not path.exists():
                continue
            try:
                if max_bytes > 0 and path.stat().st_size > max_bytes:
                    return ""
                return path.read_text(encoding="utf-8")
            except OSError:
                continue
        markdown = self.repository.load_markdown(doc_id) or ""
        if max_bytes > 0 and len(markdown.encode("utf-8")) > max_bytes:
            return ""
        return markdown

    def _safe_manifest_artifact_path(
        self,
        doc_id: str,
        doc_dir: Path,
        raw_path: str,
    ) -> Path | None:
        """Accept manifest paths only when they stay under the canonical doc dir."""
        try:
            candidate = Path(raw_path).expanduser().resolve()
            canonical_doc_dir = doc_dir.resolve()
            candidate.relative_to(canonical_doc_dir)
        except (OSError, ValueError):
            return None
        if candidate.name != f"{doc_id}_full.md":
            return None
        return candidate

    async def _ensure_current_pointer_index(
        self,
        doc_id: str,
        *,
        refresh: bool = False,
        allow_rebuild: bool = False,
    ) -> list[dict[str, Any]]:
        if refresh:
            await self.build_and_save_pointer_index(doc_id)
            return self.load_pointer_index(doc_id)

        records = self.load_pointer_index(doc_id)
        if records and await self._pointer_index_current(doc_id, records):
            return records

        if allow_rebuild:
            await self.build_and_save_pointer_index(doc_id)
            return self.load_pointer_index(doc_id)
        return []

    async def _pointer_index_current(
        self,
        doc_id: str,
        records: list[dict[str, Any]],
    ) -> bool:
        try:
            manifest = self.repository.load_manifest(doc_id)
            segmentation = await self.segmentation_service.export_document_segmentation(
                doc_id
            )
        except Exception:
            return False
        if manifest is None or not records:
            return False

        expected = {
            "doc_id": str(getattr(manifest, "doc_id", "") or ""),
            "source_pdf_sha256": str(getattr(manifest, "source_pdf_sha256", "") or ""),
            "source_revision_id": str(
                getattr(segmentation, "source_revision_id", "") or ""
            ),
            "locator_version": str(getattr(segmentation, "locator_version", "") or ""),
            "locator_source_sha256": str(
                getattr(segmentation, "locator_source_sha256", "") or ""
            ),
        }
        for record in records:
            if record.get("schema_version") != SECTION_POINTER_SCHEMA_VERSION:
                return False
            if str(record.get("doc_id", "") or "") != expected["doc_id"]:
                return False
            for key in (
                "source_pdf_sha256",
                "source_revision_id",
                "locator_version",
                "locator_source_sha256",
            ):
                if not _current_identity_matches(
                    key=key,
                    current=expected[key],
                    indexed=str(record.get(key, "") or ""),
                ):
                    return False
        return True

    async def retrieve(
        self,
        doc_id: str,
        query: str,
        *,
        limit: int = 5,
        refresh: bool = False,
    ) -> dict[str, Any]:
        records = await self._ensure_current_pointer_index(
            doc_id, refresh=refresh, allow_rebuild=False
        )
        if not records:
            return {
                "schema_version": SECTION_POINTER_SCHEMA_VERSION,
                "doc_id": doc_id,
                "query": query,
                "status": "needs_pointer_index",
                "blockers": ["missing_or_stale_section_pointer_index"],
                "result_count": 0,
                "results": [],
                "next_actions": [
                    f'document(op="pointer_index", doc_id="{doc_id}")',
                    f'document(op="structural_retrieve", doc_id="{doc_id}", query="...", refresh=true)',
                ],
            }
        doc_dir = self._existing_doc_dir(doc_id)
        markdown = self._load_markdown_bounded(doc_id, doc_dir) if doc_dir else ""
        matches = self.search_records(records, query, limit=max(1, min(limit, 25)))
        for match in matches:
            match["content_preview"] = self._materialize_preview(markdown, match)
        return {
            "schema_version": SECTION_POINTER_SCHEMA_VERSION,
            "doc_id": doc_id,
            "query": query,
            "result_count": len(matches),
            "results": matches,
            "next_actions": [
                f'document(op="structural_retrieve", doc_id="{doc_id}", query="...")',
                f'evidence(op="find", doc_id="{doc_id}", query="...")',
            ],
        }

    async def build_and_save_comparison_bundle(
        self,
        doc_a_id: str,
        doc_b_id: str,
        *,
        criteria: str,
        output_path: str | None = None,
        max_sections: int = 10,
        max_matches: int = 3,
        refresh: bool = False,
    ) -> tuple[Path, dict[str, Any]]:
        if not criteria.strip():
            raise ValueError("criteria or query is required for document comparison")
        a_records = await self._ensure_current_pointer_index(
            doc_a_id,
            refresh=refresh,
            allow_rebuild=True,
        )
        b_records = await self._ensure_current_pointer_index(
            doc_b_id,
            refresh=refresh,
            allow_rebuild=True,
        )
        selected = self.search_records(
            a_records,
            criteria,
            limit=max(1, min(max_sections, 50)),
        )
        if not selected:
            selected = a_records[: max(1, min(max_sections, 50))]

        pairs: list[dict[str, Any]] = []
        for left in selected:
            query = " ".join(
                part
                for part in (
                    criteria,
                    str(left.get("breadcrumb", "")),
                    str(left.get("text_preview", "")),
                )
                if part
            )
            right_matches = self.search_records(
                b_records,
                query,
                limit=max(1, min(max_matches, 10)),
            )
            pairs.append(
                self._comparison_pair(
                    left=left,
                    right_matches=right_matches,
                    criteria=criteria,
                )
            )

        doc_a_dir = self.repository.get_doc_dir(doc_a_id)
        safe_name = f"comparison_{doc_a_id}_vs_{doc_b_id}.json"
        target = resolve_document_output_path(
            doc_a_dir,
            output_path,
            default_name=safe_name,
            allowed_suffixes={".json"},
            reserved_names=_reserved_pointer_names(doc_a_id),
        )
        bundle = {
            "schema_version": DOCUMENT_COMPARISON_SCHEMA_VERSION,
            "doc_a_id": doc_a_id,
            "doc_b_id": doc_b_id,
            "criteria": criteria,
            "generated_at": datetime.now().isoformat(),
            "generator": "asset-aware-mcp",
            "mode": "deterministic_structural_pointer",
            "status": "needs_review",
            "summary": self._comparison_summary(pairs),
            "pairs": pairs,
            "next_actions": [
                "Review unmatched pairs before making absence claims.",
                "Promote verified pair evidence into an A2T comparison table.",
                f'document(op="structural_retrieve", doc_id="{doc_a_id}", query="...")',
                f'document(op="structural_retrieve", doc_id="{doc_b_id}", query="...")',
            ],
        }
        target.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), "utf-8")
        return target, bundle

    @staticmethod
    def search_records(
        records: list[dict[str, Any]],
        query: str,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        query_tokens = _tokens(query)
        scored: list[tuple[float, dict[str, Any]]] = []
        for record in records:
            haystack = " ".join(
                str(record.get(key, ""))
                for key in (
                    "breadcrumb",
                    "text_preview",
                    "content_sha256",
                    "pointer_id",
                )
            )
            haystack += " " + " ".join(map(str, record.get("asset_ids", [])))
            score = _lexical_score(query_tokens, haystack)
            if not query_tokens:
                score = 1.0
            if score <= 0:
                continue
            result = dict(record)
            result["score"] = round(score, 4)
            scored.append((score, result))
        scored.sort(
            key=lambda item: (
                -item[0],
                item[1].get("page_start") or 0,
                item[1].get("line_start")
                if item[1].get("line_start") is not None
                else 10**9,
                item[1].get("breadcrumb", ""),
            )
        )
        return [record for _score, record in scored[:limit]]

    def _build_records(
        self,
        *,
        manifest: Any,
        segmentation: Any,
        spans: list[Any],
    ) -> list[dict[str, Any]]:
        groups: dict[tuple[str, ...], dict[str, Any]] = {}
        root_title = manifest.title or manifest.filename or manifest.doc_id
        for segment in list(segmentation.segments):
            section_path = list(getattr(segment, "section_hierarchy", []) or [])
            if not section_path:
                section_path = [root_title]
            key = tuple(section_path)
            group = groups.setdefault(
                key,
                {
                    "section_path": section_path,
                    "segment_ids": [],
                    "asset_ids": [],
                    "segment_types": Counter(),
                    "pages": [],
                    "line_starts": [],
                    "line_ends": [],
                    "char_starts": [],
                    "char_ends": [],
                    "byte_starts": [],
                    "byte_ends": [],
                    "content_hasher": hashlib.sha256(),
                    "text_preview_parts": [],
                    "text_preview_chars": 0,
                    "has_text": False,
                    "source_revision_id": getattr(segment, "source_revision_id", ""),
                    "locator_version": getattr(segment, "locator_version", ""),
                    "locator_source_sha256": getattr(
                        segment, "locator_source_sha256", ""
                    ),
                },
            )
            group["segment_ids"].append(str(segment.segment_id))
            group["segment_types"][str(segment.segment_type)] += 1
            group["pages"].append(int(segment.page_number))
            if segment.line_start is not None:
                group["line_starts"].append(int(segment.line_start))
            if segment.line_end is not None:
                group["line_ends"].append(int(segment.line_end))
            if segment.char_start is not None:
                group["char_starts"].append(int(segment.char_start))
            if segment.char_end is not None:
                group["char_ends"].append(int(segment.char_end))
            if segment.byte_start is not None:
                group["byte_starts"].append(int(segment.byte_start))
            if segment.byte_end is not None:
                group["byte_ends"].append(int(segment.byte_end))
            if segment.asset_id:
                group["asset_ids"].append(str(segment.asset_id))
            if segment.text:
                self._append_group_text(group, str(segment.text))

        records = []
        for key, group in groups.items():
            section_path = list(key)
            line_start = min(group["line_starts"]) if group["line_starts"] else None
            line_end = max(group["line_ends"]) if group["line_ends"] else None
            char_start = min(group["char_starts"]) if group["char_starts"] else None
            char_end = max(group["char_ends"]) if group["char_ends"] else None
            byte_start = min(group["byte_starts"]) if group["byte_starts"] else None
            byte_end = max(group["byte_ends"]) if group["byte_ends"] else None
            pages = group["pages"]
            text_preview = "".join(group["text_preview_parts"]).strip()
            content_sha256 = (
                group["content_hasher"].hexdigest() if group["has_text"] else ""
            )
            asset_ids = sorted(set(group["asset_ids"]))
            evidence_span_ids = self._matching_span_ids(
                spans=spans,
                doc_id=manifest.doc_id,
                section_path=section_path,
                line_start=line_start,
                line_end=line_end,
                asset_ids=set(asset_ids),
                source_revision_id=str(group["source_revision_id"]),
                locator_version=str(group["locator_version"]),
                locator_source_sha256=str(group["locator_source_sha256"]),
            )
            seed = "|".join(
                [
                    manifest.doc_id,
                    str(group["source_revision_id"])[:16],
                    ">".join(section_path),
                    str(line_start),
                    str(line_end),
                    content_sha256[:16],
                ]
            )
            records.append(
                {
                    "schema_version": SECTION_POINTER_SCHEMA_VERSION,
                    "pointer_id": f"ptr_{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:16]}",
                    "doc_id": manifest.doc_id,
                    "section_path": section_path,
                    "breadcrumb": " > ".join(section_path),
                    "page_start": min(pages) if pages else None,
                    "page_end": max(pages) if pages else None,
                    "line_start": line_start,
                    "line_end": line_end,
                    "char_start": char_start,
                    "char_end": char_end,
                    "byte_start": byte_start,
                    "byte_end": byte_end,
                    "segment_ids": sorted(set(group["segment_ids"])),
                    "segment_count": len(group["segment_ids"]),
                    "segment_types": dict(sorted(group["segment_types"].items())),
                    "asset_ids": asset_ids,
                    "evidence_span_ids": evidence_span_ids,
                    "source_revision_id": group["source_revision_id"],
                    "source_pdf_sha256": manifest.source_pdf_sha256,
                    "locator_version": group["locator_version"],
                    "locator_source_sha256": group["locator_source_sha256"],
                    "locator_status": "complete"
                    if line_start is not None
                    and line_end is not None
                    and (char_start is not None or byte_start is not None)
                    else "partial",
                    "content_sha256": content_sha256,
                    "text_preview": _preview(text_preview, _PREVIEW_CHARS),
                }
            )
        records.sort(
            key=lambda record: (
                record.get("page_start") or 0,
                record.get("line_start")
                if record.get("line_start") is not None
                else 10**9,
                record.get("breadcrumb", ""),
            )
        )
        return records

    @staticmethod
    def _append_group_text(group: dict[str, Any], text: str) -> None:
        if group["has_text"]:
            group["content_hasher"].update(b"\n")
            if group["text_preview_chars"] < _PREVIEW_CHARS:
                group["text_preview_parts"].append("\n")
                group["text_preview_chars"] += 1
        group["has_text"] = True
        group["content_hasher"].update(text.encode("utf-8"))
        remaining = _PREVIEW_CHARS - int(group["text_preview_chars"])
        if remaining <= 0:
            return
        chunk = text[:remaining]
        group["text_preview_parts"].append(chunk)
        group["text_preview_chars"] += len(chunk)

    @staticmethod
    def _matching_span_ids(
        *,
        spans: list[Any],
        doc_id: str,
        section_path: list[str],
        line_start: int | None,
        line_end: int | None,
        asset_ids: set[str],
        source_revision_id: str,
        locator_version: str,
        locator_source_sha256: str,
    ) -> list[str]:
        matches: list[str] = []
        for span in spans:
            span_id = str(getattr(span, "span_id", "") or "")
            if not span_id:
                continue
            if str(getattr(span, "doc_id", "") or "") != doc_id:
                continue
            if not _same_locator_identity(
                span,
                source_revision_id=source_revision_id,
                locator_version=locator_version,
                locator_source_sha256=locator_source_sha256,
            ):
                continue
            if getattr(span, "asset_id", "") in asset_ids:
                matches.append(span_id)
                continue
            span_path = list(getattr(span, "section_hierarchy", []) or [])
            if span_path and (
                span_path == section_path
                or span_path[: len(section_path)] == section_path
                or section_path[: len(span_path)] == span_path
            ):
                matches.append(span_id)
                continue
            if _line_ranges_overlap(
                line_start,
                line_end,
                getattr(span, "line_start", None),
                getattr(span, "line_end", None),
            ):
                matches.append(span_id)
        return sorted(set(matches))

    @staticmethod
    def _materialize_preview(markdown: str, record: dict[str, Any]) -> str:
        line_start = record.get("line_start")
        line_end = record.get("line_end")
        if (
            markdown
            and isinstance(line_start, int)
            and isinstance(line_end, int)
            and 0 <= line_start <= line_end
        ):
            lines = markdown.splitlines()
            if line_start < len(lines):
                text = "\n".join(lines[line_start:line_end]).strip()
                if text:
                    return _preview(text, _CONTEXT_CHARS)
        return str(record.get("text_preview", ""))

    @staticmethod
    def _summary(
        *,
        doc_id: str,
        manifest: Any,
        segmentation: Any,
        records: list[dict[str, Any]],
        target: Path,
        markdown: str,
    ) -> dict[str, Any]:
        records_with_assets = [record for record in records if record["asset_ids"]]
        records_with_spans = [
            record for record in records if record["evidence_span_ids"]
        ]
        return {
            "schema_version": SECTION_POINTER_SCHEMA_VERSION,
            "doc_id": doc_id,
            "filename": manifest.filename,
            "title": manifest.title,
            "status": "ok" if records else "warning",
            "output_path": str(target),
            "generated_at": datetime.now().isoformat(),
            "source_revision_id": segmentation.source_revision_id,
            "locator_source_sha256": segmentation.locator_source_sha256,
            "metrics": {
                "pointer_count": len(records),
                "segment_count": len(segmentation.segments),
                "pointers_with_assets": len(records_with_assets),
                "pointers_with_evidence_spans": len(records_with_spans),
                "markdown_chars": len(markdown),
            },
            "issues": []
            if records
            else [{"severity": "warning", "reason": "no_pointers"}],
            "preview": records[:5],
        }

    @staticmethod
    def _comparison_pair(
        *,
        left: dict[str, Any],
        right_matches: list[dict[str, Any]],
        criteria: str,
    ) -> dict[str, Any]:
        right = right_matches[0] if right_matches else {}
        pair_seed = "|".join(
            [
                str(left.get("pointer_id", "")),
                str(right.get("pointer_id", "")),
                hashlib.sha256(criteria.encode("utf-8")).hexdigest()[:12],
            ]
        )
        shared_terms = sorted(
            _tokens(
                str(left.get("breadcrumb", ""))
                + " "
                + str(left.get("text_preview", ""))
            )
            & _tokens(
                str(right.get("breadcrumb", ""))
                + " "
                + str(right.get("text_preview", ""))
            )
        )
        return {
            "pair_id": f"cmp_{hashlib.sha256(pair_seed.encode('utf-8')).hexdigest()[:16]}",
            "status": "candidate" if right_matches else "unmatched",
            "rating": "needs_review" if right_matches else "missing_counterpart",
            "left_pointer": _comparison_pointer(left),
            "right_matches": [_comparison_pointer(match) for match in right_matches],
            "shared_terms": shared_terms[:25],
            "risk": (
                "no_counterpart_retrieved"
                if not right_matches
                else "requires_human_or_llm_review"
            ),
        }

    @staticmethod
    def _comparison_summary(pairs: list[dict[str, Any]]) -> dict[str, Any]:
        statuses = Counter(str(pair.get("status", "unknown")) for pair in pairs)
        return {
            "selected_pairs": len(pairs),
            "candidate_pairs": statuses.get("candidate", 0),
            "unmatched_pairs": statuses.get("unmatched", 0),
            "ratings": dict(
                Counter(str(pair.get("rating", "unknown")) for pair in pairs)
            ),
        }


def _comparison_pointer(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "pointer_id": record.get("pointer_id", ""),
        "doc_id": record.get("doc_id", ""),
        "breadcrumb": record.get("breadcrumb", ""),
        "page_range": [record.get("page_start"), record.get("page_end")],
        "line_range": [record.get("line_start"), record.get("line_end")],
        "asset_ids": record.get("asset_ids", []),
        "evidence_span_ids": record.get("evidence_span_ids", []),
        "score": record.get("score"),
        "text_preview": record.get("text_preview", ""),
        "source_revision_id": record.get("source_revision_id", ""),
        "source_pdf_sha256": record.get("source_pdf_sha256", ""),
        "locator_source_sha256": record.get("locator_source_sha256", ""),
    }


def _same_locator_identity(
    span: Any,
    *,
    source_revision_id: str,
    locator_version: str,
    locator_source_sha256: str,
) -> bool:
    for attr, expected in (
        ("source_revision_id", source_revision_id),
        ("locator_version", locator_version),
        ("locator_source_sha256", locator_source_sha256),
    ):
        expected_value = str(expected or "")
        if not expected_value:
            return False
        if str(getattr(span, attr, "") or "") != expected_value:
            return False
    return True


def _current_identity_matches(*, key: str, current: str, indexed: str) -> bool:
    if key == "source_pdf_sha256" and not current:
        return indexed == ""
    if not current:
        return False
    return indexed == current


def _reserved_pointer_names(doc_id: str) -> set[str]:
    return {
        f"{doc_id}_manifest.json",
        f"{doc_id}_full.md",
        "blocks.json",
        "citation_index.jsonl",
        "citation_index.status.json",
        "segmentation.json",
        "ai_safety_report.json",
        "native_structure.json",
        "segmentation_coverage.json",
        "accessibility_report.json",
    }


def _tokens(text: str) -> set[str]:
    tokens = {token.lower() for token in _TOKEN_RE.findall(text) if len(token) > 1}
    cjk_chars = _CJK_RE.findall(text)
    tokens.update(cjk_chars)
    tokens.update("".join(pair) for pair in pairwise(cjk_chars))
    return tokens


def _lexical_score(query_tokens: set[str], haystack: str) -> float:
    if not query_tokens:
        return 0.0
    hay_tokens = _tokens(haystack)
    if not hay_tokens:
        return 0.0
    overlap = query_tokens & hay_tokens
    if not overlap:
        return 0.0
    hay_lower = haystack.lower()
    exact_hits = sum(hay_lower.count(token) for token in overlap)
    return len(overlap) * 2.0 + exact_hits + (len(overlap) / len(query_tokens))


def _line_ranges_overlap(
    a_start: int | None,
    a_end: int | None,
    b_start: int | None,
    b_end: int | None,
) -> bool:
    if a_start is None or a_end is None or b_start is None or b_end is None:
        return False
    return int(a_start) < int(b_end) and int(b_start) < int(a_end)


def _preview(text: str, max_chars: int) -> str:
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars]}... [truncated chars={len(normalized)}]"


def _markdown_max_bytes() -> int:
    raw = os.environ.get(STRUCTURAL_POINTER_MARKDOWN_MAX_BYTES_ENV, "").strip()
    if not raw:
        return DEFAULT_STRUCTURAL_POINTER_MARKDOWN_MAX_BYTES
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_STRUCTURAL_POINTER_MARKDOWN_MAX_BYTES


def _pointer_index_max_bytes() -> int:
    raw = os.environ.get(STRUCTURAL_POINTER_INDEX_MAX_BYTES_ENV, "").strip()
    if not raw:
        return DEFAULT_STRUCTURAL_POINTER_INDEX_MAX_BYTES
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_STRUCTURAL_POINTER_INDEX_MAX_BYTES


def _pointer_index_max_records() -> int:
    raw = os.environ.get(STRUCTURAL_POINTER_INDEX_MAX_RECORDS_ENV, "").strip()
    if not raw:
        return DEFAULT_STRUCTURAL_POINTER_INDEX_MAX_RECORDS
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_STRUCTURAL_POINTER_INDEX_MAX_RECORDS
