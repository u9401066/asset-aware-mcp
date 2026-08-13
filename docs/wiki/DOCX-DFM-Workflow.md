# DOCX DFM Workflow

## 核心概念

DFM 是 Docx-Flavored Markdown，用於讓 LLM 或 agent 編輯 Word 文件時仍能保留 block identity、格式 metadata、表格結構與保真寫回能力。

來源：`src/application/docx_service.py`、`src/infrastructure/docx_adapter.py`、`src/infrastructure/dfm_parser.py`、`src/infrastructure/dfm_renderer.py`、`src/infrastructure/docx_validator.py`、`src/application/dfm_integrity.py`。

## Ingest

`ingest_docx(file_path=...)` 支援 `.docx` / `.docm`，並可透過 LibreOffice headless conversion 攝入 `.doc` / `.odt` / `.ods`。轉換時會避免覆蓋既有 sibling `.docx`，DOC/PDF/ODT 等輸出也需要本機可用的 LibreOffice。

輸出包含：

- `DocxIR`
- `content.dfm`
- `content.md`
- `format.yaml`
- media/assets
- original package XML parts

每個 DFM block 也會保留 DOCX locator metadata，包含 `locator_version`、
`source_part`、`source_story`、`source_element`、`source_order`、
`paragraph_index` 或 `table_index`、文字 `char_range` / `byte_range` /
`text_sha256`，以及 paragraph 的 `run_ranges`。表格 block 另外保存
`row_count`、`column_count` 與 `cell_locators`；nested table 會保留
`parent_table_id` 和 `parent_cell`。

## Editing

讀取內容：

```text
get_docx_content(doc_id="...")
get_docx_content(doc_id="...", block_id="p001")
list_docx_blocks(doc_id="...")
```

寫回內容：

```text
save_docx(
  doc_id="...",
  dfm_content="...",
  track_changes=true,
  revision_author="Asset-Aware MCP"
)
```

`save_docx` 會在 pre-save、write、post-save 階段執行 DFM integrity checks。安全寫回主要支援文字與既有 table cell 內容更新，並保留現有 table shape；結構性表格修改會 fail closed。`force=true` 只會略過部分 stale/drift safeguards，不會讓不支援的結構改寫變成安全操作。

## Track Changes

`save_docx(track_changes=true)` 會輸出 Word 原生 `w:del` / `w:ins` revisions，並產生 `revisions.jsonl` sidecar。每筆 revision 會包含：

- block id
- old/new text hash
- char/byte range
- context
- locator metadata
- author/time metadata

locator metadata 會帶回原始 Word part，例如 `word/document.xml`、
`word/header*.xml`、`word/footer*.xml` 或 `word/footnotes.xml`，並在可用時
包含 paragraph/table/run/cell index，讓 Word 表單也能像 PDF span 一樣被
promotion 前重新定位與查核。

這讓 agent 修改可以回到 Word review workflow，同時保留 citation-ready evidence trail。

## Validation

`docx_validate_roundtrip(doc_id, strict=true)` 檢查：

- structure
- text
- formatting
- table
- media
- style
- header/footer/footnote story parts
- table-cell direct formatting

Strict mode 會抓 run-level formatting drift，不只比較 body text。

## Conversion

DOCX/DFM conversion 現在預設建立 background conversion job，避免 LibreOffice 或大型輸出卡住 MCP request path。所有 conversion tool 都保留 `async_mode=false` 作為同步相容路徑。

| Tool | 目標 |
|---|---|
| `convert_docx_to_pdf` | PDF |
| `convert_docx_to_doc` | legacy DOC |
| `convert_docx_to_odt` | ODT |
| `export_markdown` | Markdown text/file -> DOCX/PDF/DOC/ODT |

## Table And Chart Bridge

| Tool | 用途 |
|---|---|
| `docx_table_to_context` | DOCX table block -> A2T TableContext |
| `docx_table_from_context` | TableContext -> DFM table block |
| `docx_table_edit_plan` | 寫回前預覽 update_cell / add_rows / delete_rows / add_columns / rename_columns 與 structural risk |
| `docx_chart_data` | DOCX chart data -> TableContext |
| `docx_table(...)` | consolidated bridge，支援 `op="edit_plan"` |

這讓 Word 內的表格可以進入 A2T 編輯、引用、history 和 rendering pipeline，再安全寫回文件。若 `docx_table_edit_plan` 顯示 structural change，建議先輸出 copy、套用後跑 `docx_validate_roundtrip(strict=true)`，不要把 row/column 變更當成單純 cell text update。
