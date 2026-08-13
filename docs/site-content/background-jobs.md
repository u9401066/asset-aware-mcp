<!-- Generated from Background-Jobs.md by scripts/build_docs_site.py -->

# Background Jobs

![Background job runtime](wiki/assets/background-jobs.jpg)

## 為什麼需要 jobs

PDF ingest、configured structured parse、OCR、LightRAG indexing 與文件格式 conversion 都可能超過 MCP client 的 request budget。Asset-Aware MCP 會把這些長任務放入 background job，讓 stdio client 仍能查詢狀態或取消任務。`convert_pdf_to_docx`、`convert_pdf_to_pptx`、DOCX/PDF/DOC/ODT conversion 與 Markdown export 現在預設 `async_mode=true`，會建立 conversion job；需要舊式同步回傳時可明確設 `async_mode=false`。

來源：`src/application/job_service.py`、`src/domain/job.py`、`src/infrastructure/job_store.py`、`src/application/ingest_worker.py`、`src/application/worker_runner.py`、`src/infrastructure/subprocess_ingest_worker_runner.py`、`src/presentation/tools/conversion_job_support.py`、`src/presentation/tools/job_tools.py`。

## Tools

| Tool | 用途 |
|---|---|
| `get_job_status(job_id)` | 查詢狀態、progress、warnings、artifacts |
| `list_jobs(active_only=false)` | 列出 jobs |
| `cancel_job(job_id)` | 取消 running job |
| `job(op=...)` | consolidated get/list/cancel |

## Job Result 內容

Job status 會盡量包含：

- status
- current step / total steps
- phase/message
- warnings
- backend
- degraded state
- artifacts
- traceback or error diagnostics
- next-step commands
- conversion result：operation、source、target_format、mode、output_path 與格式特定統計

## Worker Isolation

PDF ingest 與 Marker-backed background jobs 使用 isolated subprocess worker，stdin/stdout/stderr 會被關閉或導向 log，避免外部 MCP client 被大量模型輸出污染。Conversion jobs 使用同一個 persisted job lifecycle，但 handler 留在 MCP server process 內，方便呼叫既有 PDF/DOCX/Markdown service，並在 server restart 後由 stale-job reconciliation 明確標成 interrupted。

`JobService` 不直接依賴 presentation entrypoint；它透過 `IngestWorkerRunner` application port，讓 DDD 邊界維持清楚。

## Cancellation

取消會嘗試保留 worker 已寫入的 cancellation status，並在必要時以 bounded termination/kill fallback 結束 isolated worker。Job store 採 atomic write，降低 partial JSON 風險。
