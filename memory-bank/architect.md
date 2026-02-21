# System Architect

> 📌 此檔案記錄重大架構決策，架構變更時更新。

## 🌐 系統架構圖

```
┌─────────────────────────────────────────────┐
│              專案模板結構                      │
├─────────────────────────────────────────────┤
│  🏔️ 規則層                                        │
│  ┌─────────────┐                                  │
│  │ CONSTITUTION │ ───┐                             │
│  └─────────────┘     │                             │
│        │            ▼                             │
│        │     ┌────────────┐                        │
│        ├────▶│  Bylaws   │                        │
│        │     └────────────┘                        │
│        │            │                             │
│        ▼            ▼                             │
│  ┌───────────────────────┐                      │
│  │    Claude Skills      │                      │
│  └───────────────────────┘                      │
├─────────────────────────────────────────────┤
│  🧠 記憶層                                        │
│  ┌───────────────────────┐                      │
│  │     Memory Bank       │                      │
│  │  (7 markdown files)   │                      │
│  └───────────────────────┘                      │
├─────────────────────────────────────────────┤
│  ⚙️ 工具層                                        │
│  ┌────────┐ ┌─────────┐ ┌─────────┐           │
│  │ CI/CD  │ │ Testing │ │ Linting │           │
│  └────────┘ └─────────┘ └─────────┘           │
└─────────────────────────────────────────────┘
```

## 🏛️ 架構決策紀錄

### ADR-001: 採用憲法-子法層級架構

**日期**：2025-12-15

**背景**：需要一個清晰的規則層級系統

**決定**：採用憲法 → 子法 → Skills 三層結構

**理由**：
- 最高原則集中在 CONSTITUTION.md
- 細則可在 bylaws/ 擴展
- Skills 專注於操作程序

### ADR-002: DDD + DAL 獨立

**日期**：2025-12-15

**背景**：確保業務邏輯與資料存取分離

**決定**：Repository 介面在 Domain，實作在 Infrastructure

**理由**：
- 提高可測試性
- Domain 不依賴資料庫技術
- 可替換儲存實作

### ADR-003: uv 優先套件管理

**日期**：2025-12-15

**背景**：Python 套件管理工具選擇

**決定**：優先使用 uv，後備 pip

**理由**：
- 比 pip 快 10-100 倍
- 原生支援 lockfile
- 與 pip 完全相容

### ADR-004: DFM (Docx-Flavored Markdown) 即時編輯架構

**日期**：2026-02-11

**背景**：AI Agent 無法直接讀寫 .docx 二進位格式，需要中間表示

**決定**：設計 DFM 格式 + DocxIR 中間層，實現 docx ↔ IR ↔ DFM 完整往返

**理由**：
- Agent 天然理解 Markdown，DFM 是最小學習成本的編輯界面
- IR 保留完整格式/樣式/媒體資訊，DFM 只暴露可編輯的文字結構
- Template-based rebuild（複製原始 zip → 只改 document.xml）保證非文字部分 100% 保真
- DocxValidator 6 維度驗證彌補 Agent 無法目視確認的缺陷

**架構**：
```
.docx → DocxAdapter.docx_to_ir() → DocxIR
  DocxIR → DfmRenderer.render() → DFM (Markdown)
  DFM (edited) → DfmParser.parse() → DocxIR (updated)
  DocxIR → DocxAdapter.ir_to_docx() → .docx (rebuilt)

DocxValidator.validate(original, rebuilt) → ValidationReport (6D)
DfmTableBridge: DocxIR.tables ↔ A2T TableAsset
```

## 📦 元件圖

```
.claude/skills/          # 12 個 Skills
├── git-precommit/       # 編排器
├── ddd-architect/       # 架構
├── code-refactor/       # 重構
├── code-reviewer/       # 審查
├── test-generator/      # 測試
├── memory-updater/      # 記憶
├── memory-checkpoint/   # 檢查點
├── readme-updater/      # README
├── changelog-updater/   # CHANGELOG
├── roadmap-updater/     # ROADMAP
├── project-init/        # 初始化
└── git-doc-updater/     # 文檔更新

.github/bylaws/          # 4 個子法
├── ddd-architecture.md
├── git-workflow.md
├── memory-bank.md
└── python-environment.md
```

---
*Last updated: 2025-12-15*



## Architectural Decisions

- 採用 Docling 作為主要 ETL 引擎以獲得高品質的表格與章節識別
- 使用 FastMCP 簡化 MCP Server 開發流程
- 本地優先存儲策略，所有資產保留在 ./data 目錄下



## Design Considerations

- 採用 DDD 架構確保業務邏輯與技術細節分離
- 使用非同步 Job 處理大型 PDF 以避免 MCP 逾時
- Manifest-first 策略：Agent 應先讀取清單再精準取用資產
- 支援 Base64 圖片傳輸以配合 Vision AI 分析能力



## Components

### Presentation Layer (FastMCP)

實作 MCP 協議，定義 Tools 與 Resources。使用 FastMCP 框架。

**Responsibilities:**

- 定義 ingest_documents, fetch_document_asset 等工具
- 提供 document://{id}/outline 等動態資源
- 處理 MCP 請求與回應格式轉換

### Application Layer (Services)

協調領域對象執行業務流程。處理非同步 Job 狀態。

**Responsibilities:**

- DocumentService: 協調 ETL 流程
- JobService: 管理非同步任務狀態
- AssetService: 檢索與過濾文件資產

### Domain Layer (Core)

核心業務邏輯與實體定義。定義 Repository 介面。

**Responsibilities:**

- 定義 DocumentManifest 實體與 Asset 值物件
- 定義 PDFExtractorInterface 與 KnowledgeGraphInterface 介面
- 實作 ManifestGenerator 領域服務

### Infrastructure Layer (Adapters)

外部技術實作。包含 PDF 解析與知識圖譜。

**Responsibilities:**

- DoclingAdapter: 使用 IBM Docling 進行高精度 PDF 解析
- LightRAGAdapter: 實作知識圖譜索引與查詢
- FileStorage: 處理本地檔案系統的讀寫與圖片儲存
