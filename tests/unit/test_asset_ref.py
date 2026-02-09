"""
Unit tests for AssetRef value object.
"""

import pytest

from src.domain.value_objects import AssetRef


class TestAssetRefCreation:
    """Test AssetRef factory methods."""

    def test_from_doc_asset_section(self):
        ref = AssetRef.from_doc_asset(
            source_type="section",
            doc_id="doc_test_abc123",
            asset_id="sec_methods",
            page=5,
            excerpt="dose was 5mg/kg",
        )
        assert ref.source_type == "section"
        assert ref.doc_id == "doc_test_abc123"
        assert ref.asset_id == "sec_methods"
        assert ref.page == 5
        assert ref.excerpt == "dose was 5mg/kg"

    def test_from_doc_asset_figure(self):
        ref = AssetRef.from_doc_asset(
            source_type="figure",
            doc_id="doc_paper_xyz789",
            asset_id="fig_01",
            page=12,
            label="Figure 1",
        )
        assert ref.source_type == "figure"
        assert ref.label == "Figure 1"

    def test_from_url(self):
        ref = AssetRef.from_url(
            url="https://doi.org/10.1234/test",
            label="Smith 2024",
            excerpt="Found significant results",
        )
        assert ref.source_type == "external"
        assert ref.url == "https://doi.org/10.1234/test"
        assert ref.label == "Smith 2024"

    def test_from_user_input(self):
        ref = AssetRef.from_user_input(
            excerpt="Patient reported 5mg daily",
            label="user observation",
        )
        assert ref.source_type == "user_input"
        assert ref.excerpt == "Patient reported 5mg daily"

    def test_from_kg_entity(self):
        ref = AssetRef.from_kg_entity(
            label="Remimazolam",
            excerpt="A short-acting benzodiazepine",
        )
        assert ref.source_type == "kg_entity"
        assert ref.label == "Remimazolam"

    def test_direct_construction(self):
        ref = AssetRef(
            source_type="table",
            doc_id="doc_test_001",
            asset_id="tbl_01",
            page=3,
        )
        assert ref.source_type == "table"
        assert ref.doc_id == "doc_test_001"


class TestAssetRefImmutability:
    """Test that AssetRef is frozen (immutable)."""

    def test_cannot_modify_fields(self):
        ref = AssetRef.from_user_input("test")
        with pytest.raises(AttributeError):
            ref.excerpt = "modified"  # type: ignore[misc]

    def test_cannot_modify_source_type(self):
        ref = AssetRef(source_type="section", doc_id="doc_x")
        with pytest.raises(AttributeError):
            ref.source_type = "figure"  # type: ignore[misc]


class TestAssetRefExcerptTruncation:
    """Test that excerpt is auto-truncated to 200 chars."""

    def test_short_excerpt_unchanged(self):
        ref = AssetRef(source_type="user_input", excerpt="short")
        assert ref.excerpt == "short"

    def test_long_excerpt_truncated(self):
        long_text = "x" * 300
        ref = AssetRef(source_type="user_input", excerpt=long_text)
        assert len(ref.excerpt) == 200

    def test_exactly_200_chars_unchanged(self):
        text = "a" * 200
        ref = AssetRef(source_type="user_input", excerpt=text)
        assert len(ref.excerpt) == 200


class TestAssetRefAccessPath:
    """Test access_path property for different source types."""

    def test_section_access_path(self):
        ref = AssetRef.from_doc_asset("section", "doc_abc", "sec_01")
        path = ref.access_path
        assert "fetch_document_asset" in path
        assert "doc_abc" in path
        assert "sec_01" in path

    def test_external_access_path(self):
        ref = AssetRef.from_url("https://example.com")
        assert ref.access_path == "https://example.com"

    def test_user_input_access_path(self):
        ref = AssetRef.from_user_input("test input")
        assert "[user_input]" in ref.access_path

    def test_kg_entity_access_path(self):
        ref = AssetRef.from_kg_entity("BRCA1")
        assert "consult_knowledge_graph" in ref.access_path


class TestAssetRefToShort:
    """Test to_short() for footnote display."""

    def test_with_label(self):
        ref = AssetRef.from_doc_asset("section", "doc_a", "sec_1", label="Table 3")
        assert ref.to_short() == "Table 3"

    def test_user_input_short(self):
        ref = AssetRef.from_user_input("Patient data from interview")
        short = ref.to_short()
        assert short.startswith("user:")

    def test_external_short(self):
        ref = AssetRef.from_url("https://doi.org/10.1234/very-long-url-here")
        short = ref.to_short()
        assert len(short) <= 60

    def test_doc_asset_short(self):
        ref = AssetRef.from_doc_asset("figure", "doc_abc", "fig_01", page=5)
        short = ref.to_short()
        assert "doc_abc" in short
        assert "fig_01" in short
        assert "p.5" in short


class TestAssetRefSerialization:
    """Test to_dict() and from_dict() round-trip."""

    def test_section_round_trip(self):
        original = AssetRef.from_doc_asset(
            "section", "doc_test", "sec_01", page=5, excerpt="test"
        )
        data = original.to_dict()
        restored = AssetRef.from_dict(data)
        assert restored == original

    def test_external_round_trip(self):
        original = AssetRef.from_url("https://example.com", "Example", "excerpt")
        data = original.to_dict()
        restored = AssetRef.from_dict(data)
        assert restored == original

    def test_user_input_round_trip(self):
        original = AssetRef.from_user_input("some input", "label")
        data = original.to_dict()
        restored = AssetRef.from_dict(data)
        assert restored == original

    def test_line_range_round_trip(self):
        original = AssetRef(
            source_type="section",
            doc_id="doc_x",
            asset_id="sec_1",
            line_range=(10, 20),
        )
        data = original.to_dict()
        assert data["line_range"] == [10, 20]
        restored = AssetRef.from_dict(data)
        assert restored.line_range == (10, 20)

    def test_minimal_dict(self):
        """Only non-empty fields are serialized."""
        ref = AssetRef(source_type="user_input", excerpt="test")
        data = ref.to_dict()
        assert "source_type" in data
        assert "excerpt" in data
        assert "doc_id" not in data  # empty string omitted
        assert "url" not in data
        assert "page" not in data

    def test_kg_entity_round_trip(self):
        original = AssetRef.from_kg_entity("BRCA1", "tumor suppressor gene")
        data = original.to_dict()
        restored = AssetRef.from_dict(data)
        assert restored == original
