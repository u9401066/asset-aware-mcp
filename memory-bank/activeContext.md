# Active Context

> 📌 當前工作焦點和進行中的變更

## 🎯 當前焦點

- **發布 v0.2.0：A2T 2.0 與 PyMuPDF 輕量化整合**
- 實作了 Draft/Commit 模式以優化 Token 使用。
- 支援 AI 驅動的表格規劃 (`plan_table_schema`)。
- 支援持久化草稿與斷點續作 (`resume_draft`)。
- 完成 Ruff 程式碼品質修復與格式化。
- 同步更新 VS Code Extension 版本至 0.2.0。

## Current Goals

- 已完成 A2T 2.0 模組的完整實作、文檔更新與版本發布。
- 目前支援：
- 1. **Draft/Commit 模式**：持久化 WIP 狀態，支援長表格分批寫入。
- 2. **Token 優化**：`resume_draft` 僅回傳最小上下文；`get_section_content` 支援精準讀取。
- 3. **AI 規劃工具**：`plan_table_schema` 協助 Agent 發想表格結構。
- 4. **精準編輯**：`update_cell` 支援單元格級別的 CRUD。
- 5. **版本發布**：全專案（含 Extension）升級至 v0.2.0。

## 📝 本次變更

| 檔案/目錄 | 變更內容 |
|-----------|----------|
| `src/domain/table_entities.py` | 新增 `TableDraft`, `TableSchema`, Token 估算邏輯 |
| `src/application/table_service.py` | 實作 Draft 管理、單元格更新、持久化邏輯 |
| `src/presentation/server.py` | 註冊 A2T 2.0 MCP Tools 與 Resources |
| `docs/spec.md` | 更新 A2T 2.0 技術規格 |
| `ROADMAP.md` | 標記 v0.3.0 (A2T 2.0) 為已完成 |
| `README.md` / `README.zh-TW.md` | 更新功能列表、架構圖與工具說明 |
| `ARCHITECTURE.md` | 更新 DDD 組件說明與 A2T 工作流 |

## ⚠️ 待解決

1. **E2E 測試**：撰寫針對 A2T 2.0 工作流的整合測試。
2. **Knowledge Graph**：優化 LightRAG 與 A2T 的自動化整合。

## 💡 重要決定 (2026-01-05)

### A2T 2.0 設計
- **Draft 模式**：為了解決長表格導致的 Token 爆炸問題，引入持久化草稿。
- **Resume 邏輯**：Agent 續作時只需讀取最後 2 列，而非整張表。
- **Planning 工具**：在建表前增加一個「發想」階段，提升 AI 產出品質。

## 📁 專案結構

```
src/
├── domain/          # 🔵 核心業務邏輯 (新增 TableDraft)
├── application/     # 🟢 使用案例 (新增 TableService Draft 邏輯)
├── infrastructure/  # 🟠 外部依賴實作 (Excel 渲染)
└── presentation/    # 🔴 MCP Server (A2T 2.0 Tools)
```

---
*Last updated: 2026-01-05*
