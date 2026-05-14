"""DocxIR JSON serialization helpers for :mod:`docx_service`."""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.domain.docx_entities import DfmBlock, DocxIR

if TYPE_CHECKING:
    from src.domain.repositories import DocumentRepository

logger = logging.getLogger(__name__)


class DocxIrSerializationMixin:
    """Persist and restore the DOCX intermediate representation."""

    if TYPE_CHECKING:
        repository: DocumentRepository

    def _save_ir(self, ir: DocxIR, path: Path) -> None:
        """Serialize IR to JSON file."""
        data = {
            "doc_id": ir.doc_id,
            "source_path": ir.source_path,
            "source_filename": ir.source_filename,
            "checksum": ir.checksum,
            "style_info": ir.style_info.to_dict(),
            "blocks": [self._block_to_dict(b) for b in ir.blocks],
            "assets": ir.assets,
            "preserved_parts": ir.preserved_parts,
            "relationships": ir.relationships,
            "created_at": ir.created_at.isoformat(),
            "updated_at": ir.updated_at.isoformat(),
            "_id_counters": ir._id_counters,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp:
                tmp.write(payload)
                tmp.write("\n")
                tmp_path = Path(tmp.name)
            tmp_path.replace(path)
        finally:
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink()

    def _load_ir(self, doc_id: str) -> DocxIR | None:
        """Load IR from JSON file."""
        doc_dir = self.repository.get_doc_dir(doc_id)
        ir_path = doc_dir / "ir.json"
        if not ir_path.exists():
            return None

        try:
            data = json.loads(ir_path.read_text(encoding="utf-8"))
            return self._dict_to_ir(data)
        except Exception as e:
            logger.error("Failed to load IR: %s", e)
            return None

    @staticmethod
    def _block_to_dict(block: DfmBlock) -> dict[str, Any]:
        """Serialize a DfmBlock to dict."""
        from src.domain.docx_value_objects import ImageAnchorType

        d: dict[str, Any] = {
            "id": block.id,
            "block_type": block.block_type.value,
            "content": block.content,
        }
        if block.style_name:
            d["style_name"] = block.style_name
        if block.runs:
            d["runs"] = [r.to_dict() for r in block.runs]
        if block.level:
            d["level"] = block.level
        if block.list_level:
            d["list_level"] = block.list_level
        if block.num_id is not None:
            d["num_id"] = block.num_id
        if block.table_style:
            d["table_style"] = block.table_style
        if block.col_widths:
            d["col_widths"] = block.col_widths
        if block.merged_cells:
            d["merged_cells"] = [mc.to_dict() for mc in block.merged_cells]
        if block.cell_formats:
            d["cell_formats"] = {k: v.to_dict() for k, v in block.cell_formats.items()}
        if block.is_nested:
            d["is_nested"] = True
        if block.parent_cell:
            d["parent_cell"] = block.parent_cell
        if block.raw_xml_ref:
            d["raw_xml_ref"] = block.raw_xml_ref
        if block.image_path:
            d["image_path"] = block.image_path
        if block.image_width_cm:
            d["image_width_cm"] = block.image_width_cm
        if block.image_height_cm:
            d["image_height_cm"] = block.image_height_cm
        if block.image_anchor != ImageAnchorType.INLINE:
            d["image_anchor"] = block.image_anchor.value
        if block.image_alt:
            d["image_alt"] = block.image_alt
        if block.chart_type:
            d["chart_type"] = block.chart_type
        if block.binary_ref:
            d["binary_ref"] = block.binary_ref
        if block.data_hash:
            d["data_hash"] = block.data_hash
        if block.toc_depth != 3:
            d["toc_depth"] = block.toc_depth
        if block.field_code:
            d["field_code"] = block.field_code
        if block.hdr_ftr_type:
            d["hdr_ftr_type"] = block.hdr_ftr_type
        if block.xml_ref:
            d["xml_ref"] = block.xml_ref
        if block.preview_text:
            d["preview_text"] = block.preview_text
        if block.field_type:
            d["field_type"] = block.field_type
        if block.field_instruction:
            d["field_instruction"] = block.field_instruction
        if block.field_display:
            d["field_display"] = block.field_display
        if block.break_type:
            d["break_type"] = block.break_type.value
        if block.section_page_setup:
            d["section_page_setup"] = block.section_page_setup.to_dict()
        if block.footnote_id is not None:
            d["footnote_id"] = block.footnote_id
        if block.citation_style:
            d["citation_style"] = block.citation_style
        if block.citation_entries:
            d["citation_entries"] = block.citation_entries
        if block.bookmark_name:
            d["bookmark_name"] = block.bookmark_name
        if block.revision_type:
            d["revision_type"] = block.revision_type
        if block.revision_author:
            d["revision_author"] = block.revision_author
        if block.revision_date:
            d["revision_date"] = block.revision_date
        if block.ole_prog_id:
            d["ole_prog_id"] = block.ole_prog_id
        if block.ole_display_name:
            d["ole_display_name"] = block.ole_display_name
        if block.ole_width_cm:
            d["ole_width_cm"] = block.ole_width_cm
        if block.ole_height_cm:
            d["ole_height_cm"] = block.ole_height_cm
        if block.macro_name:
            d["macro_name"] = block.macro_name
        if block.macro_hash:
            d["macro_hash"] = block.macro_hash
        if block.metadata:
            d["metadata"] = block.metadata
        return d

    @staticmethod
    def _dict_to_ir(data: dict[str, Any]) -> DocxIR:
        """Deserialize IR from dict."""
        from datetime import datetime

        from src.domain.docx_entities import (
            CellFormat,
            DfmBlock,
            DocxStyleInfo,
            FormatRun,
            MergedCell,
            PageSetup,
        )
        from src.domain.docx_value_objects import (
            BreakType,
            DfmBlockType,
            ImageAnchorType,
        )

        ir = DocxIR(
            doc_id=data["doc_id"],
            source_path=data.get("source_path", ""),
            source_filename=data.get("source_filename", ""),
            checksum=data.get("checksum", ""),
            style_info=DocxStyleInfo.from_dict(data.get("style_info", {})),
            assets=data.get("assets", {}),
            preserved_parts=data.get("preserved_parts", {}),
            relationships=data.get("relationships", {}),
            _id_counters=data.get("_id_counters", {}),
        )

        if data.get("created_at"):
            ir.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            ir.updated_at = datetime.fromisoformat(data["updated_at"])

        for bd in data.get("blocks", []):
            block = DfmBlock(
                id=bd["id"],
                block_type=DfmBlockType(bd["block_type"]),
                content=bd.get("content", ""),
                style_name=bd.get("style_name"),
                level=bd.get("level", 0),
                list_level=bd.get("list_level", 0),
                num_id=bd.get("num_id"),
                table_style=bd.get("table_style"),
                col_widths=bd.get("col_widths", []),
                is_nested=bd.get("is_nested", False),
                parent_cell=bd.get("parent_cell"),
                raw_xml_ref=bd.get("raw_xml_ref"),
                image_path=bd.get("image_path"),
                image_width_cm=bd.get("image_width_cm"),
                image_height_cm=bd.get("image_height_cm"),
                image_alt=bd.get("image_alt", ""),
                chart_type=bd.get("chart_type"),
                binary_ref=bd.get("binary_ref"),
                data_hash=bd.get("data_hash"),
                toc_depth=bd.get("toc_depth", 3),
                field_code=bd.get("field_code"),
                hdr_ftr_type=bd.get("hdr_ftr_type"),
                xml_ref=bd.get("xml_ref"),
                preview_text=bd.get("preview_text", ""),
                field_type=bd.get("field_type"),
                field_instruction=bd.get("field_instruction"),
                field_display=bd.get("field_display"),
                footnote_id=bd.get("footnote_id"),
                citation_style=bd.get("citation_style"),
                citation_entries=bd.get("citation_entries", []),
                bookmark_name=bd.get("bookmark_name"),
                revision_type=bd.get("revision_type"),
                revision_author=bd.get("revision_author"),
                revision_date=bd.get("revision_date"),
                ole_prog_id=bd.get("ole_prog_id"),
                ole_display_name=bd.get("ole_display_name"),
                ole_width_cm=bd.get("ole_width_cm"),
                ole_height_cm=bd.get("ole_height_cm"),
                macro_name=bd.get("macro_name"),
                macro_hash=bd.get("macro_hash"),
                metadata=bd.get("metadata", {}),
            )

            if bd.get("runs"):
                block.runs = [FormatRun.from_dict(r) for r in bd["runs"]]

            if bd.get("merged_cells"):
                block.merged_cells = [
                    MergedCell.from_dict(mc) for mc in bd["merged_cells"]
                ]

            if bd.get("cell_formats"):
                block.cell_formats = {
                    k: CellFormat.from_dict(v) for k, v in bd["cell_formats"].items()
                }

            if bd.get("image_anchor"):
                block.image_anchor = ImageAnchorType(bd["image_anchor"])

            if bd.get("break_type"):
                block.break_type = BreakType(bd["break_type"])

            if bd.get("section_page_setup"):
                block.section_page_setup = PageSetup.from_dict(bd["section_page_setup"])

            ir.blocks.append(block)

        return ir
