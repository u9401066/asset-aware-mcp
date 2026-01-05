"""
Domain Layer - Chunking Strategies

Smart chunking for different document types and use cases.
Based on best practices from Unstructured, LangChain, and RAG-to-Riches.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class DocumentType(str, Enum):
    """Document type classification for optimal chunking."""

    GENERAL = "general"  # Default for most documents
    TECHNICAL = "technical"  # Papers, documentation, code
    SIMPLE = "simple"  # Plain text, notes
    LEGAL = "legal"  # Contracts, regulations
    MEDICAL = "medical"  # Clinical notes, research papers


@dataclass(frozen=True)
class ChunkConfig:
    """
    Immutable chunk configuration.

    Attributes:
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks
        min_chunk_size: Minimum chunk size (don't create tiny chunks)
        respect_sentences: Try to break at sentence boundaries
        respect_paragraphs: Try to break at paragraph boundaries
        include_metadata: Include source info in chunk
    """

    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_size: int = 100
    respect_sentences: bool = True
    respect_paragraphs: bool = True
    include_metadata: bool = True

    @classmethod
    def for_document_type(cls, doc_type: DocumentType) -> ChunkConfig:
        """
        Get optimized config for document type.

        Based on empirical best practices:
        - General: 1000/200 (balanced)
        - Technical: 1500/300 (larger context for code/equations)
        - Simple: 800/160 (faster processing)
        - Legal: 1200/400 (higher overlap for cross-references)
        - Medical: 1000/250 (moderate overlap for term consistency)
        """
        configs = {
            DocumentType.GENERAL: cls(chunk_size=1000, chunk_overlap=200),
            DocumentType.TECHNICAL: cls(chunk_size=1500, chunk_overlap=300),
            DocumentType.SIMPLE: cls(chunk_size=800, chunk_overlap=160),
            DocumentType.LEGAL: cls(chunk_size=1200, chunk_overlap=400),
            DocumentType.MEDICAL: cls(chunk_size=1000, chunk_overlap=250),
        }
        return configs.get(doc_type, cls())


@dataclass
class Chunk:
    """
    A document chunk with metadata.

    Attributes:
        text: The chunk content
        index: Chunk index in document
        start_char: Start position in original text
        end_char: End position in original text
        metadata: Additional metadata (page, section, etc.)
    """

    text: str
    index: int
    start_char: int
    end_char: int
    metadata: dict[str, str | int] = field(default_factory=dict)

    @property
    def size(self) -> int:
        """Character count of chunk."""
        return len(self.text)


class ChunkingStrategy(ABC):
    """Base class for chunking strategies."""

    @abstractmethod
    def chunk(self, text: str, config: ChunkConfig) -> list[Chunk]:
        """Split text into chunks."""
        ...


class BasicChunker(ChunkingStrategy):
    """
    Basic character-based chunking with overlap.

    Simple but effective for most use cases.
    """

    def chunk(self, text: str, config: ChunkConfig) -> list[Chunk]:
        """Split text into overlapping chunks."""
        chunks: list[Chunk] = []
        start = 0
        index = 0

        while start < len(text):
            # Calculate end position
            end = start + config.chunk_size

            # Don't exceed text length
            if end >= len(text):
                chunk_text = text[start:]
                if len(chunk_text) >= config.min_chunk_size:
                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            index=index,
                            start_char=start,
                            end_char=len(text),
                        )
                    )
                break

            chunk_text = text[start:end]

            # Find better break point if configured
            if config.respect_sentences:
                chunk_text = self._adjust_to_sentence(chunk_text, text, start, end)

            if len(chunk_text) >= config.min_chunk_size:
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        index=index,
                        start_char=start,
                        end_char=start + len(chunk_text),
                    )
                )
                index += 1

            # Move start with overlap
            start = start + len(chunk_text) - config.chunk_overlap
            if start >= len(text):
                break

        return chunks

    def _adjust_to_sentence(
        self, chunk_text: str, full_text: str, start: int, end: int
    ) -> str:
        """Adjust chunk to end at sentence boundary if possible."""
        # Look for sentence endings in the last 20% of chunk
        search_start = int(len(chunk_text) * 0.8)
        search_region = chunk_text[search_start:]

        # Find last sentence ending
        sentence_endings = [".。!?！？", "\n\n"]
        best_pos = -1

        for ending in sentence_endings[0]:
            pos = search_region.rfind(ending)
            if pos > best_pos:
                best_pos = pos

        if best_pos >= 0:
            return chunk_text[: search_start + best_pos + 1]

        return chunk_text


class SemanticChunker(ChunkingStrategy):
    """
    Semantic chunking that respects document structure.

    Chunks by:
    1. Headings (Markdown # or detected titles)
    2. Paragraphs
    3. Sentences
    4. Characters (fallback)
    """

    # Heading patterns (Markdown and common formats)
    HEADING_PATTERN = re.compile(
        r"^(?:"
        r"#{1,6}\s+.+|"  # Markdown headings
        r"[A-Z][A-Z\s]{5,50}$|"  # ALL CAPS lines
        r"\d+\.\s+[A-Z].{5,50}$"  # Numbered sections
        r")",
        re.MULTILINE,
    )

    # Paragraph separator
    PARA_SEPARATOR = re.compile(r"\n\s*\n")

    def chunk(self, text: str, config: ChunkConfig) -> list[Chunk]:
        """Split text by semantic boundaries."""
        chunks: list[Chunk] = []

        # First, split by headings
        sections = self._split_by_headings(text)

        chunk_index = 0
        for section in sections:
            section_text = str(section["text"])
            section_start = int(section["start"])
            section_end = int(section["end"])
            section_heading = str(section.get("heading", ""))

            # If section is small enough, keep as one chunk
            if len(section_text) <= config.chunk_size:
                if len(section_text) >= config.min_chunk_size:
                    chunks.append(
                        Chunk(
                            text=section_text,
                            index=chunk_index,
                            start_char=section_start,
                            end_char=section_end,
                            metadata={"heading": section_heading},
                        )
                    )
                    chunk_index += 1
            else:
                # Split large sections by paragraphs
                para_chunks = self._split_by_paragraphs(
                    section_text, section_start, config
                )

                # If paragraph splitting didn't work well, use basic chunking
                if len(para_chunks) == 1 and para_chunks[0].size > config.chunk_size:
                    basic_chunks = BasicChunker().chunk(section_text, config)
                    for bc in basic_chunks:
                        bc.index = chunk_index
                        bc.start_char += section_start
                        bc.end_char += section_start
                        bc.metadata["heading"] = section_heading
                        chunks.append(bc)
                        chunk_index += 1
                else:
                    for pc in para_chunks:
                        pc.index = chunk_index
                        pc.metadata["heading"] = section_heading
                        chunks.append(pc)
                        chunk_index += 1

        return chunks

    def _split_by_headings(self, text: str) -> list[dict[str, str | int]]:
        """Split text into sections by headings."""
        sections: list[dict[str, str | int]] = []

        matches = list(self.HEADING_PATTERN.finditer(text))

        if not matches:
            # No headings found, treat as single section
            return [{"text": text, "start": 0, "end": len(text), "heading": ""}]

        # Create sections between headings
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            sections.append(
                {
                    "text": text[start:end],
                    "start": start,
                    "end": end,
                    "heading": match.group().strip()[:50],
                }
            )

        # Don't forget text before first heading
        if matches[0].start() > 0:
            sections.insert(
                0,
                {
                    "text": text[: matches[0].start()],
                    "start": 0,
                    "end": matches[0].start(),
                    "heading": "",
                },
            )

        return sections

    def _split_by_paragraphs(
        self, text: str, offset: int, config: ChunkConfig
    ) -> list[Chunk]:
        """Split text by paragraphs, merging small ones."""
        paragraphs = self.PARA_SEPARATOR.split(text)
        chunks: list[Chunk] = []
        current_text = ""
        current_start = offset
        chunk_index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph exceeds limit, save current and start new
            if len(current_text) + len(para) + 2 > config.chunk_size:
                if len(current_text) >= config.min_chunk_size:
                    chunks.append(
                        Chunk(
                            text=current_text,
                            index=chunk_index,
                            start_char=current_start,
                            end_char=current_start + len(current_text),
                        )
                    )
                    chunk_index += 1

                # Handle overlap
                if config.chunk_overlap > 0 and current_text:
                    overlap_text = current_text[-config.chunk_overlap :]
                    current_text = overlap_text + "\n\n" + para
                    current_start = (
                        current_start + len(current_text) - len(overlap_text)
                    )
                else:
                    current_text = para
                    current_start += len(current_text) + 2
            else:
                if current_text:
                    current_text += "\n\n" + para
                else:
                    current_text = para

        # Don't forget last chunk
        if len(current_text) >= config.min_chunk_size:
            chunks.append(
                Chunk(
                    text=current_text,
                    index=chunk_index,
                    start_char=current_start,
                    end_char=current_start + len(current_text),
                )
            )

        return chunks


class PageAwareChunker(ChunkingStrategy):
    """
    Chunking that preserves page boundaries.

    Uses page markers (<!-- Page N -->) from PDF extraction.
    """

    PAGE_MARKER = re.compile(r"<!--\s*Page\s+(\d+)\s*-->")

    def chunk(self, text: str, config: ChunkConfig) -> list[Chunk]:
        """Split text respecting page boundaries."""
        # Find all page markers
        markers = list(self.PAGE_MARKER.finditer(text))

        if not markers:
            # No page markers, fall back to semantic chunking
            return SemanticChunker().chunk(text, config)

        chunks: list[Chunk] = []
        chunk_index = 0

        for i, marker in enumerate(markers):
            page_num = int(marker.group(1))
            start = marker.end()
            end = markers[i + 1].start() if i + 1 < len(markers) else len(text)

            page_text = text[start:end].strip()

            if len(page_text) <= config.chunk_size:
                # Page fits in one chunk
                if len(page_text) >= config.min_chunk_size:
                    chunks.append(
                        Chunk(
                            text=page_text,
                            index=chunk_index,
                            start_char=start,
                            end_char=end,
                            metadata={"page": page_num},
                        )
                    )
                    chunk_index += 1
            else:
                # Split large pages semantically
                semantic_chunks = SemanticChunker().chunk(page_text, config)
                for sc in semantic_chunks:
                    sc.index = chunk_index
                    sc.start_char += start
                    sc.end_char += start
                    sc.metadata["page"] = page_num
                    chunks.append(sc)
                    chunk_index += 1

        return chunks


# ============================================================================
# Utility Functions
# ============================================================================


def detect_document_type(text: str, filename: str = "") -> DocumentType:
    """
    Detect document type from content and filename.

    Args:
        text: Document text (first 5000 chars is enough)
        filename: Original filename for hints

    Returns:
        Detected DocumentType
    """
    text_sample = text[:5000].lower()
    filename_lower = filename.lower()

    # Check filename hints
    if any(ext in filename_lower for ext in [".md", ".txt", ".rst"]):
        return DocumentType.SIMPLE

    # Check content patterns
    medical_terms = [
        "patient",
        "diagnosis",
        "treatment",
        "clinical",
        "drug",
        "dose",
        "mg",
        "ml",
        "syndrome",
        "disease",
    ]
    if sum(1 for term in medical_terms if term in text_sample) >= 3:
        return DocumentType.MEDICAL

    technical_terms = [
        "algorithm",
        "implementation",
        "function",
        "class",
        "method",
        "api",
        "code",
        "parameter",
        "import",
        "def ",
    ]
    if sum(1 for term in technical_terms if term in text_sample) >= 3:
        return DocumentType.TECHNICAL

    legal_terms = [
        "hereby",
        "whereas",
        "agreement",
        "party",
        "clause",
        "section",
        "liability",
        "indemnify",
    ]
    if sum(1 for term in legal_terms if term in text_sample) >= 3:
        return DocumentType.LEGAL

    return DocumentType.GENERAL


def get_chunker(strategy: str = "semantic") -> ChunkingStrategy:
    """
    Get chunker by strategy name.

    Args:
        strategy: "basic", "semantic", or "page_aware"

    Returns:
        ChunkingStrategy instance
    """
    strategies: dict[str, type[ChunkingStrategy]] = {
        "basic": BasicChunker,
        "semantic": SemanticChunker,
        "page_aware": PageAwareChunker,
    }
    chunker_class = strategies.get(strategy, SemanticChunker)
    return chunker_class()


def smart_chunk(
    text: str,
    filename: str = "",
    strategy: str = "auto",
    custom_config: ChunkConfig | None = None,
) -> list[Chunk]:
    """
    Smart chunking with automatic configuration.

    Args:
        text: Text to chunk
        filename: Original filename (for type detection)
        strategy: "auto", "basic", "semantic", or "page_aware"
        custom_config: Override auto-detected config

    Returns:
        List of Chunks
    """
    # Detect document type
    doc_type = detect_document_type(text, filename)

    # Get config
    config = custom_config or ChunkConfig.for_document_type(doc_type)

    # Choose strategy
    if strategy == "auto":
        # Use page-aware for PDFs with markers, semantic otherwise
        if "<!-- Page" in text:
            strategy = "page_aware"
        else:
            strategy = "semantic"

    chunker = get_chunker(strategy)
    return chunker.chunk(text, config)
