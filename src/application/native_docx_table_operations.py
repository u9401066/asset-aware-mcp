"""Reference-checked Word table grid reads and managed structural mutations."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import native_asset_summary
from src.application.native_operation_results import revision_result_dict

RECEIPT_POLICY = "Latest history entry for these file bytes; a file hash can recur with a different receipt. Verify complete text_sha256 across pages."


def record_text(record: dict[str, Any]) -> str:
    text = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(text.encode()) > 16 * 1024 * 1024:
        raise ValueError("DOCX table and operation receipt exceed the 16 MiB limit")
    return text


if TYPE_CHECKING:
    from src.domain.native_asset_models import (
        NativeAssetRepository,
        NativeDocxBlockReference,
    )
    from src.domain.native_assets import NativeDocumentRequest
    from src.domain.native_docx import NativeDocxAdapter
    from src.domain.native_docx_structure import NativeDocxStructureAdapter


class NativeDocxTableOperations:
    def __init__(
        self,
        repository: NativeAssetRepository,
        docx: NativeDocxAdapter,
        structure: NativeDocxStructureAdapter,
    ):
        self.repository, self.docx, self.structure = repository, docx, structure

    def _chain(
        self,
        data: bytes,
        asset_id: str,
        revision: str,
        reference: NativeDocxBlockReference,
    ) -> list[dict[str, Any]]:
        records = self.docx.decompose(data, asset_id, revision).blocks
        lookup = {record["block_id"]: record for record in records}
        record = lookup.get(reference.locator.block_id)
        if record is None or record["evidence"] != reference.model_dump():
            raise ValueError(
                "DOCX table reference differs from the requested asset/revision"
            )
        chain: list[dict[str, Any]] = []
        seen = set()
        while record:
            if record["block_id"] in seen or len(chain) >= 32:
                raise ValueError("DOCX table ancestry is cyclic or too deep")
            seen.add(record["block_id"])
            metadata = record["representation"].get("metadata", {})
            if metadata.get("source_element") != "w:tbl":
                raise ValueError("DOCX table reference is not a complete table")
            chain.append(metadata)
            parent_id = metadata.get("parent_table_id")
            if parent_id is None:
                break
            record = lookup.get(parent_id)
            if record is None:
                raise ValueError("DOCX parent table is missing")
        return list(reversed(chain))

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "docx":
            raise ValueError("This format has no native Word table grid")
        updating = request.op == "update_docx_table_grid"
        revision = request.expected_revision if updating else request.revision
        assert revision is not None
        if updating and (asset.archived or asset.revision != revision):
            raise ValueError("Archived or stale native DOCX; inspect before editing")
        reference = (
            request.docx_table_grid.reference
            if request.docx_table_grid
            else request.docx_table_reference
        )
        assert reference is not None
        data = self.repository.read(asset.asset_id, revision)
        chain = self._chain(data, asset.asset_id, revision, reference)
        if not updating:
            history = next(
                item for item in reversed(asset.history) if item.sha256 == revision
            )
            record = {
                **self.structure.read_table(data, chain),
                "evidence": reference.model_dump(),
                "operation_result": revision_result_dict(
                    self.repository, asset, history
                ),
                "operation_receipt_policy": RECEIPT_POLICY,
            }
            text = record_text(record)
            start = min(request.text_offset, len(text))
            end = min(start + request.text_limit, len(text))
            while len(json.dumps(text[start:end], ensure_ascii=False)) > 8000:
                end = start + (end - start) // 2
            return {
                "success": True,
                "asset_id": asset.asset_id,
                "inspected_revision": revision,
                "table": {
                    "text_excerpt": text[start:end],
                    "text_length": len(text),
                    "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "excerpt_char_range": [start, end],
                    "next_text_offset": end if end < len(text) else None,
                    "representation_complete": start == 0 and end == len(text),
                },
                "review_required": [
                    "semantic_accuracy",
                    "rendered_layout",
                    "page_flow",
                    "inherited_formatting",
                ],
            }
        assert request.docx_table_grid is not None
        updated, checks = self.structure.edit_table(
            data, chain, request.docx_table_grid
        )
        # Re-extract before commit: ensure all canonical records can be produced,
        # and provide the same table's new reference (IDs may shift after edits).
        revision_after = hashlib.sha256(updated).hexdigest()
        records = self.docx.decompose(updated, asset.asset_id, revision_after).blocks
        target_meta = chain[-1]
        matches = [
            r
            for r in records
            if all(
                r["representation"].get("metadata", {}).get(k) == target_meta.get(k)
                for k in (
                    "source_part",
                    "source_story",
                    "table_index",
                    "source_order",
                    "parent_table_id",
                    "parent_cell",
                    "sdt_index",
                )
            )
            and r["representation"].get("metadata", {}).get("source_element") == "w:tbl"
        ]
        if len(matches) != 1:
            raise ValueError("Edited Word table cannot be uniquely located for review")
        new_reference = matches[0]["evidence"]
        changed = updated != data
        record_text(
            {
                **self.structure.read_table(updated, chain),
                "evidence": new_reference,
                "operation_result": checks.model_dump() if changed else None,
                "operation_receipt_policy": RECEIPT_POLICY,
            }
        )
        committed = self.repository.commit(asset.asset_id, revision, updated, checks)
        return {
            "success": True,
            "asset": native_asset_summary(committed, docx_enabled=True),
            "source_written": False,
            "operation_result": {
                "committed": changed,
                "changed_parts": checks.changed_parts,
                "checks": checks.checks,
                "review_required": checks.review_required,
                "full_result_in": "read_docx_table.operation_result"
                if changed
                else None,
                "note": "No-op: no new history entry or stored operation receipt."
                if not changed
                else "Read all review_request pages for the complete stored receipt.",
            },
            "review_request": {
                "op": "read_docx_table",
                "asset_id": asset.asset_id,
                "revision": committed.revision,
                "docx_table_reference": new_reference,
            },
        }
