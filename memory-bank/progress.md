# Progress (Updated: 2026-03-09)

## Done

- 強化 VSX extension 的 macOS uv 偵測與無工作區 storage 路徑處理
- 修正 extension 文件樹對新版/舊版 manifest 檔名的相容讀取
- 補上 macOS LibreOffice/soffice 偵測，讓 .doc 轉檔可在 mac App bundle 下工作
- 新增 extension 與 Python 單元測試，驗證路徑正規化與 manifest/LibreOffice 偵測
- 在 CI 新增 macOS smoke test，驗證 install.sh 與 VS Code extension unit tests

## Doing

- 整理本輪修正與 repo review 結果

## Next

- 如需要可提交目前修改並觀察新的 macOS CI 執行情況
