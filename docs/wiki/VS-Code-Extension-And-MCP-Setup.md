# VS Code Extension And MCP Setup

## Extension 責任

VS Code extension 位於 `vscode-extension/src`。它負責讓使用者不用手動組 MCP config，也能從 VS Code、Copilot、Cline、Codex 啟動同一個 Asset-Aware MCP server。

主要來源：

- `vscode-extension/src/extension.ts`
- `vscode-extension/src/mcpProvider.ts`
- `vscode-extension/src/copilotMcpConfig.ts`
- `vscode-extension/src/clineMcpConfig.ts`
- `vscode-extension/src/codexMcpConfig.ts`
- `vscode-extension/src/assistantAssets.ts`
- `vscode-extension/src/envManager.ts`
- `vscode-extension/src/documentTreeProvider.ts`
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

### Codex managed config

Extension 寫入的 Asset-Aware Codex block 會明確啟用 server，並使用適合
文件處理的 timeout：

```toml
[mcp_servers.asset-aware-mcp]
enabled = true
startup_timeout_sec = 180
tool_timeout_sec = 900
```

Repository `.env` 可能含有 API key、token、password、proxy 或 certificate
設定。Extension 不會把這些值寫進 `~/.codex/config.toml`；只會在
`env_vars = [...]` 列出必要的變數名稱。Codex 只會從「啟動 Codex client
本身的 OS environment」繼承同名值；Extension 不會把 workspace `.env` 或
VS Code secret setting 的值搬進 Codex process。若 managed server 需要遠端
backend credential，必須先在啟動 Codex 前 export，否則該 credential 不會被
傳入。只有
`DATA_DIR`、`ETL_ENGINE`、model 名稱與其他明確 allowlist 的非機密運作
metadata 可以內嵌在 managed env table。更新既有 managed block 時，舊的
credential-like inline values 也會改成 `env_vars` 名稱傳遞。含 userinfo、
query 或 fragment 的 runtime URL 也不會 inline，以避免 URL credential 落盤。
Config 以原子 claim/create-if-absent 寫入，temporary file permission 為
`0600`。每次真正更新既有 `config.toml` 時，舊 inode 會以
`config.toml.concurrent-backup.<pid>.<timestamp>.<random>` 留在同一目錄，
permission 也會收緊為 `0600`。這份 recovery snapshot 可保留其他 editor
已開啟的 file descriptor 在更新後才寫入的內容；首次建立與無變更的
idempotent sync 不會產生新 snapshot。可先比對 recovery snapshot 與現行
`config.toml`，確認沒有需要合併的設定、且 Codex/VS Code 不再寫入後，
再手動移除；請勿把可能含 credential 的 snapshot 內容貼到 issue 或 log。
Codex config 若無法解析或是 symbolic link，Extension 會警告並保持原檔
不動；Copilot/Cline 的 JSON 修復路徑則會在必要時建立備份。

`assetAwareMcp.manageCodexConfig` 是 machine-scoped 設定，預設為 `true`。
設為 `false` 會移除 extension-owned launch/env 欄位，並防止後續 activation
重建；同名但由使用者自訂的 block 不會被刪除。若 managed server 另有使用者
設定的 `required`、tool allow/deny、approval mode、future policy key 或
`tools.*` nested table，這些原始 bytes 會保留在一個 `enabled=false` 的 dormant
entry，讓 Codex 設定仍可解析且不啟動 server；重新啟用管理時再接回新的 managed
launch。沒有 user policy 時，entry 會完整移除。Ownership 只以 extension 的精確
managed marker 判定，不用 executable 名稱或 `src.server` 字串猜測；opt-out
清理也不依賴 uv 或 runtime preparation 成功。

## Runtime Preparation

Extension 啟動 server 時會使用 pinned package version，並透過 `uv` / `uvx`
準備 runtime。Codex 與 Cline 這類全域 external consumer 永遠使用 extension
版本鎖定的 published package，`cwd`、`DATA_DIR` 與 `UV_CACHE_DIR` 都位於
extension `globalStorage`；它們不採用 workspace local source、workspace-scoped
setting 或 repository `.env`。VS Code 原生 MCP provider 只有在 workspace trusted
且 extension 執行於 Development/Test mode 時才可選擇 local source，正式安裝版
仍使用 pinned package。這避免同名 lookalike repository 把未信任 Python 或環境值
持久化進全域 agent config。

Restricted Mode 下不會自動新增、更新或移除 Codex/Cline/Copilot config，也不會
同步 assistant assets。`package.json` 的 `untrustedWorkspaces` capability 明確標成
limited；恢復 workspace trust 後才執行 managed sync。

Marker backend setting 保留，但 security hold 期間不會安裝 `marker-pdf`。

## Assistant Assets Sync

VSIX 會打包 `vscode-extension/resources/repo-assets/asset-aware/**`。Extension 安裝/啟動時只會同步 assistant harness 類檔案到 workspace：

- `AGENTS.md`
- `.github/copilot-instructions.md`
- `.github/agents/**`
- `.github/bylaws/**`
- `.claude/skills/**`
- `.cline/skills/**`
- `.codex/skills/**`
- `.clinerules/**`

同步使用 `.asset-aware-mcp/assistant-assets.json` manifest。只有「先前由 extension 寫入且未被使用者修改」的檔案會自動更新；同路徑自訂檔會 preserved。

`scripts/count_tools.ps1` 等 package guard 相關檔案也會被打包在 repo-assets 中，用於 VSIX/package 檢查，但不是 `installAssistantAssets` 會寫回 workspace 的 assistant harness 目標。

## UI Components

| 檔案 | 用途 |
|---|---|
| `documentTreeProvider.ts` | 文件樹、Artifacts group、Citations group、artifact/citation open commands |
| `tableTreeProvider.ts` | A2T table tree |
| `statusTreeProvider.ts` | 狀態與 runtime tree |
| `statusBar.ts` | 狀態列 |
| `settingsPanel.ts` | 設定面板 |
| `dfm/*` | DFM editor service 與 language features |

## Artifact / Citation Viewer

目前的 Documents tree 會在每個已攝入文件下顯示：

| Node | 來源 artifact | 行為 |
|---|---|---|
| `Artifacts` | `manifest.json`、`full.md`、`segmentation.json`、`citation_index.jsonl`、layout overlays 等 | 點擊後在 VS Code 開啟對應檔案 |
| `Citations` | `citation_index.jsonl` 前幾筆 EvidenceSpan summary | 點擊後開啟 citation index 並跳到對應 line |

對應 helper 位於 `EnvManager.listDocumentArtifacts(docId)` 與 `EnvManager.listCitationSpans(docId, limit)`。這個 UI 不是重新計算 citation；它讀取 MCP server 已產生的 durable artifacts，方便人類快速檢查 locator、quote/hash、page 與 span kind。

## Extension Checks

```bash
cd vscode-extension
npm run test:ci
npm run sync-assets:check
npm run test:install-smoke
```

Package contents tests 會防止 dev-only extension 檔與 generated dirs 混入 repo-assets，例如 `repo-assets/**/dist`、`repo-assets/**/.venv`、`repo-assets/**/.pytest_cache`、`repo-assets/**/__pycache__`、nested generated repo-assets、`node_modules` 等。Root-level `vscode-extension/.venv` 不屬於 assistant asset sync 目標；若要檢查，需用 release artifact audit 或額外 package rule。
