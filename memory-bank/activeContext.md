# Active Context

> 📌 當前工作焦點和進行中的變更

## 🎯 當前焦點

- **v0.2.0 發布完成：A2T 2.0 與 PyMuPDF 輕量化整合**
- 成功實作 Draft/Commit 模式、AI 規劃工具與 Token 優化。
- 完成全專案品質修復 (Ruff/MyPy) 與 CI/CD 優化。
- 完成 README i18n 清理（中英文分離）。

## Current Goals

- ## 當前焦點：v0.2.6 修復與增強 (已完成)
- ### 本次修復內容
- - **路徑解析修復**：修正 `EnvManager` 在擴充功能位於子目錄時無法正確找到 `.env` 與 `data` 目錄的問題（解決「明明有資料卻顯示 not found」）。
- - **跨用戶可見性**：透過顯示解析後的 `DATA_DIR` 路徑，讓用戶能確認擴充功能是否指向正確的共享目錄。
- - **新增表格視圖**：新增「Tables & Drafts」側邊欄視圖，直接顯示 A2T 生成的表格與草稿。
- - **Excel 整合**：新增「Open in Excel」右鍵選單，方便用戶快速開啟渲染後的專業報表。
- - **程式碼品質**：修復 `pdf_extractor.py` 中的未使用變數並通過 Ruff 檢查。
- ### 修改的檔案
- - `vscode-extension/src/envManager.ts` - 增強路徑解析邏輯
- - `vscode-extension/src/tableTreeProvider.ts` - 新增表格樹狀提供者
- - `vscode-extension/src/extension.ts` - 註冊新視圖與命令
- - `vscode-extension/src/statusTreeProvider.ts` - 顯示資料目錄路徑
- - `vscode-extension/package.json` - 註冊視圖、圖示與選單
- - `src/infrastructure/pdf_extractor.py` - 修復未使用變數
- - `CHANGELOG.md`, `README.md`, `README.zh-TW.md`, `ROADMAP.md` - 更新文檔
- ### 下一步
- - 執行 Git commit + push

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
