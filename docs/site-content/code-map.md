<!-- Generated from Code-Map.md by scripts/build_docs_site.py -->

# Code Map

此頁用於快速定位目前 code 功能。詳細 API surface 見 [MCP Tools](#/mcp-tools) 與 [MCP Resources](#/mcp-resources)。

## Domain

| 檔案 | 功能 |
|---|---|
| `src/domain/entities.py` | PDF document、asset、section、manifest 等核心實體 |
| `src/domain/value_objects.py` | document id、bbox、asset refs 等 value objects |
| `src/domain/citation.py` | EvidenceSpan、AssetRef、citation locator/hash 模型 |
| `src/domain/table_entities.py` | A2T TableContext、ColumnDef、CellCitation、ChangeLog、Draft |
| `src/domain/docx_entities.py` | DocxIR、DfmBlock、run/table/cell/page/style metadata |
| `src/domain/docx_value_objects.py` | DFM block type 與 DOCX value objects |
| `src/domain/section_tree.py` | Section tree、path lookup、section search support |
| `src/domain/segmentation.py` | DocumentSegmentation / DocumentSegment |
| `src/domain/reading_order.py` | ReadingOrderPolicy |
| `src/domain/line_spans.py` | Markdown line span alignment |
| `src/domain/chunking.py` | Text chunking strategies |
| `src/domain/image_processor.py` | Image-related domain helpers |
| `src/domain/etl_profile.py` | Built-in/custom ETL profiles |
| `src/domain/job.py` | Background job entity/status |
| `src/domain/repositories.py` | Repository interfaces |
| `src/domain/services.py` | Domain service helpers |
| `src/domain/marker_errors.py` | Marker backend error classification |
| `src/domain/pdf_preflight.py` | Stable `pdf-preflight-v1` schema、page classification、OCR/engine routing、typed failures |

## Application

| 檔案 | 功能 |
|---|---|
| `src/application/document_service.py` | PDF ingest orchestration、OCR、Marker/PyMuPDF flow、LightRAG indexing |
| `src/application/asset_service.py` | Fetch table/figure/section/full_text assets |
| `src/application/segmentation_service.py` | manifest + blocks + assets -> segmentation |
| `src/application/citation_artifacts.py` | Citation status/index artifact handling |
| `src/application/citation_index_service.py` | Evidence span index build/rebuild |
| `src/application/docx_service.py` | DOCX/DFM ingest/save/conversion/validation orchestration |
| `src/application/dfm_integrity.py` | DFM integrity gates and repair checks |
| `src/application/dfm_table_bridge.py` | DOCX table/chart <-> A2T bridge |
| `src/application/table_service.py` | A2T table CRUD、citations、drafts、rendering |
| `src/application/section_service.py` | Section tree/detail/blocks/search/content services |
| `src/application/knowledge_service.py` | LightRAG query/export use cases |
| `src/application/job_service.py` | Background job lifecycle、quota、cancel、worker coordination；ingest 拒絕空清單與空白 path |
| `src/application/etl_profile_detector.py` | Heuristic ETL profile detection from file name, sample text, and layout hints |
| `src/application/ingest_worker.py` | Worker-side ingest execution |
| `src/application/worker_runner.py` | Worker runner port |
| `src/application/markdown_block_builder.py` | Marker MarkdownOutput fallback block synthesis |
| `src/application/output_paths.py` | Safe output path resolution |
| `src/application/pdf_preflight_service.py` | Non-blocking application facade over the isolated PDF inspector |
| `src/application/agent_asset_bundle_service.py` | Atomic deterministic `agent-asset-bundle-v1` export orchestration |
| `src/application/agent_asset_bundle_format.py` | Canonical JSON/hash、bundle manifest、Foam index/note serialization |
| `src/application/agent_asset_record_builder.py` | Segmentation + manifest + evidence -> text/table/figure agent asset records |

## Infrastructure

| 檔案 | 功能 |
|---|---|
| `src/infrastructure/file_storage.py` | Document/table artifacts persistence |
| `src/infrastructure/job_store.py` | Atomic persisted job store |
| `src/infrastructure/pdf_extractor.py` | PyMuPDF extraction；process-isolated worker 以 bounded 原子結果交接避開大型 payload pipe deadlock，且不改動 embedding process 的 signal timer |
| `src/infrastructure/pymupdf_preflight.py` | Process-isolated, bounded, read-only PDF page inspection and route recommendation |
| `src/infrastructure/pymupdf4llm_adapter.py` | Layout-aware base extraction；backend unavailable 時自動降級 PyMuPDF |
| `src/infrastructure/docling_adapter.py` | Active structured layout/table/formula/figure backend |
| `src/infrastructure/mineru_adapter.py` | MinerU adapter retained；package extra currently empty on security hold |
| `src/infrastructure/marker_adapter.py` | Marker adapter retained；package extra currently empty on Pillow security hold |
| `src/infrastructure/structured_extractor.py` | StructuredPDFExtractor shared protocol |
| `src/infrastructure/extractor_factory.py` | ETL engine selection、lazy backend preflight、PyMuPDF fallback |
| `src/infrastructure/docx_adapter.py` | DOCX XML parse/write, tables, revisions, charts, media |
| `src/infrastructure/dfm_parser.py` | DFM -> IR/parser |
| `src/infrastructure/dfm_renderer.py` | IR -> DFM/Markdown rendering |
| `src/infrastructure/docx_validator.py` | DOCX round-trip validation |
| `src/infrastructure/markdown_converter.py` | Markdown -> DOCX/PDF/DOC/ODT conversion |
| `src/infrastructure/excel_renderer.py` | Table rendering/export helpers |
| `src/infrastructure/layout_visualizer.py` | PDF layout overlay generation |
| `src/infrastructure/ocr_processor.py` | `ocrmypdf` wrapper |
| `src/infrastructure/lightrag_adapter.py` | LightRAG/Ollama/OpenAI backend |
| `src/infrastructure/subprocess_ingest_worker_runner.py` | Isolated worker process runner |
| `src/infrastructure/encoding_guard.py` | Fail-closed encoding/BOM/ZIP/input safety guard |
| `src/infrastructure/config.py` | Runtime configuration |

## Presentation

Presentation runtime requires official MCP Python SDK 2 (`mcp>=2,<3`). SDK v1
and `mcp.server.fastmcp` fallback are unsupported；balanced / compact / legacy
remain tool-surface UX policies on the same SDK 2 server。

| 檔案 | 功能 |
|---|---|
| `src/presentation/mcp_app.py` | `AssetAwareMCPServer(MCPServer)` singleton；tracks tools through public SDK registry APIs |
| `src/presentation/server.py` | MCP server entrypoint |
| `src/presentation/dependencies.py` | Composition root |
| `src/presentation/mcp_context.py` | SDK 2 runtime `Context` progress helper；deprecated protocol logging 改為 stderr Python logging |
| `src/presentation/markdown_utils.py` | Presentation markdown formatting helpers |
| `src/presentation/ingest_worker_main.py` | Isolated worker entrypoint |
| `src/presentation/tools/document_tools.py` | PDF/citation facades；含 read-only `preflight` 與 portable `export_assets`/`agent_assets` |
| `src/presentation/tools/{docx,job,knowledge,profile,section,table}_tools.py` | 其餘 facade/shortcut/direct tools；`citation_support.py` 與 `conversion_job_support.py` 為 shared helper |
| `src/presentation/tool_surface.py` | balanced / compact / legacy runtime policy；只用 MCPServer public `remove_tool` API |
| `src/presentation/resources/*.py` | 13 MCP resources |

## VS Code Extension

| 檔案 | 功能 |
|---|---|
| `vscode-extension/src/extension.ts` | Extension activation and command registration |
| `vscode-extension/src/mcpProvider.ts` | Native MCP provider |
| `vscode-extension/src/copilotMcpConfig.ts` | Copilot MCP config merge |
| `vscode-extension/src/clineMcpConfig.ts` | Cline MCP config merge |
| `vscode-extension/src/codexMcpConfig.ts` | Codex MCP config merge；managed 180s/900s timeout、secret-name-only `env_vars`、machine-scoped opt-out |
| `vscode-extension/src/mcpConfigCommon.ts` | Shared MCP config helpers |
| `vscode-extension/src/assistantAssets.ts` | Assistant harness sync |
| `vscode-extension/src/uv.ts` | uv discovery/runtime prep |
| `vscode-extension/src/ollama.ts` | Ollama diagnostics |
| `vscode-extension/src/envManager.ts` | Environment management、document artifact listing、citation span summaries |
| `vscode-extension/src/documentTreeProvider.ts` | Documents tree view with artifact/citation groups |
| `vscode-extension/src/tableTreeProvider.ts` | Tables tree view |
| `vscode-extension/src/statusTreeProvider.ts` | Runtime/status tree view |
| `vscode-extension/src/statusBar.ts` | Status bar |
| `vscode-extension/src/settingsPanel.ts` | Settings UI |
| `vscode-extension/src/dfm/*` | DFM editor language/features |

## Scripts

| 檔案 | 功能 |
|---|---|
| `scripts/count_tools.sh` / `.ps1` | MCP endpoint inventory |
| `scripts/build_docs_site.py` | GitHub Pages docs payload builder |
| `scripts/check_cline_skills.py` | Cline skill packaging/sync check |
| `scripts/get_version.py` | Single-source project version helper |
| `scripts/release.sh` | Local release orchestration |
| `scripts/audit_release_artifacts.py` | Wheel/sdist/VSIX artifact audit |
| `scripts/audit_release_harness.py` | Harness packaging audit |
| `scripts/install_cline_mcp.py` | Local Cline MCP installer |
| `scripts/dfm_cli.py` | DFM CLI |
| `scripts/roundtrip_test.py` | DOCX round-trip helper |
| `scripts/gh_update_issue_or_pr.sh` | GitHub issue/PR update helper |
| `scripts/gh_update_repo_metadata.sh` | GitHub metadata helper |

## Dependency Automation

| 檔案 | 功能 |
|---|---|
| `pyproject.toml` / `uv.lock` | Python 3.10-compatible universal dependency contract；MCP SDK 2 and security floors |
| `.github/dependabot.yml` | Weekly uv、npm、GitHub Actions update groups and PR limits |
| `.github/workflows/dependency-security.yml` | Read-only scheduled/PR gate：`uv lock --check`、pinned uv 0.12.3 universal audit、npm low-level lock audit |
| `.github/workflows/project-hygiene.yml` | Weekly website/docs/README/assistant-asset drift gates、managed-label sync，以及 optional token-gated repository metadata sync |
