# Roadmap

專案發展路線圖與功能規劃。完成的版本詳見 [CHANGELOG.md](CHANGELOG.md)。

---

## 最近完成 ✅

- **v0.4.1** (2026-03-09) — Release workflow lint 對齊，確保 GitHub Actions 發版全綠
- **v0.4.0** (2026-03-09) — 文件級 CRUD、DOCX/PDF 互轉、strict round-trip、Proposal 真實文件戰測
- **v0.3.3** (2026-02-23) — 生產強化、`.doc` 自動轉換、Markdown escaping 修復
- **v0.3.2** (2026-02-21) — DFM Integrity Checker、檔案層級比對、全面遷移至 uv
- **v0.3.1** (2026-02-21) — Split Format、DFM CLI、Bug 修復
- **v0.3.0** (2026-02-11) — Docx DFM 即時編輯系統
- **v0.2.14** (2026-02-10) — A2T 完整填表系統：19→7 工具合併 + Citation + Audit Trail + Templates
- **v0.2.11** (2026-02-09) — 程式碼品質、工具統計 script、CI 檢查強制
- **v0.2.10** (2026-02-09) — Presentation 層模組化 (39 tools / 6 modules)
- **v0.2.9** (2026-02-09) — Marker ETL 規格書、171 測試通過
- **v0.2.8** (2026-02-05) — Section Navigation 4 工具
- **v0.2.7** (2026-01-06) — 圖片擷取策略優化
- **v0.2.0** (2026-01-05) — A2T 2.0、Draft 系統、PyMuPDF 輕量化

---

## 進行中 🚧

### v0.2.12 - 測試覆蓋率與品質強化

**目標**：測試覆蓋率從 44% → 60%+

#### 🧪 測試覆蓋率 (Priority 1)

| 模組 | 現況 | 目標 | 策略 |
|------|------|------|------|
| `pdf_extractor.py` | 10% | 40% | Mock PDF + 輸出驗證 |
| `lightrag_adapter.py` | 11% | 40% | Mock LightRAG API |
| `asset_service.py` | 18% | 50% | Asset 查詢單元測試 |
| `job_service.py` | 21% | 50% | Job lifecycle 測試 |
| `marker_adapter.py` | 22% | 40% | Mock Marker API |
| `job_store.py` | 23% | 50% | Job 持久化測試 |

- [ ] 為 `pdf_extractor.py` 新增 mock 測試
- [ ] 為 `lightrag_adapter.py` 新增 mock 測試
- [ ] 為 `job_service.py` 新增 lifecycle 測試
- [ ] 為 `asset_service.py` 新增查詢測試
- [ ] A2T Draft 單元測試補齊

#### 🔧 程式碼品質 (Priority 2)

- [ ] 修復 MyPy 類型錯誤 (`services.py:151`, `pdf_extractor.py:586`)
- [ ] `table_tools.py` 拆分 (845 行 → 3 個子模組)
- [ ] 增加 docstring 覆蓋率

---

### v0.2.13 - 說明文件與推廣

#### 📚 文件改善 (Priority 1)

| 項目 | 現況 | 目標 |
|------|------|------|
| API Reference | ❌ 缺少 | 完整 MCP tools 參數說明 |
| Examples | ❌ 缺少 | `/examples` 資料夾 |
| FAQ | ❌ 缺少 | 常見問題集 |
| Demo GIF | ❌ 缺少 | README 操作動畫 |

- [ ] 建立 `/examples` 資料夾
  - [ ] `01-basic-ingest.md` - 基本 PDF 拆解
  - [ ] `02-section-navigation.md` - 章節導航
  - [ ] `03-a2t-workflow.md` - A2T 表格建立
  - [ ] `04-knowledge-graph.md` - 知識圖譜查詢
- [ ] 撰寫 `docs/API_REFERENCE.md`
- [ ] 撰寫 `docs/FAQ.md`
- [ ] README 加入操作 GIF (3-5 秒)

#### 📣 推廣 (Priority 2)

| 平台 | 現況 | 目標 |
|------|------|------|
| PyPI | ✅ v0.3.3 | 維持更新 |
| VSCode Marketplace | ✅ | 維持更新 |
| MCP Hub | ❌ 未登錄 | 提交登錄 |
| GitHub Topics | ❌ 未設定 | 加入 `mcp`, `ai-agents`, `pdf-extraction` |
| Awesome MCP | ❌ 未提交 | PR 提交 |

- [ ] 提交到 [modelcontextprotocol.io](https://modelcontextprotocol.io) MCP Hub
- [ ] 設定 GitHub Repository Topics
- [ ] 提交到 awesome-mcp 列表
- [ ] 撰寫技術部落格介紹 Asset-Aware 概念
- [ ] 製作 5 分鐘 YouTube 快速上手影片 (Optional)

---

### v0.2.14 - A2T 完整填表系統 (合併工具 + Citation + Audit)

> 🎯 **核心理念**：Agent 是填表者。做表和拆解是分開的功能，但共用一個 MCP。
> 表格可接受**任意來源**的資料 — PDF 資產、KG 實體、外部 URL、甚至使用者口述。

#### 設計原則

1. **Agent-friendly**：CRUD 合併為 operation-based 工具，減少工具總量
2. **做表 ≠ 拆解**：`table_*` 工具不依賴 `ingest_documents`，可獨立使用
3. **引用即紀錄**：每次填值可附帶來源（`AssetRef`），自動寫入 Audit Trail
4. **任意 Asset**：不只 PDF 拆解的資產，外部 URL、使用者輸入也是合法來源

---

#### 工具合併策略：19 → 7 工具

**現有 19 工具 → 合併為 7 個 operation-based 工具：**

```
現有 19 tools                          合併後 7 tools
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
plan_table_schema ─────────┐
list_table_templates (新) ─┤──→ plan_table (op: schema/templates/from_template)
create_from_template (新) ─┘

create_table ──────────────┐
delete_table ──────────────┤
list_tables ───────────────┤
preview_table ─────────────┤──→ table_manage (op: create/delete/list/preview
resume_table ──────────────┤         /resume/render/add_col/remove_col/rename_col)
render_table ──────────────┤
add_column (新) ───────────┤
remove_column (新) ────────┤
rename_column (新) ────────┘

add_rows ──────────────────┐
get_row (新) ──────────────┤
update_row ────────────────┤──→ table_data (op: add_rows/get_row/update_row
delete_row ────────────────┤         /delete_row/get_cell/update_cell/clear_cell)
get_cell (新) ─────────────┤    ※ update_cell 可附帶 citation
update_cell ───────────────┤
clear_cell (新) ───────────┘

add_citation (新) ─────────┐
get_citations (新) ────────┤──→ table_cite (op: add/get/remove/cell_history)
remove_citation (新) ──────┤
get_cell_history (新) ─────┘

get_table_history (新) ────┤──→ table_history
estimate_tokens ───────────┘    (op: changes/tokens)

create_table_draft ────────┐
update_table_draft ────────┤
add_rows_to_draft ─────────┤──→ table_draft (op: create/update/add_rows
commit_draft_to_table ─────┤         /resume/commit/list/delete)
list_drafts ───────────────┤
resume_draft ──────────────┘

get_section_content ───────┤──→ 移至 section_tools (本來就該在那裡)
discover_sources (新) ─────┤──→ discover_sources (獨立工具)
```

**合併後總工具數：**

| 模組 | 現有 | v0.2.14 | 說明 |
|------|------|---------|------|
| Document ETL | 6 | 6 | 不變 |
| Section Nav | 4 | 5 | +get_section_content 移入 |
| Job Mgmt | 3 | 3 | 不變 |
| Knowledge | 2 | 2 | 不變 |
| Profile | 5 | 5 | 不變 |
| **A2T** | **19** | **7** | plan/manage/data/cite/history/draft + discover |
| **合計** | **39** | **28** | **↓ 28%，功能反而增加** |

---

#### AssetRef — 統一資產引用（支援任意來源）

> **做表不依賴拆解**的關鍵：`AssetRef` 支援 7 種來源類型

```python
@dataclass(frozen=True)
class AssetRef:
    """統一資產引用 — 指向任何可引用的資料來源"""

    source_type: Literal[
        "section",      # PDF 章節
        "figure",       # PDF 圖片
        "table",        # PDF 表格
        "full_text",    # PDF 全文
        "kg_entity",    # 知識圖譜實體
        "external",     # 外部 URL / DOI
        "user_input",   # 使用者直接提供的文字
    ]

    # 定位 (PDF 資產用)
    doc_id: str = ""               # "doc_gpt4_medical_e567c6"
    asset_id: str = ""             # "sec_introduction", "fig_1"
    page: int | None = None
    line_range: tuple[int, int] | None = None

    # 外部來源
    url: str = ""                  # DOI / URL

    # 通用
    excerpt: str = ""              # 來源節錄 ≤200 chars（驗證用）
    label: str = ""                # 人類可讀標籤
```

**7 種來源的典型用法：**

| source_type | 場景 | 範例引用 |
|-------------|------|----------|
| `section` | Agent 從 PDF 章節讀到資料 | `AssetRef("section", doc_id="doc_xxx", asset_id="sec_methods", page=5, excerpt="dose was 5mg/kg")` |
| `figure` | Agent 從圖中讀取數值 | `AssetRef("figure", doc_id="doc_xxx", asset_id="fig_3", page=8)` |
| `table` | Agent 從 PDF 表格複製 | `AssetRef("table", doc_id="doc_xxx", asset_id="tab_1", page=12)` |
| `kg_entity` | Agent 查 Knowledge Graph | `AssetRef("kg_entity", label="Aspirin-NSAID relation")` |
| `external` | Agent 引用外部文獻 | `AssetRef("external", url="https://doi.org/10.1234", label="Smith 2024")` |
| `user_input` | 使用者口述/貼上文字 | `AssetRef("user_input", excerpt="Patient reported 5mg daily")` |
| `full_text` | Agent 從全文搜尋 | `AssetRef("full_text", doc_id="doc_xxx", line_range=(120,125))` |

---

#### Phase 1: AssetRef + CellCitation 基礎 ✅

**Domain Layer：**
- [x] `AssetRef` frozen dataclass（`domain/value_objects.py`）
- [x] `CellCitation` dataclass（`domain/table_entities.py`）
- [x] `TableContext.citations: dict[str, CellCitation]`
- [x] 引用序列化/反序列化（JSON 持久化）
- [x] 測試 `test_asset_ref.py` (22 tests), `test_citation_audit.py` (46 tests)

#### Phase 2: 合併現有 19 工具 → 7 工具 ✅

**7 個 operation-based 工具已實作：**

##### `plan_table`
```python
async def plan_table(
    operation: Literal["schema", "templates", "from_template"],
    # schema 用
    question: str = "", doc_ids: list[str] = [], hints: list[str] = [],
    # from_template 用
    template_name: str = "", title: str = "", overrides: dict = {},
) -> str:
```

##### `table_manage`
```python
async def table_manage(
    operation: Literal["create", "delete", "list", "preview", "resume",
                        "render", "add_column", "remove_column", "rename_column"],
    table_id: str = "",
    # create 用
    intent: str = "", title: str = "", columns: list[dict] = [],
    # render 用
    format: str = "excel", filename: str = "output",
    # column ops 用
    column_name: str = "", new_name: str = "", column_type: str = "text",
    default_value: Any = None,
    # preview 用
    limit: int = 10,
) -> str:
```

##### `table_data`
```python
async def table_data(
    operation: Literal["add_rows", "get_row", "update_row", "delete_row",
                        "get_cell", "update_cell", "clear_cell"],
    table_id: str,
    # row ops
    row_index: int | None = None, rows: list[dict] = [], row: dict = {},
    # cell ops
    column_name: str = "", value: Any = None,
    # citation (update_cell 時可選附帶)
    citation_source: str = "",     # source_type
    citation_doc_id: str = "",
    citation_asset_id: str = "",
    citation_page: int | None = None,
    citation_excerpt: str = "",
    citation_url: str = "",
    citation_label: str = "",
) -> str:
```

##### `table_cite`
```python
async def table_cite(
    operation: Literal["add", "get", "remove", "cell_history"],
    table_id: str,
    row_index: int = 0,
    column_name: str = "",
    # add 用
    source_type: str = "", doc_id: str = "", asset_id: str = "",
    page: int | None = None, excerpt: str = "", url: str = "", label: str = "",
    confidence: float | None = None,
    # remove 用
    citation_index: int = 0,
) -> str:
```

##### `table_history`
```python
async def table_history(
    operation: Literal["changes", "tokens"],
    table_id: str,
    # changes 用
    limit: int = 20,
    row_index: int | None = None,  # 篩選特定列
    column_name: str | None = None,  # 篩選特定格
) -> str:
```

##### `table_draft`
```python
async def table_draft(
    operation: Literal["create", "update", "add_rows", "resume",
                        "commit", "list", "delete"],
    draft_id: str = "",
    # create/update 用
    title: str = "", intent: str = "",
    proposed_columns: list[dict] = [], notes: str = "",
    # add_rows 用
    rows: list[dict] = [],
) -> str:
```

##### `discover_sources`
```python
async def discover_sources(
    query: str,
    doc_ids: list[str] | None = None,
    types: list[str] | None = None,  # ["section","table","figure","kg_entity"]
    limit: int = 10,
) -> str:
    """跨資產統一搜尋 — 返回可直接作為 citation 的 AssetRef"""
```

- [x] `get_section_content` 移至 `section_tools.py`
- [x] 實作 7 個合併工具（向後相容過渡期可保留舊工具但 deprecated）
- [x] `estimate_tokens` 合併入 `table_history(operation="tokens")`
- [x] 測試所有 operation 路徑（273 tests passed）

#### Phase 3: Audit Trail（自動記錄 + 引用）✅

**Domain Entity：**
```python
@dataclass
class ChangeEntry:
    timestamp: datetime
    operation: str               # "update_cell", "add_rows", etc.
    target: str                  # "table" / "row:2" / "row:2/col:Drug"
    old_value: Any | None = None
    new_value: Any | None = None
    citations: list[AssetRef] = field(default_factory=list)

@dataclass
class TableChangeLog:
    table_id: str
    entries: list[ChangeEntry] = field(default_factory=list)
```

- [x] `ChangeEntry` + `TableChangeLog` dataclass
- [x] `TableService` 所有寫入操作自動記錄（含引用）
- [x] 持久化 `_save_table` 自動包含 change_log
- [x] `table_history(operation="changes")` 查詢
- [x] 測試 `test_citation_audit.py`

#### Phase 4: Table Templates ✅

**內建 4 個模板（`_get_builtin_templates`）：**

| 模板 | 欄位 |
|------|------|
| `drug_comparison` | Drug / Dose / Route / Efficacy / Side Effects |
| `study_summary` | Study / Design / Population / Intervention / Outcome / N / Result |
| `citation_extract` | Source / Section / Page / Content / Notes |
| `pico_analysis` | Population / Intervention / Comparator / Outcome / Evidence Level |

- [x] `TableTemplate` domain entity
- [x] 內建模板（service 層 `_get_builtin_templates`）
- [x] `plan_table(operation="templates")` 列出
- [x] `plan_table(operation="from_template", ...)` 建表
- [x] 測試 `test_citation_audit.py::TestTableTemplate`

#### Phase 5: Source Discovery ✅

- [x] `discover_sources(query, doc_ids, include_kg)` — 跨資產搜尋
  - 返回含 `AssetRef` 的統一結果，Agent 可直接用於 citation
  - 整合 `DocumentService` + `KnowledgeService`
- [x] 支援搜尋 sections, tables, figures + Knowledge Graph

---

#### Export 含引用

**Markdown（腳註格式）：**
```markdown
| Drug    | Dose     | Side Effects    |
|---------|----------|-----------------|
| Aspirin | 100mg [1]| Bleeding [1][2] |

**References:**
[1] doc_xxx/sec_methods (p.5): "dose was 5mg/kg"
[2] user_input: "Patient reported bleeding"
```

**Excel：**
- 主 sheet：表格資料
- References sheet：所有引用清單
- 每個 cell 加入 Excel 批註 (comment)

---

#### 做表 vs 拆解：解耦但共存

```
┌──────────────────────────────────────────────────┐
│                   MCP Server                      │
│                                                   │
│  ┌─ PDF 拆解 ──────┐  ┌─ 做表 (A2T) ──────────┐  │
│  │ ingest_documents │  │ table_manage           │  │
│  │ inspect_manifest │  │ table_data             │  │
│  │ fetch_asset      │  │ table_cite             │  │
│  │ section tools    │  │ table_draft            │  │
│  │ ...              │  │ plan_table             │  │
│  └───────┬──────────┘  └─────────┬─────────────┘  │
│          │                       │                 │
│          │    AssetRef 橋接      │                 │
│          └───────┬───────────────┘                 │
│                  ▼                                 │
│  ┌─ discover_sources ──────────────────────────┐  │
│  │ 統一搜尋入口：PDF 資產 / KG / 外部 / 使用者   │  │
│  └─────────────────────────────────────────────┘  │
│                                                   │
└──────────────────────────────────────────────────┘

做表完全不需要先拆解 PDF！
Agent 可以直接：
  plan_table → table_manage(create) → table_data(update_cell + citation)
來源可以是使用者口述、外部 URL、或 PDF 資產
```


---

### v0.3.0 - Asset Registry + 批量處理

> v0.2.14 已解耦做表 vs 拆解。v0.3.0 聚焦**資產統一管理與批量操作**。

**Phase 1: Asset Registry（資產註冊中心）**
- [ ] 新增 `AssetRegistry` 類別 — 啟動時掃描 `data/` 建立索引
- [ ] 追蹤所有已存在資產（MD、圖片、表格、KG）
- [ ] `list_available_assets` MCP tool — 列出所有已存在資產

**Phase 2: Asset Bundle（批次讀取）**
- [ ] `get_asset_bundle` - 批次獲取多種資產
- [ ] `get_existing_image` - 直接讀取已存在圖片（不重新拆解）
- [ ] Token 消耗優化

**Phase 3: 多文件合併**
- [ ] `create_table_from_text()` - 直接從文字/Markdown 建表
- [ ] 支援多檔案合併彙整

**詳見**: [docs/ARCHITECTURE_REFACTOR_PROPOSAL.md](docs/ARCHITECTURE_REFACTOR_PROPOSAL.md)

## 設計決策 💡

| 日期 | 決策 | 理由 |
|------|------|------|
| 2025-12-26 | PyMuPDF 為核心 PDF 後端 | 輕量 (~50MB) vs Docling (~2GB)，夠用優先 |
| 2026-02-05 | Marker 作為高精度備選 | `use_marker=True` 啟用，含 bbox 座標 |
| 2026-02-09 | DDD 4 層架構 | Domain/Application/Infrastructure/Presentation 分離 |
| 2026-02-09 | Draft 系統 (斷點續傳) | 長表格工作流程不受對話中斷影響 |

> 完整決策記錄見 `memory-bank/decisionLog.md`

---

## 計劃中 📋

### v0.4.0 - 知識圖譜強化
- [ ] LightRAG 索引問題修復
- [ ] 跨文件知識查詢優化
- [ ] Figure Caption 自動提取
- [ ] 表格偵測優化 (複雜表格)

### v0.5.0 - 進階功能
- [ ] Mistral OCR 整合 (高保真度解析)
- [ ] 醫學術語 NER (Named Entity Recognition)
- [ ] 效能優化 (大檔案處理)
- [ ] Batch 處理 API

### v0.6.0 - 批量與報告
- [ ] 多文件比較功能
- [ ] 自動報告生成 (Markdown/PDF)
- [ ] 批量處理進度追蹤

### v1.0.0 - 正式版
- [ ] 完整醫學文獻 RAG 系統
- [ ] 多語言支援 (i18n)
- [ ] Docker 部署配置
- [ ] Web UI 介面 (Optional)
- [ ] 測試覆蓋率 80%+
