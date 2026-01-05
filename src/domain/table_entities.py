"""
Domain Layer - Table Entities

Entities and value objects for the A2T (Anything to Table) module.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass
class ColumnDef:
    """Definition of a table column."""

    name: str
    type: Literal["text", "number", "date", "enum", "url"]
    required: bool = True
    enum_values: list[str] | None = None  # Only used when type="enum"


@dataclass
class TableDraft:
    """
    Draft state for table work-in-progress.
    Allows resumption after conversation interruption.
    """

    table_id: str | None = None  # None if table not yet created
    intent: Literal["comparison", "citation", "summary"] | None = None
    title: str = ""
    proposed_columns: list[dict[str, Any]] = field(default_factory=list)
    extraction_plan: list[str] = field(default_factory=list)  # What to extract
    source_doc_ids: list[str] = field(default_factory=list)
    source_sections: list[str] = field(default_factory=list)  # Section IDs to use
    pending_rows: list[dict[str, Any]] = field(default_factory=list)  # Not yet added
    notes: str = ""  # Agent's working notes
    last_updated: datetime = field(default_factory=datetime.now)

    def estimate_tokens(self) -> int:
        """Estimate token count for this draft."""
        import json

        content = json.dumps(
            {
                "title": self.title,
                "columns": self.proposed_columns,
                "plan": self.extraction_plan,
                "pending": self.pending_rows,
                "notes": self.notes,
            },
            ensure_ascii=False,
        )
        # Rough estimate: 1 token ≈ 4 characters for mixed content
        return len(content) // 4


@dataclass
class TableSchema:
    """
    Proposed table schema before creation.
    Used for the "think before create" pattern.
    """

    title: str
    intent: Literal["comparison", "citation", "summary"]
    columns: list[ColumnDef]
    rationale: str  # Why this schema was chosen
    source_hints: list[str]  # Where to find data for each column
    estimated_rows: int = 0

    def to_create_params(self) -> dict[str, Any]:
        """Convert to parameters for create_table."""
        return {
            "intent": self.intent,
            "title": self.title,
            "columns": [
                {"name": c.name, "type": c.type, "required": c.required}
                for c in self.columns
            ],
        }


@dataclass
class TableContext:
    """
    Context for a table being constructed.
    Stored in memory for the MVP.
    """

    id: str
    intent: Literal["comparison", "citation", "summary"]
    title: str
    columns: list[ColumnDef]
    rows: list[dict[str, Any]] = field(default_factory=list)
    source_description: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def row_count(self) -> int:
        """Return the number of rows in the table."""
        return len(self.rows)

    def estimate_tokens(self) -> int:
        """Estimate token count for this table's content."""
        import json

        content = json.dumps(self.rows, ensure_ascii=False)
        # Add header tokens
        header_tokens = sum(len(c.name) for c in self.columns) // 4
        return len(content) // 4 + header_tokens

    def validate_row(self, row: dict[str, Any]) -> list[str]:
        """
        Validate a row against the column definitions.
        Returns a list of error messages.
        """
        errors = []
        col_names = {col.name for col in self.columns}

        # Check for unknown columns
        for key in row.keys():
            if key not in col_names:
                errors.append(f"Unknown column: '{key}'")

        # Check each column definition
        for col in self.columns:
            val = row.get(col.name)

            # Check required
            if col.required and val is None:
                errors.append(f"Missing required column: '{col.name}'")
                continue

            if val is None:
                continue

            # Check type
            if col.type == "number":
                if not isinstance(val, int | float):
                    errors.append(
                        f"Column '{col.name}' must be a number, got {type(val).__name__}"
                    )
            elif col.type == "enum":
                if col.enum_values and val not in col.enum_values:
                    errors.append(
                        f"Invalid value for enum column '{col.name}': '{val}'. Allowed: {col.enum_values}"
                    )
            # Basic URL validation could be added here if needed

        return errors
