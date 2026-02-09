# Progress (Updated: 2026-02-09)

## Done

- ✅ v0.2.7 發布完成 (圖片擷取策略增強)
- ✅ 架構重構提案完成 (`docs/ARCHITECTURE_REFACTOR_PROPOSAL.md`)
- ✅ 決策記錄更新 (Asset-Centric Architecture)
- ✅ ROADMAP 更新 (v0.3.0 規劃)
- ✅ **v0.2.8: Marker 整合 + Section Navigation**
- ✅ **v0.2.9: ETL 缺陷修復 + 路徑統一 + 文件同步**
- ✅ **v0.2.10: Presentation 層模組化完成 + Bug 修復**
- ✅ **v0.2.11: ETL Profile + DDD 架構修復**（39 tools, 268 tests）
- ✅ **v0.2.14: A2T 完整填表系統**
  - **19 → 7 工具合併**：plan_table, table_manage, table_data, table_cite, table_history, table_draft, discover_sources
  - `get_section_content` 移至 section_tools (5 section tools)
  - **總工具數：39 → 28**（功能反而增加）
  - **新增 Domain 實體**：AssetRef, CellCitation, ChangeEntry, TableChangeLog, TableTemplate
  - **Service 層增強**：Citation CRUD, Audit Trail 自動記錄, Schema Evolution (add/remove/rename column), 4 內建模板
  - **68 新測試**：test_asset_ref.py (22), test_citation_audit.py (46)
  - **273 tests passed**, 0 failures
  - **MCP E2E 測試通過**：7 tools / 17 operations 全部正常
  - README / README.zh-TW / VSCode Extension README 全部同步更新

## Doing

- 🚧 v0.2.12: 測試覆蓋率與品質強化
  - 目標：44% → 60%+

---

## Released

- ✅ **v0.2.14**: A2T 完整填表系統 (2026-02-10)
- ✅ **v0.2.11**: ETL Profile + DDD 架構修復 (2026-02-09)

## Next

- P1: 測試覆蓋率提升（pdf_extractor, lightrag_adapter, asset_service, job_service）
- P2: 說明文件與推廣（examples/, API Reference, FAQ）
- P3: v0.3.0 Asset Registry
