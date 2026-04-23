# Changelog

所有重要變更都會記錄在此檔案中。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
專案遵循 [語義化版本](https://semver.org/lang/zh-TW/)。

## [Unreleased]

## [0.6.9] - 2026-04-23

### Fixed

- **DFM messy-document hardening**
  - Escapes literal Markdown syntax and marker-looking comments so no-op saves preserve text such as `*literal*`, `~~literal~~`, `^literal^`, and `<!-- @... -->`
  - Preserves multi-line list-item continuation text and detects list paragraphs from Word `numPr` metadata even when converted files use `Normal` style
  - Parses and updates hyperlink-contained runs in document order so edited paragraphs do not leave stale linked text behind

- **DOCX table write-back safety**
  - Preserves literal pipes inside table cells all the way through final XML write-back
  - Fails closed on row/column structural table edits until XML row/column insertion is implemented, preventing false-success saves where IR changes but DOCX output is truncated

- **VS Code DFM save robustness**
  - Accepts fenced JSON, alias keys, and English/Chinese Markdown MCP result labels
  - Blocks accidental overwrite when the source DOCX changed on disk after a DFM session was opened
  - Keeps failure diagnostics visible when `save_docx` rejects malformed DFM/table edits

## [0.6.8] - 2026-04-19

### Added

- **Public synthetic DOCX release fixture**
  - `tests/integration/test_docx_complex_sample_roundtrip.py` now builds its own complex DOCX with nested tables, merged cells, mixed formatting, and multi-paragraph table cells
  - Tagged releases and local release prep now validate DOCX round-trip behavior without depending on confidential repository-local files

### Fixed

- **Release pipeline confidentiality regression**
  - Replaced the internal sample DOCX dependency in CI and release gates with a self-contained synthetic fixture so tagged builds can pass on GitHub Actions
  - Preserved the same critical checks: byte-identical no-op rebuilds and nested-table edit write-back validation

### Changed

- **Release metadata synced to 0.6.8**
  - Python package, runtime version metadata, VS Code extension manifest, and release-facing docs now point to the same patch version
  - Extension release notes now describe the public synthetic DOCX validation gate instead of an internal sample

## [0.6.7] - 2026-04-19

### Added

- **Complex DOCX round-trip release gate**
  - Added `tests/integration/test_docx_complex_sample_roundtrip.py` to CI and release workflows so the real nested-table sample DOCX is validated before every tagged release
  - `scripts/release.sh` now runs the same complex DOCX round-trip smoke test locally before packaging

### Changed

- **VS Code Marketplace branding now matches the current product family**
  - Extension icon, banner styling, and gallery banner color are aligned with the dark navy / teal / gold visual language used by `Academic Figures MCP` and `MedPaper Assistant`
  - Extension README release highlights are updated for the DOCX round-trip hardening release

### Fixed

- **DOCX DFM round-trip fidelity for nested tables and no-op rebuilds**
  - Nested tables are now extracted as first-class editable blocks, validated recursively, and written back correctly when edited
  - No-op `from_md=True` saves preserve byte-identical output for the validated sample DOCX
- **Release workflow blockers**
  - Fixed newline normalization so UTF-8 markdown and manifest reads stay canonical across Windows and Linux
  - Fixed repo-wide Ruff and MyPy issues that previously broke the release workflow

## [0.6.6] - 2026-04-14

### Changed

- **Manifest title detection is more resilient on real exam PDFs**
  - Markdown heading titles are now normalized before saving, stripping inline markdown noise such as `**` / `#`
  - When a PDF starts directly with question content, title fallback now prefers the filename stem instead of misclassifying page numbers or question stems as the title

### Added

- **Manifest text-quality diagnostics for sparse extraction results**
  - `DocumentManifest` now records `text_quality_status`, visible text counts, repeated-line ratio, and `ocr_recommended`
  - `list_documents` and `inspect_document_manifest` now surface these diagnostics, making low-text scan failures easier to spot before downstream parsing

### Fixed

- **Low-text scanned PDFs no longer look deceptively healthy in manifest metadata**
  - Repetitive outputs such as repeated `本題送分` are now flagged as `low_text` with an OCR recommendation instead of silently appearing as a normal document title

## [0.6.5] - 2026-04-14

### Added

- **Scoped page-range ingestion for PDF workflows**
  - `ingest_documents` 與 `parse_pdf_structure` 現在支援 `page_ranges`，只處理指定頁段並產生 `selected_pages.pdf`
  - Markdown page markers、TOC、tables、images 與 Marker blocks 會 remap 回原始 PDF 頁碼，避免來源引用失真

### Changed

- **Large-PDF Marker parse 內建自動保護策略**
  - 頁數超過 800 頁時會自動啟用 chunking，降低大文件解析時的記憶體壓力
  - 遇到高圖片量 PDF 時會自動停用 figure extraction，避免產出量與解析成本失控

### Fixed

- **相同 PDF 不同頁段 ingest 的識別與來源穩定性**
  - `doc_id` 現在會納入 page-range scope，避免相同來源 PDF 但不同頁段造成 collision
  - subset ingestion 產物會保留原始頁碼語意，改善後續 source tracking 與 asset citation 一致性

## [0.6.3] - 2026-03-23

### Added

- **LightRAG citation-aware structured MCP output**
  - `consult_knowledge_graph` 現在支援 `response_mode=structured|data|text`
  - 預設 structured 模式會回傳 `answer`、`references`、`metadata`、`retrieval`、`counts`
  - 新增 retrieval-only 路徑，讓 agent 可直接使用 `aquery_data` 類型資料做 citation-aware workflow

### Changed

- **LightRAG query surface 對齊上游能力**
  - Knowledge service / adapter 現在支援 `mix`、`naive`、`bypass`、`user_prompt`、`include_references`
  - VS Code extension `.env` 對齊後端設定，改用 `LIGHTRAG_WORKING_DIR`（保留 legacy `LIGHTRAG_DIR` fallback）
  - README、README.zh-TW、VS Code extension README 與 Memory Bank 同步更新，文件統一為 `47 tools / 13 resources`

### Fixed

- **Knowledge graph deletion 與本地文件刪除同步**
  - `delete_document` 在啟用 LightRAG 時，會同步嘗試刪除知識圖譜中的文件索引
  - MCP 回傳現在會明確顯示 `knowledge_graph_status`
- **Knowledge Graph tool guard rails**
  - `consult_knowledge_graph` 對非法 `response_mode` fail fast
  - `LightRAGAdapter` 會拒絕錯誤型別的建構參數，避免把非 LightRAG 物件誤當 adapter state

## [0.6.2] - 2026-03-19

### Added

- **Agent asset 覆蓋規劃與操作文件**
  - 新增 `docs/agent-asset-gap-analysis.md`，整理 agent 資產全覆蓋目標、量化 gap 與 Release A/B/C/D 分段發布策略
  - 新增 `docs/github-cli.md`，整理團隊常用 GitHub CLI 維運流程
  - 新增 `scripts/gh_update_repo_metadata.sh` 與 `scripts/gh_update_issue_or_pr.sh`，加速 repo metadata、issue、PR 的批次更新

### Changed

- **文件與版本 metadata 對齊 0.6.2**
  - README、README.zh-TW、VS Code extension README、copilot-instructions 與 Memory Bank 同步更新為 `47 tools / 13 resources`
  - Release 敘事正式拆成 `0.6.1` 與 `0.6.2` 兩段 patch release，避免把功能擴展與策略文件混成單一大版

## [0.6.1] - 2026-03-19

### Added

- **OpenDocument 互轉與保真測試**
  - `ingest_docx` 現在支援 `.odt`、`.ods` 經由 LibreOffice 自動轉為 `.docx`
  - 新增 `convert_docx_to_odt` 工具，支援 DOCX/DFM → ODT 保真匯出
  - 新增 `scripts/roundtrip_3cycle_test.py`，驗證 DFM 3-cycle 與 DOCX↔DOC / DOCX↔ODT cross-format fidelity
  - 新增 `docs/format-conversion-report.md`，記錄 round-trip 結果與退化分析

### Changed

- **Markdown / DOCX 匯出路徑擴展**
  - `export_markdown` 現在支援輸出 ODT
  - `src/presentation/tools/__init__.py` 與相關文件同步為 `47 tools / 13 resources`
- **Table domain models 對齊 Pydantic v2**
  - A2T 相關 table entities 改用 `BaseModel` / `Field` / `field_validator`，改善驗證與序列化一致性

### Fixed

- **舊版表格資料相容性**
  - `TableContext.created_at` 可安全處理 ISO string 與 legacy 空字串，降低歷史 JSON 載入失敗風險

## [0.6.0] - 2026-03-18

### Added

- **Unified segmentation / layout / OCR 工具鏈**
  - 新增 `export_document_segmentation`，輸出整合 manifest、blocks、assets、reading order 與 markdown line range 的 `segmentation.json`
  - 新增 `visualize_document_layout`，可從 `original.pdf` 產生 bbox / type / reading order overlay
  - 新增 `ocr_pdf_document`，支援 `ocrmypdf` 按需前處理掃描 PDF
- **精準 line-range / section context 回傳**
  - `fetch_document_asset` 現在直接回傳 `line_start` / `line_end` / `section_title` / `source_block_id`
  - `FigureAsset`、`TableAsset`、`FetchResult` 追加 line span 與 section metadata 欄位
- **MCP progress / logging 擴展**
  - PDF ETL、DOCX save / convert、Knowledge Graph、table render 現在都會回報 MCP-native progress
  - 非同步 ingest job 會跟隨實際 phase 與 OCR 階段更新進度

### Changed

- **Line span 正式成為 ETL 真相**
  - Marker / PyMuPDF 路徑會在 ETL 階段持久化 block 與 asset 的 markdown line span
  - `SegmentationService` 只消費持久化資料；舊 `blocks.json` 則在匯出時自動 backfill 升級
  - line resolver 升級為 page-aware + section-aware，比全文文字回推更穩定
- **Section truth 在 manifest generator 收斂**
  - `ManifestGenerator.generate()` 接受預先計算的 `sections`，避免 Marker ingest 與 manifest 重建出兩份不同 section 真相
  - PDF TOC 路徑現在也會補齊 section line span 與 preview，並由 manifest 統一回填 asset 的 `section_id` / `section_title`
- **VS Code extension / 文件同步更新**
  - 文件全面更新為 `46 tools / 13 resources`
  - extension 現在會顯示 segmentation 入口與 ETL jobs 概況

### Fixed

- **Segmentation / overlay correctness**
  - 每次 ingest 都會覆蓋保存最新 `original.pdf`，避免 overlay 對到舊檔
  - 同頁多 figure / table 的 block 對位改為優先使用 `source_block_id` / `source_order`，降低錯配
  - section line range 對外顯示統一改為 1-based，修正第一段 `start_line=0` 被隱藏的問題
- **DOCX save write-back 穩定化**
  - `save_docx` 未帶 inline DFM 時會回退使用持久化 `content.dfm`
  - 儲存前會先把 doc-linked `TableContext` 變更合併回 IR/DFM，避免最後輸出空白或遺漏表格修改

## [0.5.2] - 2026-03-18

### Changed

- **Marker / torch 改為可選安裝路徑**
  - `marker-pdf` 從預設依賴移到 optional extra：`uv sync --extra marker`
  - 預設安裝與 installer 不再自動拉入 `torch` / `surya` 依賴鏈
  - VS Code extension 新增 `enableMarkerBackend` 與 `torchBackend` 設定，預設使用 `cpu` 以降低 wheel / CUDA 相容性問題

### Added

- **MCP Server 版本釘定與自動升級**
  - Extension 啟動時使用 `--from asset-aware-mcp==X.Y.Z` 釘定 PyPI 版本，確保 server 與 extension 版本一致
  - 偵測到 extension 版本變更時自動加入 `--upgrade` 旗標，觸發 uvx 快取刷新
  - 新增 `assetAwareMcp.upgradeServer` 手動指令，使用者可強制升級 MCP Server
  - 安裝一次即全機共享（uvx 全域快取），不需每個資料夾重新安裝

### Fixed

- **Windows 上 torch DLL 載入失敗導致 server 無法啟動**
  - `src/infrastructure/__init__.py` 的 optional dependency import 改為 catch `(ImportError, OSError)`
  - 修正 Windows 下 `torch` DLL 載入失敗（`OSError: [WinError 1114]`）不被 `ImportError` 捕獲的問題
  - LightRAG、PyMuPDF、Marker 三個可選依賴均加寬例外處理
- **VS Code extension 啟動 runtime 穩定化**
  - extension 的 PyPI 啟動與本地 dev 啟動都改為優先使用 Python 3.11
  - 避免 macOS 在 Python 3.14 上為 `regex`/`marker-pdf` 觸發本機 C 編譯，導致缺少 Xcode CLT 時無法啟動
  - 不限縮專案整體的 Python 3.11+ 支援宣告，只固定 extension/installer 的穩定執行 runtime
- **跨平台 installer 對齊**
  - `scripts/install.sh` 與 `scripts/install.ps1` 以 `uv sync --python 3.11` 建立環境
  - Linux / macOS / Windows 均使用相同的穩定 runtime 策略

## [0.5.1] - 2026-03-14

### Fixed

- **Markdown 匯出器 Unicode 修復**
  - 修正水平分隔線字元損壞（`U+FFFD` → `─` U+2500）
  - 修正無序列表符號損壞（`??` → `•` U+2022）
- **CRLF 換行符相容性**
  - `MarkdownDocxConverter.convert()` 新增 `\r\n` → `\n` 正規化
  - 防止 Windows 換行符導致 Heading / Table / List 解析異常
- **LibreOffice 跨平台路徑偵測**
  - 新增 Windows `Program Files\LibreOffice\program\soffice.exe` 路徑
  - 新增 Linux `/usr/bin/libreoffice`、`/snap/bin/libreoffice` 路徑
  - macOS / Linux / Windows 三平台分流偵測
- **LibreOffice 錯誤回報改善**
  - 轉換失敗時 fallback 到 stdout 訊息，避免空白 error log
- **Inline Markdown regex 改善**
  - 加入 negative lookahead 避免 `**bold**` 誤消費 `***bold_italic***`
  - `_italic_` 限制不跨行匹配
- **測試修正**
  - `test_find_libreoffice_binary_prefers_env_var` 改用 `tmp_path` 跨平台相容
  - 新增 CRLF 換行測試、bold/italic regex 邊界測試

## [0.5.0] - 2026-03-14

### Added

- **Markdown 匯出工具 `export_markdown`**
  - 支援將 Markdown 文字匯出為 `.docx`、`.pdf`、`.doc` 格式
  - 新增 `MarkdownDocxConverter` 基礎設施元件
- **DFM 表格多行儲存格保護**
  - 表格儲存格內含 `\n` 時自動以 `<br>` 轉義，防止 pipe-table 格式破損
  - 寫入後自動驗證非空儲存格數量，偏差 >50% 時拒絕寫入
- **`save_docx` 內容收縮安全閥**
  - 寫回時若內容量縮減超過 50% 則自動拒絕，需 `force=True` 強制執行
- **`docx_validate_roundtrip` 內容量指標**
  - 新增 `total_chars`、`table_nonempty_cells`、`table_cell_chars` 統計欄位
- **`update_cell` 多行警告**
  - 寫入含換行符的儲存格時回傳字元數與換行數提示

### Fixed

- **Ollama Embedding API 相容性**
  - 支援 Ollama v0.5+ `/api/embed` 端點，向下相容 `/api/embeddings`
  - 區分「模型未安裝」與「端點不存在」的 404 錯誤

### Changed

- **MCP 工具總數**：42 → **43**（7 模組）
- **Docx 工具總數**：12 → **13**（新增 `export_markdown`）

## [0.4.2] - 2026-03-09

### Fixed

- **本機 release 驗證與 GitHub Actions 完全對齊**
  - `scripts/release.sh` 改為檢查整個 repo：`ruff check .`、`ruff format --check .`
  - 修正測試檔格式與 EOF newline，消除 release-only CI failure

## [0.4.1] - 2026-03-09

### Fixed

- **Release workflow CI 對齊**
  - 修正新測試檔在 GitHub Actions `ruff check .` 下的 lint 問題（安全路徑字串、巢狀 `with`、EOF newline）
  - 確保 Release workflow 與本機 `scripts/release.sh` 均可完整通過

## [0.4.0] - 2026-03-09

### Added

- **文件級 CRUD 與互轉工具擴充**
  - `delete_document`：刪除已攝入 PDF 與本地 artifacts
  - `delete_docx`：刪除已攝入 DOCX/DFM 與本地 artifacts
  - `list_docx_documents`：列出所有已攝入 DOCX/DFM 文件
  - `convert_docx_to_pdf`：以保真模式輸出 PDF
  - `convert_docx_to_doc`：以保真模式輸出 DOC
  - `convert_pdf_to_docx`：以內容重建模式輸出可讀 DOCX
- **Strict round-trip 驗證**
  - `DocxValidator.validate(..., strict=True)` fail-closed 模式
  - `ValidationReport` 新增 `strict_passed` / `strict_failures`
- **Save-time mutation guard**
  - `DocxService.save_docx()` 會偵測未編輯區塊被意外改動並中止寫回
- **Proposal 真實文件戰測完成**
  - 以真實 Proposal 文件驗證 DOCX→DFM→DOCX、DOCX→PDF、DOCX→DOC CLI 流程

### Changed

- **MCP 工具總數**：36 → **42**（7 模組）
- **Docx 工具總數**：8 → **12**
- `scripts/dfm_cli.py` 新增 `to-pdf`、`to-doc`、`validate --strict` 與互動式選單選項
- README、README.zh-TW、VS Code extension README 與工具統計全面同步到 42 tools

### Fixed

- **Protected block placeholder 誤判為編輯**
  - `dfm_parser.py` 不再把 protected blocks placeholder 當作 user edits
  - `dfm_integrity.py` 僅在 protected block 真的變更時發出 warning
- **無聲文件破壞風險降低**
  - 寫回流程若發現非目標區塊被更動，立即 fail closed

## [0.3.3] - 2026-02-23

### Added

- **🐳 Dockerfile — 生產級容器部署**
  - Multi-stage build（builder + runtime），Python 3.12-slim
  - Non-root `mcp` 使用者、uv 安裝、`.dockerignore` 排除非必要檔案
- **🛡️ PDF magic byte 驗證** — 在 `document_service._ingest_single()` 中驗證 `%PDF-` 標頭，防止非 PDF 檔案偽裝
- **⚡ 並行 Job 上限** — `MAX_CONCURRENT_JOBS=5`，防止資源耗盡（`job_service.py`）
- **📊 Structured logging** — `server.py` 新增 `configure_logging()`，統一格式 `%(asctime)s | %(levelname)-8s | %(name)s | %(message)s`
- **📝 `.doc` 格式自動轉換** — `ingest_docx` 支援舊版 `.doc` 檔案，自動透過 LibreOffice headless 轉換為 `.docx`
- **🧪 37 個新 MCP 工具層單元測試** — `test_mcp_tool_layer.py`，覆蓋全部 7 個 tool 模組 + server + 新功能
  - 測試類別：TestDocxTools(10), TestJobTools(3), TestDocumentTools(3), TestTableTools(11), TestProfileTools(3), TestKnowledgeTools(1), TestServerStartup(2), TestJobServiceConcurrency(1), TestPDFValidation(2)

### Fixed

- **MCP server 未攔截異常** — `main()` 加入 try/except + `logger.exception()`，避免無訊息斷線
- **bare `except Exception:` 模式** — 全面加上描述性註解（table_service、dfm_table_bridge、table_tools、document_service）
- **Markdown 跳脫修復** — 新增 `_escape_md()` / `_unescape_md()`，跳脫 `*`、`~`、`^` 字元，防止文字內容被誤判為 Markdown 格式標記（如 `※**下列` 中的 `**`）
- **Run 合併優化** — 相鄰相同格式的 runs 先合併再產生 Markdown，避免 `**A****B**` 碎片化
- **Caption 偵測修正** — 排除 `**...**` bold 模式的誤判為 caption
- **CLI import path 修正** — `src.application.docx_validator` → `src.infrastructure.docx_validator`

## [0.3.2] - 2026-02-21

### Added

- **🛡️ DFM Integrity Checker — 拆解/組裝內部驗證引擎**
  - 新模組 `dfm_integrity.py`：`DfmIntegrityChecker` 類別，6 個檢查/修復方法
  - **Post-ingest 驗證**：MD markers ↔ IR blocks ↔ YAML blocks 三方交叉比對
  - **Split-format 一致性**：content.md ↔ format.yaml 互相驗證（doc_id、block ID）
  - **Pre-save 驗證**：edit block_id 存在性、保護區塊偵測、表格欄數比對、重複編輯
  - **Post-save 驗證**：round-trip fidelity 驗證（自動呼叫 DocxValidator）
  - **Auto-repair**：自動修復 orphan markers、缺失 YAML entries、表格欄數不符（pad/truncate）
  - 整合至 `DocxService.ingest_docx()` 和 `save_docx()`，MCP 工具 + CLI 皆顯示完整性狀態
- **📊 DocxValidator 檔案層級比對**
  - 新增 SHA-256 全檔 hash 比對（一鍵判斷二進位是否完全相同）
  - 新增檔案大小比對（bytes 精確到個位數）
  - 新增 ZIP 內容差異分析（新增/移除/大小變化的 ZIP entries）
  - `ValidationReport` 新增 `binary_identical`, `original_sha256`, `rebuilt_sha256`, `zip_entry_diffs` 欄位
  - `to_markdown()` 報告新增「檔案層級比對」區塊
- **🔧 Round-trip 測試腳本** `scripts/roundtrip_test.py`

### Changed

- **🔄 CI/CD 全面遷移至 uv**（移除所有 pip/setup-python）
  - `.github/workflows/ci.yml`：5 個 jobs 全部改用 `astral-sh/setup-uv@v4`
  - `.github/workflows/release.yml`：test + publish-pypi 改用 uv
  - `.pre-commit-config.yaml`：`pytest-smoke` 改為 `uv run pytest`
  - 原始碼/文件中所有 `pip install` 建議改為 `uv add`
- CLI `cmd_ingest` / `cmd_save` 顯示完整性檢查結果
- MCP `ingest_docx` / `save_docx` 工具返回完整性狀態

### Fixed

- `test_etl_profile.py::test_to_json` — Windows cp950 編碼錯誤（`read_text()` 加 `encoding="utf-8"`）
- CLI `dfm_cli.py` 語法錯誤（多語句合併在同一行）

## [0.3.0] - 2026-02-11

### Added

- **📝 Docx 即時編輯系統 (DFM — Docx-Flavored Markdown)**
  - 全新 DFM 格式：用 Markdown 語法即時編輯 .docx 檔案，保留完整格式（粗體、斜體、連結、列表、表格）
  - `DocxIR` 中間表示層：拆解 docx → IR → DFM → 編輯 → IR → docx 完整往返
  - 支援區塊級 (block) 與行內 (run) 格式保留
  - SHA-256 checksum 驗證文件完整性
- **8 個 Docx MCP 工具**：
  - `ingest_docx` — 匯入 .docx 並拆解為 DFM
  - `get_docx_content` — 讀取指定區塊 DFM 內容
  - `save_docx` — 將 DFM 編輯寫回 .docx
  - `list_docx_blocks` — 列出文件區塊結構
  - `docx_validate_roundtrip` — 6 維度往返保真驗證
  - `docx_table_to_context` — Docx 表格 → A2T 上下文 (Bridge)
  - `docx_table_from_context` — A2T 表格 → Docx 表格 (Bridge)
  - `docx_chart_data` — 提取 Docx 圖表數據
- **DocxValidator — 6 維度往返保真驗證器**：
  - 結構 (Structure)、文字 (Text)、格式 (Formatting)、表格 (Table)、媒體 (Media)、樣式 (Style)
  - 加權評分（text=0.35, structure/format/table=0.15, media/style=0.10）
  - Emoji 等級（🟢 EXCELLENT ≥95%, 🟡 GOOD ≥80%, 🟠 FAIR ≥60%, 🔴 POOR <60%）
  - Agent 可讀的 Markdown 報告輸出
- **DfmTableBridge — DFM ↔ A2T 雙向橋接**：
  - Docx 表格直接進入 A2T 工作流（plan → draft → commit）
  - A2T 表格寫回 Docx（支援樣式映射）
  - 圖表數據提取
- **DFM 格式規格書**：`docs/dfm-spec.md`
- **Pre-commit hooks**：commit-size-guard（≤30 檔案）
- **VS Code Extension DFM 支援**：
  - DFM 語法高亮 + 語言定義
  - DFM Preview provider
  - 37 個 TypeScript 測試
- **120 個新測試**：test_dfm.py (53), test_dfm_table_bridge.py (32), test_docx_validator.py (35)

### Changed

- 總工具數：28 → **36**（+8 docx 工具）
- 模組數：6 → **7**（+docx_tools）
- Domain 層新增：`docx_entities.py`, `docx_value_objects.py`
- Application 層新增：`docx_service.py`, `dfm_table_bridge.py`
- Infrastructure 層新增：`docx_adapter.py`, `dfm_parser.py`, `dfm_renderer.py`, `docx_validator.py`

## [0.2.14] - 2026-02-10

### Added

- **A2T 工具合併 (19 → 7)**：`plan_table`, `table_manage`, `table_data`, `table_cite`, `table_history`, `table_draft`, `discover_sources`
- **AssetRef** frozen dataclass — 統一資產引用，支援 7 種來源類型 (section, figure, table, full_text, kg_entity, external, user_input)
- **CellCitation** — 儲存格級引用管理，作為表格資料的平行附加層
- **ChangeEntry + TableChangeLog** — 自動變更審計軌跡
- **TableTemplate** — 4 內建模板 (drug_comparison, study_summary, citation_extract, pico_analysis)
- **Schema Evolution** — add_column, remove_column, rename_column 欄位動態演進
- **Cell-level CRUD** — get_row, get_cell, clear_cell 精細資料操作
- **discover_sources** — 跨文件資料來源探索，整合 Documents + Knowledge Graph
- `get_section_content` 從 table_tools 移至 section_tools (5 section tools)
- 68 新測試 (test_asset_ref.py: 22, test_citation_audit.py: 46)

### Changed

- 總工具數：39 → **28**（↓28%，功能反而增加）
- table_resources.py 改為直接呼叫 service 而非 import tool functions
- test_mcp_tools.py 修正 import 路徑

## [0.2.11] - 2026-02-09

### Added
- 🎛️ **ETL Profile 設定系統**：所有 PDF 提取參數現可透過 Profile 設定
  - `ETLProfile` frozen dataclass + `ETLProfileRegistry` 管理器
  - **5 內建預設**：default, arxiv, nature, ieee, elsevier
  - **JSON 覆蓋支援**：`profiles/*.json` 可自訂期刊設定並繼承基底 profile
- 🔧 **5 個 MCP Profile Tools**：
  - `list_etl_profiles` — 列出所有可用 profiles
  - `get_etl_profile` — 取得 profile 詳細配置
  - `get_current_etl_profile` — 顯示目前使用的 profile
  - `set_etl_profile` — 切換 profile（動態重建 services）
  - `load_etl_profile_from_json` — 從 JSON 檔案載入自訂 profile
- 🧪 **32 個 ETL Profile 單元測試**：完整測試 profile 繼承、JSON 載入、registry 功能
- 🖥️ **VSCode Extension 整合**：
  - `settingsPanel.ts` — ETL Profile 下拉選單
  - `envManager.ts` — `ETL_PROFILE` 環境變數支援

### Changed
- 🏗️ **DDD 架構修復**：
  - `JobStoreInterface` 從 infrastructure 移至 `domain/repositories.py`
  - 新增 `TableRendererInterface` 抽象介面
  - `TableService` 重構為依賴注入建構子（移除 global singleton）
  - `rebuild_for_profile()` 封裝 profile 切換邏輯於 `dependencies.py`
- 📊 **工具數量更新**：34 → 39 tools in 6 modules

### Improved
- 🧪 **E2E ETL 測試** (`tests/e2e_test_etl.py`)：5 篇論文 **65 項**測試全通過
- 📄 **PDF TOC 優先策略**：使用 PDF 內建 TOC (`get_toc()`) 取代字型大小啟發式
- 📊 **Table/Figure caption 偵測**：精準匹配 "Table N" / "Figure N" 模式
- 🖼️ **Noise filtering**：過濾空表格、小圖 (<50px)

## [0.2.10] - 2026-02-09

### Changed
- 🏗️ **Presentation 層模組化完成**：`server.py` 從 2122 行瘦身為 31 行 thin entry point
  - `tools/` 目錄：5 個模組共 34 tools (document, section, job, knowledge, table)
  - `resources/` 目錄：2 個模組共 12 resources (document, table)
  - `mcp_app.py`：單一 FastMCP 實例
  - `dependencies.py`：Composition Root / DI 容器

### Fixed
- 🐛 **C2: Async mode ignore use_marker**：`JobService._process_ingest_job()` 現在正確從 `job.parameters` 讀取並傳遞 `use_marker` 參數
- 🐛 **H1: list_documents 誤列特殊目錄**：`FileStorage.list_documents()` 現在跳過 `tables`、`jobs` 目錄
- 🐛 **H4: _overlaps_existing_images 空實作**：實作 >50% bbox 重疊檢測演算法，正確過濾重複圖片

## [0.2.9] - 2026-02-09

### Added
- 📋 **Marker ETL 規格書** (`docs/marker-etl-spec.md`)：完整定義 PDF 結構化拆分的輸入/輸出契約、品質要求、驗收標準
  - 10 類品質指標 (QM/QF/QT/QI/QS/QB/QG/QST/QMT/QE)
  - 三層測試策略 (Unit → Integration → Benchmark)
  - Block Type 對照表與 Definition of Done 清單
- 🧪 **171 個單元測試全部通過**：
  - `test_marker_blocks.py`: MarkerBlock/MarkerParseResult 模型驗證 (10 項)
  - `test_marker_conversion.py`: Block→Asset 轉換與缺陷修復驗證 (27 項)
  - `test_section_tree.py`: SectionTree 結構建構與查詢 (27 項)
  - `test_section_service.py`: SectionService 服務層 (15 項)
  - `test_marker_etl.py`: Integration test 骨架（需 Marker 模型）

### Fixed
- 🐛 **Figure-Block 匹配 bug**：修復所有圖片都匹配到第一個 Figure block 的問題，改為 index-based 1:1 匹配
- 🐛 **Table row/col 未解析**：從 markdown 表格文字自動解析 `row_count` 和 `col_count`（原本固定為 0）
- 🐛 **圖片尺寸為 0x0**：使用 PIL 讀取實際圖片尺寸（`width`/`height`），同時修復了 `document_service.py` 和 `marker_adapter.py`
- 🔧 **路徑慣例統一**：修正 `SectionService` 和 `server.py` 使用 `data/sources/{doc_id}/` 與 `FileStorage` 使用 `data/{doc_id}/` 不一致問題，統一為 `data/{doc_id}/`
- 🔧 **DocId 一致性**：修正 `marker_adapter.py` 使用原始 `hashlib.md5` 生成 doc_id，改為統一使用 `DocId.generate()`

### Changed
- 📝 **指令與技能文件更新**：同步更新 `copilot-instructions.md`、`CLAUDE.md`、`AGENTS.md`、`pdf-asset-extractor/SKILL.md` 以反映雙引擎 PDF 解析、Section Navigation 等新功能
- 🏗️ **Presentation 層重構骨架**：新增 `mcp_app.py`（FastMCP 實例）、`dependencies.py`（Composition Root）、`tools/`、`resources/` 子模組結構（WIP）

## [0.2.8] - 2026-02-05

### Added
- 🌲 **動態章節導航工具**：支援任意深度的章節階層結構，完美適應不同書籍的目錄格式
  - `list_section_tree`: 顯示完整章節樹狀結構
  - `get_section_detail`: 取得特定章節詳細資訊（頁碼範圍、區塊數量、子章節）
  - `get_section_blocks`: 提取指定章節的所有內容區塊（含頁碼與 bbox）
  - `search_sections`: 搜尋章節標題
- 🏗️ **Domain 層模型**：新增 `SectionNode` 與 `SectionTree` 資料結構，遵循 DDD 架構
- ⚡ **快取機制**：`SectionService` 實作章節樹快取，避免重複解析

## [0.2.7] - 2026-01-06

### Added
- 🖼️ **三層級圖片擷取策略加速**：透過 1) XObject 提取、2) 向量圖形空間聚類、3) 非文字區域網格掃描，大幅提升複雜 PDF（如科學論文圖表、流程圖）的擷取完備度。
- ✅ **視覺內容驗證**：新增影像有效性檢查，自動過濾掉空白或無效的擷取片段，確保工具回傳的圖片資產具有實際意義。
- ⚡ **CPU 友善優化**：在不增加額外機器學習依賴（如 OCR）的情況下，透過純啟發式演算法達成與高複雜度模型相近的圖表辨識效果。

### Fixed
- 🔧 **程式碼品質提升**：修復 `pdf_extractor.py` 中的未使用變數，並優化內部資源管理機制。

## [0.2.6] - 2026-01-05

### Fixed
- 🔧 **VS Code 擴充功能路徑解析修復**：修正 `EnvManager` 在擴充功能位於子目錄時無法正確找到 `.env` 與 `data` 目錄的問題。
- 📂 **資料目錄可見性**：在 Status 視圖中顯示解析後的 `DATA_DIR` 絕對路徑，方便確認共享目錄設定。

### Added
- 📊 **A2T 表格視圖**：新增「Tables & Drafts」側邊欄視圖，直接顯示 A2T 生成的表格與草稿。
- 📗 **Excel 快速開啟**：新增「Open in Excel」右鍵選單，方便快速開啟渲染後的專業報表。

## [0.2.5] - 2026-01-05

### Added
- 🎨 **向量圖形提取支援**：針對科學論文中常見的「非獨立圖層」圖片（由向量路徑組成的圖表），新增自動偵測與渲染功能。
  - 自動計算向量圖形邊界框 (Bounding Box)
  - 高解析度渲染為 PNG 格式
  - 解決了部分 PDF 無法提取圖片的問題

## [0.2.4] - 2026-01-05

### Fixed
- 🔧 **修復 uv 路徑問題**：使用完整路徑執行 uv/uvx，不再依賴 PATH 環境變數
  - 自動搜尋常見安裝位置（Windows: AppData, Unix: ~/.local/bin, ~/.cargo/bin）
  - 儲存已找到的 uv 路徑供後續使用
- 🔄 **安裝後提示重新載入**：uv 安裝完成後會提示使用者重新載入 VS Code

### Added
- 📦 **VS Code Extension 測試框架**：新增 Mocha 測試套件
  - 擴充功能啟動測試
  - 命令註冊測試
  - 設定預設值測試
  - 工具函數測試

### Changed
- mcpProvider 支援使用 context 傳遞的 uvPath
- 改進依賴檢查命令的輸出資訊

## [0.2.3] - 2026-01-05

### Added
- 🔧 **自動安裝 uv**：擴充功能啟動時會自動檢測並安裝 `uv`（支援 Windows PowerShell 和 Unix curl）
- 🚀 **真正的一鍵即用**：使用者只需安裝擴充功能，無需任何手動設定：
  1. 擴充功能自動安裝 `uv`
  2. `uvx asset-aware-mcp` 自動從 PyPI 安裝並運行 MCP server
  3. 不需要 clone 專案、不需要手動安裝 Python 套件

### Changed
- 依賴檢查更新：不再要求本地有 MCP server 原始碼
- 安裝狀態提示更清晰

## [0.2.2] - 2026-01-05

### Added
- 🚀 **一鍵即用**：VS Code 擴充功能現在使用 `uvx asset-aware-mcp` 從 PyPI 直接運行，無需手動安裝或 clone 專案。
- 🔧 **雙模式支援**：
  - **生產模式**（預設）：使用 `uvx` 從 PyPI 自動安裝並運行
  - **開發模式**：如果在 workspace 中偵測到本地原始碼，會自動切換使用本地版本

### Changed
- 環境變數現在完全從 VS Code 設定面板讀取，無需手動編輯 `.env` 檔案
- `DATA_DIR` 預設為工作區的 `./data` 目錄

## [0.2.1] - 2026-01-05

### Fixed
- 🐛 **VS Code 擴充功能啟動修復**：修復 TypeScript 編譯錯誤（重複宣告問題）與 `@types/vscode` 版本不匹配。
- 🔧 **移除不必要的 API 提案**：MCP API 在 VS Code 1.96+ 已是穩定 API，移除 `enabledApiProposals`。
- 📝 **新增診斷日誌**：擴充功能現在會輸出詳細的啟動日誌到 Output Channel，方便除錯。
- ➕ **新增 Show Output 命令**：使用者可透過命令面板顯示擴充功能日誌。

## [0.2.0] - 2026-01-05

### Added
- 📊 **A2T 2.0 (Anything to Table)**：重大升級，支援持久化草稿 (Drafting)、Token 節省續作 (Resumption) 與 AI 驅動的表格規劃工具。
- 🚀 **輕量化 ETL 引擎**：完全移除 Docling (2GB+ 依賴)，改用 **PyMuPDF (fitz)** 作為核心解析引擎。
- 🛠️ **型別安全與品質提升**：修復了 187+ 個 Ruff lint 錯誤與 29+ 個 MyPy 型別錯誤。
- 📦 **uv 整合優化**：更新所有指令使用 `uv run`，確保環境隔離。
- 🧩 **VS Code 擴充功能安全性更新**：升級 TypeScript 5.7.2 與 ESLint 9。

### Changed
- 移除 `docling` 相關 adapter 與依賴。
- 更新 `README`、`spec.md` 與 `ARCHITECTURE.md` 以反映 PyMuPDF 與 A2T 2.0 架構。

### Fixed
- 修復 `TableAsset` 屬性名稱不一致問題 (`description` -> `caption`)。
- 修復 `ChunkingStrategy` 抽象類別實作問題。

## [0.1.1] - 2025-12-26

### Added
- 🎯 **完整 MCP Server** - 5 個工具全部實作完成
  - `ingest_documents` - PDF 匯入與 ETL 處理
  - `list_documents` - 列出已處理文件
  - `inspect_document_manifest` - 查看文件結構清單
  - `fetch_document_asset` - 精準取得表格/章節/圖片
  - `consult_knowledge_graph` - LightRAG 知識圖譜查詢
- 🏗️ **DDD 分層架構** - Domain/Application/Infrastructure/Presentation
- 🧪 **完整測試覆蓋** - 55 個測試（單元測試 + 整合測試）
- 📚 **Claude Skills 系統**
  - `mcp-operator` - MCP 工具操作指南
  - `git-precommit` - Git 提交前編排器
  - `code-refactor` - 程式碼重構輔助
  - `test-generator` - 測試生成器
  - 更多 skills（共 13 個）
- 🧠 **Ollama 整合** - 本地 LLM 支援（qwen2.5:7b + nomic-embed-text）
- 📖 **完整文檔體系**
  - `CONSTITUTION.md` - 專案憲法
  - `AGENTS.md` - Agent Mode 入口
  - `.github/copilot-instructions.md` - Copilot 自定義指令

### Changed
- 從 OpenAI 改為 Ollama 作為預設 LLM 後端
- 重構 PDF 提取器使用 PyMuPDF

## [0.1.0] - 2025-12-15

### Added
- 初始化專案結構
- 新增 Claude Skills 支援
  - `git-doc-updater` - Git 提交前自動更新文檔技能
- 新增 Memory Bank 系統
  - `activeContext.md` - 當前工作焦點
  - `productContext.md` - 專案上下文
  - `progress.md` - 進度追蹤
  - `decisionLog.md` - 決策記錄
  - `projectBrief.md` - 專案簡介
  - `systemPatterns.md` - 系統模式
  - `architect.md` - 架構文檔
- 新增 VS Code 設定
  - 啟用 Claude Skills
  - 啟用 Agent 模式
  - 啟用自定義指令檔案
