"""Managed presentation operations with precise native locators and review evidence."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import native_asset_summary
from src.application.native_pptx_picture_operations import NativePptxPictureOperations
from src.domain.native_pptx import PPTX_MEDIA_TYPE, shape_representation_sha256

if TYPE_CHECKING:
    from src.domain.native_assets import NativeAssetRepository, NativeDocumentRequest
    from src.domain.native_pptx import NativePresentationAdapter
    from src.domain.native_rendering import NativePresentationRenderer

REVIEW_REQUIRED = [
    "semantic_accuracy",
    "rendered_layout",
    "text_overflow",
    "inherited_formatting",
]


def attach_pptx_evidence(record: dict[str, Any], asset_id: str, revision: str) -> None:
    record["schema_version"] = "native-pptx-shape-v1"
    record["evidence"] = {
        "schema_version": "native-pptx-shape-ref-v1",
        "asset_id": asset_id,
        "revision": revision,
        "locator": dict(record["locator"]),
        "value_sha256": shape_representation_sha256(record),
        "verification_scope": "immutable_native_representation",
    }


def shape_excerpt(record: dict[str, Any], offset: int, limit: int) -> dict[str, Any]:
    text = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    start = min(offset, len(text))
    end = min(start + limit, len(text))
    while len(json.dumps(text[start:end], ensure_ascii=False)) > 8000:
        end = start + (end - start) // 2
    return {
        "locator": record["locator"],
        "evidence": record["evidence"],
        "text_excerpt": text[start:end],
        "text_length": len(text),
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "excerpt_char_range": [start, end],
        "next_text_offset": end if end < len(text) else None,
        "representation_complete": start == 0 and end == len(text),
        "serialization": "canonical-json; UTF-8 SHA-256",
    }


class NativePptxOperations:
    def __init__(
        self,
        repository: NativeAssetRepository,
        presentations: NativePresentationAdapter,
        renderer: NativePresentationRenderer | None = None,
    ):
        self.repository = repository
        self.presentations = presentations
        self.renderer = renderer
        self.pictures = NativePptxPictureOperations(repository, presentations)

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        return {
            "render_pptx_slide": self._render,
            "read_pptx_layouts": self._read_layouts,
            "add_pptx_slides": self._update,
            "delete_pptx_slides": self._update,
            "reorder_pptx_slides": self._update,
            "create_pptx": self._create,
            "add_pptx_pictures": self.pictures.execute,
            "replace_pptx_pictures": self.pictures.execute,
            "read_pptx_picture": self.pictures.execute,
            "extract_pptx_picture": self.pictures.execute,
            "read_pptx": self._read,
            "read_pptx_shape": self._read_shape,
            "update_pptx": self._update,
            "add_pptx_tables": self._update,
            "update_pptx_table_grid": self._update,
            "add_pptx_shapes": self._update,
            "delete_pptx_shapes": self._update,
        }[request.op](request)

    def _source(self, request: NativeDocumentRequest) -> tuple[bytes, str, str]:
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "pptx":
            raise ValueError("This format has no native PPTX reader")
        revision = request.revision or asset.revision
        return self.repository.read(asset.asset_id, revision), asset.asset_id, revision

    def _render(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.renderer is None:
            raise ValueError("Native presentation renderer is not configured")
        assert request.pptx_slide_key is not None and request.revision is not None
        data, asset_id, revision = self._source(request)
        return {
            **self.renderer.render(data, request.pptx_slide_key, request.render_size),
            "success": True,
            "asset_id": asset_id,
            "inspected_revision": revision,
            "pptx_slide_key": request.pptx_slide_key.model_dump(),
            "source_written": False,
            "review_required": REVIEW_REQUIRED,
        }

    def _create(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.presentation is not None
        data = self.presentations.create(request.presentation)
        asset = self.repository.create(
            request.presentation.name, data, "pptx", PPTX_MEDIA_TYPE
        )
        return {
            "success": True,
            "asset": native_asset_summary(asset, pptx_enabled=True),
            "source_written": False,
            "review_required": REVIEW_REQUIRED,
        }

    def _read(self, request: NativeDocumentRequest) -> dict[str, Any]:
        data, asset_id, revision = self._source(request)
        metadata = self.presentations.inspect(data)
        slides = metadata.pop("slides")
        selected: list[dict[str, Any]] = []
        count = metadata["shape_count"]
        for record in self.presentations.iter_shapes(
            data, offset=request.offset, limit=request.limit
        ):
            attach_pptx_evidence(record, asset_id, revision)
            selected.append(
                {
                    "locator": record["locator"],
                    "kind": record["kind"],
                    "name": record["name"][:120],
                    "group_path": record["group_path"],
                    "evidence": record["evidence"],
                }
            )
        return {
            "success": True,
            "asset_id": asset_id,
            "inspected_revision": revision,
            "metadata": metadata,
            "slides": slides[request.offset : request.offset + request.limit],
            "next_slide_offset": request.offset + request.limit
            if request.offset + request.limit < len(slides)
            else None,
            "shapes": selected,
            "shape_count": count,
            "next_offset": request.offset + request.limit
            if request.offset + request.limit < count
            else None,
            "locator_scope": "immutable_revision; shape IDs may change in later revisions",
            "review_required": REVIEW_REQUIRED,
        }

    def _read_layouts(self, request: NativeDocumentRequest) -> dict[str, Any]:
        data, asset_id, revision = self._source(request)
        layouts = self.presentations.read_layouts(data)
        selected: list[dict[str, Any]] = []
        for layout in layouts[request.offset : request.offset + request.limit]:
            if (
                selected
                and len(json.dumps([*selected, layout], ensure_ascii=False)) > 6000
            ):
                break
            selected.append(layout)
        end = min(request.offset + len(selected), len(layouts))
        return {
            "success": True,
            "asset_id": asset_id,
            "inspected_revision": revision,
            "layouts": selected,
            "layout_count": len(layouts),
            "next_offset": end if end < len(layouts) else None,
            "review_required": REVIEW_REQUIRED,
        }

    def _read_shape(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.pptx_locator is not None
        data, asset_id, revision = self._source(request)
        record = self.presentations.read_shape(data, request.pptx_locator)
        attach_pptx_evidence(record, asset_id, revision)
        return {
            "success": True,
            "asset_id": asset_id,
            "inspected_revision": revision,
            "shape": shape_excerpt(record, request.text_offset, request.text_limit),
            "review_required": REVIEW_REQUIRED,
        }

    def _update(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None and request.expected_revision is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "pptx":
            raise ValueError("This format has no native PPTX editor")
        if asset.archived or asset.revision != request.expected_revision:
            raise ValueError("Archived or stale native asset; inspect before editing")
        references = list(request.pptx_shape_refs)
        if request.pptx_table_grid is not None:
            references.append(request.pptx_table_grid.reference)
        for reference in references:
            if (
                reference.asset_id != asset.asset_id
                or reference.revision != request.expected_revision
            ):
                raise ValueError(
                    "Presentation edit reference has a different asset or revision"
                )
        data = self.repository.read(asset.asset_id, request.expected_revision)
        if request.op == "add_pptx_slides":
            assert request.pptx_slide_insert is not None
            updated, checks = self.presentations.add_slides(
                data, request.pptx_slide_insert
            )
        elif request.op == "delete_pptx_slides":
            updated, checks = self.presentations.delete_slides(
                data, request.pptx_slide_keys
            )
        elif request.op == "reorder_pptx_slides":
            updated, checks = self.presentations.reorder_slides(
                data, request.pptx_slide_order
            )
        elif request.op == "update_pptx_table_grid":
            assert request.pptx_table_grid is not None
            updated, checks = self.presentations.edit_table_grid(
                data, request.pptx_table_grid
            )
        elif request.op == "add_pptx_tables":
            updated, checks = self.presentations.add_tables(data, request.pptx_tables)
        elif request.op == "add_pptx_shapes":
            updated, checks = self.presentations.add_shapes(data, request.pptx_shapes)
        elif request.op == "delete_pptx_shapes":
            updated, checks = self.presentations.delete_shapes(
                data, request.pptx_shape_refs
            )
        else:
            updated, checks = self.presentations.edit(data, request.pptx_edits)
        committed = self.repository.commit(
            asset.asset_id, request.expected_revision, updated, checks
        )
        return {
            "success": True,
            "asset": native_asset_summary(committed, pptx_enabled=True),
            "operation_result": checks.model_dump(),
            "source_written": False,
            "review_request": {
                "op": "read_pptx",
                "asset_id": asset.asset_id,
                "revision": committed.revision,
            },
        }
