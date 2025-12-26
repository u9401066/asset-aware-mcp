# Changelog

所有重要變更都會記錄在此檔案中。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
專案遵循 [語義化版本](https://semver.org/lang/zh-TW/)。

## [Unreleased]

### Known Issues
- 圖片返回格式為 markdown string，尚未支援 MCP ImageContent（視覺 AI 無法看圖）
- Figure caption 對應需要實作（fig_2_1 不等於 "Figure 1"）
- Knowledge Graph 索引需要時間才會有查詢結果

## [0.2.0] - 2025-12-26

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
