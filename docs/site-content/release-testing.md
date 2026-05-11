<!-- Generated from Release-And-Testing.md by scripts/build_docs_site.py -->

# Release And Testing

## Focused Checks

依變更範圍先跑 focused tests：

```bash
uv run pytest tests/unit/test_count_tools_script.py -q
uv run pytest tests/unit/test_mcp_tool_layer.py -q
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

## Release Harness

```bash
python scripts/audit_release_artifacts.py
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

## Tool Count

工具數量不可手算：

```bash
./scripts/count_tools.sh
```

目前輸出：

```text
Total tools:      59 tools in 7 modules
Total resources:  13 resources in 2 modules
Grand total:      72 MCP endpoints
```

## Docker Smoke

```bash
docker build -t asset-aware-mcp:smoke .
docker run --rm --entrypoint python asset-aware-mcp:smoke -c "import src.presentation.server"
```

Docker build context 已忽略 local uv/runtime caches、assistant harness folders 與 document processing artifacts，避免 release smoke 被本機輸出拖慢或污染。
