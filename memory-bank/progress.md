# Progress (Updated: 2026-02-11)

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
  - 19 → 7 工具合併，總工具數 39 → 28
  - 68 新測試 (asset_ref + citation_audit)
- ✅ **v0.3.0: Docx DFM 即時編輯系統**
  - **DFM 格式 (Docx-Flavored Markdown)** — 用 Markdown 語法即時編輯 .docx
  - **DocxIR 中間表示** — docx → IR → DFM → 編輯 → IR → docx 完整往返
  - **8 個 Docx MCP 工具**：core (4) + validator (1) + bridge (3)
  - **DocxValidator** — 6 維度往返保真驗證器（結構/文字/格式/表格/媒體/樣式）
  - **DfmTableBridge** — DFM ↔ A2T 雙向橋接
  - **DFM 規格書**：`docs/dfm-spec.md`
  - **VS Code Extension DFM 支援**：語法高亮 + Preview (37 TS tests)
  - **Pre-commit hooks**：commit-size-guard
  - **120 新測試**：test_dfm (53) + test_dfm_table_bridge (32) + test_docx_validator (35)
  - **總工具數：28 → 36**（7 modules）

## Doing

- 🚧 測試覆蓋率與品質強化（目標 60%+）

---

## Released

- ✅ **v0.3.0**: Docx DFM 即時編輯系統 (2026-02-11)
- ✅ **v0.2.14**: A2T 完整填表系統 (2026-02-10)
- ✅ **v0.2.11**: ETL Profile + DDD 架構修復 (2026-02-09)

## Next

- P1: 測試覆蓋率提升（pdf_extractor, lightrag_adapter, asset_service, job_service）
- P2: 說明文件與推廣（examples/, API Reference, FAQ）
- P3: Asset Registry
