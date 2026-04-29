# Active Context

> 📌 當前工作焦點和進行中的變更

## Current Goals

- 正在完成 0.6.14 release prep：整合 Asset-Aware VSIX assistant harness auto-sync、Copilot/Cline/Codex MCP config conservative merge，以及 DOCX Track Changes → DFM revision review blocks；本輪會完成 MEM+GIT+PUSH+TAG 發布。

## 🎯 當前焦點

- **Release gate parity 已落地**：GitHub CI、tagged release workflow、local `scripts/release.sh` 現在共享 Python/extension/Cline/artifact/Docker/version consistency 檢查
- **VSIX 發布安全已加固**：package content test 會拒絕 `out/test/**`，publish workflow 只發布已驗證的 `.vsix`
- **VSIX install smoke 已 fail-closed**：安裝後找不到 extension 不再 fallback 到 workspace root；Linux CI 會在 `xvfb` 下要求 extension activation 成功
- **Cline harness 可發版檢查已制度化**：新增 release harness audit，覆蓋 `.clinerules` workflows、`.cline/skills`、`.claude/skills` 與 Cline MCP setup helper
- **當前版本真相為 0.6.14**：本次 patch 版本保留 0.6.13 release hardening，並新增 VSIX assistant harness auto-sync / external MCP conservative merge / DOCX Track Changes DFM review support
- **Agent asset 全覆蓋規劃已補齊**：新增 `docs/agent-asset-gap-analysis.md`，明確拆成格式轉換、資產拆解、結構導航、語義理解四層，並量化目前完成度約 35%
- **建議採分段發布**：先發格式入口補齊（RTF/TXT/MD/CSV/HTML），再發 XLSX 原生化，其次是 agent 理解增強，最後才是 PPTX/EPUB/EML 等高成本格式
- **Section truth 已收斂**：manifest generator 現在是 section metadata 最終寫入點；Marker ingest 不再先算 section 再被 generator 用另一套規則覆蓋
- **Line span 正式化完成**：fetch asset 已可直接回傳 line range / section context，Marker blocks 也在 ETL 階段持久化 line span
- **Segmentation correctness 修復完成**：已修正 stale `original.pdf`、same-page asset 錯配與 section line range 顯示語意
- **MCP 處理可視化**：已把 progress 從單純 ETL 擴展到 segmentation、layout overlay、OCR、knowledge graph、table render
- **v0.5.2 已發布**：Marker optional + Server 版本釘定 + Windows DLL 錯誤修正
- **版本釘定**：Extension 啟動時 `--from asset-aware-mcp==X.Y.Z`，版本變更自動 `--upgrade`
- **Windows 修正**：`except (ImportError, OSError)` 捕獲 torch DLL 載入失敗
- **save_docx 穩定化**：MCP/agent 透過 TableContext 改表格後，`save_docx` 先同步 IR/DFM，再輸出 DOCX，避免最後一步產生空白內容

## 🆕 ETL / Layout / OCR 可視化 (2026-03-18)

- `src/domain/segmentation.py`：新增 `DocumentSegment` / `DocumentSegmentation`
- `src/application/segmentation_service.py`：整合 manifest + blocks + assets + reading order，輸出 `segmentation.json`
- `segmentation.json` 現在同時保留 `reading_order` 與 `line_start` / `line_end`，可用於內容流理解與精準行號引用
- `src/domain/line_spans.py`：新增 page-aware / section-aware line span index，對重複句子會先在 page 與 section 範圍內定位
- `blocks.json` 現在會持久化 `line_start` / `line_end` / `line_match_strategy` 等 metadata；舊資料在 export segmentation 時會自動 backfill
- `fetch_document_asset` 現在直接回傳 asset 的 line range、section、source block，減少 agent 端額外查詢成本
- `FigureAsset` / `TableAsset` 追加 `source_block_id` / `source_order`，segmentation 會優先按來源 block 身分配對，避免同頁多資產錯配
- `src/infrastructure/layout_visualizer.py`：以 `original.pdf` 或白底畫布渲染 bbox overlay
- `src/infrastructure/ocr_processor.py`：封裝 `ocrmypdf`，支援 `language` / `rotate_pages` / `deskew`
- `DocumentService`：每次 ingest 會覆蓋保存最新 `original.pdf`，可選 OCR 後再進 ETL；`JobService` step 數跟隨 OCR 階段
- `document_tools.py`：新增 `export_document_segmentation`、`visualize_document_layout`、`ocr_pdf_document`
- `document_resources.py`：新增 `document://{doc_id}/segmentation`
- `vscode-extension`：Documents tree 相容新 manifest 結構，並顯示 segmentation 與 ETL jobs 概況
- 驗證結果：`uv run pytest tests/unit -q` → 384 passed；`npm run compile` 通過

## 🆕 Reading Order 與行號並存 (2026-03-18)

- `src/domain/reading_order.py`：新增顯式 `ReadingOrderPolicy`
- policy 不取代 line-level citation；`DocumentSegment` 另存 `line_start` / `line_end`
- 排序依據分離為兩軸：
    - `reading_order`：回答「內容應該怎麼讀」
    - `line_start/end`：回答「這段資訊在 markdown 第幾行」
- Marker block metadata 會保存 `source_order`，segmentation 匯出時再套用 type/caption/non-text policy
- 驗證結果：`uv run pytest tests/unit -q` → 379 passed

## 🆕 MCP Progress / Logging (2026-03-18)

- `src/presentation/mcp_context.py`：封裝安全 progress/log helper
- `DocumentService.ingest()`：新增可選 progress callback，提供每個檔案內部 phase 訊號
- `JobService`：改接真實 ingest phase，不再手動模擬 job 階段
- 已接入 progress 的工具：
    - PDF：`ingest_documents`、`parse_pdf_structure`、`convert_pdf_to_docx`
    - DOCX：`ingest_docx`、`save_docx`、`convert_docx_to_doc`、`convert_docx_to_pdf`、`docx_validate_roundtrip`、`export_markdown`
- 驗證結果：`uv run pytest tests/unit -q` → 368 passed

## 🆕 v0.4.0 新功能

### 文件級 CRUD 與互轉 (2026-03-09)
- `delete_document` / `delete_docx` / `list_docx_documents`
- `convert_docx_to_pdf` / `convert_docx_to_doc` / `convert_pdf_to_docx`
- `scripts/dfm_cli.py` 新增 `to-pdf`、`to-doc`、`validate --strict`

### 保真與安全強化 (2026-03-09)
- `DocxValidator.validate(..., strict=True)` fail-closed 驗證
- `DocxService.save_docx()` 新增 unedited block mutation guard
- Proposal 真實文件通過 DOCX→DFM→DOCX、DOCX→PDF、DOCX→DOC 實戰驗證

## 🛡️ v0.3.3 新功能

### 生產強化 (2026-02-22)
- Dockerfile multi-stage build
- PDF magic byte 驗證
- 並行 Job 上限 MAX_CONCURRENT_JOBS=5
- Structured logging
- 37 個新 MCP 工具層測試

### .doc 格式支援 (2026-02-23)
- `ingest_docx` 自動偵測 `.doc` 格式，透過 LibreOffice 轉換為 `.docx`
- `_convert_doc_to_docx()` — LibreOffice headless 模式轉換

### Markdown 跳脫修復 (2026-02-23)
- `_escape_md()` / `_unescape_md()` — 跳脫 `*`, `~`, `^` 防止文字被誤判為格式標記
- Run 合併優化 — 相鄰相同格式的 runs 先合併再產生 Markdown
- Caption 偵測修正 — 排除 `**...**` bold 模式的誤判
- CLI import path 修正 — `src.application.docx_validator` → `src.infrastructure.docx_validator`

## Docx DFM 系統概要 (v0.3.0)

### 12 個 Docx MCP 工具
| Tool | 類別 | 功能 |
|------|------|------|
| `ingest_docx` | Core | 匯入 .docx → DocxIR → DFM |
| `get_docx_content` | Core | 讀取指定區塊 DFM 內容 |
| `save_docx` | Core | DFM 編輯寫回 .docx |
| `list_docx_blocks` | Core | 列出文件區塊結構 |
| `list_docx_documents` | Core | 列出所有已攝入 DOCX/DFM 文件 |
| `delete_docx` | Core | 刪除已攝入 DOCX/DFM 與本地 artifacts |
| `convert_docx_to_pdf` | Core | 以保真模式輸出 PDF |
| `convert_docx_to_doc` | Core | 以保真模式輸出 DOC |
| `docx_validate_roundtrip` | Validator | 6 維度往返保真驗證 + strict fail-closed |
| `docx_table_to_context` | Bridge | Docx 表格 → A2T 上下文 |
| `docx_table_from_context` | Bridge | A2T 表格 → Docx 表格 |
| `docx_chart_data` | Bridge | 提取 Docx 圖表數據 |

### DocxValidator 6 維度
- 結構 (Structure) / 文字 (Text) / 格式 (Formatting) / 表格 (Table) / 媒體 (Media) / 樣式 (Style)
- 加權評分：text=0.35, structure/format/table=0.15, media/style=0.10
- Emoji 等級：🟢 ≥95% / 🟡 ≥80% / 🟠 ≥60% / 🔴 <60%

## 📁 專案結構

```
src/
├── domain/          # 🔵 核心業務邏輯 (+docx_entities, docx_value_objects)
├── application/     # 🟢 使用案例 (+docx_service, dfm_table_bridge)
├── infrastructure/  # 🟠 外部依賴實作 (+docx_adapter, dfm_parser, dfm_renderer, docx_validator)
└── presentation/    # 🔴 MCP Server (48 tools in 7 modules, 13 resources)
    ├── tools/
    │   ├── document_tools.py   # ETL + document management (11)
    │   ├── docx_tools.py       # Docx DFM + conversion (14) — core + validator + bridge
    │   ├── section_tools.py    # Navigation (5)
    │   ├── job_tools.py        # Job (3)
    │   ├── knowledge_tools.py  # KG (2)
    │   ├── profile_tools.py    # Profile (5)
    │   └── table_tools.py      # A2T (7) — operation-based
    └── resources/              # 13 resources
```

## 📝 新功能 (v0.3.1)

### 分離格式 (Split Format)
- `content.md` — 乾淨 Markdown，`<!-- @ID -->` 標記（預覽不可見），減少 78% 雜訊
- `format.yaml` — 所有格式元資料（runs, cell_formats, merged_cells…）
- `content.dfm` — 原格式保留（MCP 工具用）

### DFM CLI 工具
- `scripts/dfm_cli.py` — 互動式選單（匯入/開啟/存檔/驗證/列表/一鍵流程）
- `.vscode/tasks.json` — 6 個 VS Code Tasks

### Bug 修復
- `docx_adapter._update_table_text()` — 在更新第一個 run 後清除後續 runs，修復表格文字重複

## ⚗️ 待解決

1. **測試覆蓋率**: 目標 60%+
2. **文件缺乏**: API Reference, Examples, FAQ

---
*Last updated: 2026-04-24*
