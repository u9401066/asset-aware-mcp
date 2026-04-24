# Progress (Updated: 2026-04-24)

## Done

- 完成 0.6.12 release hardening：CI、tagged release workflow、local `scripts/release.sh` 已收斂到同一組 release gates
- 新增 `scripts/audit_release_harness.py` 檢查 Cline rules/workflows/skills/MCP setup 是否維持可讀與可發版狀態
- 新增 `scripts/audit_release_artifacts.py` 檢查 Python sdist/wheel 與 VSIX 內容，避免大型或不應發布的檔案混入 artifact
- VSIX package 現在排除 `out/test/**`，並有 `npm run test:package-contents` 在 CI/local release 先擋住 compiled test leakage
- VS Code extension install smoke 現在不再 fallback 到 workspace root；CI 會在 Linux `xvfb` 下要求 activation 成功
- Release workflow 會在 publish 前驗證 tag/input version、Python metadata、VSIX manifest 三者一致
- 已將 Python package、Docker label、runtime version、VSIX manifest、version-pin tests、README banner 與 changelog 對齊到 0.6.12

## Doing

- 執行 0.6.12 post-bump full verification，通過後建立 release commit、push `master`，並推送 annotated tag `v0.6.12`

## Next

- 觀察 GitHub Actions tagged release：PyPI / VS Code Marketplace 發布 jobs 應使用已驗證 artifact 與版本一致性 gate
