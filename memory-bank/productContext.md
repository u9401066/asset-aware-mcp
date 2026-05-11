# Product Context

> 📌 此檔案描述專案的技術架構和產品定位。

## 📋 專案概述

**專案名稱**：asset-aware-mcp

**一句話描述**：Asset-Aware MCP Server，讓 AI Agent 精準存取 PDF 資產並安全編輯 DOCX/DFM，支援文件級 CRUD、互轉與 strict round-trip 驗證

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

- 📄 PDF → Markdown 轉換 (PyMuPDF / Marker)
- 🧩 Unified segmentation 匯出（reading order + markdown line span）
- 🖼️ Layout overlay 偵錯（直接檢查 bbox / type / order）
- 🔤 Optional OCR preprocessing（掃描 PDF 按需前處理）
- 📝 Docx ↔ DFM 即時編輯與互轉 (17 tools, 6D validator + strict gate + table edit planning)
- 🗺️ Document Manifest 生成 (Asset 清單)
- 📊 A2T 表格系統 (7 operation-based tools)
- 🧠 LightRAG 知識圖譜建立，可選 verified evidence bundle
- 🔌 MCP Tools (62 tools in 7 modules, 13 resources) 暴露給 Agent
- 🧩 Cline-safe Marker background jobs with isolated subprocess execution and
  explicit job status artifacts/warnings for long-running structure parsing

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
*Last updated: 2026-05-11*


## Project Description

Medical RAG with Asset-Aware MCP - Precise PDF asset retrieval (tables, figures, sections) and Knowledge Graph for AI Agents. Featuring A2T (Anything to Table) 2.0 for professional data orchestration.



## Architecture

┌─────────────────────────────────────────────────────────┐
│                    AI Agent (Copilot)                   │
└─────────────────────┬───────────────────────────────────┘
                      │ MCP Protocol (Tools & Resources)
┌─────────────────────▼───────────────────────────────────┐
│                 MCP Server (server.py)                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │   ingest    │ │  inspect    │ │     fetch       │   │
│  │  documents  │ │  manifest   │ │     asset       │   │
│  └─────────────┘ └─────────────┘ └─────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │          A2T (Anything to Table) Workflow       │   │
│  │  [Plan] → [Draft] → [Batch Add] → [Commit]      │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                  ETL Pipeline (DDD)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ PyMuPDF  │  │  Asset   │  │ LightRAG │              │
│  │ Adapter  │→ │  Parser  │→ │  Index   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   Local Storage                         │
│  ./data/                                                │
│  ├── {doc_id}/        # PDF document artifacts          │
│  ├── tables/          # A2T Tables (JSON/MD/XLSX)       │
│  │   └── drafts/      # Table Drafts (Persistence)      │
│  └── lightrag_db/     # Knowledge Graph                 │
└─────────────────────────────────────────────────────────┘



## Technologies

- Python 3.10+
- DDD (Domain-Driven Design)
- MCP (Model Context Protocol)
- RAG (Retrieval-Augmented Generation)
- Knowledge Graph (LightRAG)



## Libraries and Dependencies

- PyMuPDF (fitz)
- LightRAG (lightrag-hku)
- FastMCP
- XlsxWriter
- uv
