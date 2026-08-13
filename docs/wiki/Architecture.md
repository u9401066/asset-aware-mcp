# Architecture

## 分層結構

Asset-Aware MCP 以 DDD 方向維持邊界：

| Layer | 路徑 | 責任 |
|---|---|---|
| Domain | `src/domain` | 實體、value objects、citation、section tree、reading order、segmentation、PDF preflight schema、ETL profile、table model |
| Application | `src/application` | use case 編排：document/docx/table/job/knowledge/section services、PDF preflight、agent asset bundle、citation artifact、DFM integrity、ETL profile detect |
| Infrastructure | `src/infrastructure` | 外部 adapter：PyMuPDF/PyMuPDF4LLM/Docling、process-isolated PDF preflight、DOCX XML、LibreOffice、LightRAG、OCR、file/job store、layout visualizer；MinerU/Marker adapter 保留但依賴處於 security hold |
| Presentation | `src/presentation` | 官方 MCP Python SDK 2 `MCPServer`、tools/resources、dependency composition、runtime Context progress、stderr Python logging、worker entrypoint |
| VSIX | `vscode-extension/src` | VS Code provider、settings panel、tree views、MCP config merge、assistant assets sync |

主要 import 規則：`Presentation -> Application -> Domain <- Infrastructure`。Infrastructure 只可透過明確 application port 反向接入，例如 `src.application.worker_runner`。

來源：`.github/copilot-instructions.md`、`tests/unit/test_import_boundaries.py`。

## MCP SDK 2 邊界

- Runtime contract 是 `mcp>=2,<3` 與官方 `mcp.server.mcpserver.MCPServer`；SDK v1
  不受支援，也沒有 `mcp.server.fastmcp` fallback。
- `AssetAwareMCPServer` 只透過 SDK 公開的 `add_tool`、`remove_tool`、
  `list_tools` API 追蹤與裁切 registry，不依賴 private tool-manager internals。
- Tool 的 `Context` 參數由 MCPServer 在 request runtime 注入，只用於 bounded
  progress；它不是 client input。Operational logs 使用 Python logging 寫到
  stderr，不呼叫 deprecated MCP protocol logging API。回歸測試會檢查所有公開
  input schema 都沒有 `ctx`，避免 framework-only 欄位洩漏給 agent。
- `balanced`、`compact`、`legacy` 是同一個 SDK 2 server 上的 tool UX policy。
  `legacy` 只保留舊 direct tool 名稱與 allow-list，不代表 SDK v1 protocol 相容。

## PDF 資料流

```text
PDF
  -> optional document(op="preflight")
  -> pdf-preflight-v1 routing report (read-only, process-isolated)
  -> DocumentService.ingest
  -> PyMuPDFExtractor / PyMuPDF4LLM / Docling
  -> FileStorage
  -> $DATA_DIR/{doc_id}/original.pdf
  -> $DATA_DIR/{doc_id}/{doc_id}_full.md
  -> $DATA_DIR/{doc_id}/{doc_id}_manifest.json
  -> blocks.json
  -> segmentation.json
  -> citation_index.jsonl + citation_index.status.json
  -> images/ + manifest table/figure metadata
  -> optional LightRAG indexing
  -> optional document(op="export_assets")
  -> portable agent-asset-bundle-v1 + Foam subtree
```

核心設計是同時保存「人可讀內容」與「機器可驗證 locator」。`{doc_id}_full.md` 服務全文與 LLM chunk；`{doc_id}_manifest.json` 保存 document identity 和資產摘要；`blocks.json` 保存 block-level metadata；`segmentation.json` 統一 reading order、line span、char/byte range、source revision 與 hash。A2T table 的 durable artifacts 存在 `$DATA_DIR/tables/`，PDF 內抽到的 table/figure metadata 則保存在 manifest、blocks 與 segmentation 中。

`document(op="preflight", pdf_path=...)` 不攝入或改寫來源；它先用有 timeout、
file/page/layout-item/memory 上限的隔離程序分類 native、sparse、image、scanned、
hybrid pages，回傳 source SHA-256、1-based page/bbox locator、OCR pages 與建議引擎。
`document(op="export_assets", doc_id=...)` 則在 ingest 後把 text/table/figure、
AssetRef/evidence refs、locator 與 hashes 組成 deterministic bundle，供其他 agent
重用或直接掛入 Foam wiki。

## DOCX/DFM 資料流

```text
DOCX/DOC
  -> DocxAdapter.parse_to_ir
  -> DocxIR
  -> DFM renderer/parser
  -> editable content.dfm/content.md/format.yaml
  -> DocxService.save_docx
  -> DFM integrity gates
  -> DocxAdapter.ir_to_docx
  -> optional Word Track Changes + revisions.jsonl
  -> strict DocxValidator round trip
```

DOCX 儲存不只是文字替換；它會保留 block identity、run-level style、tables、merged cells、nested tables、headers/footers/footnotes、hyperlink/SDT wrapper，以及必要的 protected blocks。

## Background Job 邊界

`JobService` 將耗時任務拆出 MCP request path。`src/application/worker_runner.py` 定義 runner port，`src/infrastructure/subprocess_ingest_worker_runner.py` 實作 subprocess 隔離，`src/presentation/ingest_worker_main.py` 是 worker entrypoint。

這個結構讓 MCP server 可以繼續回應 `get_job_status`、`cancel_job`，避免 structured extraction/OCR/大型 PDF ingest 卡住 stdio client。`0.6.28` 起 conversion tools 也預設建立 `JobType.CONVERSION` background job；conversion handler 目前在 MCP process 內執行，因此重啟後可保留 job record，但未完成的 in-memory handler 不會跨 process 恢復。

## Storage Layout

預設 runtime data 不應提交：

```text
data/
  {doc_id}/
    original.pdf
    {doc_id}_full.md
    {doc_id}_manifest.json
    blocks.json
    segmentation.json
    citation_index.jsonl
    citation_index.status.json
    images/
    ocr/
    pages/
    agent-assets/
      manifest.json
      assets.jsonl
      index.md
      notes/
      media/
  docx/{doc_id}/
  tables/
  lightrag_db/
.asset-aware-mcp/
```

`.gitignore` 會忽略 `data/`、`lightrag_db/`、`.asset-aware-mcp/`、VSIX build output 與 runtime backup。
