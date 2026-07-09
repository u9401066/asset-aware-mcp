# Progress (Updated: 2026-07-09)

## Done

- v0.8.0 發布文件同步完成：README.md/README.zh-TW.md、CHANGELOG.md、ROADMAP.md、docs/wiki (Home.md, PDF-Document-Workflow.md)、docs/site-content 重新生成、docs/index.html+site.js 版本字串均已反映多引擎 PDF ETL 能力
- 版本號全面同步至 0.8.0：pyproject.toml、src/__init__.py、Dockerfile、uv.lock、vscode-extension/package.json、package-lock.json（包含 root 與 packages[""] 兩處）
- 發現並修復 3 個 docs 同步測試失敗：版本字串未同步(Home.md/build_docs_site.py內嵌英文overview/site.js/index.html)、wiki 頁面不得連結到非 wiki 注冊頁面(改用 code span 參考 docs/docling-setup.md)
- 發布前置審計全部通過：scripts/audit_release_artifacts.py 版本一致性檢查 OK (0.8.0)；854 unit+infrastructure 測試全過；ruff 乾淨

## Doing



## Next

- git add 所有發布相關檔案並 commit
- git push origin master
- 建立並 push annotated tag v0.8.0
- push 後檢查 GitHub Actions CI 狀態，有失敗優先修復
