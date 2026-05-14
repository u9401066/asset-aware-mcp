<!-- Generated from Release-And-Testing.md by scripts/build_docs_site.py -->

# Release And Testing

## Focused Checks

依變更範圍先跑 focused tests：

```bash
uv run pytest tests/unit/test_count_tools_script.py -q
uv run pytest tests/unit/test_mcp_docx_tools.py tests/unit/test_mcp_job_tools.py tests/unit/test_mcp_document_tools.py tests/unit/test_mcp_table_tools.py tests/unit/test_mcp_profile_tools.py tests/unit/test_mcp_knowledge_tools.py tests/unit/test_mcp_server_startup.py tests/unit/test_job_service_concurrency.py tests/unit/test_pdf_validation.py -q
uv run pytest tests/unit/test_docx_service.py -q
```

## Full Python Gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src --ignore-missing-imports
uv run pytest
uv lock --check
```

## Extension Gates

```bash
cd vscode-extension
npm run test:ci
npm run sync-assets:check
npm run test:install-smoke
```

`test:install-smoke` 需要可執行的 VS Code CLI；Linux headless activation 另需 `xvfb-run`，下載版 VS Code 也需要系統圖形 runtime libraries（例如 `libgbm.so.1`）。

Before PyPI publish, runtime is verified from the built wheel with
`scripts/smoke_built_wheel.py`. After PyPI publish, the workflow verifies
`uvx --from asset-aware-mcp==$VERSION` diagnostics and MCP stdio handshake.

## Release Harness

```bash
python scripts/audit_release_artifacts.py
python scripts/smoke_built_wheel.py
python scripts/audit_release_harness.py
./scripts/release.sh
```

Release workflow 會檢查：

- Python package version consistency。
- wheel/sdist required runtime files。
- VSIX package contents。
- retired external harness 是否被誤打包。
- Node/GitHub Actions release path。
- Marketplace publish visibility/retry。

The release harness now treats built-wheel console script execution and MCP
stdio handshake as first-class gates, not just import or `--help` checks.

## Tool Count

工具數量不可手算：

```bash
./scripts/count_tools.sh
```

目前輸出：

```text
Total tools:      62 tools in 7 modules
Total resources:  13 resources in 2 modules
Grand total:      75 MCP endpoints
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
