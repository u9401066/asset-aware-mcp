# DOCX DFM Workflow

## 核心概念

DFM 是 Docx-Flavored Markdown，用於讓 LLM 或 agent 編輯 Word 文件時仍能保留 block identity、格式 metadata、表格結構與保真寫回能力。

來源：`src/application/docx_service.py`、`src/infrastructure/docx_adapter.py`、`src/infrastructure/dfm_parser.py`、`src/infrastructure/dfm_renderer.py`、`src/infrastructure/docx_validator.py`、`src/application/dfm_integrity.py`。

## Ingest

`ingest_docx(file_path=...)` 支援 `.docx` / `.docm`，並可透過 LibreOffice headless conversion 攝入 `.doc` / `.odt` / `.ods`。轉換時會避免覆蓋既有 sibling `.docx`，DOC/PDF/ODT 等輸出也需要本機可用的 LibreOffice。

Ingest 是冪等的：同一份檔案已攝入時會回傳既有文件狀態（`existing: true`、目前
`revision`、已編輯的 `changed_block_ids`），所有已儲存/已 commit 的編輯都保留，
所以每個工作階段或 agent 都可以安全地先 ingest。要捨棄所有編輯、從來源檔重建，
必須明確傳 `reset=true`（會先備份；有他人有效租約時拒絕）。

輸出包含：

- `DocxIR`（`ir.json`，每次 `save_docx` 更新為目前狀態）
- `baseline_ir.json`（ingest 時的不可變 IR，描述 `original.docx`）
- `edit_state.sqlite3`（內容 revision 歷史、區塊租約、修訂作者；見下方多 agent 編輯）
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

`save_docx` 會在 pre-save、write、post-save 階段執行 DFM integrity checks。安全寫回主要支援文字與既有 table cell 內容更新，並保留現有 table shape；結構性表格修改會 fail closed。`force=true` 只會略過內容縮減 fail-safe 與 post-save integrity 失敗，不會讓不支援的結構改寫變成安全操作，也**不會**略過 revision 衝突、區塊租約或來源 checksum 不符。不在任何 block marker 內的文字會被忽略並回報 `UNMARKED_TEXT` 警告（DFM 不能新增區塊）。

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

### 多 agent 併發編輯：revision 與區塊租約（1.5.0）

`content.dfm` front matter 的 `checksum` 是原始檔的 SHA-256（來源身分），
ingest 後永不改變；`revision` 則是**內容版本**，每次成功儲存都會改變。1.5.0 以前
兩個 client 讀同一份 DFM、先後儲存不同段落時，後者會默默還原前者的編輯；現在：

- 每個寫入操作都在文件鎖（`edit_state.sqlite3` 的 `BEGIN IMMEDIATE`，跨 process
  有效）中執行。
- `save_docx` 收到較舊 `revision` 的 DFM 時做 **3-way merge**：只套用你相對於
  base 改過的區塊，保留別人在之後改過的區塊（回傳 `revision_merge.mode="merged"`）；
  若同一區塊兩邊都改過，拒絕並回傳 `conflict_block_ids`，不寫入任何檔案。
- 沒有 `revision` 的舊 DFM 只在 ingest 後從未儲存、或剛升級的 1.4.x 目錄尚無任何
  新儲存時接受；1.4.x 目錄升級後第一個操作會自動替未修改的檔案補上 `revision`。
- split 格式（`from_md=True`）的基準 revision 只取自 `content.md`。
- 保留最新 50 個 revision；更舊的 DFM 需重新開啟。
- 成功儲存回傳 `revision_front_matter`（buffer 與儲存結果相同時）：繼續編輯同一份
  DFM 時，把 front matter 的 `revision:` 行換成它，否則下次儲存可能把你自己先前
  的儲存視為衝突；回傳 `reopen_before_next_save` 時請重新讀取。
- 共用的 `content.dfm` / `content.md` / `format.yaml` 若有尚未儲存的就地編輯，其他
  agent 的儲存不會覆蓋它們，最新內容改寫到 `content.current.*` 並發出警告；之後用
  `save_docx`（`from_md=True` 或不帶 `dfm_content`）儲存就地編輯即可 3-way merge。

讓多個 agent（Claude Code subagents、Copilot、Cline、Codex）同時編輯不同區塊，
建議使用區塊租約：

```text
docx(op="list_blocks", doc_id="...")                      # 找出要改的區塊
docx(op="checkout", doc_id="...", block_ids=["p005"],
     holder="claude-methods", ttl_seconds=900)            # 取得 lease_token + 片段
# 只編輯回傳的片段（保留 marker 行）
docx(op="commit", doc_id="...", lease_token="...",
     edits={"p005": "<!-- @b:p005 -->\n新的段落文字"},
     track_changes=true)                                  # 套用到最新文件並釋放
docx(op="release", doc_id="...", lease_token="...")       # 放棄時歸還
docx(op="leases", doc_id="...")                           # 查看誰持有哪些區塊
```

- checkout 遇到他人有效租約立即失敗（回報 holder 與到期時間），不會阻塞等待；
  巢狀表格與父表格一起租用。可帶 `request_id`：回應遺失時用同一個 `request_id`
  重試會取回同一個租約與新 token；回應被截斷時 `lease_token` 一定保留。
- commit 只接受租約內區塊，套用在**目前**文件上（保留他人已 commit 的區塊），
  走相同的累積寫回與 post-save 驗證；`track_changes=true` 時作者預設為 holder，
  Word 會顯示哪個 agent 改了哪一段。
- 全文 `save_docx` 與 `docx_table_from_context` 會拒絕修改被他人租用的區塊。
- 租約預設 900 秒、上限 3600 秒；不要在閒置期間持有租約，編輯完立即 commit，
  需要更久時用 `renew`。過期租約可被他人回收，或用 `break_lease` 清除（有效租約需
  `force=true`，屬管理操作）。
- Native `update_docx` 仍以文件層級 `expected_revision` 序列化（native block ID 只在
  單一 revision 有效）；過期錯誤會提示改用上述租約流程。
- 所有編輯同一個 DATA_DIR 的 client 都必須是 ≥ 1.5.0；舊版 server 不參與鎖。
- DATA_DIR 在 Google Drive（「我的雲端硬碟」）、OneDrive、Dropbox、iCloud 或網路
  磁碟時仍可使用，但結果與 `asset-aware-mcp doctor` 會警告：鎖只在同一台電腦有效，
  請一次只從一台電腦編輯同一份文件。

完整規格見 `docs/dfm-spec.md` §12。

### 輸出位置

`output_path` 預設為 `data/{doc_id}/output.docx`。相對路徑會解析到文件目錄內，
絕對路徑也必須位於 `data/{doc_id}/` 內，否則回傳
`Output path must stay within document directory`；`original.docx`、`ir.json`、
`baseline_ir.json` 等保留檔不可覆寫。`save_docx` 不會改寫使用者的來源檔案。

要寫回使用者原本的位置，請用 native file asset 流程：
`document(op="native")` 的 `register` 登記來源檔 → `read_docx` /
`update_docx` 建立新版本 → `writeback`（需要 `expected_revision` 與
`expected_source_sha256`，會檢查來源檔 hash/stat 是否已被外部修改並保留備份），
或用 `publish` 建立新的外部檔案。詳見 [Native File Assets](Native-File-Assets)。

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
- `revision_author`（每個區塊的修訂作者；多 agent 時為 lease holder）

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
