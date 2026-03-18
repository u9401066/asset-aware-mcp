# Progress (Updated: 2026-03-18)

## Done

- **v0.5.2 發布**
- MCP Server 版本釘定與自動升級（`--from`, `--upgrade`, `upgradeServer` 指令）
- Windows `OSError` (torch DLL) 安全降級修正（`except (ImportError, OSError)`）
- 測試工具計數更新：36 → 43
- `marker-pdf` 改為 optional extra：預設安裝不再拉入 torch / surya 依賴鏈
- install scripts 改為預設 `uv sync --python 3.11`，僅在 `--with-marker` 時才安裝 Marker backend
- VS Code extension 新增 Marker backend 開關與 `torchBackend` 設定，預設 `cpu`
- `marker_adapter.py` 改為懶 import，未安裝 Marker 時仍可 import dataclass 與跑 unit tests
- 補齊文件說明：README / README.zh-TW / extension README / CHANGELOG 對齊 optional Marker 安裝策略
- 修復 VS Code extension 在 macOS / Python 3.14 上因 `regex` / `marker-pdf` 原生編譯而啟動失敗的問題
- extension 與 installer 啟動 runtime 固定為 Python 3.11，但不限制專案整體 3.11+ 支援宣告
- 新增 extension 單元測試：`mcpProvider.test.ts` 驗證 prod/dev mode 都帶入 `--python 3.11`
- 補齊 README、README.zh-TW、vscode-extension README 的 runtime 說明與 docx/tool 數量一致性
- 驗證完成：extension unit tests、VSIX install smoke test、Python 基線測試、Linux installer diagnostics
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

- v0.5.2 released — 等待 CI / PyPI / VSIX 發布完成

## Next

- 視需要將 Linux smoke test 擴展為 CI 中對 `Check System Dependencies` 輸出的斷言
- Bug #4: 欄位名稱長度觸發 pipe-table 對齊偏移（低優先）
- Bug #6: 工具參數命名一致性（低優先）
- VS Code extension npm audit 相依套件弱點
