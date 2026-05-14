"""DOCX Markdown table and write-back helpers for DocxAdapter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

from lxml import etree  # type: ignore[import-untyped]

from src.domain.docx_value_objects import DfmBlockType
from src.infrastructure.dfm_parser import DfmParser
from src.infrastructure.docx_openxml import (
    HALF_POINTS_TO_PT,
    NS,
)
from src.infrastructure.docx_openxml import (
    NON_VISIBLE_REVISION_TAGS as _NON_VISIBLE_REVISION_TAGS,
)
from src.infrastructure.docx_openxml import (
    REVISION_TAG_TYPES as _REVISION_TAG_TYPES,
)
from src.infrastructure.docx_openxml import (
    XML_SPACE as _XML_SPACE,
)
from src.infrastructure.docx_openxml import (
    safe_int as _safe_int,
)

if TYPE_CHECKING:
    from pathlib import Path

    from src.domain.docx_entities import DfmBlock, DocxIR, FormatRun

_DIFF_TOKEN_RE = re.compile(r"\s+|\S+")


@dataclass
class _TrackChangeContext:
    """Shared state for one DOCX tracked-change write operation."""

    author: str
    date: str
    next_id: int = 1

    def take_id(self) -> str:
        revision_id = str(self.next_id)
        self.next_id += 1
        return revision_id


@dataclass
class _RunStyleSpan:
    """Character span mapped to the run properties that styled it."""

    start: int
    end: int
    rpr: etree._Element | None = None


class DocxWritebackMixin:
    def _get_paragraph_text(self, p_elem: etree._Element) -> str:
        raise NotImplementedError

    def _get_vmerge_state(self, tc_pr: etree._Element | None) -> str | None:
        raise NotImplementedError

    def _iter_row_cells(
        self,
        tr_elem: etree._Element,
    ) -> list[tuple[int, etree._Element, int, etree._Element | None]]:
        raise NotImplementedError

    def _local_name(self, elem: etree._Element) -> str:
        raise NotImplementedError

    def _has_ancestor_with_local_name(
        self,
        elem: etree._Element,
        local_names: set[str],
    ) -> bool:
        raise NotImplementedError

    @staticmethod
    def _rows_to_md_table(rows: list[list[str]]) -> str:
        """Convert a list of rows to a Markdown pipe table."""
        if not rows:
            return ""

        # Ensure all rows have same number of columns
        max_cols = max(len(r) for r in rows)
        for row in rows:
            while len(row) < max_cols:
                row.append("")

        # Clean cell text (escape table delimiters/newlines for markdown, strip)
        for row in rows:
            for i, cell in enumerate(row):
                row[i] = (
                    cell.replace("\\", "\\\\")
                    .replace("|", "\\|")
                    .replace("\n", "<br>")
                    .strip()
                )

        # Calculate column widths
        widths = [0] * max_cols
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell), 3)

        # Build table
        lines = []

        # Header row
        header = (
            "| "
            + " | ".join(rows[0][i].ljust(widths[i]) for i in range(max_cols))
            + " |"
        )
        lines.append(header)

        # Separator
        sep = "| " + " | ".join("-" * widths[i] for i in range(max_cols)) + " |"
        lines.append(sep)

        # Data rows
        for row in rows[1:]:
            line = (
                "| "
                + " | ".join(row[i].ljust(widths[i]) for i in range(max_cols))
                + " |"
            )
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def _nested_table_marker(block_id: str) -> str:
        """Return the inline placeholder used for nested tables inside cell text."""
        return f"[[NESTED_TABLE:{block_id}]]"

    @classmethod
    def _nested_table_marker_match(cls, value: str) -> re.Match[str] | None:
        """Match a nested-table placeholder token."""
        return re.fullmatch(r"\[\[NESTED_TABLE:(t\d{3})\]\]", value.strip())

    # ========================================================================
    # Private: Rebuild docx from IR
    # ========================================================================

    def _update_document_xml(
        self,
        docx_path: Path,
        ir: DocxIR,
        changed_block_ids: set[str] | None = None,
        *,
        original_ir: DocxIR | None = None,
        track_changes: bool = False,
        revision_author: str = "Asset-Aware MCP",
    ) -> None:
        """
        Update document.xml within the docx zip with modified text from IR.

        Strategy: Parse the existing document.xml, walk paragraphs and tables
        in order, match them 1:1 with IR blocks, and update text content
        where it has changed.
        """
        import zipfile

        # Read the existing zip
        temp_path = docx_path.with_suffix(".tmp")

        with zipfile.ZipFile(docx_path, "r") as zin:
            doc_xml = zin.read("word/document.xml")

            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    if item.filename == "word/document.xml":
                        # Modify document.xml
                        modified_xml = self._apply_text_changes(
                            doc_xml,
                            ir,
                            changed_block_ids,
                            original_ir=original_ir,
                            track_changes=track_changes,
                            revision_author=revision_author,
                        )
                        zout.writestr(item, modified_xml)
                    elif item.filename == "word/settings.xml" and track_changes:
                        settings_xml = zin.read(item.filename)
                        zout.writestr(item, self._enable_track_revisions(settings_xml))
                    else:
                        zout.writestr(item, zin.read(item.filename))

        # Replace original with modified
        temp_path.replace(docx_path)

    def _apply_text_changes(
        self,
        doc_xml: bytes,
        ir: DocxIR,
        changed_block_ids: set[str] | None = None,
        *,
        original_ir: DocxIR | None = None,
        track_changes: bool = False,
        revision_author: str = "Asset-Aware MCP",
    ) -> bytes:
        """
        Apply text changes from IR blocks back to document.xml.

        Walks paragraphs and tables in the same order as original parsing,
        matching each to the corresponding IR block by index position.
        """
        tree = etree.fromstring(doc_xml)
        body = tree.find(f".//{{{NS['w']}}}body")
        if body is None:
            return doc_xml

        original_blocks = (
            {block.id: block for block in original_ir.blocks} if original_ir else {}
        )
        revision_context = (
            _TrackChangeContext(
                author=revision_author or "Asset-Aware MCP",
                date=self._revision_timestamp(),
                next_id=self._max_revision_id(tree) + 1,
            )
            if track_changes
            else None
        )

        top_level_blocks = [
            block
            for block in ir.blocks
            if not (
                block.block_type == DfmBlockType.TABLE and block.parent_cell is not None
            )
            and block.block_type != DfmBlockType.REVISION
        ]
        block_idx = 0
        nested_blocks_by_parent: dict[str, dict[str, list[DfmBlock]]] = {}
        for block in ir.blocks:
            if block.block_type != DfmBlockType.TABLE or block.parent_cell is None:
                continue
            parent_id = str(block.metadata.get("parent_table_id", ""))
            if not parent_id:
                continue
            nested_blocks_by_parent.setdefault(parent_id, {}).setdefault(
                block.parent_cell,
                [],
            ).append(block)

        for element in body:
            tag = etree.QName(element.tag).localname

            if tag == "p":
                if block_idx < len(top_level_blocks):
                    block = top_level_blocks[block_idx]
                    if block.block_type in (
                        DfmBlockType.PARAGRAPH,
                        DfmBlockType.HEADING,
                        DfmBlockType.LIST_ITEM,
                        DfmBlockType.FORMAT,
                        DfmBlockType.CAPTION,
                    ) and (changed_block_ids is None or block.id in changed_block_ids):
                        original_block = original_blocks.get(block.id)
                        original_text = (
                            self._block_write_text(original_block)
                            if original_block is not None
                            else self._get_paragraph_text(element)
                        )
                        self._update_paragraph_text(
                            element,
                            block,
                            revision_context=revision_context,
                            original_text=original_text,
                        )
                    block_idx += 1
            elif tag == "tbl" and block_idx < len(top_level_blocks):
                block = top_level_blocks[block_idx]
                if block.block_type == DfmBlockType.TABLE:
                    should_update_self = (
                        changed_block_ids is None or block.id in changed_block_ids
                    )
                    has_nested_updates = self._table_has_changed_nested_descendant(
                        block.id,
                        nested_blocks_by_parent,
                        changed_block_ids,
                    )
                    if should_update_self or has_nested_updates:
                        self._update_table_text(
                            element,
                            block,
                            nested_blocks_by_parent,
                            changed_block_ids,
                            update_direct_text=should_update_self,
                            revision_context=revision_context,
                        )
                block_idx += 1

        return bytes(
            etree.tostring(
                tree, xml_declaration=True, encoding="UTF-8", standalone=True
            )
        )

    def _update_paragraph_text(
        self,
        p_elem: etree._Element,
        block: DfmBlock,
        *,
        revision_context: _TrackChangeContext | None = None,
        original_text: str | None = None,
    ) -> None:
        """Update text content of a paragraph element from a DfmBlock."""
        if revision_context is not None:
            desired_text = self._block_write_text(block)
            baseline_text = (
                original_text
                if original_text is not None
                else self._get_paragraph_text(p_elem)
            )
            if baseline_text != desired_text:
                self._replace_paragraph_with_tracked_change(
                    p_elem,
                    baseline_text,
                    desired_text,
                    revision_context,
                    new_runs=block.runs,
                )
                return

        runs = self._iter_text_runs(p_elem)
        if not runs:
            return

        if block.runs:
            runs_text = "".join(run.text for run in block.runs)
            text_segments = (
                [run.text for run in block.runs]
                if runs_text == block.content
                else [block.content]
            )
        else:
            text_segments = [block.content]
        if not text_segments:
            text_segments = [""]

        self._set_run_texts(runs, text_segments)

    @staticmethod
    def _block_write_text(block: DfmBlock) -> str:
        """Return the exact visible text intended for DOCX write-back."""
        return block.plain_text if block.runs else block.content

    def _update_table_text(
        self,
        tbl_elem: etree._Element,
        block: DfmBlock,
        nested_blocks_by_parent: dict[str, dict[str, list[DfmBlock]]],
        changed_block_ids: set[str] | None = None,
        *,
        update_direct_text: bool = True,
        revision_context: _TrackChangeContext | None = None,
    ) -> None:
        """Update text content of table cells from a DfmBlock."""
        md_rows = self._parse_md_table(block.content)
        if not md_rows:
            return

        xml_rows = tbl_elem.findall(f"{{{NS['w']}}}tr")

        for row_idx, (xml_row, md_row) in enumerate(
            zip(xml_rows, md_rows, strict=False)
        ):
            for col_idx, cell, _col_span, tc_pr in self._iter_row_cells(xml_row):
                if col_idx >= len(md_row):
                    continue
                if self._get_vmerge_state(tc_pr) == "continue":
                    continue
                md_cell = md_row[col_idx]
                nested_blocks = nested_blocks_by_parent.get(block.id, {}).get(
                    f"{row_idx}:{col_idx}",
                    [],
                )
                desired_text = md_cell.strip()
                current_text = self._get_table_cell_content_for_compare(
                    cell,
                    nested_blocks,
                ).strip()
                should_update_direct_text = (
                    update_direct_text and desired_text != current_text
                )
                self._update_table_cell(
                    cell,
                    desired_text,
                    nested_blocks,
                    nested_blocks_by_parent,
                    changed_block_ids,
                    update_direct_text=should_update_direct_text,
                    revision_context=revision_context,
                )

    def _get_table_cell_content_for_compare(
        self,
        cell: etree._Element,
        nested_blocks: list[DfmBlock],
    ) -> str:
        """Return direct cell content using nested-table markers for comparison."""
        segments: list[str] = []
        nested_iter = iter(nested_blocks)
        for child in cell:
            tag = etree.QName(child.tag).localname
            if tag == "tcPr":
                continue
            if tag == "p":
                segments.append(self._get_paragraph_text(child))
                continue
            if tag == "tbl":
                nested_block = next(nested_iter, None)
                if nested_block is not None:
                    segments.append(self._nested_table_marker(nested_block.id))

        while segments and not segments[-1]:
            segments.pop()
        return "\n".join(segments)

    def _update_table_cell(
        self,
        cell: etree._Element,
        cell_text: str,
        nested_blocks: list[DfmBlock],
        nested_blocks_by_parent: dict[str, dict[str, list[DfmBlock]]],
        changed_block_ids: set[str] | None = None,
        *,
        update_direct_text: bool = True,
        revision_context: _TrackChangeContext | None = None,
    ) -> None:
        """Update a table cell while preserving nested table boundaries."""
        desired_items = cell_text.split("\n") if cell_text else []
        direct_children = [
            child for child in cell if etree.QName(child.tag).localname != "tcPr"
        ]
        last_paragraph: etree._Element | None = None
        nested_iter = iter(nested_blocks)

        for child in direct_children:
            tag = etree.QName(child.tag).localname
            if tag == "p":
                next_text = self._get_paragraph_text(child)
                if update_direct_text:
                    next_text = ""
                    if desired_items and not self._nested_table_marker_match(
                        desired_items[0]
                    ):
                        next_text = desired_items.pop(0)
                    self._set_paragraph_plain_text(
                        child,
                        next_text,
                        revision_context=revision_context,
                    )
                last_paragraph = child
                continue

            if tag != "tbl":
                continue

            nested_block = next(nested_iter, None)
            if desired_items and self._nested_table_marker_match(desired_items[0]):
                desired_items.pop(0)
            if nested_block is None:
                continue
            if changed_block_ids is None or nested_block.id in changed_block_ids:
                self._update_table_text(
                    child,
                    nested_block,
                    nested_blocks_by_parent,
                    changed_block_ids,
                    revision_context=revision_context,
                )

        leftover_text = [
            item for item in desired_items if not self._nested_table_marker_match(item)
        ]
        if update_direct_text and leftover_text and last_paragraph is not None:
            current_text = self._get_paragraph_text(last_paragraph)
            suffix = "\n".join(leftover_text)
            merged = f"{current_text}\n{suffix}" if current_text else suffix
            self._set_paragraph_plain_text(
                last_paragraph,
                merged,
                revision_context=revision_context,
            )

    def _table_has_changed_nested_descendant(
        self,
        table_id: str,
        nested_blocks_by_parent: dict[str, dict[str, list[DfmBlock]]],
        changed_block_ids: set[str] | None,
    ) -> bool:
        """Return whether a table has any changed nested descendant blocks."""
        if changed_block_ids is None:
            return True

        child_groups = nested_blocks_by_parent.get(table_id, {})
        for child_blocks in child_groups.values():
            for child_block in child_blocks:
                if child_block.id in changed_block_ids:
                    return True
                if self._table_has_changed_nested_descendant(
                    child_block.id,
                    nested_blocks_by_parent,
                    changed_block_ids,
                ):
                    return True
        return False

    def _set_paragraph_plain_text(
        self,
        p_elem: etree._Element,
        text: str,
        *,
        revision_context: _TrackChangeContext | None = None,
    ) -> None:
        """Replace the visible text in a paragraph while preserving existing runs."""
        if revision_context is not None:
            original_text = self._get_paragraph_text(p_elem)
            if original_text != text:
                self._replace_paragraph_with_tracked_change(
                    p_elem,
                    original_text,
                    text,
                    revision_context,
                )
                return

        runs = self._iter_text_runs(p_elem)
        if not runs:
            return
        self._set_run_texts(runs, [text])

    def _replace_paragraph_with_tracked_change(
        self,
        p_elem: etree._Element,
        old_text: str,
        new_text: str,
        revision_context: _TrackChangeContext,
        *,
        new_runs: list[FormatRun] | None = None,
    ) -> None:
        """Rewrite a paragraph's textual content as native Word revisions."""
        old_spans = self._paragraph_run_style_spans(p_elem)
        new_spans = self._format_run_style_spans(new_runs or [])
        target = self._track_change_rewrite_target(p_elem)
        self._remove_textual_children(target)

        for op, text, old_start, old_end, new_start, new_end in self._diff_text_ops(
            old_text, new_text
        ):
            if not text:
                continue
            if op == "equal":
                self._append_text_with_style_spans(
                    target,
                    text,
                    old_spans,
                    old_start,
                    old_end,
                )
            elif op == "delete":
                self._append_revision_text_with_style_spans(
                    target,
                    "del",
                    text,
                    revision_context,
                    old_spans,
                    old_start,
                    old_end,
                )
            elif op == "insert":
                spans = new_spans or old_spans
                span_start = new_start if new_spans else old_start
                span_end = new_end if new_spans else old_start
                self._append_revision_text_with_style_spans(
                    target,
                    "ins",
                    text,
                    revision_context,
                    spans,
                    span_start,
                    span_end,
                )

    def _diff_text_chunks(self, old_text: str, new_text: str) -> list[tuple[str, str]]:
        """Return stable token-level chunks for Word revision emission."""
        return [
            (op, text)
            for op, text, _old_start, _old_end, _new_start, _new_end in self._diff_text_ops(
                old_text, new_text
            )
        ]

    def _diff_text_ops(
        self, old_text: str, new_text: str
    ) -> list[tuple[str, str, int, int, int, int]]:
        """Return token-level diff ops with source offsets for styling/provenance."""
        old_tokens = self._tokenize_diff_text(old_text)
        new_tokens = self._tokenize_diff_text(new_text)
        old_offsets = self._token_offsets(old_tokens)
        new_offsets = self._token_offsets(new_tokens)
        matcher = SequenceMatcher(None, old_tokens, new_tokens, autojunk=False)

        chunks: list[tuple[str, str, int, int, int, int]] = []
        for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
            old_char_start = old_offsets[old_start]
            old_char_end = old_offsets[old_end]
            new_char_start = new_offsets[new_start]
            new_char_end = new_offsets[new_end]
            if tag == "equal":
                chunks.append(
                    (
                        "equal",
                        "".join(new_tokens[new_start:new_end]),
                        old_char_start,
                        old_char_end,
                        new_char_start,
                        new_char_end,
                    )
                )
            elif tag == "delete":
                chunks.append(
                    (
                        "delete",
                        "".join(old_tokens[old_start:old_end]),
                        old_char_start,
                        old_char_end,
                        new_char_start,
                        new_char_end,
                    )
                )
            elif tag == "insert":
                chunks.append(
                    (
                        "insert",
                        "".join(new_tokens[new_start:new_end]),
                        old_char_start,
                        old_char_end,
                        new_char_start,
                        new_char_end,
                    )
                )
            else:
                chunks.append(
                    (
                        "delete",
                        "".join(old_tokens[old_start:old_end]),
                        old_char_start,
                        old_char_end,
                        new_char_start,
                        new_char_start,
                    )
                )
                chunks.append(
                    (
                        "insert",
                        "".join(new_tokens[new_start:new_end]),
                        old_char_start,
                        old_char_start,
                        new_char_start,
                        new_char_end,
                    )
                )
        return chunks

    @staticmethod
    def _tokenize_diff_text(text: str) -> list[str]:
        """Tokenize while preserving whitespace so diff chunks quote exactly."""
        if not text:
            return []
        return _DIFF_TOKEN_RE.findall(text)

    @staticmethod
    def _token_offsets(tokens: list[str]) -> list[int]:
        offsets = [0]
        cursor = 0
        for token in tokens:
            cursor += len(token)
            offsets.append(cursor)
        return offsets

    def _track_change_rewrite_target(self, p_elem: etree._Element) -> etree._Element:
        """Preserve a single hyperlink/SDT wrapper when all text lives inside it."""
        textual_children = [
            child
            for child in p_elem
            if self._local_name(child) != "pPr"
            and self._is_textual_paragraph_child(child)
        ]
        if len(textual_children) != 1:
            return p_elem

        child = textual_children[0]
        tag = self._local_name(child)
        if tag == "hyperlink":
            return child
        if tag == "sdt":
            content = child.find(f"{{{NS['w']}}}sdtContent")
            if content is not None:
                return content
        return p_elem

    def _paragraph_run_style_spans(self, p_elem: etree._Element) -> list[_RunStyleSpan]:
        spans: list[_RunStyleSpan] = []
        cursor = 0
        for r_elem in self._iter_text_runs(p_elem):
            text = self._run_visible_text(r_elem)
            if not text:
                continue
            rpr = r_elem.find(f"{{{NS['w']}}}rPr")
            spans.append(
                _RunStyleSpan(
                    start=cursor,
                    end=cursor + len(text),
                    rpr=self._clone_rpr(rpr),
                )
            )
            cursor += len(text)
        return spans

    def _format_run_style_spans(self, runs: list[FormatRun]) -> list[_RunStyleSpan]:
        spans: list[_RunStyleSpan] = []
        cursor = 0
        for run in runs:
            if not run.text:
                continue
            spans.append(
                _RunStyleSpan(
                    start=cursor,
                    end=cursor + len(run.text),
                    rpr=self._format_run_to_rpr(run),
                )
            )
            cursor += len(run.text)
        return spans

    def _append_revision_text_with_style_spans(
        self,
        parent: etree._Element,
        tag: str,
        text: str,
        revision_context: _TrackChangeContext,
        spans: list[_RunStyleSpan],
        source_start: int,
        source_end: int,
    ) -> None:
        revision = etree.SubElement(parent, f"{{{NS['w']}}}{tag}")
        revision.set(f"{{{NS['w']}}}id", revision_context.take_id())
        revision.set(f"{{{NS['w']}}}author", revision_context.author)
        revision.set(f"{{{NS['w']}}}date", revision_context.date)
        self._append_text_with_style_spans(
            revision,
            text,
            spans,
            source_start,
            source_end,
            text_tag="delText" if tag == "del" else "t",
        )

    def _append_text_with_style_spans(
        self,
        parent: etree._Element,
        text: str,
        spans: list[_RunStyleSpan],
        source_start: int,
        source_end: int,
        *,
        text_tag: str = "t",
    ) -> None:
        if not text:
            return
        if not spans or source_end <= source_start:
            self._append_text_run(
                parent,
                text,
                text_tag=text_tag,
                rpr_template=self._style_at_offset(spans, source_start),
            )
            return

        emitted_until = 0
        for span in spans:
            overlap_start = max(source_start, span.start)
            overlap_end = min(source_end, span.end)
            if overlap_end <= overlap_start:
                continue

            chunk_start = overlap_start - source_start
            chunk_end = overlap_end - source_start
            if chunk_start > emitted_until:
                self._append_text_run(
                    parent,
                    text[emitted_until:chunk_start],
                    text_tag=text_tag,
                    rpr_template=self._style_at_offset(
                        spans, source_start + emitted_until
                    ),
                )
            self._append_text_run(
                parent,
                text[chunk_start:chunk_end],
                text_tag=text_tag,
                rpr_template=span.rpr,
            )
            emitted_until = chunk_end

        if emitted_until < len(text):
            self._append_text_run(
                parent,
                text[emitted_until:],
                text_tag=text_tag,
                rpr_template=self._style_at_offset(spans, source_start + emitted_until),
            )

    def _style_at_offset(
        self, spans: list[_RunStyleSpan], offset: int
    ) -> etree._Element | None:
        if not spans:
            return None
        previous = spans[0]
        for span in spans:
            if span.start <= offset < span.end:
                return self._clone_rpr(span.rpr)
            if span.end <= offset:
                previous = span
        return self._clone_rpr(previous.rpr)

    def _run_visible_text(self, r_elem: etree._Element) -> str:
        parts: list[str] = []
        for child in r_elem:
            tag = self._local_name(child)
            if tag in {"t", "delText"} and child.text:
                parts.append(child.text)
            elif tag == "tab":
                parts.append("\t")
            elif tag == "br":
                br_type = child.get(f"{{{NS['w']}}}type")
                if br_type != "page":
                    parts.append("\n")
        return "".join(parts)

    def _format_run_to_rpr(self, run: FormatRun) -> etree._Element | None:
        rpr = etree.Element(f"{{{NS['w']}}}rPr")
        if run.bold:
            etree.SubElement(rpr, f"{{{NS['w']}}}b")
        if run.italic:
            etree.SubElement(rpr, f"{{{NS['w']}}}i")
        if run.underline:
            etree.SubElement(rpr, f"{{{NS['w']}}}u", {f"{{{NS['w']}}}val": "single"})
        if run.font_name:
            etree.SubElement(
                rpr,
                f"{{{NS['w']}}}rFonts",
                {
                    f"{{{NS['w']}}}ascii": run.font_name,
                    f"{{{NS['w']}}}hAnsi": run.font_name,
                },
            )
        if run.font_size:
            etree.SubElement(
                rpr,
                f"{{{NS['w']}}}sz",
                {f"{{{NS['w']}}}val": str(int(run.font_size / HALF_POINTS_TO_PT))},
            )
        if run.color:
            etree.SubElement(
                rpr,
                f"{{{NS['w']}}}color",
                {f"{{{NS['w']}}}val": run.color.lstrip("#")},
            )
        return rpr if len(rpr) > 0 else None

    def _clone_rpr(self, rpr: etree._Element | None) -> etree._Element | None:
        return etree.fromstring(etree.tostring(rpr)) if rpr is not None else None

    def _remove_textual_children(self, p_elem: etree._Element) -> None:
        """Remove paragraph text containers while preserving non-textual anchors."""
        for child in list(p_elem):
            if self._local_name(child) == "pPr":
                continue
            if self._is_textual_paragraph_child(child):
                p_elem.remove(child)

    def _is_textual_paragraph_child(self, elem: etree._Element) -> bool:
        tag = self._local_name(elem)
        if tag in {"del", "ins", "moveFrom", "moveTo"}:
            return True
        if tag in {"hyperlink", "sdt"}:
            return self._element_has_textual_content(elem)
        if tag == "r":
            return self._element_has_textual_content(elem)
        return False

    def _element_has_textual_content(self, elem: etree._Element) -> bool:
        text_tags = {"t", "delText", "instrText", "tab", "br"}
        return any(self._local_name(child) in text_tags for child in elem.iter())

    def _append_revision_run(
        self,
        parent: etree._Element,
        tag: str,
        text: str,
        revision_context: _TrackChangeContext,
        *,
        rpr_template: etree._Element | None = None,
    ) -> None:
        revision = etree.SubElement(parent, f"{{{NS['w']}}}{tag}")
        revision.set(f"{{{NS['w']}}}id", revision_context.take_id())
        revision.set(f"{{{NS['w']}}}author", revision_context.author)
        revision.set(f"{{{NS['w']}}}date", revision_context.date)
        self._append_text_run(
            revision,
            text,
            text_tag="delText" if tag == "del" else "t",
            rpr_template=rpr_template,
        )

    def _append_text_run(
        self,
        parent: etree._Element,
        text: str,
        *,
        text_tag: str = "t",
        rpr_template: etree._Element | None = None,
    ) -> None:
        run = etree.SubElement(parent, f"{{{NS['w']}}}r")
        if rpr_template is not None:
            run.append(etree.fromstring(etree.tostring(rpr_template)))
        for part in re.split(r"(\t|\n)", text):
            if not part:
                continue
            if part == "\t":
                etree.SubElement(run, f"{{{NS['w']}}}tab")
                continue
            if part == "\n":
                etree.SubElement(run, f"{{{NS['w']}}}br")
                continue
            text_elem = etree.SubElement(run, f"{{{NS['w']}}}{text_tag}")
            text_elem.text = part
            text_elem.set(_XML_SPACE, "preserve")

    def _iter_text_runs(self, p_elem: etree._Element) -> list[etree._Element]:
        """Return paragraph runs in document order, including hyperlink/SDT runs."""
        runs = []
        for r_elem in p_elem.findall(f".//{{{NS['w']}}}r"):
            if self._has_ancestor_with_local_name(r_elem, _NON_VISIBLE_REVISION_TAGS):
                continue
            runs.append(r_elem)
        return runs

    def _set_run_texts(self, runs: list[etree._Element], segments: list[str]) -> None:
        """Assign visible text across existing XML runs without rewriting structure."""
        normalized_segments = list(segments) if segments else [""]
        for index, r_elem in enumerate(runs):
            t_elem = r_elem.find(f"{{{NS['w']}}}t")
            segment = (
                normalized_segments[index] if index < len(normalized_segments) else ""
            )
            if t_elem is None:
                has_break = r_elem.find(f"{{{NS['w']}}}br") is not None
                if has_break and segment in {"\n", "\r\n"}:
                    continue
                if segment:
                    t_elem = etree.SubElement(r_elem, f"{{{NS['w']}}}t")
                else:
                    continue

            text = segment
            if index == len(runs) - 1 and len(normalized_segments) > len(runs):
                tail = normalized_segments[index:]
                text = "".join(tail)

            t_elem.text = text
            t_elem.set(_XML_SPACE, "preserve")

    @staticmethod
    def _revision_timestamp() -> str:
        """Return an OOXML-compatible UTC timestamp."""
        return (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

    def _max_revision_id(self, tree: etree._Element) -> int:
        """Find the highest existing Word revision id to avoid collisions."""
        max_id = 0
        for elem in tree.iter():
            if self._local_name(elem) not in _REVISION_TAG_TYPES:
                continue
            revision_id = _safe_int(elem.get(f"{{{NS['w']}}}id"), default=0)
            if revision_id is not None:
                max_id = max(max_id, revision_id)
        return max_id

    def _enable_track_revisions(self, settings_xml: bytes) -> bytes:
        """Ensure Word's settings part records Track Changes as enabled."""
        try:
            tree = etree.fromstring(settings_xml)
        except etree.XMLSyntaxError:
            return settings_xml

        if tree.find(f"{{{NS['w']}}}trackRevisions") is None:
            etree.SubElement(tree, f"{{{NS['w']}}}trackRevisions")
        return bytes(
            etree.tostring(
                tree, xml_declaration=True, encoding="UTF-8", standalone=True
            )
        )

    @staticmethod
    def _parse_md_table(md_table: str) -> list[list[str]]:
        """Parse a markdown pipe table back into rows of cell text."""
        rows = []
        for line in md_table.strip().split("\n"):
            line = line.strip()
            if not line.startswith("|"):
                continue
            # Skip separator row
            if DfmParser._is_md_table_separator_row(line):
                continue
            cells = DfmParser._split_md_table_row(line)
            # Restore escaped newlines (<br> → real newline)
            cells = [c.replace("<br>", "\n") for c in cells]
            rows.append(cells)
        return rows
