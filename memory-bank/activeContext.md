# Active Context

> 📌 當前工作焦點和進行中的變更

## 🎯 當前焦點

- **v0.5.0 發布中**：完成多行儲存格保護、Markdown 匯出、Ollama API 修復等功能
- **下一步**：完成 v0.5.0 tag、push、marketplace 發布

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
└── presentation/    # 🔴 MCP Server (43 tools in 7 modules, 12 resources)
    ├── tools/
    │   ├── document_tools.py   # ETL + document management (8)
    │   ├── docx_tools.py       # Docx DFM + conversion (12) — core + validator + bridge
    │   ├── section_tools.py    # Navigation (5)
    │   ├── job_tools.py        # Job (3)
    │   ├── knowledge_tools.py  # KG (2)
    │   ├── profile_tools.py    # Profile (5)
    │   └── table_tools.py      # A2T (7) — operation-based
    └── resources/              # 12 resources
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
*Last updated: 2026-03-09*
