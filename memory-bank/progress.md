# Progress (Updated: 2026-02-21)

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
  - 8 個 Docx MCP 工具 + DocxValidator + DfmTableBridge
  - 120 新測試（DFM 53 + Bridge 32 + Validator 35）
  - 總工具數：28 → 36（7 modules）
- ✅ **v0.3.1: 分離格式 + CLI + Bug 修復**
  - Split Format: content.md + format.yaml
  - DFM CLI: `scripts/dfm_cli.py` + VS Code Tasks
  - Bug Fix: 表格文字重複修復
- ✅ **v0.3.2: Integrity Checker + 檔案層級比對 + uv 遷移**
  - DfmIntegrityChecker: 6 個檢查/修復方法 + 自動整合至 DocxService/MCP/CLI
  - DocxValidator: SHA-256 + 檔案大小 + ZIP diff
  - CI/CD: pip → uv 全面遷移
  - 271 單元測試全數通過

## Doing

- 🚧 測試覆蓋率與品質強化（目標 60%+）

---

## Released

- ✅ **v0.3.2**: Integrity Checker + 檔案層級比對 + uv 遷移 (2026-02-21)
- ✅ **v0.3.1**: 分離格式 + CLI + Bug 修復 (2026-02-21)
- ✅ **v0.3.0**: Docx DFM 即時編輯系統 (2026-02-11)
- ✅ **v0.2.14**: A2T 完整填表系統 (2026-02-10)
- ✅ **v0.2.11**: ETL Profile + DDD 架構修復 (2026-02-09)

## Next

- P1: 測試覆蓋率提升（pdf_extractor, lightrag_adapter, asset_service, job_service）
- P2: 說明文件與推廣（examples/, API Reference, FAQ）
- P3: Asset Registry
