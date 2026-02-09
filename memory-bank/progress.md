# Progress (Updated: 2026-02-09)

## Done

- ✅ v0.2.7 發布完成 (圖片擷取策略增強)
- ✅ 架構重構提案完成 (`docs/ARCHITECTURE_REFACTOR_PROPOSAL.md`)
- ✅ 決策記錄更新 (Asset-Centric Architecture)
- ✅ ROADMAP 更新 (v0.3.0 規劃)
- ✅ **v0.2.8: Marker 整合 + Section Navigation**
  - `ingest_documents(use_marker=True)` 產出 blocks.json
  - IngestResult 新增 `backend` 欄位追蹤使用的解析器
  - 支援 lazy-load Marker extractor (避免啟動時載入重模型)
  - `list_section_tree`, `get_section_detail`, `get_section_blocks`, `search_sections`
  - 支援任意深度的章節層級，不 hardcode
- ✅ **v0.2.9: ETL 缺陷修復 + 路徑統一 + 文件同步**
  - `docs/marker-etl-spec.md` — 完整規格書
  - 171 個單元測試全部通過
  - 修復 3 個 ETL 缺陷：Figure-Block 匹配、Table row/col 解析、圖片尺寸讀取
  - 修復路徑慣例不一致：`data/sources/{doc_id}/` → `data/{doc_id}/`
  - 修復 DocId 一致性：`marker_adapter.py` 改用 `DocId.generate()`
  - 更新 4 個指令/技能文件 (copilot-instructions, CLAUDE, AGENTS, SKILL)
  - 更新 README/CHANGELOG/ROADMAP 反映雙引擎 + Section Navigation
  - Presentation 層重構骨架：`mcp_app.py`, `dependencies.py`, `tools/`, `resources/`
- ✅ **v0.2.10: Presentation 層模組化完成 + Bug 修復**
  - server.py 從 2122 行瘦身為 31 行 thin entry point
  - 34 tools 分佈在 5 個模組 (tools/)
  - 12 resources 分佈在 2 個模組 (resources/)
  - 修復 C2: `use_marker` 現在正確傳遞到 async job
  - 修復 H1: `list_documents` 跳過 tables/jobs 目錄
  - 修復 H4: `_overlaps_existing_images` 實作 >50% bbox 重疊檢測
- ✅ **ETL 品質改進 第一輪 (PDF TOC + Table + Title + Noise Filter)**
  - 優先使用 PDF 內建 TOC (`get_toc()`) 取代字型大小啟發式
  - 使用 PDF metadata title 補強標題偵測
  - 加入 heading noise filter（最小長度 3 + regex 過濾）
  - 修復 table 提取：安裝 tabulate + fallback 機制
  - 合併連續 H1 heading 修復截斷標題
  - E2E 測試 5 篇論文 34 項全通過
- ✅ **ETL 品質改進 第二輪 (Caption Detection + Noise Filtering)**
  - 表格雜訊過濾：過濾 0 行或 ≤1 欄的空表格（GPT-4: 32→13 有效表格）
  - 小圖過濾：跳過 <50px 的 icon/logo 圖片
  - 表格 caption 偵測：搜尋表格 bbox 上下方 80px 文字，匹配 "Table N" 模式
  - 圖片 caption 偵測：掃描頁面文字匹配 "Figure N / Fig. N" 模式
  - Caption 覆蓋率：Tables 10/26 (38.5%)、Figures 50/136 (36.8%)
  - E2E 測試擴充至 44 項全通過
- ✅ **ETL 品質改進 第三輪 (Caption Precision + TOC Cleanup)**
  - Figure caption 行首錨定 + 最小長度 10 + number 去重，消除 in-text false positive
  - Table caption 限制 number ≤ 999，排除 "Table 34733" 等 false positive
  - PDF TOC 過濾 Figure/Table 條目，避免 caption 被誤判為 sections
  - Caption 精度 100%（所有 caption 皆為真實標題）
  - E2E 測試擴充至 47 項全通過

## Doing

- 🚧 ETL 拆解品質持續改進（第三輪）
- 🚧 v0.3.0 架構重構：Asset-Centric Architecture
  - Phase 1: Asset Registry（資產註冊中心）

## Next

- P1: 抽取共用 asset utils（消除 document_service ↔ marker_adapter 重複）
- Phase 1: 建立 `AssetRegistry` 類別
- Phase 2: TableService 支援 `create_table_from_*` 方法
- Phase 3: Asset Bundle 批次獲取
