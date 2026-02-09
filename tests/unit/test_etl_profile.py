"""Unit tests for ETLProfile and ETLProfileRegistry."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.domain.etl_profile import (
    ETLProfile,
    ETLProfileRegistry,
    FigureTableFilter,
    FontThresholds,
)


# ============================================================================
# FontThresholds
# ============================================================================


class TestFontThresholds:
    def test_defaults(self):
        ft = FontThresholds()
        assert ft.h1 == 16.0
        assert ft.h2 == 14.0
        assert ft.h3 == 12.0

    def test_custom(self):
        ft = FontThresholds(h1=18.0, h2=13.0, h3=10.0)
        assert ft.h1 == 18.0

    def test_frozen(self):
        ft = FontThresholds()
        with pytest.raises(AttributeError):
            ft.h1 = 20.0  # type: ignore


# ============================================================================
# FigureTableFilter
# ============================================================================


class TestFigureTableFilter:
    def test_defaults(self):
        f = FigureTableFilter()
        assert f.min_figure_px == 50
        assert f.min_table_rows == 1
        assert f.min_table_cols == 2
        assert f.max_caption_number == 999
        assert f.min_caption_body_len == 10


# ============================================================================
# ETLProfile
# ============================================================================


class TestETLProfile:
    def test_default_profile(self):
        p = ETLProfile.default()
        assert p.name == "default"
        assert isinstance(p.font_thresholds, FontThresholds)
        assert isinstance(p.filters, FigureTableFilter)
        assert p.min_heading_length == 3

    def test_frozen(self):
        p = ETLProfile.default()
        with pytest.raises(AttributeError):
            p.name = "modified"  # type: ignore

    def test_compile_heading_noise_re(self):
        p = ETLProfile.default()
        regex = p.compile_heading_noise_re()
        assert isinstance(regex, re.Pattern)
        assert regex.match("OPEN")
        assert regex.match("arXiv:1234.5678")
        assert regex.match("42")
        assert not regex.match("Introduction")

    def test_compile_section_noise_re(self):
        p = ETLProfile.default()
        regex = p.compile_section_noise_re()
        assert regex.match("layers")
        assert regex.match("params")
        assert not regex.match("Introduction")

    def test_compile_title_noise_re(self):
        p = ETLProfile.default()
        regex = p.compile_title_noise_re()
        assert regex.match("arXiv:2301.12345v2")
        assert regex.match("OPEN")
        assert not regex.match("Deep Learning for Medical Imaging")

    def test_compile_toc_caption_re(self):
        p = ETLProfile.default()
        regex = p.compile_toc_caption_re()
        assert regex.match("Figure 1")
        assert regex.match("Table 3. Results")
        assert not regex.match("Introduction")

    def test_compile_table_caption_re(self):
        p = ETLProfile.default()
        regex = p.compile_table_caption_re()
        m = regex.search("Table 1. Comparison of methods")
        assert m
        assert m.group(1) == "1"

    def test_compile_figure_caption_re(self):
        p = ETLProfile.default()
        regex = p.compile_figure_caption_re()
        m = regex.search("Figure 3. Architecture overview")
        assert m
        assert m.group(1) == "3"

    def test_compile_numbered_section_re(self):
        p = ETLProfile.default()
        regex = p.compile_numbered_section_re()
        assert regex.match("1. Introduction")
        assert regex.match("3.1. Methods")
        assert regex.match("A1. Appendix")
        assert not regex.match("Just text")

    def test_to_dict_roundtrip(self):
        p = ETLProfile.default()
        d = p.to_dict()
        assert d["name"] == "default"
        assert d["font_thresholds"]["h1"] == 16.0
        assert "heading_noise_patterns" in d
        assert isinstance(d["section_keywords"], list)

    def test_from_dict_override(self):
        p = ETLProfile.from_dict({
            "name": "custom",
            "min_heading_length": 5,
            "font_thresholds": {"h1": 20.0},
        })
        assert p.name == "custom"
        assert p.min_heading_length == 5
        assert p.font_thresholds.h1 == 20.0
        # Inherited from default
        assert p.font_thresholds.h2 == 14.0
        assert p.filters.min_figure_px == 50

    def test_from_dict_with_base(self):
        base = ETLProfile(
            name="base",
            min_heading_length=10,
            font_thresholds=FontThresholds(h1=20.0, h2=18.0, h3=16.0),
        )
        p = ETLProfile.from_dict({"name": "child"}, base=base)
        assert p.name == "child"
        assert p.min_heading_length == 10  # Inherited from base
        assert p.font_thresholds.h1 == 20.0

    def test_from_json(self, tmp_path: Path):
        data = {
            "name": "test_json",
            "min_heading_length": 7,
            "filters": {"min_figure_px": 100},
        }
        json_path = tmp_path / "test.json"
        json_path.write_text(json.dumps(data))

        p = ETLProfile.from_json(json_path)
        assert p.name == "test_json"
        assert p.min_heading_length == 7
        assert p.filters.min_figure_px == 100
        # Default inherited
        assert p.filters.min_table_cols == 2

    def test_from_json_not_found(self):
        with pytest.raises(FileNotFoundError):
            ETLProfile.from_json("/nonexistent/path.json")

    def test_to_json(self, tmp_path: Path):
        p = ETLProfile.default()
        out = tmp_path / "out.json"
        p.to_json(out)
        assert out.exists()
        loaded = json.loads(out.read_text())
        assert loaded["name"] == "default"

    def test_section_keywords_frozenset(self):
        p = ETLProfile.from_dict({
            "section_keywords": ["abstract", "introduction", "custom"],
        })
        assert "custom" in p.section_keywords
        assert isinstance(p.section_keywords, frozenset)


# ============================================================================
# ETLProfileRegistry
# ============================================================================


class TestETLProfileRegistry:
    def setup_method(self):
        """Reset registry before each test."""
        ETLProfileRegistry.reset()

    def test_builtins_available(self):
        names = ETLProfileRegistry.list_profiles()
        assert "default" in names
        assert "arxiv" in names
        assert "nature" in names
        assert "ieee" in names
        assert "elsevier" in names

    def test_get_default(self):
        p = ETLProfileRegistry.get("default")
        assert p.name == "default"

    def test_get_arxiv(self):
        p = ETLProfileRegistry.get("arxiv")
        assert p.name == "arxiv"
        assert "related work" in p.section_keywords

    def test_get_nature(self):
        p = ETLProfileRegistry.get("nature")
        assert p.font_thresholds.h1 == 18.0
        assert p.filters.min_figure_px == 80

    def test_get_ieee(self):
        p = ETLProfileRegistry.get("ieee")
        # IEEE profile uses Roman numeral section patterns
        regex = p.compile_numbered_section_re()
        assert regex.match("I. Introduction")
        assert regex.match("II. Methods")

    def test_get_case_insensitive(self):
        p = ETLProfileRegistry.get("ArXiv")
        assert p.name == "arxiv"

    def test_get_not_found(self):
        with pytest.raises(KeyError, match="not found"):
            ETLProfileRegistry.get("nonexistent")

    def test_register_custom(self):
        custom = ETLProfile(name="my_journal", description="Custom")
        ETLProfileRegistry.register(custom)
        p = ETLProfileRegistry.get("my_journal")
        assert p.description == "Custom"

    def test_load_from_json(self, tmp_path: Path):
        data = {
            "base": "arxiv",
            "name": "my_arxiv",
            "description": "Custom arXiv variant",
            "min_heading_length": 5,
        }
        json_path = tmp_path / "my_arxiv.json"
        json_path.write_text(json.dumps(data))

        p = ETLProfileRegistry.load_from_json(json_path)
        assert p.name == "my_arxiv"
        assert p.min_heading_length == 5
        # Inherited from arxiv base
        assert "related work" in p.section_keywords
        # Registered in registry
        assert "my_arxiv" in ETLProfileRegistry.list_profiles()

    def test_reset(self):
        ETLProfileRegistry.get("default")  # Ensure builtins loaded
        ETLProfileRegistry.reset()
        # After reset, builtins will be re-loaded on next access
        assert ETLProfileRegistry.list_profiles()  # Should re-initialize


# ============================================================================
# Integration: Profile → Regex consistency
# ============================================================================


class TestProfileRegexConsistency:
    """Verify that all profile presets produce valid regexes."""

    def test_all_presets_compile(self):
        for name in ETLProfileRegistry.list_profiles():
            p = ETLProfileRegistry.get(name)
            # All compile methods should succeed
            p.compile_heading_noise_re()
            p.compile_section_noise_re()
            p.compile_title_noise_re()
            p.compile_toc_caption_re()
            p.compile_table_caption_re()
            p.compile_figure_caption_re()
            p.compile_numbered_section_re()

    def test_default_matches_original_constants(self):
        """Verify that default profile matches the original hardcoded constants."""
        p = ETLProfile.default()

        # Heading noise: should match what was _HEADING_NOISE_RE
        h = p.compile_heading_noise_re()
        assert h.match("a")          # single lowercase
        assert h.match("OPEN")
        assert h.match("www.example.com")
        assert h.match("http://x")
        assert h.match("42")
        assert h.match("AB")         # 1-2 uppercase
        assert h.match("arXiv:1234.5678v1")
        assert h.match("layers")
        assert h.match("filters")
        assert h.match("params")
        assert h.match("output size")
        assert not h.match("Introduction")
        assert not h.match("Deep Residual Learning")
