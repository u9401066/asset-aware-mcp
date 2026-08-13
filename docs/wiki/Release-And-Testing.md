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

```bash
python scripts/audit_release_artifacts.py
python scripts/smoke_built_wheel.py
python scripts/build_docs_site.py --check
python scripts/audit_release_harness.py
./scripts/release.sh
```

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
目前 Dockerfile 使用 cache mount，因此本機 Docker smoke 需要 BuildKit/buildx 可用。
