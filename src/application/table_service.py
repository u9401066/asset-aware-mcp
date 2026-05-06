"""
Application Layer - Table Service

Orchestrates table creation, data accumulation, rendering,
citation management, audit trail, and schema evolution.
"""

import json
import logging
import uuid
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Literal

from src.domain.repositories import TableRendererInterface
from src.domain.table_entities import (
    CellCitation,
    ChangeEntry,
    ColumnDef,
    TableChangeLog,
    TableContext,
    TableDraft,
    TableTemplate,
)
from src.domain.value_objects import AssetRef

logger = logging.getLogger(__name__)


class TableService:
    """Service for managing A2T (Anything to Table) workflows with persistence."""

    def __init__(
        self,
        table_output_dir: Path,
        table_renderer: TableRendererInterface,
    ) -> None:
        """
        Initialize table service with dependencies.

        Args:
            table_output_dir: Directory for storing table files
            table_renderer: Renderer for generating output files (Excel, etc.)
        """
        self.storage_dir = table_output_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.draft_dir = self.storage_dir / "drafts"
        self.draft_dir.mkdir(parents=True, exist_ok=True)
        # In-memory cache
        self._tables: dict[str, TableContext] = {}
        self._drafts: dict[str, TableDraft] = {}
        self._table_renderer = table_renderer
        self._load_existing_tables()
        self._load_existing_drafts()

    def _load_existing_tables(self) -> None:
        """Load table metadata from disk on startup."""
        for json_file in self.storage_dir.glob("*.json"):
            try:
                with json_file.open(encoding="utf-8") as f:
                    data = json.load(f)
                    # Reconstruct TableContext
                    col_defs = [ColumnDef(**c) for c in data["columns"]]
                    # Reconstruct citations
                    citations: dict[str, CellCitation] = {}
                    for key, cite_data in data.get("citations", {}).items():
                        citations[key] = CellCitation.from_dict(cite_data)
                    # Reconstruct change log
                    change_log = None
                    if "change_log" in data:
                        change_log = TableChangeLog.from_dict(data["change_log"])
                    context = TableContext(
                        id=data["id"],
                        intent=data["intent"],
                        title=data["title"],
                        columns=col_defs,
                        rows=data["rows"],
                        source_description=data.get("source_description", ""),
                        source_doc_id=data.get("source_doc_id", ""),
                        source_block_id=data.get("source_block_id", ""),
                        source_revision_id=data.get("source_revision_id", ""),
                        source_block_hash=data.get("source_block_hash", ""),
                        created_at=data.get("created_at", ""),
                        citations=citations,
                        change_log=change_log,
                    )
                    self._tables[context.id] = context
            except Exception:
                logger.debug("Skipping corrupted table file: %s", json_file)
                continue

    def _save_table(self, context: TableContext) -> None:
        """Persist table state to JSON and Markdown."""
        # Save JSON state
        json_path = self.storage_dir / f"{context.id}.json"
        state: dict[str, Any] = {
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
            "source_doc_id": context.source_doc_id,
            "source_block_id": context.source_block_id,
            "source_revision_id": context.source_revision_id,
            "source_block_hash": context.source_block_hash,
            "created_at": str(context.created_at)
            if isinstance(context.created_at, datetime)
            else context.created_at,
        }
        # Persist citations
        if context.citations:
            state["citations"] = {
                key: cite.to_dict() for key, cite in context.citations.items()
            }
        # Persist change log
        if context.change_log and context.change_log.entries:
            state["change_log"] = context.change_log.to_dict()

        with json_path.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        # Save Markdown preview
        md_path = self.storage_dir / f"{context.id}.md"
        with md_path.open("w", encoding="utf-8") as f:
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
        self._record_change(
            context,
            "create",
            "table",
            new_value={"title": title, "intent": intent},
        )
        self._save_table(context)
        return table_id

    def add_rows(self, table_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Add rows to an existing table and update persistence."""
        context = self._get_context(table_id)
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
            self._record_change(
                context, "add_rows", "table", new_value={"count": added_count}
            )
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
        context = self._get_context(table_id)
        if index < 0 or index >= len(context.rows):
            raise ValueError(f"Invalid row index: {index}")

        row_errors = context.validate_row(row)
        if row_errors:
            return {"success": False, "errors": row_errors}

        old_row = dict(context.rows[index])
        removed_citations = self._remove_changed_row_citations(context, index, row)
        context.rows[index] = row
        self._record_change(
            context,
            "update_row",
            f"row:{index}",
            old_value=old_row,
            new_value=row,
        )
        self._save_table(context)
        return {"success": True, "citations_removed": removed_citations}

    def delete_row(self, table_id: str, index: int) -> dict[str, Any]:
        """Delete a row by index."""
        context = self._get_context(table_id)
        if index < 0 or index >= len(context.rows):
            raise ValueError(f"Invalid row index: {index}")

        old_row = dict(context.rows[index])
        context.rows.pop(index)
        # Shift citation keys for rows after deleted row
        self._shift_citation_keys(context, index)
        self._record_change(context, "delete_row", f"row:{index}", old_value=old_row)
        self._save_table(context)
        return {"success": True, "total_rows": context.row_count}

    def _shift_citation_keys(self, context: TableContext, deleted_index: int) -> None:
        """After deleting a row, shift citation keys for rows above it."""
        # Remove citations for deleted row
        to_remove = [k for k in context.citations if k.startswith(f"{deleted_index}:")]
        for k in to_remove:
            del context.citations[k]

        # Shift keys for rows after deleted index
        new_citations: dict[str, CellCitation] = {}
        for k, v in context.citations.items():
            row_str, col = k.split(":", 1)
            row_idx = int(row_str)
            if row_idx > deleted_index:
                new_citations[f"{row_idx - 1}:{col}"] = v
            else:
                new_citations[k] = v
        context.citations = new_citations

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
                "columns": t.column_names,
                "citations": len(t.citations),
                "created_at": str(t.created_at),
            }
            for t in self._tables.values()
        ]

    def update_cell(
        self, table_id: str, row_index: int, column_name: str, value: Any
    ) -> dict[str, Any]:
        """Update a single cell in the table."""
        context = self._get_context(table_id)
        self._validate_cell_address(context, row_index, column_name)

        # Update the cell
        old_value = context.rows[row_index].get(column_name)
        citation_removed = self._remove_cell_citation_if_value_changed(
            context,
            row_index,
            column_name,
            old_value,
            value,
        )
        context.rows[row_index][column_name] = value
        self._record_change(
            context,
            "update_cell",
            f"row:{row_index}/col:{column_name}",
            old_value=old_value,
            new_value=value,
        )
        self._save_table(context)

        return {
            "success": True,
            "row_index": row_index,
            "column": column_name,
            "old_value": old_value,
            "new_value": value,
            "citation_removed": citation_removed,
        }

    def get_table_status(self, table_id: str) -> dict[str, Any]:
        """Get compact status of a table for resumption."""
        context = self._get_context(table_id)
        col_names = [col.name for col in context.columns]

        return {
            "id": context.id,
            "title": context.title,
            "intent": context.intent,
            "columns": col_names,
            "row_count": context.row_count,
            "citation_count": len(context.citations),
            "source_description": context.source_description,
            "source_doc_id": context.source_doc_id,
            "source_block_id": context.source_block_id,
            "created_at": str(context.created_at),
            # Compact: only show last 2 rows to save tokens
            "last_rows": context.rows[-2:] if context.rows else [],
        }

    def preview_table(self, table_id: str, limit: int = 10) -> str:
        """Generate a Markdown preview of the table."""
        context = self._get_context(table_id)

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
        return self._get_context(table_id)

    async def render_table(
        self,
        table_id: str,
        format: Literal["excel", "markdown", "html"] = "excel",
        filename: str = "output",
    ) -> dict[str, Any]:
        """Render the table to the specified format."""
        context = self._get_context(table_id)

        context = self._tables[table_id]
        if context.row_count == 0:
            raise ValueError("Cannot render an empty table. Add rows first.")

        if format == "excel":
            file_path = self._table_renderer.render(context, filename)
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
        elif format == "html":
            content = self._render_html_table(context)
            return {
                "success": True,
                "format": "html",
                "content": content,
                "row_count": context.row_count,
            }
        else:
            raise NotImplementedError(f"Format '{format}' is not yet supported.")

    def _remove_changed_row_citations(
        self,
        context: TableContext,
        row_index: int,
        new_row: dict[str, Any],
    ) -> list[str]:
        """Remove cell citations when the cited cell value changes."""
        removed: list[str] = []
        old_row = context.rows[row_index]
        for column_name in context.column_names:
            if old_row.get(column_name) == new_row.get(column_name):
                continue
            if context.get_citation(row_index, column_name) is None:
                continue
            context.remove_citation(row_index, column_name)
            removed.append(f"{row_index}:{column_name}")
        return removed

    @staticmethod
    def _remove_cell_citation_if_value_changed(
        context: TableContext,
        row_index: int,
        column_name: str,
        old_value: Any,
        new_value: Any,
    ) -> bool:
        """Remove a citation from a single cell if the cell content changed."""
        if old_value == new_value:
            return False
        if context.get_citation(row_index, column_name) is None:
            return False
        context.remove_citation(row_index, column_name)
        return True

    @staticmethod
    def _render_html_table(context: TableContext) -> str:
        headers = context.column_names
        header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
        rows_html = []
        for row in context.rows:
            cells = "".join(
                f"<td>{escape(str(row.get(header, '')))}</td>" for header in headers
            )
            rows_html.append(f"<tr>{cells}</tr>")
        body_html = "".join(rows_html)
        return (
            "<table>"
            f"<caption>{escape(context.title)}</caption>"
            f"<thead><tr>{header_html}</tr></thead>"
            f"<tbody>{body_html}</tbody>"
            "</table>"
        )

    # =========================================================================
    # Audit Trail Recording
    # =========================================================================

    def _record_change(
        self,
        context: TableContext,
        operation: str,
        target: str,
        old_value: Any = None,
        new_value: Any = None,
        citations: list[AssetRef] | None = None,
    ) -> None:
        """Record a change entry in the table's change log."""
        if context.change_log is None:
            context.change_log = TableChangeLog(table_id=context.id)
        entry = ChangeEntry(
            timestamp=datetime.now(),
            operation=operation,
            target=target,
            old_value=old_value,
            new_value=new_value,
            citations=citations or [],
        )
        context.change_log.add(entry)

    def get_change_history(
        self, table_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Get recent change history for a table."""
        context = self._get_context(table_id)
        if context.change_log is None:
            return []
        return [e.to_dict() for e in context.change_log.get_recent(limit)]

    def get_cell_history(
        self, table_id: str, row_index: int, column_name: str
    ) -> list[dict[str, Any]]:
        """Get change history for a specific cell."""
        context = self._get_context(table_id)
        if context.change_log is None:
            return []
        return [
            e.to_dict() for e in context.change_log.get_by_cell(row_index, column_name)
        ]

    # =========================================================================
    # Citation Management
    # =========================================================================

    def add_citation(
        self,
        table_id: str,
        row_index: int,
        column_name: str,
        refs: list[dict[str, Any]],
        confidence: float | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        """Add or update citation for a specific cell."""
        context = self._get_context(table_id)
        self._validate_cell_address(context, row_index, column_name)

        asset_refs = [AssetRef.from_dict(r) for r in refs]

        existing = context.get_citation(row_index, column_name)
        if existing:
            for ref in asset_refs:
                existing.add_ref(ref)
            if confidence is not None:
                existing.confidence = confidence
            if notes:
                existing.notes = notes
        else:
            context.set_citation(
                row_index,
                column_name,
                CellCitation(refs=asset_refs, confidence=confidence, notes=notes),
            )

        self._record_change(
            context,
            "add_citation",
            f"row:{row_index}/col:{column_name}",
            new_value={"refs_count": len(asset_refs)},
            citations=asset_refs,
        )
        self._save_table(context)

        return {
            "success": True,
            "cell": f"row:{row_index}/col:{column_name}",
            "total_refs": len(
                context.get_citation(row_index, column_name).refs  # type: ignore[union-attr]
            ),
        }

    def get_citations(
        self,
        table_id: str,
        row_index: int | None = None,
        column_name: str | None = None,
    ) -> dict[str, Any]:
        """Get citations for a cell, row, or entire table."""
        context = self._get_context(table_id)

        if row_index is not None and column_name is not None:
            cite = context.get_citation(row_index, column_name)
            if cite:
                return {
                    "cell": f"row:{row_index}/col:{column_name}",
                    "citation": cite.to_dict(),
                }
            return {"cell": f"row:{row_index}/col:{column_name}", "citation": None}

        if row_index is not None:
            row_cites = context.get_row_citations(row_index)
            return {
                "row": row_index,
                "citations": {k: v.to_dict() for k, v in row_cites.items()},
            }

        # All citations
        return {
            "table_id": table_id,
            "total_citations": len(context.citations),
            "citations": {k: v.to_dict() for k, v in context.citations.items()},
        }

    def remove_citation(
        self,
        table_id: str,
        row_index: int,
        column_name: str,
        ref_index: int | None = None,
    ) -> dict[str, Any]:
        """Remove a citation or a specific ref from a cell."""
        context = self._get_context(table_id)
        self._validate_cell_address(context, row_index, column_name)

        cite = context.get_citation(row_index, column_name)
        if cite is None:
            return {"success": False, "error": "No citation found for this cell"}

        if ref_index is not None:
            removed = cite.remove_ref(ref_index)
            if removed is None:
                return {"success": False, "error": f"Invalid ref index: {ref_index}"}
            self._record_change(
                context,
                "remove_citation_ref",
                f"row:{row_index}/col:{column_name}",
                old_value=removed.to_dict(),
            )
        else:
            context.remove_citation(row_index, column_name)
            self._record_change(
                context,
                "remove_citation",
                f"row:{row_index}/col:{column_name}",
                old_value=cite.to_dict(),
            )

        self._save_table(context)
        return {"success": True}

    # =========================================================================
    # Schema Evolution
    # =========================================================================

    def add_column(
        self,
        table_id: str,
        name: str,
        col_type: str = "text",
        required: bool = False,
        default_value: Any = None,
        enum_values: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add a new column to the table."""
        context = self._get_context(table_id)

        if any(c.name == name for c in context.columns):
            return {"success": False, "error": f"Column '{name}' already exists"}

        col_def = ColumnDef(
            name=name,
            type=col_type,  # type: ignore[arg-type]
            required=required,
            enum_values=enum_values,
        )
        context.add_column(col_def, default_value)
        self._record_change(
            context,
            "add_column",
            "table",
            new_value={"name": name, "type": col_type},
        )
        self._save_table(context)
        return {"success": True, "columns": context.column_names}

    def remove_column(self, table_id: str, column_name: str) -> dict[str, Any]:
        """Remove a column from the table."""
        context = self._get_context(table_id)

        if not context.remove_column(column_name):
            return {"success": False, "error": f"Column '{column_name}' not found"}

        self._record_change(
            context, "remove_column", "table", old_value={"name": column_name}
        )
        self._save_table(context)
        return {"success": True, "columns": context.column_names}

    def rename_column(
        self, table_id: str, old_name: str, new_name: str
    ) -> dict[str, Any]:
        """Rename a column."""
        context = self._get_context(table_id)

        if not context.rename_column(old_name, new_name):
            return {"success": False, "error": f"Column '{old_name}' not found"}

        self._record_change(
            context,
            "rename_column",
            "table",
            old_value={"name": old_name},
            new_value={"name": new_name},
        )
        self._save_table(context)
        return {"success": True, "columns": context.column_names}

    # =========================================================================
    # Cell-level Operations
    # =========================================================================

    def get_row(self, table_id: str, row_index: int) -> dict[str, Any]:
        """Get a single row with its citations."""
        context = self._get_context(table_id)
        row = context.get_row(row_index)
        if row is None:
            raise ValueError(f"Invalid row index: {row_index}")

        row_cites = context.get_row_citations(row_index)
        return {
            "row_index": row_index,
            "data": row,
            "citations": {k: v.to_dict() for k, v in row_cites.items()}
            if row_cites
            else None,
        }

    def get_cell(
        self, table_id: str, row_index: int, column_name: str
    ) -> dict[str, Any]:
        """Get a single cell value with its citation."""
        context = self._get_context(table_id)
        self._validate_cell_address(context, row_index, column_name)

        value = context.get_cell(row_index, column_name)
        cite = context.get_citation(row_index, column_name)

        return {
            "row_index": row_index,
            "column": column_name,
            "value": value,
            "citation": cite.to_dict() if cite else None,
        }

    def clear_cell(
        self, table_id: str, row_index: int, column_name: str
    ) -> dict[str, Any]:
        """Clear a cell value (set to None) and remove its citation."""
        context = self._get_context(table_id)
        self._validate_cell_address(context, row_index, column_name)

        old_value = context.rows[row_index].get(column_name)
        context.rows[row_index][column_name] = None
        context.remove_citation(row_index, column_name)

        self._record_change(
            context,
            "clear_cell",
            f"row:{row_index}/col:{column_name}",
            old_value=old_value,
        )
        self._save_table(context)
        return {"success": True, "old_value": old_value}

    # =========================================================================
    # Template Management
    # =========================================================================

    def list_templates(self) -> list[dict[str, Any]]:
        """List available table templates."""
        templates = self._get_builtin_templates()
        return [t.to_dict() for t in templates]

    def create_from_template(self, template_name: str, title_override: str = "") -> str:
        """Create a table from a named template."""
        templates = {t.name: t for t in self._get_builtin_templates()}
        if template_name not in templates:
            available = ", ".join(templates.keys())
            raise ValueError(
                f"Template '{template_name}' not found. Available: {available}"
            )

        tpl = templates[template_name]
        params = tpl.to_create_params(title_override)
        return self.create_table(**params)

    @staticmethod
    def _get_builtin_templates() -> list[TableTemplate]:
        """Return built-in table templates."""
        return [
            TableTemplate(
                name="drug_comparison",
                title="Drug Comparison Table",
                intent="comparison",
                description="Compare multiple drugs: mechanism, dosing, side effects",
                columns=[
                    ColumnDef(name="Drug", type="text"),
                    ColumnDef(name="Mechanism", type="text"),
                    ColumnDef(name="Dose", type="text"),
                    ColumnDef(
                        name="Route", type="enum", enum_values=["IV", "IM", "PO", "SC"]
                    ),
                    ColumnDef(name="Side_Effects", type="text"),
                    ColumnDef(name="Notes", type="text", required=False),
                ],
            ),
            TableTemplate(
                name="study_summary",
                title="Study Summary Table",
                intent="summary",
                description="Summarize key findings from multiple studies",
                columns=[
                    ColumnDef(name="Study", type="text"),
                    ColumnDef(name="Year", type="number"),
                    ColumnDef(name="Design", type="text"),
                    ColumnDef(name="Participants", type="number"),
                    ColumnDef(name="Intervention", type="text"),
                    ColumnDef(name="Outcome", type="text"),
                ],
            ),
            TableTemplate(
                name="citation_extract",
                title="Citation Extraction Table",
                intent="citation",
                description="Extract structured data from cited sources",
                columns=[
                    ColumnDef(name="Source", type="text"),
                    ColumnDef(name="Claim", type="text"),
                    ColumnDef(name="Evidence", type="text"),
                    ColumnDef(name="Page", type="number", required=False),
                    ColumnDef(name="Confidence", type="text", required=False),
                ],
            ),
            TableTemplate(
                name="pico_analysis",
                title="PICO Analysis Table",
                intent="comparison",
                description="PICO framework analysis for clinical questions",
                columns=[
                    ColumnDef(name="Study", type="text"),
                    ColumnDef(name="Population", type="text"),
                    ColumnDef(name="Intervention", type="text"),
                    ColumnDef(name="Comparator", type="text"),
                    ColumnDef(name="Outcome", type="text"),
                    ColumnDef(name="Result", type="text"),
                ],
            ),
        ]

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_context(self, table_id: str) -> TableContext:
        """Get table context or raise ValueError."""
        if table_id not in self._tables:
            raise ValueError(f"Table not found: {table_id}")
        return self._tables[table_id]

    def _validate_cell_address(
        self, context: TableContext, row_index: int, column_name: str
    ) -> None:
        """Validate that a cell address is valid."""
        if row_index < 0 or row_index >= len(context.rows):
            raise ValueError(f"Invalid row index: {row_index}")
        col_names = {col.name for col in context.columns}
        if column_name not in col_names:
            raise ValueError(f"Unknown column: '{column_name}'")

    # =========================================================================
    # Draft Management (for token-efficient workflows)
    # =========================================================================

    def _load_existing_drafts(self) -> None:
        """Load drafts from disk on startup."""
        for json_file in self.draft_dir.glob("draft_*.json"):
            try:
                with json_file.open(encoding="utf-8") as f:
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
                logger.debug("Skipping corrupted draft file: %s", json_file)
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
        with json_path.open("w", encoding="utf-8") as f:
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
        context = self._get_context(table_id)

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
