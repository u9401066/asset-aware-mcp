# Developer Guide

## 常用指令

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src --ignore-missing-imports
uv run pytest
./scripts/count_tools.sh
```

Extension：

```bash
cd vscode-extension
npm run test:ci
npm run sync-assets:check
```

## 本機 CI 對等檢查（push 前）

`scripts/pretest.py` 從受測 commit 讀取 `ci.yml` 全部 job 與 `release.yml` 的
`test` job，以相同 `run:` 指令及 workflow 釘選的 uv／Node／Python 版本執行，
最後列出「CI job → 本機結果」對照表：

```bash
python scripts/pretest.py --setup-wsl   # 一次性：WSL Ubuntu-26.04 安裝 CI 的 apt 套件、uv、Node
python scripts/pretest.py --quick       # commit 時：ruff、format、mypy、bandit、zizmor、uv lock、文件、資產同步
python scripts/pretest.py               # push 時：全部 CI job
python scripts/pretest.py --only integration-tests --skip windows-smoke
```

- `ubuntu-latest` job 在 WSL `Ubuntu-26.04`（與 GitHub 相同的 Ubuntu 26.04 與
  LibreOffice 26.2.7.3）的乾淨 checkout 執行；workflow 未安裝 LibreOffice 的 job
  看不到 LibreOffice。
- `windows-latest` job 在 Windows 主機的乾淨 checkout（預設 `C:\aamg`）以短
  ASCII `TEMP`／`--basetemp` 執行；主機未啟用 Win32 長路徑（GitHub runner 已啟用）
  時，`--basetemp` 改用 `\\?\` 長路徑前綴，讓超過 260 字元的 Wiki／證據路徑仍可
  測試，並在表格註明。
- macOS job 標示 **NOT VERIFIED**。工具版本不符或缺少 WSL distro 會直接 FAIL。
- `uv run pre-commit install --hook-type pre-commit --hook-type pre-push --hook-type commit-msg`
  會在 commit 跑 `--quick`、在 push 跑完整檢查。詳見 `CONTRIBUTING.md`。

## 新增 MCP Tool

1. 在 `src/presentation/tools/{module}.py` 加 `@mcp.tool()` async function。
2. 讓主要邏輯留在 application service，不把 domain/infrastructure 細節塞進 presentation。
3. 若會改變行為，加 focused regression test。
4. 執行 `./scripts/count_tools.sh` 更新工具數量。
5. 同步 README、Wiki 或 extension docs。

## 新增 Resource

1. 在 `src/presentation/resources/{module}.py` 加 `@mcp.resource(...)`。
2. Resource 應偏 read-only。
3. 不要讓 read path 有隱性 mutation；例如 segmentation resource 只讀已存在 schema。
4. 更新 [MCP Resources](MCP-Resources)。

## 新增 Document Artifact

新增 artifact 時要確認：

- stable filename。
- source identity。
- locator metadata。
- content/hash revision。
- 是否需要 FileStorage read/write method。
- 是否需要 deletion cleanup。
- 是否需要 VSIX tree view 顯示。

## DDD Boundary

不要讓 application/domain import presentation。測試：

```bash
uv run pytest tests/unit/test_import_boundaries.py -q
```

若 infrastructure 需要啟動 worker 或外部程序，先定義 application port，再由 infrastructure 實作。

## 文件與 Memory Bank

重要變更要更新：

- `memory-bank/progress.md`
- `memory-bank/activeContext.md`
- `CHANGELOG.md`，若對 release/user-facing 行為有影響
- README/Wiki，若 public surface 或操作方式改變

## 不要提交的東西

- `dist/`
- `vscode-extension/out/`
- `.venv/`
- `data/`
- `lightrag_db/`
- `.asset-aware-mcp/`
- document processing outputs
- local VSIX install artifacts
