# Progress (Updated: 2026-03-09)

## Done

- 補齊 PDF/DOCX 文件級 CRUD 與互轉能力
- 實作 strict DOCX round-trip 驗證與 save-time mutation guard
- 以 Proposal 真實文件完成 DOCX→DFM→DOCX、DOCX→PDF、DOCX→DOC 實戰驗證
- 修正 protected block placeholder 被誤判為編輯的 parser/integrity 根因問題
- 同步更新 CLI 與 README/README.zh-TW 的 42 tools 文件描述
- 完成 0.4.0 release 驗證：ruff、mypy、336 單元測試、Python build、VSIX 0.4.0 打包
- 修正 GitHub Release workflow 專屬 lint 問題，準備滾動 patch release v0.4.1

## Doing

- push / tag v0.4.1 並確認 CI/Release workflow 全綠

## Next

- 如需要，可處理 VS Code extension npm audit 顯示的相依套件弱點
