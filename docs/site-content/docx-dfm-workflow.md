<!-- Generated from DOCX-DFM-Workflow.md by scripts/build_docs_site.py -->

# DOCX DFM Workflow

## 核心概念

DFM 是 Docx-Flavored Markdown，用於讓 LLM 或 agent 編輯 Word 文件時仍能保留 block identity、格式 metadata、表格結構與保真寫回能力。

來源：`src/application/docx_service.py`、`src/infrastructure/docx_adapter.py`、`src/infrastructure/dfm_parser.py`、`src/infrastructure/dfm_renderer.py`、`src/infrastructure/docx_validator.py`、`src/application/dfm_integrity.py`。

## Ingest

`ingest_docx(file_path=...)` 支援 `.docx` / `.docm`，並可透過 LibreOffice headless conversion 攝入 `.doc` / `.odt` / `.ods`。轉換時會避免覆蓋既有 sibling `.docx`，DOC/PDF/ODT 等輸出也需要本機可用的 LibreOffice。

輸出包含：

- `DocxIR`（`ir.json`，每次 `save_docx` 更新為目前狀態）
- `baseline_ir.json`（ingest 時的不可變 IR，描述 `original.docx`）
- `original.docx`（原始 package，永不修改）
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

### 累積寫回（cumulative write-back）

每次 `save_docx` 都以 `original.docx` 為底，寫入「自 ingest 以來」所有與
`baseline_ir.json` 不同的區塊，而不只是本次 DFM 的修改：

- 第二次、第三次儲存會保留先前儲存過的編輯，不需要重新套用。
- 重新儲存未修改的 DFM（no-op save）仍會輸出含全部編輯的文件；
  只有內容與原始文件完全相同時，輸出才會是 `original.docx` 的位元組複本。
- `docx_table_from_context` 等只更新 `ir.json` 的操作，也會在下一次儲存寫入。
- 未編輯的區塊與其他 package parts 保持位元組不變。
- Post-save integrity check 以 `original.docx` 為比較基準，逐一確認每個預期
  變更都出現在輸出中；任何編輯遺失都會讓儲存失敗，而不是回報成功。
- 回傳的 `changed_block_ids` 是輸出相對原始文件的所有變更區塊，
  `edited_block_ids` 是本次請求修改的區塊。

v1.4.1 以前建立的文件目錄沒有 `baseline_ir.json`。下一次儲存會先驗證
`original.docx` 的 SHA-256 與 ingest checksum 相符，再從 `original.docx`
重建基準並檢查 block 結構與 `ir.json` 一致；成功時寫入 `baseline_ir.json`，
並在 warnings 列出先前已存在、舊版輸出可能遺漏的編輯。無法驗證時（原始檔被
替換、結構不符、基準檔損毀）會拒絕儲存且不寫入任何檔案，請重新 ingest 並從
`content.dfm`（或 `.backups/`）重新套用編輯。

### 輸出位置

`output_path` 預設為 `data/{doc_id}/output.docx`。相對路徑會解析到文件目錄內，
絕對路徑也必須位於 `data/{doc_id}/` 內，否則回傳
`Output path must stay within document directory`；`original.docx`、`ir.json`、
`baseline_ir.json` 等保留檔不可覆寫。`save_docx` 不會改寫使用者的來源檔案。

要寫回使用者原本的位置，請用 native file asset 流程：
`document(op="native")` 的 `register` 登記來源檔 → `read_docx` /
`update_docx` 建立新版本 → `writeback`（需要 `expected_revision` 與
`expected_source_sha256`，會檢查來源檔 hash/stat 是否已被外部修改並保留備份），
或用 `publish` 建立新的外部檔案。詳見 [Native File Assets](#/native-file-assets)。

## Track Changes

`save_docx(track_changes=true)` 會輸出 Word 原生 `w:del` / `w:ins` revisions，並產生 `revisions.jsonl` sidecar。

修訂的比較基準由 `revision_base` 決定：

| `revision_base` | 輸出 |
|---|---|
| `original`（預設） | 自 ingest 以來的所有編輯都標成修訂，相對於原始文件；適合 IRB/PI 審查 |
| `last_save` | 先前儲存過的編輯以已接受的純文字寫入，只把本次相對於上次儲存狀態（本次請求前的 `ir.json`）的變更標成修訂；適合多輪審查 |

要求 Track Changes 但輸出沒有新增任何 `w:ins` / `w:del` 時，儲存會失敗；
內容與修訂基準相同時會成功但回傳「no Word revisions were written」警告，
不會把原始文件的複本當成已追蹤修訂的結果。

每筆 revision 會包含：

- block id
- old/new text hash
- char/byte range
- context
- locator metadata
- author/time metadata
- `revision_base`

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
