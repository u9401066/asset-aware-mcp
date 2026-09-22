"""Operate on native file assets independently of the PDF ingestion repository."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from src.application.native_delimited_operations import NativeDelimitedOperations
from src.application.native_derivation_service import NativeDerivationService
from src.application.native_document_contract import (
    native_asset_summary,
    native_document_contract,
)
from src.application.native_docx_note_operations import NativeDocxNoteOperations
from src.application.native_docx_operations import NativeDocxOperations
from src.application.native_docx_story_operations import NativeDocxStoryOperations
from src.application.native_docx_story_structure_operations import (
    NativeDocxStoryStructureOperations,
)
from src.application.native_evidence_service import (
    NativeEvidenceService,
    attach_native_evidence,
)
from src.application.native_image_operations import NativeImageOperations
from src.application.native_ods_operations import NativeODSOperations
from src.application.native_pdf_annotation_operations import (
    NativePdfAnnotationOperations,
)
from src.application.native_pdf_operations import NativePdfOperations
from src.application.native_pdf_region_service import NativePdfRegionService
from src.application.native_pptx_operations import NativePptxOperations
from src.application.native_rendition_operations import NativeRenditionOperations
from src.application.native_schema import read_schema
from src.application.native_selection_service import NativeSelectionService
from src.application.native_table_operations import NativeTableOperations
from src.application.native_wiki_service import NativeWikiService
from src.application.native_workbook_operations import NativeWorkbookOperations
from src.domain.native_image import IMAGE_EXTENSIONS

if TYPE_CHECKING:
    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeDocumentRequest,
        NativeFileAsset,
        NativeSpreadsheetAdapter,
    )
    from src.domain.native_delimited import NativeDelimitedAdapter
    from src.domain.native_derivation import NativeDerivationRepository
    from src.domain.native_docx import NativeDocxAdapter
    from src.domain.native_docx_notes import NativeDocxNoteAdapter
    from src.domain.native_docx_stories import NativeDocxStoryAdapter
    from src.domain.native_docx_structure import NativeDocxStructureAdapter
    from src.domain.native_grid import NativeGridAdapter
    from src.domain.native_image import NativeImageAdapter
    from src.domain.native_image_archive import NativeImageArchive
    from src.domain.native_ods import NativeODSAdapter
    from src.domain.native_pdf import NativePdfAdapter
    from src.domain.native_pptx import NativePresentationAdapter
    from src.domain.native_rendering import (
        NativePresentationRenderer,
        NativeWordRenderer,
    )
    from src.domain.native_rendition import NativeWorkbookRenderer
    from src.domain.native_table_create import NativeTableCreateAdapter
    from src.domain.native_table_edit import NativeTableEditAdapter
    from src.domain.native_table_workspace import (
        NativeTableRangeReader,
        NativeTableWorkspaces,
    )
    from src.domain.native_wiki import NativeWikiPublisher
    from src.domain.native_workbook import NativeWorkbookStructureAdapter


class NativeDocumentService:
    def __init__(
        self,
        repository: NativeAssetRepository,
        spreadsheets: NativeSpreadsheetAdapter,
        wiki_publisher: NativeWikiPublisher | None = None,
        docx: NativeDocxAdapter | None = None,
        presentations: NativePresentationAdapter | None = None,
        pdfs: NativePdfAdapter | None = None,
        derivations: NativeDerivationRepository | None = None,
        pptx_renderer: NativePresentationRenderer | None = None,
        docx_structure: NativeDocxStructureAdapter | None = None,
        docx_renderer: NativeWordRenderer | None = None,
        workbook_structure: NativeWorkbookStructureAdapter | None = None,
        workbook_ranges: NativeTableRangeReader | None = None,
        table_workspaces: NativeTableWorkspaces | None = None,
        workbook_grid: NativeGridAdapter | None = None,
        workbook_tables: NativeTableEditAdapter | None = None,
        workbook_table_creation: NativeTableCreateAdapter | None = None,
        workbook_renderer: NativeWorkbookRenderer | None = None,
        delimited: NativeDelimitedAdapter | None = None,
        docx_stories: NativeDocxStoryAdapter | None = None,
        docx_notes: NativeDocxNoteAdapter | None = None,
        images: NativeImageAdapter | None = None,
        image_archive: NativeImageArchive | None = None,
        ods: NativeODSAdapter | None = None,
        ods_renderer: NativeWorkbookRenderer | None = None,
    ):
        self.ods = ods
        self.ods_operations = (
            NativeODSOperations(repository, ods, self._summary) if ods else None
        )
        self.repository = repository
        self.spreadsheets = spreadsheets
        self.images = images
        self.image_archive = image_archive
        self.image_operations = (
            NativeImageOperations(repository, images, image_archive) if images else None
        )
        if (workbook_renderer is not None or ods_renderer is not None) and pdfs is None:
            raise ValueError("Workbook rendering requires native PDF read-back support")
        self.rendition_operations = NativeRenditionOperations(
            repository, workbook_renderer, ods_renderer
        )
        if workbook_grid is not None and workbook_structure is None:
            raise ValueError("Native grid editing requires workbook read-back support")
        self.workbook_grid = workbook_grid
        if workbook_tables is not None and workbook_structure is None:
            raise ValueError("Native Table editing requires workbook read-back support")
        self.workbook_tables = workbook_tables
        if workbook_table_creation is not None and workbook_structure is None:
            raise ValueError(
                "Native Table creation requires workbook read-back support"
            )
        self.workbook_table_creation = workbook_table_creation
        self.workbook_operations = (
            NativeWorkbookOperations(
                repository,
                workbook_structure,
                workbook_grid,
                tables=workbook_tables,
                table_creation=workbook_table_creation,
                summarize=self._summary,
            )
            if workbook_structure
            else None
        )
        self.table_operations = (
            NativeTableOperations(
                repository,
                spreadsheets,
                workbook_ranges,
                table_workspaces,
                summarize=self._summary,
                grid=workbook_grid,
            )
            if workbook_ranges and table_workspaces
            else None
        )
        if docx_stories is not None and docx is None:
            raise ValueError("Native Word stories require the DOCX read-back bridge")
        self.docx = docx
        self.docx_stories = docx_stories
        if docx_notes is not None and docx is None:
            raise ValueError("Native Word notes require the DOCX read-back bridge")
        self.docx_notes = docx_notes
        self.docx_structure = docx_structure
        self.docx_renderer = docx_renderer
        self.presentations = presentations
        self.pptx_renderer = pptx_renderer
        self.pdfs = pdfs
        self.delimited = delimited
        self.delimited_operations = (
            NativeDelimitedOperations(repository, delimited, self._summary)
            if delimited
            else None
        )
        self.pdf_operations = NativePdfOperations(repository, pdfs) if pdfs else None
        self.pptx_operations = (
            NativePptxOperations(repository, presentations, pptx_renderer)
            if presentations
            else None
        )
        self.evidence = NativeEvidenceService(
            repository,
            spreadsheets,
            docx,
            presentations,
            pdfs,
            delimited,
            docx_stories,
            docx_notes,
            images=images,
            image_archive=image_archive,
            ods=ods,
        )
        self.derivations = (
            NativeDerivationService(derivations, self.evidence) if derivations else None
        )
        self.docx_operations = (
            NativeDocxOperations(repository, docx, docx_structure, docx_renderer)
            if docx
            else None
        )
        self.wiki = (
            NativeWikiService(
                repository,
                spreadsheets,
                wiki_publisher,
                docx,
                presentations,
                pdfs,
                self.derivations,
                delimited,
                docx_stories,
                docx_notes,
                images=images,
                image_archive=image_archive,
                ods=ods,
            )
            if wiki_publisher is not None
            else None
        )

    def _summary(self, asset: NativeFileAsset) -> dict[str, Any]:
        return native_asset_summary(
            asset,
            docx_enabled=self.docx is not None,
            pptx_enabled=self.presentations is not None,
            pdf_enabled=self.pdfs is not None,
            delimited_enabled=self.delimited is not None,
            workbook_structure_enabled=self.workbook_operations is not None,
            workbook_grid_enabled=self.workbook_grid is not None,
            workbook_table_edit_enabled=self.workbook_tables is not None,
            workbook_table_creation_enabled=self.workbook_table_creation is not None,
            table_workspaces_enabled=self.table_operations is not None,
            images_enabled=self.images is not None,
            ods_enabled=self.ods is not None,
        )

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        handlers = {
            "contract": self._contract,
            "contract_details": self._contract,
            "schema": read_schema,
            "list": self._list,
            "register": self._register,
            "create": self._create,
            "history": self._history,
            "read_cell": self._read_cell,
            "project_workbook_table": self._table_operation,
            "read_table_workspace": self._table_operation,
            "apply_table_workspace": self._table_operation,
            "create_workbook_from_table": self._table_operation,
            "read_workbook": self._workbook_operation,
            "create_workbook_rendition": self.rendition_operations.execute,
            "read_rendition": self.rendition_operations.execute,
            "update_worksheet_grid": self._workbook_operation,
            "read_worksheet_layout": self._workbook_operation,
            "update_worksheet_layout": self._workbook_operation,
            "update_workbook_table": self._workbook_operation,
            "add_workbook_table": self._workbook_operation,
            "add_worksheets": self._workbook_operation,
            "rename_worksheet": self._workbook_operation,
            "reorder_worksheets": self._workbook_operation,
            "delete_worksheets": self._workbook_operation,
            "create_ods": self._ods_operation,
            "read_ods": self._ods_operation,
            "read_ods_cell": self._ods_operation,
            "update_ods": self._ods_operation,
            "read_ods_dependencies": self._ods_operation,
            "rename_ods_table": self._ods_operation,
            "create_delimited": self._delimited_operation,
            "read_delimited": self._delimited_operation,
            "read_delimited_cell": self._delimited_operation,
            "update_delimited": self._delimited_operation,
            "create_pdf": self._pdf_operation,
            "create_image": self._image_operation,
            "extract_image": self._image_operation,
            "compose_images": self._image_operation,
            "read_image": self._image_operation,
            "read_image_frame": self._image_operation,
            "render_image_frame": self._image_operation,
            "read_image_region": self._image_operation,
            "update_image": self._image_operation,
            "read_pdf": self._pdf_operation,
            "read_pdf_page": self._pdf_operation,
            "read_pdf_region": NativePdfRegionService(self.evidence).read,
            "read_pdf_annotations": self._pdf_annotation_operation,
            "read_pdf_annotation": self._pdf_annotation_operation,
            "update_pdf_annotations": self._pdf_annotation_operation,
            "render_pdf_page": self._pdf_operation,
            "add_pdf_pages": self._pdf_operation,
            "update_pdf": self._pdf_operation,
            "delete_pdf_pages": self._pdf_operation,
            "reorder_pdf_pages": self._pdf_operation,
            "read_pptx_layouts": self._pptx_operation,
            "render_pptx_slide": self._pptx_operation,
            "add_pptx_slides": self._pptx_operation,
            "delete_pptx_slides": self._pptx_operation,
            "reorder_pptx_slides": self._pptx_operation,
            "create_pptx": self._pptx_operation,
            "add_pptx_pictures": self._pptx_operation,
            "replace_pptx_pictures": self._pptx_operation,
            "read_pptx_picture": self._pptx_operation,
            "extract_pptx_picture": self._pptx_operation,
            "read_pptx": self._pptx_operation,
            "read_pptx_shape": self._pptx_operation,
            "update_pptx": self._pptx_operation,
            "add_pptx_tables": self._pptx_operation,
            "update_pptx_table_grid": self._pptx_operation,
            "add_pptx_shapes": self._pptx_operation,
            "delete_pptx_shapes": self._pptx_operation,
            "read_docx_notes": self._note_operation,
            "read_docx_note": self._note_operation,
            "update_docx_note": self._note_operation,
            "update_docx_notes": self._note_operation,
            "read_docx_stories": self._story_operation,
            "read_docx_story": self._story_operation,
            "update_docx_story": self._story_operation,
            "read_docx_story_structure": self._story_structure_operation,
            "update_docx_story_structure": self._story_structure_operation,
            "read_docx": self._docx_operation,
            "render_docx_page": self._docx_operation,
            "create_docx": self._docx_operation,
            "add_docx_blocks": self._docx_operation,
            "delete_docx_blocks": self._docx_operation,
            "read_docx_block": self._docx_operation,
            "read_docx_table": self._docx_operation,
            "update_docx_table_grid": self._docx_operation,
            "update_docx": self._docx_operation,
            "verify": self._verify,
            "read_selection": NativeSelectionService(self.evidence).read,
            "record_derivation": self._derivation_operation,
            "read_derivations": self._derivation_operation,
            "retract_derivation": self._derivation_operation,
            "verify_derivation": self._derivation_operation,
            "export_wiki": self._export_wiki,
            "inspect": self._inspect,
            "refresh": self._refresh,
            "archive": self._archive,
            "publish": self._publish,
            "writeback": self._writeback,
            "update": self._update,
        }
        return handlers[request.op](request)

    def _export_wiki(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.wiki is None:
            raise ValueError("Native wiki publisher is not configured")
        return self.wiki.export(request)

    def _derivation_operation(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.derivations is None:
            raise ValueError("Native derivation repository is not configured")
        return self.derivations.execute(request)

    def _delimited_operation(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.delimited_operations is None:
            raise ValueError("Native delimited adapter is not configured")
        return self.delimited_operations.execute(request)

    def _pdf_operation(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.pdf_operations is None:
            raise ValueError("Native PDF adapter is not configured")
        return self.pdf_operations.execute(request)

    def _image_operation(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.image_operations is None:
            raise ValueError("Native image adapter is not configured")
        return self.image_operations.execute(request)

    def _pdf_annotation_operation(
        self, request: NativeDocumentRequest
    ) -> dict[str, Any]:
        if self.pdfs is None:
            raise ValueError("Native PDF adapter is not configured")
        return NativePdfAnnotationOperations(self.repository, self.pdfs).execute(
            request
        )

    def _ods_operation(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.ods_operations is None:
            raise ValueError("Native ODS adapter is not configured")
        return self.ods_operations.execute(request)

    def _verify(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.reference is not None
        return self.evidence.verify(request.reference)

    def _contract(self, request: NativeDocumentRequest) -> dict[str, Any]:
        return native_document_contract(
            request,
            docx_stories_enabled=self.docx_stories is not None,
            docx_notes_enabled=self.docx_notes is not None,
            images_enabled=self.images is not None,
            ods_enabled=self.ods is not None,
            image_evidence_retention_enabled=self.images is not None
            and self.image_archive is not None,
            workbook_rendering_configured=self.rendition_operations.renderer
            is not None,
            ods_rendering_configured=self.rendition_operations.ods_renderer is not None,
            docx_enabled=self.docx is not None,
            pptx_enabled=self.presentations is not None,
            pdf_enabled=self.pdfs is not None,
            delimited_enabled=self.delimited is not None,
            workbook_structure_enabled=self.workbook_operations is not None,
            workbook_grid_enabled=self.workbook_grid is not None,
            workbook_table_edit_enabled=self.workbook_tables is not None,
            workbook_table_creation_enabled=self.workbook_table_creation is not None,
            table_workspaces_enabled=self.table_operations is not None,
            derivations_enabled=self.derivations is not None,
            docx_structure_enabled=self.docx is not None
            and self.docx_structure is not None,
            docx_rendering_configured=self.docx is not None
            and self.docx_renderer is not None,
            pptx_rendering_configured=self.pptx_renderer is not None
            and self.presentations is not None,
        )

    def _list(self, request: NativeDocumentRequest) -> dict[str, Any]:
        return {
            "success": True,
            "assets": [
                self._summary(asset)
                for asset in self.repository.list_assets(request.offset, request.limit)
            ],
        }

    def _register(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.source_path is not None
        asset = self.repository.register(request.source_path)
        return {"success": True, "asset": self._summary(asset)}

    def _create(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.workbook is not None
        data = self.spreadsheets.create(request.workbook)
        asset = self.repository.create(
            request.workbook.name,
            data,
            "xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        return {"success": True, "asset": self._summary(asset)}

    def _history(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        return {
            "success": True,
            "asset": self._summary(asset),
            "history": [
                revision.model_dump(exclude={"result"})
                for revision in asset.history[
                    request.offset : request.offset + request.limit
                ]
            ],
            "next_offset": request.offset + request.limit
            if request.offset + request.limit < len(asset.history)
            else None,
        }

    def _read_cell(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset_id = request.asset_id
        asset = self.repository.load(asset_id)
        if asset.format not in {"xlsx", "xlsm"}:
            raise ValueError("This format has no native cell reader")
        assert request.sheet is not None and request.cell is not None
        revision = request.revision or asset.revision
        cell = self.spreadsheets.read_cell(
            self.repository.read(asset_id, revision), request.sheet, request.cell
        )
        attach_native_evidence(cell, asset_id, revision)
        if isinstance(cell.get("value"), str):
            value = cell.pop("value")
            start = min(request.text_offset, len(value))
            end = min(start + request.text_limit, len(value))
            cell.update(
                value_excerpt=value[start:end],
                value_length=len(value),
                value_text_sha256=hashlib.sha256(value.encode("utf-8")).hexdigest(),
                excerpt_char_range=[start, end],
                next_text_offset=end if end < len(value) else None,
                representation_complete=start == 0 and end == len(value),
            )
        return {
            "success": True,
            "asset_id": asset_id,
            "inspected_revision": revision,
            "cell": cell,
        }

    def _inspect(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset_id = request.asset_id
        asset = self.repository.load(asset_id)
        revision = request.revision or asset.revision
        data = self.repository.read(asset_id, revision)
        result: dict[str, Any] = {
            "success": True,
            "asset": self._summary(asset),
            "inspected_revision": revision,
        }
        if asset.format in {"xlsx", "xlsm"}:
            result["content"] = self.spreadsheets.inspect(
                data,
                sheet=request.sheet,
                offset=request.offset,
                limit=request.limit,
            )
            for cell in result["content"]["cells"]:
                attach_native_evidence(cell, asset_id, revision)
        elif asset.format == "ods" and self.ods is not None:
            result["content"] = {
                "representation": "ods_package",
                "size_bytes": len(data),
                "read_operation": "read_ods",
            }
        elif asset.format in {"csv", "tsv"} and self.delimited is not None:
            result["content"] = {
                "representation": "delimited_table",
                "size_bytes": len(data),
                "read_operation": "read_delimited",
            }
        elif asset.format == "pptx" and self.presentations is not None:
            result["content"] = {
                "representation": "pptx_package",
                "size_bytes": len(data),
                "read_operation": "read_pptx",
            }
        elif asset.format == "docx" and self.docx is not None:
            result["content"] = {
                "representation": "docx_package",
                "size_bytes": len(data),
                "native_editor": "dfm_bridge",
                "read_operation": "read_docx",
            }
        elif asset.format in IMAGE_EXTENSIONS and self.images is not None:
            result["content"] = {
                "representation": "native_raster_frames",
                "size_bytes": len(data),
                "read_operation": "read_image",
                "format_detection": "Read the pinned catalog; decoding identifies actual bytes, not the filename.",
            }
        else:
            result["content"] = {
                "representation": "opaque_binary",
                "size_bytes": len(data),
                "native_editor": "unavailable",
            }
        return result

    def _refresh(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset_id = request.asset_id
        assert request.expected_revision is not None
        assert request.expected_source_sha256 is not None
        return {
            "success": True,
            "asset": self._summary(
                self.repository.refresh(
                    asset_id,
                    request.expected_revision,
                    request.expected_source_sha256,
                )
            ),
            "source_written": False,
        }

    def _archive(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset_id = request.asset_id
        assert request.expected_revision is not None
        return {
            "success": True,
            "asset": self._summary(
                self.repository.archive(asset_id, request.expected_revision)
            ),
            "source_deleted": False,
        }

    def _publish(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset_id = request.asset_id
        assert request.expected_revision is not None
        assert request.output_path is not None
        return self.repository.publish(
            asset_id, request.expected_revision, request.output_path
        )

    def _writeback(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset_id = request.asset_id
        assert request.expected_revision is not None
        assert request.expected_source_sha256 is not None
        return self.repository.writeback(
            asset_id, request.expected_revision, request.expected_source_sha256
        )

    def _update(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset_id = request.asset_id
        asset = self.repository.load(asset_id)
        assert request.expected_revision is not None
        if asset.format not in {"xlsx", "xlsm"}:
            raise ValueError("This format has no native editing adapter yet")
        if asset.archived or asset.revision != request.expected_revision:
            raise ValueError("Archived or stale native asset; inspect before editing")
        data = self.repository.read(asset_id, request.expected_revision)
        updated, checks = self.spreadsheets.edit(data, request.edits)
        committed = self.repository.commit(
            asset_id, request.expected_revision, updated, checks
        )
        return {
            "success": True,
            "asset": self._summary(committed),
            "operation_result": checks.model_dump(),
            "source_written": False,
        }

    def _note_operation(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.docx_notes is None:
            raise ValueError("Native Word notes are not configured")
        return NativeDocxNoteOperations(self.repository, self.docx_notes).execute(
            request
        )

    def _story_operation(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.docx_stories is None:
            raise ValueError("Native DOCX story adapter is not configured")
        return NativeDocxStoryOperations(self.repository, self.docx_stories).execute(
            request
        )

    def _story_structure_operation(
        self, request: NativeDocumentRequest
    ) -> dict[str, Any]:
        if self.docx_stories is None:
            raise ValueError("Native Word stories are not configured")
        return NativeDocxStoryStructureOperations(
            self.repository, self.docx_stories
        ).execute(request)

    def _docx_operation(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.docx_operations is None:
            raise ValueError("The native DOCX bridge is not configured")
        result = self.docx_operations.execute(request)
        if request.op == "read_docx" and self.docx_notes is not None:
            result["notes_request"] = {
                "op": "read_docx_notes",
                "asset_id": request.asset_id,
                "revision": result["inspected_revision"],
            }
        if request.op == "read_docx" and self.docx_stories is not None:
            result["header_footer_request"] = {
                "op": "read_docx_stories",
                "asset_id": request.asset_id,
                "revision": result["inspected_revision"],
            }
        return result

    def _pptx_operation(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.pptx_operations is None:
            raise ValueError("The native PPTX adapter is not configured")
        return self.pptx_operations.execute(request)

    def _workbook_operation(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.workbook_operations is None:
            raise ValueError("Native workbook structure adapter is not configured")
        return self.workbook_operations.execute(request)

    def _table_operation(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if self.table_operations is None:
            raise ValueError("Native table workspace adapters are not configured")
        return self.table_operations.execute(request)
