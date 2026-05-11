# Progress (Updated: 2026-05-11)

## 2026-05-11

- Fast-forwarded the main worktree to `origin/master` / `v0.6.27` after moving older VSIX-installed LLM wiki harness files to `/tmp/asset-aware-harness-backup-20260511091421` so upstream tracked files could land cleanly.
- Marked VSIX-managed assistant harness paths as local `skip-worktree` to keep extension auto-sync noise out of normal Git status while preserving the tracked source assets for release packaging.
- Fixed `scripts/count_tools.sh` and `scripts/count_tools.ps1` so helper modules with zero endpoints no longer break counts or inflate module totals.
- Added `tests/unit/test_count_tools_script.py`; focused validation passed with `2 passed`, and `./scripts/count_tools.sh` now reports 59 tools, 13 resources, 72 total MCP endpoints.
- Built a complete GitHub Wiki page set covering architecture, all tools/resources, workflows, VSIX setup, Git harness hygiene, developer guide, release checks, and code map. The same pages are mirrored under `docs/wiki/` as versioned wiki source.
- Generated 11 current web-sized JPG diagrams under `docs/wiki/assets/` with updated `v0.6.27`, 59-tool, and 13-resource labeling, then embedded them in the matching wiki pages.
- Merged the newly initialized GitHub Wiki remote initial page into `/tmp/asset-aware-mcp.wiki`, kept the generated full wiki content, and pushed `master` to `asset-aware-mcp.wiki.git`; remote head is `d6b3a17`.
- Verified the published Wiki: root wiki URL, `_pages`, representative content pages, raw `Home.md`, and raw `assets/overview-architecture.jpg` all returned HTTP 200, and the rendered Home page contains the expected `Asset-Aware MCP Wiki`, `59 tools`, and architecture diagram references.

## 2026-05-08

- Preparing `v0.6.27` as a security and release-hygiene patch after multi-agent prerelease checks found runtime dependency CVEs, the `marker-pdf`/Pillow resolver conflict, table citation locator-source drift, and VSIX package guard gaps.
- Raised secure runtime floors and put Marker extras on security hold because upstream `marker-pdf` 1.10.2 still pins `Pillow<11`; VSIX/local launch now logs the hold and avoids `--extra marker` / `--with marker-pdf`.
- Preserved `locator_source_sha256` through `AssetRef` serialization and table citation reload, with focused regression coverage for evidence-span conversion and table persistence.
- Hardened VSIX packaging and assistant asset sync against root `dist`/`tmp` and nested generated repo-assets, and added an Insiders selector for install smoke.
- Preparing `v0.6.26` hotfix after a Codex-style MCP stdio smoke reproduced an 80-second sync PyMuPDF ingest request for a tiny PDF on Windows.
- Fixed MCP PDF ingest so `ingest_documents(async_mode=False)` also returns a background job, preserving request responsiveness and leaving actual PyMuPDF work to the isolated worker path.
- Added regression coverage that sync MCP PDF ingest creates a job, preserves job parameters, skips page-count probes, and never calls inline document ingestion.
- Verified the repaired stdio path with a Codex-style MCP client smoke: `ingest_documents(async_mode=False)` returned in 0.047s, `parse_pdf_structure` in 0.032s, `ocr_pdf_document` in 0.031s, knowledge graph disabled responses stayed bounded, and all created jobs were cancellable.
- The dirty main worktree still contains unrelated LLM-wiki/retired harness files that make full pytest fail in harness-boundary tests; they remain intentionally outside the hotfix scope.
- Preparing `v0.6.25` as a scoped stability release for Cline responsiveness, isolated ingest worker durability, citation-ready Marker fallback artifacts, DOCX/table safety, and VSIX activation/runtime hardening.
- Fixed blocking MCP paths by routing `parse_pdf_structure` and `ocr_pdf_document` through background jobs, failing synchronous LightRAG indexing closed to a background job, and adding request-level timeout guards to knowledge graph query/export tools.
- Split citation and worker support into smaller modules: `markdown_block_builder`, `citation_artifacts`, `citation_index_service`, `citation_support`, `worker_runner`, `subprocess_ingest_worker_runner`, and `presentation/ingest_worker_main`.
- Hardened failed ingest visibility with traceback capture, per-file logs, heartbeat/progress percentage updates, and failed job warnings.
- Added strict DOCX validation for header/footer/footnote story parts and table-cell formatting, plus atomic TableService JSON/Markdown persistence.
- Hardened VSIX installed activation smoke and runtime preparation with provider-definition verification, extension-storage `UV_CACHE_DIR`, and `ELECTRON_RUN_AS_NODE` cleanup before launching Code.exe.
- Release handling is intentionally segmented: Python reliability, DOCX/table safety, VSIX runtime, and release metadata will be staged with exact pathspecs while unrelated assistant harness drafts and test artifacts remain uncommitted.

## 2026-05-07

- Preparing `v0.6.23` corrective release after multi-agent review of `docs/code-review-todo-20260507.md` confirmed Cline still needed Marker work forced out of synchronous MCP request paths.
- Fixed Marker-backed PDF parsing and ingest to default to background jobs, with guarded synchronous diagnostics, visible segmentation fallback warnings, and Marker output suppression/log routing in generated Cline/VS Code environments.
- Hardened background jobs with quota locking, atomic job store writes, unsafe job ID rejection, awaited cancellation cleanup, and background Marker preflight.
- Hardened LightRAG/Ollama integration with `lightrag-hku` distribution validation, batch `/api/embed` embeddings, legacy fallback, and configurable timeouts.
- Surfaced skipped pending TableContext merge warnings from `save_docx` so DOCX saves no longer hide failed pending A2T sync.
- Added regression coverage for Cline-safe async Marker defaults, forced background thresholds, job durability, LightRAG/Ollama behavior, Marker suppression, Cline env generation, and DOCX warning visibility.
- Preparing `v0.6.22` corrective release for Cline MCP usability after live Cline settings still pointed at stale `asset-aware-mcp==0.6.17` and old workspace data.
- Fixed local Cline installer coverage for VS Code Insiders settings, workspace-local `DATA_DIR`, non-destructive managed-entry detection, and preservation of `alwaysAllow`, `disabled`, custom env, and unrelated MCP servers.
- Hardened VS Code extension Cline config merge with fail-closed schema validation for malformed top-level and nested server metadata.
- Removed ignored retired Zotero/PubMed harness leftovers from the workspace and expanded release audit coverage across `.github`, `.claude`, `.cline`, `.codex`, `.clinerules`, and `scripts/hooks`.
- Restored LLM wiki harness scope to Asset-Aware document evidence and added an audit guard against drifting back to bundled Zotero/PubMed workflow ownership.
- Updated bundled Cline release workflows to use PowerShell-safe command forms and synchronized repo-assets.
- Added regression coverage for Cline installer boundaries, Cline harness asset boundaries, schema validation, readable Traditional Chinese triggers, and assistant asset preservation behavior.
- Local release gates passed for `v0.6.22`: Python ruff/format/mypy/full pytest (`719 passed, 19 skipped`), Cline skill audit, release harness audit, VSIX `test:ci` (`112 passing`, package contents 62 files), Python sdist/wheel build, VSIX package, artifact audit, Windows VSIX install/update smoke, and Docker import smoke. Windows local activation smoke remains CI/Linux-xvfb gated by design.

## 2026-05-06

- Preparing `v0.6.21` corrective release after the `v0.6.20` release workflow exposed missing uv setup in cross-platform activation smoke.
- Removed Zotero Keeper and PubMed Search MCP harness assets from Asset-Aware source and VSIX repo-assets; retained the LLM wiki builder as an Asset-Aware document-evidence workflow with external literature tools treated as optional.
- Added regression coverage for DOCX/DFM fail-closed checksum/doc-id/pre-save guards, citation locator-source verification and cache rebuilds, stale A2T table-context rejection, read-only segmentation provenance, VSIX package harness boundaries, release harness audits, and retired managed assistant-asset pruning.
- Hardened release workflows with cross-platform VSIX smoke, uv setup before packaged activation tests, and a release preflight gate before PyPI publishing.
- Reconciled the original local workspace to the published `v0.6.17` mainline after full history fetch showed the apparent `ahead 78` state was a shallow/grafted history artifact.
- Kept the full pre-reconcile dirty state in stash `pre-0.6.17-original-workspace-reconcile-20260506-091930`.
- Restored and prepared the remaining useful local assets for `v0.6.18`: `.cline/.codex` `llm-wiki-builder` skills, Cline Foam/LLM wiki rules/workflow, and `asset-aware-mcp-cline-timeout-report-2026-05-05.md`.
- Updated the VSIX assistant asset sync and package-content guard so the LLM wiki harness is bundled and release-checked.
- Started `0.6.18` version bump for Python package metadata, Docker label, VSIX manifest/lock, changelog, and memory bank.

## Done

- 完成 0.6.16 multi-agent repo corrective release：修正 Marker optional backend preflight/fallback、Marker page-map metadata remap、LightRAG entity prompt context、PyMuPDF segmentation backend provenance、A2T table resource traversal/stale citation/render contract、DOCX legacy conversion overwrite、OCR language normalization、PyMuPDF spawn fallback、VSIX local-source env 與 assistant harness legacy migration
- 完成 0.6.16 release/documentation hygiene：新增 `docs/asset-aware-mcp-issue-report-20260429.md` 作為修正來源報告，README/diagram/Copilot harness/Marker docs 對齊 50 tools / 13 resources，CI/release 改用 `uv sync --frozen` 並於 release workflow 執行 `uv lock --check`
- 完成 0.6.16 final local verification：`uv run pytest -q` → `686 passed, 21 skipped`（Ollama / Marker integration 因本機服務或 optional backend 未安裝跳過）、`uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy src --ignore-missing-imports`、`uv lock --check`、VSIX `npm run test:ci`、`git diff --check` 全部通過
- 完成 0.6.16 release version bump：Python package、Docker label、runtime version、VSIX manifest/lock、VSIX README banner、CHANGELOG 與 Memory Bank 已對齊到 0.6.16
- 完成 opt-in DFM→DOCX Track Changes emission：`save_docx(track_changes=True)` 會以原始 IR / edited IR 產生 token-level `w:del`/`w:ins`，同步啟用 `word/settings.xml` 的 `w:trackRevisions`，並支援表格儲存格文字 diff
- 完成 Track Changes citation-ready sidecar：`save_docx(track_changes=True)` 現在同步輸出 `revisions.jsonl`，每筆 record 含 `doc_id`、`source_revision_id`、`revision_id`、`block_id`、`op`、old/new text hash、char/byte range、context 與 locator，可銜接 MedPaper/Foam block anchor
- 完成 Track Changes write-back 修正後審查 findings：保留單一 hyperlink/SDT wrapper，依 run span 套用 revision run properties，避免 mixed-format 段落全部退化為第一 run 樣式
- 完成 DocxValidator run-level formatting gate：格式比對由 first-run sampling 改為逐 run + run count strict diff，補上 later-run regression test
- 完成 save_docx reserved-name fail-closed：明確拒絕輸出到 `original.docx`、`ir.json`、`content.*` 等 document state artifact
- 完成 VSIX assistant asset non-destructive sync：新增 workspace manifest，只有未被使用者修改的 extension-managed assets 會自動更新；custom same-path harness 會保留
- 完成 VSIX bundled harness 自洽性修正：`.github/bylaws/**` 與 `.claude/skills/**` 已納入 `resources/repo-assets/asset-aware/**`、sync script 與 package contents audit
- 完成 Copilot/Cline/Codex MCP config fail-closed：malformed JSON / suspicious TOML / unreadable config 會跳過寫入，避免把 custom server 或 unrelated entries 從原檔移除
- 完成 MedPaper LLM wiki / Foam 對齊契約文件：`docs/medpaper-llm-wiki-foam-alignment.md` 明確 Asset-Aware 作為 locator/provenance authority，MedPaper 作為 Foam materializer
- 完成 DOCX Track Changes → DFM review annotation 支援：`w:ins`、`w:del`、`w:moveFrom`、`w:moveTo` 與常見 paragraph/run format change 會輸出為唯讀 `dfm:revision` 區塊，並保留 revision id、author/date、source OOXML tag、scope、source block 與 visible-in-current-text metadata
- 完成 0.6.15 final local verification：Ruff、format、MyPy、full pytest (`667 passed, 21 skipped`)、Cline skill audit、release harness audit、VSIX `npm run test:ci` (`93 passing`, package contents 67 files)、VSIX install/update smoke、uv build、VSIX package、artifact audit、Docker build/import smoke、version sync、diff hygiene 全部通過；activation smoke 因本機無 `DISPLAY`/`xvfb-run` 正常跳過
- 完成 0.6.15 release version bump：Python package、Docker label、runtime version、VSIX manifest/lock、README banner、CHANGELOG 與 Memory Bank 已對齊到 0.6.15
- 完成 0.6.12 release hardening：CI、tagged release workflow、local `scripts/release.sh` 已收斂到同一組 release gates
- 完成 0.6.13 corrective fix：VSIX package-content guard 改用 VSCE `listFiles()` API，避免 Windows `npx` subprocess `spawn EINVAL`
- 新增 `scripts/audit_release_harness.py` 檢查 Cline rules/workflows/skills/MCP setup 是否維持可讀與可發版狀態
- 新增 `scripts/audit_release_artifacts.py` 檢查 Python sdist/wheel 與 VSIX 內容，避免大型或不應發布的檔案混入 artifact
- VSIX package 現在排除 `out/test/**`，並有 `npm run test:package-contents` 在 CI/local release 先擋住 compiled test leakage
- VS Code extension install smoke 現在不再 fallback 到 workspace root；CI 會在 Linux `xvfb` 下要求 activation 成功
- Release workflow 會在 publish 前驗證 tag/input version、Python metadata、VSIX manifest 三者一致
- 已將 Python package、Docker label、runtime version、VSIX manifest、version-pin tests、README banner 與 changelog 對齊到 0.6.13

## Doing

- 0.6.27 security/release-hygiene gates, exact-path commits, push, and annotated `v0.6.27` tag.

## Next

- 若要再提升 citation-ready 到「Word revision id ↔ sidecar record」完全對位，可在 OOXML emission 時把 `w:id` 回填到 `revisions.jsonl`，目前 sidecar 已提供 block/span/hash/range 級對位
- 觀察 GitHub Actions tagged release：PyPI / VS Code Marketplace 發布 jobs 應使用已驗證 artifact 與版本一致性 gate
