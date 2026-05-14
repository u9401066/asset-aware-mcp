# Active Context

## 2026-05-14 - v0.6.32 repo health and release prep

- Release scope is `v0.6.32` on `master`, following the `v0.6.31` tag. The work focuses on production-readiness before push/tag: oversized source/test modules were split, stale VSIX-installed harness leftovers and orphan/generated files were cleaned, and the release smoke gates were expanded around built wheels, stdio MCP startup, Docker, VSIX install/update, and release artifact audits.
- All tracked source/test files over 2000 lines were refactored into smaller modules while preserving public MCP tools and monkeypatch/import compatibility: document tools gained `document_evidence_support.py`, `DocumentService` gained markdown/page-scope helpers, `DocxAdapter` gained OpenXML/writeback helpers, and the old MCP tool-layer test monolith was split into focused test modules.
- KG/Foam behavior remains a first-class release surface: `citation_bundle(output_format="foam")`, `document_asset(op="foam_notes")`, `evidence(op="health")`, and claim-promotion workflows are covered by focused tests and practical smoke coverage so wiki links, anchors, embedded AssetRefs, and verification payloads stay auditable.
- Local RAG defaults changed for the release candidate: Ollama LLM now defaults to `granite4.1`, while LightRAG/KG is opt-in (`ENABLE_LIGHTRAG=false`) so CPU-only or document-only installs do not require KG dependencies or embedding models.
- Assistant harness assets are Asset-Aware-scoped again after removing retired Zotero/PubMed/academic-figure leftovers from the bundled source and VSIX repo-assets. `npm run sync-assets` must stay clean before packaging the VSIX.
- Fresh non-Docker release verification passed after the Granite/KG default change: Ruff, format, MyPy, `uv lock --check`, docs-site check, release harness audit, VSIX asset sync check, full pytest (`887 passed, 22 skipped`), VSIX `test:ci` (`125 passing` plus package contents), Python/VSIX packaging, release artifact audit, built-wheel runtime/stdout MCP smoke, and VSIX install/update smoke. Docker build was explicitly stopped by the user because it hangs in this environment and is waived for this local release run.

## 2026-05-11 - v0.6.29 DFM/citation-ready release prep

- Multi-subagent review confirmed DFM is correct for the supported mainline: DOCX/DOC ingest, DocxIR/DFM/split Markdown+YAML, no-op/text/existing-table-cell edits, `save_docx`, strict validation, and layout smoke. The boundary remains explicit: arbitrary Word structural edits and legacy `.doc` source-conversion layout drift are not claimed as fully solved.
- Multi-subagent review confirmed citation-ready is usable as a core loop: PDF span -> AssetRef -> verification -> bundle/Foam -> health check -> claim promotion. The strongest remaining product direction is making Foam/wiki promotion more durable and reviewable.
- Release scope moved to `0.6.29` because `v0.6.28` is already tagged. Version files, README/VSIX README, changelog, wiki source, GitHub Pages payload, and Memory Bank are aligned to `0.6.29`.
- Citation-ready was strengthened once more before release: Foam claim promotion notes now keep the original AssetRef JSON and an explicit Verification Payload JSON fence, so wiki-layer promotion can preserve full verification evidence while still failing closed before writes.
- Release harness audit is now clean after restoring local skip-worktree LLM wiki harness files to the tracked Asset-Aware-scoped wording and moving untracked retired Zotero/PubMed harness leftovers to `/tmp/asset-aware-retired-harness-backup-20260511T164609Z`.
- Release gates passed for the `0.6.29` candidate: Ruff, format, MyPy, `uv lock --check`, full pytest (`840 passed, 21 skipped`), docs site check, JS syntax, release harness audit, tool count, VSIX sync-assets, VSIX `test:ci` (`119 passing` plus package contents), VSIX install/update smoke, `uv build`, VSIX package, artifact audit, Docker build/import smoke, and `git diff --check`.
- Docker smoke required one compatibility fix: the production Dockerfile no longer depends on BuildKit cache mounts, so hosts without `docker buildx` can complete the release build.

## 2026-05-11 - Real IRB folder DOCX/PDF round-trip smoke

- Ran a real Asset-Aware smoke over `/home/eric/workspace251226/asset-aware-mcp/一般案-新案2025.00 (20250520)_20260128R` with 26 files: 18 DOCX, 5 legacy DOC, and 3 PDF. Original source hashes/mtimes were preserved; all generated artifacts live under `tmp/asset_aware_real_roundtrip_20260511T144132Z`.
- Initial result: 16/23 Word-like files passed strict validator + LibreOffice PDF raster layout checks; 2 failed save guards, 2 failed strict validator, 3 had validator-pass layout diffs, and 1 PDF content DOCX conversion failed despite complete ETL artifacts.
- Fixed the reproduced root causes: Markdown table blank rows are no longer mistaken for separator rows, split-format break blocks are protected/non-editable, terminal line-break normalization no longer creates false expected edits, break-only runs no longer receive duplicate `\n` text, and PDF->DOCX image embedding re-encodes python-docx-unrecognized JPEG headers through PNG.
- Targeted fix verification over the previously failing real files passed: `02`, `06-3`, `12`, `17`, and `18` all reached strict 100.0 with layout max mean diff `0.0`; `※審查費繳費單下載相關公告...pdf` now converts to content DOCX with one embedded figure. Fix-check artifacts live under `tmp/asset_aware_real_roundtrip_fixcheck_20260511T150045Z`.
- Full after-fix real-folder run over all 26 files passed source-integrity checks (`changed_count=0`): 18 DOCX reached strict 100.0 and layout diff `0.0`, all 5 legacy DOC files reached strict 100.0, and the two remaining layout warnings are isolated to `.doc` source-to-LibreOffice conversion baseline drift while converted-DOCX-to-IR rebuild diff is `0.0`. All 3 PDFs passed artifact/citation checks with citation lines carrying locator/hash/context/offset fields.
- Citation-ready provenance was strengthened so PDF manifests now persist root-level `source_pdf_sha256` plus `selected_page_map`, separating the original PDF byte identity from markdown/citation locator hashes.
- Foam/LLM wiki promotion support now lives on the existing evidence bundle path: `citation_bundle(output_format="foam", citation_key="...")` emits a Foam-compatible evidence pack with YAML frontmatter, `^spn-...` anchors, wikilink/embed strings, verification status, locator hashes, and embedded AssetRef JSON. `evidence(op="bundle", output_format="foam", citation_key="...")` routes to the same exporter.
- Foam promotion moved from export-only to wiki-maintenance capable: `citation_bundle(..., wiki_root=..., output_path=..., index_path=...)` writes the evidence pack under the Foam root and updates a managed evidence index block; `evidence(op="health", wiki_root=...)` scans Markdown notes for embedded span AssetRefs and `[[note#^spn-...]]` links, then reports stale/mismatched refs and missing target notes/anchors.
- Table/Figure Foam notes now hang off `document_asset(op="foam_notes", ...)`: manifest table/figure assets become `table_evidence` / `figure_evidence` notes with source block/order, line span, section context, source PDF hash, asset locator hash, and embedded table/figure AssetRef JSON. Foam health now validates span/table/figure refs and generic `[[note#^...]]` anchors.
- DOCX DFM blocks now carry Word-origin locator metadata in `DfmBlock.metadata`: `locator_version=docx-dfm-locator-v1`, `source_part`, `source_story`, `source_element`, paragraph/table/source indexes, run ranges, text char/byte/hash locator, and table cell locators; `get_docx_content(block_id=...)`, `list_docx_blocks`, split `format.yaml`, and Track Changes `revisions.jsonl` expose the locator so Word forms can be promoted/audited closer to PDF spans.
- Claim promotion workflow is now available through `evidence(op="claim_promotion" | "claims" | "promote_claims", ...)`: it proposes exact-quote claim candidates with embedded AssetRefs and Foam anchors, and Foam writes are blocked unless every candidate verifies against the current citation index.
- Regression validation is tracked through the split MCP tool-layer modules (`tests/unit/test_mcp_docx_tools.py`, `tests/unit/test_mcp_job_tools.py`, `tests/unit/test_mcp_document_tools.py`, `tests/unit/test_mcp_table_tools.py`, `tests/unit/test_mcp_profile_tools.py`, `tests/unit/test_mcp_knowledge_tools.py`, `tests/unit/test_mcp_server_startup.py`, `tests/unit/test_job_service_concurrency.py`, and `tests/unit/test_pdf_validation.py`) plus focused DOCX/citation/docs gates.

## 2026-05-11 - v0.6.28 feature release prep

- Preparing `v0.6.28` from `master` after adding six requested capability refinements: conversion background jobs, verified citation bundle export, KG answers with verified evidence, DOCX table structural edit plans, ETL profile auto-detect, and a VSIX artifact/citation viewer.
- Current endpoint inventory is 62 tools in 7 modules and 13 resources in 2 modules, 75 MCP endpoints total.
- Focused validation has passed for the new Python tools and services, MCP tool registration/counts, VSIX EnvManager and DocumentTreeProvider behavior, TypeScript compile/lint/unit slices, Ruff checks, and formatting on changed Python files.
- Docs/site/MEM are aligned to `0.6.28`, refreshed wiki assets are regenerated, and local release gates pass for Python, docs, VSIX unit/package, build artifacts, and release audits.
- Remaining environment caveats before publication are host-level only: VSIX install smoke is blocked by missing `libgbm.so.1` when using downloaded VS Code and by a hanging remote `code-insiders` CLI, while Docker smoke is blocked by missing Docker buildx/BuildKit support.

## 2026-05-11 - Git harness hygiene and wiki documentation setup

- Follow-up multi-subagent documentation alignment completed after the human-facing docs site was reviewed against the actual code. Corrections were made for MCP tool/resource contracts, `knowledge-graph://summary`, PDF artifact names (`{doc_id}_full.md`, `{doc_id}_manifest.json`, `citation_index.jsonl`), background-job/conversion boundaries, DOCX/DFM supported formats and safe-write limits, A2T `resume`, ETL profile activation semantics, Knowledge Graph response modes/timeouts, VSIX runtime cache behavior, assistant asset sync scope, and Code Map coverage.
- Added `tests/unit/test_docs_site_reference_sync.py` so `docs/wiki/MCP-Tools.md` and `docs/wiki/MCP-Resources.md` are checked against the actual `@mcp.tool()` / `@mcp.resource()` decorators, including resource URI strings and Start Here navigation order.
- Regenerated `docs/site-content.js` and `docs/site-content/*.md` from `docs/wiki/**`; validation passed for docs builder `--check`, JS syntax, linked wiki images, stale-string scan, ruff on changed Python files, `git diff --check`, `./scripts/count_tools.sh`, and focused docs/count tests.
- Main worktree was fast-forwarded from the stale local checkout to `origin/master` / `v0.6.27`; four older VSIX-installed LLM wiki harness files were moved to `/tmp/asset-aware-harness-backup-20260511091421` before the fast-forward because the same paths are now tracked upstream.
- VSIX-managed assistant harness source paths were marked local-only with `git update-index --skip-worktree` to keep automatic extension sync from dirtying normal feature work: `AGENTS.md`, `.github/copilot-instructions.md`, `.github/agents`, `.github/bylaws`, `.claude/skills`, `.cline/skills`, `.codex/skills`, and `.clinerules`.
- `scripts/count_tools.sh` and `scripts/count_tools.ps1` were fixed to skip helper modules with zero MCP endpoints; focused regression coverage now lives in `tests/unit/test_count_tools_script.py`.
- Endpoint inventory from the repaired script was 59 tools in 7 modules and 13 resources in 2 modules, 72 MCP endpoints total before the later `0.6.28` feature additions.
- A full GitHub Wiki page set was authored in `/tmp/asset-aware-mcp.wiki` and mirrored into `docs/wiki/` for versioned source control. The page set includes Home, sidebar, architecture, all MCP tools/resources, PDF/DOCX/A2T/KG/jobs/profiles workflows, VSIX setup, Git harness hygiene, developer/release guide, and code map.
- Existing docs diagrams were reviewed as source material, but several embedded stale counts/versions such as `48 tools` made them unsafe for the current wiki. A new web-sized diagram batch was generated with Pillow under `docs/wiki/assets/`, covering architecture, endpoint map, PDF, DOCX/DFM, citation provenance, A2T, knowledge graph, jobs, ETL profiles, VSIX setup, and Git harness hygiene.
- After the GitHub Wiki was initialized, `/tmp/asset-aware-mcp.wiki` was merged with the remote initial page using `--allow-unrelated-histories` and pushed to `asset-aware-mcp.wiki.git`; remote `master` now points at `d6b3a17`.
- GitHub Wiki verification passed: the root wiki URL returns HTTP 200, `_pages` lists the generated pages, representative pages such as `MCP-Tools`, `PDF-Document-Workflow`, `DOCX-DFM-Workflow`, `VS-Code-Extension-And-MCP-Setup`, `Git-Harness-Hygiene`, and `Code-Map` return HTTP 200, and the raw `overview-architecture.jpg` asset returns HTTP 200 as `image/jpeg`.
- A PubMed-style GitHub Pages documentation site now lives under `docs/` and is published from `master` `/docs` at `https://u9401066.github.io/asset-aware-mcp/#/overview-zh`. The site uses `docs/index.html`, `docs/site.css`, `docs/site.js`, generated `docs/site-content.js`, and generated `docs/site-content/*.md`; `scripts/build_docs_site.py --check` is wired into CI docs-check to keep the site payload aligned with `docs/wiki/**`.
- The docs site was refined for human readers: Home now starts with task-oriented path cards, `Design-And-UX.md` documents audience, information architecture, page rhythm, UI choices, visual direction, and completeness criteria, and the CSS palette was adjusted away from the earlier single warm/green note. Main repo `master` contains `27aca29`; GitHub Wiki `master` contains `404b640`.

## 2026-05-08 - v0.6.27 security and release hygiene patch

- Preparing `v0.6.27` from a clean worktree on top of `v0.6.26` after prerelease audit found runtime dependency CVEs, Marker/Pillow resolver conflict, table citation provenance drift, and VSIX package guard gaps.
- Default runtime dependency floors now require patched image/XML/network/auth packages, including `Pillow>=12.2.0` and `lxml>=6.1.0`.
- Marker extras are intentionally empty in this release because upstream `marker-pdf` 1.10.2 pins `Pillow<11`; the VSIX/local launcher now logs a Marker security hold and does not install `marker-pdf` even if `assetAwareMcp.enableMarkerBackend` is set.
- Table citation AssetRefs now preserve `locator_source_sha256` through serialization/reload, with regression coverage for evidence-span conversion and table persistence.
- VSIX release hygiene now blocks root `dist/`/`tmp/`, generated nested repo-assets, and generated assistant asset directories during sync. Install smoke can be forced to VS Code Insiders with `ASSET_AWARE_MCP_VSCODE_QUALITY=insiders`.
- Main worktree remains intentionally dirty with unrelated LLM-wiki/harness/agent/test artifacts; release staging must happen only from the isolated `asset-aware-mcp-v0.6.27-fix` worktree with exact pathspecs.

## 2026-05-08 - v0.6.26 MCP stdio ingest hotfix

- Preparing `v0.6.26` as a patch on top of the already-pushed `v0.6.25` tag after a Codex-style stdio MCP smoke found that `ingest_documents(async_mode=False, use_marker=False)` could still block on Windows PyMuPDF document-level extractor timeouts.
- The MCP presentation layer now treats `async_mode=False` for PDF ingest as backwards-compatible input only; all PDF ingest requests return a background job so Cline/Codex/VS Code stdio clients stay responsive.
- Regression coverage now asserts that sync MCP PDF ingest creates a job, preserves job parameters, skips page-count probes, and never calls inline `document_service.ingest()`.
- Validation includes focused MCP tool tests, ruff, format, mypy, and a Codex-style stdio MCP client smoke covering initialize, tools/list, `ingest_documents`, `parse_pdf_structure`, `ocr_pdf_document`, disabled knowledge graph responses, and job cancellation.
- Main worktree full pytest is intentionally polluted by unrelated LLM-wiki/retired harness files; release verification must run from a clean worktree or exact staged scope so those harness drafts are not mixed into the hotfix.

## 2026-05-08 - v0.6.25 stability release prep

- Preparing `v0.6.25` as a scoped stability release after the Cline timeout and VSIX activation fixes were validated locally.
- MCP request responsiveness is the release focus: `parse_pdf_structure` and `ocr_pdf_document` now always return background jobs, synchronous ingest fails closed to a background job when LightRAG indexing would block, and knowledge graph query/export tools have request-level timeout guards.
- Isolated ingest worker behavior is hardened with presentation-owned worker entrypoint composition, application-layer worker helpers only, per-file logs, traceback capture, heartbeat/progress updates, and visible failed-job warnings.
- Citation-ready Marker fallback is improved with markdown block synthesis, citation status files, and helper modules split out of `document_service.py` and `document_tools.py`.
- The DDD boundary is improved by introducing an `IngestWorkerRunner` application port and a subprocess infrastructure adapter, keeping subprocess/env/log runner details out of `JobService`.
- DOCX/table safety is included in this release: strict validation now covers header/footer/footnote story parts and table-cell direct formatting, while table persistence is atomic.
- VSIX smoke coverage now verifies installed-extension activation and MCP provider definition, with runtime preparation using extension-storage `UV_CACHE_DIR` and avoiding `ELECTRON_RUN_AS_NODE=1` leakage into Code.exe.
- Git hygiene goal for this release: use segmented commits and exact pathspecs, leave ad-hoc `.github/agents`, `.pytest-tmp`, `.vscode-test`, PDFs, and unrelated LLM wiki harness sync files out of the release unless explicitly staged later.

## 2026-05-07 - v0.6.24 Cline worker isolation release prep

- Preparing `v0.6.24` after 4 subagents completed 3 review rounds over the Cline failure path, job lifecycle, document ingestion, and release pipeline.
- Marker-backed background jobs now use `src.application.ingest_worker` in an isolated subprocess with stdin/stdout/stderr closed, so Cline can keep calling `get_job_status` and `cancel_job` while Marker parses.
- `parse_pdf_structure(async_mode=True)` now carries `require_marker=True` and fails closed without writing PyMuPDF fallback artifacts when Marker structure is required.
- Job results now include per-document backend, warnings, artifacts, degraded state, and next-step commands; Cline no longer has to infer whether a Marker job actually degraded to PyMuPDF.
- Job cancellation, stale active job reconciliation, and ETL profile isolation were hardened with regression tests.
- Local Cline install now preserves cross-workspace `DATA_DIR` unless `--force-workspace` is explicit.
- Release workflow now guards PyPI reruns, VS Code Marketplace retry/visibility, wheel/sdist required runtime files, VSIX bundled `count_tools.ps1`, and precise release staging without `git add -A`.
- Verification so far: `ruff`, full `uv run pytest -q` (`781 passed, 19 skipped`), VSIX `npm run test:ci`, sync-assets check, release harness audit, `uv build`, artifact audit, `count_tools.ps1`, and `git diff --check` all passed.

## 2026-05-07 - v0.6.23 Cline / Marker corrective release

- Preparing `v0.6.23` as the second Cline corrective patch after multi-agent review found that Marker model loading and synchronous PDF parsing could still exceed Cline request budgets.
- Marker-backed `parse_pdf_structure` and `ingest_documents` now default to background jobs, with explicit synchronous diagnostics guarded by page/file-size checks.
- Generated Cline and VS Code MCP launch environments suppress noisy Marker stdout/stderr and preserve diagnostics in a workspace `logs/marker.log` file.
- Background job creation/cancellation/store writes are hardened against quota races, orphan tasks, unsafe IDs, and partial JSON writes.
- LightRAG/Ollama integration now validates the expected `lightrag-hku` distribution, uses batch Ollama embeddings with legacy fallback, and exposes timeout knobs.
- `save_docx` now surfaces skipped pending TableContext merge warnings; segmentation fallback warnings are visible in MCP output.
- Release gates for this patch must cover full Python checks, Cline skill audit, release harness audit, sync-assets, VSIX `test:ci`, install smoke, Docker smoke, artifact audit, git push, and `v0.6.23` tag publication.

> 📌 當前工作焦點和進行中的變更

## Current Goals

- Complete the `0.6.29` DFM/citation-ready release with docs/wiki/site/MEM alignment, full local gates, exact-path segmented commits, push, GitHub Pages verification, and annotated tag publication while leaving real test data and generated artifacts uncommitted.

## 🎯 當前焦點

- **版本真相為 0.6.29**：本次 release 是 `v0.6.28` 之後的 DFM real-corpus / citation-ready Foam promotion patch，不重用既有 tag。
- **DFM 主線結論**：支援範圍內可正確進行 DFM 拆解與重組；文件與 release notes 必須保留 `.doc` conversion drift、結構性表格變更、header/footer/footnote locator 測試深度等邊界。
- **Citation-ready 主線結論**：EvidenceSpan / AssetRef / verify / bundle / Foam / health / claim promotion 已可用；CRAAP 仍是保守 scaffold，不可宣稱已完成 source quality 評分。
- **Git policy**：只 stage tracked source/docs/test/version changes；`tmp/`、真實 IRB source folder、`dist/`、VSIX artifact、runtime cache、ignored data 皆不可提交。
- **Release blockers**：若 VSIX install smoke 或 Docker smoke 因 host-level dependency 失敗，必須記錄為環境阻塞；不把 generated artifacts 或 real corpus outputs 混入 release。

## 🆕 ETL / Layout / OCR 可視化 (2026-03-18)

- `src/domain/segmentation.py`：新增 `DocumentSegment` / `DocumentSegmentation`
- `src/application/segmentation_service.py`：整合 manifest + blocks + assets + reading order，輸出 `segmentation.json`
- `segmentation.json` 現在同時保留 `reading_order` 與 `line_start` / `line_end`，可用於內容流理解與精準行號引用
- `src/domain/line_spans.py`：新增 page-aware / section-aware line span index，對重複句子會先在 page 與 section 範圍內定位
- `blocks.json` 現在會持久化 `line_start` / `line_end` / `line_match_strategy` 等 metadata；舊資料在 export segmentation 時會自動 backfill
- `fetch_document_asset` 現在直接回傳 asset 的 line range、section、source block，減少 agent 端額外查詢成本
- `FigureAsset` / `TableAsset` 追加 `source_block_id` / `source_order`，segmentation 會優先按來源 block 身分配對，避免同頁多資產錯配
- `src/infrastructure/layout_visualizer.py`：以 `original.pdf` 或白底畫布渲染 bbox overlay
- `src/infrastructure/ocr_processor.py`：封裝 `ocrmypdf`，支援 `language` / `rotate_pages` / `deskew`
- `DocumentService`：每次 ingest 會覆蓋保存最新 `original.pdf`，可選 OCR 後再進 ETL；`JobService` step 數跟隨 OCR 階段
- `document_tools.py`：新增 `export_document_segmentation`、`visualize_document_layout`、`ocr_pdf_document`
- `document_resources.py`：新增 `document://{doc_id}/segmentation`
- `vscode-extension`：Documents tree 相容新 manifest 結構，並顯示 segmentation 與 ETL jobs 概況
- 驗證結果：`uv run pytest tests/unit -q` → 384 passed；`npm run compile` 通過

## 🆕 Reading Order 與行號並存 (2026-03-18)

- `src/domain/reading_order.py`：新增顯式 `ReadingOrderPolicy`
- policy 不取代 line-level citation；`DocumentSegment` 另存 `line_start` / `line_end`
- 排序依據分離為兩軸：
    - `reading_order`：回答「內容應該怎麼讀」
    - `line_start/end`：回答「這段資訊在 markdown 第幾行」
- Marker block metadata 會保存 `source_order`，segmentation 匯出時再套用 type/caption/non-text policy
- 驗證結果：`uv run pytest tests/unit -q` → 379 passed

## 🆕 MCP Progress / Logging (2026-03-18)

- `src/presentation/mcp_context.py`：封裝安全 progress/log helper
- `DocumentService.ingest()`：新增可選 progress callback，提供每個檔案內部 phase 訊號
- `JobService`：改接真實 ingest phase，不再手動模擬 job 階段
- 已接入 progress 的工具：
    - PDF：`ingest_documents`、`parse_pdf_structure`、`convert_pdf_to_docx`
    - DOCX：`ingest_docx`、`save_docx`、`convert_docx_to_doc`、`convert_docx_to_pdf`、`docx_validate_roundtrip`、`export_markdown`
- 驗證結果：`uv run pytest tests/unit -q` → 368 passed

## 🆕 v0.4.0 新功能

### 文件級 CRUD 與互轉 (2026-03-09)
- `delete_document` / `delete_docx` / `list_docx_documents`
- `convert_docx_to_pdf` / `convert_docx_to_doc` / `convert_pdf_to_docx`
- `scripts/dfm_cli.py` 新增 `to-pdf`、`to-doc`、`validate --strict`

### 保真與安全強化 (2026-03-09)
- `DocxValidator.validate(..., strict=True)` fail-closed 驗證
- `DocxService.save_docx()` 新增 unedited block mutation guard
- Proposal 真實文件通過 DOCX→DFM→DOCX、DOCX→PDF、DOCX→DOC 實戰驗證

## 🛡️ v0.3.3 新功能

### 生產強化 (2026-02-22)
- Dockerfile multi-stage build
- PDF magic byte 驗證
- 並行 Job 上限 MAX_CONCURRENT_JOBS=5
- Structured logging
- 37 個新 MCP 工具層測試

### .doc 格式支援 (2026-02-23)
- `ingest_docx` 自動偵測 `.doc` 格式，透過 LibreOffice 轉換為 `.docx`
- `_convert_doc_to_docx()` — LibreOffice headless 模式轉換

### Markdown 跳脫修復 (2026-02-23)
- `_escape_md()` / `_unescape_md()` — 跳脫 `*`, `~`, `^` 防止文字被誤判為格式標記
- Run 合併優化 — 相鄰相同格式的 runs 先合併再產生 Markdown
- Caption 偵測修正 — 排除 `**...**` bold 模式的誤判
- CLI import path 修正 — `src.application.docx_validator` → `src.infrastructure.docx_validator`

## Docx DFM 系統概要 (v0.3.0)

### 12 個 Docx MCP 工具
| Tool | 類別 | 功能 |
|------|------|------|
| `ingest_docx` | Core | 匯入 .docx → DocxIR → DFM |
| `get_docx_content` | Core | 讀取指定區塊 DFM 內容 |
| `save_docx` | Core | DFM 編輯寫回 .docx |
| `list_docx_blocks` | Core | 列出文件區塊結構 |
| `list_docx_documents` | Core | 列出所有已攝入 DOCX/DFM 文件 |
| `delete_docx` | Core | 刪除已攝入 DOCX/DFM 與本地 artifacts |
| `convert_docx_to_pdf` | Core | 以保真模式輸出 PDF |
| `convert_docx_to_doc` | Core | 以保真模式輸出 DOC |
| `docx_validate_roundtrip` | Validator | 6 維度往返保真驗證 + strict fail-closed |
| `docx_table_to_context` | Bridge | Docx 表格 → A2T 上下文 |
| `docx_table_from_context` | Bridge | A2T 表格 → Docx 表格 |
| `docx_chart_data` | Bridge | 提取 Docx 圖表數據 |

### DocxValidator 6 維度
- 結構 (Structure) / 文字 (Text) / 格式 (Formatting) / 表格 (Table) / 媒體 (Media) / 樣式 (Style)
- 加權評分：text=0.35, structure/format/table=0.15, media/style=0.10
- Emoji 等級：🟢 ≥95% / 🟡 ≥80% / 🟠 ≥60% / 🔴 <60%

## 📁 專案結構

```
src/
├── domain/          # 🔵 核心業務邏輯 (+docx_entities, docx_value_objects)
├── application/     # 🟢 使用案例 (+docx_service, dfm_table_bridge)
├── infrastructure/  # 🟠 外部依賴實作 (+docx_adapter, dfm_parser, dfm_renderer, docx_validator)
└── presentation/    # 🔴 MCP Server (62 tools in 7 modules, 13 resources)
    ├── tools/
    │   ├── document_tools.py   # ETL + document management (11)
    │   ├── docx_tools.py       # Docx DFM + conversion (16) — core + validator + bridge
    │   ├── section_tools.py    # Navigation (5)
    │   ├── job_tools.py        # Job (4)
    │   ├── knowledge_tools.py  # KG (3)
    │   ├── profile_tools.py    # Profile (6)
    │   └── table_tools.py      # A2T (7) — operation-based
    └── resources/              # 13 resources
```

## 📝 新功能 (v0.3.1)

### 分離格式 (Split Format)
- `content.md` — 乾淨 Markdown，`<!-- @ID -->` 標記（預覽不可見），減少 78% 雜訊
- `format.yaml` — 所有格式元資料（runs, cell_formats, merged_cells…）
- `content.dfm` — 原格式保留（MCP 工具用）

### DFM CLI 工具
- `scripts/dfm_cli.py` — 互動式選單（匯入/開啟/存檔/驗證/列表/一鍵流程）
- `.vscode/tasks.json` — 6 個 VS Code Tasks

### Bug 修復
- `docx_adapter._update_table_text()` — 在更新第一個 run 後清除後續 runs，修復表格文字重複

## ⚗️ 待解決

1. **測試覆蓋率**: 目標 60%+
2. **文件缺乏**: API Reference, Examples, FAQ

---
*Last updated: 2026-04-24*
