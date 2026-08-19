<!-- Generated from Git-Harness-Hygiene.md by scripts/build_docs_site.py -->

# Git Harness Hygiene

## 問題

VSIX 會自動同步 assistant harness 檔案。這些檔案對使用者工作區很有用，但在開發工作樹中，若 extension 先投放較舊版本或重新寫入 managed copy，Git status 會出現不必要的 untracked/modified noise，甚至阻擋 `git pull --ff-only`。

## 選用的本機降噪

`skip-worktree` 是開發者可以自行選用的 local Git index 設定，不是
repository 的預設狀態，也不代表目前機器一定已啟用。先以
`git ls-files -v` 查看實際 index flag；輸出行開頭的 `S` 代表
`skip-worktree`：

```bash
git ls-files -v \
  AGENTS.md \
  .github/copilot-instructions.md \
  .github/agents \
  .github/bylaws \
  .claude/skills \
  .cline/skills \
  .codex/skills \
  .clinerules
```

若確定要在當前 clone 啟用降噪，才執行：

```bash
git ls-files \
  AGENTS.md \
  .github/copilot-instructions.md \
  .github/agents \
  .github/bylaws \
  .claude/skills \
  .cline/skills \
  .codex/skills \
  .clinerules \
  | xargs -r git update-index --skip-worktree --
```

這是本機 Git index 設定，不會進入 commit，也不會改 repository
內容。它可能讓 tracked 變更隱於一般 `git status`，所以不是安全邊界，
也不應當作共享團隊政策。

## 何時解除

若你要真的修改 harness source，例如 release 前更新 `.clinerules` 或 `.codex/skills`，先解除：

```bash
git ls-files \
  AGENTS.md \
  .github/copilot-instructions.md \
  .github/agents \
  .github/bylaws \
  .claude/skills \
  .cline/skills \
  .codex/skills \
  .clinerules \
  | xargs -r git update-index --no-skip-worktree --
```

修改後再執行：

```bash
cd vscode-extension
npm run sync-assets
npm run sync-assets:check
```

## `.gitignore` 邊界

Repo 會忽略外部 MCP/assistant harness，例如 retired PubMed/Zotero/Copilot hooks；Asset-Aware 自己的 bundled harness source 仍保留在 repo 中，以便 VSIX packaging 可以同步。

也就是說：

- 外部 harness：忽略，不由此 repo 維護。
- Asset-Aware bundled harness：source 仍在 repo；開發者可在自己的 clone
  選用 `skip-worktree` 降噪，但修改或發布前必須先解除。
- `.asset-aware-mcp/assistant-assets.json`：runtime manifest，已被 `.gitignore` 忽略。
