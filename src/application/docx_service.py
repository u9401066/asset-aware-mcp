"""
Application Layer - Docx Service

Use cases for docx ingestion, DFM conversion, and write-back.
Orchestrates DocxAdapter, DfmRenderer, and DfmParser.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.application.dfm_integrity import DfmIntegrityChecker, IntegrityIssue
from src.domain.docx_entities import DfmBlock, DocxIR
from src.infrastructure.dfm_parser import DfmParser
from src.infrastructure.dfm_renderer import DfmRenderer
from src.infrastructure.docx_adapter import DocxAdapter

if TYPE_CHECKING:
    from src.domain.repositories import DocumentRepository

logger = logging.getLogger(__name__)


class DocxService:
    """
    Application service for docx ↔ DFM operations.

    Orchestrates:
    1. ingest_docx: .docx → DocxIR → content.dfm + ir.json + preserved parts
    2. get_dfm: Read the editable DFM content
    3. save_docx: Edited DFM → parse edits → merge with IR → rebuild .docx
    4. list_blocks: Summary of all blocks in the document
    """

    def __init__(self, repository: DocumentRepository):
        self.repository = repository
        self.adapter = DocxAdapter()
        self.renderer = DfmRenderer()
        self.parser = DfmParser()
        self.integrity = DfmIntegrityChecker()

    # ========================================================================
    # Ingest
    # ========================================================================

    async def ingest_docx(self, file_path: str) -> dict[str, Any]:
        """
        Ingest a .docx file into DFM format.

        Creates:
            data/{doc_id}/
            ├── content.dfm          # Editable markdown+YAML
            ├── ir.json              # Serialized IR for round-trip
            ├── original.docx        # Copy of original file
            ├── parts/               # Preserved XML parts
            └── assets/              # Images and binary assets

        Args:
            file_path: Path to the .docx file

        Returns:
            Summary dict with doc_id, block counts, etc.
        """
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {path}"}
        if path.suffix.lower() not in (".docx", ".docm"):
            return {"success": False, "error": f"Not a docx file: {path}"}

        try:
            # Generate doc_id from filename + hash
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            doc_id = f"docx_{path.stem}_{checksum}"

            # Set up output directory
            doc_dir = self.repository.get_doc_dir(doc_id)

            # Copy original file
            original_path = doc_dir / "original.docx"
            shutil.copy2(path, original_path)

            # Parse docx → IR
            ir = self.adapter.parse_to_ir(path, doc_dir)
            ir.doc_id = doc_id

            # Render IR → DFM text
            dfm_text = self.renderer.render(ir)

            # Save DFM (original format, for MCP tools)
            dfm_path = doc_dir / "content.dfm"
            dfm_path.write_text(dfm_text, encoding="utf-8")

            # Render split format: clean MD + format YAML
            md_text, yaml_text = self.renderer.render_split(ir)
            md_path = doc_dir / "content.md"
            md_path.write_text(md_text, encoding="utf-8")
            yaml_path = doc_dir / "format.yaml"
            yaml_path.write_text(yaml_text, encoding="utf-8")

            # Save IR as JSON for round-trip
            self._save_ir(ir, doc_dir / "ir.json")

            # --- Post-ingest integrity check ---
            ingest_report = self.integrity.check_ingest(ir, md_text, yaml_text)
            if not ingest_report.passed:
                # Auto-repair and re-render
                md_text, yaml_text, repair_report = self.integrity.auto_repair_split(
                    md_text, yaml_text, ir
                )
                md_path.write_text(md_text, encoding="utf-8")
                yaml_path.write_text(yaml_text, encoding="utf-8")
                logger.info("Ingest auto-repair: %s", repair_report.to_summary())

            summary = ir.get_summary()
            summary["success"] = True
            summary["dfm_path"] = str(dfm_path)
            summary["md_path"] = str(md_path)
            summary["integrity"] = ingest_report.to_summary()
            return summary

        except Exception as e:
            logger.exception("Failed to ingest docx: %s", file_path)
            return {"success": False, "error": str(e)}

    # ========================================================================
    # Read
    # ========================================================================

    async def get_dfm(self, doc_id: str) -> str | None:
        """
        Get the editable DFM content for a document.

        Returns:
            DFM text string, or None if not found.
        """
        doc_dir = self.repository.get_doc_dir(doc_id)
        dfm_path = doc_dir / "content.dfm"
        if not dfm_path.exists():
            return None
        return dfm_path.read_text(encoding="utf-8")

    async def get_md(self, doc_id: str) -> str | None:
        """
        Get the clean Markdown content for human editing.

        Returns:
            MD text, or None if not found.
        """
        doc_dir = self.repository.get_doc_dir(doc_id)
        md_path = doc_dir / "content.md"
        if not md_path.exists():
            return None
        return md_path.read_text(encoding="utf-8")

    async def get_block_content(
        self, doc_id: str, block_id: str
    ) -> dict[str, Any] | None:
        """Get content of a specific block."""
        ir = self._load_ir(doc_id)
        if ir is None:
            return None
        block = ir.find_block(block_id)
        if block is None:
            return None
        return {
            "id": block.id,
            "type": block.block_type.value,
            "editable": block.is_editable,
            "content": block.content,
            "style": block.style_name,
        }

    async def list_blocks(self, doc_id: str) -> list[dict[str, Any]] | None:
        """
        List all blocks in a document with summary info.

        Returns:
            List of block summaries, or None if doc not found.
        """
        ir = self._load_ir(doc_id)
        if ir is None:
            return None

        blocks = []
        for block in ir.blocks:
            preview = block.plain_text[:80] if block.plain_text else ""
            blocks.append(
                {
                    "id": block.id,
                    "type": block.block_type.value,
                    "editable": block.is_editable,
                    "style": block.style_name,
                    "preview": preview,
                }
            )
        return blocks

    # ========================================================================
    # Write-back
    # ========================================================================

    async def save_docx(
        self,
        doc_id: str,
        dfm_text: str | None = None,
        output_path: str | None = None,
        *,
        from_md: bool = False,
    ) -> dict[str, Any]:
        """
        Save edited content back to a .docx file.

        Supports two modes:
        - DFM mode (default): pass dfm_text with the full .dfm content
        - MD mode (from_md=True): reads content.md + format.yaml from disk

        Args:
            doc_id: Document ID
            dfm_text: Edited DFM content (ignored if from_md=True)
            output_path: Output .docx path (default: data/{doc_id}/output.docx)
            from_md: If True, read content.md + format.yaml instead of dfm_text

        Returns:
            Result dict with output path and any errors.
        """
        doc_dir = self.repository.get_doc_dir(doc_id)

        # Load original IR
        ir = self._load_ir(doc_id)
        if ir is None:
            return {"success": False, "error": f"IR not found for {doc_id}"}

        try:
            # Parse edits from the appropriate format
            if from_md:
                md_path = doc_dir / "content.md"
                yaml_path = doc_dir / "format.yaml"
                if not md_path.exists() or not yaml_path.exists():
                    return {
                        "success": False,
                        "error": "content.md or format.yaml not found",
                    }
                md_content = md_path.read_text(encoding="utf-8")
                yaml_content = yaml_path.read_text(encoding="utf-8")

                split_report = self.integrity.check_split_consistency(
                    md_content, yaml_content
                )
                if split_report.error_count:
                    return {
                        "success": False,
                        "error": (
                            "Split format consistency check failed. "
                            "Fix duplicate/mismatched markers in content.md and "
                            "format.yaml before save_docx."
                        ),
                        "warnings": [i.message for i in split_report.issues],
                    }

                parse_result = self.parser.parse_split(md_content, yaml_content)
            else:
                if dfm_text is None:
                    return {"success": False, "error": "No content provided"}
                parse_result = self.parser.parse(dfm_text)

            # Abort on format mismatch — prevents silent data loss
            format_errors = [
                e for e in parse_result.errors if e.startswith("FORMAT_MISMATCH")
            ]
            if format_errors:
                return {
                    "success": False,
                    "error": (
                        "Split-format content (<!-- @ID -->) was passed to the DFM "
                        "parser which expects <!-- @b:ID --> markers. No edits were "
                        "detected. Aborting to prevent data loss. "
                        "Use save_docx with from_md=True, or pass .dfm-format content."
                    ),
                }

            duplicate_id_errors = [
                e for e in parse_result.errors if e.startswith("DUPLICATE_ID")
            ]
            if duplicate_id_errors:
                return {
                    "success": False,
                    "error": (
                        "Duplicate marker IDs detected in edited content. "
                        "Aborting to prevent ambiguous write-back. "
                        "Please make all <!-- @ID --> markers unique."
                    ),
                    "warnings": duplicate_id_errors,
                }

            # Verify checksum matches
            if parse_result.checksum and parse_result.checksum != ir.checksum:
                logger.warning(
                    "Checksum mismatch: DFM=%s, IR=%s",
                    parse_result.checksum,
                    ir.checksum,
                )

            # --- Pre-save integrity check + auto-repair ---
            pre_report = self.integrity.check_pre_save(ir, parse_result)
            for edit in parse_result.edits:
                if edit.table_rows:
                    block = ir.find_block(edit.block_id)
                    if block and block.content:
                        edit.table_rows, repair = self.integrity.auto_repair_table_edit(
                            block.content, edit.table_rows
                        )
                        for issue in repair.issues:
                            pre_report.add(issue)
            if pre_report.issues:
                logger.info("Pre-save check: %s", pre_report.to_summary())

            # Apply edits to IR
            ir = self.parser.apply_edits(ir, parse_result)

            # Determine output path
            out = doc_dir / "output.docx" if output_path is None else Path(output_path)

            # Rebuild docx
            result_path = self.adapter.ir_to_docx(ir, doc_dir, out)

            # Save updated IR
            self._save_ir(ir, doc_dir / "ir.json")

            # --- Auto-backup before overwrite ---
            self._backup_before_overwrite(doc_dir)

            # Snapshot old content.md for drift detection
            old_md_path = doc_dir / "content.md"
            old_md_text = (
                old_md_path.read_text(encoding="utf-8") if old_md_path.exists() else ""
            )

            # Update all formats with current state
            updated_dfm = self.renderer.render(ir)
            (doc_dir / "content.dfm").write_text(updated_dfm, encoding="utf-8")

            md_text, yaml_text = self.renderer.render_split(ir)
            (doc_dir / "content.md").write_text(md_text, encoding="utf-8")
            (doc_dir / "format.yaml").write_text(yaml_text, encoding="utf-8")

            # --- Content drift detection ---
            drift_issues = self._detect_content_drift(old_md_text, md_text)
            for issue in drift_issues:
                pre_report.add(issue)

            # --- Post-save integrity check ---
            original_path = doc_dir / "original.docx"
            post_report = self.integrity.check_post_save(original_path, result_path)

            result: dict[str, Any] = {
                "success": True,
                "output_path": str(result_path),
                "integrity": post_report.to_summary(),
            }
            warnings = list(parse_result.errors)
            for issue in pre_report.issues + post_report.issues:
                if issue.severity in ("error", "warning"):
                    prefix = "[auto-fixed] " if issue.auto_fixed else ""
                    warnings.append(f"{prefix}{issue.message}")
            if warnings:
                result["warnings"] = warnings
            return result

        except Exception as e:
            logger.exception("Failed to save docx: %s", doc_id)
            return {"success": False, "error": str(e)}

    # ========================================================================
    # Content drift detection
    # ========================================================================

    @staticmethod
    def _detect_content_drift(old_md: str, new_md: str) -> list[IntegrityIssue]:
        """Compare old vs re-rendered content.md and flag significant losses.

        Detects:
        - Lines present in old but absent in new (deleted content)
        - Substantial character-level shrinkage (>5%)

        Returns list of IntegrityIssue objects for any detected drift.
        """
        issues: list[IntegrityIssue] = []
        if not old_md:
            return issues

        # --- Character-level shrinkage check ---
        old_len = len(old_md)
        new_len = len(new_md)
        if old_len > 0 and new_len < old_len * 0.95:
            shrinkage_pct = (1 - new_len / old_len) * 100
            issues.append(
                IntegrityIssue(
                    severity="warning",
                    stage="content_drift",
                    message=(
                        f"Content shrunk by {shrinkage_pct:.1f}% after re-render "
                        f"({old_len} → {new_len} chars). Possible data loss."
                    ),
                    details={"old_len": old_len, "new_len": new_len},
                )
            )

        # --- Line-level diff: find lost non-trivial lines ---
        old_lines = [
            ln.strip()
            for ln in old_md.splitlines()
            if ln.strip() and not ln.strip().startswith("<!--")
        ]
        new_lines_set = {
            ln.strip()
            for ln in new_md.splitlines()
            if ln.strip() and not ln.strip().startswith("<!--")
        }

        lost_lines = [
            ln for ln in old_lines if ln not in new_lines_set and len(ln) > 20
        ]
        if lost_lines:
            preview = lost_lines[:5]
            issues.append(
                IntegrityIssue(
                    severity="warning",
                    stage="content_drift",
                    message=(
                        f"{len(lost_lines)} non-trivial lines lost after re-render. "
                        f"Samples: {preview}"
                    ),
                    details={"lost_count": len(lost_lines), "samples": preview},
                )
            )

        if issues:
            logger.warning(
                "Content drift detected: %d issues. Check .backups/ for recovery.",
                len(issues),
            )

        return issues

    # ========================================================================
    # IR persistence
    # ========================================================================

    @staticmethod
    def _backup_before_overwrite(doc_dir: Path, max_backups: int = 5) -> None:
        """Create timestamped backups of content.md, content.dfm, format.yaml, ir.json before overwrite.

        Keeps at most `max_backups` backup sets (oldest are pruned).
        """
        backup_dir = doc_dir / ".backups"
        backup_dir.mkdir(exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slot = backup_dir / ts
        slot.mkdir(exist_ok=True)

        for name in ("content.md", "content.dfm", "format.yaml", "ir.json"):
            src = doc_dir / name
            if src.exists():
                shutil.copy2(src, slot / name)

        logger.info("Pre-overwrite backup created: %s", slot)

        # Prune old backups — keep newest max_backups
        existing = sorted(
            [d for d in backup_dir.iterdir() if d.is_dir()],
            key=lambda p: p.name,
        )
        while len(existing) > max_backups:
            old = existing.pop(0)
            shutil.rmtree(old, ignore_errors=True)
            logger.info("Pruned old backup: %s", old)

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
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

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

            # Runs
            if bd.get("runs"):
                block.runs = [FormatRun.from_dict(r) for r in bd["runs"]]

            # Merged cells
            if bd.get("merged_cells"):
                block.merged_cells = [
                    MergedCell.from_dict(mc) for mc in bd["merged_cells"]
                ]

            # Cell formats
            if bd.get("cell_formats"):
                block.cell_formats = {
                    k: CellFormat.from_dict(v) for k, v in bd["cell_formats"].items()
                }

            # Image anchor
            if bd.get("image_anchor"):
                block.image_anchor = ImageAnchorType(bd["image_anchor"])

            # Break type
            if bd.get("break_type"):
                block.break_type = BreakType(bd["break_type"])

            # Section page setup
            if bd.get("section_page_setup"):
                block.section_page_setup = PageSetup.from_dict(bd["section_page_setup"])

            ir.blocks.append(block)

        return ir
