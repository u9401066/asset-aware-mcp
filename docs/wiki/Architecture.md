# Architecture

![Asset-Aware MCP architecture](assets/overview-architecture.jpg)

## 分層結構

Asset-Aware MCP 以 DDD 方向維持邊界：

| Layer | 路徑 | 責任 |
|---|---|---|
| Domain | `src/domain` | 實體、value objects、citation、section tree、reading order、segmentation、ETL profile、table model |
| Application | `src/application` | use case 編排：document/docx/table/job/knowledge/section services、citation artifact、DFM integrity |
| Infrastructure | `src/infrastructure` | 外部 adapter：PyMuPDF、Marker、DOCX XML、LibreOffice、LightRAG、OCR、file/job store、layout visualizer |
| Presentation | `src/presentation` | FastMCP app、tools/resources、dependency composition、MCP progress/log、worker entrypoint |
| VSIX | `vscode-extension/src` | VS Code provider、settings panel、tree views、MCP config merge、assistant assets sync |

主要 import 規則：`Presentation -> Application -> Domain <- Infrastructure`。Infrastructure 只可透過明確 application port 反向接入，例如 `src.application.worker_runner`。

來源：`.github/copilot-instructions.md`、`tests/unit/test_import_boundaries.py`。

## PDF 資料流

```text
PDF
  -> DocumentService.ingest
  -> PyMuPDFExtractor 或 MarkerAdapter
  -> FileStorage
  -> $DATA_DIR/{doc_id}/original.pdf
  -> $DATA_DIR/{doc_id}/{doc_id}_full.md
  -> $DATA_DIR/{doc_id}/{doc_id}_manifest.json
  -> blocks.json
  -> segmentation.json
  -> citation_index.jsonl + citation_index.status.json
  -> images/ + manifest table/figure metadata
  -> optional LightRAG indexing
```

核心設計是同時保存「人可讀內容」與「機器可驗證 locator」。`{doc_id}_full.md` 服務全文與 LLM chunk；`{doc_id}_manifest.json` 保存 document identity 和資產摘要；`blocks.json` 保存 block-level metadata；`segmentation.json` 統一 reading order、line span、char/byte range、source revision 與 hash。A2T table 的 durable artifacts 存在 `$DATA_DIR/tables/`，PDF 內抽到的 table/figure metadata 則保存在 manifest、blocks 與 segmentation 中。

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

這個結構讓 MCP server 可以繼續回應 `get_job_status`、`cancel_job`，避免 Marker/OCR/大型 PDF ingest 卡住 stdio client。

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
  docx/{doc_id}/
  tables/
  lightrag_db/
.asset-aware-mcp/
```

`.gitignore` 會忽略 `data/`、`lightrag_db/`、`.asset-aware-mcp/`、VSIX build output 與 runtime backup。
