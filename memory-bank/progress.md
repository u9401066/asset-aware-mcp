# Progress (Updated: 2026-03-14)

## Done

- 修復 DFM 表格多行儲存格 `\n` 遺失問題（`<br>` 轉義策略，6 處一致）
- 新增 `export_markdown` 工具（md→docx/pdf/doc 匯出）
- 新增 `docx_table_from_context` 寫入後驗證（非空儲存格數量 >50% 偏差拒絕）
- 新增 `save_docx` 內容收縮安全閥（>50% 縮減自動拒絕 + `force` 參數）
- 新增 `docx_validate_roundtrip` 內容量指標（total_chars, table_nonempty_cells）
- 新增 `update_cell` 多行警告訊息
- 修復 Ollama Embedding API 相容性（`/api/embed` + legacy fallback）
- v0.5.0 發布：43 tools, 12 resources
- 補齊 PDF/DOCX 文件級 CRUD 與互轉能力
- 實作 strict DOCX round-trip 驗證與 save-time mutation guard
- 以 Proposal 真實文件完成 DOCX→DFM→DOCX、DOCX→PDF、DOCX→DOC 實戰驗證
- 修正 protected block placeholder 被誤判為編輯的 parser/integrity 根因問題

## Doing

- v0.5.0 tag & marketplace 發布

## Next

- Bug #4: 欄位名稱長度觸發 pipe-table 對齊偏移（低優先）
- Bug #6: 工具參數命名一致性（低優先）
- VS Code extension npm audit 相依套件弱點
