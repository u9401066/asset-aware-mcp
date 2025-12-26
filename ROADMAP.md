# Roadmap

專案發展路線圖與功能規劃。

## 已完成 ✅

### v0.2.0 (2025-12-26) - 正式發布
- [x] 專案初始化
- [x] Memory Bank 系統建立
- [x] DDD 分層架構實作
  - [x] Domain Layer (Entities, Value Objects, Services)
  - [x] Application Layer (Document, Asset, Knowledge Services)
  - [x] Infrastructure Layer (FileStorage, PDFExtractor, LightRAG)
  - [x] Presentation Layer (MCP Server)
- [x] 單元測試 + 整合測試 (55 tests)
- [x] MCP Server 5 Tools 實作
- [x] ImageContent 修復 (Vision AI 可看圖)
- [x] GitHub 發布
- [x] README 完整安裝指南
- [x] 多 PDF 測試 (Nobel Prize 2024/2025, Attention Paper)

## 進行中 🚧

### v0.3.0 - 知識圖譜強化
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
