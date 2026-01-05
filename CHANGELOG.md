# Changelog

所有重要變更都會記錄在此檔案中。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
專案遵循 [語義化版本](https://semver.org/lang/zh-TW/)。

## [0.2.2] - 2026-01-05

### Added
- 🚀 **一鍵即用**：VS Code 擴充功能現在使用 `uvx asset-aware-mcp` 從 PyPI 直接運行，無需手動安裝或 clone 專案。
- 🔧 **雙模式支援**：
  - **生產模式**（預設）：使用 `uvx` 從 PyPI 自動安裝並運行
  - **開發模式**：如果在 workspace 中偵測到本地原始碼，會自動切換使用本地版本

### Changed
- 環境變數現在完全從 VS Code 設定面板讀取，無需手動編輯 `.env` 檔案
- `DATA_DIR` 預設為工作區的 `./data` 目錄

## [0.2.1] - 2026-01-06

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
