# Progress (Updated: 2026-03-09)

## Done

- 新增 VSIX install smoke 測試腳本，模擬 fresh install 與 update install
- 在本機以真實 VSIX 驗證 0.2.10 → 0.3.3 更新與 0.3.3 新安裝
- 修正 ESLint 忽略 .vscode-test 與 *.vsix，避免 smoke test 後 lint OOM

## Doing

- 整理 CI 與本地 install-smoke 驗證結果

## Next

- 如需要可提交 install-smoke 變更並 push 觸發新的跨平台 CI
