"""
Infrastructure Layer - Docx Round-Trip Validator

Programmatic comparison of two .docx files to verify round-trip fidelity.
Agent 無法直接看到 docx 渲染結果，此驗證器提供結構化的比對報告，
讓 AI agent 可以判斷 docx → DFM → 編輯 → docx 是否正確保留了內容。

比對維度：
1. 結構 (Structure): 段落數、表格數、圖片數
2. 文字 (Text): 逐段純文字比對
3. 格式 (Formatting): bold/italic/font/size/color 抽樣
4. 表格 (Table): 行列數 + 儲存格內容
5. 媒體 (Media): 圖片 hash
6. 樣式 (Styles): 段落樣式名稱
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar
from zipfile import ZipFile

from lxml import etree

logger = logging.getLogger(__name__)

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


@dataclass
class TextDiff:
    """A single text difference between two paragraphs."""

    index: int
    location: str  # e.g. "paragraph 3", "table 1/row 2/col 1"
    original: str
    rebuilt: str


@dataclass
class FormatDiff:
    """A formatting difference."""

    index: int
    location: str
    attribute: str  # bold, italic, font_name, font_size, color
    original: str
    rebuilt: str


@dataclass
class StructureDiff:
    """A structural difference."""

    category: str
    original_count: int
    rebuilt_count: int


@dataclass
class MediaDiff:
    """A media (image) difference."""

    filename: str
    status: str  # "missing", "added", "changed"
    original_hash: str = ""
    rebuilt_hash: str = ""


@dataclass
class ValidationReport:
    """Complete round-trip validation report."""

    original_path: str = ""
    rebuilt_path: str = ""

    # Per-category scores (0.0 ~ 1.0)
    structure_score: float = 0.0
    text_score: float = 0.0
    format_score: float = 0.0
    table_score: float = 0.0
    media_score: float = 0.0
    style_score: float = 0.0

    # Overall fidelity (weighted average)
    fidelity_score: float = 0.0

    # Diff lists
    structure_diffs: list[StructureDiff] = field(default_factory=list)
    text_diffs: list[TextDiff] = field(default_factory=list)
    format_diffs: list[FormatDiff] = field(default_factory=list)
    table_diffs: list[TextDiff] = field(default_factory=list)
    media_diffs: list[MediaDiff] = field(default_factory=list)
    style_diffs: list[TextDiff] = field(default_factory=list)

    # File-level stats
    original_file_size: int = 0
    rebuilt_file_size: int = 0
    original_sha256: str = ""
    rebuilt_sha256: str = ""
    binary_identical: bool = False
    zip_entry_diffs: list[str] = field(default_factory=list)

    # Summary stats
    original_stats: dict[str, int] = field(default_factory=dict)
    rebuilt_stats: dict[str, int] = field(default_factory=dict)

    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "original_path": self.original_path,
            "rebuilt_path": self.rebuilt_path,
            "binary_identical": self.binary_identical,
            "original_file_size": self.original_file_size,
            "rebuilt_file_size": self.rebuilt_file_size,
            "file_size_diff": self.rebuilt_file_size - self.original_file_size,
            "original_sha256": self.original_sha256,
            "rebuilt_sha256": self.rebuilt_sha256,
            "fidelity_score": round(self.fidelity_score * 100, 1),
            "scores": {
                "structure": round(self.structure_score * 100, 1),
                "text": round(self.text_score * 100, 1),
                "format": round(self.format_score * 100, 1),
                "table": round(self.table_score * 100, 1),
                "media": round(self.media_score * 100, 1),
                "style": round(self.style_score * 100, 1),
            },
            "original_stats": self.original_stats,
            "rebuilt_stats": self.rebuilt_stats,
            "structure_diffs": [
                {
                    "category": d.category,
                    "original": d.original_count,
                    "rebuilt": d.rebuilt_count,
                }
                for d in self.structure_diffs
            ],
            "text_diffs": [
                {
                    "index": d.index,
                    "location": d.location,
                    "original": d.original[:100],
                    "rebuilt": d.rebuilt[:100],
                }
                for d in self.text_diffs[:20]
            ],
            "format_diffs": [
                {
                    "index": d.index,
                    "location": d.location,
                    "attribute": d.attribute,
                    "original": d.original,
                    "rebuilt": d.rebuilt,
                }
                for d in self.format_diffs[:20]
            ],
            "table_diffs": [
                {
                    "index": d.index,
                    "location": d.location,
                    "original": d.original[:80],
                    "rebuilt": d.rebuilt[:80],
                }
                for d in self.table_diffs[:20]
            ],
            "media_diffs": [
                {
                    "filename": d.filename,
                    "status": d.status,
                }
                for d in self.media_diffs
            ],
            "style_diffs": [
                {
                    "index": d.index,
                    "location": d.location,
                    "original": d.original,
                    "rebuilt": d.rebuilt,
                }
                for d in self.style_diffs[:20]
            ],
            "errors": self.errors,
        }

    def to_markdown(self) -> str:
        """Render report as human/agent-readable markdown."""
        lines: list[str] = []
        pct = round(self.fidelity_score * 100, 1)

        # Header with emoji grade
        if pct >= 95:
            grade = "🟢 EXCELLENT"
        elif pct >= 80:
            grade = "🟡 GOOD"
        elif pct >= 60:
            grade = "🟠 FAIR"
        else:
            grade = "🔴 POOR"

        lines.append(f"## Docx Round-Trip Validation: {grade} ({pct}%)")
        lines.append("")

        # File-level comparison
        lines.append("### 檔案層級比對")
        if self.binary_identical:
            lines.append("✅ **二進位完全相同** — 檔案未被改動")
        else:
            size_diff = self.rebuilt_file_size - self.original_file_size
            sign = "+" if size_diff > 0 else ""
            lines.append("| 指標 | 原始 | 重建 |")
            lines.append("|------|------|------|")
            lines.append(
                f"| 檔案大小 | {self.original_file_size:,} bytes "
                f"| {self.rebuilt_file_size:,} bytes ({sign}{size_diff:,}) |"
            )
            lines.append(
                f"| SHA-256 | `{self.original_sha256[:16]}…` "
                f"| `{self.rebuilt_sha256[:16]}…` |"
            )
            if self.zip_entry_diffs:
                lines.append("")
                lines.append(f"**ZIP 內容差異** ({len(self.zip_entry_diffs)} 項):")
                lines.extend(f"  - {d}" for d in self.zip_entry_diffs[:15])
        lines.append("")

        # Score breakdown
        lines.append("| 維度 | 分數 |")
        lines.append("|------|------|")
        for name, score in [
            ("結構 (Structure)", self.structure_score),
            ("文字 (Text)", self.text_score),
            ("格式 (Formatting)", self.format_score),
            ("表格 (Table)", self.table_score),
            ("媒體 (Media)", self.media_score),
            ("樣式 (Style)", self.style_score),
        ]:
            s = round(score * 100, 1)
            bar = "█" * int(s / 10) + "░" * (10 - int(s / 10))
            lines.append(f"| {name} | {bar} {s}% |")

        # Stats comparison
        lines.append("")
        lines.append("### 文件統計")
        lines.append("| 指標 | 原始 | 重建 |")
        lines.append("|------|------|------|")
        all_keys = sorted(
            set(list(self.original_stats.keys()) + list(self.rebuilt_stats.keys()))
        )
        for key in all_keys:
            orig = self.original_stats.get(key, 0)
            rebuilt = self.rebuilt_stats.get(key, 0)
            marker = " ✅" if orig == rebuilt else " ❌"
            lines.append(f"| {key} | {orig} | {rebuilt}{marker} |")

        # Diffs
        if self.text_diffs:
            lines.append("")
            lines.append(f"### 文字差異 ({len(self.text_diffs)} 處)")
            for d in self.text_diffs[:10]:
                lines.append(f"- **{d.location}**:")
                lines.append(f"  - 原始: `{d.original[:80]}`")
                lines.append(f"  - 重建: `{d.rebuilt[:80]}`")

        if self.format_diffs:
            lines.append("")
            lines.append(f"### 格式差異 ({len(self.format_diffs)} 處)")
            lines.extend(
                f"- **{d.location}** [{d.attribute}]: `{d.original}` → `{d.rebuilt}`"
                for d in self.format_diffs[:10]
            )

        if self.table_diffs:
            lines.append("")
            lines.append(f"### 表格差異 ({len(self.table_diffs)} 處)")
            lines.extend(
                f"- **{d.location}**: `{d.original[:60]}` → `{d.rebuilt[:60]}`"
                for d in self.table_diffs[:10]
            )

        if self.media_diffs:
            lines.append("")
            lines.append(f"### 媒體差異 ({len(self.media_diffs)} 處)")
            lines.extend(f"- `{d.filename}`: {d.status}" for d in self.media_diffs)

        if self.style_diffs:
            lines.append("")
            lines.append(f"### 樣式差異 ({len(self.style_diffs)} 處)")
            lines.extend(
                f"- **{d.location}**: `{d.original}` → `{d.rebuilt}`"
                for d in self.style_diffs[:10]
            )

        if self.errors:
            lines.append("")
            lines.append("### ⚠️ 錯誤")
            lines.extend(f"- {e}" for e in self.errors)

        return "\n".join(lines)


class DocxValidator:
    """
    Programmatic validator for docx round-trip fidelity.

    Compares two .docx files element by element and produces a
    structured ValidationReport that an AI agent can interpret.
    """

    # Weights for overall fidelity score
    WEIGHTS: ClassVar[dict[str, float]] = {
        "structure": 0.15,
        "text": 0.35,
        "format": 0.15,
        "table": 0.15,
        "media": 0.10,
        "style": 0.10,
    }

    def validate(self, original_path: Path, rebuilt_path: Path) -> ValidationReport:
        """
        Compare original and rebuilt .docx files.

        Args:
            original_path: Path to the original .docx
            rebuilt_path: Path to the rebuilt .docx

        Returns:
            ValidationReport with scores and diffs
        """
        report = ValidationReport(
            original_path=str(original_path),
            rebuilt_path=str(rebuilt_path),
        )

        if not original_path.exists():
            report.errors.append(f"Original file not found: {original_path}")
            return report
        if not rebuilt_path.exists():
            report.errors.append(f"Rebuilt file not found: {rebuilt_path}")
            return report

        # File-level comparison
        self._compare_file_level(original_path, rebuilt_path, report)

        try:
            orig_data = self._extract_docx_data(original_path)
            rebuilt_data = self._extract_docx_data(rebuilt_path)
        except Exception as e:
            report.errors.append(f"Failed to parse docx: {e}")
            return report

        # Compare each dimension
        self._compare_structure(orig_data, rebuilt_data, report)
        self._compare_text(orig_data, rebuilt_data, report)
        self._compare_formatting(orig_data, rebuilt_data, report)
        self._compare_tables(orig_data, rebuilt_data, report)
        self._compare_media(orig_data, rebuilt_data, report)
        self._compare_styles(orig_data, rebuilt_data, report)

        # Compute overall fidelity
        report.fidelity_score = (
            self.WEIGHTS["structure"] * report.structure_score
            + self.WEIGHTS["text"] * report.text_score
            + self.WEIGHTS["format"] * report.format_score
            + self.WEIGHTS["table"] * report.table_score
            + self.WEIGHTS["media"] * report.media_score
            + self.WEIGHTS["style"] * report.style_score
        )

        return report

    def validate_ir_roundtrip(
        self,
        original_path: Path,
        adapter: Any,
        data_dir: Path,
    ) -> ValidationReport:
        """
        Full round-trip validation: original.docx → IR → rebuilt.docx → compare.

        This performs the complete cycle without any edits to test baseline fidelity.

        Args:
            original_path: Path to the source .docx
            adapter: DocxAdapter instance
            data_dir: Working directory for IR storage

        Returns:
            ValidationReport
        """
        from src.infrastructure.docx_adapter import DocxAdapter

        if not isinstance(adapter, DocxAdapter):
            adapter = DocxAdapter()

        # Step 1: Parse original → IR
        ir = adapter.parse_to_ir(original_path, data_dir)

        # Step 2: Rebuild docx from IR (no edits)
        rebuilt_path = data_dir / "roundtrip_output.docx"
        adapter.ir_to_docx(ir, data_dir, rebuilt_path)

        # Step 3: Compare
        return self.validate(original_path, rebuilt_path)

    # ========================================================================
    # Data extraction
    # ========================================================================

    def _extract_docx_data(self, docx_path: Path) -> dict[str, Any]:
        """Extract structured data from a .docx file for comparison."""
        data: dict[str, Any] = {
            "paragraphs": [],  # list of {text, style, runs:[{text,bold,italic,...}]}
            "tables": [],  # list of {rows: [[cell_text, ...], ...]}
            "media": {},  # filename → sha256
            "xml_parts": set(),  # which XML parts exist
        }

        with ZipFile(docx_path, "r") as zf:
            # Extract media hashes
            for name in zf.namelist():
                if name.startswith("word/media/"):
                    content = zf.read(name)
                    filename = Path(name).name
                    data["media"][filename] = hashlib.sha256(content).hexdigest()[:16]

            # Track XML parts
            for name in zf.namelist():
                if name.endswith(".xml"):
                    data["xml_parts"].add(name)

            # Parse document.xml
            if "word/document.xml" not in zf.namelist():
                return data

            doc_xml = zf.read("word/document.xml")
            tree = etree.fromstring(doc_xml)  # noqa: S320
            body = tree.find(f".//{{{NS['w']}}}body")
            if body is None:
                return data

            for element in body:
                tag = etree.QName(element.tag).localname

                if tag == "p":
                    para = self._extract_paragraph(element)
                    data["paragraphs"].append(para)
                elif tag == "tbl":
                    table = self._extract_table(element)
                    data["tables"].append(table)
                elif tag == "sdt":
                    # Structured doc tag — extract inner paragraphs/tables
                    sdt_content = element.find(f"{{{NS['w']}}}sdtContent")
                    if sdt_content is not None:
                        for child in sdt_content:
                            child_tag = etree.QName(child.tag).localname
                            if child_tag == "p":
                                data["paragraphs"].append(
                                    self._extract_paragraph(child)
                                )
                            elif child_tag == "tbl":
                                data["tables"].append(self._extract_table(child))

        return data

    def _extract_paragraph(self, p_elem: etree._Element) -> dict[str, Any]:
        """Extract paragraph data for comparison."""
        # Style
        ppr = p_elem.find(f"{{{NS['w']}}}pPr")
        style = None
        if ppr is not None:
            style_el = ppr.find(f"{{{NS['w']}}}pStyle")
            if style_el is not None:
                style = style_el.get(f"{{{NS['w']}}}val")

        # Runs with formatting
        runs = []
        for r_elem in p_elem.findall(f"{{{NS['w']}}}r"):
            text_parts = []
            for child in r_elem:
                child_tag = etree.QName(child.tag).localname
                if child_tag == "t":
                    text_parts.append(child.text or "")
                elif child_tag == "tab":
                    text_parts.append("\t")
                elif child_tag == "br":
                    br_type = child.get(f"{{{NS['w']}}}type")
                    if br_type != "page":
                        text_parts.append("\n")

            text = "".join(text_parts)
            if not text:
                continue

            rpr = r_elem.find(f"{{{NS['w']}}}rPr")
            run_data: dict[str, Any] = {"text": text}

            if rpr is not None:
                # Bold
                b = rpr.find(f"{{{NS['w']}}}b")
                if b is not None:
                    val = b.get(f"{{{NS['w']}}}val")
                    run_data["bold"] = val != "0" if val else True

                # Italic
                i = rpr.find(f"{{{NS['w']}}}i")
                if i is not None:
                    val = i.get(f"{{{NS['w']}}}val")
                    run_data["italic"] = val != "0" if val else True

                # Font
                fonts = rpr.find(f"{{{NS['w']}}}rFonts")
                if fonts is not None:
                    font_name = fonts.get(f"{{{NS['w']}}}ascii") or fonts.get(
                        f"{{{NS['w']}}}hAnsi"
                    )
                    if font_name:
                        run_data["font_name"] = font_name

                # Size (half-points)
                sz = rpr.find(f"{{{NS['w']}}}sz")
                if sz is not None:
                    val = sz.get(f"{{{NS['w']}}}val")
                    if val:
                        run_data["font_size"] = int(val)

                # Color
                color = rpr.find(f"{{{NS['w']}}}color")
                if color is not None:
                    val = color.get(f"{{{NS['w']}}}val")
                    if val and val != "auto":
                        run_data["color"] = val

                # Underline
                u = rpr.find(f"{{{NS['w']}}}u")
                if u is not None:
                    val = u.get(f"{{{NS['w']}}}val")
                    if val and val != "none":
                        run_data["underline"] = True

            runs.append(run_data)

        full_text = "".join(r["text"] for r in runs)

        return {
            "text": full_text,
            "style": style,
            "runs": runs,
        }

    def _extract_table(self, tbl_elem: etree._Element) -> dict[str, Any]:
        """Extract table data for comparison."""
        rows: list[list[str]] = []
        for tr_elem in tbl_elem.findall(f"{{{NS['w']}}}tr"):
            row_cells: list[str] = []
            for tc_elem in tr_elem.findall(f"{{{NS['w']}}}tc"):
                cell_parts = []
                for p in tc_elem.findall(f"{{{NS['w']}}}p"):
                    text_parts = [
                        t.text for t in p.findall(f".//{{{NS['w']}}}t") if t.text
                    ]
                    cell_parts.append("".join(text_parts))
                row_cells.append("\n".join(cell_parts))
            rows.append(row_cells)

        # Table style
        tbl_pr = tbl_elem.find(f"{{{NS['w']}}}tblPr")
        table_style = None
        if tbl_pr is not None:
            style_el = tbl_pr.find(f"{{{NS['w']}}}tblStyle")
            if style_el is not None:
                table_style = style_el.get(f"{{{NS['w']}}}val")

        return {
            "rows": rows,
            "row_count": len(rows),
            "col_count": max((len(r) for r in rows), default=0),
            "style": table_style,
        }

    # ========================================================================
    # Comparison methods
    # ========================================================================

    def _compare_file_level(
        self,
        original_path: Path,
        rebuilt_path: Path,
        report: ValidationReport,
    ) -> None:
        """Compare files at binary/ZIP level."""
        orig_bytes = original_path.read_bytes()
        rebuilt_bytes = rebuilt_path.read_bytes()

        report.original_file_size = len(orig_bytes)
        report.rebuilt_file_size = len(rebuilt_bytes)
        report.original_sha256 = hashlib.sha256(orig_bytes).hexdigest()
        report.rebuilt_sha256 = hashlib.sha256(rebuilt_bytes).hexdigest()
        report.binary_identical = report.original_sha256 == report.rebuilt_sha256

        if not report.binary_identical:
            # Compare ZIP entries
            try:
                with ZipFile(original_path) as oz, ZipFile(rebuilt_path) as rz:
                    orig_entries = set(oz.namelist())
                    rebuilt_entries = set(rz.namelist())

                    for name in sorted(orig_entries - rebuilt_entries):
                        report.zip_entry_diffs.append(f"🔴 removed: {name}")
                    for name in sorted(rebuilt_entries - orig_entries):
                        report.zip_entry_diffs.append(f"🟢 added: {name}")

                    # Check size changes in shared entries
                    for name in sorted(orig_entries & rebuilt_entries):
                        o_info = oz.getinfo(name)
                        r_info = rz.getinfo(name)
                        if o_info.file_size != r_info.file_size:
                            diff = r_info.file_size - o_info.file_size
                            sign = "+" if diff > 0 else ""
                            report.zip_entry_diffs.append(
                                f"🟡 changed: {name} "
                                f"({o_info.file_size:,} → {r_info.file_size:,}, "
                                f"{sign}{diff:,} bytes)"
                            )
            except Exception as e:
                report.zip_entry_diffs.append(f"⚠️ ZIP comparison error: {e}")

    def _compare_structure(
        self,
        orig: dict[str, Any],
        rebuilt: dict[str, Any],
        report: ValidationReport,
    ) -> None:
        """Compare structural element counts."""
        orig_stats = {
            "paragraphs": len(orig["paragraphs"]),
            "tables": len(orig["tables"]),
            "media_files": len(orig["media"]),
            "xml_parts": len(orig["xml_parts"]),
        }
        rebuilt_stats = {
            "paragraphs": len(rebuilt["paragraphs"]),
            "tables": len(rebuilt["tables"]),
            "media_files": len(rebuilt["media"]),
            "xml_parts": len(rebuilt["xml_parts"]),
        }

        report.original_stats = orig_stats
        report.rebuilt_stats = rebuilt_stats

        total_checks = 0
        matches = 0

        for key in orig_stats:
            total_checks += 1
            if orig_stats[key] == rebuilt_stats[key]:
                matches += 1
            else:
                report.structure_diffs.append(
                    StructureDiff(
                        category=key,
                        original_count=orig_stats[key],
                        rebuilt_count=rebuilt_stats[key],
                    )
                )

        report.structure_score = matches / total_checks if total_checks > 0 else 1.0

    def _compare_text(
        self,
        orig: dict[str, Any],
        rebuilt: dict[str, Any],
        report: ValidationReport,
    ) -> None:
        """Compare text content paragraph by paragraph."""
        orig_paras = orig["paragraphs"]
        rebuilt_paras = rebuilt["paragraphs"]

        max_len = max(len(orig_paras), len(rebuilt_paras))
        if max_len == 0:
            report.text_score = 1.0
            return

        matches = 0
        for i in range(max_len):
            orig_text = orig_paras[i]["text"] if i < len(orig_paras) else ""
            rebuilt_text = rebuilt_paras[i]["text"] if i < len(rebuilt_paras) else ""

            # Normalize whitespace for comparison
            orig_norm = _normalize_text(orig_text)
            rebuilt_norm = _normalize_text(rebuilt_text)

            if orig_norm == rebuilt_norm:
                matches += 1
            else:
                report.text_diffs.append(
                    TextDiff(
                        index=i,
                        location=f"paragraph {i + 1}",
                        original=orig_text,
                        rebuilt=rebuilt_text,
                    )
                )

        report.text_score = matches / max_len

    def _compare_formatting(
        self,
        orig: dict[str, Any],
        rebuilt: dict[str, Any],
        report: ValidationReport,
    ) -> None:
        """Compare run-level formatting."""
        orig_paras = orig["paragraphs"]
        rebuilt_paras = rebuilt["paragraphs"]

        total_checks = 0
        matches = 0

        for i in range(min(len(orig_paras), len(rebuilt_paras))):
            orig_runs = orig_paras[i]["runs"]
            rebuilt_runs = rebuilt_paras[i]["runs"]

            # Compare format attributes of first run (primary format)
            if orig_runs and rebuilt_runs:
                for attr in [
                    "bold",
                    "italic",
                    "font_name",
                    "font_size",
                    "color",
                    "underline",
                ]:
                    orig_val = orig_runs[0].get(attr)
                    rebuilt_val = rebuilt_runs[0].get(attr)
                    if orig_val is not None or rebuilt_val is not None:
                        total_checks += 1
                        if orig_val == rebuilt_val:
                            matches += 1
                        else:
                            report.format_diffs.append(
                                FormatDiff(
                                    index=i,
                                    location=f"paragraph {i + 1}",
                                    attribute=attr,
                                    original=str(orig_val),
                                    rebuilt=str(rebuilt_val),
                                )
                            )

        report.format_score = matches / total_checks if total_checks > 0 else 1.0

    def _compare_tables(
        self,
        orig: dict[str, Any],
        rebuilt: dict[str, Any],
        report: ValidationReport,
    ) -> None:
        """Compare table content cell by cell."""
        orig_tables = orig["tables"]
        rebuilt_tables = rebuilt["tables"]

        if not orig_tables and not rebuilt_tables:
            report.table_score = 1.0
            return

        total_cells = 0
        matching_cells = 0

        for t_idx in range(min(len(orig_tables), len(rebuilt_tables))):
            orig_rows = orig_tables[t_idx]["rows"]
            rebuilt_rows = rebuilt_tables[t_idx]["rows"]

            for r_idx in range(max(len(orig_rows), len(rebuilt_rows))):
                orig_row = orig_rows[r_idx] if r_idx < len(orig_rows) else []
                rebuilt_row = rebuilt_rows[r_idx] if r_idx < len(rebuilt_rows) else []

                for c_idx in range(max(len(orig_row), len(rebuilt_row))):
                    orig_cell = orig_row[c_idx] if c_idx < len(orig_row) else ""
                    rebuilt_cell = (
                        rebuilt_row[c_idx] if c_idx < len(rebuilt_row) else ""
                    )

                    total_cells += 1
                    orig_norm = _normalize_text(orig_cell)
                    rebuilt_norm = _normalize_text(rebuilt_cell)

                    if orig_norm == rebuilt_norm:
                        matching_cells += 1
                    else:
                        report.table_diffs.append(
                            TextDiff(
                                index=t_idx,
                                location=f"table {t_idx + 1}/row {r_idx + 1}/col {c_idx + 1}",
                                original=orig_cell,
                                rebuilt=rebuilt_cell,
                            )
                        )

        # Also penalize missing/extra tables
        if len(orig_tables) != len(rebuilt_tables):
            diff_tables = abs(len(orig_tables) - len(rebuilt_tables))
            # Estimate cells in missing tables
            avg_cells = (
                total_cells / min(len(orig_tables), len(rebuilt_tables))
                if min(len(orig_tables), len(rebuilt_tables)) > 0
                else 10
            )
            total_cells += int(diff_tables * avg_cells)

        report.table_score = matching_cells / total_cells if total_cells > 0 else 1.0

    def _compare_media(
        self,
        orig: dict[str, Any],
        rebuilt: dict[str, Any],
        report: ValidationReport,
    ) -> None:
        """Compare media files by hash."""
        orig_media = orig["media"]
        rebuilt_media = rebuilt["media"]

        if not orig_media and not rebuilt_media:
            report.media_score = 1.0
            return

        all_files = set(list(orig_media.keys()) + list(rebuilt_media.keys()))
        matches = 0

        for filename in all_files:
            if filename not in orig_media:
                report.media_diffs.append(MediaDiff(filename=filename, status="added"))
            elif filename not in rebuilt_media:
                report.media_diffs.append(
                    MediaDiff(filename=filename, status="missing")
                )
            elif orig_media[filename] == rebuilt_media[filename]:
                matches += 1
            else:
                report.media_diffs.append(
                    MediaDiff(
                        filename=filename,
                        status="changed",
                        original_hash=orig_media[filename],
                        rebuilt_hash=rebuilt_media[filename],
                    )
                )

        report.media_score = matches / len(all_files) if all_files else 1.0

    def _compare_styles(
        self,
        orig: dict[str, Any],
        rebuilt: dict[str, Any],
        report: ValidationReport,
    ) -> None:
        """Compare paragraph styles."""
        orig_paras = orig["paragraphs"]
        rebuilt_paras = rebuilt["paragraphs"]

        total = 0
        matches = 0

        for i in range(min(len(orig_paras), len(rebuilt_paras))):
            orig_style = orig_paras[i]["style"]
            rebuilt_style = rebuilt_paras[i]["style"]

            # Only count if at least one has a style
            if orig_style is not None or rebuilt_style is not None:
                total += 1
                if orig_style == rebuilt_style:
                    matches += 1
                else:
                    report.style_diffs.append(
                        TextDiff(
                            index=i,
                            location=f"paragraph {i + 1}",
                            original=str(orig_style),
                            rebuilt=str(rebuilt_style),
                        )
                    )

        report.style_score = matches / total if total > 0 else 1.0


def _normalize_text(text: str) -> str:
    """Normalize text for comparison (collapse whitespace, strip)."""
    return re.sub(r"\s+", " ", text).strip()
