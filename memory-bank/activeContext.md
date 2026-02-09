# Active Context

> 📌 當前工作焦點和進行中的變更

## 🎯 當前焦點

- **v0.2.9 已完成**：ETL 缺陷修復、路徑統一、文件同步
- **🚧 P0 server.py 模組化拆分**：2122 行 → 子模組（骨架已建立）
- **🚧 v0.3.0 架構重構**：Asset-Centric Architecture

## 已完成的工作 (v0.2.9)

### ETL 缺陷修復（3 個 bug）
1. **Figure-Block 匹配** — 改為 index-based 1:1 匹配
2. **Table row/col** — 從 markdown 解析實際行列數
3. **圖片尺寸** — 使用 PIL 取得實際 width/height

### 路徑慣例統一
- `SectionService`, `server.py`: `data/sources/{doc_id}/` → `data/{doc_id}/`
- `marker_adapter.py`: 原始 hashlib.md5 → `DocId.generate()`

### 文件同步
- 更新 `copilot-instructions.md`, `CLAUDE.md`, `AGENTS.md`, `pdf-asset-extractor/SKILL.md`
- 更新 `README.md`, `README.zh-TW.md` 反映雙引擎 + Section Navigation
- 更新 `CHANGELOG.md` v0.2.9 完整條目
- 更新 `ROADMAP.md` v0.2.8 + v0.2.9 完成項

### Presentation 層重構骨架
- `src/presentation/mcp_app.py` — FastMCP 實例工廠
- `src/presentation/dependencies.py` — Composition Root (DI 容器)
- `src/presentation/tools/document_tools.py` — 文件工具（已完成）
- `src/presentation/tools/__init__.py`, `resources/__init__.py` — 子模組結構

### 測試
- 171 個單元測試全部通過 ✅
- 涵蓋：marker_blocks, marker_conversion, section_tree, section_service

## 進行中

### P0: server.py 模組化拆分
- **目標**：2122 行 → 瘦入口 + 7 個子模組
- **已完成**：`mcp_app.py`, `dependencies.py`, `tools/document_tools.py`
- **待完成**：
  - `tools/section_tools.py` — 4 個 Section Navigation 工具
  - `tools/knowledge_tools.py` — KG 查詢 + 匯出
  - `tools/table_tools.py` — 19 個 A2T 工具
  - `tools/job_tools.py` — Job 管理 3 工具
  - `resources/document_resources.py` — 文件相關 Resources
  - `resources/table_resources.py` — 表格相關 Resources
  - 重寫 `server.py` 為瘦入口

### v0.3.0: Asset-Centric Architecture
- Phase 1: 建立 AssetRegistry 類別
- Phase 2: 擴展 TableService
- Phase 3: 新增 MCP Tools

## ⚠️ 待解決

1. **P0**: 完成 server.py 拆分
2. **P1**: 抽取 document_service ↔ marker_adapter 共用程式碼
3. **小圖過濾**：Marker 產出的圖片中過濾 <50px 的小圖標

## 📁 專案結構

```
src/
├── domain/          # 🔵 核心業務邏輯
├── application/     # 🟢 使用案例
├── infrastructure/  # 🟠 外部依賴實作
└── presentation/    # 🔴 MCP Server
    ├── mcp_app.py        # FastMCP 實例
    ├── dependencies.py   # Composition Root
    ├── server.py         # 主入口（待拆分）
    ├── tools/            # MCP 工具（部分完成）
    └── resources/        # MCP 資源（待完成）
```

---
*Last updated: 2026-02-09*
