<!-- Generated from Background-Jobs.md by scripts/build_docs_site.py -->

# Background Jobs

![Background job runtime](wiki/assets/background-jobs.jpg)

## 為什麼需要 jobs

PDF parsing、Marker、OCR、LightRAG indexing 和 conversion 都可能超過 MCP client 的 request budget。Asset-Aware MCP 會把長任務放入 background job，讓 stdio client 仍能查詢狀態或取消任務。

來源：`src/application/job_service.py`、`src/domain/job.py`、`src/infrastructure/job_store.py`、`src/application/ingest_worker.py`、`src/application/worker_runner.py`、`src/infrastructure/subprocess_ingest_worker_runner.py`、`src/presentation/tools/job_tools.py`。

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

## Worker Isolation

Marker-backed background jobs 使用 isolated subprocess worker，stdin/stdout/stderr 會被關閉或導向 log，避免外部 MCP client 被大量模型輸出污染。

`JobService` 不直接依賴 presentation entrypoint；它透過 `IngestWorkerRunner` application port，讓 DDD 邊界維持清楚。

## Cancellation

取消會嘗試保留 worker 已寫入的 cancellation status，並在必要時以 bounded termination/kill fallback 結束 isolated worker。Job store 採 atomic write，降低 partial JSON 風險。
