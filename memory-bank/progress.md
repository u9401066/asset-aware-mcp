# Progress (Updated: 2026-04-14)

## Done

- 釐清 VSIX 安裝範圍：擴充套件保持全域安裝、狀態面板新增 Install Scope/Storage Root 顯示，且 README（含 zh-TW）/ extension README 說明資料仍存於 workspace `./data` 以避免重複安裝
- 完成 0.6.6 patch release 內容：修正 manifest title detection 在真實考題 PDF 上把頁碼/題幹誤當標題的問題，並新增低文字品質診斷欄位 (`text_quality_status` / `ocr_recommended` 等)
- `ManifestGenerator` 現在會先正規化 heading title、遇到 question-first PDF 退回 filename stem、並對低文字或高重複內容產生 OCR 建議
- `list_documents` / `inspect_document_manifest` 已顯示文字品質摘要，讓掃描型答案 PDF 不再只顯示模糊 title
- focused validation 完成：`uv run pytest tests/unit/test_services.py -q` 通過，且真實 `109/111/112` 題本與 `109` 答案本的 title / low-text 診斷皆符合預期
- 完成 0.6.5 版本號同步到 Python package、extension package、package-lock、版本測試與 changelog
- 確認 scoped large-PDF / page-range ingestion 關聯測試在 uv 環境通過，Python release metadata 已對齊 0.6.5

## Doing

- 建立 v0.6.6 release commit、tag 並推送

## Next

- 如需正式對外發布到套件平台，再執行 PyPI / VS Code Marketplace 發布流程
