# Active Context

> 📌 當前工作焦點和進行中的變更

## 🎯 當前焦點

- **PyMuPDF 輕量級 PDF 後端完成測試**
- 86 個測試全數通過
- 圖片壓縮功能驗證成功
- GitHub: https://github.com/u9401066/asset-aware-mcp

## Current Goals

- 已完成 VS Code 擴充功能的安全性更新與打包。
- - TypeScript 已更新至 5.7.2，ESLint 已更新至 9.x 並切換至 flat config (eslint.config.mjs)。
- - 已生成最新的 `asset-aware-mcp-0.1.1.vsix`。
- - 已完成 Git 提交與推送。
- 下一步：考慮更新 PyPI 套件以保持 Python 核心與擴充功能同步，隨後開始 A2T 開發。

## 📝 本次變更

| 檔案/目錄 | 變更內容 |
|-----------|----------|
| `pyproject.toml` | PyMuPDF 核心, Docling 可選 |
| `src/presentation/server.py` | 直接使用 PyMuPDFExtractor |
| `src/application/document_service.py` | 動態表格來源偵測 |
| `src/domain/image_processor.py` | 圖片壓縮處理器 |
| `ROADMAP.md` | 新增「設計決策」章節 |
| `tests/` | 86 個測試全通過 |

## ⚠️ 待解決

1. **表格萃取**：測試 PDF 無表格（可能是圖片式）
2. **Knowledge Graph**：待測試 LightRAG 索引
3. **Figure caption**：`fig_2_1` 對應問題

## 💡 重要決定 (2025-12-26)

### PDF 後端選擇
- **PyMuPDF**（核心）：輕量、快速、50MB
- **Docling**（可選）：需 PyTorch + CUDA，~2GB
- 原因：「我們是輕量級旁支專案！」

### 圖片處理
- max_size: 1024px
- JPEG 品質: 85%
- 4501×5482 → 840×1024 壓縮成功

## 📁 專案結構

```
src/
├── domain/          # 🔵 核心業務邏輯
├── application/     # 🟢 使用案例
├── infrastructure/  # 🟠 外部依賴實作
└── presentation/    # 🔴 MCP Server
tests/
├── unit/            # ✅ 單元測試
└── integration/     # ✅ 整合測試
```

---
*Last updated: 2025-12-26*
