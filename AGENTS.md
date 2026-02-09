# AGENTS.md

> 📌 此檔案為 VS Code GitHub Copilot 的 Agent Mode 提供專案上下文入口。
> 
> 詳細指令請參見：[`.github/copilot-instructions.md`](.github/copilot-instructions.md)

---

## 快速參考

### 專案類型

- **MCP Server** - Asset-Aware Medical RAG
- **語言**: Python 3.10+
- **框架**: FastMCP, LightRAG, PyMuPDF, marker-pdf
- **策略**: 雙引擎 PDF 解析（PyMuPDF 快速 + Marker 高精度）

### 關鍵規則

1. 遵循 **DDD 分層架構**
2. 使用 **uv** 管理依賴
3. 更新 **Memory Bank** 保持上下文
4. 提交前執行 **檢查清單**

### 重要檔案

| 檔案 | 用途 |
|------|------|
| `.github/copilot-instructions.md` | 完整 Copilot 指令 |
| `CONSTITUTION.md` | 專案憲法（最高原則） |
| `memory-bank/` | 專案記憶庫 |
| `docs/spec.md` | 技術規格 |
| `docs/marker-etl-spec.md` | Marker ETL 規格書 |

### 核心功能

- 📄 **PDF ETL** — 雙引擎文件拆解（圖片、表格、章節）
- 📊 **A2T** — Anything to Table 表格建立
- 🧭 **Section Navigation** — 動態層級章節導航（4 Tools）
- 🔍 **Knowledge Graph** — 跨文獻知識圖譜（LightRAG）
- 🖼️ **Vision AI** — 圖片分析（base64 返回）

### LLM 後端

- **預設**: Ollama (本地)
  - LLM: `qwen2.5:7b`
  - Embedding: `nomic-embed-text`
- **備選**: OpenAI (需 API Key)

---

*詳細內容請參閱 `.github/copilot-instructions.md`*
