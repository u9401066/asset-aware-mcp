<!-- Generated from Getting-Started.md by scripts/build_docs_site.py -->

# Getting Started

## 安裝與啟動

```bash
uv sync
uv run python -m src.presentation.server
```

`0.6.27` 的預設安裝不會安裝 Marker，因為 upstream `marker-pdf` 1.10.2 仍要求 `Pillow<11`，而此版本安全 runtime 需要 `Pillow>=12.2.0`。目前請使用預設 PyMuPDF 後端；`use_marker=True` 或 `parse_pdf_structure` 會回報 Marker 暫不可用，而不是靜默使用不安全依賴。

來源：`pyproject.toml`、`README.md`、`CHANGELOG.md`。

## 最短 PDF 流程

```text
ingest_documents(file_paths=["/path/paper.pdf"], async_mode=true)
get_job_status(job_id="...")
inspect_document_manifest(doc_id="...")
export_document_segmentation(doc_id="...")
find_evidence_spans(doc_id="...", query="outcome")
```

長任務會回傳 background job。這包含 PDF ingest、Marker parse、OCR 與部分 conversion，目的是避免 Cline/Codex/VS Code stdio MCP request 被大型文件阻塞。

## 最短 DOCX 流程

```text
ingest_docx(file_path="/path/report.docx")
get_docx_content(doc_id="docx_...")
save_docx(doc_id="docx_...", dfm_content="...", track_changes=true)
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

相關頁面：[VS Code Extension And MCP Setup](#/vs-code-extension)。
