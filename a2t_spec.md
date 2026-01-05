# Project Specification: A2T (Anything to Table)
**Version:** 2.0.0 (Stateful Workflow Edition)  
**Date:** 2026-01-05  
**Architecture Type:** Agent-Driven ETL with Stateful MCP Enforcement  
**Core Technology:** FastMCP, DuckDB, Polars, Pydantic, XlsxWriter

## 1. Executive Summary (專案概述)
A2T (Anything to Table) 是一個進階的 MCP Server，旨在解決現有 LLM (Gemini/Copilot) 在製作表格時的「幻覺」、「格式崩壞」與「缺乏邏輯」問題。

不同於傳統 Chatbot 直接輸出 Markdown，A2T 採用 **「模具與澆注 (Mold & Pour)」** 模式：
- **Agent (The Brain)**: 負責非結構化文本的理解與提取 (Extract)。
- **MCP (The Engine)**: 負責狀態管理、Schema 驗證、邏輯運算 (Transform) 與 視覺化渲染 (Load)。

核心差異在於引入了 **Session (會話狀態)** 與 **DuckDB (中間層數據庫)**，確保處理大量數據時的穩定性與可追溯性。

## 2. System Architecture (系統架構)
### 2.1 Workflow Pipeline
系統運作遵循嚴格的狀態機 (State Machine) 流程：

```mermaid
graph TD
    A[IDLE] -->|tool: start_session| B[INIT]
    B -->|tool: set_intent| C[SCHEMA_LOCKED]
    C -->|tool: add_rows (Loop)| D[STAGED (DuckDB)]
    D -->|tool: analyze/preview| D
    D -->|tool: render_final| E[COMPLETED]
```

### 2.2 Component Diagram
- **Session Manager**: 管理 `session_id`，維護當前狀態 (`state`) 與 DuckDB 連線 (`conn`)。
- **Schema Registry**: 定義不同意圖 (`Intent`) 的 Pydantic 模型（如引用、大綱、通用數據）。
- **ETL Engine**:
    - **Ingest**: DuckDB (High-performance SQL storage).
    - **Compute**: Polars (Data cleaning, sorting, aggregation).
- **Render Engine**:
    - **Excel**: XlsxWriter (Conditional formatting, rich text).
    - **HTML**: Great Tables (Interactive preview).

## 3. Data Architecture (數據架構)
### 3.1 Session Context
每個任務由一個 Session 物件維護，存活於記憶體中 (或是 Redis)。

```python
class SessionContext:
    id: str              # UUID
    state: str           # IDLE, INIT, SCHEMA_LOCKED, STAGED, COMPLETED
    intent: str          # citation, outline, general
    db_conn: duckdb.DuckDBPyConnection
    metadata: dict       # 存放標題、來源描述等
```

### 3.2 Dynamic Schemas (Intent Definitions)
- **Type A: citation (Academic/Research)**
    - **Goal**: 整理文獻來源與證據。
    - **Columns**: `source`, `author`, `year` (int), `quote` (text), `relevance_score` (1-5), `tags` (list)。
    - **Visual Logic**: Heatmap on `relevance_score`。
- **Type B: outline (Structure/Project)**
    - **Goal**: 整理會議記錄或專案大綱。
    - **Columns**: `section_id` (e.g., "1.2"), `topic`, `action_item`, `owner`, `status` (Enum: Pending/Done)。
    - **Visual Logic**: Status badges (Red/Green/Yellow)。
- **Type C: general (Discovery)**
    - **Goal**: Agent 自主發現的數據。
    - **Columns**: `entity` (Row Header), `metrics` (JSON/Dict for dynamic columns)。
    - **Visual Logic**: Auto-detect numbers for Data Bars。

## 4. MCP Tool Definitions (API Spec)
### Group 1: Session Lifecycle
- **`start_session()`**
    - **Returns**: `session_id` (Must be used in all subsequent calls).
    - **Transition**: `IDLE` -> `INIT`。
- **`set_intent(session_id, intent, source_description)`**
    - **Args**: `intent` ("citation" | "outline" | "general")。
    - **Action**: Initializes DuckDB table schema based on intent。
    - **Transition**: `INIT` -> `SCHEMA_LOCKED`。

### Group 2: ETL Operations (The Heavy Lifting)
- **`add_rows(session_id, data)`**
    - **Args**: `data` (List of JSON objects matching the intent schema)。
    - **Action**: Validates via Pydantic -> Inserts into DuckDB。
    - **Note**: Can be called multiple times (Streaming input)。
    - **Transition**: `SCHEMA_LOCKED` -> `STAGED`。
- **`run_sql_query(session_id, query)`** (Optional/Advanced)
    - **Args**: SQL query string。
    - **Action**: Allows Agent to perform complex aggregation (e.g., "Count items by status") inside DuckDB。
    - **Constraint**: Read-only queries on staging table。

### Group 3: Visualization & Output
- **`preview_table(session_id)`**
    - **Returns**: Markdown representation of the top 10 rows。
    - **Purpose**: For Agent to self-correct before final rendering。
- **`render_final(session_id, format, filename)`**
    - **Args**: `format` ("excel" | "html")。
    - **Logic**:
        1. Fetch all data from DuckDB to Polars DataFrame。
        2. Apply intent-specific sorting (e.g., Sort Citation by Year DESC)。
        3. Inject Design Elements (Colors, Fonts)。
    - **Returns**: File path or Base64 artifact。
    - **Transition**: `STAGED` -> `COMPLETED`。

## 5. Implementation Details (實作細節)
### 5.1 Guardrails (防錯機制)
使用 Python Decorator (`@require_state`) 強制執行順序。如果 Agent 在 `INIT` 狀態直接呼叫 `render_final`，系統必須拋出明確錯誤：
*"Error: Current state is INIT. You must set intent and add rows before rendering."*

### 5.2 Visual Design System (Excel)
渲染引擎必須自動套用以下樣式，無需 Agent 指定：
- **Header**: Dark Grey Background (#2C3E50), White Text, Bold。
- **Text Alignment**: Top Vertical Align, Wrap Text enabled。
- **Column Width**: Auto-calculated based on content length (max 50 chars)。
- **Conditional Formatting**:
    - Text contains "High Risk" -> Light Red Fill。
    - Text contains "Done" -> Light Green Fill。
    - Number columns -> Excel Data Bars (Blue)。

## 6. Directory Structure (專案結構)
```plaintext
a2t-mcp/
├── pyproject.toml         # Dependencies: fastmcp, duckdb, polars, xlsxwriter, pydantic
├── main.py                # Entry point, MCP Server instantiation
├── core/
│   ├── session.py         # SessionContext & State Machine logic
│   └── store.py           # DuckDB connection wrapper
├── schemas/
│   ├── base.py
│   ├── citation.py        # Pydantic models for Citation
│   └── outline.py         # Pydantic models for Outline
└── engine/
    ├── etl.py             # Polars transformations (Sorting, Cleaning)
    └── renderer.py        # XlsxWriter & Great Tables logic
```

## 7. Development Roadmap
- **Phase 1: The Core (Skeleton)**
    - Implement `SessionContext` and `start_session`。
    - Setup in-memory DuckDB connection。
    - Implement basic `add_rows` logic。
- **Phase 2: The Logic (Brain)**
    - Define Pydantic models for `citation` and `outline`。
    - Implement Intent switching logic。
    - Add Pydantic validation to `add_rows`。
- **Phase 3: The Beauty (Face)**
    - Implement `renderer.py` with XlsxWriter。
    - Add "Semantic Coloring" (e.g., Relevance Score Heatmap)。
    - Test with Claude/Cursor to verify the workflow loop。

---
**使用說明**
將此檔案存為 `SPEC.md`。當您使用 Cursor 或 Cline 開發時，請在 Prompt 中引用此檔案：
"User spec is in SPEC.md. Please implement the Session State logic first."
