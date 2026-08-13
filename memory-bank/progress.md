# Progress (Updated: 2026-08-13)

## v1.0.1 validation in progress

- Implemented the bounded streaming MessagePack PDF worker result channel and
  comprehensive fork/spawn, large-binary, timeout, crash, malformed-envelope,
  permission and cleanup regressions. Focused PDF/document tests, Ruff, MyPy,
  Bandit, frozen lock and universal dependency audit are green.
- Implemented MCP stderr logging, empty/blank ingest rejection and the managed
  dotenv-disable switch. The integrated Python run reached 1,138 passed and 30
  intentional optional-backend skips; its sole generated-docs version drift was
  rebuilt and the 16-file docs contract then passed.
- Added a true-stdio PDF asset regression with source/citation/media/Foam/hash
  integrity and deterministic repeat export. The final 15-page Attention paper
  run completed in 3.286 seconds: 27 text, six table and six figure assets,
  435 verified spans, 39 deterministic bundle records and 39 Foam notes; source
  bytes/mtime and protocol cleanliness were preserved.
- Codex CLI 0.147.0 is installed for parser/runtime verification. The VSIX
  semantic TOML parser bundle passed packaged activation smoke; final version
  alignment, local Codex config migration and `v1.0.1` release remain pending.
- Independent VSIX review found and fixed destructive Codex policy merging:
  extension-owned launch/env fields are rebuilt, while primary approval/future
  keys and nested `tools.*` tables are byte-preserved through update, opt-out
  and re-enable. Opt-out uses a non-executable `enabled=false` transport shell
  only when policy remains. Focused tests, all 185 VSIX tests, real Codex CLI
  parsing in all three states, npm audit, package audit and release harness pass.
- Closed the remaining global-config trust boundary: untrusted/lookalike
  workspaces cannot write Codex, Cline or Copilot settings, and production
  external-consumer launches are pinned to the extension version with isolated
  globalStorage data/cache instead of local source or workspace `.env`.
- Rebuilt the website and docs reader around the Evidence Rail contract,
  exact 30-tool explorer, install and development/release guidance, and GitHub
  navigation. Desktop and 390px Playwright screenshots, route/search/language/
  copy/mobile-menu/sidebar interactions and console/overflow assertions pass.

## Done

- 將 stale local checkout 快進至已發布 `v0.9.0` 基線；原始 dirty
  worktree 完整保存在 `pre-v0.9-sync-2026-08-13` stash。
- 完成 GitHub 收斂：關閉 PR #3/#4/#5/#8、刪除所有 13 條非 default
  remote branches，並從 backup branch 人工移植資料目錄對齊、Ollama
  embedding dimension probe、line metadata/query excerpt 等仍有效語意。
- 完成官方 MCP Python SDK `2.0.0` breaking migration：`MCPServer`、runtime
  `Context`、snake_case models、v2 `Client` smoke/tests，30 tool schemas 無
  `ctx` leakage，不保留 SDK v1 fallback。
- 完成 `pdf-preflight-v1`：五類 PDF、per-page OCR reason、native/OCR/Docling
  route、SHA-256/source-change guard、1-based top-left locators、spawn timeout/
  file/page/layout/memory caps；未直接引入尚未發布最新 DoS hardening 的
  `pdf-inspector` dependency。
- 完成 `agent-asset-bundle-v1`：deterministic manifest/JSONL/text/table/
  figure/media、stable hashes/locators/citations、portable Foam index/notes，
  使用 document-scoped staging/atomic replace 並保護來源及非 bundle output。
- Python universal lock、LightRAG floor、VSIX npm lock、Actions majors、
  Dependabot 與 dependency-security workflow 已更新；Python core/dev 與 npm
  audit 均為零已知漏洞。MinerU/Marker extras 因上游 cap 保持安全暫停。
- GitHub description/homepage/topics 與 area/security/provenance/release labels
  已同步；README、wiki、架構、VSIX Marketplace 說明與 `1.0.0` changelog 已
  對齊 reusable agent assets + Foam/LightRAG 核心定位。
- 修正 release review 發現的 LightRAG 初始化競態、figure hash/copy TOCTOU、
  evidence join 平方複雜度與無界輸出；bundle 現有 50,000 spans、25,000 records、
  256 MiB output hard limits，Marker/MinerU 即使手動安裝也無法走 production factory。
- GitHub Pages payload 與 VSIX assistant assets 已重新產生並驗證同步。
- 完整 Python gate：`1096 passed / 30 skipped`；Python 3.10 MCP/preflight/bundle
  focused gate：`32 passed`。Ruff、format、MyPy、Bandit、uv/npm audits、workflow
  security、docs/harness、git diff gates 全部通過。
- 重建 wheel/sdist/VSIX 並完成 clean Python 3.10 wheel smoke、MCP 2.0 stdio、
  154 VSIX tests、artifact audit、VS Code 1.133.0 fresh/update activation smoke。
- Docker `1.0.0` image 重建成功；容器內 doctor/list-tools/SDK 2 schema/stdio
  全綠，30 tools 且 `ctx` leakage 為零。
- 已建立並推送三個分段提交（core、release、docs），將 GitHub default branch、
  Pages source 與本機 tracking 原子遷移為 `main`，刪除遠端 `master`；目前遠端
  僅保留單一 `main` branch，沒有 open PR。
- 第一輪 `main` Actions 除 Windows VSIX smoke 外全綠；其根因是 npm script
  內單引號 glob 被 Windows 視為字面檔名，現已改為跨平台雙引號並加入契約測試。
- Replacement `main@183bbeb` CI、Windows、fail-closed `📋 Test Summary` 與
  `main:/docs` Pages build/deployment 全綠；線上網站已實測回傳 1.0.0、MCP 2、
  `export_assets` 與 Foam 內容。
- `main` 現受 strict aggregate check、至少 1 個 approval、stale review dismissal、
  conversation resolution、linear history、禁止 force-push/deletion 等 branch
  protection 保護。
- Annotated `v1.0.0` 已由 tag-first harness 建立並推送；Release workflow 的 tests、
  三平台 VSIX smoke、artifact/Docker preflight、PyPI、Marketplace、GitHub Release
  共 8 jobs 全綠。PyPI wheel/sdist 與公開下載 hashes 符合本機 build，Marketplace
  CDN 與 GitHub Release VSIX bytes/hash 一致。
- GitHub Wiki 已從舊 0.6.28 同步至 v1（19 files changed、5 new、0 deleted），
  並先建立 `pre-v1.0.0-sync-790a337` recovery tag；Home、LLM Wiki 與圖片 URL
  均回 HTTP 200。歷史 `v0.2.0` draft 因仍有對應 tag 與唯一 VSIX 而保留。

## Doing

- [x] v1.0.0 refresh、convergence、publication 與 post-release verification 完成。


## Next

- Let the scheduled uv/npm/Actions dependency workflows and Dependabot maintain
  the refreshed security floors; fail closed if held MinerU/Marker chains regress.
- Extend the reusable asset bundle through explicit DOCX/general-document
  repository adapters while preserving the v1 hashes, locators and Foam contract.
