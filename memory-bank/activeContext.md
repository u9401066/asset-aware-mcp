# Active Context

> 📌 當前工作焦點和進行中的變更

## 🎯 當前焦點

- **v0.3.0 已完成**：Docx DFM 即時編輯系統 + DocxValidator + DfmTableBridge
- **下一步**：測試覆蓋率提升 / 文件與推廣

## Docx DFM 系統概要 (v0.3.0)

### 8 個 Docx MCP 工具
| Tool | 類別 | 功能 |
|------|------|------|
| `ingest_docx` | Core | 匯入 .docx → DocxIR → DFM |
| `get_docx_content` | Core | 讀取指定區塊 DFM 內容 |
| `save_docx` | Core | DFM 編輯寫回 .docx |
| `list_docx_blocks` | Core | 列出文件區塊結構 |
| `docx_validate_roundtrip` | Validator | 6 維度往返保真驗證 |
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
└── presentation/    # 🔴 MCP Server (36 tools in 7 modules, 12 resources)
    ├── tools/
    │   ├── document_tools.py   # ETL (6)
    │   ├── docx_tools.py       # Docx DFM (8) — core + validator + bridge
    │   ├── section_tools.py    # Navigation (5)
    │   ├── job_tools.py        # Job (3)
    │   ├── knowledge_tools.py  # KG (2)
    │   ├── profile_tools.py    # Profile (5)
    │   └── table_tools.py      # A2T (7) — operation-based
    └── resources/              # 12 resources
```

## ⚠️ 待解決

1. **測試覆蓋率**: 目標 60%+
2. **文件缺乏**: API Reference, Examples, FAQ

---
*Last updated: 2026-02-11*
