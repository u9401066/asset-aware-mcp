"""
Application Layer - Docx Service

Use cases for docx ingestion, DFM conversion, and write-back.
Orchestrates DocxAdapter, DfmRenderer, and DfmParser.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.application.dfm_integrity import DfmIntegrityChecker, IntegrityIssue
from src.application.output_paths import resolve_document_output_path
from src.domain.docx_entities import DfmBlock, DocxIR
from src.domain.docx_value_objects import DfmBlockType
from src.infrastructure.dfm_parser import DfmParser
from src.infrastructure.dfm_renderer import DfmRenderer
from src.infrastructure.docx_adapter import DocxAdapter
from src.infrastructure.encoding_guard import (
    EncodingError,
    normalize_text_input,
    read_text_file,
    sanitize_id_stem,
    validate_docx_structure,
    validate_zip_magic,
    write_utf8_text,
)

if TYPE_CHECKING:
    from src.domain.repositories import DocumentRepository

logger = logging.getLogger(__name__)

RESERVED_DOCX_ARTIFACT_NAMES = {
    "content.dfm",
    "content.md",
    "format.yaml",
    "ir.json",
    "original.docx",
    "revisions.jsonl",
}
_REVISION_TOKEN_RE = re.compile(r"\s+|\S+")


class DocxService:
    """
    Application service for docx ↔ DFM operations.

    Orchestrates:
    1. ingest_docx: .docx → DocxIR → content.dfm + ir.json + preserved parts
    2. get_dfm: Read the editable DFM content
    3. save_docx: Edited DFM → parse edits → merge with IR → rebuild .docx
    4. list_blocks: Summary of all blocks in the document
    """

    def __init__(
        self,
        repository: DocumentRepository,
        export_root: Path | None = None,
    ):
        self.repository = repository
        self.adapter = DocxAdapter()
        self.renderer = DfmRenderer()
        self.parser = DfmParser()
        self.integrity = DfmIntegrityChecker()
        repo_base = getattr(repository, "base_dir", None)
        if export_root is None and isinstance(repo_base, str | os.PathLike):
            export_root = Path(repo_base) / "exports"
        self.export_root = (export_root or Path.cwd() / "exports").resolve()
        self.export_root.mkdir(parents=True, exist_ok=True)

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

        # Auto-convert .doc / .odt / .ods to .docx via LibreOffice
        if path.suffix.lower() in (".doc", ".odt", ".ods"):
            converted = self._convert_to_docx_via_libreoffice(path)
            if converted is None:
                return {
                    "success": False,
                    "error": (
                        f"Failed to convert {path.suffix} to .docx: {path}. "
                        "Please install LibreOffice and ensure the 'libreoffice' or "
                        "'soffice' binary is available, or set LIBREOFFICE_BIN."
                    ),
                }
            logger.info(
                "Auto-converted %s → .docx: %s → %s",
                path.suffix,
                path,
                converted,
            )
            path = converted

        if path.suffix.lower() not in (".docx", ".docm"):
            return {"success": False, "error": f"Not a docx file: {path}"}

        # Reject files that are not actually ZIP archives (fail-closed).
        try:
            validate_zip_magic(path)
        except EncodingError as exc:
            return {"success": False, "error": str(exc)}

        try:
            # Generate doc_id from sanitized filename stem + content hash.
            # sanitize_id_stem ensures the id is filesystem-safe even for
            # filenames with CJK/accented/special characters.
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            safe_stem = sanitize_id_stem(path.stem)
            doc_id = f"docx_{safe_stem}_{checksum}"

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
            write_utf8_text(dfm_path, dfm_text, hint=str(dfm_path))

            # Render split format: clean MD + format YAML
            md_text, yaml_text = self.renderer.render_split(ir)
            md_path = doc_dir / "content.md"
            write_utf8_text(md_path, md_text, hint=str(md_path))
            yaml_path = doc_dir / "format.yaml"
            write_utf8_text(yaml_path, yaml_text, hint=str(yaml_path))

            # Save IR as JSON for round-trip
            self._save_ir(ir, doc_dir / "ir.json")

            # --- Post-ingest integrity check ---
            ingest_report = self.integrity.check_ingest(ir, md_text, yaml_text)
            if not ingest_report.passed:
                # Auto-repair and re-render
                md_text, yaml_text, repair_report = self.integrity.auto_repair_split(
                    md_text, yaml_text, ir
                )
                write_utf8_text(md_path, md_text, hint=str(md_path))
                write_utf8_text(yaml_path, yaml_text, hint=str(yaml_path))
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
    # .doc conversion
    # ========================================================================

    @staticmethod
    def _find_libreoffice_binary() -> str | None:
        """Find a LibreOffice executable across Windows/Linux/macOS."""
        env_candidate = os.getenv("LIBREOFFICE_BIN")
        if env_candidate and Path(env_candidate).exists():
            return env_candidate

        for binary_name in ("libreoffice", "soffice"):
            resolved = shutil.which(binary_name)
            if resolved:
                return resolved

        import sys

        platform_candidates: list[str] = []
        if os.name == "nt":
            # Windows — check both 64-bit and 32-bit Program Files
            for pf in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
                pf_path = os.getenv(pf)
                if pf_path:
                    platform_candidates.append(
                        str(Path(pf_path) / "LibreOffice" / "program" / "soffice.exe")
                    )
        elif sys.platform == "darwin":
            # macOS app bundle
            platform_candidates.extend(
                [
                    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
                    "/Applications/LibreOffice.app/Contents/MacOS/libreoffice",
                ]
            )
        else:
            # Linux — common install locations
            platform_candidates.extend(
                [
                    "/usr/bin/libreoffice",
                    "/usr/bin/soffice",
                    "/snap/bin/libreoffice",
                ]
            )

        for candidate in platform_candidates:
            if Path(candidate).exists():
                return candidate

        return None

    @staticmethod
    def _convert_doc_to_docx(doc_path: Path) -> Path | None:
        """Convert a legacy .doc file to .docx using LibreOffice.

        Returns the path to the converted .docx, or None on failure.
        """
        return DocxService._convert_to_docx_via_libreoffice(doc_path)

    @staticmethod
    def _convert_to_docx_via_libreoffice(source_path: Path) -> Path | None:
        """Convert any LibreOffice-supported file (.doc/.odt/.ods) to .docx.

        Returns the path to the converted .docx, or None on failure.
        """
        try:
            libreoffice_bin = DocxService._find_libreoffice_binary()
            if libreoffice_bin is None:
                logger.error(
                    "LibreOffice not installed or not discoverable. "
                    "Checked LIBREOFFICE_BIN, libreoffice, soffice, and the macOS app bundle."
                )
                return None

            with tempfile.TemporaryDirectory() as tmp_dir:
                result = subprocess.run(
                    [
                        libreoffice_bin,
                        "--headless",
                        "--convert-to",
                        "docx",
                        str(source_path),
                        "--outdir",
                        tmp_dir,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                if result.returncode != 0:
                    logger.error(
                        "LibreOffice %s→docx failed: %s",
                        source_path.suffix,
                        result.stderr,
                    )
                    return None

                # Find the converted file
                converted = Path(tmp_dir) / (source_path.stem + ".docx")
                if not converted.exists():
                    logger.error("Converted file not found: %s", converted)
                    return None

                # Move to same directory as original
                dest = source_path.with_suffix(".docx")
                if dest.exists():
                    logger.error(
                        "Refusing to overwrite existing converted DOCX: %s", dest
                    )
                    return None
                shutil.move(str(converted), str(dest))
                validate_docx_structure(dest)
                return dest
        except FileNotFoundError:
            logger.error("LibreOffice not installed")
            return None
        except subprocess.TimeoutExpired:
            logger.error("LibreOffice conversion timed out")
            return None

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
        return read_text_file(dfm_path, hint=f"DFM for {doc_id}")

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
        return read_text_file(md_path, hint=f"Markdown for {doc_id}")

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

    async def list_documents(self) -> list[dict[str, Any]]:
        """List all ingested DOCX/DFM documents."""
        return self.repository.list_docx_documents()

    async def delete_docx(self, doc_id: str) -> dict[str, Any]:
        """Delete an ingested DOCX/DFM document and all local artifacts."""
        documents = self.repository.list_docx_documents()
        document = next(
            (item for item in documents if item.get("doc_id") == doc_id), None
        )
        if document is None:
            return {"success": False, "error": f"DOCX document not found: {doc_id}"}

        deleted = self.repository.delete_document(doc_id)
        if not deleted:
            return {
                "success": False,
                "error": f"Failed to delete DOCX document directory for {doc_id}",
            }

        return {
            "success": True,
            "doc_id": doc_id,
            "filename": document.get("filename", ""),
        }

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
        force: bool = False,
        track_changes: bool = False,
        revision_author: str = "Asset-Aware MCP",
        _allow_external_output: bool = False,
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
            track_changes: If True, emit DFM edits as native Word revisions
            revision_author: Author recorded on generated Word revisions

        Returns:
            Result dict with output path and any errors.
        """
        doc_dir = self.repository.get_doc_dir(doc_id)
        staged_out: Path | None = None
        save_warnings: list[str] = []

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
                md_content = read_text_file(md_path, hint=f"Markdown for {doc_id}")
                yaml_content = read_text_file(yaml_path, hint=f"YAML for {doc_id}")
                md_content = normalize_text_input(
                    md_content, hint=f"Markdown for {doc_id}"
                )
                yaml_content = normalize_text_input(
                    yaml_content, hint=f"YAML for {doc_id}"
                )

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
                    persisted_dfm = doc_dir / "content.dfm"
                    if not persisted_dfm.exists():
                        return {"success": False, "error": "No content provided"}
                    dfm_text = read_text_file(persisted_dfm, hint=f"DFM for {doc_id}")
                # Normalise user-supplied text: strip BOM, reject NUL bytes.
                try:
                    dfm_text = normalize_text_input(dfm_text, hint="dfm_text")
                except EncodingError as exc:
                    return {"success": False, "error": str(exc)}
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
                stale_message = (
                    "Stale DFM edit detected: edited DFM checksum "
                    f"{parse_result.checksum} does not match the current IR checksum "
                    f"{ir.checksum}. Re-open the current DFM or re-ingest the document "
                    "before saving; use force=True only when you have manually verified "
                    "the edit is based on the current document."
                )
                logger.warning(
                    "%s",
                    stale_message,
                )
                if not force:
                    return {
                        "success": False,
                        "error": stale_message,
                        "warnings": [
                            (
                                "Saving was aborted before applying edits to prevent "
                                "overwriting a newer DFM/IR session."
                            )
                        ],
                    }
                save_warnings.append(
                    "Forced stale DFM save: edited DFM checksum "
                    f"{parse_result.checksum} did not match current IR checksum "
                    f"{ir.checksum}."
                )
                logger.info(
                    "Forced checksum mismatch: DFM=%s, IR=%s",
                    parse_result.checksum,
                    ir.checksum,
                )

            # --- Pre-save integrity check + auto-repair ---
            pre_report = self.integrity.check_pre_save(ir, parse_result)
            table_shape_errors = self._validate_table_edit_shapes(ir, parse_result)
            if table_shape_errors:
                return {
                    "success": False,
                    "error": (
                        "Table structural edits are not supported by safe DOCX "
                        "write-back. Preserve the original row/column shape, or "
                        "rebuild the table in Word."
                    ),
                    "warnings": table_shape_errors,
                }
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

            original_ir = deepcopy(ir)

            # Apply edits to IR
            ir = self.parser.apply_edits(ir, parse_result)

            expected_changed_ids = self._expected_changed_block_ids(
                original_ir, parse_result
            )
            expected_diff_locations = self._expected_content_diff_locations(
                original_ir,
                parse_result,
                expected_changed_ids,
            )
            expected_diff_counts = {
                "text": len(expected_diff_locations["text"]),
                "table": len(expected_diff_locations["table"]),
            }
            unexpected_mutations = self._detect_unedited_block_mutations(
                original_ir, ir, expected_changed_ids
            )
            if unexpected_mutations:
                return {
                    "success": False,
                    "error": (
                        "Unexpected changes detected in unedited blocks during write-back. "
                        "Aborting to prevent silent document corruption."
                    ),
                    "warnings": unexpected_mutations,
                }

            if _allow_external_output and output_path is not None:
                out = Path(output_path)
                out.parent.mkdir(parents=True, exist_ok=True)
            else:
                try:
                    out = resolve_document_output_path(
                        doc_dir,
                        output_path,
                        default_name="output.docx",
                        allowed_suffixes={".docx"},
                        reserved_names=RESERVED_DOCX_ARTIFACT_NAMES,
                    )
                except ValueError as e:
                    return {"success": False, "error": str(e)}

            # Snapshot old content.md for drift detection
            old_md_path = doc_dir / "content.md"
            old_md_text = (
                old_md_path.read_text(encoding="utf-8") if old_md_path.exists() else ""
            )

            # Render new artifacts before touching disk so fail-safe checks can abort
            # without leaving partially updated DFM state or output files behind.
            updated_dfm = self.renderer.render(ir)
            md_text, yaml_text = self.renderer.render_split(ir)

            # --- Content drift detection ---
            drift_issues = self._detect_content_drift(old_md_text, md_text)
            for issue in drift_issues:
                pre_report.add(issue)

            # --- Fail-safe: reject output if severe content loss detected ---
            if old_md_text and not force:
                old_len = len(self._normalize_markdown_for_drift(old_md_text))
                new_len = len(self._normalize_markdown_for_drift(md_text))
                if old_len > 100 and new_len < old_len * 0.5:
                    shrinkage_pct = (1 - new_len / old_len) * 100
                    logger.error(
                        "Content shrunk by %.1f%% (%d → %d chars). "
                        "Refusing to output corrupted docx.",
                        shrinkage_pct,
                        old_len,
                        new_len,
                    )
                    return {
                        "success": False,
                        "error": (
                            f"Content shrunk by {shrinkage_pct:.1f}% "
                            f"({old_len} → {new_len} chars). "
                            f"Refusing to output — likely data loss. "
                            f"Check .backups/ for recovery. "
                            f"Use force=True to override."
                        ),
                    }

            original_path = doc_dir / "original.docx"
            staged_out = self._staged_docx_output_path(out)
            if not expected_changed_ids:
                shutil.copy2(original_path, staged_out)
                result_path = staged_out
            else:
                adapter_kwargs: dict[str, Any] = {
                    "changed_block_ids": expected_changed_ids,
                }
                if track_changes:
                    adapter_kwargs.update(
                        {
                            "original_ir": original_ir,
                            "track_changes": True,
                            "revision_author": revision_author or "Asset-Aware MCP",
                        }
                    )
                result_path = self.adapter.ir_to_docx(
                    ir,
                    doc_dir,
                    staged_out,
                    **adapter_kwargs,
                )

            # --- Post-save integrity check before touching user-visible files ---
            post_report = self.integrity.check_post_save(
                original_path,
                result_path,
                content_edits_expected=bool(expected_changed_ids),
                expected_text_diffs=expected_diff_counts["text"],
                expected_table_diffs=expected_diff_counts["table"],
                expected_text_diff_locations=expected_diff_locations["text"],
                expected_table_diff_locations=expected_diff_locations["table"],
                revision_markup_expected=track_changes,
            )
            if not post_report.passed and not force:
                warnings = list(parse_result.errors) + save_warnings
                for issue in pre_report.issues + post_report.issues:
                    if issue.severity in ("error", "warning"):
                        prefix = "[auto-fixed] " if issue.auto_fixed else ""
                        warnings.append(f"{prefix}{issue.message}")
                try:
                    staged_out.unlink(missing_ok=True)
                except OSError:
                    logger.warning("Failed to remove staged docx: %s", staged_out)
                return {
                    "success": False,
                    "error": (
                        "Post-save integrity check failed; output and editable "
                        "artifacts were not overwritten. Use force=True to override."
                    ),
                    "integrity": post_report.to_summary(),
                    "warnings": warnings,
                }

            # --- Auto-backup before overwriting DFM state ---
            self._backup_before_overwrite(doc_dir)

            staged_out.replace(out)
            result_path = out
            staged_out = None

            # Save updated IR and synchronized editable artifacts.
            self._save_ir(ir, doc_dir / "ir.json")
            write_utf8_text(
                doc_dir / "content.dfm", updated_dfm, hint=f"DFM for {doc_id}"
            )
            write_utf8_text(
                doc_dir / "content.md", md_text, hint=f"Markdown for {doc_id}"
            )
            write_utf8_text(
                doc_dir / "format.yaml", yaml_text, hint=f"YAML for {doc_id}"
            )

            result: dict[str, Any] = {
                "success": True,
                "output_path": str(result_path),
                "integrity": post_report.to_summary(),
                "track_changes": track_changes,
            }
            if track_changes:
                result["revision_author"] = revision_author or "Asset-Aware MCP"
                result["track_change_blocks"] = len(expected_changed_ids)
                revision_sidecar, revision_count = self._write_revision_sidecar(
                    doc_dir,
                    original_ir,
                    ir,
                    expected_changed_ids,
                    result_path,
                )
                result["revision_sidecar_path"] = str(revision_sidecar)
                result["revision_records"] = revision_count
            warnings = list(parse_result.errors) + save_warnings
            for issue in pre_report.issues + post_report.issues:
                if issue.severity in ("error", "warning"):
                    prefix = "[auto-fixed] " if issue.auto_fixed else ""
                    warnings.append(f"{prefix}{issue.message}")
            if warnings:
                result["warnings"] = warnings
            return result

        except Exception as e:
            if staged_out is not None and staged_out.exists():
                try:
                    staged_out.unlink()
                except OSError:
                    logger.warning("Failed to remove staged docx: %s", staged_out)
            logger.exception("Failed to save docx: %s", doc_id)
            return {"success": False, "error": str(e)}

    def _write_revision_sidecar(
        self,
        doc_dir: Path,
        original_ir: DocxIR,
        updated_ir: DocxIR,
        changed_block_ids: set[str],
        output_docx: Path,
    ) -> tuple[Path, int]:
        """Write machine-readable DFM edit spans for citation-ready consumers."""
        original_blocks = {block.id: block for block in original_ir.blocks}
        records: list[dict[str, Any]] = []

        for block in updated_ir.blocks:
            if block.id not in changed_block_ids:
                continue
            original_block = original_blocks.get(block.id)
            if original_block is None:
                continue

            old_text = self._block_write_text(original_block)
            new_text = self._block_write_text(block)
            if old_text == new_text:
                continue

            records.extend(
                self._revision_records_for_block(
                    updated_ir,
                    block,
                    old_text,
                    new_text,
                    output_docx,
                    start_index=len(records),
                )
            )

        sidecar_path = doc_dir / "revisions.jsonl"
        with sidecar_path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return sidecar_path, len(records)

    def _revision_records_for_block(
        self,
        ir: DocxIR,
        block: DfmBlock,
        old_text: str,
        new_text: str,
        output_docx: Path,
        *,
        start_index: int,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        old_tokens = _REVISION_TOKEN_RE.findall(old_text)
        new_tokens = _REVISION_TOKEN_RE.findall(new_text)
        old_offsets = self._token_offsets(old_tokens)
        new_offsets = self._token_offsets(new_tokens)
        matcher = SequenceMatcher(None, old_tokens, new_tokens, autojunk=False)

        for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
            if tag == "equal":
                continue
            old_char_range = [old_offsets[old_start], old_offsets[old_end]]
            new_char_range = [new_offsets[new_start], new_offsets[new_end]]
            if tag in {"delete", "replace"} and old_char_range[0] != old_char_range[1]:
                records.append(
                    self._build_revision_record(
                        ir,
                        block,
                        output_docx,
                        op="delete",
                        old_text=old_text,
                        new_text=new_text,
                        old_char_range=old_char_range,
                        new_char_range=[new_char_range[0], new_char_range[0]],
                        index=start_index + len(records) + 1,
                    )
                )
            if tag in {"insert", "replace"} and new_char_range[0] != new_char_range[1]:
                records.append(
                    self._build_revision_record(
                        ir,
                        block,
                        output_docx,
                        op="insert",
                        old_text=old_text,
                        new_text=new_text,
                        old_char_range=[old_char_range[0], old_char_range[0]],
                        new_char_range=new_char_range,
                        index=start_index + len(records) + 1,
                    )
                )
        return records

    def _build_revision_record(
        self,
        ir: DocxIR,
        block: DfmBlock,
        output_docx: Path,
        *,
        op: str,
        old_text: str,
        new_text: str,
        old_char_range: list[int],
        new_char_range: list[int],
        index: int,
    ) -> dict[str, Any]:
        old_quote = old_text[old_char_range[0] : old_char_range[1]]
        new_quote = new_text[new_char_range[0] : new_char_range[1]]
        return {
            "schema": "asset-aware.docx-revisions.v1",
            "doc_id": ir.doc_id,
            "source_revision_id": ir.checksum,
            "revision_id": f"{block.id}:rev{index:04d}",
            "block_id": block.id,
            "block_type": block.block_type.value,
            "op": op,
            "output_docx": str(output_docx),
            "old_text": old_quote,
            "new_text": new_quote,
            "old_text_hash": self._sha256_text(old_quote),
            "new_text_hash": self._sha256_text(new_quote),
            "old_char_range": old_char_range,
            "new_char_range": new_char_range,
            "old_byte_range": self._byte_range(old_text, old_char_range),
            "new_byte_range": self._byte_range(new_text, new_char_range),
            "old_context": self._range_context(old_text, old_char_range),
            "new_context": self._range_context(new_text, new_char_range),
            "locator": {
                "doc_id": ir.doc_id,
                "block_id": block.id,
                "source_revision_id": ir.checksum,
                "old_char_range": old_char_range,
                "new_char_range": new_char_range,
            },
        }

    @staticmethod
    def _block_write_text(block: DfmBlock) -> str:
        return block.plain_text if block.runs else block.content

    @staticmethod
    def _token_offsets(tokens: list[str]) -> list[int]:
        offsets = [0]
        cursor = 0
        for token in tokens:
            cursor += len(token)
            offsets.append(cursor)
        return offsets

    @staticmethod
    def _byte_range(text: str, char_range: list[int]) -> list[int]:
        start, end = char_range
        return [len(text[:start].encode("utf-8")), len(text[:end].encode("utf-8"))]

    @staticmethod
    def _range_context(text: str, char_range: list[int], radius: int = 40) -> str:
        start, end = char_range
        return text[max(0, start - radius) : min(len(text), end + radius)]

    @staticmethod
    def _sha256_text(text: str) -> str:
        return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"

    async def convert_to_pdf(
        self,
        doc_id: str,
        output_path: str | None = None,
        *,
        mode: str = "fidelity",
    ) -> dict[str, Any]:
        """
        Convert an ingested DOCX/DFM document to PDF.

        Supported modes:
        - ``fidelity``: rebuild current DOCX state and render via LibreOffice.
        - ``content``: unsupported because DOCX already has a layout-preserving source.
        """
        if mode != "fidelity":
            return {
                "success": False,
                "error": (
                    "DOCX → PDF currently supports fidelity mode only. "
                    "Use fidelity mode to preserve layout via LibreOffice."
                ),
            }

        doc_dir = self.repository.get_doc_dir(doc_id)
        if not (doc_dir / "ir.json").exists():
            return {"success": False, "error": f"IR not found for {doc_id}"}

        dfm_text = await self.get_dfm(doc_id)
        if dfm_text is None:
            return {"success": False, "error": f"DFM not found for {doc_id}"}

        try:
            target_pdf = resolve_document_output_path(
                doc_dir,
                output_path,
                default_name="output.pdf",
                allowed_suffixes={".pdf"},
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            temp_docx = tmp_dir / f"{doc_id}.docx"

            save_result = await self.save_docx(
                doc_id,
                dfm_text,
                str(temp_docx),
                _allow_external_output=True,
            )
            if not save_result.get("success"):
                return save_result

            converted_pdf = self._convert_docx_file_to_pdf(temp_docx, target_pdf)
            if converted_pdf is not None and not Path(converted_pdf).exists():
                return {
                    "success": False,
                    "error": f"PDF conversion reported success but file is missing: {converted_pdf}",
                }
            if converted_pdf is None:
                return {
                    "success": False,
                    "error": (
                        "Failed to convert DOCX to PDF. Please install LibreOffice and ensure "
                        "the 'libreoffice' or 'soffice' binary is available, or set LIBREOFFICE_BIN."
                    ),
                }

        return {
            "success": True,
            "doc_id": doc_id,
            "output_path": str(converted_pdf),
            "mode": mode,
        }

    async def convert_to_doc(
        self,
        doc_id: str,
        output_path: str | None = None,
        *,
        mode: str = "fidelity",
    ) -> dict[str, Any]:
        """
        Convert an ingested DOCX/DFM document to legacy .doc.

        Supported modes:
        - ``fidelity``: rebuild current DOCX state and render via LibreOffice.
        - ``content``: unsupported because DOCX already has a layout-preserving source.
        """
        if mode != "fidelity":
            return {
                "success": False,
                "error": (
                    "DOCX → DOC currently supports fidelity mode only. "
                    "Use fidelity mode to preserve layout via LibreOffice."
                ),
            }

        doc_dir = self.repository.get_doc_dir(doc_id)
        if not (doc_dir / "ir.json").exists():
            return {"success": False, "error": f"IR not found for {doc_id}"}

        dfm_text = await self.get_dfm(doc_id)
        if dfm_text is None:
            return {"success": False, "error": f"DFM not found for {doc_id}"}

        try:
            target_doc = resolve_document_output_path(
                doc_dir,
                output_path,
                default_name="output.doc",
                allowed_suffixes={".doc"},
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            temp_docx = tmp_dir / f"{doc_id}.docx"

            save_result = await self.save_docx(
                doc_id,
                dfm_text,
                str(temp_docx),
                _allow_external_output=True,
            )
            if not save_result.get("success"):
                return save_result

            converted_doc = self._convert_docx_file_to_doc(temp_docx, target_doc)
            if converted_doc is not None and not Path(converted_doc).exists():
                return {
                    "success": False,
                    "error": f"DOC conversion reported success but file is missing: {converted_doc}",
                }
            if converted_doc is None:
                return {
                    "success": False,
                    "error": (
                        "Failed to convert DOCX to DOC. Please install LibreOffice and ensure "
                        "the 'libreoffice' or 'soffice' binary is available, or set LIBREOFFICE_BIN."
                    ),
                }

        return {
            "success": True,
            "doc_id": doc_id,
            "output_path": str(converted_doc),
            "mode": mode,
        }

    async def convert_to_odt(
        self,
        doc_id: str,
        output_path: str | None = None,
        *,
        mode: str = "fidelity",
    ) -> dict[str, Any]:
        """
        Convert an ingested DOCX/DFM document to ODT (OpenDocument Text).

        Supported modes:
        - ``fidelity``: rebuild current DOCX state and render via LibreOffice.
        """
        if mode != "fidelity":
            return {
                "success": False,
                "error": (
                    "DOCX → ODT currently supports fidelity mode only. "
                    "Use fidelity mode to preserve layout via LibreOffice."
                ),
            }

        doc_dir = self.repository.get_doc_dir(doc_id)
        if not (doc_dir / "ir.json").exists():
            return {"success": False, "error": f"IR not found for {doc_id}"}

        dfm_text = await self.get_dfm(doc_id)
        if dfm_text is None:
            return {"success": False, "error": f"DFM not found for {doc_id}"}

        try:
            target_odt = resolve_document_output_path(
                doc_dir,
                output_path,
                default_name="output.odt",
                allowed_suffixes={".odt"},
            )
        except ValueError as e:
            return {"success": False, "error": str(e)}

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            temp_docx = tmp_dir / f"{doc_id}.docx"

            save_result = await self.save_docx(
                doc_id,
                dfm_text,
                str(temp_docx),
                _allow_external_output=True,
            )
            if not save_result.get("success"):
                return save_result

            converted_odt = self._convert_docx_file_to_odt(temp_docx, target_odt)
            if converted_odt is not None and not Path(converted_odt).exists():
                return {
                    "success": False,
                    "error": f"ODT conversion reported success but file is missing: {converted_odt}",
                }
            if converted_odt is None:
                return {
                    "success": False,
                    "error": (
                        "Failed to convert DOCX to ODT. Please install LibreOffice and ensure "
                        "the 'libreoffice' or 'soffice' binary is available, or set LIBREOFFICE_BIN."
                    ),
                }

        return {
            "success": True,
            "doc_id": doc_id,
            "output_path": str(converted_odt),
            "mode": mode,
        }

    # ========================================================================
    # Markdown → DOCX/PDF/DOC/ODT export (no prior ingest needed)
    # ========================================================================

    async def export_from_markdown(
        self,
        md_text: str | None = None,
        md_path: str | None = None,
        output_path: str | None = None,
        output_format: str = "docx",
    ) -> dict[str, Any]:
        """
        Convert standalone Markdown to DOCX, PDF, DOC, or ODT.

        Unlike save_docx (which requires a prior ingest_docx), this method
        creates a document from scratch — no original .docx is needed.

        Args:
            md_text: Markdown content as a string.
            md_path: Path to a .md file (used if md_text is None).
            output_path: Where to write the output file. Absolute paths must stay
                under the configured export root; relative paths are resolved there.
            output_format: "docx", "pdf", "doc", or "odt".

        Returns:
            Result dict with output_path and success status.
        """
        from src.infrastructure.markdown_converter import MarkdownDocxConverter

        # Resolve markdown content
        if md_text is None and md_path is not None:
            p = Path(md_path)
            if not p.exists():
                return {"success": False, "error": f"Markdown file not found: {p}"}
            md_text = read_text_file(p, hint=str(p))

        if not md_text:
            return {"success": False, "error": "No markdown content provided"}

        output_format = output_format.lower().strip()
        if output_format not in ("docx", "pdf", "doc", "odt"):
            return {
                "success": False,
                "error": f"Unsupported format: {output_format}. Use docx, pdf, doc, or odt.",
            }

        try:
            out = self._resolve_export_output_path(
                md_path=md_path,
                output_path=output_path,
                output_format=output_format,
            )
        except ValueError as exc:
            return {"success": False, "error": str(exc)}

        converter = MarkdownDocxConverter()

        try:
            if output_format == "docx":
                converter.convert(md_text, out)
                validate_docx_structure(out)
                return {"success": True, "output_path": str(out), "format": "docx"}

            # For PDF/DOC/ODT: first create a temp docx, then convert via LibreOffice
            with tempfile.TemporaryDirectory() as tmp_dir_name:
                tmp_docx = Path(tmp_dir_name) / "temp.docx"
                converter.convert(md_text, tmp_docx)

                if output_format == "pdf":
                    result = self._convert_docx_file_to_pdf(tmp_docx, out)
                elif output_format == "odt":
                    result = self._convert_docx_file_to_odt(tmp_docx, out)
                else:  # doc
                    result = self._convert_docx_file_to_doc(tmp_docx, out)

                if output_format == "docx" and result is not None:
                    validate_docx_structure(Path(result))

                if result is None:
                    return {
                        "success": False,
                        "error": (
                            f"DOCX → {output_format.upper()} conversion failed. "
                            "Please install LibreOffice and ensure the 'libreoffice' or "
                            "'soffice' binary is available, or set LIBREOFFICE_BIN."
                        ),
                    }
                return {
                    "success": True,
                    "output_path": str(result),
                    "format": output_format,
                }
        except Exception as e:
            logger.exception("export_from_markdown failed")
            return {"success": False, "error": str(e)}

    def _resolve_export_output_path(
        self,
        *,
        md_path: str | None,
        output_path: str | None,
        output_format: str,
    ) -> Path:
        suffix = f".{output_format}"
        if output_path:
            candidate = Path(output_path)
        else:
            stem = sanitize_id_stem(Path(md_path).stem) if md_path else "output"
            candidate = Path(f"{stem}{suffix}")

        if candidate.suffix.lower() != suffix:
            raise ValueError(f"Output path must end with {suffix}")

        if not candidate.is_absolute():
            candidate = self.export_root / candidate
        resolved = candidate.resolve()

        try:
            resolved.relative_to(self.export_root)
        except ValueError as exc:
            raise ValueError(
                f"Output path must stay within export root: {self.export_root}"
            ) from exc

        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved

    @staticmethod
    def _block_signature(block: DfmBlock) -> dict[str, Any]:
        """Build a comparable snapshot for a DFM block."""
        return asdict(block)

    def _expected_changed_block_ids(
        self,
        original_ir: DocxIR,
        parse_result: Any,
    ) -> set[str]:
        """Determine which block IDs are expected to change based on parsed edits."""
        changed_ids: set[str] = set()

        for edit in parse_result.edits:
            block = original_ir.find_block(edit.block_id)
            if block is None or block.is_protected:
                continue

            if edit.table_rows is not None:
                current_rows = self.parser._parse_md_table(block.content)
                if self._normalize_table_rows(
                    edit.table_rows
                ) != self._normalize_table_rows(current_rows):
                    changed_ids.add(edit.block_id)
                continue

            if edit.updated_runs is not None:
                expected_runs = [run.to_dict() for run in edit.updated_runs]
                current_runs = [run.to_dict() for run in block.runs]
                runs_text = "".join(run.text for run in edit.updated_runs)
                expected_content = edit.new_content or runs_text
                if expected_runs != current_runs or expected_content != block.content:
                    changed_ids.add(edit.block_id)
                continue

            current_text = block.plain_text if block.runs else block.content
            if edit.new_content != current_text:
                changed_ids.add(edit.block_id)

        return changed_ids

    def _expected_content_diff_counts(
        self,
        original_ir: DocxIR,
        parse_result: Any,
        expected_changed_ids: set[str],
    ) -> dict[str, int]:
        """Count post-save text/table diffs expected from semantic DFM edits."""
        locations = self._expected_content_diff_locations(
            original_ir,
            parse_result,
            expected_changed_ids,
        )
        return {"text": len(locations["text"]), "table": len(locations["table"])}

    def _expected_content_diff_locations(
        self,
        original_ir: DocxIR,
        parse_result: Any,
        expected_changed_ids: set[str],
    ) -> dict[str, set[str]]:
        """Map expected DFM edits to DocxValidator text/table diff locations."""
        paragraph_locations: dict[str, str] = {}
        table_locations: dict[str, int] = {}
        paragraph_index = 0
        table_index = 0

        for ir_block in original_ir.blocks:
            if ir_block.block_type == DfmBlockType.TABLE:
                table_index += 1
                table_locations[ir_block.id] = table_index
            elif self._is_body_text_block(ir_block):
                paragraph_index += 1
                paragraph_locations[ir_block.id] = f"paragraph {paragraph_index}"

        text_locations: set[str] = set()
        table_cell_locations: set[str] = set()
        for edit in parse_result.edits:
            if edit.block_id not in expected_changed_ids:
                continue

            edited_block = original_ir.find_block(edit.block_id)
            if edited_block is None:
                continue

            if edit.table_rows is not None:
                table_number = table_locations.get(edit.block_id)
                if table_number is not None:
                    table_cell_locations.update(
                        self._changed_table_cell_locations(
                            table_number,
                            self.parser._parse_md_table(edited_block.content),
                            edit.table_rows,
                        )
                    )
                table_cell_locations.update(
                    self._parent_table_cell_locations(edited_block, table_locations)
                )
                continue

            location = paragraph_locations.get(edit.block_id)
            if location is not None:
                text_locations.add(location)

        return {"text": text_locations, "table": table_cell_locations}

    @staticmethod
    def _is_body_text_block(block: DfmBlock) -> bool:
        """Return True for editable blocks represented as body paragraphs."""
        return block.block_type in {
            DfmBlockType.PARAGRAPH,
            DfmBlockType.HEADING,
            DfmBlockType.LIST_ITEM,
            DfmBlockType.FORMAT,
            DfmBlockType.CAPTION,
        }

    def _changed_table_cell_locations(
        self,
        table_number: int,
        original_rows: list[list[str]] | None,
        edited_rows: list[list[str]] | None,
    ) -> set[str]:
        """Return DocxValidator locations for table cells changed by an edit."""
        original = self._normalize_table_rows(original_rows)
        edited = self._normalize_table_rows(edited_rows)
        locations: set[str] = set()

        for row_index in range(max(len(original), len(edited))):
            original_row = original[row_index] if row_index < len(original) else []
            edited_row = edited[row_index] if row_index < len(edited) else []
            for col_index in range(max(len(original_row), len(edited_row))):
                original_cell = (
                    original_row[col_index] if col_index < len(original_row) else ""
                )
                edited_cell = (
                    edited_row[col_index] if col_index < len(edited_row) else ""
                )
                if original_cell != edited_cell:
                    locations.add(
                        f"table {table_number}/row {row_index + 1}/col {col_index + 1}"
                    )

        return locations

    @staticmethod
    def _parent_table_cell_locations(
        block: DfmBlock,
        table_locations: dict[str, int],
    ) -> set[str]:
        """Return parent cell locations dirtied by nested table edits."""
        parent_table_id = block.metadata.get("parent_table_id")
        if not parent_table_id or not block.parent_cell:
            return set()

        table_number = table_locations.get(str(parent_table_id))
        if table_number is None:
            return set()

        row_text, separator, col_text = block.parent_cell.partition(":")
        if not separator:
            return set()

        try:
            row_index = int(row_text)
            col_index = int(col_text)
        except ValueError:
            return set()

        return {f"table {table_number}/row {row_index + 1}/col {col_index + 1}"}

    def _validate_table_edit_shapes(
        self,
        ir: DocxIR,
        parse_result: Any,
    ) -> list[str]:
        """Reject table row/column shape edits until XML structure edits exist."""
        errors: list[str] = []
        for edit in parse_result.edits:
            if edit.table_rows is None:
                continue

            block = ir.find_block(edit.block_id)
            if block is None or block.block_type != DfmBlockType.TABLE:
                continue

            original_rows = self.parser._parse_md_table(block.content)
            edited_rows = edit.table_rows
            if not original_rows or not edited_rows:
                continue

            original_row_count = len(original_rows)
            edited_row_count = len(edited_rows)
            if edited_row_count != original_row_count:
                errors.append(
                    f"Table {edit.block_id} row count changed "
                    f"({original_row_count} -> {edited_row_count})"
                )

            original_col_count = len(original_rows[0]) if original_rows[0] else 0
            for row_index, row in enumerate(edited_rows):
                if len(row) != original_col_count:
                    errors.append(
                        f"Table {edit.block_id} row {row_index} column count changed "
                        f"({original_col_count} -> {len(row)})"
                    )
        return errors

    @staticmethod
    def _normalize_table_rows(
        rows: list[list[str]] | None,
    ) -> list[list[str]]:
        """Normalize parsed markdown-table rows for semantic equality checks."""
        if not rows:
            return []
        return [[cell.strip() for cell in row] for row in rows]

    def _detect_unedited_block_mutations(
        self,
        original_ir: DocxIR,
        updated_ir: DocxIR,
        expected_changed_ids: set[str],
    ) -> list[str]:
        """Detect blocks that changed even though no semantic edit targeted them."""
        original_blocks = {block.id: block for block in original_ir.blocks}
        updated_blocks = {block.id: block for block in updated_ir.blocks}
        unexpected: list[str] = []

        for block_id, original_block in original_blocks.items():
            if block_id in expected_changed_ids:
                continue

            updated_block = updated_blocks.get(block_id)
            if updated_block is None:
                unexpected.append(f"Block {block_id} disappeared during write-back")
                continue

            if self._block_signature(original_block) != self._block_signature(
                updated_block
            ):
                unexpected.append(
                    f"Block {block_id} changed without an explicit edit request"
                )

        for block_id in updated_blocks.keys() - original_blocks.keys():
            if block_id not in expected_changed_ids:
                unexpected.append(
                    f"Unexpected new block {block_id} appeared during write-back"
                )

        return unexpected

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

        old_md = DocxService._normalize_markdown_for_drift(old_md)
        new_md = DocxService._normalize_markdown_for_drift(new_md)

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
        if len(lost_lines) >= 3:
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

    @staticmethod
    def _normalize_markdown_for_drift(markdown: str) -> str:
        """Normalize markdown table padding so drift checks focus on semantic loss."""
        normalized_lines: list[str] = []
        for line in markdown.splitlines():
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                raw_cells = [cell.strip() for cell in stripped.split("|")[1:-1]]
                if re.match(r"^\|[\s\-:|]+\|$", stripped):
                    normalized_lines.append(
                        "| " + " | ".join("---" for _ in raw_cells) + " |"
                    )
                else:
                    normalized_lines.append("| " + " | ".join(raw_cells) + " |")
                continue
            normalized_lines.append(
                stripped if stripped.startswith("<!--") else line.rstrip()
            )

        return "\n".join(normalized_lines)

    @staticmethod
    def _staged_docx_output_path(output_path: Path) -> Path:
        """Return a same-directory temporary DOCX path for atomic replacement."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return output_path.with_name(
            f".{output_path.stem}.{timestamp}.{os.getpid()}.tmp.docx"
        )

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

    @classmethod
    def _convert_docx_file_to_pdf(
        cls, docx_path: Path, output_path: Path
    ) -> Path | None:
        """Convert a DOCX file to PDF using LibreOffice."""
        return cls._convert_docx_file_to_format(docx_path, output_path, "pdf")

    @classmethod
    def _convert_docx_file_to_doc(
        cls, docx_path: Path, output_path: Path
    ) -> Path | None:
        """Convert a DOCX file to DOC using LibreOffice."""
        return cls._convert_docx_file_to_format(docx_path, output_path, "doc")

    @classmethod
    def _convert_docx_file_to_odt(
        cls, docx_path: Path, output_path: Path
    ) -> Path | None:
        """Convert a DOCX file to ODT using LibreOffice."""
        return cls._convert_docx_file_to_format(docx_path, output_path, "odt")

    @classmethod
    def _convert_docx_file_to_format(
        cls,
        docx_path: Path,
        output_path: Path,
        target_format: str,
    ) -> Path | None:
        """Convert a DOCX file to another office format using LibreOffice."""
        try:
            libreoffice_bin = cls._find_libreoffice_binary()
            if libreoffice_bin is None:
                logger.error(
                    "LibreOffice not installed or not discoverable for DOCX → %s",
                    target_format.upper(),
                )
                return None

            with tempfile.TemporaryDirectory() as tmp_dir_name:
                tmp_dir = Path(tmp_dir_name)
                result = subprocess.run(
                    [
                        libreoffice_bin,
                        "--headless",
                        "--convert-to",
                        target_format,
                        str(docx_path),
                        "--outdir",
                        str(tmp_dir),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                if result.returncode != 0:
                    error_detail = (
                        result.stderr
                        or result.stdout
                        or f"exit code {result.returncode}"
                    )
                    logger.error(
                        "LibreOffice DOCX→%s failed: %s",
                        target_format.upper(),
                        error_detail,
                    )
                    return None

                converted_path = tmp_dir / f"{docx_path.stem}.{target_format}"
                if not converted_path.exists():
                    logger.error(
                        "Converted %s not found: %s",
                        target_format.upper(),
                        converted_path,
                    )
                    return None

                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(converted_path, output_path)
                return output_path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.exception(
                "DOCX → %s conversion failed for %s",
                target_format.upper(),
                docx_path,
            )
            return None

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
