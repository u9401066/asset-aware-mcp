# Roadmap

專案發展路線圖與功能規劃。

## 已完成 ✅

### v0.2.0 (2026-01-05) - A2T 2.0 & PyMuPDF 輕量化
- [x] A2T (Anything to Table) 核心實作
- [x] Draft 草稿系統（斷點續傳）
- [x] Token 估算工具
- [x] Section-level 快取讀取
- [x] Excel 自動美化渲染
- [x] 輕量化 ETL 引擎 (PyMuPDF)
- [x] Ruff 程式碼品質修復
- [x] VS Code Extension 升級

### v0.1.1 (2025-12-26) - 正式發布
- [x] 專案初始化
- [x] Memory Bank 系統建立
- [x] DDD 分層架構實作
- [x] MCP Server 5 Tools 實作
- [x] ImageContent 修復 (Vision AI 可看圖)

## 進行中 🚧

### v0.3.0 - 知識圖譜強化 & 跨文件分析
- [ ] LightRAG 索引問題修復
- [ ] 跨文件知識查詢
- [ ] Figure Caption 自動提取
- [ ] 表格偵測優化

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

### 短期目標 (v0.4.0)
- [ ] Mistral OCR 整合 (高保真度解析)
- [ ] CI/CD 流程建立
- [ ] 醫學術語 NER
- [ ] 效能優化

### 中期目標 (v0.5.0)
- [ ] 多文件比較功能
- [ ] 自動報告生成
- [ ] 批量處理優化

### 長期目標 (v1.0.0)
- [ ] 完整醫學文獻 RAG 系統
- [ ] 多語言支援
- [ ] Docker 部署
- [ ] Web UI 介面
