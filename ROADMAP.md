# Roadmap

專案發展路線圖與功能規劃。

## 已完成 ✅

### v0.2.7 (2026-01-06) - 圖片擷取策略優化
- [x] 三層級圖片擷取策略 (XObject, Vector Clustering, Grid Scanning)
- [x] VS Code Extension 路徑修復
- [x] A2T 表格視圖與 Excel 導出

### v0.2.0 (2026-01-05) - A2T 2.0 & PyMuPDF 輕量化
- [x] A2T (Anything to Table) 核心實作
- [x] Draft 草稿系統（斷點續傳）
- [x] Token 估算工具
- [x] Section-level 快取讀取
- [x] Excel 自動美化渲染
- [x] 輕量化 ETL 引擎 (PyMuPDF)
- [x] Ruff 程式碼品質修復
- [x] VS Code Extension 升級 (v0.2.6: 新增表格視圖與路徑修復)

### v0.1.1 (2025-12-26) - 正式發布
- [x] 專案初始化
- [x] Memory Bank 系統建立
- [x] DDD 分層架構實作
- [x] MCP Server 5 Tools 實作
- [x] ImageContent 修復 (Vision AI 可看圖)

## 進行中 🚧

### v0.3.0 - Asset-Centric Architecture（架構重構）
> 🚨 **重大重構**：解決三大功能耦合問題

**核心問題**：
- ❌ 做表功能被迫依賴 PDF 拆解
- ❌ 已存在的圖片需重新拆解才能使用
- ❌ 三個功能（做表/拆解/重送）互相影響

**Phase 1: Asset Registry（資產註冊中心）**
- [ ] 新增 `AssetRegistry` 類別
- [ ] 啟動時掃描 `data/` 目錄建立索引
- [ ] 追蹤所有已存在資產（MD、圖片、表格）

**Phase 2: TableService 擴展**
- [ ] 新增 `create_table_from_text()` - 直接從文字建表
- [ ] 新增 `create_table_from_files()` - 從 MD 檔案建表
- [ ] 支援多檔案合併彙整

**Phase 3: 新增 MCP Tools**
- [ ] `list_available_assets` - 列出所有已存在資產
- [ ] `get_existing_image` - 直接讀取已存在圖片
- [ ] `create_table_from_markdown` - 從 MD 建表
- [ ] `create_table_from_text` - 從文字建表

**Phase 4: Asset Bundle**
- [ ] `get_asset_bundle` - 批次獲取多種資產
- [ ] Token 消耗優化

**詳見**: [docs/ARCHITECTURE_REFACTOR_PROPOSAL.md](docs/ARCHITECTURE_REFACTOR_PROPOSAL.md)

## 設計決策 💡

### PDF 後端選擇 (2025-12-26)

**決策：PyMuPDF 作為唯一核心依賴，Docling 保留為可選**

**理由：**
- 🎯 **輕量優先**：本專案定位為輕量級旁支工具，不是重型 AI 平台
- 📦 **依賴地獄**：Docling 拉入 PyTorch + ONNX (~2GB)，對多數用例過重
- ⚡ **夠用就好**：PyMuPDF 的 `find_tables()` 對學術 PDF 已足夠
- 🔌 **接口預留**：`docling_adapter.py` 保留，未來需要高精度表格識別時可啟用

**安裝選項：**
```bash
uv sync              # 預設：PyMuPDF only (~50MB)
uv sync -E docling   # 進階：+ Docling (~2GB)
```

---

## 計劃中 📋

### v0.4.0 - 知識圖譜強化
- [ ] LightRAG 索引問題修復
- [ ] 跨文件知識查詢
- [ ] Figure Caption 自動提取
- [ ] 表格偵測優化

### v0.5.0 - 進階功能
- [ ] Mistral OCR 整合 (高保真度解析)
- [ ] CI/CD 流程建立
- [ ] 醫學術語 NER
- [ ] 效能優化

### v0.6.0 - 批量與報告
- [ ] 多文件比較功能
- [ ] 自動報告生成
- [ ] 批量處理優化

### v1.0.0 - 正式版
- [ ] 完整醫學文獻 RAG 系統
- [ ] 多語言支援
- [ ] Docker 部署
- [ ] Web UI 介面
