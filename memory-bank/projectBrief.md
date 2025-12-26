# Project Brief

> 📌 此檔案描述專案的高層級目標和範圍，建立後很少更改。

## 🎯 專案目的

建立一個 **Local-first MCP Server**，專為醫學研究設計：
- 讓 AI Agent (Copilot) 能從多個 PDF 撰寫準確報告
- 不盲目餵入全文，而是產生結構化「Document Manifest」
- Agent 可精準檢視結構、按需取得特定 Assets (表格、章節)

## 👥 目標用戶

- 醫學研究人員
- 需要處理大量 PDF 文獻的研究者
- 使用 VS Code + GitHub Copilot 的開發者

## 🏆 成功指標

- [ ] ETL Pipeline 能正確解析 PDF → Markdown
- [ ] Manifest 能清楚列出所有 Assets (表格、章節、圖片)
- [ ] MCP Server 能暴露 4 個核心工具
- [ ] Agent 能透過 Manifest 精準取得資料
- [ ] LightRAG 知識圖譜能支援跨文獻查詢

## 🚫 範圍限制

- MVP 不需要 Docker/Milvus
- ETL 階段不做 LLM 摘要（速度優先）
- 信任 Mistral OCR 的表格結構輸出

## 📝 核心設計原則

1. **Manifest First** - Agent 先查地圖，再取資料
2. **Asset-Aware** - 精準識別表格、章節、圖片
3. **Local-first** - 本地檔案系統，無需複雜基礎設施

---
*Created: 2025-12-26*
