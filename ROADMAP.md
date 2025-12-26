# Roadmap

專案發展路線圖與功能規劃。

## 已完成 ✅

### v0.0.1 (2025-12-26) - 基礎架構
- [x] 專案初始化
- [x] Memory Bank 系統建立
- [x] DDD 分層架構實作
  - [x] Domain Layer (Entities, Value Objects, Services)
  - [x] Application Layer (Document, Asset, Knowledge Services)
  - [x] Infrastructure Layer (FileStorage, PDFExtractor, LightRAG)
  - [x] Presentation Layer (MCP Server)
- [x] 單元測試 (45 tests)
- [x] MCP Server 5 Tools 實作

## 進行中 🚧

### v0.1.0 - MVP 發布
- [ ] 整合測試 (ETL Pipeline)
- [ ] E2E 測試 (MCP Server)
- [ ] README 完整安裝指南
- [ ] 測試用 PDF 樣本

## 計劃中 📋

### 短期目標 (v0.2.0)
- [ ] Mistral OCR 整合 (高保真度解析)
- [ ] 表格偵測優化
- [ ] 圖片 Caption 自動提取
- [ ] CI/CD 流程建立

### 中期目標 (v0.3.0)
- [ ] LightRAG 知識圖譜完整整合
- [ ] 多文件比較功能
- [ ] 醫學術語 NER
- [ ] 效能優化

### 長期目標 (v1.0.0)
- [ ] 完整醫學文獻 RAG 系統
- [ ] 自動報告生成
- [ ] 多語言支援
- [ ] Docker 部署
