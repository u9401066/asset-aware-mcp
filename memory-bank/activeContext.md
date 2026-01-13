# Active Context

> 📌 當前工作焦點和進行中的變更

## 🎯 當前焦點

- **🚨 v0.3.0 架構重構：三大功能獨立化**
- 解決「做表功能被迫依賴 PDF 拆解」的問題
- 解決「已存在的圖片需要重新拆解才能使用」的問題
- 實現 Asset-Centric Architecture（資產優先架構）

## Current Goals

### 當前焦點：v0.3.0 架構重構 (進行中)

**核心問題**：
1. ❌ 做表功能：用戶已有 MD 檔案，但被迫先拆解 PDF
2. ❌ 圖片使用：上次 session 已拆解的圖片，這次還要重新拆解
3. ❌ 功能耦合：三個功能（做表/拆解/重送）互相依賴

**解決方案**：Asset Registry（資產註冊中心）
- 啟動時掃描 `data/` 目錄，建立所有已存在資產的索引
- 不需要重新拆解就能使用已存在的圖片、MD 文件
- TableService 支援直接從 MD 檔案或文字內容建表

### 修改的檔案（計畫中）
- `src/domain/asset_registry.py` - **新增** 資產索引核心
- `src/application/table_service.py` - 新增 `create_table_from_*` 方法
- `src/application/asset_service.py` - 整合 AssetRegistry
- `src/presentation/server.py` - 新增 4 個 MCP Tools

### 下一步
1. Phase 1: 建立 AssetRegistry 類別
2. Phase 2: 擴展 TableService
3. Phase 3: 新增 MCP Tools
4. Phase 4: Asset Bundle 批次獲取

## 📝 本次變更

| 檔案/目錄 | 變更內容 |
|-----------|----------|
| `docs/ARCHITECTURE_REFACTOR_PROPOSAL.md` | **新增** 架構重構提案文檔 |
| `memory-bank/activeContext.md` | **更新** 當前焦點為 v0.3.0 重構 |
| `memory-bank/decisionLog.md` | **新增** 架構重構決策記錄 |

## ⚠️ 待解決

1. **Phase 1**：建立 AssetRegistry 類別（掃描現有資產）
2. **Phase 2**：TableService 支援 `create_table_from_text()` 和 `create_table_from_files()`
3. **Phase 3**：新增 4 個 MCP Tools
4. **Phase 4**：實作 Asset Bundle 批次獲取

## 💡 重要決定 (2026-01-12)

### 架構重構：Asset-Centric Architecture
- **為何需要？**：用戶反映三大功能（做表/拆解/重送）存在不必要的耦合
- **核心變更**：新增 AssetRegistry 作為資產索引中心
- **預期效果**：
  - 做表功能可直接從 MD 檔案建表，不需先拆解 PDF
  - 已存在的圖片可直接使用，不需重新拆解
  - 三個功能完全獨立，互不影響

## 📁 專案結構

```
src/
├── domain/          # 🔵 核心業務邏輯 (新增 TableDraft)
├── application/     # 🟢 使用案例 (新增 TableService Draft 邏輯)
├── infrastructure/  # 🟠 外部依賴實作 (Excel 渲染, PDF 提取)
└── presentation/    # 🔴 MCP Server (A2T 2.0 Tools)
```

---
*Last updated: 2026-01-06*
