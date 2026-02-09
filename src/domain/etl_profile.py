"""
Domain Layer - ETL Profile

Configurable extraction profile for different journal/paper formats.
Each profile defines thresholds, patterns, and keywords that control
how the ETL pipeline detects headings, captions, and filters noise.

Architecture:
  - ETLProfile: Pure domain value object (dataclass, immutable)
  - ETLProfileRegistry: In-memory registry with built-in presets
  - JSON override: Load from JSON file to customize any profile field

Usage:
    from src.domain.etl_profile import ETLProfile, ETLProfileRegistry

    # Use default
    profile = ETLProfile.default()

    # Use preset
    profile = ETLProfileRegistry.get("arxiv")

    # Load from JSON (merges with default)
    profile = ETLProfile.from_json("profiles/nature.json")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FontThresholds:
    """Font size thresholds for heading detection (in points).

    Text with font_size > threshold is tagged as that heading level.
    """

    h1: float = 16.0   # > 16pt → # H1
    h2: float = 14.0   # > 14pt → ## H2
    h3: float = 12.0   # > 12pt → ### H3


@dataclass(frozen=True)
class FigureTableFilter:
    """Thresholds for filtering noise figures and tables."""

    min_figure_px: int = 50      # Skip figures smaller than this (width or height)
    min_table_rows: int = 1      # Skip tables with fewer data rows
    min_table_cols: int = 2      # Skip single-column "tables"
    max_caption_number: int = 999  # Reject captions like "Table 34733"
    min_caption_body_len: int = 10  # Minimum text after "Figure N."


@dataclass(frozen=True)
class ETLProfile:
    """
    Configurable ETL extraction profile.

    Controls all tunable parameters of the PDF extraction pipeline.
    Immutable value object — create a new instance for different settings.
    """

    # ── Identity ──────────────────────────────────────────────────────
    name: str = "default"
    description: str = "General-purpose profile for most PDF documents"

    # ── Font-size heading detection ───────────────────────────────────
    font_thresholds: FontThresholds = field(default_factory=FontThresholds)

    # Minimum length for heading text (filters "a", "b", "OPEN")
    min_heading_length: int = 3

    # ── Heading noise patterns (pdf_extractor) ────────────────────────
    # Regex patterns that should NEVER be treated as headings.
    # Each string is combined with | into a single compiled regex.
    heading_noise_patterns: tuple[str, ...] = (
        r"[a-z]$",             # single lowercase letter
        r"OPEN$",              # "OPEN" label
        r"www\.",              # URLs
        r"http",               # URLs
        r"\d+$",               # pure numbers
        r"[A-Z]{1,2}$",       # 1-2 uppercase letters
        r"arXiv:\S+",         # arXiv identifiers
        r"layers$",           # table column headers
        r"filters$",
        r"params$",
        r"output size$",
    )

    # ── Bold section detection (for double-column papers) ─────────────
    # Numbered section regex (matches "1. Intro", "3.1. Methods")
    numbered_section_pattern: str = r"^(?:[A-Z]?\d+\.(?:\d+\.)*)\s+\S"

    # Keywords that indicate a section heading even without numbers
    section_keywords: frozenset[str] = frozenset({
        "abstract", "introduction", "conclusion", "conclusions",
        "references", "acknowledgements", "acknowledgments",
        "appendix", "supplementary",
    })

    # ── Caption detection patterns ────────────────────────────────────
    table_caption_pattern: str = (
        r"(?:Table|TABLE|Tab\.?)\s+(\d+)\s*[.:,]?\s*(.*)"
    )
    figure_caption_pattern: str = (
        r"^\s*(?:Figure|FIGURE|Fig\.?)\s+(\d+)\s*[.:,]?\s*(.*)"
    )
    # Whether figure captions require line-start anchor (MULTILINE)
    figure_caption_require_line_start: bool = True

    # ── Figure/Table filters ──────────────────────────────────────────
    filters: FigureTableFilter = field(default_factory=FigureTableFilter)

    # ── Section noise patterns (services.py) ──────────────────────────
    # Noise section titles to ignore (combined into regex)
    section_noise_patterns: tuple[str, ...] = (
        r"layers",
        r"filters",
        r"ﬁlters",       # ligature variant
        r"params",
        r"output size",
        r"output map size",
        r"method",
        r"error",
        r"[a-z]",         # single lowercase letter
        r"\d+$",          # pure numbers
        r"[A-Z]{1,2}$",  # 1-2 uppercase letters
    )

    # Title noise patterns (arXiv stamps, etc.)
    title_noise_patterns: tuple[str, ...] = (
        r"arXiv:\S+",    # arXiv identifiers
        r"OPEN$",        # Noise label
        r"\d+$",         # Pure numbers
    )

    # TOC caption filter (remove Figure/Table entries from PDF TOC)
    toc_caption_pattern: str = (
        r"^(?:Figure|Fig\.?|Table|Tab\.?)\s+\d+"
    )

    # ── Compiled regex cache (not part of equality) ───────────────────

    def compile_heading_noise_re(self) -> re.Pattern:
        """Compile heading noise patterns into a single regex."""
        combined = "|".join(self.heading_noise_patterns)
        return re.compile(rf"^(?:{combined})", re.IGNORECASE)

    def compile_section_noise_re(self) -> re.Pattern:
        """Compile section noise patterns into a single regex."""
        combined = "|".join(self.section_noise_patterns)
        return re.compile(rf"^(?:{combined})$", re.IGNORECASE)

    def compile_title_noise_re(self) -> re.Pattern:
        """Compile title noise patterns into a single regex."""
        combined = "|".join(self.title_noise_patterns)
        return re.compile(rf"^(?:{combined})", re.IGNORECASE)

    def compile_toc_caption_re(self) -> re.Pattern:
        """Compile TOC caption filter pattern."""
        return re.compile(self.toc_caption_pattern, re.IGNORECASE)

    def compile_table_caption_re(self) -> re.Pattern:
        """Compile table caption detection pattern."""
        return re.compile(self.table_caption_pattern, re.IGNORECASE)

    def compile_figure_caption_re(self) -> re.Pattern:
        """Compile figure caption detection pattern."""
        flags = re.IGNORECASE
        if self.figure_caption_require_line_start:
            flags |= re.MULTILINE
        return re.compile(self.figure_caption_pattern, flags)

    def compile_numbered_section_re(self) -> re.Pattern:
        """Compile numbered section heading pattern."""
        return re.compile(self.numbered_section_pattern)

    # ── Factory methods ───────────────────────────────────────────────

    @classmethod
    def default(cls) -> ETLProfile:
        """Return the default general-purpose profile."""
        return cls()

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, base: ETLProfile | None = None) -> ETLProfile:
        """Create a profile from a dict, optionally merging with a base profile.

        Args:
            data: Dict with profile fields to override
            base: Base profile to inherit from (default: ETLProfile.default())

        Returns:
            New ETLProfile with merged settings
        """
        base = base or cls.default()

        # Start with base values
        kwargs: dict[str, Any] = {}

        # Simple scalar fields
        for key in (
            "name", "description", "min_heading_length",
            "numbered_section_pattern",
            "table_caption_pattern", "figure_caption_pattern",
            "figure_caption_require_line_start",
            "toc_caption_pattern",
        ):
            kwargs[key] = data.get(key, getattr(base, key))

        # FontThresholds
        if "font_thresholds" in data:
            ft_data = data["font_thresholds"]
            base_ft = base.font_thresholds
            kwargs["font_thresholds"] = FontThresholds(
                h1=ft_data.get("h1", base_ft.h1),
                h2=ft_data.get("h2", base_ft.h2),
                h3=ft_data.get("h3", base_ft.h3),
            )
        else:
            kwargs["font_thresholds"] = base.font_thresholds

        # FigureTableFilter
        if "filters" in data:
            f_data = data["filters"]
            base_f = base.filters
            kwargs["filters"] = FigureTableFilter(
                min_figure_px=f_data.get("min_figure_px", base_f.min_figure_px),
                min_table_rows=f_data.get("min_table_rows", base_f.min_table_rows),
                min_table_cols=f_data.get("min_table_cols", base_f.min_table_cols),
                max_caption_number=f_data.get("max_caption_number", base_f.max_caption_number),
                min_caption_body_len=f_data.get("min_caption_body_len", base_f.min_caption_body_len),
            )
        else:
            kwargs["filters"] = base.filters

        # Tuple fields (noise patterns)
        for key in (
            "heading_noise_patterns",
            "section_noise_patterns",
            "title_noise_patterns",
        ):
            if key in data:
                val = data[key]
                if isinstance(val, list):
                    kwargs[key] = tuple(val)
                else:
                    kwargs[key] = val
            else:
                kwargs[key] = getattr(base, key)

        # Frozenset fields
        if "section_keywords" in data:
            kw = data["section_keywords"]
            if isinstance(kw, (list, set)):
                kwargs["section_keywords"] = frozenset(kw)
            else:
                kwargs["section_keywords"] = kw
        else:
            kwargs["section_keywords"] = base.section_keywords

        return cls(**kwargs)

    @classmethod
    def from_json(cls, path: str | Path, *, base: ETLProfile | None = None) -> ETLProfile:
        """Load a profile from a JSON file, merging with base profile.

        Args:
            path: Path to JSON file
            base: Base profile to inherit from (default: ETLProfile.default())

        Returns:
            New ETLProfile with merged settings
        """
        json_path = Path(path)
        if not json_path.exists():
            raise FileNotFoundError(f"Profile JSON not found: {json_path}")

        data = json.loads(json_path.read_text(encoding="utf-8"))
        return cls.from_dict(data, base=base)

    def to_dict(self) -> dict[str, Any]:
        """Serialize profile to a JSON-compatible dict."""
        return {
            "name": self.name,
            "description": self.description,
            "font_thresholds": {
                "h1": self.font_thresholds.h1,
                "h2": self.font_thresholds.h2,
                "h3": self.font_thresholds.h3,
            },
            "min_heading_length": self.min_heading_length,
            "heading_noise_patterns": list(self.heading_noise_patterns),
            "numbered_section_pattern": self.numbered_section_pattern,
            "section_keywords": sorted(self.section_keywords),
            "table_caption_pattern": self.table_caption_pattern,
            "figure_caption_pattern": self.figure_caption_pattern,
            "figure_caption_require_line_start": self.figure_caption_require_line_start,
            "filters": {
                "min_figure_px": self.filters.min_figure_px,
                "min_table_rows": self.filters.min_table_rows,
                "min_table_cols": self.filters.min_table_cols,
                "max_caption_number": self.filters.max_caption_number,
                "min_caption_body_len": self.filters.min_caption_body_len,
            },
            "section_noise_patterns": list(self.section_noise_patterns),
            "title_noise_patterns": list(self.title_noise_patterns),
            "toc_caption_pattern": self.toc_caption_pattern,
        }

    def to_json(self, path: str | Path) -> None:
        """Save profile to a JSON file."""
        json_path = Path(path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class ETLProfileRegistry:
    """
    Registry of built-in ETL profiles.

    Provides preset profiles for common journal/paper formats,
    plus the ability to register custom profiles at runtime.
    """

    _profiles: dict[str, ETLProfile] = {}

    @classmethod
    def _ensure_builtins(cls) -> None:
        """Register built-in profiles if not already done."""
        if cls._profiles:
            return

        # ── Default (general purpose) ─────────────────────────────────
        cls._profiles["default"] = ETLProfile.default()

        # ── arXiv (double-column, no PDF TOC, numbered sections) ──────
        cls._profiles["arxiv"] = ETLProfile(
            name="arxiv",
            description="arXiv preprints: double-column, bold numbered sections, no PDF TOC",
            font_thresholds=FontThresholds(h1=16.0, h2=14.0, h3=12.0),
            heading_noise_patterns=(
                *ETLProfile.default().heading_noise_patterns,
                r"Ensemble\b",        # "Ensemble - nlnet" table entries
                r"Single\b",          # "Single - MIR-MRC" table entries
            ),
            section_keywords=frozenset({
                "abstract", "introduction", "conclusion", "conclusions",
                "references", "acknowledgements", "acknowledgments",
                "appendix", "supplementary", "related work",
            }),
        )

        # ── Nature / Scientific Reports ───────────────────────────────
        cls._profiles["nature"] = ETLProfile(
            name="nature",
            description="Nature/Scientific Reports: single-column, PDF TOC available, large figures",
            font_thresholds=FontThresholds(h1=18.0, h2=14.0, h3=12.0),
            filters=FigureTableFilter(
                min_figure_px=80,  # Nature has larger, high-quality figures
                min_table_rows=1,
                min_table_cols=2,
                max_caption_number=50,
                min_caption_body_len=15,
            ),
        )

        # ── IEEE (double-column, Roman numeral sections) ──────────────
        cls._profiles["ieee"] = ETLProfile(
            name="ieee",
            description="IEEE format: double-column, Roman numeral sections (I., II., etc.)",
            font_thresholds=FontThresholds(h1=14.0, h2=12.0, h3=10.0),
            numbered_section_pattern=r"^(?:[IVX]+\.(?:\d+\.)*|[A-Z]?\d+\.(?:\d+\.)*)\s+\S",
            section_keywords=frozenset({
                "abstract", "introduction", "conclusion", "conclusions",
                "references", "acknowledgment", "acknowledgement",
                "appendix",
            }),
        )

        # ── Elsevier (single-column, numbered sections) ───────────────
        cls._profiles["elsevier"] = ETLProfile(
            name="elsevier",
            description="Elsevier journals: single-column, numbered sections, highlights",
            font_thresholds=FontThresholds(h1=16.0, h2=13.0, h3=11.0),
            section_keywords=frozenset({
                "abstract", "introduction", "conclusion", "conclusions",
                "references", "acknowledgements",
                "appendix", "highlights", "graphical abstract",
            }),
        )

    @classmethod
    def get(cls, name: str) -> ETLProfile:
        """Get a profile by name.

        Args:
            name: Profile name (case-insensitive)

        Returns:
            ETLProfile instance

        Raises:
            KeyError: If profile not found
        """
        cls._ensure_builtins()
        key = name.lower()
        if key not in cls._profiles:
            available = ", ".join(sorted(cls._profiles.keys()))
            raise KeyError(f"Profile '{name}' not found. Available: {available}")
        return cls._profiles[key]

    @classmethod
    def register(cls, profile: ETLProfile) -> None:
        """Register a custom profile.

        Args:
            profile: ETLProfile instance with a unique name
        """
        cls._ensure_builtins()
        cls._profiles[profile.name.lower()] = profile

    @classmethod
    def list_profiles(cls) -> list[str]:
        """List all available profile names."""
        cls._ensure_builtins()
        return sorted(cls._profiles.keys())

    @classmethod
    def load_from_json(cls, path: str | Path) -> ETLProfile:
        """Load a profile from JSON, register it, and return it.

        The JSON can specify a "base" field to inherit from an existing profile.

        Args:
            path: Path to JSON file

        Returns:
            Loaded and registered ETLProfile
        """
        cls._ensure_builtins()
        json_path = Path(path)
        data = json.loads(json_path.read_text(encoding="utf-8"))

        # Check if inheriting from a base profile
        base_name = data.pop("base", "default")
        base = cls._profiles.get(base_name.lower(), ETLProfile.default())

        profile = ETLProfile.from_dict(data, base=base)
        cls.register(profile)
        return profile

    @classmethod
    def reset(cls) -> None:
        """Reset registry (mainly for testing)."""
        cls._profiles.clear()
