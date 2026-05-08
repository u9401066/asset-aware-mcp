"""
Application Layer - DFM Integrity Checker

Validates consistency at every stage of the docx ↔ DFM pipeline
and auto-repairs common issues.

Checks:
1. Post-ingest: rendered DFM/MD re-parses back to same block count
2. Split-format consistency: MD markers match YAML block keys
3. Pre-save: edit block IDs exist, table columns match, protected blocks untouched
4. Post-save: round-trip fidelity via DocxValidator
5. Auto-repair: fix broken markers, table column mismatch, orphan blocks
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml  # type: ignore[import-untyped]

from src.infrastructure.dfm_parser import DfmParser, DfmParseResult

if TYPE_CHECKING:
    from pathlib import Path

    from src.domain.docx_entities import DocxIR

logger = logging.getLogger(__name__)

# Marker regex (same as in dfm_parser.py)
_SPLIT_MARKER_RE = re.compile(r"<!--\s*@(\S+)\s*-->")


@dataclass
class IntegrityIssue:
    """A single integrity issue found during checking."""

    severity: str  # "error", "warning", "info"
    stage: str  # "ingest", "pre_save", "post_save", "split_consistency"
    message: str
    auto_fixed: bool = False
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrityReport:
    """Complete integrity check report."""

    passed: bool = True
    issues: list[IntegrityIssue] = field(default_factory=list)
    auto_fixes_applied: int = 0

    def add(self, issue: IntegrityIssue) -> None:
        self.issues.append(issue)
        if issue.severity == "error" and not issue.auto_fixed:
            self.passed = False
        if issue.auto_fixed:
            self.auto_fixes_applied += 1

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error" and not i.auto_fixed)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def to_summary(self) -> str:
        """One-line summary."""
        if self.passed and not self.issues:
            return "integrity_check: PASS (no issues)"
        parts = []
        if self.error_count:
            parts.append(f"{self.error_count} errors")
        if self.warning_count:
            parts.append(f"{self.warning_count} warnings")
        if self.auto_fixes_applied:
            parts.append(f"{self.auto_fixes_applied} auto-fixed")
        status = "FAIL" if not self.passed else "PASS"
        return f"integrity_check: {status} ({', '.join(parts)})"

    def to_markdown(self) -> str:
        """Detailed Markdown report."""
        lines = []
        if self.passed:
            lines.append("### Integrity Check: PASS")
        else:
            lines.append("### Integrity Check: FAIL")

        if not self.issues:
            lines.append("No issues found.")
            return "\n".join(lines)

        lines.append("")
        lines.append("| # | Severity | Stage | Message | Auto-fixed |")
        lines.append("|---|----------|-------|---------|------------|")
        for idx, issue in enumerate(self.issues, 1):
            icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(
                issue.severity, ""
            )
            fixed = "✅" if issue.auto_fixed else ""
            lines.append(
                f"| {idx} | {icon} {issue.severity} | {issue.stage} "
                f"| {issue.message} | {fixed} |"
            )

        if self.auto_fixes_applied:
            lines.append("")
            lines.append(f"**{self.auto_fixes_applied} issues auto-repaired.**")

        return "\n".join(lines)


class DfmIntegrityChecker:
    """
    Validates and auto-repairs DFM artifacts at every pipeline stage.

    Usage:
        checker = DfmIntegrityChecker()

        # After ingest
        report = checker.check_ingest(ir, md_text, yaml_text)

        # Before save
        report = checker.check_pre_save(ir, parse_result)
        md_text, yaml_text = checker.auto_repair_split(md_text, yaml_text, ir)

        # After save
        report = checker.check_post_save(
            original_path,
            output_path,
            content_edits_expected=True,
            expected_text_diff_locations={"paragraph 1"},
            expected_table_diff_locations=set(),
        )
    """

    def __init__(self) -> None:
        self._parser = DfmParser()

    # ========================================================================
    # 1. Post-ingest verification
    # ========================================================================

    def check_ingest(
        self,
        ir: DocxIR,
        md_text: str,
        yaml_text: str,
    ) -> IntegrityReport:
        """
        Verify that ingest output is internally consistent.

        Checks:
        - MD markers count matches IR block count
        - YAML block keys match IR block IDs
        - Re-parsing MD+YAML yields same block count
        - All editable blocks have non-empty content
        - All protected blocks preserved
        """
        report = IntegrityReport()
        ir_block_ids = {b.id for b in ir.blocks}
        ir_editable_ids = {b.id for b in ir.blocks if b.is_editable}

        # --- Check MD markers ---
        md_marker_ids = set(_SPLIT_MARKER_RE.findall(md_text))

        missing_in_md = ir_block_ids - md_marker_ids
        # Some blocks (e.g. BOOKMARK) may not render in MD — filter
        bookmark_ids = {b.id for b in ir.blocks if b.block_type.value == "bookmark"}
        truly_missing = missing_in_md - bookmark_ids

        if truly_missing:
            report.add(
                IntegrityIssue(
                    severity="warning",
                    stage="ingest",
                    message=f"{len(truly_missing)} IR blocks missing from content.md",
                    details={"missing_ids": sorted(truly_missing)[:10]},
                )
            )

        extra_in_md = md_marker_ids - ir_block_ids
        if extra_in_md:
            report.add(
                IntegrityIssue(
                    severity="error",
                    stage="ingest",
                    message=f"{len(extra_in_md)} orphan markers in content.md (not in IR)",
                    details={"orphan_ids": sorted(extra_in_md)[:10]},
                )
            )

        # --- Check YAML blocks ---
        try:
            fmt = yaml.safe_load(yaml_text)
            if isinstance(fmt, dict):
                yaml_block_ids = set(fmt.get("blocks", {}).keys())
                missing_in_yaml = ir_block_ids - yaml_block_ids
                if missing_in_yaml:
                    report.add(
                        IntegrityIssue(
                            severity="error",
                            stage="ingest",
                            message=f"{len(missing_in_yaml)} IR blocks missing from format.yaml",
                            details={"missing_ids": sorted(missing_in_yaml)[:10]},
                        )
                    )
                extra_in_yaml = yaml_block_ids - ir_block_ids
                if extra_in_yaml:
                    report.add(
                        IntegrityIssue(
                            severity="error",
                            stage="ingest",
                            message=f"{len(extra_in_yaml)} orphan blocks in format.yaml",
                            details={"orphan_ids": sorted(extra_in_yaml)[:10]},
                        )
                    )
        except yaml.YAMLError as e:
            report.add(
                IntegrityIssue(
                    severity="error",
                    stage="ingest",
                    message=f"format.yaml is invalid YAML: {e}",
                )
            )

        # --- Re-parse and compare ---
        try:
            parse_result = self._parser.parse_split(md_text, yaml_text)
            parsed_ids = {e.block_id for e in parse_result.edits}
            reparsed_missing = ir_editable_ids - parsed_ids - bookmark_ids
            if reparsed_missing:
                report.add(
                    IntegrityIssue(
                        severity="warning",
                        stage="ingest",
                        message=(
                            f"{len(reparsed_missing)} editable blocks not recovered "
                            f"on re-parse"
                        ),
                        details={"missing_ids": sorted(reparsed_missing)[:10]},
                    )
                )
            if parse_result.errors:
                for err in parse_result.errors:
                    report.add(
                        IntegrityIssue(
                            severity="warning",
                            stage="ingest",
                            message=f"Parse warning: {err}",
                        )
                    )
        except Exception as e:
            report.add(
                IntegrityIssue(
                    severity="error",
                    stage="ingest",
                    message=f"Re-parse failed: {e}",
                )
            )

        # --- Empty editable blocks ---
        empty_editable = [
            b.id for b in ir.blocks if b.is_editable and not b.plain_text.strip()
        ]
        if empty_editable:
            report.add(
                IntegrityIssue(
                    severity="info",
                    stage="ingest",
                    message=f"{len(empty_editable)} editable blocks are empty",
                    details={"empty_ids": empty_editable[:10]},
                )
            )

        return report

    # ========================================================================
    # 2. Split-format consistency
    # ========================================================================

    def check_split_consistency(self, md_text: str, yaml_text: str) -> IntegrityReport:
        """
        Check that content.md and format.yaml are mutually consistent.

        Verifies:
        - Every MD marker has a matching YAML block entry
        - doc_id matches between MD frontmatter and YAML
        - YAML is valid and parseable
        """
        report = IntegrityReport()

        md_markers = _SPLIT_MARKER_RE.findall(md_text)
        md_marker_ids = set(md_markers)

        # Detect duplicate marker IDs (high-risk: can misapply edits)
        marker_counts = Counter(md_markers)
        duplicate_ids = [
            marker_id for marker_id, count in marker_counts.items() if count > 1
        ]
        if duplicate_ids:
            report.add(
                IntegrityIssue(
                    severity="error",
                    stage="split_consistency",
                    message=f"{len(duplicate_ids)} duplicate MD marker IDs found",
                    details={"ids": sorted(duplicate_ids)[:10]},
                )
            )

        try:
            fmt = yaml.safe_load(yaml_text)
        except yaml.YAMLError as e:
            report.add(
                IntegrityIssue(
                    severity="error",
                    stage="split_consistency",
                    message=f"format.yaml is invalid: {e}",
                )
            )
            return report

        if not isinstance(fmt, dict):
            report.add(
                IntegrityIssue(
                    severity="error",
                    stage="split_consistency",
                    message="format.yaml root is not a mapping",
                )
            )
            return report

        yaml_block_ids = set(fmt.get("blocks", {}).keys())

        # MD markers without YAML metadata
        md_only = md_marker_ids - yaml_block_ids
        if md_only:
            report.add(
                IntegrityIssue(
                    severity="warning",
                    stage="split_consistency",
                    message=f"{len(md_only)} MD markers have no format.yaml entry",
                    details={"ids": sorted(md_only)[:10]},
                )
            )

        # YAML blocks without MD markers (could be bookmarks — just warn)
        yaml_only = yaml_block_ids - md_marker_ids
        if yaml_only:
            report.add(
                IntegrityIssue(
                    severity="info",
                    stage="split_consistency",
                    message=f"{len(yaml_only)} format.yaml blocks have no MD marker",
                    details={"ids": sorted(yaml_only)[:10]},
                )
            )

        # Cross-check doc_id
        yaml_doc_id = fmt.get("doc_id", "")
        md_doc_id = ""
        fm_match = re.search(r"^---\s*\n(.*?)\n---", md_text, re.DOTALL)
        if fm_match:
            try:
                fm_data = yaml.safe_load(fm_match.group(1))
                md_doc_id = fm_data.get("doc_id", "") if fm_data else ""
            except yaml.YAMLError:
                pass

        if yaml_doc_id and md_doc_id and yaml_doc_id != md_doc_id:
            report.add(
                IntegrityIssue(
                    severity="error",
                    stage="split_consistency",
                    message=(f"doc_id mismatch: MD={md_doc_id}, YAML={yaml_doc_id}"),
                )
            )

        return report

    # ========================================================================
    # 3. Pre-save validation
    # ========================================================================

    def check_pre_save(
        self, ir: DocxIR, parse_result: DfmParseResult
    ) -> IntegrityReport:
        """
        Validate edits before applying them to the IR.

        Checks:
        - All edit block_ids exist in IR
        - No edits target protected blocks
        - Table edits have matching column count
        - No duplicate block_ids in edits
        """
        report = IntegrityReport()
        ir_block_map = {b.id: b for b in ir.blocks}
        seen_ids: set[str] = set()

        for edit in parse_result.edits:
            # Duplicate check
            if edit.block_id in seen_ids:
                report.add(
                    IntegrityIssue(
                        severity="warning",
                        stage="pre_save",
                        message=f"Duplicate edit for block {edit.block_id}",
                    )
                )
            seen_ids.add(edit.block_id)

            # Existence check
            block = ir_block_map.get(edit.block_id)
            if block is None:
                report.add(
                    IntegrityIssue(
                        severity="error",
                        stage="pre_save",
                        message=f"Block {edit.block_id} not found in IR",
                    )
                )
                continue

            # Protected block check: only warn if user actually changed content.
            if block.is_protected and self._protected_block_changed(block, edit):
                report.add(
                    IntegrityIssue(
                        severity="warning",
                        stage="pre_save",
                        message=(
                            f"Edit targets protected block {edit.block_id} "
                            f"(type={block.block_type.value}) — will be skipped"
                        ),
                    )
                )

            # Table column count check
            if edit.table_rows and block.content:
                orig_rows = self._parser._parse_md_table(block.content)
                if orig_rows and edit.table_rows:
                    orig_cols = len(orig_rows[0]) if orig_rows else 0
                    edit_cols = len(edit.table_rows[0]) if edit.table_rows else 0
                    if orig_cols != edit_cols:
                        report.add(
                            IntegrityIssue(
                                severity="warning",
                                stage="pre_save",
                                message=(
                                    f"Table {edit.block_id}: column count changed "
                                    f"({orig_cols} → {edit_cols})"
                                ),
                                details={
                                    "block_id": edit.block_id,
                                    "original_cols": orig_cols,
                                    "edit_cols": edit_cols,
                                },
                            )
                        )

        # Check for missing edits (editable blocks not in parse result)
        parsed_ids = {e.block_id for e in parse_result.edits}
        editable_ids = {b.id for b in ir.blocks if b.is_editable}
        missing_edits = editable_ids - parsed_ids
        if missing_edits:
            report.add(
                IntegrityIssue(
                    severity="info",
                    stage="pre_save",
                    message=(
                        f"{len(missing_edits)} editable blocks not in edit set "
                        f"(content unchanged)"
                    ),
                )
            )

        # Report parse errors
        for err in parse_result.errors:
            report.add(
                IntegrityIssue(
                    severity="warning",
                    stage="pre_save",
                    message=f"Parse issue: {err}",
                )
            )

        return report

    @staticmethod
    def _protected_block_changed(block: Any, edit: Any) -> bool:
        """Return True only when a protected block's visible content was changed."""
        current_content = (
            block.plain_text if getattr(block, "runs", None) else block.content
        ) or ""
        edited_content = (edit.new_content or "").strip()
        return bool(edited_content) and edited_content != current_content.strip()

    # ========================================================================
    # 4. Post-save validation
    # ========================================================================

    def check_post_save(
        self,
        original_path: Path,
        output_path: Path,
        *,
        content_edits_expected: bool = False,
        expected_text_diffs: int | None = None,
        expected_table_diffs: int | None = None,
        expected_text_diff_locations: set[str] | None = None,
        expected_table_diff_locations: set[str] | None = None,
        revision_markup_expected: bool = False,
    ) -> IntegrityReport:
        """
        Run round-trip validation after saving docx.

        Uses DocxValidator to compare original vs rebuilt.

        When content edits are expected, text/table differences are the intended
        user changes and should not fail the post-save guard by themselves.
        Structural, media, style, and non-revision formatting regressions still
        fail closed.
        """
        report = IntegrityReport()

        if not output_path.exists():
            report.add(
                IntegrityIssue(
                    severity="error",
                    stage="post_save",
                    message=f"Output file not found: {output_path}",
                )
            )
            return report

        try:
            from src.infrastructure.docx_validator import DocxValidator

            validator = DocxValidator()
            val_report = validator.validate(original_path, output_path)

            if content_edits_expected:
                blocking_structure = [
                    diff
                    for diff in val_report.structure_diffs
                    if diff.category != "table_nonempty_cells"
                ]
                allowed_format_attributes = (
                    {"run_count"} if revision_markup_expected else set()
                )
                blocking_format = [
                    diff
                    for diff in val_report.format_diffs
                    if diff.attribute not in allowed_format_attributes
                    or (
                        diff.attribute == "run_count"
                        and not (
                            self._diff_location_allowed(
                                getattr(diff, "location", ""),
                                expected_text_diff_locations,
                            )
                            or self._diff_location_allowed(
                                getattr(diff, "location", ""),
                                expected_table_diff_locations,
                            )
                        )
                    )
                ]
                blocking_text, missing_text = self._content_diff_scope_issues(
                    val_report.text_diffs,
                    expected_count=expected_text_diffs,
                    expected_locations=expected_text_diff_locations,
                )
                blocking_table, missing_table = self._content_diff_scope_issues(
                    val_report.table_diffs,
                    expected_count=expected_table_diffs,
                    expected_locations=expected_table_diff_locations,
                )
                if (
                    val_report.errors
                    or blocking_structure
                    or blocking_text
                    or blocking_table
                    or missing_text
                    or missing_table
                    or blocking_format
                    or val_report.media_diffs
                    or val_report.style_diffs
                ):
                    report.add(
                        IntegrityIssue(
                            severity="error",
                            stage="post_save",
                            message=(
                                "Post-save non-content fidelity degraded after "
                                "applying expected edits"
                            ),
                            details={
                                "fidelity_score": round(
                                    val_report.fidelity_score * 100, 1
                                ),
                                "structure_diffs": len(blocking_structure),
                                "text_diffs": len(blocking_text),
                                "table_diffs": len(blocking_table),
                                "missing_text_diffs": len(missing_text),
                                "missing_table_diffs": len(missing_table),
                                "format_diffs": len(blocking_format),
                                "media_diffs": len(val_report.media_diffs),
                                "style_diffs": len(val_report.style_diffs),
                                "errors": len(val_report.errors),
                            },
                        )
                    )
                else:
                    report.add(
                        IntegrityIssue(
                            severity="info",
                            stage="post_save",
                            message=(
                                "Post-save non-content fidelity passed with "
                                "expected content edits"
                            ),
                            details={
                                "fidelity_score": round(
                                    val_report.fidelity_score * 100, 1
                                ),
                                "text_diffs": len(val_report.text_diffs),
                                "table_diffs": len(val_report.table_diffs),
                                "format_diffs": len(val_report.format_diffs),
                            },
                        )
                    )
                return report

            score = val_report.fidelity_score
            if score >= 0.95:
                report.add(
                    IntegrityIssue(
                        severity="info",
                        stage="post_save",
                        message=f"Round-trip fidelity: {score * 100:.1f}% (excellent)",
                    )
                )
            elif score >= 0.80:
                report.add(
                    IntegrityIssue(
                        severity="warning",
                        stage="post_save",
                        message=f"Round-trip fidelity: {score * 100:.1f}% (good, minor diffs)",
                        details={
                            "text_diffs": len(val_report.text_diffs),
                            "format_diffs": len(val_report.format_diffs),
                            "table_diffs": len(val_report.table_diffs),
                        },
                    )
                )
            else:
                report.add(
                    IntegrityIssue(
                        severity="error",
                        stage="post_save",
                        message=f"Round-trip fidelity: {score * 100:.1f}% (degraded)",
                        details={
                            "text_diffs": len(val_report.text_diffs),
                            "format_diffs": len(val_report.format_diffs),
                            "table_diffs": len(val_report.table_diffs),
                        },
                    )
                )

            if val_report.errors:
                for err in val_report.errors:
                    report.add(
                        IntegrityIssue(
                            severity="error",
                            stage="post_save",
                            message=f"Validator error: {err}",
                        )
                    )

        except Exception as e:
            report.add(
                IntegrityIssue(
                    severity="error",
                    stage="post_save",
                    message=f"Validation failed: {e}",
                )
            )

        return report

    @staticmethod
    def _content_diff_scope_issues(
        diffs: list[Any],
        *,
        expected_count: int | None,
        expected_locations: set[str] | None,
    ) -> tuple[list[Any], set[str]]:
        """Return unexpected diffs plus expected locations that did not appear."""
        if expected_locations is not None:
            actual_locations = {
                getattr(diff, "location", "") for diff in diffs if diff is not None
            }
            unexpected = [
                diff
                for diff in diffs
                if getattr(diff, "location", "") not in expected_locations
            ]
            missing = expected_locations - actual_locations
            return unexpected, missing

        if expected_count is not None and len(diffs) > expected_count:
            return diffs[expected_count:], set()

        if expected_count is None and diffs:
            return diffs, set()

        return [], set()

    @staticmethod
    def _diff_location_allowed(
        location: str,
        expected_locations: set[str] | None,
    ) -> bool:
        return expected_locations is not None and location in expected_locations

    # ========================================================================
    # 5. Auto-repair: split format
    # ========================================================================

    def auto_repair_split(
        self,
        md_text: str,
        yaml_text: str,
        ir: DocxIR,
    ) -> tuple[str, str, IntegrityReport]:
        """
        Auto-repair common issues in content.md + format.yaml.

        Repairs:
        - Missing YAML block entries → add from IR
        - Orphan MD markers → remove from MD
        - Table column mismatch → pad/truncate to match IR
        - doc_id mismatch → fix to match IR

        Returns:
            (repaired_md, repaired_yaml, report)
        """
        report = IntegrityReport()
        ir_block_map = {b.id: b for b in ir.blocks}
        ir_block_ids = set(ir_block_map.keys())

        # --- Parse YAML ---
        try:
            fmt = yaml.safe_load(yaml_text)
            if not isinstance(fmt, dict):
                fmt = {}
        except yaml.YAMLError:
            report.add(
                IntegrityIssue(
                    severity="error",
                    stage="auto_repair",
                    message="format.yaml is unparseable — cannot auto-repair",
                )
            )
            return md_text, yaml_text, report

        yaml_blocks: dict[str, dict[str, Any]] = fmt.get("blocks", {})
        yaml_block_ids = set(yaml_blocks.keys())

        # --- Fix doc_id ---
        if fmt.get("doc_id") != ir.doc_id:
            fmt["doc_id"] = ir.doc_id
            report.add(
                IntegrityIssue(
                    severity="warning",
                    stage="auto_repair",
                    message=f"Fixed doc_id in format.yaml → {ir.doc_id}",
                    auto_fixed=True,
                )
            )

        # --- Add missing YAML block entries ---
        missing_in_yaml = ir_block_ids - yaml_block_ids
        if missing_in_yaml:
            from src.infrastructure.dfm_renderer import DfmRenderer

            renderer = DfmRenderer()
            for block_id in missing_in_yaml:
                block = ir_block_map[block_id]
                meta = renderer._render_block_meta(block)
                if meta is not None:
                    yaml_blocks[block_id] = meta
            fmt["blocks"] = yaml_blocks
            report.add(
                IntegrityIssue(
                    severity="warning",
                    stage="auto_repair",
                    message=f"Added {len(missing_in_yaml)} missing blocks to format.yaml",
                    auto_fixed=True,
                )
            )

        # --- Remove orphan YAML entries ---
        extra_in_yaml = yaml_block_ids - ir_block_ids
        if extra_in_yaml:
            for oid in extra_in_yaml:
                yaml_blocks.pop(oid, None)
            fmt["blocks"] = yaml_blocks
            report.add(
                IntegrityIssue(
                    severity="warning",
                    stage="auto_repair",
                    message=f"Removed {len(extra_in_yaml)} orphan blocks from format.yaml",
                    auto_fixed=True,
                )
            )

        # --- Remove orphan MD markers ---
        md_marker_ids = set(_SPLIT_MARKER_RE.findall(md_text))
        orphan_md = md_marker_ids - ir_block_ids
        if orphan_md:
            lines = md_text.split("\n")
            cleaned_lines = []
            skip_until_next_marker = False
            for line in lines:
                m = _SPLIT_MARKER_RE.match(line.strip())
                if m and m.group(1) in orphan_md:
                    skip_until_next_marker = True
                    continue
                if skip_until_next_marker:
                    if _SPLIT_MARKER_RE.match(line.strip()):
                        skip_until_next_marker = False
                        cleaned_lines.append(line)
                    # else skip (content of orphan block)
                    continue
                cleaned_lines.append(line)
            md_text = "\n".join(cleaned_lines)
            report.add(
                IntegrityIssue(
                    severity="warning",
                    stage="auto_repair",
                    message=f"Removed {len(orphan_md)} orphan markers from content.md",
                    auto_fixed=True,
                )
            )

        # --- Rebuild YAML text ---
        repaired_yaml = yaml.dump(
            fmt,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        return md_text, repaired_yaml, report

    # ========================================================================
    # 6. Auto-repair: table column mismatch
    # ========================================================================

    def auto_repair_table_edit(
        self,
        ir_block_content: str,
        edit_table_rows: list[list[str]],
    ) -> tuple[list[list[str]], IntegrityReport]:
        """
        Auto-repair table edits where column count doesn't match original.

        Strategy:
        - Extra columns → truncate to original width
        - Missing columns → pad with empty strings

        Returns:
            (repaired_rows, report)
        """
        report = IntegrityReport()

        orig_rows = self._parser._parse_md_table(ir_block_content)
        if not orig_rows or not edit_table_rows:
            return edit_table_rows, report

        orig_cols = len(orig_rows[0])
        edit_cols = len(edit_table_rows[0]) if edit_table_rows else 0

        if orig_cols == edit_cols:
            return edit_table_rows, report

        repaired: list[list[str]] = []
        for row in edit_table_rows:
            if len(row) > orig_cols:
                repaired.append(row[:orig_cols])
            elif len(row) < orig_cols:
                repaired.append(row + [""] * (orig_cols - len(row)))
            else:
                repaired.append(row)

        action = "truncated" if edit_cols > orig_cols else "padded"
        report.add(
            IntegrityIssue(
                severity="warning",
                stage="auto_repair",
                message=(
                    f"Table column mismatch ({edit_cols} → {orig_cols}): "
                    f"rows {action} to match original"
                ),
                auto_fixed=True,
            )
        )

        return repaired, report
