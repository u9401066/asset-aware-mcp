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
| `src/application/job_service.py` | Background job lifecycle、quota、cancel、worker coordination |
| `src/application/ingest_worker.py` | Worker-side ingest execution |
| `src/application/worker_runner.py` | Worker runner port |
| `src/application/markdown_block_builder.py` | Marker MarkdownOutput fallback block synthesis |
| `src/application/output_paths.py` | Safe output path resolution |

## Infrastructure

| 檔案 | 功能 |
|---|---|
| `src/infrastructure/file_storage.py` | Document/table artifacts persistence |
| `src/infrastructure/job_store.py` | Atomic persisted job store |
| `src/infrastructure/pdf_extractor.py` | PyMuPDF extraction |
| `src/infrastructure/marker_adapter.py` | Marker backend adapter and conversion |
| `src/infrastructure/docx_adapter.py` | DOCX XML parse/write, tables, revisions, charts, media |
| `src/infrastructure/dfm_parser.py` | DFM -> IR/parser |
| `src/infrastructure/dfm_renderer.py` | IR -> DFM/Markdown rendering |
| `src/infrastructure/docx_validator.py` | DOCX round-trip validation |
| `src/infrastructure/markdown_converter.py` | Markdown -> DOCX/PDF/DOC conversion |
| `src/infrastructure/excel_renderer.py` | Table rendering/export helpers |
| `src/infrastructure/layout_visualizer.py` | PDF layout overlay generation |
| `src/infrastructure/ocr_processor.py` | `ocrmypdf` wrapper |
| `src/infrastructure/lightrag_adapter.py` | LightRAG/Ollama/OpenAI backend |
| `src/infrastructure/subprocess_ingest_worker_runner.py` | Isolated worker process runner |
| `src/infrastructure/config.py` | Runtime configuration |

## Presentation

| 檔案 | 功能 |
|---|---|
| `src/presentation/mcp_app.py` | FastMCP app instance |
| `src/presentation/server.py` | MCP server entrypoint |
| `src/presentation/dependencies.py` | Composition root |
| `src/presentation/mcp_context.py` | Progress/log helpers |
| `src/presentation/markdown_utils.py` | Presentation markdown formatting helpers |
| `src/presentation/ingest_worker_main.py` | Isolated worker entrypoint |
| `src/presentation/tools/*.py` | 59 MCP tools |
| `src/presentation/resources/*.py` | 13 MCP resources |

## VS Code Extension

| 檔案 | 功能 |
|---|---|
| `vscode-extension/src/extension.ts` | Extension activation and command registration |
| `vscode-extension/src/mcpProvider.ts` | Native MCP provider |
| `vscode-extension/src/copilotMcpConfig.ts` | Copilot MCP config merge |
| `vscode-extension/src/clineMcpConfig.ts` | Cline MCP config merge |
| `vscode-extension/src/codexMcpConfig.ts` | Codex MCP config merge |
| `vscode-extension/src/mcpConfigCommon.ts` | Shared MCP config helpers |
| `vscode-extension/src/assistantAssets.ts` | Assistant harness sync |
| `vscode-extension/src/uv.ts` | uv discovery/runtime prep |
| `vscode-extension/src/ollama.ts` | Ollama diagnostics |
| `vscode-extension/src/envManager.ts` | Environment management |
| `vscode-extension/src/documentTreeProvider.ts` | Documents tree view |
| `vscode-extension/src/tableTreeProvider.ts` | Tables tree view |
| `vscode-extension/src/statusTreeProvider.ts` | Runtime/status tree view |
| `vscode-extension/src/statusBar.ts` | Status bar |
| `vscode-extension/src/settingsPanel.ts` | Settings UI |
| `vscode-extension/src/dfm/*` | DFM editor language/features |

## Scripts

| 檔案 | 功能 |
|---|---|
| `scripts/count_tools.sh` / `.ps1` | MCP endpoint inventory |
| `scripts/release.sh` | Local release orchestration |
| `scripts/audit_release_artifacts.py` | Wheel/sdist/VSIX artifact audit |
| `scripts/audit_release_harness.py` | Harness packaging audit |
| `scripts/install_cline_mcp.py` | Local Cline MCP installer |
| `scripts/dfm_cli.py` | DFM CLI |
| `scripts/roundtrip_test.py` | DOCX round-trip helper |
| `scripts/gh_update_issue_or_pr.sh` | GitHub issue/PR update helper |
| `scripts/gh_update_repo_metadata.sh` | GitHub metadata helper |
