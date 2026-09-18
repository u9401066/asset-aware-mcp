<!-- Generated from Release-And-Testing.md by scripts/build_docs_site.py -->

# Release And Testing

## Focused Checks

依變更範圍先跑 focused tests：

```bash
uv run pytest tests/unit/test_count_tools_script.py -q
uv run pytest tests/test_mcp_tools.py tests/unit/test_mcp_docx_tools.py tests/unit/test_mcp_job_tools.py tests/unit/test_mcp_document_tools.py tests/unit/test_mcp_table_tools.py tests/unit/test_mcp_profile_tools.py tests/unit/test_mcp_knowledge_tools.py tests/unit/test_mcp_server_startup.py tests/unit/test_job_service_concurrency.py tests/unit/test_pdf_validation.py -q
uv run pytest tests/unit/test_pdf_preflight.py tests/unit/test_agent_asset_bundle_service.py -q
uv run pytest tests/unit/test_docx_service.py -q
```

MCP tests target official SDK 2 `MCPServer` registration and real client/stdio
transports. They also assert that runtime-injected `Context` parameters never
appear in public tool input schemas. `mcp>=2,<3` is the supported contract；SDK
v1 and FastMCP/v1 fallback are intentionally unsupported。Balanced / compact /
legacy matrix 僅驗證 tool UX，不代表 protocol-version compatibility。

## Codex PDF evaluation

這是模型實際使用 MCP 的 opt-in 測試，與一般 SDK stdio 測試分開。需要已登入的
Codex CLI，會使用模型額度；一般 `pytest` 不會啟動 Codex。來源只有產生的合成
PDF，執行器不更改使用者 MCP 設定，也不讀取登入憑證。

```bash
uv run pytest tests/unit/test_pdf_rotated_crops.py tests/unit/test_codex_pdf_evaluation.py tests/integration/test_pdf_crud_stdio_matrix.py -q
uv run python -m tests.codex_pdf.run --mode mixed --output /tmp/pdf-codex-mixed
uv run python -m tests.codex_pdf.run --mode scanned --output /tmp/pdf-codex-scanned
# Codex 未在 PATH 時加 --codex /absolute/path/to/codex；output 必須是新目錄。
# 重做獨立稽核，不再呼叫模型：
uv run python -m tests.codex_pdf.audit /tmp/pdf-codex-scanned
```

執行器以 `--ignore-user-config`／`--ephemeral` 和單一必要 MCP server 連到目前
checkout；停用 shell／其他 apps／子 Agent，只允許測試用工具操作隔離資料。
這依據 [Codex 非互動模式](https://learn.chatgpt.com/docs/non-interactive-mode) 與
[MCP 設定](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。實際通過範例使用
CLI `0.154.0-alpha.6.1`；模型沿用 Codex 預設，不宣稱不同模型版本結果相同。

每份三頁 PDF 有七列、五欄，涵蓋純文字／無文字層掃描／混合頁、90 度旋轉、
非零 cropbox、前導零、負號、小數、百分比、比較符號與 µ 單位。期望值保留在
Agent 工作目錄之外，禁止用 shell 或讀取 fixture 程式取得答案。

`events.jsonl` 保留真實 MCP 呼叫及影像回應；`audit.json` 獨立核對來源 hash/mtime、
35 個欄位值、實際影像傳遞、掃描像素、各列引用、修改／刪除／還原歷史、Excel
重新開啟與 Wiki 資產包 hash。`run.json` 記錄程序結果，`expected.json` 記錄測資與
伺服器程式／lock hash。程序 exit 0 或 Agent 宣告成功，均不足以通過稽核。
可修復的工具錯誤保留在報告，完成後標示 `passed_with_recoveries`。
`first_transcription_exact` 另記初次轉錄是否完全正確，不把 Agent 事後修正
當成第一次就讀對；第二輪純掃描實測曾有兩個前導零缺漏，重新看圖後修正。

這些結果驗證限定測資與工具工作流程。掃描文字由 Agent 視覺轉錄，不冒充既有
文字 span；影像無法證明原始字元的 Unicode 編碼。模糊／手寫／合併儲存格／
複雜多欄與真實文件基準仍須擴充。表格 CRUD 操作衍生資料，並不改寫 PDF 版面。

## Full Python Gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src --ignore-missing-imports
uv run bandit -q -r src -x tests --severity-level medium
uv run pytest
python3 scripts/build_docs_site.py --check
uv lock --check
uvx --from uv==0.12.3 uv audit --preview-features audit-command --frozen --python-version 3.10
```

## Extension Gates

```bash
cd vscode-extension
npm run test:ci
npm run sync-assets:check
npm run test:install-smoke
npm audit --package-lock-only --audit-level=low
```

`test:install-smoke` 需要可執行的 VS Code CLI；Linux headless activation 另需 `xvfb-run`，下載版 VS Code 也需要系統圖形 runtime libraries（例如 `libgbm.so.1`）。

Before PyPI publish, runtime is verified from the built wheel with
`scripts/smoke_built_wheel.py`. After PyPI publish, the workflow verifies
`uvx --from asset-aware-mcp==$VERSION` diagnostics and MCP stdio handshake.

## Release Harness

`scripts/release.sh` 的預設模式是 pre-tag verification（安全的
dry-run）：它會執行完整 gates、重建 wheel/sdist 與 VSIX、執行 install /
stdio / Docker smoke，但不會建立 tag，也不會發布到 registry。執行前必須
先將 release 變更 commit 並 push 到 `main`；script 會 fail closed，要求 clean
worktree、local `main` 與 `origin/main` 完全相同、Python/VSIX 版本一致，
且預定的 annotated tag 尚未存在。

```bash
python scripts/audit_release_artifacts.py
python scripts/smoke_built_wheel.py
python scripts/build_docs_site.py --check
python scripts/audit_release_harness.py

# 預設：只驗證與建置，不建 tag、不發布
./scripts/release.sh

# 確認上述結果、main push 與 CI 後，再建立並 push annotated tag
./scripts/release.sh --push-tag
```

`--push-tag` 會重跑相同 gates，通過後建立 `v<version>` annotated
tag 並只 push 該 tag。推送 tag 會觸發 `.github/workflows/release.yml`；
GitHub Actions 之後擁有發布流程，local script 不會直接上傳 PyPI、
Marketplace 或 GitHub Release。`workflow_dispatch` 是 recovery／重跑入口，
仍要求已存在的 remote annotated tag、對應 commit 在 `main` 歷史中，
且 tag commit 與 workflow SHA 一致。

Actions 的發布順序是：

1. `test`：版本／tag identity、Python checks、完整 pytest、docs、security、
   harness 與 VSIX CI／install activation smoke。
2. `cross-platform-smoke`：Ubuntu、macOS、Windows 三平台 VSIX 安裝測試。
3. `release-preflight`：預先驗 Marketplace 權限，建置並稽核
   wheel/sdist 與 VSIX，執行 built-wheel 與 Docker stdio smoke。
4. `publish-pypi`：透過 trusted publishing 發布（已有同版本時驗證後重用）。
5. `publish-vscode`：先從 PyPI 安裝精確版本並完成 CLI／stdio
   smoke，再發布 VSIX、等待 Marketplace 可見，並上傳 workflow artifact。
6. `github-release`：用同一個 tag 建立 GitHub Release，並附上上一階段的
   VSIX。

Release workflow 會檢查：

- Python package version consistency。
- generated docs site 與 canonical wiki source exact sync。
- wheel/sdist required runtime files。
- VSIX package contents。
- retired external harness 是否被誤打包。
- Node/GitHub Actions release path。
- Marketplace publish visibility/retry。

The release harness now treats built-wheel console script execution and MCP
stdio handshake as first-class gates, not just import or `--help` checks.

## Post-Publish Verification

不以 workflow 單純顯示綠燈當作結案。等待所有 jobs 完成後，至少驗證
Actions、PyPI runtime、Marketplace 可見性與 GitHub Release 四個邊界：

```bash
VERSION="$(python3 scripts/get_version.py --strict-semver)"

gh run list --workflow release.yml --limit 5
gh run watch <run-id> --exit-status

uvx --refresh --python 3.11 \
  --from "asset-aware-mcp==$VERSION" \
  asset-aware-mcp doctor --json
uv run --no-project --python 3.11 \
  --with "asset-aware-mcp==$VERSION" \
  python scripts/smoke_mcp_stdio.py -- asset-aware-mcp

(cd vscode-extension && npx --no-install vsce show u9401066.asset-aware-mcp --json)
gh release view "v$VERSION" --json tagName,targetCommitish,isDraft,isPrerelease,assets
```

同時開啟 `https://pypi.org/project/asset-aware-mcp/$VERSION/` 與
`https://marketplace.visualstudio.com/items?itemName=u9401066.asset-aware-mcp`，
確認兩個 registry 都顯示精確版本；GitHub Release 必須不是 draft／
prerelease（除非本次本來就是 prerelease）、tag/target commit 正確，且
VSIX asset 存在。任一邊界未可見時，先保留 tag 與 workflow 證據並修復，
不要重用版本號。

## Dependency And Security Gate

`.github/workflows/dependency-security.yml` 是唯讀 gate：dependency manifests、
lockfiles 或 workflows 的 PR 會觸發，也可手動執行，並在每週一 05:17 UTC
排程執行。它不會自動寫回 repository：

- `uv lock --check` 防止 `pyproject.toml` 與 `uv.lock` drift。
- pinned uv 0.12.3 的 `uv audit --frozen --python-version 3.10` 稽核 universal lock，包含所有可解析
  runtime、dev 與 optional extras；不使用 vulnerability allowlist。
- `npm audit --package-lock-only --audit-level=low` 稽核 VSIX lockfile。
- Bandit 阻擋 Python source 的 medium/high security findings。
- CI 與 release preflight 也執行 Python lock check/audit，避免安全檢查只存在於
  排程。

`.github/dependabot.yml` 每週分流更新 uv/PyPI、npm 與 GitHub Actions，minor/patch
合併成 ecosystem group，major 保持獨立 PR，並設合理 open-PR limits。Python
專案使用 GitHub 官方 `uv` ecosystem，確保 `pyproject.toml` 與 `uv.lock` 一起更新。

## Scheduled Project Hygiene

`.github/workflows/project-hygiene.yml` 會在每週三 06:43 UTC 執行，也可用
`workflow_dispatch` 手動啟動。它刻意不 commit、不 push，也不繞過受保護的
`main`：

- 以 `scripts/build_docs_site.py --check`、public docs regressions、release
  metadata audit 與 VSIX `sync-assets:check` 驗證 website、Wiki source、README
  和 bundled assistant assets 都仍由 canonical source 可重建。
- 只對這個專案管理的 labels 執行 idempotent apply + exact check；workflow
  只提升該 job 的 `issues: write`，不刪除使用者或 GitHub 建立的其他 labels。
- repository description、homepage 與 canonical topics 預設只做 exact
  read-only drift check。若 repository owner 配置具有 Administration write
  的 repo-scoped `PROJECT_HYGIENE_TOKEN`，排程才會 apply 後再次驗證；手動要求
  apply 但缺 token 時會 fail closed。

本機可先執行同一份契約：

```bash
./scripts/gh_sync_labels.sh --check
./scripts/gh_update_repo_metadata.sh --check

# 只有在明確要寫入且 token 權限足夠時
./scripts/gh_sync_labels.sh --apply
./scripts/gh_update_repo_metadata.sh --apply
```

這個排程負責 deterministic 同步與 drift 告警；需要人類撰寫的新功能說明
仍應走一般 branch／review／CI，再由 Pages 部署與 Wiki sync 發布，避免 bot
自行改寫技術主張。

目前兩個重型 PDF backend 採 fail-closed security hold：

- MinerU adapter 保留，但 `[mineru]` extra 為空；MinerU 3.4.4 pin
  `transformers<5`，而相關 fixes 需要 `transformers>=5.5`。
- Marker adapter 保留，但 `[marker]` extra 為空；marker-pdf 1.10.2 pin
  `Pillow<11`，與 `Pillow>=12.2.0` 安全底線衝突。

等待上游解除限制後才恢復 extras，不用 audit ignore 把不可解 graph 假裝成綠燈。

## Tool Count

工具數量不可手算：

```bash
./scripts/count_tools.sh
```

目前輸出：

```text
Default public tools:       30 tools (balanced surface)
Decorator inventory:        63 tools in 7 modules
Total resources:            13 resources in 2 modules
Public MCP endpoints:       43 endpoints
Legacy decorator endpoints: 76 endpoints
```

## Docker Smoke

```bash
docker build -t asset-aware-mcp:smoke .
docker run --rm asset-aware-mcp:smoke doctor --json
docker run --rm asset-aware-mcp:smoke list-tools --json
uv run python scripts/smoke_mcp_stdio.py -- docker run --rm -i asset-aware-mcp:smoke
```

Docker build context 已忽略 local uv/runtime caches、assistant harness folders 與 document processing artifacts，避免 release smoke 被本機輸出拖慢或污染。
目前 Dockerfile 刻意不使用 BuildKit cache mount，以保留 legacy builder
相容性；這個 build 不會單因 Dockerfile 而要求 `docker buildx`。
