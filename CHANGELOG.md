# Changelog

所有重要變更都會記錄在此檔案中。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
專案遵循 [語義化版本](https://semver.org/lang/zh-TW/)。

## [Unreleased]

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
