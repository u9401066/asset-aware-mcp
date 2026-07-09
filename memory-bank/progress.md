# Progress (Updated: 2026-07-09)

## Done

- 發布前置準備：版本由 0.8.0 升級至 0.9.0（minor bump，因為包含真實新功能混合批次攝入 + 多引擎來源統一），同步更新 pyproject.toml/src/__init__.py/vscode-extension/package.json+package-lock.json/Dockerfile/uv.lock 共 6 處版本號
- 新增 CHANGELOG.md v0.9.0 段落（Added: 混合批次攝入+source_engine可見化；Fixed: 多引擎來源統一+Docling bbox正規化+job結果形狀/失敗語意/next-steps三項修正），同步更新 README.md/README.zh-TW.md 新增混合批次攝入 feature bullet、ROADMAP.md 新增 v0.9.0 完成項、docs/wiki/Home.md+PDF-Document-Workflow.md+vscode-extension/README.md 新增說明
- 重新產生 docs/site-content.js 與 docs/site-content/*.md（從 docs/wiki 來源），並修正 build_docs_site.py 內嵌英文 overview 版本號與 docs/site.js 版本字串；順帶修正 build_docs_site.py 一個現有 mypy 變數名衝突問題（path 變重用導致 Path→str）
- 完整發布前驗證全部通過：876 unit+infra+integration 測試、ruff check+format、mypy已改檔案、docs site sync 測試(16個)、VS Code extension test:ci（152 passing + VSIX package contents）、scripts/check_cline_skills.py、scripts/audit_release_harness.py、uv build + audit_release_artifacts.py + smoke_built_wheel.py（確認 wheel 安裝後仍是30個公開工具）全部維持締淨

## Doing



## Next

- Commit 所有 v0.9.0 發布文件變更
- 建立 annotated tag v0.9.0
- Push commits + tag 到 origin/master，觸發 GitHub Actions release workflow（發布到 PyPI + VS Code Marketplace + GitHub Release）
- Push 後必須監控 CI 狀態，如有失敗優先修復
