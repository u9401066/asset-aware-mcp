# Active Context

> 📌 當前工作焦點和進行中的變更

## 🎯 當前焦點

- **ETL 品質改進第二輪已完成**：Caption 偵測 + 雜訊過濾
- **🚧 繼續完善拆解品質**：提升 caption 覆蓋率、改善匹配精度
- **🚧 v0.3.0 架構重構**：Asset-Centric Architecture

## 已完成的工作 (ETL 第二輪)

### 雜訊過濾
1. **Noise table 過濾** — 過濾 0 行或 ≤1 欄空表格（GPT-4: 32→13）
2. **Small figure 過濾** — 跳過 <50px icon/logo 圖片

### Caption 偵測
3. **Table caption** — `_detect_table_caption()`: 搜尋 table bbox 上下方 80px 文字
4. **Figure caption** — `extract_figure_captions()`: 掃描頁面文字匹配 Figure/Fig 模式
5. **Caption 覆蓋率**: Tables 10/26 (38.5%), Figures 50/136 (36.8%)

### 測試
- E2E 測試擴充至 **44 項**全部通過
- 新增：`test_no_noise_tables`, `test_table_has_caption`, `test_no_small_figures`, `test_figure_captions`
- 跨文件：`test_no_noise_tables_globally`, `test_no_small_figures_globally`, `test_caption_coverage_summary`

## 進行中

### v0.3.0: Asset-Centric Architecture
- Phase 1: 建立 AssetRegistry 類別
- Phase 2: 擴展 TableService
- Phase 3: 新增 MCP Tools

## ⚠️ 待解決

1. **P1**: 抽取 document_service ↔ marker_adapter 共用程式碼
2. **Caption 精度改善**：部分 false positive（如 Docling "Table 34733"）、重複 caption
3. **Marker 引擎小圖過濾**：Marker 產出的圖片中也需過濾 <50px 的小圖標

## 📁 專案結構

```
src/
├── domain/          # 🔵 核心業務邏輯
├── application/     # 🟢 使用案例
├── infrastructure/  # 🟠 外部依賴實作
└── presentation/    # 🔴 MCP Server (34 tools, 12 resources)
    ├── mcp_app.py        # FastMCP 實例
    ├── dependencies.py   # Composition Root
    ├── server.py         # 31 行 thin entry point
    ├── tools/            # 5 模組
    └── resources/        # 2 模組
```

---
*Last updated: 2026-02-09*
