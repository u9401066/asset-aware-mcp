"""
Unit tests for CellCitation, ChangeEntry, TableChangeLog, TableTemplate.
"""

from datetime import datetime

from src.domain.table_entities import (
    CellCitation,
    ChangeEntry,
    ColumnDef,
    TableChangeLog,
    TableContext,
    TableTemplate,
)
from src.domain.value_objects import AssetRef

# ============================================================================
# CellCitation Tests
# ============================================================================


class TestCellCitation:
    """Test CellCitation dataclass."""

    def test_create_empty(self):
        cite = CellCitation()
        assert cite.refs == []
        assert cite.confidence is None
        assert cite.notes == ""

    def test_create_with_refs(self):
        ref = AssetRef.from_doc_asset("section", "doc_a", "sec_01", excerpt="test")
        cite = CellCitation(refs=[ref], confidence=0.9, notes="High quality source")
        assert len(cite.refs) == 1
        assert cite.confidence == 0.9

    def test_add_ref(self):
        cite = CellCitation()
        ref = AssetRef.from_user_input("oral report")
        cite.add_ref(ref)
        assert len(cite.refs) == 1
        assert cite.refs[0].source_type == "user_input"

    def test_remove_ref(self):
        ref1 = AssetRef.from_user_input("a")
        ref2 = AssetRef.from_user_input("b")
        cite = CellCitation(refs=[ref1, ref2])

        removed = cite.remove_ref(0)
        assert removed == ref1
        assert len(cite.refs) == 1
        assert cite.refs[0] == ref2

    def test_remove_ref_invalid_index(self):
        cite = CellCitation()
        assert cite.remove_ref(0) is None
        assert cite.remove_ref(-1) is None

    def test_to_footnote(self):
        refs = [AssetRef.from_user_input(f"ref{i}") for i in range(3)]
        cite = CellCitation(refs=refs)
        assert cite.to_footnote() == "[1][2][3]"
        assert cite.to_footnote(start_index=5) == "[5][6][7]"

    def test_to_footnote_empty(self):
        cite = CellCitation()
        assert cite.to_footnote() == ""

    def test_serialization_round_trip(self):
        ref = AssetRef.from_doc_asset("section", "doc_a", "sec_01")
        original = CellCitation(refs=[ref], confidence=0.85, notes="verified")
        data = original.to_dict()
        restored = CellCitation.from_dict(data)
        assert len(restored.refs) == 1
        assert restored.confidence == 0.85
        assert restored.notes == "verified"

    def test_serialization_minimal(self):
        """Empty citation serializes cleanly."""
        cite = CellCitation()
        data = cite.to_dict()
        assert data == {"refs": []}
        restored = CellCitation.from_dict(data)
        assert restored.refs == []
        assert restored.confidence is None
        assert restored.notes == ""


# ============================================================================
# ChangeEntry Tests
# ============================================================================


class TestChangeEntry:
    """Test ChangeEntry dataclass."""

    def test_create_basic(self):
        entry = ChangeEntry(
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            operation="update_cell",
            target="row:0/col:Drug",
            old_value="Propofol",
            new_value="Remimazolam",
        )
        assert entry.operation == "update_cell"
        assert entry.target == "row:0/col:Drug"

    def test_create_with_citations(self):
        ref = AssetRef.from_doc_asset("section", "doc_a", "sec_results")
        entry = ChangeEntry(
            timestamp=datetime.now(),
            operation="add_rows",
            target="table",
            new_value=[{"Drug": "Test"}],
            citations=[ref],
        )
        assert len(entry.citations) == 1

    def test_serialization_round_trip(self):
        ref = AssetRef.from_url("https://example.com")
        original = ChangeEntry(
            timestamp=datetime(2025, 6, 15, 10, 30, 0),
            operation="delete_row",
            target="row:2",
            old_value={"Drug": "X", "Dose": 1.0},
            citations=[ref],
        )
        data = original.to_dict()
        restored = ChangeEntry.from_dict(data)
        assert restored.operation == "delete_row"
        assert restored.target == "row:2"
        assert restored.old_value == {"Drug": "X", "Dose": 1.0}
        assert restored.timestamp == datetime(2025, 6, 15, 10, 30, 0)
        assert len(restored.citations) == 1

    def test_serialization_minimal(self):
        entry = ChangeEntry(
            timestamp=datetime(2025, 1, 1),
            operation="create",
            target="table",
        )
        data = entry.to_dict()
        assert "old_value" not in data
        assert "new_value" not in data
        assert "citations" not in data


# ============================================================================
# TableChangeLog Tests
# ============================================================================


class TestTableChangeLog:
    """Test TableChangeLog dataclass."""

    def _make_entry(self, op: str, target: str, **kwargs) -> ChangeEntry:
        return ChangeEntry(
            timestamp=datetime.now(),
            operation=op,
            target=target,
            **kwargs,
        )

    def test_create_empty(self):
        log = TableChangeLog(table_id="tbl_001")
        assert log.table_id == "tbl_001"
        assert log.entries == []

    def test_add_entry(self):
        log = TableChangeLog(table_id="tbl_001")
        entry = self._make_entry("create", "table")
        log.add(entry)
        assert len(log.entries) == 1

    def test_get_recent(self):
        log = TableChangeLog(table_id="tbl_001")
        for i in range(30):
            log.add(self._make_entry("update_cell", f"row:{i}/col:Drug"))
        recent = log.get_recent(5)
        assert len(recent) == 5
        assert recent[0].target == "row:25/col:Drug"

    def test_get_recent_default(self):
        log = TableChangeLog(table_id="tbl_001")
        for i in range(5):
            log.add(self._make_entry("update_cell", f"row:{i}/col:Drug"))
        recent = log.get_recent()
        assert len(recent) == 5

    def test_get_by_cell(self):
        log = TableChangeLog(table_id="tbl_001")
        log.add(self._make_entry("update_cell", "row:0/col:Drug"))
        log.add(self._make_entry("update_cell", "row:0/col:Dose"))
        log.add(self._make_entry("update_cell", "row:1/col:Drug"))
        log.add(self._make_entry("update_cell", "row:0/col:Drug"))

        history = log.get_by_cell(0, "Drug")
        assert len(history) == 2

    def test_get_by_row(self):
        log = TableChangeLog(table_id="tbl_001")
        log.add(self._make_entry("update_cell", "row:0/col:Drug"))
        log.add(self._make_entry("update_cell", "row:0/col:Dose"))
        log.add(self._make_entry("update_cell", "row:1/col:Drug"))

        history = log.get_by_row(0)
        assert len(history) == 2

    def test_serialization_round_trip(self):
        log = TableChangeLog(table_id="tbl_test")
        log.add(self._make_entry("create", "table"))
        log.add(self._make_entry("add_rows", "table", new_value=[{"Drug": "A"}]))

        data = log.to_dict()
        restored = TableChangeLog.from_dict(data)
        assert restored.table_id == "tbl_test"
        assert len(restored.entries) == 2


# ============================================================================
# TableContext Citation Integration Tests
# ============================================================================


class TestTableContextCitations:
    """Test citation functionality on TableContext."""

    def _make_context(self) -> TableContext:
        return TableContext(
            id="tbl_test",
            intent="comparison",
            title="Test Table",
            columns=[
                ColumnDef(name="Drug", type="text"),
                ColumnDef(name="Dose", type="number"),
            ],
            rows=[
                {"Drug": "Remimazolam", "Dose": 0.2},
                {"Drug": "Propofol", "Dose": 2.0},
            ],
        )

    def test_set_and_get_citation(self):
        ctx = self._make_context()
        ref = AssetRef.from_doc_asset("section", "doc_a", "sec_01")
        cite = CellCitation(refs=[ref], confidence=0.9)

        ctx.set_citation(0, "Drug", cite)
        result = ctx.get_citation(0, "Drug")
        assert result is not None
        assert result.confidence == 0.9

    def test_get_citation_nonexistent(self):
        ctx = self._make_context()
        assert ctx.get_citation(0, "Drug") is None

    def test_remove_citation(self):
        ctx = self._make_context()
        cite = CellCitation(refs=[AssetRef.from_user_input("test")])
        ctx.set_citation(0, "Drug", cite)
        assert ctx.remove_citation(0, "Drug") is True
        assert ctx.get_citation(0, "Drug") is None

    def test_remove_citation_nonexistent(self):
        ctx = self._make_context()
        assert ctx.remove_citation(0, "Drug") is False

    def test_get_row_citations(self):
        ctx = self._make_context()
        ctx.set_citation(0, "Drug", CellCitation(refs=[AssetRef.from_user_input("a")]))
        ctx.set_citation(0, "Dose", CellCitation(refs=[AssetRef.from_user_input("b")]))
        ctx.set_citation(1, "Drug", CellCitation(refs=[AssetRef.from_user_input("c")]))

        row0 = ctx.get_row_citations(0)
        assert len(row0) == 2
        assert "Drug" in row0
        assert "Dose" in row0

    def test_change_log_auto_init(self):
        ctx = self._make_context()
        assert ctx.change_log is not None
        assert ctx.change_log.table_id == "tbl_test"


# ============================================================================
# TableContext Schema Evolution Tests
# ============================================================================


class TestTableContextSchemaEvolution:
    """Test add_column, remove_column, rename_column."""

    def _make_context(self) -> TableContext:
        return TableContext(
            id="tbl_test",
            intent="comparison",
            title="Test Table",
            columns=[
                ColumnDef(name="Drug", type="text"),
                ColumnDef(name="Dose", type="number"),
            ],
            rows=[
                {"Drug": "A", "Dose": 1.0},
                {"Drug": "B", "Dose": 2.0},
            ],
        )

    def test_add_column(self):
        ctx = self._make_context()
        ctx.add_column(ColumnDef(name="Route", type="text"), default_value="IV")
        assert len(ctx.columns) == 3
        assert ctx.rows[0]["Route"] == "IV"
        assert ctx.rows[1]["Route"] == "IV"

    def test_add_column_none_default(self):
        ctx = self._make_context()
        ctx.add_column(ColumnDef(name="Notes", type="text", required=False))
        assert ctx.rows[0]["Notes"] is None

    def test_remove_column(self):
        ctx = self._make_context()
        assert ctx.remove_column("Dose") is True
        assert len(ctx.columns) == 1
        assert "Dose" not in ctx.rows[0]

    def test_remove_column_with_citations(self):
        ctx = self._make_context()
        ctx.set_citation(0, "Dose", CellCitation(refs=[AssetRef.from_user_input("x")]))
        ctx.set_citation(1, "Dose", CellCitation(refs=[AssetRef.from_user_input("y")]))

        ctx.remove_column("Dose")
        assert ctx.get_citation(0, "Dose") is None
        assert ctx.get_citation(1, "Dose") is None

    def test_remove_column_nonexistent(self):
        ctx = self._make_context()
        assert ctx.remove_column("NotExist") is False

    def test_rename_column(self):
        ctx = self._make_context()
        assert ctx.rename_column("Drug", "Medication") is True
        assert ctx.columns[0].name == "Medication"
        assert ctx.rows[0]["Medication"] == "A"
        assert "Drug" not in ctx.rows[0]

    def test_rename_column_with_citations(self):
        ctx = self._make_context()
        cite = CellCitation(refs=[AssetRef.from_user_input("ref")])
        ctx.set_citation(0, "Drug", cite)

        ctx.rename_column("Drug", "Medication")
        assert ctx.get_citation(0, "Medication") is not None
        assert ctx.get_citation(0, "Drug") is None

    def test_rename_column_nonexistent(self):
        ctx = self._make_context()
        assert ctx.rename_column("NotExist", "New") is False

    def test_get_row(self):
        ctx = self._make_context()
        row = ctx.get_row(0)
        assert row is not None
        assert row["Drug"] == "A"

    def test_get_row_out_of_range(self):
        ctx = self._make_context()
        assert ctx.get_row(99) is None

    def test_get_cell(self):
        ctx = self._make_context()
        assert ctx.get_cell(0, "Drug") == "A"
        assert ctx.get_cell(0, "Dose") == 1.0

    def test_get_cell_out_of_range(self):
        ctx = self._make_context()
        assert ctx.get_cell(99, "Drug") is None

    def test_column_names(self):
        ctx = self._make_context()
        assert ctx.column_names == ["Drug", "Dose"]


# ============================================================================
# TableTemplate Tests
# ============================================================================


class TestTableTemplate:
    """Test TableTemplate dataclass."""

    def test_create_template(self):
        tpl = TableTemplate(
            name="drug_comparison",
            title="Drug Comparison Table",
            intent="comparison",
            description="Compare drugs side by side",
            columns=[
                ColumnDef(name="Drug", type="text"),
                ColumnDef(name="Dose", type="number"),
                ColumnDef(name="Route", type="enum", enum_values=["IV", "IM", "PO"]),
            ],
        )
        assert tpl.name == "drug_comparison"
        assert len(tpl.columns) == 3

    def test_to_create_params(self):
        tpl = TableTemplate(
            name="test",
            title="Original Title",
            intent="comparison",
            columns=[ColumnDef(name="Drug", type="text")],
        )
        params = tpl.to_create_params()
        assert params["title"] == "Original Title"
        assert params["intent"] == "comparison"
        assert len(params["columns"]) == 1

    def test_to_create_params_with_override(self):
        tpl = TableTemplate(
            name="test",
            title="Original",
            intent="summary",
            columns=[ColumnDef(name="Drug", type="text")],
        )
        params = tpl.to_create_params(title_override="Custom Title")
        assert params["title"] == "Custom Title"

    def test_serialization_round_trip(self):
        original = TableTemplate(
            name="drug_compare",
            title="Drug Comparison",
            intent="comparison",
            description="Systematic drug comparison",
            columns=[
                ColumnDef(name="Drug", type="text"),
                ColumnDef(name="Dose", type="number"),
                ColumnDef(
                    name="Route",
                    type="enum",
                    required=False,
                    enum_values=["IV", "IM"],
                ),
            ],
        )
        data = original.to_dict()
        restored = TableTemplate.from_dict(data)
        assert restored.name == original.name
        assert restored.title == original.title
        assert restored.intent == original.intent
        assert restored.description == original.description
        assert len(restored.columns) == 3
        assert restored.columns[2].enum_values == ["IV", "IM"]
        assert restored.columns[2].required is False
