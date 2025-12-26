# Active Context

> 📌 當前工作焦點和進行中的變更

## 🎯 當前焦點

- **準備 GitHub 首次 Push**
- MCP 系統 5 工具全部實作完成
- 55 個測試全數通過

## Current Goals

1. 建立 GitHub repository 並 push
2. 修復圖片返回格式（ImageContent vs markdown string）
3. 實作 figure caption 解析

## 📝 已完成的變更

| 檔案/目錄 | 變更內容 |
|-----------|----------|
| `src/domain/` | Entities, Value Objects, Services, Repositories |
| `src/application/` | DocumentService, AssetService, KnowledgeService |
| `src/infrastructure/` | FileStorage, PDFExtractor, LightRAGAdapter, Config |
| `src/presentation/server.py` | MCP Server (5 Tools) |
| `tests/` | 55 個測試（unit + integration） |
| `.claude/skills/mcp-operator/` | MCP 操作指南 skill |
| `CONSTITUTION.md` | 專案憲法 |
| `AGENTS.md` | Agent Mode 入口 |

## ⚠️ 待解決

1. **圖片格式問題**：server.py 返回 markdown string，應返回 `ImageContent` 讓 vision AI 可看圖
2. **Figure caption 對應**：`fig_2_1` 不等於 "Figure 1"，需解析 PDF 中的 caption
3. **Knowledge Graph**：LightRAG 索引需要時間才會有結果

## 💡 重要決定

- 使用 PyMuPDF 作為主要 PDF 解析 (保留頁碼資訊)
- Base64 傳輸圖片，附帶頁碼供驗證
- Manifest First 設計原則
- Local-first 儲存策略
- 使用 Ollama 本地 LLM（預設）

## 📁 專案結構

```
src/
├── domain/          # 🔵 核心業務邏輯
├── application/     # 🟢 使用案例
├── infrastructure/  # 🟠 外部依賴實作
└── presentation/    # 🔴 MCP Server
tests/
├── unit/            # ✅ 單元測試
└── integration/     # ✅ 整合測試
```

---
*Last updated: 2025-12-26*
