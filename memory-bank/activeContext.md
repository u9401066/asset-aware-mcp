# Active Context

> 📌 當前工作焦點和進行中的變更

## 🎯 當前焦點

- **v0.2.11 已發布**：ETL Profile + DDD 架構修復
- **🚧 v0.3.0 架構重構**：Asset-Centric Architecture

## 已完成的工作 (v0.2.11)

### ETL Profile 系統
1. **ETL Profile 實體** — `ETLProfile` frozen dataclass + `ETLProfileRegistry`
2. **5 內建預設** — default, arxiv, nature, ieee, elsevier
3. **JSON 覆蓋** — `profiles/*.json` 支援繼承與自訂
4. **5 MCP Profile Tools** — list/get/get_current/set/load_from_json
5. **VSCode 整合** — 設定面板 + 環境變數支援

### DDD 架構修復
1. **JobStoreInterface** — 從 infrastructure 移至 domain/repositories.py
2. **TableRendererInterface** — 新增抽象介面
3. **TableService DI** — 重構為依賴注入建構子
4. **rebuild_for_profile()** — 封裝 profile 切換邏輯

### 測試
- **268 測試**全部通過（203 unit + 65 E2E）
- 新增 32 個 ETLProfile 單元測試

## 進行中

### v0.3.0: Asset-Centric Architecture
- Phase 1: 建立 AssetRegistry 類別
- Phase 2: 擴展 TableService
- Phase 3: 新增 MCP Tools

## ⚠️ 待解決

1. **P1**: 抽取 document_service ↔ marker_adapter 共用程式碼
2. **Domain exports 補齊**: `domain/__init__.py` 有 17 個 symbols 未匯出（cosmetic）

## 📁 專案結構

```
src/
├── domain/          # 🔵 核心業務邏輯 (10 files, 2760 lines)
├── application/     # 🟢 使用案例 (6 files, 2255 lines)
├── infrastructure/  # 🟠 外部依賴實作 (8 files, 2347 lines)
└── presentation/    # 🔴 MCP Server (39 tools in 6 modules, 12 resources)
    ├── mcp_app.py        # FastMCP 實例
    ├── dependencies.py   # Composition Root
    ├── server.py         # 31 行 thin entry point
    ├── tools/            # 6 模組 (document, section, job, knowledge, table, profile)
    └── resources/        # 2 模組
```

---
*Last updated: 2026-02-09*
