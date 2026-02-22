"""
Infrastructure Layer - DFM Parser

Parses DFM (Docx-Flavored Markdown) text back into a modified DocxIR.
Used for the write-back path: user edits DFM → Parser extracts changes → merge with original IR.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import yaml

from src.domain.docx_entities import (
    DocxIR,
    DocxStyleInfo,
    FormatRun,
)
from src.domain.docx_value_objects import (
    DfmBlockType,
)

logger = logging.getLogger(__name__)

# ============================================================================
# Parsed edit result
# ============================================================================


@dataclass
class BlockEdit:
    """Represents a user's edit to a single block."""

    block_id: str
    new_content: str
    block_type: DfmBlockType | None = None
    # For format blocks: updated runs parsed from YAML
    updated_runs: list[FormatRun] | None = None
    # For table blocks: updated cell text parsed from markdown table
    table_rows: list[list[str]] | None = None


@dataclass
class DfmParseResult:
    """Result of parsing a DFM file."""

    doc_id: str
    source: str
    checksum: str
    style_info: DocxStyleInfo | None = None
    edits: list[BlockEdit] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ============================================================================
# Regex patterns
# ============================================================================

# Frontmatter
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

# Styles block
_STYLES_RE = re.compile(r"<!-- dfm:styles\n(.*?)\n-->", re.DOTALL)

# Simple block annotation: <!-- @b:ID [s:StyleName] -->
_SIMPLE_BLOCK_RE = re.compile(
    r"<!--\s*@b:(\S+)(?:\s+s:(\S+))?(?:\s+level:(\d+))?(?:\s+numId:(\d+))?\s*-->"
)

# Opening tag for compound blocks: <!-- dfm:TYPE @b:ID ... -->
# Matches both single-line (with -->) and start of multi-line opening tags
_COMPOUND_OPEN_RE = re.compile(r"<!--\s*dfm:(\w+)\s+@b:(\S+)\s*(.*?)-->", re.DOTALL)
# Matches just the start of a compound block (for multi-line opening tags)
_COMPOUND_START_RE = re.compile(r"<!--\s*dfm:(\w+)\s+@b:(\S+)")

# Closing tag: <!-- /dfm:TYPE -->
_COMPOUND_CLOSE_RE = re.compile(r"<!--\s*/dfm:(\w+)\s*-->")

# Bookmark: <!-- dfm:bookmark @b:ID name:"..." -->
_BOOKMARK_RE = re.compile(r'<!--\s*dfm:bookmark\s+@b:(\S+)\s+name:"([^"]*?)"\s*-->')

# Break: <!-- dfm:break @b:ID type:TYPE ... -->
_BREAK_RE = re.compile(
    r"<!--\s*dfm:break\s+@b:(\S+)(?:\s+type:(\S+))?\s*(.*?)\s*-->", re.DOTALL
)

# Heading prefix
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")

# List item prefix
_LIST_ITEM_RE = re.compile(r"^(\s*)(?:[-*]|\d+\.)\s+(.*)")


# Marker in split-format .md: <!-- @ID -->
_SPLIT_MARKER_RE = re.compile(r"<!--\s*@(\S+)\s*-->")


class DfmParser:
    """Parses DFM text and extracts block edits for merging with the original IR."""

    # ========================================================================
    # Split format: content.md + format.yaml
    # ========================================================================

    def parse_split(self, md_text: str, yaml_text: str) -> DfmParseResult:
        """
        Parse the split MD + YAML format into a DfmParseResult.

        Args:
            md_text: Clean Markdown content (content.md)
            yaml_text: Format metadata (format.yaml)

        Returns:
            DfmParseResult with extracted edits.
        """
        result = DfmParseResult(doc_id="", source="", checksum="")

        # 1. Parse format.yaml
        try:
            fmt = yaml.safe_load(yaml_text)
            if not isinstance(fmt, dict):
                result.errors.append("Invalid format.yaml: not a mapping")
                return result
            result.doc_id = fmt.get("doc_id", "")
            result.source = fmt.get("source", "")
            result.checksum = fmt.get("checksum", "")
            styles_data = fmt.get("styles")
            if styles_data:
                result.style_info = DocxStyleInfo.from_dict(styles_data)
        except yaml.YAMLError as e:
            result.errors.append(f"Invalid format.yaml: {e}")
            return result

        block_meta: dict[str, dict[str, Any]] = fmt.get("blocks", {})

        # 2. Parse frontmatter from .md (just to cross-check doc_id)
        fm_match = _FRONTMATTER_RE.search(md_text)
        if fm_match:
            try:
                fm_data = yaml.safe_load(fm_match.group(1))
                if fm_data and fm_data.get("doc_id") and not result.doc_id:
                    result.doc_id = fm_data["doc_id"]
            except yaml.YAMLError:
                pass

        # 3. Parse blocks from .md using <!-- @ID --> markers
        self._parse_split_blocks(md_text, block_meta, result)

        return result

    def _parse_split_blocks(
        self,
        md_text: str,
        block_meta: dict[str, dict[str, Any]],
        result: DfmParseResult,
    ) -> None:
        """Parse blocks from clean Markdown with @ID markers."""
        lines = md_text.split("\n")
        i = 0
        n = len(lines)
        seen_ids: dict[str, int] = {}  # block_id -> occurrence count

        # Skip frontmatter
        if i < n and lines[i].strip() == "---":
            i += 1
            while i < n and lines[i].strip() != "---":
                i += 1
            i += 1

        while i < n:
            line = lines[i]
            m = _SPLIT_MARKER_RE.match(line.strip())
            if not m:
                i += 1
                continue

            block_id = m.group(1)
            # --- Duplicate ID detection & auto-fix ---
            if block_id in seen_ids:
                seen_ids[block_id] += 1
                new_id = f"{block_id}_d{seen_ids[block_id]}"
                result.errors.append(
                    f"DUPLICATE_ID: Marker @{block_id} appears multiple times "
                    f"(occurrence #{seen_ids[block_id]}). Auto-renamed to @{new_id}. "
                    f"This may cause edits to apply to the wrong block. "
                    f"Fix content.md to use unique IDs."
                )
                logger.warning(
                    "Duplicate marker @%s (occurrence #%d) → auto-renamed to @%s",
                    block_id,
                    seen_ids[block_id],
                    new_id,
                )
                block_id = new_id
            else:
                seen_ids[block_id] = 1
            i += 1

            # Collect content until next marker or end
            content_lines: list[str] = []
            while i < n:
                if _SPLIT_MARKER_RE.match(lines[i].strip()):
                    break
                content_lines.append(lines[i])
                i += 1

            # Trim trailing blanks
            while content_lines and content_lines[-1].strip() == "":
                content_lines.pop()

            raw_content = "\n".join(content_lines).strip()

            # Look up metadata
            meta = block_meta.get(block_id, {})
            bt_str = meta.get("type", "paragraph")
            try:
                bt = DfmBlockType(bt_str)
            except ValueError:
                bt = DfmBlockType.PARAGRAPH

            edit = BlockEdit(
                block_id=block_id,
                new_content=raw_content,
                block_type=bt,
            )

            # Protected blocks: skip editing
            if bt.is_protected:
                result.edits.append(edit)
                continue

            # Type-specific parsing
            if bt == DfmBlockType.TABLE:
                edit.table_rows = self._parse_md_table(raw_content)

            elif bt == DfmBlockType.FORMAT:
                runs_data = meta.get("runs", [])
                if runs_data:
                    edit.updated_runs = [FormatRun.from_dict(r) for r in runs_data]
                edit.new_content = self._md_to_plain(raw_content)

            elif bt == DfmBlockType.HEADING:
                hm = _HEADING_RE.match(raw_content)
                if hm:
                    edit.new_content = hm.group(2)
                else:
                    edit.new_content = self._md_to_plain(raw_content)

            elif bt == DfmBlockType.LIST_ITEM:
                lm = _LIST_ITEM_RE.match(raw_content)
                if lm:
                    edit.new_content = self._md_to_plain(lm.group(2))
                else:
                    edit.new_content = self._md_to_plain(raw_content)

            elif bt == DfmBlockType.CAPTION:
                # Strip italic markers
                clean = raw_content.strip("*").strip()
                edit.new_content = clean

            else:
                # Paragraph etc.
                edit.new_content = self._md_to_plain(raw_content)

            result.edits.append(edit)

    # ========================================================================
    # Original DFM format (single file)
    # ========================================================================

    def parse(self, dfm_text: str) -> DfmParseResult:
        """
        Parse DFM text into a DfmParseResult.

        Args:
            dfm_text: The full content of a .dfm file.

        Returns:
            DfmParseResult with extracted edits and metadata.
        """
        result = DfmParseResult(doc_id="", source="", checksum="")

        # 1. Parse frontmatter
        self._parse_frontmatter(dfm_text, result)

        # 2. Parse styles
        self._parse_styles(dfm_text, result)

        # 3. Detect format mismatch: split-format content passed to DFM parser
        split_markers = _SPLIT_MARKER_RE.findall(dfm_text)
        dfm_markers = _SIMPLE_BLOCK_RE.findall(dfm_text)
        if split_markers and not dfm_markers:
            result.errors.append(
                f"FORMAT_MISMATCH: Detected {len(split_markers)} split-format "
                f"markers (<!-- @ID -->) but 0 DFM markers (<!-- @b:ID -->). "
                f"Content appears to be in split .md format, not .dfm format. "
                f"This will result in 0 edits applied — the original IR will "
                f"be rendered unchanged, effectively REVERTING all .md edits. "
                f"Use from_md=True or pass content in .dfm format."
            )
            logger.error(
                "FORMAT_MISMATCH in parse(): %d split markers, 0 DFM markers. "
                "Edits will NOT be applied. Risk of data loss!",
                len(split_markers),
            )

        # 4. Parse blocks
        self._parse_blocks(dfm_text, result)

        return result

    def apply_edits(self, ir: DocxIR, parse_result: DfmParseResult) -> DocxIR:
        """
        Apply parsed edits back to the original IR.

        Uses format merge strategy:
        - Small edit (length change < 20%): proportional redistribution across runs
        - Large edit: assign entire content to primary (first) run format

        Args:
            ir: Original DocxIR
            parse_result: Parsed DFM edits

        Returns:
            Modified DocxIR (mutated in place)
        """
        for edit in parse_result.edits:
            block = ir.find_block(edit.block_id)
            if block is None:
                parse_result.errors.append(
                    f"Block {edit.block_id} not found in IR, skipping."
                )
                continue

            if block.is_protected:
                # Protected blocks are not editable
                continue

            # Update content
            old_content = block.plain_text
            new_content = edit.new_content

            if edit.table_rows is not None:
                # Table: rebuild content from parsed rows
                block.content = self._rows_to_md_table(edit.table_rows)
            elif edit.updated_runs is not None:
                # Format block with YAML runs — check if content.md
                # text diverges from runs' text (user edited content.md)
                runs_text = "".join(r.text for r in edit.updated_runs)
                if new_content and new_content != runs_text:
                    # Content was edited in .md — merge new text with
                    # original runs' formatting
                    block.runs = self._merge_runs(
                        edit.updated_runs, runs_text, new_content
                    )
                    block.content = new_content
                else:
                    block.runs = edit.updated_runs
                    block.content = runs_text
            elif block.runs:
                # Apply format merge strategy
                block.runs = self._merge_runs(block.runs, old_content, new_content)
                block.content = new_content
            else:
                block.content = new_content

        from datetime import datetime

        ir.updated_at = datetime.now()
        return ir

    # ========================================================================
    # Frontmatter parsing
    # ========================================================================

    def _parse_frontmatter(self, text: str, result: DfmParseResult) -> None:
        """Extract YAML frontmatter."""
        m = _FRONTMATTER_RE.search(text)
        if not m:
            result.errors.append("Missing YAML frontmatter.")
            return
        try:
            data = yaml.safe_load(m.group(1))
            result.doc_id = data.get("doc_id", "")
            result.source = data.get("source", "")
            result.checksum = data.get("checksum", "")
        except yaml.YAMLError as e:
            result.errors.append(f"Invalid frontmatter YAML: {e}")

    # ========================================================================
    # Styles parsing
    # ========================================================================

    def _parse_styles(self, text: str, result: DfmParseResult) -> None:
        """Extract document styles block."""
        m = _STYLES_RE.search(text)
        if not m:
            return
        try:
            data = yaml.safe_load(m.group(1))
            result.style_info = DocxStyleInfo.from_dict(data)
        except yaml.YAMLError as e:
            result.errors.append(f"Invalid styles YAML: {e}")

    # ========================================================================
    # Block parsing
    # ========================================================================

    def _parse_blocks(self, text: str, result: DfmParseResult) -> None:
        """Parse all content blocks from DFM text."""
        lines = text.split("\n")
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]

            # Skip frontmatter
            if line.strip() == "---":
                i += 1
                while i < n and lines[i].strip() != "---":
                    i += 1
                i += 1
                continue

            # Skip styles block
            if line.strip().startswith("<!-- dfm:styles"):
                while i < n and not lines[i].strip().endswith("-->"):
                    i += 1
                i += 1
                continue

            # Bookmark (single-line)
            bm = _BOOKMARK_RE.match(line.strip())
            if bm:
                result.edits.append(
                    BlockEdit(
                        block_id=bm.group(1),
                        new_content="",
                        block_type=DfmBlockType.BOOKMARK,
                    )
                )
                i += 1
                continue

            # Break (single or multi-line)
            brk = _BREAK_RE.match(line.strip())
            if brk:
                result.edits.append(
                    BlockEdit(
                        block_id=brk.group(1),
                        new_content="",
                        block_type=DfmBlockType.BREAK,
                    )
                )
                i += 1
                continue

            # Compound block: <!-- dfm:TYPE @b:ID ... -->
            cm = _COMPOUND_OPEN_RE.match(line.strip())
            if cm:
                i = self._parse_compound_block(lines, i, cm, result)
                continue

            # Multi-line compound block (opening tag spans lines)
            cms = _COMPOUND_START_RE.match(line.strip())
            if cms and not line.strip().endswith("-->"):
                i = self._parse_compound_block_multiline(lines, i, cms, result)
                continue

            # Simple block annotation: <!-- @b:ID ... -->
            sm = _SIMPLE_BLOCK_RE.match(line.strip())
            if sm:
                i = self._parse_simple_block(lines, i, sm, result)
                continue

            i += 1

    def _parse_simple_block(
        self,
        lines: list[str],
        start: int,
        match: re.Match,
        result: DfmParseResult,
    ) -> int:
        """Parse a simple (editable) block: paragraph, heading, list, caption."""
        block_id = match.group(1)
        i = start + 1

        # Collect content lines until next block marker or blank line sequence
        content_lines: list[str] = []
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Stop at next block annotation or compound block
            if (
                _SIMPLE_BLOCK_RE.match(stripped)
                or _COMPOUND_OPEN_RE.match(stripped)
                or _COMPOUND_START_RE.match(stripped)
                or _BOOKMARK_RE.match(stripped)
                or _BREAK_RE.match(stripped)
            ):
                break

            # Stop at double blank line (block separator)
            if stripped == "" and content_lines and content_lines[-1].strip() == "":
                break

            content_lines.append(line)
            i += 1

        # Trim trailing blanks
        while content_lines and content_lines[-1].strip() == "":
            content_lines.pop()

        raw_content = "\n".join(content_lines)

        # Determine block type from content
        block_type = DfmBlockType.PARAGRAPH
        clean_content = raw_content

        heading_m = _HEADING_RE.match(raw_content)
        list_m = _LIST_ITEM_RE.match(raw_content)

        if heading_m:
            block_type = DfmBlockType.HEADING
            clean_content = heading_m.group(2)
        elif list_m:
            block_type = DfmBlockType.LIST_ITEM
            clean_content = list_m.group(2)
        elif raw_content.startswith("*") and raw_content.endswith("*"):
            # Could be a caption
            block_type = DfmBlockType.CAPTION
            clean_content = raw_content.strip("*").strip()

        # Strip markdown formatting for plain text
        clean_content = self._md_to_plain(clean_content)

        result.edits.append(
            BlockEdit(
                block_id=block_id,
                new_content=clean_content,
                block_type=block_type,
            )
        )
        return i

    def _parse_compound_block(
        self,
        lines: list[str],
        start: int,
        match: re.Match,
        result: DfmParseResult,
    ) -> int:
        """Parse a compound block enclosed in <!-- dfm:TYPE --> ... <!-- /dfm:TYPE -->."""
        block_type_str = match.group(1)
        block_id = match.group(2)
        yaml_text = match.group(3).strip()

        # Find the opening comment end (may be multi-line)
        i = start
        if not lines[i].strip().endswith("-->"):
            # Multi-line opening tag — accumulate YAML
            yaml_lines = []
            if yaml_text:
                yaml_lines.append(yaml_text)
            i += 1
            while i < len(lines) and not lines[i].strip().endswith("-->"):
                yaml_lines.append(lines[i])
                i += 1
            # The line ending with --> belongs to the opening tag
            closing_line = lines[i].strip() if i < len(lines) else ""
            if closing_line.endswith("-->"):
                remaining = closing_line[:-3].strip()
                if remaining:
                    yaml_lines.append(remaining)
            yaml_text = "\n".join(yaml_lines)
            i += 1
        else:
            i += 1

        # Find closing tag
        close_tag = f"<!-- /dfm:{block_type_str} -->"
        content_lines: list[str] = []
        while i < len(lines):
            if lines[i].strip() == close_tag:
                i += 1
                break
            content_lines.append(lines[i])
            i += 1

        content = "\n".join(content_lines).strip()

        # Parse YAML metadata
        meta: dict[str, Any] = {}
        if yaml_text:
            try:
                parsed = yaml.safe_load(yaml_text)
                if isinstance(parsed, dict):
                    meta = parsed
            except yaml.YAMLError:
                pass

        # Dispatch by type
        try:
            bt = DfmBlockType(block_type_str)
        except ValueError:
            result.errors.append(f"Unknown block type: {block_type_str}")
            return i

        edit = BlockEdit(
            block_id=block_id,
            new_content=content,
            block_type=bt,
        )

        if bt == DfmBlockType.TABLE:
            edit.table_rows = self._parse_md_table(content)
            edit.new_content = content
        elif bt == DfmBlockType.FORMAT:
            runs_data = meta.get("runs", [])
            if runs_data:
                edit.updated_runs = [FormatRun.from_dict(r) for r in runs_data]
            # Also extract the fallback text
            edit.new_content = self._md_to_plain(content)

        result.edits.append(edit)
        return i

    def _parse_compound_block_multiline(
        self,
        lines: list[str],
        start: int,
        match: re.Match,
        result: DfmParseResult,
    ) -> int:
        """Parse a compound block whose opening tag spans multiple lines."""
        block_type_str = match.group(1)
        block_id = match.group(2)

        # Accumulate YAML from the opening tag lines
        # First line after the <!-- dfm:TYPE @b:ID part
        first_line = lines[start].strip()
        # Extract any YAML on the first line after the @b:ID
        after_id = re.sub(r"<!--\s*dfm:\w+\s+@b:\S+\s*", "", first_line)
        yaml_lines = []
        if after_id and after_id != "-->":
            yaml_lines.append(after_id)

        i = start + 1
        while i < len(lines) and not lines[i].strip().endswith("-->"):
            yaml_lines.append(lines[i])
            i += 1

        # Line ending with -->
        if i < len(lines):
            closing = lines[i].strip()
            if closing.endswith("-->"):
                remaining = closing[:-3].strip()
                if remaining:
                    yaml_lines.append(remaining)
            i += 1

        yaml_text = "\n".join(yaml_lines).strip()

        # Find closing tag
        close_tag = f"<!-- /dfm:{block_type_str} -->"
        content_lines: list[str] = []
        while i < len(lines):
            if lines[i].strip() == close_tag:
                i += 1
                break
            content_lines.append(lines[i])
            i += 1

        content = "\n".join(content_lines).strip()

        # Parse YAML metadata
        meta: dict[str, Any] = {}
        if yaml_text:
            try:
                parsed = yaml.safe_load(yaml_text)
                if isinstance(parsed, dict):
                    meta = parsed
            except yaml.YAMLError:
                pass

        # Dispatch by type
        try:
            bt = DfmBlockType(block_type_str)
        except ValueError:
            result.errors.append(f"Unknown block type: {block_type_str}")
            return i

        edit = BlockEdit(
            block_id=block_id,
            new_content=content,
            block_type=bt,
        )

        if bt == DfmBlockType.TABLE:
            edit.table_rows = self._parse_md_table(content)
            edit.new_content = content
        elif bt == DfmBlockType.FORMAT:
            runs_data = meta.get("runs", [])
            if runs_data:
                edit.updated_runs = [FormatRun.from_dict(r) for r in runs_data]
            edit.new_content = self._md_to_plain(content)

        result.edits.append(edit)
        return i

    # ========================================================================
    # Table parsing helpers
    # ========================================================================

    @staticmethod
    def _parse_md_table(text: str) -> list[list[str]] | None:
        """Parse a markdown table into a 2D list of cell texts."""
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        if not lines:
            return None

        rows: list[list[str]] = []
        for line in lines:
            # Skip separator rows (|---|---|)
            if re.match(r"^\|[\s\-:|]+\|$", line):
                continue
            if not line.startswith("|"):
                continue
            # Split by pipes, strip outer empties
            cells = line.split("|")
            cells = [c.strip() for c in cells[1:-1]]  # Remove first/last empty
            rows.append(cells)
        return rows if rows else None

    @staticmethod
    def _rows_to_md_table(rows: list[list[str]]) -> str:
        """Convert 2D rows back to a markdown table string."""
        if not rows:
            return ""

        lines = []
        # Header row
        lines.append("| " + " | ".join(rows[0]) + " |")
        # Separator
        lines.append("| " + " | ".join("---" for _ in rows[0]) + " |")
        # Data rows
        for row in rows[1:]:
            # Pad row to match header width
            padded = row + [""] * (len(rows[0]) - len(row))
            lines.append("| " + " | ".join(padded[: len(rows[0])]) + " |")
        return "\n".join(lines)

    # ========================================================================
    # Format merge strategy
    # ========================================================================

    @staticmethod
    def _merge_runs(
        original_runs: list[FormatRun],
        old_text: str,
        new_text: str,
    ) -> list[FormatRun]:
        """
        Merge edited text back into format runs.

        Strategy:
        - If text length change < 20%: proportional redistribution
        - If text length change >= 20%: assign all to primary run format
        """
        if not original_runs:
            return [FormatRun(text=new_text)]

        old_len = len(old_text) if old_text else 1
        change_ratio = abs(len(new_text) - old_len) / old_len

        if change_ratio < 0.2 and len(original_runs) > 1:
            # Proportional redistribution
            return DfmParser._proportional_redistribute(original_runs, new_text)
        else:
            # Assign to primary run format
            primary = original_runs[0]
            return [
                FormatRun(
                    text=new_text,
                    bold=primary.bold,
                    italic=primary.italic,
                    underline=primary.underline,
                    strike=primary.strike,
                    superscript=primary.superscript,
                    subscript=primary.subscript,
                    font_name=primary.font_name,
                    font_size=primary.font_size,
                    color=primary.color,
                    highlight=primary.highlight,
                    small_caps=primary.small_caps,
                )
            ]

    @staticmethod
    def _proportional_redistribute(
        runs: list[FormatRun], new_text: str
    ) -> list[FormatRun]:
        """Distribute new text across runs proportionally to original lengths."""
        total_old = sum(len(r.text) for r in runs)
        if total_old == 0:
            return [FormatRun(text=new_text)]

        result = []
        pos = 0
        for idx, run in enumerate(runs):
            if idx == len(runs) - 1:
                # Last run gets remaining text
                chunk = new_text[pos:]
            else:
                ratio = len(run.text) / total_old
                chunk_len = round(ratio * len(new_text))
                chunk = new_text[pos : pos + chunk_len]
                pos += chunk_len

            result.append(
                FormatRun(
                    text=chunk,
                    bold=run.bold,
                    italic=run.italic,
                    underline=run.underline,
                    strike=run.strike,
                    superscript=run.superscript,
                    subscript=run.subscript,
                    font_name=run.font_name,
                    font_size=run.font_size,
                    color=run.color,
                    highlight=run.highlight,
                    small_caps=run.small_caps,
                )
            )
        return result

    # ========================================================================
    # Markdown stripping
    # ========================================================================

    @staticmethod
    def _md_to_plain(text: str) -> str:
        """Strip common Markdown formatting to get plain text."""
        # Bold+italic
        text = re.sub(r"\*{3}(.+?)\*{3}", r"\1", text)
        # Bold
        text = re.sub(r"\*{2}(.+?)\*{2}", r"\1", text)
        # Italic
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        # Strikethrough
        text = re.sub(r"~~(.+?)~~", r"\1", text)
        # Superscript
        text = re.sub(r"\^(.+?)\^", r"\1", text)
        # Subscript (pandoc-style)
        text = re.sub(r"~(.+?)~", r"\1", text)
        return text
