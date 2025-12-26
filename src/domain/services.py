"""
Domain Layer - Domain Services

Business logic that doesn't naturally fit within an entity.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .entities import (
    DocumentAssets,
    DocumentManifest,
    FigureAsset,
    SectionAsset,
    TableAsset,
)

if TYPE_CHECKING:
    pass


class ManifestGenerator:
    """
    Domain Service for generating document manifests.

    Responsible for creating the "map" of a document
    that allows AI Agents to navigate its structure.
    """

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

        Returns:
            Complete DocumentManifest
        """
        # Use provided tables (Docling) or parse from markdown
        if tables:
            parsed_tables = tables
        else:
            parsed_tables = self._parse_tables(markdown)

        # Parse sections from markdown
        sections = self._parse_sections(markdown)

        # Build TOC from sections
        toc = [s.title for s in sections if s.level <= 2]

        # Detect title
        title = self._detect_title(markdown)

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
                )
            )

        return tables

    def _parse_sections(self, markdown: str) -> list[SectionAsset]:
        """Parse markdown headers as sections."""
        sections = []
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

                # Generate section ID
                sec_id = f"sec_{re.sub(r'[^a-z0-9]', '_', title.lower())[:30]}"

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
        """Detect document title from first heading."""
        # Try first H1 heading
        match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
        if match:
            return match.group(1).strip()

        # Fallback: first non-empty line
        for line in markdown.split("\n"):
            line = line.strip()
            if line and not line.startswith("<!--"):
                return line[:100]

        return ""


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
