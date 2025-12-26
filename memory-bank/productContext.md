# Product Context

> 📌 此檔案描述專案的技術架構和產品定位。

## 📋 專案概述

**專案名稱**：asset-aware-mcp

**一句話描述**：Medical RAG with Asset-Aware MCP - 讓 AI Agent 精準存取 PDF 文獻中的表格、章節與知識圖譜

**目標用戶**：醫學研究人員、使用 VS Code + Copilot 的開發者

## 🏗️ 架構

```
AI Agent (Copilot)
       │ MCP Protocol
       ▼
MCP Server (server.py)
  ├── ingest_documents
  ├── inspect_document_manifest
  ├── fetch_document_asset
  └── consult_knowledge_graph
       │
       ▼
ETL Pipeline (etl.py)
  ├── Mistral OCR
  ├── Asset Parser
  └── LightRAG Index
       │
       ▼
Local Storage
  ├── {doc_id}_full.md
  ├── {doc_id}_manifest.json
  └── lightrag_db/
```

## ✨ 核心功能

- 📄 PDF → Markdown 轉換 (Mistral OCR)
- 🗺️ Document Manifest 生成 (Asset 清單)
- 🧠 LightRAG 知識圖譜建立
- 🔌 MCP Tools 暴露給 Agent

## 🔧 技術棧

| 類別 | 技術 |
|------|------|
| 語言 | Python 3.10+ |
| OCR | Mistral AI SDK (`mistralai`) |
| RAG | LightRAG (`lightrag-hku`) |
| MCP | FastMCP (`fastmcp`) |
| 儲存 | Local filesystem (JSON/Markdown) |

## 📦 依賴

### 核心依賴
- mistralai
- lightrag-hku
- fastmcp

### 開發依賴
- pytest, pytest-cov
- ruff, mypy

---
*Last updated: 2025-12-26*
