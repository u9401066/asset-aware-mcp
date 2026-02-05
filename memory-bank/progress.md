# Progress (Updated: 2026-02-05)

## Done

- ✅ v0.2.7 發布完成 (圖片擷取策略增強)
- ✅ 架構重構提案完成 (`docs/ARCHITECTURE_REFACTOR_PROPOSAL.md`)
- ✅ 決策記錄更新 (Asset-Centric Architecture)
- ✅ ROADMAP 更新 (v0.3.0 規劃)
- ✅ **Marker 整合到標準 ingest 流程**
  - `ingest_documents(use_marker=True)` 產出 blocks.json
  - IngestResult 新增 `backend` 欄位追蹤使用的解析器
  - 支援 lazy-load Marker extractor (避免啟動時載入重模型)
  - 研究 Unstructured.io (13.9k stars) 作為未來備選方案
- ✅ **Section Navigation Tools (動態層級)**
  - `list_section_tree`: 顯示完整 section hierarchy 樹狀結構
  - `get_section_detail`: 取得特定 section 的詳細資訊
  - `get_section_blocks`: 提取特定 section 的所有 blocks
  - `search_sections`: 搜尋 section 名稱
  - 支援任意深度的章節層級，不 hardcode

## Doing

- 🚧 v0.3.0 架構重構：Asset-Centric Architecture
  - Phase 1: Asset Registry（資產註冊中心）

## Next

- Phase 1: 建立 `AssetRegistry` 類別
- Phase 2: TableService 支援 `create_table_from_*` 方法
- Phase 3: Asset Bundle 批次獲取
