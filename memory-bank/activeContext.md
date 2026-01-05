# Active Context

> 📌 當前工作焦點和進行中的變更

## 🎯 當前焦點

- **v0.2.0 發布完成：A2T 2.0 與 PyMuPDF 輕量化整合**
- 成功實作 Draft/Commit 模式、AI 規劃工具與 Token 優化。
- 完成全專案品質修復 (Ruff/MyPy) 與 CI/CD 優化。
- 完成 README i18n 清理（中英文分離）。

## Current Goals

- 維護 v0.2.0 穩定性並收集用戶回饋。
- 準備下一階段的功能開發（如 E2E 測試強化）。
- 支援：
- 1. **Draft/Commit 模式**：持久化 WIP 狀態，支援長表格分批寫入。
- 2. **Token 優化**：`resume_draft` 僅回傳最小上下文；`get_section_content` 支援精準讀取。
- 3. **AI 規劃工具**：`plan_table_schema` 協助 Agent 發想表格結構。
- 4. **精準編輯**：`update_cell` 支援單元格級別的 CRUD。
- 5. **版本發布**：全專案（含 Extension）已升級至 v0.2.0。

## 📝 本次變更

| 檔案/目錄 | 變更內容 |
|-----------|----------|
| `README.md` / `README.zh-TW.md` | **i18n 清理**：確保中英文內容完全分離，無混用。 |
| `memory-bank/` | **同步更新**：更新所有記憶文件以反映 v0.2.0 最終狀態。 |
| `src/presentation/server.py` | **型別修復**：解決 MyPy 報錯，提升代碼健壯性。 |
| `scripts/release.sh` | **路徑修復**：確保發布腳本在不同環境下皆可正確執行。 |

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
