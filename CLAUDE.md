# CLAUDE.md - Claude Code 專案指引

此文件為 Claude Code（Anthropic 的 AI 編程助手）提供專案上下文。
當使用 Claude Code 時，它會自動讀取此文件以了解專案規範。

---

## 專案概述

這是一個 **MCP Server — Asset-Aware Medical RAG**，用於：
- 📄 PDF 文件拆解（圖片、表格、章節提取）
- 📊 A2T（Anything to Table）表格建立
- 🔍 跨文獻知識圖譜（LightRAG）
- 🖼️ Vision AI 圖片分析

**技術架構**：
- 憲法-子法層級規則系統
- Claude Skills 模組化技能
- Memory Bank 專案記憶
- DDD + DAL 獨立架構
- 雙引擎 PDF 解析：PyMuPDF（快速）+ Marker（高精度）
- Section Navigation：動態層級章節導航

## 法規層級

```
CONSTITUTION.md          ← 最高原則（不可違反）
  │
  ├── .github/bylaws/    ← 子法（細則規範）
  │     ├── ddd-architecture.md
  │     ├── git-workflow.md
  │     └── memory-bank.md
  │
  └── .claude/skills/    ← 實施細則（操作程序）
```

## 核心原則

### 0. 開發哲學 💡
> **「想要寫文件的時候，就更新 Memory Bank 吧！」**
> 
> **「想要零散測試的時候，就寫測試檔案進 tests/ 資料夾吧！」**

- 不要另開檔案寫筆記，直接寫進 Memory Bank
- 今天的零散測試，就是明天的回歸測試

### 1. DDD 架構
- Domain Layer 不依賴外部
- DAL (Data Access Layer) 必須獨立
- 使用 Repository Pattern
- 參見：`.github/bylaws/ddd-architecture.md`

### 2. Python 環境（uv 優先）
```bash
# 初始化
uv venv && uv sync --all-extras

# 安裝依賴
uv add package-name
uv add --dev pytest ruff mypy
```
- 參見：`.github/bylaws/python-environment.md`

### 3. Memory Bank 同步
每次重要操作必須更新：
- `memory-bank/progress.md` - 進度追蹤
- `memory-bank/activeContext.md` - 當前焦點
- `memory-bank/decisionLog.md` - 重要決策

### 4. Git 工作流
提交前執行檢查清單：
1. Memory Bank 同步
2. README 更新（如需要）
3. CHANGELOG 更新
4. ROADMAP 標記

## 可用 Skills

| Skill | 用途 |
|-------|------|
| `git-precommit` | Git 提交前編排器 |
| `git-doc-updater` | Git 提交前文檔同步 |
| `ddd-architect` | DDD 架構輔助 |
| `code-refactor` | 主動重構與模組化 |
| `memory-updater` | Memory Bank 同步 |
| `memory-checkpoint` | 記憶檢查點（Summarize 前外部化） |
| `readme-updater` | README 智能更新 |
| `readme-i18n` | README 多語言同步（中英對照） |
| `changelog-updater` | CHANGELOG 自動更新 |
| `roadmap-updater` | ROADMAP 狀態追蹤 |
| `code-reviewer` | 程式碼審查 |
| `test-generator` | 測試生成（Unit/Integration/E2E） |
| `project-init` | 專案初始化 |
| `pdf-asset-extractor` | PDF→圖文分解+知識圖譜 |

## 💸 Memory Checkpoint 規則

### 主動觸發時機
- 對話超過 **10 輪** 時，主動建議 checkpoint
- 完成 **重大功能** 後，主動執行 checkpoint
- 使用者說要 **離開/等等繼續** 時，主動執行 checkpoint

### Checkpoint 內容必須包含
- 具體檔案路徑
- 變更摘要
- 下一步計畫
- 重要決策（如有）

### 觸發指令
```
「記憶檢查點」 / 「checkpoint」 / 「存檔」
「保存記憶」 / 「sync memory」
```

## 常用指令

```
「準備 commit」       → 執行完整提交流程
「快速 commit」       → 只同步 Memory Bank
「建立新功能 X」      → 生成 DDD 結構
「review 程式碼」     → 程式碼審查
「更新 memory bank」  → 同步專案記憶
```

## 目錄結構約定

```
src/
├── domain/           # 核心領域（純業務邏輯，無外部依賴）
│   ├── entities.py        # Document, Asset, Section 等核心實體
│   ├── table_entities.py  # A2T 表格相關實體
│   ├── section_tree.py    # SectionTree 章節樹結構
│   ├── chunking.py        # 文本分塊策略
│   └── repositories.py    # Repository 介面定義
├── application/      # 應用層（用例編排）
│   ├── document_service.py  # ETL 文件處理（雙引擎）
│   ├── table_service.py     # A2T 表格服務
│   ├── section_service.py   # 章節導航服務
│   ├── asset_service.py     # 資產查詢服務
│   ├── knowledge_service.py # 知識圖譜服務
│   └── job_service.py       # 非同步工作管理
├── infrastructure/   # 基礎設施（DAL、外部服務）
│   ├── file_storage.py      # 檔案儲存 Repository 實作
│   ├── pdf_extractor.py     # PyMuPDF 快速提取
│   ├── marker_adapter.py    # Marker 高精度提取
│   ├── excel_renderer.py    # Excel 渲染
│   ├── lightrag_adapter.py  # LightRAG 知識圖譜
│   └── config.py            # 配置管理
└── presentation/     # 呈現層（MCP Server）
    └── server.py            # FastMCP 工具/資源註冊
```

## 注意事項

- 修改程式碼前先更新規格文檔
- 程式碼是文檔的「編譯產物」
- 遵循 Conventional Commits 格式
- 使用繁體中文回應
