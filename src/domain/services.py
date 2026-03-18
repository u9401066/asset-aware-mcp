"""
Domain Layer - Domain Services

Business logic that doesn't naturally fit within an entity.
"""

from __future__ import annotations

import re

from .entities import (
    DocumentAssets,
    DocumentManifest,
    FigureAsset,
    SectionAsset,
    TableAsset,
)
from .etl_profile import ETLProfile
from .line_spans import MarkdownLineSpanIndex


class ManifestGenerator:
    """
    Domain Service for generating document manifests.

    Responsible for creating the "map" of a document
    that allows AI Agents to navigate its structure.
    Configurable via ETLProfile.
    """

    def __init__(self, profile: ETLProfile | None = None):
        """
        Initialize with an ETL profile.

        Args:
            profile: ETL extraction profile (default: ETLProfile.default())
        """
        self.profile = profile or ETLProfile.default()

        # Pre-compile regexes from profile (once, at init)
        self._toc_caption_re = self.profile.compile_toc_caption_re()
        self._section_noise_re = self.profile.compile_section_noise_re()
        self._title_noise_re = self.profile.compile_title_noise_re()

    def generate(
        self,
        doc_id: str,
        filename: str,
        markdown: str,
        figures: list[FigureAsset],
        page_count: int,
        markdown_path: str,
        lightrag_entities: list[str] | None = None,
        tables: list[TableAsset] | None = None,
        pdf_toc: list[tuple[int, str, int]] | None = None,
        pdf_title: str = "",
        sections: list[SectionAsset] | None = None,
    ) -> DocumentManifest:
        """
        Generate a complete document manifest.

        Args:
            doc_id: Unique document identifier
            filename: Original filename
            markdown: Full markdown content
            figures: Extracted figures
            page_count: Total pages
            markdown_path: Path to saved markdown
            lightrag_entities: Optional entities from LightRAG
            tables: Optional pre-extracted tables (from Docling)
            pdf_toc: Optional PDF built-in TOC [(level, title, page), ...]
            pdf_title: Optional title from PDF metadata

        Returns:
            Complete DocumentManifest
        """
        # Use provided tables (Docling) or parse from markdown
        parsed_tables = tables if tables else self._parse_tables(markdown)

        # Parse sections: prefer PDF built-in TOC over font-size heuristics
        sections = (
            sections
            if sections is not None
            else self._sections_from_pdf_toc(pdf_toc, markdown)
            if pdf_toc
            else self._parse_sections(markdown)
        )

        self._assign_asset_sections(figures, parsed_tables, sections)

        # Build TOC from sections
        toc = [s.title for s in sections if s.level <= 2]

        # Detect title: prefer PDF metadata > merge consecutive H1 > first heading
        title = pdf_title or self._detect_title(markdown)

        return DocumentManifest(
            doc_id=doc_id,
            filename=filename,
            title=title,
            toc=toc,
            assets=DocumentAssets(
                tables=parsed_tables,
                figures=figures,
                sections=sections,
            ),
            lightrag_entities=lightrag_entities or [],
            page_count=page_count,
            markdown_path=markdown_path,
            manifest_path="",  # Will be set by repository when saving
        )

    def _parse_tables(self, markdown: str) -> list[TableAsset]:
        """Parse markdown pipe tables."""
        tables = []

        # Regex for markdown tables
        table_pattern = r"(\|[^\n]+\|\n\|[-:\| ]+\|\n(?:\|[^\n]+\|\n?)+)"

        for match_idx, match in enumerate(re.finditer(table_pattern, markdown)):
            table_text = match.group(1)

            # Count rows and columns
            rows = [r for r in table_text.strip().split("\n") if r.strip()]
            row_count = len(rows) - 1  # Exclude header separator
            col_count = rows[0].count("|") - 1 if rows else 0

            # Find which page this table is on
            table_start = match.start()
            page_for_table = self._find_page_at_position(markdown, table_start)
            line_start = markdown[:table_start].count("\n")
            line_end = line_start + len(table_text.splitlines())

            # Preview: first 100 chars
            preview = table_text[:100].replace("\n", " ")

            tables.append(
                TableAsset(
                    id=f"tab_{match_idx + 1}",
                    page=page_for_table,
                    caption="",  # Caption detection TODO
                    preview=preview,
                    markdown=table_text,
                    row_count=row_count,
                    col_count=col_count,
                    line_start=line_start,
                    line_end=line_end,
                    line_source="markdown-table",
                )
            )

        return tables

    def _parse_sections(self, markdown: str) -> list[SectionAsset]:
        """Parse markdown headers as sections."""
        sections: list[SectionAsset] = []
        lines = markdown.split("\n")
        current_page = 1

        for i, line in enumerate(lines):
            # Update current page
            page_match = re.search(r"<!-- Page (\d+) -->", line)
            if page_match:
                current_page = int(page_match.group(1))
                continue

            # Detect headers
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()

                # Clean title (remove markdown formatting)
                title = re.sub(r"\*\*([^*]+)\*\*", r"\1", title)
                title = title.strip()

                if not title:
                    continue

                # Skip noise headings (table column headers like "# layers")
                if self._section_noise_re.match(title):
                    continue

                # Generate section ID (deduplicate with counter)
                base_id = f"sec_{re.sub(r'[^a-z0-9]', '_', title.lower())[:30]}"
                sec_id = base_id
                existing_ids = {s.id for s in sections}
                if sec_id in existing_ids:
                    counter = 2
                    while f"{base_id}_{counter}" in existing_ids:
                        counter += 1
                    sec_id = f"{base_id}_{counter}"

                # Find section end (next header of same or higher level)
                end_line = len(lines)
                for j in range(i + 1, len(lines)):
                    next_header = re.match(r"^(#{1,6})\s+", lines[j])
                    if next_header and len(next_header.group(1)) <= level:
                        end_line = j
                        break

                # Preview: content after header
                content_lines = lines[i + 1 : min(i + 5, end_line)]
                preview = " ".join(
                    ln.strip()
                    for ln in content_lines
                    if ln.strip() and not ln.startswith("<!--")
                )[:200]

                sections.append(
                    SectionAsset(
                        id=sec_id,
                        title=title,
                        level=level,
                        page=current_page,
                        start_line=i,
                        end_line=end_line,
                        preview=preview,
                    )
                )

        return sections

    def _find_page_at_position(self, markdown: str, position: int) -> int:
        """Find page number at a given position in markdown."""
        page = 1
        for match in re.finditer(r"<!-- Page (\d+) -->", markdown[:position]):
            page = int(match.group(1))
        return page

    def _detect_title(self, markdown: str) -> str:
        """
        Detect document title from markdown.

        Strategy:
        1. Merge consecutive H1 headings (often split across lines in PDFs)
        2. If no H1, try consecutive H2 headings
        3. Fallback to first non-empty line
        """
        lines = markdown.split("\n")

        # Try H1 first, then H2
        for target_level in ("#", "##"):
            titles: list[str] = []
            collecting = False

            for line in lines:
                stripped = line.strip()
                if not stripped or stripped.startswith("<!--"):
                    continue

                header_match = re.match(
                    rf"^{re.escape(target_level)}\s+(.+)$", stripped
                )
                if header_match:
                    title_text = header_match.group(1).strip()
                    # Skip noise headings
                    if (
                        len(title_text) < 3
                        or self._title_noise_re.match(title_text)
                        or self._section_noise_re.match(title_text)
                    ):
                        if collecting:
                            break  # Stop collecting after noise
                        continue
                    titles.append(title_text)
                    collecting = True
                elif collecting:
                    # Stop collecting when we hit non-target content
                    break

            if titles:
                return " ".join(titles)

        # Fallback: first non-empty line
        for line in markdown.split("\n"):
            line = line.strip()
            if line and not line.startswith("<!--"):
                return line[:100]

        return ""

    def _sections_from_pdf_toc(
        self,
        pdf_toc: list[tuple[int, str, int]],
        markdown: str,
    ) -> list[SectionAsset]:
        """
        Convert PDF built-in TOC to SectionAsset list.

        PDF TOC is much more reliable than font-size heuristics.

        Args:
            pdf_toc: List of (level, title, page) from PyMuPDF get_toc()

        Returns:
            List of SectionAsset
        """
        sections = []
        existing_ids: set[str] = set()
        line_index = MarkdownLineSpanIndex(markdown)

        for level, title, page in pdf_toc:
            title = title.strip()
            if not title:
                continue

            # Skip figure/table captions masquerading as TOC entries
            if self._toc_caption_re.match(title):
                continue

            # Generate section ID
            clean_title = re.sub(r"[^a-z0-9]", "_", title.lower())[:30]
            base_id = f"sec_{clean_title}"
            sec_id = base_id
            counter = 2
            while sec_id in existing_ids:
                sec_id = f"{base_id}_{counter}"
                counter += 1

            section_span = line_index.find_section_span(
                title,
                page_hint=page or None,
            )
            start_line = section_span.start_line if section_span else 0
            end_line = section_span.end_line if section_span else 0
            preview = (
                line_index.extract_preview(start_line, end_line)
                if section_span is not None
                else ""
            )

            sections.append(
                SectionAsset(
                    id=sec_id,
                    title=title,
                    level=level,
                    page=page,
                    start_line=start_line,
                    end_line=end_line,
                    preview=preview,
                )
            )
            existing_ids.add(sec_id)

        return sections

    @staticmethod
    def _assign_asset_sections(
        figures: list[FigureAsset],
        tables: list[TableAsset],
        sections: list[SectionAsset],
    ) -> None:
        if not sections:
            return

        def assign_asset_section(asset: FigureAsset | TableAsset) -> None:
            if asset.line_start is None or asset.line_end is None:
                return
            containing = [
                section
                for section in sections
                if section.start_line <= asset.line_start
                and asset.line_end <= section.end_line
            ]
            if not containing:
                return
            section = max(containing, key=lambda item: (item.level, item.start_line))
            asset.section_id = section.id
            asset.section_title = section.title

        for table_asset in tables:
            assign_asset_section(table_asset)

        for figure_asset in figures:
            assign_asset_section(figure_asset)


class AssetExtractor:
    """
    Domain Service for extracting specific assets from markdown.
    """

    def extract_section_content(self, markdown: str, section: SectionAsset) -> str:
        """Extract full content of a section."""
        lines = markdown.split("\n")

        if section.start_line >= len(lines):
            return ""

        section_lines = lines[section.start_line : section.end_line]
        return "\n".join(section_lines)

    def extract_table_by_id(self, markdown: str, table_id: str) -> str | None:
        """Extract a specific table by ID."""
        # Parse tables and find matching one
        table_pattern = r"(\|[^\n]+\|\n\|[-:\| ]+\|\n(?:\|[^\n]+\|\n?)+)"

        for match_idx, match in enumerate(re.finditer(table_pattern, markdown)):
            if f"tab_{match_idx + 1}" == table_id:
                return match.group(1)

        return None
