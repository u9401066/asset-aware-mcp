# Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-18 | **`marker-pdf` 改為 optional extra，預設安裝不帶 torch** | `Marker` 是高精度但重量級的可選功能，會帶入 `torch` / `surya` 與平台相關 wheels，最容易造成安裝失敗。預設安裝改為只保留 PyMuPDF，可顯著降低 cross-platform 安裝摩擦；需要 `use_marker=True` 時再透過 `uv sync --extra marker` 或 extension 設定明確啟用。 |
| 2026-03-18 | **不收窄 package 的 Python 3.11+ 支援宣告，只固定 extension / installer runtime 為 Python 3.11** | 使用者要求保留 3.11+ 支援。真正的啟動問題不是專案邏輯不支援新版 Python，而是終端使用者機器在 `uvx` 自動選到 3.14 時，`marker-pdf -> regex` 依賴鏈可能觸發本機原生編譯。將 extension / installer 固定到 wheel 可用性最佳的 3.11，可同時保留專案相容性與跨平台穩定啟動。 |
| 2026-03-09 | **DOCX→PDF / DOCX→DOC 採保真模式，PDF→DOCX 採內容重建模式** | DOCX 來源具可逆結構，適合透過 LibreOffice 做 fidelity export；PDF ETL 不具版面可逆性，因此僅承諾可讀內容重建，不宣稱 layout fidelity。 |
| 2026-03-09 | **strict round-trip 採 fail-closed 策略** | 對生產級文件編輯流程，任何結構、文字、格式、表格、媒體、樣式差異都應明確視為失敗，避免只靠總分掩蓋回歸。 |
| 2026-03-09 | **save_docx 加入 unedited block mutation guard** | 真實 Proposal 文件測試證明 parser/render 流程若誤動未編輯區塊，必須立即中止寫回，避免 silent corruption。 |
| 2026-02-23 | **`.doc` 格式支援 — LibreOffice 自動轉換** | 使用者需要編輯舊版 `.doc` 檔案，DFM 僅支援 `.docx`。透過 `subprocess` 呼叫 LibreOffice headless 模式自動轉換，無需使用者手動操作。轉換後的 `.docx` 存於 tempdir 避免污染原始目錄。 |
| 2026-02-23 | **Markdown 跳脫機制 (`_escape_md` / `_unescape_md`)** | 文字內容含 `*`、`~`、`^` 字元時，Round-trip 會被 Markdown 格式標記干擾（如 `※**下列` 中的 `**`）。新增跳脫/反跳脫對稱方法，並合併相鄰同格式 runs 避免 `**A****B**` 問題。 |
| 2026-02-11 | DFM (Docx-Flavored Markdown) 格式設計 | Agent 無法直接看 docx，需要 Markdown 中間格式即時編輯。DFM 保留 block-level 與 run-level 格式資訊，支援完整往返 |
| 2026-02-11 | DocxIR 中間表示層 | docx → IR → DFM → edit → IR → docx 保證往返保真。IR 保留原始 preserved_parts、assets、styles、checksum |
| 2026-02-11 | DocxValidator 6 維度驗證 | Agent 看不到渲染結果，需程式化驗證。6 維度加權評分（text 0.35 最重）取代肉眼對比 |
| 2026-02-11 | DfmTableBridge 雙向橋接 | Docx 表格 → A2T 工作流（plan → draft → commit）→ Docx 表格，打通兩個子系統 |
| 2026-02-11 | Template-based rebuild (複製 original → 只改 document.xml) | 最大限度保留 media/styles/theme/fonts 等，非文字部分保真率極高 |
| 2026-02-10 | A2T 工具合併 19→7 (operation-based) | 減少工具總量 28%，降低 Agent 認知負擔，用 Literal type 統一入口 |
| 2026-02-10 | AssetRef 支援 7 種來源類型 | 做表 ≠ 拆解，表格應接受任意來源（PDF/KG/URL/口述） |
| 2026-02-10 | Citation 作為平行附加層 | 不改變 rows list[dict] 結構，用 dict[str, CellCitation] 側掛 |
| 2026-02-10 | ChangeEntry 自動審計 | 所有寫入操作自動記錄，支援 cell-level 歷史追溯 |
| 2026-02-10 | get_section_content 移至 section_tools | 語意上屬於 section 導航，不應在 table_tools |
| 2025-12-15 | 採用憲法-子法層級架構 | 類似 speckit 的規則層級，可擴展且清晰 |
| 2025-12-15 | DDD + DAL 獨立架構 | 業務邏輯與資料存取分離，提高可測試性 |
| 2025-12-15 | Skills 模組化拆分 | 單一職責，可組合使用，易於維護 |
| 2025-12-15 | Memory Bank 與操作綁定 | 確保專案記憶即時更新，不遺漏 |

---

## [2025-12-15] 採用憲法-子法層級架構

### 背景
需要一個清晰的規則層級系統，類似 speckit 但可擴展。

### 選項
1. 單一 copilot-instructions.md - 簡單但不夠靈活
2. 憲法 + 子法層級 - 清晰層級，可擴展
3. 全部放在 Skills 內 - 分散，難以管理

### 決定
採用選項 2：憲法-子法層級

### 理由
- 最高原則集中在 CONSTITUTION.md
- 細則可在 bylaws/ 擴展
- Skills 專注於操作程序
- 符合現實法律體系，易理解

### 影響
- 新增 CONSTITUTION.md
- 新增 .github/bylaws/ 目錄
- Skills 需引用相關法規
| 2025-12-26 | 使用 Ollama 作為預設 LLM 後端 | 1. 本地運行，無需 API Key 成本
2. 支援 qwen2.5:7b (LLM) 和 nomic-embed-text (Embedding)
3. 隱私保護，資料不離開本機
4. 仍保留 OpenAI 作為備選後端 |
| 2025-12-26 | Figure caption mapping 需要實作 - 目前 fig_{page}_{index} 命名未對應實際圖說 | 測試 Nobel Prize PDF 時發現 fig_2_1 實際對應 "Figure 1. Regulation of cell-type specific functions"，系統缺乏 caption 解析功能。未來版本應在 ETL 階段提取圖說文字，建立 asset_id 到 caption 的映射。 |
| 2025-12-26 | mcp-operator skill 必須明確警告：純文字 AI 無法分析 base64 圖片 | 測試時發現純文字 AI 會根據「標準知識」猜測圖片內容而非實際分析，導致錯誤答案。必須在 skill 中明確禁止這種行為，要求 agent 誠實告知使用者其視覺能力限制。 |
| 2026-01-05 | 升級 Node.js 環境至 v20 並完成 VS Code 擴充功能打包 | 原環境 Node.js v12 不支援現代 JavaScript 語法（如 ?? 運算子），導致 npm install 失敗。升級至 v20 後成功編譯並生成 .vsix 檔案，確保擴充功能可供安裝。 |
| 2026-01-05 | 全面對齊文件至 Docling-based Asset-Aware ETL 實作 | 專案已從初始的「Medical RAG」想法演進為具體的「Asset-Aware ETL」架構，使用 Docling 作為核心引擎。為了避免開發者與使用者混淆，必須將 README、Spec 與擴充功能說明全面更新，反映當前的 DDD 架構、非同步 Job 處理與 Manifest 優先的資料存取模式。 |
| 2026-01-05 | 捨棄 Docling 引擎，改以 PyMuPDF 作為核心 ETL 引擎 | Docling 雖然精度高但依賴過重（約 2GB，需 PyTorch/CUDA），不符合專案輕量化的需求。PyMuPDF (fitz) 速度快、體積小，且已實作表格與圖片提取功能，足以滿足當前 Asset-Aware ETL 的核心需求。 |
| 2026-01-12 | **🚨 架構重構：Asset-Centric Architecture** | 用戶反映三大功能存在耦合問題：(1) 做表被迫依賴 PDF 拆解、(2) 已存在的圖片需重新拆解、(3) 功能間互相影響。決定引入 AssetRegistry 作為資產索引中心，實現真正的功能獨立。詳見 `docs/ARCHITECTURE_REFACTOR_PROPOSAL.md`。 |
| 2026-02-03 | **Marker 整合到標準 ingest 流程** | 為支援精確來源追蹤（頁碼+bbox），將 Marker 整合到 `ingest_documents` tool 中。新增 `use_marker=True` 參數，可選擇：(1) PyMuPDF（預設、快速）或 (2) Marker（結構化、含 blocks.json）。Marker 採用 lazy-load 避免啟動延遲。研究 Unstructured.io (13.9k stars) 作為未來備選方案，但目前 Marker 已足夠。 |
| 2026-02-05 | **Section Navigation Tools (動態層級)** | 為支援任意深度的書籍章節結構，實作 SectionNode/SectionTree domain model 和 SectionService。新增 4 個 MCP tools: `list_section_tree`, `get_section_detail`, `get_section_blocks`, `search_sections`。不 hardcode 層級數，從 blocks.json 動態建構 section hierarchy。 |
| 2026-02-09 | **ETL Profile 設定模組化** | ETL 管線中大量硬編碼常數（字型閾值、heading noise patterns、caption patterns、section keywords 等），不同期刊格式需不同設定。決定採用「兩者並行」策略：Python dataclass 定義預設值 + JSON 檔案可覆蓋。`ETLProfile` 為 frozen dataclass（domain value object），`ETLProfileRegistry` 提供 5 個內建預設。DI 鏈：`dependencies.py` 建立共享 profile → `PyMuPDFExtractor(profile=)` + `ManifestGenerator(profile=)`。 |
| 2026-02-09 | **Marker ETL 規格書與缺陷修復** | 建立完整規格書 `docs/marker-etl-spec.md`，定義品質要求（QM/QF/QT/QI/QS/QB/QST/QMT/QE），修復 3 個實作缺陷：(1) Figure-Block 匹配 bug — 改為 index-based 1:1 匹配而非全部用第一個、(2) Table row/col 解析 — 從 markdown 表格文字解析實際行列數、(3) 圖片尺寸讀取 — 使用 PIL 取得實際 width/height。新增 89 個單元測試全部通過。 |
