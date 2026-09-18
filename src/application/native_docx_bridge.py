"""Adapt immutable DOCX bytes to the existing checked DFM save workflow.

This is a blocking adapter, called by native operations in the MCP worker thread.
Its private event loop runs the existing asynchronous DocxService entry points.
"""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any

import yaml

from src.application.docx_service import DocxService
from src.domain.native_docx import MAX_DFM_BYTES, NativeDocxRead

if TYPE_CHECKING:
    from src.domain.native_assets import NativeEditResult
    from src.domain.native_docx import (
        NativeDocxEdit,
        NativeDocxWorkspace,
        NativeDocxWorkspaces,
    )


def _frontmatter(dfm: str) -> tuple[dict[str, Any], str]:
    if not dfm.startswith("---\n") or "\n---\n" not in dfm[4:]:
        raise ValueError("Native DFM requires its complete frontmatter")
    header, body = dfm[4:].split("\n---\n", 1)
    if len(header) > 8192:
        raise ValueError("Native DFM frontmatter exceeds its limit")
    try:
        fields = yaml.safe_load(header)
    except yaml.YAMLError as exc:
        raise ValueError("Invalid native DFM frontmatter") from exc
    if not isinstance(fields, dict):
        raise ValueError("Native DFM frontmatter must be a mapping")
    return fields, body


def _bound_dfm(dfm: str, asset_id: str, revision: str) -> str:
    fields, body = _frontmatter(dfm)
    fields.pop("created", None)
    fields.update(native_asset_id=asset_id, native_revision=revision)
    text = "---\n" + yaml.safe_dump(fields, allow_unicode=True) + "---\n" + body
    if len(text.encode("utf-8")) > MAX_DFM_BYTES:
        raise ValueError("DFM projection exceeds the 4 MiB UTF-8 limit")
    return text


def _check_success(result: dict[str, Any]) -> None:
    if not result.get("success"):
        warnings = "; ".join(str(item) for item in result.get("warnings", []))
        raise ValueError(
            f"DOCX workflow rejected the operation: {result.get('error')}; {warnings}"
        )


def _check_complete_projection(
    service: DocxService, original: str, edited: str
) -> None:
    marker = r"<!--\s*(?:dfm:\w+\s+)?@b:(\S+)"
    if re.findall(marker, original) != re.findall(marker, edited):
        raise ValueError(
            "Native DOCX edits must retain every block marker in its original order"
        )
    baseline = service.parser.parse(original)
    candidate = service.parser.parse(edited)
    if candidate.style_info != baseline.style_info:
        raise ValueError("Native DOCX document-level style edits are not supported")
    if candidate.errors:
        raise ValueError("Native DFM parse errors: " + "; ".join(candidate.errors))


class NativeDocxBridge:
    def __init__(self, workspaces: NativeDocxWorkspaces):
        self.workspaces = workspaces

    @staticmethod
    async def _ingest(workspace: NativeDocxWorkspace) -> tuple[DocxService, str]:
        service = DocxService(workspace.repository)
        result = await service.ingest_docx(workspace.source_path)
        _check_success(result)
        return service, str(result["doc_id"])

    def read(self, data: bytes, asset_id: str, revision: str) -> NativeDocxRead:
        return asyncio.run(self._read(data, asset_id, revision))

    async def _read(self, data: bytes, asset_id: str, revision: str) -> NativeDocxRead:
        with self.workspaces.open(data) as workspace:
            service, doc_id = await self._ingest(workspace)
            dfm = await service.get_dfm(doc_id)
            blocks = await service.list_blocks(doc_id)
            if dfm is None or blocks is None:
                raise ValueError("DOCX workflow did not return its DFM representation")
            return NativeDocxRead(_bound_dfm(dfm, asset_id, revision), blocks)

    def edit(
        self, data: bytes, asset_id: str, revision: str, edit: NativeDocxEdit
    ) -> tuple[bytes, NativeEditResult, list[str]]:
        fields, _ = _frontmatter(edit.dfm_text)
        if (
            fields.get("native_asset_id") != asset_id
            or fields.get("native_revision") != revision
        ):
            raise ValueError(
                "Native DFM asset/revision binding mismatch; read the current revision"
            )
        return asyncio.run(self._edit(data, edit))

    async def _edit(
        self, data: bytes, edit: NativeDocxEdit
    ) -> tuple[bytes, NativeEditResult, list[str]]:
        with self.workspaces.open(data, for_edit=True) as workspace:
            service, doc_id = await self._ingest(workspace)
            original = await service.get_dfm(doc_id)
            if original is None:
                raise ValueError("DOCX workflow did not return its DFM representation")
            _check_complete_projection(service, original, edit.dfm_text)
            result = await service.save_docx(
                doc_id,
                edit.dfm_text,
                force=False,
                track_changes=edit.track_changes,
                revision_author=edit.revision_author,
            )
            _check_success(result)
            updated, checks = workspace.read_result(
                result["output_path"], result["changed_block_ids"], edit.track_changes
            )
            return updated, checks, list(result.get("warnings", []))
