# Copilot 自定義指令

> 📌 此檔案為 VS Code GitHub Copilot Agent Mode 與 Claude Code 的統一指引。

---

## 專案概述

**MCP Server — Asset-Aware MCP**

| 項目 | 說明 |
|------|------|
| 語言 | Python 3.10+ |
| 框架 | 官方 MCP Python SDK 2 `MCPServer`、LightRAG、PyMuPDF；active optional engines 為 Docling / PyMuPDF4LLM |
| 策略 | 文件→可重用 agent assets；`ETL_ENGINE` active paths 為 pymupdf（快速預設）/ pymupdf4llm（版面感知）/ docling，MinerU/Marker adapter 目前 security hold |

> 🎯 **核心目標**：完整、快速地把文件轉換成「圖、文、表」等 **agent 友善的資產**，並保留精確來源定位（page / bbox / line span）供引用。

### 核心功能

- Native discovery advertises contract_delivery separately from schema_delivery.
  When paged, assemble ALL contract_request / contract_details pages using one
  contract_sha256 and for_op; check UTF-8 text_sha256 before reading complete policies.
  Keep every enabled flag and format/schema continuation from the compact index.
  Rediscover on capability/scope/hash changes; never operate from preview_json.
- When docx_story_structure_enabled is advertised, read_docx_story_structure pins
  revision and pages full catalog/catalog_sha256/latest operation_result. Update
  with expected_revision, docx_story_structure.expected_catalog_sha256, explicit
  scope sections_and_following_inheritors and sequential create/clone/bind/delete/
  first_page/even_pages edits. Clone/delete need exact part hashes. bind part:null
  resumes inheritance, not blank; create/bind an empty paragraph to blank a slot.
  Explicitly rebind following sections when retaining their previous definitions.
  Read every receipt/story and actual page. Supported unique identities are remapped;
  range/control/revision/note/embedded cloning dependencies remain explicit limits.
  Deleted parts retain historical refs/Wikis; orphan media is not securely erased.
  Public1.4.0, next consolidated1.4.1; no per-feature bump.

- When docx_stories_enabled is advertised, read_docx_stories discovers actual
  header/footer definitions, section inheritance and dormant/shared bindings.
  read_docx_story pins docx_story_part; assemble every story page at one text_sha256.
  update_docx_story needs full docx_story_reference and expected_revision; its
  docx_story_update requires part, shared_scope:all_sections_using_part and sequential
  set_text/insert_blocks/delete_blocks edits. Paths/indices address intermediate XML.
  Read complete receipts and all affected actual PNGs. Literal field caches and
  alternate/revision branches are not evaluated results. Preserve historical refs;
  selections/derivations/citations and docx-stories-v1 Wiki retain full evidence.
  Legacy DFM header/footer fields are abbreviated; never infer roles from filenames.
  Definition lifecycle/relinking use the operations above; note stories remain open.
  Public1.4.0; next consolidated1.4.1, no per-feature version bump.

- When docx_table_layout_enabled is advertised, update_docx_table_grid accepts
  set_header_rows(count) and set_row_layout(index,count,height,split). Header rows
  form a contiguous prefix; do not cut a vertical merge. Height rule auto/inherit
  has no value; at_least/exact requires value_twips. Split allow/prevent/inherit
  changes direct properties; omitted fields stay intact. Read full before/after
  operation_result and all current row_layout/native XML pages, then EVERY actual
  Word page PNG. Exact heights can clip; oversized rows can still span pages.
  Inherited styles and Microsoft Word parity require Agent review. Source bytes,
  historical references and Wikis remain intact. Public1.4.0 / Unreleased1.4.x.

- When docx_table_grid_enabled is advertised, read_docx_table requires a full
  docx_table_reference, asset_id and revision. Read all grid/native XML chunks at
  one text_sha256; omitted positions and merged coverage are not empty cells.
  update_docx_table_grid pins expected_revision and full reference; 1..32 sequential
  zero-based insert/delete/resize/merge/split edits use each intermediate grid.
  sizes_twips means minimum row height or fixed column width. merge requires
  require_empty/append_blocks; split keeps anchor content, other cells blank.
  Mutation summaries are bounded; full operation_result is in paged table reads.
  Repeated file SHAs can have newer receipts: verify complete text_sha256.
  Read complete review_request and current references, then all actual Word page
  PNGs. Sources/history/Wiki remain unchanged; table refs are not new cell refs.
  MCP checks native structure/bytes; Agent reviews meaning, inherited styles,
  repeated headers, nested overflow and page flow. Public1.4.0 / Unreleased1.4.x.

- For legacy PDF ETL evidence, discover inspect_etl_source/capture_etl_source/
  read_etl_source/view_etl_source through evidence csl_contract. Inspect selectors
  return complete current AssetRefs without writing; capture requires the whole
  verified ref. Read all hash-pinned pages, then retain etl-citation-ref-v1 and view
  actual captured original PDF pages. Mixed CSL sources accept captured/native
  refs; Wiki retains all snapshot artifacts. ETL deletion cannot change snapshots.
  Hash/locator checks do not prove extraction, semantics or bibliographic truth;
  Agent reviews those and coordinates corrections. Public1.4.0 / Unreleased1.4.x.

- For document-context academic citations, discover evidence(op="csl_contract")
  completely, then render_citations with structured CSL-JSON items and ordered
  clusters. Read every text page at one text_sha256. sources holds full native
  references; source_keys binds cites without overriding canonical locators.
  Printed CSL locators and bibliographic truth require Agent review. wiki_root
  exports immutable citations, source files and a typography preview; use the
  preview hash as expected_text_sha256. Old refs/snapshots remain historical.
  CSL uses optional local Node.js; existing custom display templates remain.
  Public1.4.0 / Unreleased1.4.x; no per-feature version bump.

- When delimited_enabled is advertised, create_delimited creates independent CSV/TSV
  string tables. Pin revisions for read_delimited/read_delimited_cell; logical row/
  column indices are zero-based. Assemble complete JSON at one text_sha256. Explicit
  delimited_dialect binds delimiter/quote/escape/encoding; custom settings must follow
  all reads, edits and Wiki. No header/type inference. update_delimited uses full refs
  for set_cells or explicit row/column positions. Native byte splices retain untouched
  spelling/EOL/BOM; required empty-field/row-separator repairs are recorded. Read the
  complete review_request receipt; no-op updates create no history entry. Same file
  SHA may recur with a newer receipt. verify/selections/derivations/Wiki bind exact
  fields/dialects; old refs never migrate. Agent reviews meaning and downstream
  rendering/formula interpretation. Public1.4.0 / Unreleased1.4.x; no per-feature bump.

- PDF listings/page records may include parser_checks for independently proven
  equal, direct duplicate stream Length values. Keep those observations with the
  evidence; original bytes are unchanged. Other warnings/conflicting/indirect
  lengths still require a separate repair workflow. Requested page edits/copies
  record canonicalized_equal_duplicate_stream_lengths when serialized. Agent
  reviews actual images and meaning; these checks are not an OCR/fidelity verdict.

- When pdf_regions_enabled is advertised, read_pdf_region takes a full PDF page
  reference plus pdf_region.rect in displayed CropBox fractions (0–1, top-left,
  after rotation), or a full existing region reference without selector override.
  Read the complete record and actual PNG; render_size changes detail, not identity.
  Agent checks glyph coverage/transcription and records explicit region-to-cell
  derivations. verify checks geometry/source only; read_selection selects region JSON.
  Wiki retains region JSON/PNG/render metadata and source PDFs. Missing external
  citation metadata is reported, never borrowed from target authors/year. Historical
  assertions do not migrate; sources/history stay unchanged. Public1.4.0 / 1.4.x.


- **工作表尺寸修正（Unreleased／1.4.x）** — `read_worksheet_layout` 固定 revision／worksheet_key，完整讀回尺寸；`update_worksheet_layout` 明確指定點數列高、原始 OOXML 欄寬、重設或隱藏。保留儲存格／樣式，物件沿原錨點規則調整；清除公式及圖表快取。完整讀回紀錄，再由 Agent 產生新 PDF 核對畫面與結果，來源及歷史證據保持；公開版仍 1.4.0。

- **工作簿版面核對（Unreleased／1.4.x）** — `create_workbook_rendition` 固定 XLSX revision，明確指定 print／whole_sheet 與 recalculate／prefer_cache，使用選配 Calc 建立獨立 PDF。完整讀取 `read_rendition` 與所有頁面 PNG；Wiki 附來源 XLSX 及轉換紀錄。隱藏、空白頁、溢出文字及公式結果由 Agent 核對，來源不改寫；公開版仍 1.4.0。

- **原生 Table 合計列（Unreleased／1.4.x）** — `table_totals_lifecycle_enabled` 啟用時，以 `table_update.totals_row` 新增、移除或重用合計定義；新增前檢查空白範圍，移除明確選擇 clear／keep_cells。保留公式固定原 Table 範圍，其他引用保持結構化形式。完整讀回操作紀錄，由 Agent 核對公式結果及版面；公開版維持 1.4.0。

- **原生 Table 建立（main 未發布／1.4.x）** — `workbook_table_creation_enabled` 啟用時，`add_workbook_table` 在固定 worksheet key／ref／revision 建立 Table。可搭配 `create` 獨立建立 XLSX；既有標題須相符或明確填空，合計列須先為空白，計算欄覆寫須明確。保留資料、格式與歷史證據；讀回完整 created_table／header_cells／operation_result，再由 Agent 核對公式結果與畫面。公開版仍 1.4.0。
- **Table 專用編輯（main 未發布／1.4.x）** — `workbook_table_edit_enabled` 啟用時，以 `update_workbook_table` 同步修改欄名／富文字標題／計算欄／既有總計列。先完整讀取 references 與 header_cells XML，固定版本、Table part／ref 與 column_id／expected_name；header_runs 保留段格式，公式例外值須明確處理。新公式使用新欄名，既有引用依身分更新；Agent 核對語意、公式與畫面，舊證據及 A2T 綁定不遷移。公開版仍為 1.4.0。

- **原生 A2T（main 未發布／1.4.x）** — 指定工作簿範圍投影為帶型別的表格，完整讀回固定 hash 與原始格引用。`table_grid_apply_enabled` 啟用時，列欄增刪用 structural_plan 的明確 worksheet_grid 與 table/file revision 一次套回原檔；穩定 column_ids 區分改名與重建。整列欄搬移會影響投影外內容，Table 邊界可用 expand_tables 的 part／當步 expected_ref 明確擴展；native_generated 只保留本次新生成標題／公式。完整 read_workbook.tables 可查原生定義；特殊計算欄編輯與重排另有範圍；Agent 核對語意、公式及版面。完整讀回操作紀錄與不可變快照，來源綁定不自動前進。native contract.for_op 只接受原生操作；table_data/table_manage 使用其 MCP schema。公開版仍 1.4.0。

- **工作表結構（main 未發布／1.4.x）** — `read_workbook` 完整分頁核對工作表／引用清單；新增、改名、重排、刪除使用 expected_revision 與目前 sheet_id／part。`workbook_grid_enabled` 啟用時，`update_worksheet_grid` 循序插刪列欄；位置從 1 起算，每步依前一步完成後的工作表定位，讀回完整操作紀錄與幾何假設。相依及 3D 範圍變動有檢查，原 parts 與歷史證據保留；Agent 核對動態引用、計算結果與畫面。舊 A2T 綁定不自動搬移；相同檔案 SHA 可再次出現，操作紀錄須依當次歷史核對。公開版仍 1.4.0。

- **精確選取（main 未發布／1.4.x）** — `read_selection` 以完整父引用、JSON Pointer 與 Unicode 範圍選取值；分頁核對固定 text_sha256，verify／轉製帳本／Wiki 保留選取證據。範圍對應解析字串，文件更新不自動搬移主張；Agent 核對語意／畫面。

- 📄 **PDF ETL** — 多引擎文件拆解成 agent 資產（圖片、表格、章節、公式），`ETL_ENGINE` 可插拔
- 🩺 **PDF Preflight** — 攝入前唯讀、process-isolated page classification / OCR / engine routing
- 📦 **Agent Asset Export** — deterministic text/table/figure + provenance bundle，可直接形成 Foam subtree
- 🧩 **Segmentation Export** — 統一 segmentation schema（reading order + line span）
- 📊 **Native files** — `document(op="native")` 支援原生檔案版本、XLSX 建立、XLSX/XLSM cells 讀寫、明確回寫與來源同步；完整語意／視覺／公式核對由 Agent 負責。
- 📝 **Native DOCX（1.3.0）** — `read_docx`／`update_docx` 將不可變版本接到 DFM 檢查，更新先建立受管理版本，來源回寫仍明確指定；先查安裝版本 contract。元件引用可用 `read_docx_block`／`verify`，Wiki 使用獨立 projection 保留完整區塊與原始 package parts；完整性不代表抽取完整。
- 📽️ **Native PPTX（1.4.0）** — 原生建立、投影片／備註形狀讀取、精確文字 run 更新、版本引用與完整 package Wiki；先查安裝版本 contract，完整語意／版面／文字溢出由 Agent 核對。`native-contract-v2` 支援 for_op 與 schema_sha256 分段規格。
- 📽️ **PPTX 形狀操作（main 未發布）** — 先查 contract；`add_pptx_shapes` 新增文字框，`delete_pptx_shapes` 使用目前版本完整引用刪除形狀。已知相依會阻擋刪除，附件仍保留；Agent 核對版面與未涵蓋相依，來源回寫仍明確指定。公開版維持 1.4.0／後續 1.4.x。
- 🖼️ **DOCX 整頁預覽（main 未發布）** — `render_docx_page` 以明確 revision／零起算 `docx_page_index` 回傳真實 MCP PNG；需另裝 LibreOffice Writer，依 `next_page_index` 看完目前與歷史版本。每次重新轉換，頁碼屬於該次輸出；Agent 核對語意／版面，不能宣稱已驗證 Microsoft Word 保真。
- 📝 **DOCX 建立與結構（main 未發布）** — `create_docx` 獨立建立段落／表格；`add_docx_blocks`／`delete_docx_blocks` 以目前完整引用操作主本文。合併格、富文字與未修改 parts 會核對；已知範圍／欄位等相依阻擋不支援的刪除，Agent 核對分頁／版面，公開版仍 1.4.0／後續 1.4.x。
- 📽️ **整張投影片預覽（main 未發布）** — `render_pptx_slide` 使用選配 LibreOffice Impress，以 revision／pptx_slide_key 回傳實際 PNG。Agent 比較遮擋、溢出與版面；回報渲染器與已做核對，不能宣稱 PowerPoint 保真驗證。公開版仍 1.4.0。
- 📽️ **PPTX 投影片結構（main 未發布）** — `read_pptx_layouts` 探索版型，`add_pptx_slides` 插頁並建立空白繼承預留位置／文字框；重排與刪頁使用目前版本完整 slide_id／part 清單。保留原 parts，檢查相依／章節／播放範圍；Agent 核對畫面與檢視器快取，仍為 1.4.x 開發。
- 🖼️ **PPTX 圖片（main 未發布）** — `add_pptx_pictures`／`replace_pptx_pictures` 使用版本化 PNG/JPEG 資產，保留共用 media；`read_pptx_picture` 顯示實際內嵌圖片，`extract_pptx_picture` 建立含來源歷程的新資產。`native-file-ref-v1` 只驗證完整不可變位元組。Agent 核對投影片畫面、裁切、效果與語意；公開版仍 1.4.0／後續 1.4.x。
- 📊 **PPTX 原生表格（main 未發布）** — `add_pptx_tables` 新增明確尺寸、合併與文字格式的表格；讀回／修改 anchor run／刪除／證據與 Wiki 沿用原生操作。目的簡報樣式及溢出由 Agent 核對。`citation_contract` typed schema 僅存引用顯示格式，來源證據另行保存。
- 📊 **PPTX 格網（main 未發布）** — `update_pptx_table_grid` 使用完整引用依序列欄插刪與調整尺寸；檢查合併區擴縮、起點移動及隱藏內容衝突。合併須明確選擇 require_empty／append_paragraphs；後者依序搬移完整段落，拆分保留起點內容、不自動分回。Agent 核對新版位置、畫面與轉製關係。
- 🔗 **轉製來源帳本（main 未發布）** — 完整原生引用連結來源與產物；先讀 hash 固定的帳本，再新增／修訂／撤回。MCP 驗證引用，Agent 核對聲明另存；Wiki 保留帳本與活躍關係的來源附件。舊版本主張不會自動繼承。
- 📄 **Native PDF（main 未發布）** — 頁面建立／讀取／PNG 顯示／複製／插刪／重排／旋轉裁切、版本引用與 Wiki；先查 contract，完整頁面引用必須固定版本。MCP 檢查物件圖與有限解析度讀回，Agent 核對語意／完整畫面／表單行為；不提供任意文字編輯或 secure redaction。公開版仍 1.4.0。
- 📊 **A2T** — Anything to Table 表格建立
- 🧭 **Section Navigation** — 動態層級章節導航（5 Tools）
- 🔍 **Knowledge Graph** — 跨文獻知識圖譜（LightRAG）
- 🖼️ **Vision AI** — 圖片分析（base64 返回）
- 🔤 **OCR Preprocessing** — 掃描 PDF 按需前處理

### LLM 後端

- **預設**: Ollama (本地) — CPU `granite4.1:3b`；GPU hint `granite4.1:8b`；`nomic-embed-text` 僅在啟用 LightRAG/KG 時需要
- **備選**: OpenAI (需 API Key)

### PDF → 資產引擎選擇 🚦

透過環境變數 `ETL_ENGINE` 選擇拆解引擎；結構化引擎懶加載，未安裝時自動降級為 PyMuPDF。

| 引擎 | 安裝 extra | 何時使用 | 授權 |
|------|-----------|----------|------|
| `pymupdf`（預設） | 內建 | 快速、數位 PDF、無模型 | AGPL |
| `pymupdf4llm` | `[pdf-plus]` | 低風險升級：版面感知 reading order + 表格 markdown | AGPL |
| `docling` | `[docling]` | 高精度：layout+表格+公式+圖表理解，附輕量 GraniteDocling VLM | MIT |
| `mineru` | security hold（extra 空） | adapter 保留；MinerU 3.4.4 pin `transformers<5`，而 fixes 需要 `>=5.5` | Apache-2.0 衍生 |
| `marker` | security hold（extra 空） | marker-pdf 1.10.2 pin Pillow<11 與安全基線衝突 | — |

- Active Docling / PyMuPDF4LLM extras 已驗證可解析 `Pillow>=12.2.0`；不得用 audit ignore 繞過 held backend 的不可解 graph。
- 結構化 adapters（docling/mineru/marker）實作共通 `StructuredPDFExtractor` Protocol，輸出 `MarkerParseResult`，共用 `_ingest_single_with_marker` 資產管線；held backend 未安裝時降級 PyMuPDF。
- 對應 adapter：`src/infrastructure/{pymupdf4llm,docling,mineru}_adapter.py`；工廠：`extractor_factory.py`。

---

## 開發哲學 💡

> **「想要寫文件的時候，就更新 Memory Bank 吧！」**
>
> **「想要零散測試的時候，就寫測試檔案進 tests/ 資料夾吧！」**

- 不要另開檔案寫筆記，直接寫進 Memory Bank
- 今天的零散測試，就是明天的回歸測試

---

## 法規遵循

你必須遵守以下法規層級：

1. **憲法**：`CONSTITUTION.md` - 最高原則，不可違反
2. **子法**：`.github/bylaws/*.md` - 細則規範
3. **技能**：`.claude/skills/*/SKILL.md` - 操作程序

---

## 架構原則

- 採用 **DDD (Domain-Driven Design)**
- **DAL (Data Access Layer) 必須獨立**
- 依賴方向：`Presentation → Application → Domain ← Infrastructure`
- 參見子法：`.github/bylaws/ddd-architecture.md`

---

## MCP SDK 2 邊界

- 唯一 runtime contract 是 `mcp>=2,<3` 與官方
  `mcp.server.mcpserver.MCPServer`。SDK v1 不受支援；禁止新增
  `mcp.server.fastmcp` 或其他 v1 fallback。
- Tool `Context` 只能由 MCPServer 在 request runtime 注入，用於 bounded
  progress。Operational logs 必須使用 Python logging 寫到 stderr，不得再呼叫
  deprecated MCP protocol logging API。`Context` 不得成為 client input，也不得
  出現在公開 JSON schema；修改 decorators/signatures 時必須保留 schema-leak
  regression guard。
- Tool registry 只能使用 SDK 公開 `add_tool`、`remove_tool`、`list_tools` API；
  不得依賴 private tool-manager internals。
- `balanced`（30）、`compact`（17）、`legacy`（完整 direct inventory）是 SDK 2
  server 上的 tool UX policy。`legacy` 只相容舊 tool names/allow-lists，不是
  SDK v1 protocol compatibility。
- `document(op="preflight", pdf_path=...)` 必須維持唯讀：回傳穩定
  `pdf-preflight-v1` source hash/page locator/OCR/engine routing schema，不建立
  document artifacts。
- `document(op="export_assets", doc_id=..., output_dir=...)`（alias
  `agent_assets`）輸出 deterministic `agent-asset-bundle-v1`，包含
  `manifest.json`、`assets.jsonl`、Foam `index.md`/`notes/**` 與 figure media；
  不得改寫 source/citation state，且只能原子替換 matching managed bundle。

---

## Python 環境（uv 優先）

- 新專案必須使用 uv 管理套件
- 必須建立虛擬環境（禁止全域安裝）
- 參見子法：`.github/bylaws/python-environment.md`

```bash
# 初始化環境
uv venv
uv sync                    # 基本安裝（PyMuPDF 快速引擎）

# Active PDF→資產引擎（可選，皆相容 Pillow>=12.2.0）
uv sync --extra pdf-plus   # pymupdf4llm（輕量版面感知，drop-in）
uv sync --extra docling    # Docling（MIT：layout+表格+公式+圖表）
# MinerU / Marker extras 皆暫時為空；只保留 adapters，不安裝已知不安全 graph。

# 安裝依賴
uv add package-name
uv add --dev pytest ruff
```

### Dependency / Security automation

- `uv lock --check` 驗證 manifest/lock 一致性；
  `uvx --from uv==0.12.3 uv audit --preview-features audit-command --frozen --python-version 3.10`
  必須對 universal lock 零漏洞，不使用 allowlist。
- `npm --prefix vscode-extension audit --package-lock-only --audit-level=low`
  稽核 VSIX lockfile。
- `uv run bandit -q -r src -x tests --severity-level medium` 阻擋 Python
  medium/high security findings。
- `.github/workflows/dependency-security.yml` 在 dependency PR、手動執行與每週
  排程只讀執行上述 gates，不自動寫回。
- `.github/dependabot.yml` 每週管理 `uv`、`npm`、`github-actions`，採分組與
  open-PR limits；Python 必須使用官方 `uv` ecosystem，讓 `pyproject.toml` 與
  `uv.lock` 同步更新。
- MinerU hold：3.4.4 pin `transformers<5`、修補線需 `>=5.5`。Marker hold：
  marker-pdf 1.10.2 pin `Pillow<11`、專案安全底線為 `Pillow>=12.2.0`。

---

## Memory Bank 同步

每次重要操作必須更新 Memory Bank：

| 操作 | 更新文件 |
|------|----------|
| 完成任務 | `progress.md` (Done) |
| 開始任務 | `progress.md` (Doing), `activeContext.md` |
| 重大決策 | `decisionLog.md` |
| 架構變更 | `architect.md` |

參見子法：`.github/bylaws/memory-bank.md`

---

## Git 工作流

提交前必須執行檢查清單：

1. ✅ Memory Bank 同步（必要）
2. 📖 README 更新（如需要）
3. 📋 CHANGELOG 更新（如需要）
4. 🗺️ ROADMAP 標記（如需要）

**⚠️ PUSH 後必須檢查 CI 狀態！**
- 推送完成後立即檢查 GitHub Actions 是否通過
- 如有失敗，優先修復 CI 問題再繼續開發

**📊 更新工具數量時必須使用 Script**
- 執行 `./scripts/count_tools.sh` (Linux/macOS) or `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/count_tools.ps1` (Windows) 統計實際數量
- 不可手動計算或猜測工具數量
- 確保 README、copilot-instructions、VSCode extension README 三處同步

參見子法：`.github/bylaws/git-workflow.md`

---

## VSIX / MCP Harness 同步

VS Code extension 發布前必須確認 assistant harness 和 MCP 設定路徑同步：

- VSIX 會打包 `vscode-extension/resources/repo-assets/asset-aware/**`
- 安裝/啟動時會同步 workspace harness：`AGENTS.md`、`.github/copilot-instructions.md`、`.github/agents/asset-aware-document.agent.md`、`.cline/skills/asset-aware-mcp-harness`、`.codex/skills/asset-aware-mcp-harness`、`.clinerules`
- MCP 設定會保守 merge：Copilot `.vscode/mcp.json`、Cline `cline_mcp_settings.json`、Codex `~/.codex/config.toml`
- 不可覆蓋使用者自訂 server、Codex comments、Cline `alwaysAllow` 或 unrelated MCP entries

必要檢查：

```bash
cd vscode-extension
npm run sync-assets:check
npm run test:ci
```

---

## 可用 Skills

位於 `.claude/skills/` 目錄：

| Skill | 功能 | 觸發詞 |
|-------|------|--------|
| git-precommit | Git 提交前編排器 | `GIT`, `commit`, `push` |
| git-doc-updater | Git 提交前文檔同步 | `docs`, `文檔`, `sync docs` |
| ddd-architect | DDD 架構輔助 | `DDD`, `arch`, `新功能` |
| code-refactor | 主動重構與模組化 | `RF`, `refactor`, `重構` |
| memory-updater | Memory Bank 同步 | `MB`, `memory`, `記憶` |
| memory-checkpoint | 記憶檢查點 | `CP`, `checkpoint`, `存檔` |
| readme-updater | README 智能更新 | `readme`, `說明` |
| readme-i18n | README 多語言同步 | `i18n`, `翻譯`, `translate` |
| changelog-updater | CHANGELOG 自動更新 | `CL`, `changelog` |
| roadmap-updater | ROADMAP 狀態追蹤 | `RM`, `roadmap` |
| code-reviewer | 程式碼審查 | `CR`, `review`, `審查` |
| test-generator | 測試生成 | `TG`, `test`, `測試` |
| project-init | 專案初始化 | `init`, `new`, `新專案` |
| **pdf-asset-extractor** | **PDF→圖文分解+知識圖譜** | `PDF`, `ingest`, `figure`, `table`, `知識圖譜` |

> ⚠️ **pdf-asset-extractor 注意**：圖片 base64 非常大，一次只處理一張！

---

## 💸 Memory Checkpoint 規則

為避免對話被 Summarize 壓縮時遺失重要上下文：

### 主動觸發時機

1. 對話超過 **10 輪**
2. 累積修改超過 **5 個檔案**
3. 完成一個 **重要功能/修復**
4. 使用者說要 **離開/等等**

### 執行指令

- 「記憶檢查點」「checkpoint」「存檔」
- 「保存記憶」「sync memory」

### 必須記錄

- 當前工作焦點
- 變更的檔案列表（完整路徑）
- 待解決事項
- 下一步計畫

---

## 回應風格

- 使用**繁體中文**
- 提供清晰的步驟說明
- 引用相關法規條文
- 執行操作後更新 Memory Bank

---

## 目錄結構約定

```
src/
├── domain/           # 核心領域（純業務邏輯，無外部依賴）
│   ├── entities.py        # Document, Asset, Section 等核心實體
│   ├── pdf_preflight.py   # Stable PDF preflight schema / routing / failures
│   ├── table_entities.py  # A2T 表格相關實體
│   ├── section_tree.py    # SectionTree 章節樹結構
│   ├── chunking.py        # 文本分塊策略
│   └── repositories.py    # Repository 介面定義
├── application/      # 應用層（用例編排）
│   ├── document_service.py  # ETL 文件處理與 fallback orchestration
│   ├── pdf_preflight_service.py # Async-safe preflight application facade
│   ├── agent_asset_bundle_service.py # Atomic reusable agent/Foam bundle export
│   ├── agent_asset_bundle_format.py  # Canonical JSON/hash + Foam serialization
│   ├── agent_asset_record_builder.py # Segmentation/manifest/evidence records
│   ├── table_service.py     # A2T 表格服務
│   ├── section_service.py   # 章節導航服務
│   ├── asset_service.py     # 資產查詢服務
│   ├── knowledge_service.py # 知識圖譜服務
│   └── job_service.py       # 非同步工作管理
├── infrastructure/   # 基礎設施（DAL、外部服務）
│   ├── file_storage.py      # 檔案儲存 Repository 實作
│   ├── pdf_extractor.py     # PyMuPDF 快速提取（base + fallback）
│   ├── pymupdf4llm_adapter.py # PyMuPDF4LLM 版面感知（drop-in 升級）
│   ├── docling_adapter.py   # Docling 高精度（MIT：layout+表格+公式+圖表）
│   ├── mineru_adapter.py    # MinerU adapter（security hold；extra 空）
│   ├── marker_adapter.py    # Marker adapter（security hold；Pillow<11）
│   ├── pymupdf_preflight.py # Process-isolated bounded PDF inspection
│   ├── structured_extractor.py # StructuredPDFExtractor Protocol（引擎共通契約）
│   ├── extractor_factory.py # ETL_ENGINE 引擎選擇工廠
│   ├── excel_renderer.py    # Excel 渲染
│   ├── lightrag_adapter.py  # LightRAG 知識圖譜
│   └── config.py            # 配置管理
└── presentation/     # 呈現層（MCP Server, 模組化）
    ├── server.py            # Thin entry point (31 行)
    ├── mcp_app.py           # Official SDK 2 MCPServer 單一實例 + public registry tracking
    ├── mcp_context.py       # Runtime Context progress + stderr logging helpers
    ├── tool_surface.py      # balanced / compact / legacy public-API filtering
    ├── dependencies.py      # Composition Root
    ├── tools/               # 30 balanced public / 17 compact / 63 legacy tools
    │   ├── document_tools.py   # ETL + preflight + reusable agent asset export
    │   ├── docx_tools.py       # Docx ↔ DFM + conversion (16)
    │   ├── section_tools.py    # Navigation (5)
    │   ├── job_tools.py        # Job management (4)
    │   ├── knowledge_tools.py  # KG (3)
    │   ├── profile_tools.py    # Profile (6)
    │   └── table_tools.py      # A2T (7) — operation-based
    └── resources/           # 13 resources (2 模組)
        ├── document_resources.py  # Documents (8)
        └── table_resources.py     # Tables (5)
```

---

## 重要檔案參考

| 檔案 | 用途 |
|------|------|
| `CONSTITUTION.md` | 專案憲法（最高原則） |
| `memory-bank/` | 專案記憶庫 |
| `docs/spec.md` | 技術規格 |
| `docs/marker-etl-spec.md` | Marker ETL 規格書 |
| `.github/bylaws/*.md` | 子法細則 |
| `.claude/skills/*/SKILL.md` | 技能操作程序 |
