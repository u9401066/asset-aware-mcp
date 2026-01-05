# Progress (Updated: 2026-01-05)

## Done

- 環境配置與依賴安裝 (xlsxwriter, pydantic-settings)
- 實作 A2T Domain Entities (TableDraft, TableSchema, TableContext)
- 實作 TableService (支援 Draft 持久化、單元格更新、Token 估算)
- 實作 ExcelRenderer (XlsxWriter 封裝)
- 註冊 A2T 2.0 MCP Tools (plan, draft, resume, update_cell, etc.)
- 完成單元測試並驗證 A2T 2.0 工作流
- 更新所有專案文檔 (README, Spec, Roadmap, Architecture) 以反映 A2T 2.0 功能
- 執行 Ruff 程式碼品質檢查與格式化修復
- 發布版本 v0.2.0 (包含 A2T 2.0 與 PyMuPDF 輕量化)

## Doing



## Next

- 撰寫 E2E 整合測試場景 (探索 -> 提取 -> 建表 -> 輸出)
- 優化 LightRAG 查詢與 A2T 的整合流程
