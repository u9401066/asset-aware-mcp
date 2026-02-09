# Active Context

> 📌 當前工作焦點和進行中的變更

## 🎯 當前焦點

- **v0.2.14 已完成並驗證**：A2T 完整填表系統，MCP E2E 測試通過
- **下一步**：v0.2.12 測試覆蓋率提升 / v0.2.13 文件與推廣

## MCP E2E 測試結果 (2026-02-09)

7 個 tools、17 個 operations 全部通過：

| Tool | 測試操作 | 狀態 |
|------|---------|------|
| `plan_table` | templates | ✅ 4 個模板正常 |
| `table_manage` | create, add_column, rename_column, preview, list, delete | ✅ CRUD + Schema 演進 |
| `table_data` | add_rows, get_cell, update_cell | ✅ 資料讀寫正常 |
| `table_cite` | add, get | ✅ AssetRef 引用附加層正常 |
| `table_history` | changes, tokens | ✅ Audit Trail 完整紀錄 4 筆操作 |
| `table_draft` | create, add_rows, resume, commit | ✅ 草稿→正式表格完整流程 |
| `discover_sources` | 跨文件搜尋 | ✅ 找到 2 個 section 來源 |

## 已完成的工作 (v0.2.14)

### A2T 工具合併 (19 → 7)
1. **plan_table** — schema 規劃 + 模板查詢 + 從模板建表
2. **table_manage** — create/delete/list/preview/resume/render + schema evolution
3. **table_data** — add_rows/get_row/update_row/delete_row/get_cell/update_cell/clear_cell
4. **table_cite** — add/get/remove citations + cell_history
5. **table_history** — changes audit trail + token estimation
6. **table_draft** — create/update/add_rows/resume/commit/list/delete
7. **discover_sources** — 跨文件資料來源探索

### 新增 Domain 實體
- **AssetRef** — frozen dataclass, 7 種來源類型, 工廠方法
- **CellCitation** — 儲存格級引用管理
- **ChangeEntry + TableChangeLog** — 變更審計軌跡
- **TableTemplate** — 表格模板 (4 內建)

## 📁 專案結構

```
src/
├── domain/          # 🔵 核心業務邏輯
├── application/     # 🟢 使用案例
├── infrastructure/  # 🟠 外部依賴實作
└── presentation/    # 🔴 MCP Server (28 tools in 6 modules, 12 resources)
    ├── tools/
    │   ├── document_tools.py   # ETL (6)
    │   ├── section_tools.py    # Navigation (5)
    │   ├── job_tools.py        # Job (3)
    │   ├── knowledge_tools.py  # KG (2)
    │   ├── profile_tools.py    # Profile (5)
    │   └── table_tools.py      # A2T (7) — operation-based
    └── resources/              # 12 resources
```

## ⚠️ 待解決

1. **MyPy 類型錯誤**: `services.py:151`, `pdf_extractor.py:586`
2. **測試覆蓋率**: 44% → 目標 60%+
3. **文件缺乏**: API Reference, Examples, FAQ

---
*Last updated: 2026-02-09*
