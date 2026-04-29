# Progress (Updated: 2026-04-29)

## Done

- 完成 DOCX Track Changes → DFM review annotation 支援：`w:ins`、`w:del`、`w:moveFrom`、`w:moveTo` 與常見 paragraph/run format change 會輸出為唯讀 `dfm:revision` 區塊，並保留 revision id、author/date、source OOXML tag、scope、source block 與 visible-in-current-text metadata
- 完成 0.6.14 release version bump：Python package、Docker label、runtime version、VSIX manifest/lock、README banner、CHANGELOG 與 Memory Bank 已對齊到 0.6.14
- 完成 0.6.14 local release verification：Ruff、format、MyPy、full pytest、Cline skill audit、release harness audit、VSIX asset sync、extension CI、VSIX install/update smoke、Docker smoke、uv build、artifact audit、VSIX asset-content audit、diff hygiene 全部通過
- 完成 0.6.12 release hardening：CI、tagged release workflow、local `scripts/release.sh` 已收斂到同一組 release gates
- 完成 0.6.13 corrective fix：VSIX package-content guard 改用 VSCE `listFiles()` API，避免 Windows `npx` subprocess `spawn EINVAL`
- 新增 `scripts/audit_release_harness.py` 檢查 Cline rules/workflows/skills/MCP setup 是否維持可讀與可發版狀態
- 新增 `scripts/audit_release_artifacts.py` 檢查 Python sdist/wheel 與 VSIX 內容，避免大型或不應發布的檔案混入 artifact
- VSIX package 現在排除 `out/test/**`，並有 `npm run test:package-contents` 在 CI/local release 先擋住 compiled test leakage
- VS Code extension install smoke 現在不再 fallback 到 workspace root；CI 會在 Linux `xvfb` 下要求 activation 成功
- Release workflow 會在 publish 前驗證 tag/input version、Python metadata、VSIX manifest 三者一致
- 已將 Python package、Docker label、runtime version、VSIX manifest、version-pin tests、README banner 與 changelog 對齊到 0.6.13

## Doing

- 執行 0.6.14 full verification；通過後建立 release commit、push `master`，並推送 annotated tag `v0.6.14`
- 本機缺 `xvfb-run` 且 sudo 需要密碼，因此 activation-required VSIX smoke 只能交給 GitHub CI/release workflow 的 `xvfb-run -a npm run test:install-smoke -- --require-activation` gate；本機已通過 fresh/update install smoke

## Next

- 建立 0.6.14 release commit，push `master`，建立並推送 annotated tag `v0.6.14`
- 若要讓 AI 在 DFM 中做出的修改回寫成真正 Word Track Changes，下一步需新增 opt-in 的 DFM→DOCX diff emission：比較原始 block 與 edited block，產生 `w:del`/`w:ins`，並更新 `word/settings.xml` 的 track revisions 設定
- 觀察 GitHub Actions tagged release：PyPI / VS Code Marketplace 發布 jobs 應使用已驗證 artifact 與版本一致性 gate
