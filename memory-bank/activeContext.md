# Active Context

> 📌 當前工作焦點和進行中的變更

## 🎯 當前焦點

- **v0.2.7 發布：強化圖片擷取與 A2T 整合**
- 實作三層級圖片擷取策略（XObject, Vector Clustering, Grid Scanning），大幅提升 PDF 圖表擷取完整度。
- 修正擴充功能路徑解析問題，確保 `data` 目錄在不同工作區配置下皆可見。
- 優化 A2T (Anything to Table) 視圖與 Excel 導出功能。

## Current Goals

- ### 當前焦點：v0.2.7 圖片擷取策略優化 (已完成)
- - **三層級擷取**：解決科學論文中「由向量路徑組成」的圖表無法被傳統工具識別的問題。
- - **低資源消耗**：維持 CPU 友善，不依賴重型 OCR 模型。
- - **A2T 視覺增強**：提升表格生成過程中對 PDF 視覺資產的引用精準度。
- ### 修改的檔案
- - `src/infrastructure/pdf_extractor.py` - 核心擷取邏輯重構
- - `pyproject.toml` & `vscode-extension/package.json` - 版本號更新至 0.2.7
- - `CHANGELOG.md` - 記錄新功能
- ### 下一步
- - 執行 Git commit + push tag v0.2.7

## 📝 本次變更

| 檔案/目錄 | 變更內容 |
|-----------|----------|
| `src/infrastructure/pdf_extractor.py` | **三層級擷取**：新增向量聚類與網格掃描，大幅提升擷取完備度。 |
| `vscode-extension/` | **擴充功能增強**：路徑解析修復與 Tables & Drafts 視圖。 |
| `CHANGELOG.md` | **版本日誌**：新增 0.2.7 變更紀錄。 |
| `pyproject.toml` | **版本更新**：0.2.6 -> 0.2.7。 |

## ⚠️ 待解決

1. **E2E 測試**：撰寫針對 A2T 2.0 工作流的整合測試。
2. **Knowledge Graph**：優化 LightRAG 與 A2T 的自動化整合。

## 💡 重要決定 (2026-01-06)

### 圖片擷取策略
- **為何不使用 OCR？**：考慮到醫療情境下，使用者可能使用筆電或無 GPU 環境，啟發式向量聚類能提供極高的效能/品質比。
- **三層級防護**：XObject 處理標準圖片，向量聚類處理專業繪圖，網格掃描處理無法通過前兩者識別的複雜圖案。

## 📁 專案結構

```
src/
├── domain/          # 🔵 核心業務邏輯 (新增 TableDraft)
├── application/     # 🟢 使用案例 (新增 TableService Draft 邏輯)
├── infrastructure/  # 🟠 外部依賴實作 (Excel 渲染, PDF 提取)
└── presentation/    # 🔴 MCP Server (A2T 2.0 Tools)
```

---
*Last updated: 2026-01-06*
