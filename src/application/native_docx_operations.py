"""Managed native DOCX reads/edits, preserving immutable source identity."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, Literal

from src.application.native_document_contract import native_asset_summary
from src.application.native_docx_records import docx_block_excerpt
from src.domain.native_docx_structure import DOCX_MEDIA_TYPE

if TYPE_CHECKING:
    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeDocumentRequest,
        NativeDocxBlockReference,
    )
    from src.domain.native_docx import NativeDocxAdapter
    from src.domain.native_docx_structure import NativeDocxStructureAdapter
    from src.domain.native_rendering import NativeWordRenderer


class NativeDocxOperations:
    def __init__(
        self,
        repository: NativeAssetRepository,
        docx: NativeDocxAdapter,
        structure: NativeDocxStructureAdapter | None = None,
        renderer: NativeWordRenderer | None = None,
    ):
        self.repository = repository
        self.docx = docx
        self.structure = structure
        self.renderer = renderer

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        return {
            "render_docx_page": self._render,
            "create_docx": self._create,
            "add_docx_blocks": self._structure,
            "delete_docx_blocks": self._structure,
            "read_docx": self._read,
            "update_docx": self._update,
            "read_docx_block": self._read_block,
        }[request.op](request)

    def _render(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.renderer is None:
            raise ValueError("Native DOCX renderer is not configured")
        assert request.asset_id is not None and request.revision is not None
        assert request.docx_page_index is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "docx":
            raise ValueError("This format has no native DOCX page renderer")
        data = self.repository.read(asset.asset_id, request.revision)
        return {
            **self.renderer.render(data, request.docx_page_index, request.render_size),
            "success": True,
            "asset_id": asset.asset_id,
            "inspected_revision": request.revision,
            "docx_page_index": request.docx_page_index,
            "source_written": False,
            "review_required": [
                "semantic_accuracy",
                "rendered_layout",
                "page_flow",
                "inherited_formatting",
                "fields_and_revisions",
            ],
        }

    def _create(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.structure is None:
            raise ValueError("Native DOCX structure adapter is not configured")
        assert request.docx_create is not None
        data = self.structure.create(request.docx_create)
        asset = self.repository.create(
            request.docx_create.name, data, "docx", DOCX_MEDIA_TYPE
        )
        return {
            "success": True,
            "asset": native_asset_summary(asset, docx_enabled=True),
            "source_written": False,
            "review_request": {
                "op": "read_docx",
                "asset_id": asset.asset_id,
                "revision": asset.revision,
            },
            "review_required": [
                "semantic_accuracy",
                "rendered_layout",
                "page_flow",
                "inherited_formatting",
            ],
        }

    def _positions(
        self,
        data: bytes,
        asset_id: str,
        revision: str,
        references: list[NativeDocxBlockReference],
    ) -> list[int]:
        if not references:
            return []
        records = self.docx.decompose(data, asset_id, revision).blocks
        lookup = {record["block_id"]: record for record in records}
        positions = []
        for reference in references:
            record = lookup.get(reference.locator.block_id)
            if record is None or record["evidence"] != reference.model_dump():
                raise ValueError(
                    "DOCX structural reference differs from the current asset/revision"
                )
            meta = record["representation"].get("metadata", {})
            if (
                meta.get("source_part") != "word/document.xml"
                or meta.get("source_story") != "body"
                or meta.get("source_element") not in {"w:p", "w:tbl"}
                or any(
                    key in meta
                    for key in ("parent_table_id", "parent_cell", "sdt_index")
                )
                or type(meta.get("source_order")) is not int
            ):
                raise ValueError(
                    "DOCX structural targets must be complete top-level body paragraphs/tables"
                )
            position = meta["source_order"]
            if meta["source_element"] == "w:p":
                same = [
                    r
                    for r in records
                    if r["representation"].get("metadata", {}).get("source_part")
                    == "word/document.xml"
                    and r["representation"].get("metadata", {}).get("source_order")
                    == position
                    and "parent_table_id" not in r["representation"].get("metadata", {})
                ]
                if len(same) != 1:
                    raise ValueError(
                        "DOCX reference covers only part of a multi-block paragraph"
                    )
            positions.append(position)
        return positions

    def _structure(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.structure is None:
            raise ValueError("Native DOCX structure adapter is not configured")
        assert request.asset_id is not None and request.expected_revision is not None
        asset = self.repository.load(request.asset_id)
        if (
            asset.format != "docx"
            or asset.archived
            or asset.revision != request.expected_revision
        ):
            raise ValueError(
                "Wrong format, archived or stale native DOCX; inspect before editing"
            )
        data = self.repository.read(asset.asset_id, request.expected_revision)
        if request.op == "add_docx_blocks":
            assert request.docx_insert is not None
            item = request.docx_insert
            position: int | Literal["start", "end"]
            if item.position in {"start", "end"}:
                position = item.position
            else:
                assert item.anchor is not None
                position = self._positions(
                    data, asset.asset_id, asset.revision, [item.anchor]
                )[0] + (item.position == "after")
            updated, checks = self.structure.insert(data, item.blocks, position)
        else:
            positions = self._positions(
                data, asset.asset_id, asset.revision, request.docx_block_refs
            )
            updated, checks = self.structure.delete(data, positions)
        committed = self.repository.commit(
            asset.asset_id, request.expected_revision, updated, checks
        )
        return {
            "success": True,
            "asset": native_asset_summary(committed, docx_enabled=True),
            "source_written": False,
            "operation_result": checks.model_dump(),
            "review_request": {
                "op": "read_docx",
                "asset_id": asset.asset_id,
                "revision": committed.revision,
            },
        }

    def _read_block(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None and request.block_id is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "docx":
            raise ValueError("This format has no native DOCX block reader")
        revision = request.revision or asset.revision
        record = self.docx.read_block(
            self.repository.read(asset.asset_id, revision),
            asset.asset_id,
            revision,
            request.block_id,
        )
        return {
            "success": True,
            "asset_id": asset.asset_id,
            "inspected_revision": revision,
            "block": docx_block_excerpt(
                record, request.text_offset, request.text_limit
            ),
            "review_required": [
                "semantic_accuracy",
                "rendered_layout",
                "fields_and_revisions",
            ],
        }

    def _read(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "docx" or self.docx is None:
            raise ValueError("This format has no configured native DOCX bridge")
        revision = request.revision or asset.revision
        document = self.docx.read(
            self.repository.read(asset.asset_id, revision), asset.asset_id, revision
        )
        text = document.dfm_text
        start = min(request.text_offset, len(text))
        end = min(start + request.text_limit, len(text))
        return {
            "success": True,
            "asset": native_asset_summary(asset, docx_enabled=True),
            "inspected_revision": revision,
            "dfm": {
                "text_excerpt": text[start:end],
                "text_length": len(text),
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "excerpt_char_range": [start, end],
                "next_text_offset": end if end < len(text) else None,
                "representation_complete": start == 0 and end == len(text),
            },
            "blocks": document.blocks[request.offset : request.offset + request.limit],
            "block_count": len(document.blocks),
            "next_offset": request.offset + request.limit
            if request.offset + request.limit < len(document.blocks)
            else None,
            "locator_scope": "immutable_revision; block IDs may change in later revisions",
            "review_required": [
                "semantic_accuracy",
                "rendered_layout",
                "fields_and_revisions",
            ],
        }

    def _update(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None and request.expected_revision is not None
        assert request.docx_edit is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "docx" or self.docx is None:
            raise ValueError("This format has no configured native DOCX bridge")
        if asset.archived or asset.revision != request.expected_revision:
            raise ValueError("Archived or stale native asset; inspect before editing")
        data = self.repository.read(asset.asset_id, request.expected_revision)
        updated, checks, warnings = self.docx.edit(
            data, asset.asset_id, request.expected_revision, request.docx_edit
        )
        committed = self.repository.commit(
            asset.asset_id, request.expected_revision, updated, checks
        )
        return {
            "success": True,
            "asset": native_asset_summary(committed, docx_enabled=True),
            "operation_result": checks.model_dump(),
            "warnings": warnings,
            "source_written": False,
        }
