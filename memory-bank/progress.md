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

## Doing

- 🚧 v0.3.0 架構重構：Asset-Centric Architecture
  - Phase 1: Asset Registry（資產註冊中心）
- 🚧 P0 server.py 模組化拆分（2122 行 → 子模組，骨架已建立，待完成）

## Next

- 完成 server.py 拆分（tools/ 5 模組 + resources/ 2 模組 + 瘦入口）
- P1: 抽取共用 asset utils（消除 document_service ↔ marker_adapter 重複）
- Phase 1: 建立 `AssetRegistry` 類別
- Phase 2: TableService 支援 `create_table_from_*` 方法
- Phase 3: Asset Bundle 批次獲取
