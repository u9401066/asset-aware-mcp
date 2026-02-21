"""
Domain Layer - Table Entities

Entities and value objects for the A2T (Anything to Table) module.
Includes: TableContext, CellCitation, ChangeEntry, TableChangeLog, TableTemplate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from .value_objects import AssetRef

# ============================================================================
# Column & Schema
# ============================================================================


@dataclass
class ColumnDef:
    """Definition of a table column."""

    name: str
    type: Literal["text", "number", "date", "enum", "url"]
    required: bool = True
    enum_values: list[str] | None = None  # Only used when type="enum"


# ============================================================================
# CellCitation — 儲存格引用層
# ============================================================================


@dataclass
class CellCitation:
    """
    一個儲存格的完整引用紀錄。

    引用是 row data 的「平行附加層」，不改變 rows: list[dict] 結構。
    可有多個引用來源，以及 Agent 信心度。
    """

    refs: list[AssetRef] = field(default_factory=list)
    confidence: float | None = None  # Agent 信心度 0.0~1.0
    notes: str = ""  # Agent 填寫備註

    def add_ref(self, ref: AssetRef) -> None:
        """新增一個引用來源。"""
        self.refs.append(ref)

    def remove_ref(self, index: int) -> AssetRef | None:
        """移除指定索引的引用，返回被移除的引用。"""
        if 0 <= index < len(self.refs):
            return self.refs.pop(index)
        return None

    def to_dict(self) -> dict[str, Any]:
        """序列化為 dict。"""
        d: dict[str, Any] = {
            "refs": [r.to_dict() for r in self.refs],
        }
        if self.confidence is not None:
            d["confidence"] = self.confidence
        if self.notes:
            d["notes"] = self.notes
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CellCitation:
        """從 dict 反序列化。"""
        return cls(
            refs=[AssetRef.from_dict(r) for r in data.get("refs", [])],
            confidence=data.get("confidence"),
            notes=data.get("notes", ""),
        )

    def to_footnote(self, start_index: int = 1) -> str:
        """產生腳註文字，例如 [1][2]。"""
        indices = range(start_index, start_index + len(self.refs))
        return "".join(f"[{i}]" for i in indices)


# ============================================================================
# Audit Trail — 變更紀錄
# ============================================================================


@dataclass
class ChangeEntry:
    """
    一筆表格變更紀錄。

    記錄「改了什麼」+「依據是什麼」。
    """

    timestamp: datetime
    operation: str  # "update_cell", "add_rows", "delete_row", etc.
    target: str  # "table" / "row:2" / "row:2/col:Drug"
    old_value: Any | None = None
    new_value: Any | None = None
    citations: list[AssetRef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """序列化為 dict。"""
        d: dict[str, Any] = {
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
            "target": self.target,
        }
        if self.old_value is not None:
            d["old_value"] = self.old_value
        if self.new_value is not None:
            d["new_value"] = self.new_value
        if self.citations:
            d["citations"] = [c.to_dict() for c in self.citations]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChangeEntry:
        """從 dict 反序列化。"""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            operation=data["operation"],
            target=data["target"],
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            citations=[AssetRef.from_dict(c) for c in data.get("citations", [])],
        )


@dataclass
class TableChangeLog:
    """表格完整變更歷史。"""

    table_id: str
    entries: list[ChangeEntry] = field(default_factory=list)

    def add(self, entry: ChangeEntry) -> None:
        """新增一筆變更紀錄。"""
        self.entries.append(entry)

    def get_recent(self, limit: int = 20) -> list[ChangeEntry]:
        """取得最近 N 筆變更。"""
        return self.entries[-limit:]

    def get_by_cell(self, row_index: int, column_name: str) -> list[ChangeEntry]:
        """取得特定 cell 的所有變更歷史。"""
        target = f"row:{row_index}/col:{column_name}"
        return [e for e in self.entries if e.target == target]

    def get_by_row(self, row_index: int) -> list[ChangeEntry]:
        """取得特定 row 的所有變更歷史。"""
        prefix = f"row:{row_index}"
        return [e for e in self.entries if e.target.startswith(prefix)]

    def to_dict(self) -> dict[str, Any]:
        """序列化為 dict。"""
        return {
            "table_id": self.table_id,
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TableChangeLog:
        """從 dict 反序列化。"""
        return cls(
            table_id=data["table_id"],
            entries=[ChangeEntry.from_dict(e) for e in data.get("entries", [])],
        )


# ============================================================================
# Table Templates
# ============================================================================


@dataclass
class TableTemplate:
    """預設表格模板。"""

    name: str
    title: str
    intent: Literal["comparison", "citation", "summary"]
    columns: list[ColumnDef]
    description: str = ""

    def to_create_params(self, title_override: str = "") -> dict[str, Any]:
        """轉換為 create_table 參數。"""
        return {
            "intent": self.intent,
            "title": title_override or self.title,
            "columns": [
                {"name": c.name, "type": c.type, "required": c.required}
                for c in self.columns
            ],
        }

    def to_dict(self) -> dict[str, Any]:
        """序列化為 dict。"""
        return {
            "name": self.name,
            "title": self.title,
            "intent": self.intent,
            "description": self.description,
            "columns": [
                {
                    "name": c.name,
                    "type": c.type,
                    "required": c.required,
                    "enum_values": c.enum_values,
                }
                for c in self.columns
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TableTemplate:
        """從 dict 反序列化。"""
        return cls(
            name=data["name"],
            title=data["title"],
            intent=data["intent"],
            description=data.get("description", ""),
            columns=[
                ColumnDef(
                    name=c["name"],
                    type=c["type"],
                    required=c.get("required", True),
                    enum_values=c.get("enum_values"),
                )
                for c in data.get("columns", [])
            ],
        )


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

    citations 是「平行附加層」，key 格式為 "row_index:column_name"。
    change_log 為每個 table 獨立的變更歷史。
    """

    id: str
    intent: Literal["comparison", "citation", "summary"]
    title: str
    columns: list[ColumnDef]
    rows: list[dict[str, Any]] = field(default_factory=list)
    source_description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    # 平行引用層 — key: "row_index:column_name"
    citations: dict[str, CellCitation] = field(default_factory=dict)
    # 變更歷史（惰性初始化）
    change_log: TableChangeLog | None = None

    def __post_init__(self) -> None:
        """Ensure change_log is initialized."""
        if self.change_log is None:
            self.change_log = TableChangeLog(table_id=self.id)

    @staticmethod
    def _cite_key(row_index: int, column_name: str) -> str:
        """產生引用 key。"""
        return f"{row_index}:{column_name}"

    def get_citation(self, row_index: int, column_name: str) -> CellCitation | None:
        """取得特定儲存格的引用。"""
        return self.citations.get(self._cite_key(row_index, column_name))

    def set_citation(
        self, row_index: int, column_name: str, citation: CellCitation
    ) -> None:
        """設定特定儲存格的引用。"""
        self.citations[self._cite_key(row_index, column_name)] = citation

    def remove_citation(self, row_index: int, column_name: str) -> bool:
        """移除特定儲存格的引用，返回是否成功。"""
        key = self._cite_key(row_index, column_name)
        if key in self.citations:
            del self.citations[key]
            return True
        return False

    def get_row_citations(self, row_index: int) -> dict[str, CellCitation]:
        """取得某一行所有欄位的引用。"""
        prefix = f"{row_index}:"
        return {
            k.split(":", 1)[1]: v
            for k, v in self.citations.items()
            if k.startswith(prefix)
        }

    @property
    def column_names(self) -> list[str]:
        """Return column names."""
        return [c.name for c in self.columns]

    @property
    def row_count(self) -> int:
        """Return the number of rows in the table."""
        return len(self.rows)

    def get_row(self, row_index: int) -> dict[str, Any] | None:
        """取得指定行的資料。"""
        if 0 <= row_index < len(self.rows):
            return self.rows[row_index]
        return None

    def get_cell(self, row_index: int, column_name: str) -> Any | None:
        """取得指定儲存格的值。"""
        if 0 <= row_index < len(self.rows):
            return self.rows[row_index].get(column_name)
        return None

    def add_column(self, col_def: ColumnDef, default_value: Any = None) -> None:
        """新增欄位（帶預設值），不影響現有資料。"""
        self.columns.append(col_def)
        for row in self.rows:
            row[col_def.name] = default_value

    def remove_column(self, column_name: str) -> bool:
        """移除欄位及其所有資料和引用。"""
        col_idx = next(
            (i for i, c in enumerate(self.columns) if c.name == column_name),
            None,
        )
        if col_idx is None:
            return False
        self.columns.pop(col_idx)
        for row in self.rows:
            row.pop(column_name, None)
        # 清除相關引用
        to_remove = [k for k in self.citations if k.endswith(f":{column_name}")]
        for k in to_remove:
            del self.citations[k]
        return True

    def rename_column(self, old_name: str, new_name: str) -> bool:
        """重新命名欄位。"""
        col = next((c for c in self.columns if c.name == old_name), None)
        if col is None:
            return False
        col.name = new_name
        for row in self.rows:
            if old_name in row:
                row[new_name] = row.pop(old_name)
        # 更新引用 key
        old_suffix = f":{old_name}"
        new_suffix = f":{new_name}"
        keys_to_rename = [k for k in self.citations if k.endswith(old_suffix)]
        for k in keys_to_rename:
            self.citations[k.replace(old_suffix, new_suffix)] = self.citations.pop(k)
        return True

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
        for key in row:
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
