<!-- Generated from DOCX-DFM-Workflow.md by scripts/build_docs_site.py -->

# DOCX DFM Workflow

![DOCX and DFM round-trip workflow](wiki/assets/docx-dfm-workflow.jpg)

## 核心概念

DFM 是 Docx-Flavored Markdown，用於讓 LLM 或 agent 編輯 Word 文件時仍能保留 block identity、格式 metadata、表格結構與保真寫回能力。

來源：`src/application/docx_service.py`、`src/infrastructure/docx_adapter.py`、`src/infrastructure/dfm_parser.py`、`src/infrastructure/dfm_renderer.py`、`src/infrastructure/docx_validator.py`、`src/application/dfm_integrity.py`。

## Ingest

`ingest_docx(file_path=...)` 支援 `.docx` 與 legacy `.doc`。`.doc` 透過 LibreOffice headless conversion 轉成 `.docx`，且會避免覆蓋既有 sibling `.docx`。

輸出包含：

- `DocxIR`
- `content.dfm`
- `content.md`
- `format.yaml`
- media/assets
- original package XML parts

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

`save_docx` 會在 pre-save、write、post-save 階段執行 DFM integrity checks。嚴重錯誤會 fail closed，除非呼叫端明確使用 `force=true`。

## Track Changes

`save_docx(track_changes=true)` 會輸出 Word 原生 `w:del` / `w:ins` revisions，並產生 `revisions.jsonl` sidecar。每筆 revision 會包含：

- block id
- old/new text hash
- char/byte range
- context
- locator metadata
- author/time metadata

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

| Tool | 目標 |
|---|---|
| `convert_docx_to_pdf` | PDF |
| `convert_docx_to_doc` | legacy DOC |
| `convert_docx_to_odt` | ODT |
| `export_markdown` | Markdown text/file -> DOCX/PDF/DOC |

## Table And Chart Bridge

| Tool | 用途 |
|---|---|
| `docx_table_to_context` | DOCX table block -> A2T TableContext |
| `docx_table_from_context` | TableContext -> DFM table block |
| `docx_chart_data` | DOCX chart data -> TableContext |
| `docx_table(...)` | consolidated bridge |

這讓 Word 內的表格可以進入 A2T 編輯、引用、history 和 rendering pipeline，再安全寫回文件。
