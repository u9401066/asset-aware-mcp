# Progress (Updated: 2026-08-13)

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
  153 VSIX tests、artifact audit、VS Code 1.133.0 fresh/update activation smoke。
- Docker `1.0.0` image 重建成功；容器內 doctor/list-tools/SDK 2 schema/stdio
  全綠，30 tools 且 `ctx` leakage 為零。

## Doing

- [ ] Create segmented commits, migrate `master` atomically to `main`,
  push and monitor GitHub Actions.


## Next

- Publish the annotated `v1.0.0` tag only after the new `main` CI is green.
- Verify the GitHub release, PyPI package and Marketplace VSIX from their
  published artifacts; add branch protection/rules after the first green main
  run establishes valid required-check names.
