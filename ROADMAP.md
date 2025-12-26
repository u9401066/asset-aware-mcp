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
