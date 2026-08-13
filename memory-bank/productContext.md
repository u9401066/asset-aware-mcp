# Product Context

> 本檔描述目前產品定位與技術真相；歷史版本決策請見
> `activeContext.md` 與 `decisionLog.md`。

## 專案定位

**asset-aware-mcp** 將 PDF、DOCX 與其他文件轉換成 agent 可重用、可驗證、
可攜帶的文字／表格／圖片資產。每筆資產保留穩定 ID、來源 hash、精確 locator
與 citation reference，並可輸出 Foam-compatible notes，供本機 LLM wiki 與
LightRAG 知識圖譜重複使用。

主要使用者是需要可信文件證據鏈的研究人員，以及透過 Codex、Cline、Copilot
或其他 MCP client 工作的開發者。

## 核心工作流

```text
source document
  -> PDF preflight / DOCX ingest
  -> bounded extractor routing
  -> canonical document artifacts
  -> segmentation + citation index
  -> deterministic agent-asset-bundle-v1
  -> Foam notes / local LLM wiki / optional LightRAG
```

- `document(op="preflight", pdf_path=...)` 在寫入前分類 PDF、指出逐頁 OCR
  原因並建議安全 route。
- `document(op="auto", file_paths=[...])` 攝入 PDF、DOCX、DOC、ODT、ODS 等
  支援格式；長任務使用可觀測 background job。
- `document(op="export_assets", doc_id=...)` 產生 deterministic manifest、
  JSONL records、Markdown/text/table/figure/media 與 portable Foam notes。
- Evidence 與 citation 工具以 source revision、line/char/byte span、page/bbox
  與 surrounding context 驗證引用，stale index 不會被宣稱為 citation-ready。
- DOCX/DFM round trip 保留 block identity、格式與媒體，寫回前執行 stale source
  與 strict validation guard。

## MCP Surface

- 官方 MCP Python SDK `>=2,<3`，使用 `MCPServer`；SDK v1／FastMCP runtime
  不受支援。
- 預設 balanced surface：30 tools（17 facade + 13 shortcuts）與 13 resources。
- compact surface：17 個 operation-based facade tools。
- legacy surface：SDK 2 上的舊 direct tool-name inventory；不是 protocol v1
  compatibility。
- Runtime `Context` 由 SDK 注入，絕不出現在公開 tool input schema。

## PDF Engines

| 狀態 | Engine | 用途 |
|---|---|---|
| default | PyMuPDF | 快速、無模型、可靠 fallback |
| optional `[pdf-plus]` | PyMuPDF4LLM | 輕量 layout-aware extraction |
| optional `[docling]` | Docling | 隔離執行的結構化表格／公式／圖表 extraction |
| security hold | MinerU | upstream 限制 `transformers<5`，目前不可安全解析 |
| security hold | Marker | upstream 限制 `Pillow<11`，與安全底線衝突 |

`pdf-inspector` 的分類、逐頁 OCR reason 與 resource-boundary 思路已落地為
內建 preflight adapter；目前不直接依賴 registry 版，因其尚未包含 pinned
upstream main 的最新 DoS hardening。

## 技術棧

| 類別 | 技術 |
|---|---|
| Runtime | Python 3.10+、uv universal lock |
| MCP | official `mcp` SDK 2.x / `MCPServer` |
| PDF | PyMuPDF、optional PyMuPDF4LLM／Docling |
| DOCX | python-docx、DFM／DocxIR reversible pipeline |
| RAG / wiki | optional LightRAG、Foam-compatible Markdown |
| Storage | local filesystem；JSON／JSONL／Markdown／media |
| Quality | pytest、Ruff、mypy、Bandit、pinned uv audit、npm audit、artifact audit |

核心 runtime dependency 包含 `mcp`、`pymupdf`、`pydantic`、`mistralai`；
LightRAG 與 structured PDF engines 採明確 optional extra / isolated runtime。

---

*Last updated: 2026-08-13*
