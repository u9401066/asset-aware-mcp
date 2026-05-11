<!-- Generated from VS-Code-Extension-And-MCP-Setup.md by scripts/build_docs_site.py -->

# VS Code Extension And MCP Setup

![VS Code extension and MCP setup](wiki/assets/vsix-mcp-setup.jpg)

## Extension 責任

VS Code extension 位於 `vscode-extension/src`。它負責讓使用者不用手動組 MCP config，也能從 VS Code、Copilot、Cline、Codex 啟動同一個 Asset-Aware MCP server。

主要來源：

- `vscode-extension/src/extension.ts`
- `vscode-extension/src/mcpProvider.ts`
- `vscode-extension/src/copilotMcpConfig.ts`
- `vscode-extension/src/clineMcpConfig.ts`
- `vscode-extension/src/codexMcpConfig.ts`
- `vscode-extension/src/assistantAssets.ts`
- `vscode-extension/src/uv.ts`
- `vscode-extension/src/ollama.ts`

## MCP Config Merge

Extension 會保守 merge：

| 目標 | 行為 |
|---|---|
| Copilot | workspace `.vscode/mcp.json` |
| Cline | `cline_mcp_settings.json` |
| Codex | `~/.codex/config.toml` |

Merge 原則：

- 保留使用者自訂 server。
- 保留 Cline `alwaysAllow`、`disabled`、custom env 與 unrelated entries。
- malformed JSON/TOML 會 fail closed，必要時先備份。
- 不用空白 config 覆蓋現有設定。

## Runtime Preparation

Extension 啟動 server 時會使用 pinned package version，並透過 `uv` 準備 runtime。`0.6.27` 中 runtime preparation 使用 extension-storage `UV_CACHE_DIR`，避免使用者 global uv cache 權限問題。

Marker backend setting 保留，但 security hold 期間不會安裝 `marker-pdf`。

## Assistant Assets Sync

VSIX 會打包 `vscode-extension/resources/repo-assets/asset-aware/**`，安裝/啟動時同步到 workspace：

- `AGENTS.md`
- `.github/copilot-instructions.md`
- `.github/agents/**`
- `.github/bylaws/**`
- `.claude/skills/**`
- `.cline/skills/**`
- `.codex/skills/**`
- `.clinerules/**`

同步使用 `.asset-aware-mcp/assistant-assets.json` manifest。只有「先前由 extension 寫入且未被使用者修改」的檔案會自動更新；同路徑自訂檔會 preserved。

## UI Components

| 檔案 | 用途 |
|---|---|
| `documentTreeProvider.ts` | 文件樹 |
| `tableTreeProvider.ts` | A2T table tree |
| `statusTreeProvider.ts` | 狀態與 runtime tree |
| `statusBar.ts` | 狀態列 |
| `settingsPanel.ts` | 設定面板 |
| `dfm/*` | DFM editor service 與 language features |

## Extension Checks

```bash
cd vscode-extension
npm run test:ci
npm run sync-assets:check
npm run test:install-smoke
```

Package contents tests 會防止 `dist/`、`tmp/`、nested generated repo-assets、`node_modules`、`.venv`、`.pytest_cache`、`__pycache__` 等被打包進 VSIX。
