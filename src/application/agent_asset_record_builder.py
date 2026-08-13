"""Build portable agent asset records from segmentation and manifest assets."""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.application.agent_asset_bundle_format import (
    DEFAULT_MAX_BUNDLE_RECORDS,
    RECORD_VERSION,
    AgentAssetBundleLimitError,
    BundleOutputBudget,
    canonical_json,
    file_sha256,
    note_metadata,
    sha256_text,
    slug,
)

SpanRefFactory = Callable[[Any], dict[str, Any]]
AssetRefFactory = Callable[[Any, str, Any], dict[str, Any]]
_KIND_ORDER = {"text": 0, "table": 1, "figure": 2}
_IMAGE_SUFFIXES = {"gif", "jpeg", "jpg", "png", "webp"}
_COPY_CHUNK_BYTES = 1024 * 1024


@dataclass
class _EvidenceIndex:
    """Linear-time lookup preserving the citation index's stable order."""

    by_block: dict[str, list[Any]] = field(default_factory=dict)
    by_asset: dict[str, list[Any]] = field(default_factory=dict)
    positions: dict[int, int] = field(default_factory=dict)


class AgentAssetRecordBuilder:
    """Map document assets to deterministic records without touching sources."""

    def __init__(
        self,
        span_ref_factory: SpanRefFactory,
        asset_ref_factory: AssetRefFactory,
        *,
        max_records: int = DEFAULT_MAX_BUNDLE_RECORDS,
        output_budget: BundleOutputBudget | None = None,
    ) -> None:
        if max_records <= 0:
            raise ValueError("max bundle records must be > 0")
        self.span_ref_factory = span_ref_factory
        self.asset_ref_factory = asset_ref_factory
        self.max_records = max_records
        self.output_budget = output_budget or BundleOutputBudget()

    def build(
        self,
        manifest: Any,
        segmentation: Any,
        spans: list[Any],
        source_identity: dict[str, Any],
        stage: Path,
        doc_dir: Path,
    ) -> list[dict[str, Any]]:
        text_record_count = sum(
            segment.segment_type not in {"Table", "Picture"}
            and bool(segment.text.strip())
            for segment in segmentation.segments
        )
        record_count = (
            text_record_count
            + len(manifest.assets.tables)
            + len(manifest.assets.figures)
        )
        if record_count > self.max_records:
            raise AgentAssetBundleLimitError("records", record_count, self.max_records)

        segment_by_asset = {
            segment.asset_id: segment
            for segment in segmentation.segments
            if segment.asset_id
        }
        evidence_index = self._index_evidence(spans)
        records = self._text_records(segmentation, evidence_index, source_identity)
        records.extend(
            self._table_records(
                manifest, segment_by_asset, evidence_index, source_identity
            )
        )
        records.extend(
            self._figure_records(
                manifest,
                segment_by_asset,
                evidence_index,
                source_identity,
                stage,
                doc_dir,
            )
        )
        records.sort(key=self._record_sort_key)
        return records

    def _text_records(
        self,
        segmentation: Any,
        evidence_index: _EvidenceIndex,
        source_identity: dict[str, Any],
    ) -> list[dict[str, Any]]:
        records = []
        for segment in segmentation.segments:
            if segment.segment_type in {"Table", "Picture"} or not segment.text.strip():
                continue
            block_id = str(
                segment.metadata.get("source_block_id") or segment.segment_id
            )
            records.append(
                self._base_record(
                    "text",
                    segment.segment_id,
                    source_identity,
                    self._segment_locator(segment),
                    {"text": segment.text, "segment_type": segment.segment_type},
                    segment.text_sha256 or sha256_text(segment.text),
                    self._evidence_refs(evidence_index, block_id, ""),
                )
            )
        return records

    def _table_records(
        self,
        manifest: Any,
        segment_by_asset: dict[str, Any],
        evidence_index: _EvidenceIndex,
        source_identity: dict[str, Any],
    ) -> list[dict[str, Any]]:
        records = []
        for table in manifest.assets.tables:
            content = {
                "caption": table.caption,
                "markdown": table.markdown,
                "preview": table.preview,
                "rows": table.row_count,
                "columns": table.col_count,
            }
            records.append(
                self._base_record(
                    "table",
                    table.id,
                    source_identity,
                    self._asset_locator(table, segment_by_asset.get(table.id)),
                    content,
                    sha256_text(table.markdown or table.preview or table.caption),
                    self._evidence_refs(
                        evidence_index, table.source_block_id, table.id
                    ),
                    primary_ref=self.asset_ref_factory(manifest, "table", table),
                )
            )
        return records

    def _figure_records(
        self,
        manifest: Any,
        segment_by_asset: dict[str, Any],
        evidence_index: _EvidenceIndex,
        source_identity: dict[str, Any],
        stage: Path,
        doc_dir: Path,
    ) -> list[dict[str, Any]]:
        records = []
        for figure in manifest.assets.figures:
            media = self._copy_figure(stage, doc_dir, figure)
            content = {
                "caption": figure.caption,
                "media_path": media.get("path", ""),
                "media_sha256": media.get("sha256", ""),
                "media_available": bool(media),
                "format": figure.ext,
                "width": figure.width,
                "height": figure.height,
            }
            records.append(
                self._base_record(
                    "figure",
                    figure.id,
                    source_identity,
                    self._asset_locator(figure, segment_by_asset.get(figure.id)),
                    content,
                    str(media.get("sha256") or sha256_text(figure.caption)),
                    self._evidence_refs(
                        evidence_index, figure.source_block_id, figure.id
                    ),
                    primary_ref=self.asset_ref_factory(manifest, "figure", figure),
                )
            )
        return records

    @staticmethod
    def _index_evidence(spans: list[Any]) -> _EvidenceIndex:
        index = _EvidenceIndex()
        for position, span in enumerate(spans):
            index.positions[id(span)] = position
            block_id = str(span.block_id or "")
            asset_id = str(span.asset_id or "")
            if block_id:
                index.by_block.setdefault(block_id, []).append(span)
            if asset_id:
                index.by_asset.setdefault(asset_id, []).append(span)
        return index

    def _evidence_refs(
        self,
        evidence_index: _EvidenceIndex,
        block_id: str,
        asset_id: str,
    ) -> list[dict[str, Any]]:
        matches_by_identity: dict[int, Any] = {}
        if block_id:
            matches_by_identity.update(
                (id(span), span) for span in evidence_index.by_block.get(block_id, [])
            )
        if asset_id:
            matches_by_identity.update(
                (id(span), span) for span in evidence_index.by_asset.get(asset_id, [])
            )
        matches = sorted(
            matches_by_identity.values(),
            key=lambda span: evidence_index.positions[id(span)],
        )
        return [self.span_ref_factory(span) for span in matches]

    @staticmethod
    def _segment_locator(segment: Any) -> dict[str, Any]:
        bbox = []
        if None not in (segment.left, segment.top, segment.width, segment.height):
            bbox = [
                segment.left,
                segment.top,
                segment.left + segment.width,
                segment.top + segment.height,
            ]
        return {
            "page": segment.page_number,
            "bbox": bbox,
            "line_range": [segment.line_start, segment.line_end],
            "char_range": [segment.char_start, segment.char_end],
            "byte_range": [segment.byte_start, segment.byte_end],
            "section_hierarchy": list(segment.section_hierarchy),
            "block_id": str(segment.metadata.get("source_block_id") or ""),
            "reading_order": segment.reading_order,
            "source_revision_id": segment.source_revision_id,
            "locator_version": segment.locator_version,
            "locator_source_sha256": segment.locator_source_sha256,
        }

    @classmethod
    def _asset_locator(cls, asset: Any, segment: Any | None) -> dict[str, Any]:
        if segment is not None:
            return cls._segment_locator(segment)
        return {
            "page": asset.page,
            "bbox": list(getattr(asset, "figure_bbox", []) or []),
            "line_range": [asset.line_start, asset.line_end],
            "char_range": [None, None],
            "byte_range": [None, None],
            "section_hierarchy": [asset.section_title] if asset.section_title else [],
            "block_id": asset.source_block_id,
            "reading_order": asset.source_order,
            "source_revision_id": "",
            "locator_version": "asset-manifest-v1",
            "locator_source_sha256": "",
        }

    def _base_record(
        self,
        kind: str,
        asset_id: str,
        source_identity: dict[str, Any],
        locator: dict[str, Any],
        content: dict[str, Any],
        content_sha256: str,
        evidence_refs: list[dict[str, Any]],
        *,
        primary_ref: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        asset_key = f"{kind}:{asset_id}"
        record = {
            "record_version": RECORD_VERSION,
            "asset_key": asset_key,
            "asset_id": asset_id,
            "asset_type": kind,
            "doc_id": source_identity["doc_id"],
            "source_identity": source_identity,
            "locator": locator,
            "content": content,
            "content_sha256": content_sha256,
            "citation": {
                "status": "citation_ready"
                if evidence_refs
                else ("asset_locator_only" if primary_ref else "unavailable"),
                "asset_ref": primary_ref or (evidence_refs[0] if evidence_refs else {}),
                "evidence_refs": evidence_refs,
            },
            "foam": note_metadata(asset_key, source_identity["doc_id"]),
        }
        record["record_sha256"] = sha256_text(canonical_json(record))
        self.output_budget.project(len(canonical_json(record).encode("utf-8")))
        return record

    def _copy_figure(self, stage: Path, doc_dir: Path, figure: Any) -> dict[str, Any]:
        source = Path(str(figure.path))
        if not source.is_absolute():
            source = doc_dir / source
        try:
            source = source.resolve(strict=True)
            source.relative_to(doc_dir)
        except (FileNotFoundError, ValueError):
            return {}
        suffix = re.sub(r"[^a-z0-9]", "", source.suffix.lower().lstrip("."))
        if not source.is_file() or suffix not in _IMAGE_SUFFIXES:
            return {}
        return self._copy_figure_snapshot(stage, source, figure.id, suffix)

    def _copy_figure_snapshot(
        self,
        stage: Path,
        source: Path,
        figure_id: str,
        suffix: str,
    ) -> dict[str, Any]:
        """Atomically stage and hash the exact bytes read from one source handle."""
        media_dir = stage / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        temporary = media_dir / f".{slug(figure_id)}.copying-{uuid.uuid4().hex}"
        digest = hashlib.sha256()

        try:
            with (
                source.open("rb") as source_handle,
                temporary.open("xb") as target_handle,
            ):
                initial_stat = os.fstat(source_handle.fileno())
                while chunk := source_handle.read(_COPY_CHUNK_BYTES):
                    self.output_budget.reserve(len(chunk))
                    digest.update(chunk)
                    target_handle.write(chunk)
                final_stat = os.fstat(source_handle.fileno())

            try:
                current_path_stat = source.stat()
            except OSError as exc:
                raise ValueError(
                    f"Figure source changed during agent asset export: {source}"
                ) from exc
            if not (
                self._same_file_snapshot(initial_stat, final_stat)
                and self._same_file_snapshot(initial_stat, current_path_stat)
            ):
                raise ValueError(
                    f"Figure source changed during agent asset export: {source}"
                )

            snapshot_sha256 = digest.hexdigest()
            filename = f"{slug(figure_id)}-{snapshot_sha256[:12]}.{suffix}"
            snapshot_path = media_dir / filename
            temporary.replace(snapshot_path)
            if file_sha256(snapshot_path) != snapshot_sha256:
                snapshot_path.unlink(missing_ok=True)
                raise ValueError(
                    f"Figure snapshot hash verification failed during export: {source}"
                )
            return {
                "path": f"media/{filename}",
                "sha256": snapshot_sha256,
            }
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    @staticmethod
    def _same_file_snapshot(left: Any, right: Any) -> bool:
        return (
            int(left.st_dev),
            int(left.st_ino),
            int(left.st_size),
            int(left.st_mtime_ns),
        ) == (
            int(right.st_dev),
            int(right.st_ino),
            int(right.st_size),
            int(right.st_mtime_ns),
        )

    @staticmethod
    def _record_sort_key(record: dict[str, Any]) -> tuple[int, int, int, str]:
        locator = record["locator"]
        return (
            _KIND_ORDER[record["asset_type"]],
            locator.get("page") or 0,
            locator.get("reading_order") or 0,
            record["asset_id"],
        )
