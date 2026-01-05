"""
Application Layer - Table Service

Orchestrates table creation, data accumulation, and rendering.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Literal

from src.domain.table_entities import ColumnDef, TableContext, TableDraft
from src.infrastructure.config import settings
from src.infrastructure.excel_renderer import ExcelRenderer


class TableService:
    """Service for managing A2T (Anything to Table) workflows with persistence."""

    def __init__(self) -> None:
        self.storage_dir = settings.table_output_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.draft_dir = self.storage_dir / "drafts"
        self.draft_dir.mkdir(parents=True, exist_ok=True)
        # In-memory cache
        self._tables: dict[str, TableContext] = {}
        self._drafts: dict[str, TableDraft] = {}
        self._excel_renderer = ExcelRenderer(self.storage_dir)
        self._load_existing_tables()
        self._load_existing_drafts()

    def _load_existing_tables(self) -> None:
        """Load table metadata from disk on startup."""
        for json_file in self.storage_dir.glob("*.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                    # Reconstruct TableContext
                    col_defs = [ColumnDef(**c) for c in data["columns"]]
                    context = TableContext(
                        id=data["id"],
                        intent=data["intent"],
                        title=data["title"],
                        columns=col_defs,
                        rows=data["rows"],
                        source_description=data.get("source_description", ""),
                        created_at=data.get("created_at", ""),
                    )
                    self._tables[context.id] = context
            except Exception:
                continue

    def _save_table(self, context: TableContext) -> None:
        """Persist table state to JSON and Markdown."""
        # Save JSON state
        json_path = self.storage_dir / f"{context.id}.json"
        state = {
            "id": context.id,
            "intent": context.intent,
            "title": context.title,
            "columns": [
                {
                    "name": c.name,
                    "type": c.type,
                    "required": c.required,
                    "enum_values": c.enum_values,
                }
                for c in context.columns
            ],
            "rows": context.rows,
            "source_description": context.source_description,
            "created_at": str(context.created_at)
            if isinstance(context.created_at, datetime)
            else context.created_at,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        # Save Markdown preview
        md_path = self.storage_dir / f"{context.id}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self.preview_table(context.id, limit=1000))

    def create_table(
        self,
        intent: Literal["comparison", "citation", "summary"],
        title: str,
        columns: list[dict[str, Any]],
        source_description: str = "",
    ) -> str:
        """Create a new table context and persist it."""
        table_id = f"tbl_{uuid.uuid4().hex[:8]}"

        col_defs = [
            ColumnDef(
                name=col["name"],
                type=col["type"],
                required=col.get("required", True),
                enum_values=col.get("enum_values"),
            )
            for col in columns
        ]

        context = TableContext(
            id=table_id,
            intent=intent,
            title=title,
            columns=col_defs,
            source_description=source_description,
        )

        self._tables[table_id] = context
        self._save_table(context)
        return table_id

    def add_rows(self, table_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Add rows to an existing table and update persistence."""
        if table_id not in self._tables:
            raise ValueError(f"Table not found: {table_id}")

        context = self._tables[table_id]
        added_count = 0
        errors = []

        for i, row in enumerate(rows):
            row_errors = context.validate_row(row)
            if row_errors:
                errors.append({"row_index": i, "errors": row_errors})
            else:
                context.rows.append(row)
                added_count += 1

        if added_count > 0:
            self._save_table(context)

        return {
            "success": added_count > 0,
            "added": added_count,
            "total_rows": context.row_count,
            "errors": errors if errors else None,
        }

    def update_row(
        self, table_id: str, index: int, row: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an existing row by index."""
        if table_id not in self._tables:
            raise ValueError(f"Table not found: {table_id}")

        context = self._tables[table_id]
        if index < 0 or index >= len(context.rows):
            raise ValueError(f"Invalid row index: {index}")

        row_errors = context.validate_row(row)
        if row_errors:
            return {"success": False, "errors": row_errors}

        context.rows[index] = row
        self._save_table(context)
        return {"success": True}

    def delete_row(self, table_id: str, index: int) -> dict[str, Any]:
        """Delete a row by index."""
        if table_id not in self._tables:
            raise ValueError(f"Table not found: {table_id}")

        context = self._tables[table_id]
        if index < 0 or index >= len(context.rows):
            raise ValueError(f"Invalid row index: {index}")

        context.rows.pop(index)
        self._save_table(context)
        return {"success": True, "total_rows": context.row_count}

    def delete_table(self, table_id: str) -> bool:
        """Delete a table and its files."""
        if table_id in self._tables:
            del self._tables[table_id]
            # Delete files
            for ext in [".json", ".md", ".xlsx"]:
                path = self.storage_dir / f"{table_id}{ext}"
                if path.exists():
                    path.unlink()
            return True
        return False

    def list_tables(self) -> list[dict[str, Any]]:
        """List all available tables."""
        return [
            {
                "id": t.id,
                "title": t.title,
                "intent": t.intent,
                "rows": t.row_count,
                "created_at": str(t.created_at),
            }
            for t in self._tables.values()
        ]

    def update_cell(
        self, table_id: str, row_index: int, column_name: str, value: Any
    ) -> dict[str, Any]:
        """Update a single cell in the table."""
        if table_id not in self._tables:
            raise ValueError(f"Table not found: {table_id}")

        context = self._tables[table_id]
        if row_index < 0 or row_index >= len(context.rows):
            raise ValueError(f"Invalid row index: {row_index}")

        # Verify column exists
        col_names = {col.name for col in context.columns}
        if column_name not in col_names:
            raise ValueError(f"Unknown column: '{column_name}'")

        # Update the cell
        old_value = context.rows[row_index].get(column_name)
        context.rows[row_index][column_name] = value
        self._save_table(context)

        return {
            "success": True,
            "row_index": row_index,
            "column": column_name,
            "old_value": old_value,
            "new_value": value,
        }

    def get_table_status(self, table_id: str) -> dict[str, Any]:
        """Get compact status of a table for resumption."""
        if table_id not in self._tables:
            raise ValueError(f"Table not found: {table_id}")

        context = self._tables[table_id]
        col_names = [col.name for col in context.columns]

        return {
            "id": context.id,
            "title": context.title,
            "intent": context.intent,
            "columns": col_names,
            "row_count": context.row_count,
            "source_description": context.source_description,
            "created_at": str(context.created_at),
            # Compact: only show last 2 rows to save tokens
            "last_rows": context.rows[-2:] if context.rows else [],
        }

    def preview_table(self, table_id: str, limit: int = 10) -> str:
        """Generate a Markdown preview of the table."""
        if table_id not in self._tables:
            raise ValueError(f"Table not found: {table_id}")

        context = self._tables[table_id]
        if not context.columns:
            return "Table has no columns defined."

        # Header
        headers = [col.name for col in context.columns]
        header_line = "| " + " | ".join(headers) + " |"
        sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"

        # Rows
        row_lines = []
        for row in context.rows[:limit]:
            vals = [str(row.get(h, "-")) for h in headers]
            row_lines.append("| " + " | ".join(vals) + " |")

        preview = f"### {context.title}\n\n{header_line}\n{sep_line}\n" + "\n".join(
            row_lines
        )

        if context.row_count > limit:
            preview += f"\n\n*(Showing {limit} of {context.row_count} rows)*"

        return preview

    def get_table_context(self, table_id: str) -> TableContext:
        """Retrieve the full table context."""
        if table_id not in self._tables:
            raise ValueError(f"Table not found: {table_id}")
        return self._tables[table_id]

    async def render_table(
        self,
        table_id: str,
        format: Literal["excel", "markdown", "html"] = "excel",
        filename: str = "output",
    ) -> dict[str, Any]:
        """Render the table to the specified format."""
        if table_id not in self._tables:
            raise ValueError(f"Table not found: {table_id}")

        context = self._tables[table_id]
        if context.row_count == 0:
            raise ValueError("Cannot render an empty table. Add rows first.")

        if format == "excel":
            file_path = self._excel_renderer.render(context, filename)
            return {
                "success": True,
                "format": "excel",
                "file_path": str(file_path),
                "row_count": context.row_count,
            }
        elif format == "markdown":
            preview = self.preview_table(table_id, limit=context.row_count)
            return {
                "success": True,
                "format": "markdown",
                "content": preview,
                "row_count": context.row_count,
            }
        else:
            raise NotImplementedError(f"Format '{format}' is not yet supported.")

    # =========================================================================
    # Draft Management (for token-efficient workflows)
    # =========================================================================

    def _load_existing_drafts(self) -> None:
        """Load drafts from disk on startup."""
        for json_file in self.draft_dir.glob("draft_*.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                    draft = TableDraft(
                        table_id=data.get("table_id"),
                        intent=data.get("intent"),
                        title=data.get("title", ""),
                        proposed_columns=data.get("proposed_columns", []),
                        extraction_plan=data.get("extraction_plan", []),
                        source_doc_ids=data.get("source_doc_ids", []),
                        source_sections=data.get("source_sections", []),
                        pending_rows=data.get("pending_rows", []),
                        notes=data.get("notes", ""),
                    )
                    draft_id = json_file.stem  # draft_xxx
                    self._drafts[draft_id] = draft
            except Exception:
                continue

    def _save_draft(self, draft_id: str, draft: TableDraft) -> None:
        """Persist draft to disk."""
        json_path = self.draft_dir / f"{draft_id}.json"
        state = {
            "table_id": draft.table_id,
            "intent": draft.intent,
            "title": draft.title,
            "proposed_columns": draft.proposed_columns,
            "extraction_plan": draft.extraction_plan,
            "source_doc_ids": draft.source_doc_ids,
            "source_sections": draft.source_sections,
            "pending_rows": draft.pending_rows,
            "notes": draft.notes,
            "last_updated": str(draft.last_updated),
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def create_draft(
        self,
        title: str,
        intent: Literal["comparison", "citation", "summary"] | None = None,
        proposed_columns: list[dict[str, Any]] | None = None,
        extraction_plan: list[str] | None = None,
        source_doc_ids: list[str] | None = None,
        source_sections: list[str] | None = None,
        notes: str = "",
    ) -> str:
        """Create a new draft for table planning."""
        draft_id = f"draft_{uuid.uuid4().hex[:8]}"
        draft = TableDraft(
            title=title,
            intent=intent,
            proposed_columns=proposed_columns or [],
            extraction_plan=extraction_plan or [],
            source_doc_ids=source_doc_ids or [],
            source_sections=source_sections or [],
            notes=notes,
        )
        self._drafts[draft_id] = draft
        self._save_draft(draft_id, draft)
        return draft_id

    def update_draft(
        self,
        draft_id: str,
        **updates: Any,
    ) -> dict[str, Any]:
        """Update draft fields."""
        if draft_id not in self._drafts:
            raise ValueError(f"Draft not found: {draft_id}")

        draft = self._drafts[draft_id]

        # Update allowed fields
        allowed_fields = {
            "table_id",
            "intent",
            "title",
            "proposed_columns",
            "extraction_plan",
            "source_doc_ids",
            "source_sections",
            "pending_rows",
            "notes",
        }

        for key, value in updates.items():
            if key in allowed_fields:
                setattr(draft, key, value)

        draft.last_updated = datetime.now()
        self._save_draft(draft_id, draft)

        return {"success": True, "draft_id": draft_id}

    def get_draft(self, draft_id: str) -> TableDraft:
        """Get a draft by ID."""
        if draft_id not in self._drafts:
            raise ValueError(f"Draft not found: {draft_id}")
        return self._drafts[draft_id]

    def list_drafts(self) -> list[dict[str, Any]]:
        """List all drafts."""
        return [
            {
                "id": draft_id,
                "title": d.title,
                "intent": d.intent,
                "has_table": d.table_id is not None,
                "columns_planned": len(d.proposed_columns),
                "pending_rows": len(d.pending_rows),
                "last_updated": str(d.last_updated),
            }
            for draft_id, d in self._drafts.items()
        ]

    def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft."""
        if draft_id in self._drafts:
            del self._drafts[draft_id]
            json_path = self.draft_dir / f"{draft_id}.json"
            if json_path.exists():
                json_path.unlink()
            return True
        return False

    def commit_draft_to_table(self, draft_id: str) -> str:
        """Convert a draft into an actual table."""
        if draft_id not in self._drafts:
            raise ValueError(f"Draft not found: {draft_id}")

        draft = self._drafts[draft_id]

        if not draft.proposed_columns:
            raise ValueError("Draft has no columns defined")
        if not draft.intent:
            raise ValueError("Draft has no intent defined")

        # Create table from draft
        table_id = self.create_table(
            intent=draft.intent,
            title=draft.title,
            columns=draft.proposed_columns,
            source_description=f"Sources: {', '.join(draft.source_doc_ids)}"
            if draft.source_doc_ids
            else "",
        )

        # Add pending rows if any
        if draft.pending_rows:
            self.add_rows(table_id, draft.pending_rows)

        # Update draft with table_id
        draft.table_id = table_id
        self._save_draft(draft_id, draft)

        return table_id

    # =========================================================================
    # Token Estimation
    # =========================================================================

    def estimate_table_tokens(self, table_id: str) -> dict[str, int]:
        """Estimate token usage for a table."""
        if table_id not in self._tables:
            raise ValueError(f"Table not found: {table_id}")

        context = self._tables[table_id]
        content_tokens = context.estimate_tokens()

        # Estimate preview tokens
        preview = self.preview_table(table_id, limit=10)
        preview_tokens = len(preview) // 4

        return {
            "content_tokens": content_tokens,
            "preview_tokens": preview_tokens,
            "full_preview_tokens": len(self.preview_table(table_id, limit=1000)) // 4,
            "row_count": context.row_count,
            "tokens_per_row": content_tokens // max(context.row_count, 1),
        }


# Global instance
table_service = TableService()
