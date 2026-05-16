# Getting Started

## 安裝與啟動

```bash
uv sync
uv run python -m src.presentation.server
```

正式使用前先跑 diagnostics：

```bash
uv run asset-aware-mcp doctor --json
uv run asset-aware-mcp list-tools --json
```

目前 `0.6.35` 的安全預設是：

| 設定 | 預設 | 原因 |
|---|---|---|
| PDF backend | PyMuPDF | 不需要大型模型，也避開 Marker/Pillow 安全相容性問題 |
| `OLLAMA_MODEL` | `granite4.1:3b` | CPU-friendly 本機 RAG/text generation 預設模型；設定 `ASSET_AWARE_HAS_GPU=true` 或 `NVIDIA_VISIBLE_DEVICES` 時會選 `granite4.1:8b`，也可手動覆寫成任何已安裝 Ollama 模型 |
| `OPENROUTER_MODEL` | `liquid/lfm-2.5-1.2b-instruct:free` | Optional OpenRouter fast/free preset for low-cost summaries and draft RAG answers; set `LLM_BACKEND=openrouter` and `OPENROUTER_API_KEY` in VS Code Settings or `.env` |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | 只有啟用 LightRAG/KG 時才需要 embedding model |
| `ENABLE_LIGHTRAG` | `false` | CPU-only 或文件處理情境不會因 KG 沒裝好而失敗 |

`0.6.35` 的預設安裝仍不會安裝 Marker，因為 upstream `marker-pdf` 1.10.2 仍要求 `Pillow<11`，而此版本安全 runtime 需要 `Pillow>=12.2.0`。目前請使用預設 PyMuPDF 後端。`parse_pdf_structure` 是 Marker-required 入口，Marker backend unavailable 或 security hold 會在建立 job 前回傳明確診斷；`ingest_documents(use_marker=true)` 只代表偏好 Marker，公開工具沒有 `require_marker` 參數，Marker 不可用時會回到 PyMuPDF 的安全流程。

來源：`pyproject.toml`、`README.md`、`CHANGELOG.md`。

## 最短 PDF 流程

```text
ingest_documents(file_paths=["/path/paper.pdf"], async_mode=true)
get_job_status(job_id="...")
inspect_document_manifest(doc_id="...")
export_document_segmentation(doc_id="...")
find_evidence_spans(doc_id="...", query="outcome")
citation_bundle(doc_id="...", query="outcome", output_format="json")
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

長任務會回傳 background job。這包含 PDF ingest、Marker-required parse、OCR 與 conversion，目的是避免 Cline/Codex/VS Code stdio MCP request 被大型文件阻塞。若需要舊版同步 conversion，可在 conversion tool 傳入 `async_mode=false`。

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

相關頁面：[VS Code Extension And MCP Setup](VS-Code-Extension-And-MCP-Setup)。
