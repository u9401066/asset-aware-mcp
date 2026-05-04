# Progress (Updated: 2026-05-04)

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

- 0.6.16 local release gates 已完成；接著 commit、push、建立並推送 `v0.6.16` tag

## Next

- 若要再提升 citation-ready 到「Word revision id ↔ sidecar record」完全對位，可在 OOXML emission 時把 `w:id` 回填到 `revisions.jsonl`，目前 sidecar 已提供 block/span/hash/range 級對位
- 觀察 GitHub Actions tagged release：PyPI / VS Code Marketplace 發布 jobs 應使用已驗證 artifact 與版本一致性 gate
