"""Revision-bound string-table reads and one-CAS native byte mutations."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.domain.native_delimited import (
    DELIMITED_REVIEW,
    NativeDelimitedDialect,
    attach_delimited_evidence,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeDocumentRequest,
        NativeEditResult,
        NativeFileAsset,
    )
    from src.domain.native_delimited import NativeDelimitedAdapter


def dialect_for(
    format_name: str, explicit: NativeDelimitedDialect | None
) -> NativeDelimitedDialect:
    return explicit or NativeDelimitedDialect(
        delimiter="\t" if format_name == "tsv" else ","
    )


def _record_text(record: dict[str, Any]) -> str:
    text = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if len(text.encode()) > 128 * 1024 * 1024:
        raise ValueError("Delimited representation exceeds the complete read budget")
    return text


def _page(record: dict[str, Any], request: NativeDocumentRequest) -> dict[str, Any]:
    text = _record_text(record)
    start = min(request.text_offset, len(text))
    end = min(start + request.text_limit, len(text))
    result: dict[str, Any] = {
        "success": True,
        "asset_id": request.asset_id,
        "inspected_revision": request.revision,
        "representation": record["schema_version"],
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "text_length": len(text),
        "serialization": "canonical-json; UTF-8 SHA-256; Unicode character offsets",
        "source_written": False,
        "review_required": DELIMITED_REVIEW,
    }
    while True:
        result.update(
            text_excerpt=text[start:end],
            excerpt_char_range=[start, end],
            next_text_offset=end if end < len(text) else None,
            representation_complete=start == 0 and end == len(text),
        )
        if len(json.dumps(result, ensure_ascii=False, indent=2)) <= 10_000:
            return result
        end = start + (end - start) // 2


class NativeDelimitedOperations:
    def __init__(
        self,
        repository: NativeAssetRepository,
        adapter: NativeDelimitedAdapter,
        summarize: Callable[[NativeFileAsset], dict[str, Any]],
    ):
        self.repository = repository
        self.adapter = adapter
        self.summarize = summarize

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if request.op == "create_delimited":
            assert request.delimited_create is not None
            creation = request.delimited_create
            data, report = self.adapter.create(creation)
            kind = creation.name.rsplit(".", 1)[-1].lower()
            asset = self.repository.create(
                creation.name,
                data,
                kind,
                "text/tab-separated-values" if kind == "tsv" else "text/csv",
                result=report,
            )
            return self._result(asset, report)
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        if asset.format not in {"csv", "tsv"}:
            raise ValueError("This format has no native delimited adapter")
        dialect = dialect_for(asset.format, request.delimited_dialect)
        if request.op in {"read_delimited", "read_delimited_cell"}:
            assert request.revision is not None
            data = self.repository.read(asset.asset_id, request.revision)
            if request.op == "read_delimited_cell":
                assert (
                    request.delimited_row is not None
                    and request.delimited_column is not None
                )
                record = self.adapter.read_cell(
                    data, dialect, request.delimited_row, request.delimited_column
                )
                attach_delimited_evidence(record, asset.asset_id, request.revision)
            else:
                record = self.adapter.inspect(data, dialect)
                history = next(
                    h for h in reversed(asset.history) if h.sha256 == request.revision
                )
                record.update(
                    asset_id=asset.asset_id,
                    revision=request.revision,
                    operation_result=history.result.model_dump()
                    if history.result
                    else None,
                )
            return _page(record, request)
        assert (
            request.expected_revision is not None
            and request.delimited_update is not None
        )
        if asset.archived or asset.revision != request.expected_revision:
            raise ValueError("Archived or stale native asset; inspect before editing")
        update = request.delimited_update
        if update.operation == "set_cells" and any(
            edit.reference.asset_id != asset.asset_id for edit in update.cells
        ):
            raise ValueError(
                "Delimited cell references must belong to the target asset"
            )
        data = self.repository.read(asset.asset_id, request.expected_revision)
        changed, report = self.adapter.update(data, dialect, update)
        # A complete result must be readable before exposing the new revision.
        _record_text(
            {
                **self.adapter.inspect(changed, dialect),
                "operation_result": report.model_dump(),
            }
        )
        committed = self.repository.commit(
            asset.asset_id, request.expected_revision, changed, report
        )
        return self._result(committed, report, new_revision_created=changed != data)

    def _result(
        self,
        asset: NativeFileAsset,
        report: NativeEditResult,
        *,
        new_revision_created: bool = True,
    ) -> dict[str, Any]:
        return {
            "success": True,
            "asset": self.summarize(asset),
            "source_written": False,
            "new_revision_created": new_revision_created,
            "operation_result": report.model_dump()
            if not new_revision_created
            else {
                "changed_parts": report.changed_parts,
                "checks": report.checks,
                "repairs": report.repairs,
                "review_required": report.review_required,
                "full_result_in": "read_delimited.operation_result",
            },
            "review_request": {
                "op": "read_delimited",
                "asset_id": asset.asset_id,
                "revision": asset.revision,
                "delimited_dialect": report.changes[0]["dialect"],
            },
        }
