"""Capture complete extraction evidence and resolve immutable citation sources."""

from __future__ import annotations

import json
import re
from pathlib import PurePath
from typing import TYPE_CHECKING, Any

from src.application.csl_citation_service import canonical, citation_page, digest
from src.application.etl_references import (
    _asset_ref_from_manifest_asset,
    _strict_json_equal,
    asset_ref_from_span,
    verify_asset_reference,
    verify_span_reference,
)
from src.domain.citation import build_evidence_spans
from src.domain.entities import DocumentManifest
from src.domain.etl_evidence import (
    MAX_ETL_RECORD_BYTES,
    MAX_ETL_SNAPSHOT_BYTES,
    EtlEvidenceReference,
    EtlSourceSelector,
)
from src.domain.native_pdf import NativePdfPageLocator

if TYPE_CHECKING:
    from src.domain.etl_evidence import EtlSnapshotRepository, EtlSourceReader
    from src.domain.native_pdf import NativePdfAdapter


class EtlEvidenceService:
    def __init__(
        self,
        source: EtlSourceReader,
        repository: EtlSnapshotRepository,
        pdfs: NativePdfAdapter,
    ):
        self.source, self.repository, self.pdfs = source, repository, pdfs

    def inspect(self, selector: EtlSourceSelector) -> dict[str, Any]:
        files = self.source.capture(
            selector.doc_id,
            selector.source_id if selector.source_type == "figure" else None,
        )
        manifest = DocumentManifest.model_validate_json(
            self.source.decode_text(files["source-manifest.json"])
        )
        if selector.source_type == "span":
            blocks = json.loads(self.source.decode_text(files["blocks.json"]))
            if not isinstance(blocks, list) or any(
                not isinstance(block, dict) for block in blocks
            ):
                raise ValueError("ETL blocks must be a complete JSON array of objects")
            spans = build_evidence_spans(
                doc_id=selector.doc_id,
                markdown=self.source.decode_text(files["canonical.md"]),
                blocks=blocks,
                source_backend=manifest.source_engine,
            )
            span = next((s for s in spans if s.span_id == selector.source_id), None)
            if span is None:
                raise ValueError("ETL span not found in current canonical artifacts")
            ref = asset_ref_from_span(span)
        else:
            asset = (
                manifest.assets.find_table(selector.source_id)
                if selector.source_type == "table"
                else manifest.assets.find_figure(selector.source_id)
            )
            if asset is None:
                raise ValueError("ETL asset not found")
            ref = _asset_ref_from_manifest_asset(manifest, selector.source_type, asset)
        return {"asset_ref": ref, "record": self._record(ref, files)}

    def _record(self, ref: dict[str, Any], files: dict[str, bytes]) -> dict[str, Any]:
        if len(canonical(ref)) > MAX_ETL_RECORD_BYTES:
            raise ValueError("ETL reference exceeds its byte limit")
        if ref.get("canonical_asset_ref") is False:
            raise ValueError("ETL capture requires a complete reference, not a preview")
        source_type = ref.get("source_type")
        if source_type not in {"span", "table", "figure"}:
            raise ValueError(
                "ETL capture requires a canonical span/table/figure reference"
            )
        manifest = DocumentManifest.model_validate_json(
            self.source.decode_text(files["source-manifest.json"])
        )
        if manifest.doc_id != ref.get("doc_id"):
            raise ValueError("ETL document identity mismatch")
        suffix = PurePath(manifest.filename).suffix.lower()
        source_name = "original" + suffix
        if (
            re.fullmatch(r"[a-f0-9]{64}", manifest.source_pdf_sha256) is None
            or source_name not in files
            or digest(files[source_name]) != manifest.source_pdf_sha256
        ):
            raise ValueError("ETL original source bytes do not match the manifest hash")
        markdown = self.source.decode_text(files["canonical.md"])
        blocks = json.loads(self.source.decode_text(files["blocks.json"]))
        if not isinstance(blocks, list) or any(not isinstance(b, dict) for b in blocks):
            raise ValueError("ETL blocks must be a complete JSON array of objects")
        if source_type == "span":
            # Rebuild from the captured artifacts; never trust a persisted index that
            # could contain forged text with otherwise matching revision metadata.
            spans = build_evidence_spans(
                doc_id=manifest.doc_id,
                markdown=markdown,
                blocks=blocks,
                source_backend=manifest.source_engine,
            )
            span = next((s for s in spans if s.span_id == ref.get("span_id")), None)
            verification = verify_span_reference(ref, span)
            evidence = span.model_dump(mode="json") if span is not None else {}
            expected_ref = asset_ref_from_span(span) if span is not None else {}
        else:
            verification = verify_asset_reference(ref, manifest)
            asset = (
                manifest.assets.find_table(str(ref.get("asset_id", "")))
                if source_type == "table"
                else manifest.assets.find_figure(str(ref.get("asset_id", "")))
            )
            evidence = asset.model_dump(mode="json") if asset is not None else {}
            expected_ref = (
                _asset_ref_from_manifest_asset(manifest, source_type, asset)
                if asset is not None
                else {}
            )
        if not verification["valid"]:
            raise ValueError(
                "ETL reference failed verification: "
                + ", ".join(verification["issues"])
            )
        for field in (set(expected_ref) | set(ref)) - {"label", "craap"}:
            if (
                field not in ref
                or field not in expected_ref
                or not _strict_json_equal(ref[field], expected_ref[field])
            ):
                raise ValueError("ETL complete reference failed verification: " + field)
        images = sorted(
            name for name in files if name.startswith(("figure.", "raw-figure."))
        )
        expected = {"source-manifest.json", "canonical.md", "blocks.json", source_name}
        if source_type == "figure":
            if sum(name.startswith("figure.") for name in images) != 1:
                raise ValueError("ETL figure snapshot requires its complete image")
            expected.update(images)
        if set(files) != expected:
            raise ValueError("Unexpected ETL captured artifact inventory")
        record = {
            "schema_version": "etl-evidence-record-v1",
            "source_reference": ref,
            "source_file": source_name,
            "source_identity": {
                "doc_id": manifest.doc_id,
                "filename": manifest.filename,
                "source_sha256": manifest.source_pdf_sha256,
                "source_engine": manifest.source_engine,
                "selected_page_map": manifest.selected_page_map,
                "canonical_markdown_sha256": digest(markdown.encode("utf-8")),
                "text_normalization": "existing encoding guard: decoded Unicode, BOM removed, LF line endings; raw bytes retained separately",
            },
            "evidence": evidence,
            "verification": verification,
            "checks": {
                "original_source_hash": True,
                "reference_locators": True,
                "span_rebuilt_from_canonical_artifacts": source_type == "span",
            },
            "artifacts": {
                name: {"sha256": digest(data), "size_bytes": len(data)}
                for name, data in sorted(files.items())
            },
            "review_required": [
                "extraction_accuracy",
                "semantic_support",
                "bibliographic_metadata",
                "printed_locator_correspondence",
                "source_page_rendering",
            ],
            "annotation_scope": "caller reference labels/CRAAP annotations are preserved, not assessed",
        }
        if len(canonical(record)) > MAX_ETL_RECORD_BYTES:
            raise ValueError("ETL complete evidence record exceeds its byte limit")
        return record

    @staticmethod
    def _reference(record: dict[str, Any], snapshot: str) -> EtlEvidenceReference:
        ref = record["source_reference"]
        return EtlEvidenceReference(
            snapshot_id=snapshot,
            record_sha256=digest(canonical(record)),
            doc_id=ref["doc_id"],
            source_type=ref["source_type"],
            source_id=ref["span_id"]
            if ref["source_type"] == "span"
            else ref["asset_id"],
            source_sha256=record["source_identity"]["source_sha256"],
        )

    def capture(
        self, ref: dict[str, Any], expected_hash: str | None = None
    ) -> dict[str, Any]:
        if len(canonical(ref)) > MAX_ETL_RECORD_BYTES:
            raise ValueError("ETL reference exceeds its byte limit")
        if ref.get("source_type") not in {"span", "table", "figure"}:
            raise ValueError(
                "ETL capture requires a canonical span/table/figure reference"
            )
        doc_id = ref.get("doc_id")
        if not isinstance(doc_id, str):
            raise ValueError("ETL capture requires a document ID")
        figure_id = ref.get("asset_id") if ref["source_type"] == "figure" else None
        if ref["source_type"] == "figure" and (
            not isinstance(figure_id, str) or not figure_id
        ):
            raise ValueError("ETL capture requires a figure ID")
        files = self.source.capture(doc_id, figure_id)
        record = self._record(ref, files)
        files = {**files, "evidence.json": canonical(record)}
        manifest = {
            "schema_version": "etl-evidence-snapshot-v1",
            "record_sha256": digest(files["evidence.json"]),
            "files": {
                name: {"sha256": digest(data), "size_bytes": len(data)}
                for name, data in sorted(files.items())
            },
        }
        files["manifest.json"] = canonical(manifest)
        snapshot = digest(files["manifest.json"])
        reference = self._reference(record, snapshot)
        result = {"reference": reference.model_dump(mode="json"), "record": record}
        citation_page(result, 0, 4000, expected_hash)
        if sum(map(len, files.values())) > MAX_ETL_SNAPSHOT_BYTES:
            raise ValueError("ETL snapshot exceeds its byte limit")
        self.repository.save(snapshot, files)
        return result

    def resolve(
        self, reference: EtlEvidenceReference
    ) -> tuple[dict[str, Any], dict[str, bytes]]:
        files = self.repository.read(reference.snapshot_id)
        encoded = files["evidence.json"]
        if (
            len(encoded) > MAX_ETL_RECORD_BYTES
            or digest(encoded) != reference.record_sha256
        ):
            raise ValueError("ETL evidence record hash mismatch")
        record = json.loads(encoded)
        if not isinstance(record, dict) or not isinstance(
            record.get("source_reference"), dict
        ):
            raise ValueError("Invalid ETL evidence record")
        original = {
            name: data
            for name, data in files.items()
            if name not in {"manifest.json", "evidence.json"}
        }
        rebuilt = self._record(record["source_reference"], original)
        if (
            canonical(rebuilt) != encoded
            or self._reference(rebuilt, reference.snapshot_id) != reference
        ):
            raise ValueError("ETL snapshot reference/content mismatch")
        return record, files

    def read(self, reference: EtlEvidenceReference) -> dict[str, Any]:
        record, _ = self.resolve(reference)
        return {"reference": reference.model_dump(mode="json"), "record": record}

    def view(self, reference: EtlEvidenceReference, size: int) -> dict[str, Any]:
        if type(size) is not int or not 64 <= size <= 2048:
            raise ValueError("ETL render_size must be 64..2048")
        record, files = self.resolve(reference)
        page = record["source_reference"].get("page")
        if record["source_file"] != "original.pdf" or type(page) is not int or page < 1:
            raise ValueError(
                "ETL page preview requires a captured PDF and known source page"
            )
        data = files[record["source_file"]]
        pages = self.pdfs.inspect(data)["pages"]
        if page > len(pages):
            raise ValueError("ETL source page is outside the captured PDF")
        locator = NativePdfPageLocator.model_validate(pages[page - 1]["locator"])
        png = self.pdfs.render(data, locator, size)
        return {
            "success": True,
            "reference": reference.model_dump(mode="json"),
            "source_page": page,
            "render_size": size,
            "image_sha256": digest(png),
            "image_png": png,
            "view_scope": "whole captured original PDF page; extraction/semantic accuracy requires Agent review",
        }
