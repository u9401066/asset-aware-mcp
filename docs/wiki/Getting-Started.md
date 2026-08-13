# Getting Started

## 安裝與啟動

若是一般 Codex 使用者，直接加入已發布且版本鎖定的 stdio server：

```bash
codex mcp add asset-aware-mcp -- uv tool run --python 3.11 --from asset-aware-mcp==1.0.1 asset-aware-mcp
```

以下是 repository 開發模式：

```bash
uv sync
uv run python -m src.presentation.server
```

正式使用前先跑 diagnostics：

```bash
uv run asset-aware-mcp doctor --json
uv run asset-aware-mcp list-tools --json
```

目前 `1.0.1` 的安全預設是：

| 設定 | 預設 | 原因 |
|---|---|---|
| PDF backend | PyMuPDF | 不需要大型模型，也避開 Marker/Pillow 安全相容性問題 |
| `OLLAMA_MODEL` | `granite4.1:3b` | CPU-friendly 本機 RAG/text generation 預設模型；設定 `ASSET_AWARE_HAS_GPU=true` 或 `NVIDIA_VISIBLE_DEVICES` 時會選 `granite4.1:8b`，也可手動覆寫成任何已安裝 Ollama 模型 |
| `OPENROUTER_MODEL` | `liquid/lfm-2.5-1.2b-instruct:free` | Optional OpenRouter fast/free preset for low-cost summaries and draft RAG answers; set `LLM_BACKEND=openrouter` and `OPENROUTER_API_KEY` in VS Code Settings or `.env` |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | 只有啟用 LightRAG/KG 時才需要 embedding model |
| `ENABLE_LIGHTRAG` | `false` | CPU-only 或文件處理情境不會因 KG 沒裝好而失敗 |

`1.0.1` 的 active packaged PDF extras 只有 `[pdf-plus]`（PyMuPDF4LLM）與
`[docling]`。MinerU 3.4.4 鎖定 `transformers<5`、Marker PDF 1.10.2 鎖定
`Pillow<11`，分別與目前 `transformers>=5.5`、`Pillow>=12.2.0` 安全底線
衝突，因此 `[mineru]` 與 `[marker]` 都是空的 fail-closed security hold，不能
透過 installer 啟用。`use_marker=true` 是為相容舊 client 保留的參數名稱，現在
表示「要求目前設定的 structured extractor」；請設定 `ETL_ENGINE=docling`，或
使用預設 PyMuPDF／`ETL_ENGINE=pymupdf4llm`。公開工具沒有 `require_marker` 參數；
那是 worker 內部的 fail-closed job policy。`parse_pdf_structure` 也會先驗證
configured structured extractor，held 或缺少 backend 時不建立 job。

來源：`pyproject.toml`、`README.md`、`CHANGELOG.md`。

## 最短 PDF 流程

```text
document(op="auto", file_paths=["/path/paper.pdf"], async_mode=true)
job(op="get", job_id="...")
document(op="prepare_ai", doc_id="...")
document(op="audit", doc_id="...")
document(op="pointer_index", doc_id="...")
document(op="structural_retrieve", doc_id="...", query="outcome")
evidence(op="find", doc_id="...", query="outcome")
evidence(op="bundle", doc_id="...", query="outcome", output_format="json")
citation_bundle(doc_id="...", query="outcome", output_format="foam", citation_key="paper-key")
citation_bundle(
  doc_id="...",
  query="outcome",
  output_format="foam",
  citation_key="paper-key",
  wiki_root="/path/to/wiki",
  output_path="evidence/paper-key.md"
)
evidence(op="health", wiki_root="/path/to/wiki", output_format="json")
document_asset(
  op="foam_notes",
  doc_id="...",
  asset_type="all",
  asset_id="all",
  wiki_root="/path/to/wiki",
  output_dir="assets",
  citation_key="paper-key"
)
```

長任務會回傳 background job。這包含 PDF ingest、configured structured parse、OCR 與 conversion，目的是避免 Cline/Codex/VS Code stdio MCP request 被大型文件阻塞。若需要舊版同步 conversion，可在 conversion tool 傳入 `async_mode=false`。

`document(op="ingest"/"auto")` 與 `ingest_documents(...)` 至少需要一個
非空白的 input path。空清單或空白 path 會直接回報 validation error，
不會產生無意義的 `0/0` completed job。

## 最短 DOCX 流程

```text
ingest_docx(file_path="/path/report.docx")
get_docx_content(doc_id="docx_...")
save_docx(doc_id="docx_...", dfm_content="...", track_changes=true)
docx_table_edit_plan(doc_id="docx_...", block_id="...", target_columns=["A", "B"])
docx_validate_roundtrip(doc_id="docx_...", strict=true)
```

DOCX pipeline 會保留 DFM block identity、格式 metadata、表格、圖片、header/footer/footnote story parts，並在 strict validation 中檢查 round-trip 風險。

## VS Code Extension

Extension 會提供：

- 原生 VS Code MCP provider。
- Copilot workspace `.vscode/mcp.json` merge。
- Cline MCP settings merge。
- Codex `~/.codex/config.toml` merge。
- Assistant harness assets sync：`AGENTS.md`、`.github/copilot-instructions.md`、`.github/agents`、`.github/bylaws`、`.claude/skills`、`.cline/skills`、`.codex/skills`、`.clinerules`。
- Documents tree 中的 artifact/citation viewer，可直接開啟 manifest、segmentation、citation index 與 EvidenceSpan line。

Codex managed entry 預設使用 `startup_timeout_sec = 180` 與
`tool_timeout_sec = 900`。API key/token 等機密值不會被寫入 TOML；
config 只以 `env_vars` 記錄必要名稱。Codex 只會轉送啟動 Codex client 時
已存在於 OS environment 的同名值，不會讀取 workspace `.env` 或 VS Code
secret setting；遠端 backend 使用者需在啟動 Codex 前 export credential。
若要自行維護 Codex config，將
machine-scoped `assetAwareMcp.manageCodexConfig` 設為 `false`，extension 就會
移除自己管理的 block 並停止重建，但不動使用者的同名 custom block。

MCP SDK 2 protocol logging 已 deprecated；server 的運作訊息使用 Python
logging 寫到 stderr，MCP JSON-RPC stdout 保持純淨。Progress notification
仍透過 SDK 2 `Context` 發送。

相關頁面：[VS Code Extension And MCP Setup](VS-Code-Extension-And-MCP-Setup)。
