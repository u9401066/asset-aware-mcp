<!-- Generated from Home.md by scripts/build_docs_site.py -->

# Asset-Aware MCP Docs

Asset-Aware MCP 是給 AI agents 使用的 citation-ready 文件工作流伺服器。它把
PDF、DOCX/DFM、表格、圖片、section、citation index、Foam evidence pack 與選用
KG/RAG 串成可驗證的文件流程。

章節導覽依任務整理；本份文件對應 `2.0.0`。正式發布狀態以
[GitHub Releases](https://github.com/u9401066/asset-aware-mcp/releases) 為準。

## 進行中的產品方向

目標是 Agent 跨格式文件 CRUD、獨立表格創造與 wikilink 證據庫。
MCP 提供來源／版本、格式與操作結果的必要檢查；Agent 負責完整核對與修正。
現有 PDF、DOCX/DFM、A2T 與可攜資產保留來源；原生試算表／簡報 CRUD 等仍在擴充。

## 2.0.0 highlights

- 原生 PPTX 建立、形狀／備註讀取與精確文字修改，版本引用與 Wiki 保留完整套件附件。
- contract 改為可分段規格：先看 schema_delivery，用 for_op 或 hash-pinned schema_request。
- 舊 XLSX／DOCX 證據不變；Agent 核對語意、版面、繼承格式與溢出。詳見 [Native File Assets](#/native-file-assets)。
- Codex 實測掃描 PDF → 表格 CRUD／引用／Excel；旋轉裁切有像素回歸，詳見 [Release And Testing](#/release-testing)。

## 1.2.0 highlights

- 原生引用驗證與 XLSX/XLSM wiki 快照保留固定版本、完整 cell reference 與來源附件；
  自訂引用顯示保持獨立，詳見 [Native File Assets](#/native-file-assets)。
- 原生快照不覆寫既有筆記；PDF bundle 重匯出核對清單與 hash，更新時保留備份。
  固定資產 ID、獨立 XLSX 建立與局部編輯持續支援；完整 CSL 仍待實作。
- MCP SDK 2.2.0；必要結構檢查與確定性修復由 MCP 執行，語意、畫面、公式結果由 Agent 核對。

## 1.0.0 foundation

- 官方 MCP Python SDK `>=2,<3` 與 `MCPServer`，30 個 public tools 不外露 runtime context。
- PDF preflight 在隔離程序判斷 OCR／引擎路線，保留頁碼、座標與來源 SHA-256。
- 可攜式 agent-asset bundle 保留完整紀錄、圖文表、citation locator 與 Foam notes。
- 混合文件攝入、結構導覽與 citation audit；PyMuPDF4LLM / Docling 可用，
  MinerU / Marker 因相依安全限制維持暫停。

<div class="path-grid">
  <section class="path-card">
    <p class="card-kicker">Path 1</p>
    <h3>先跑起來</h3>
    <p>安裝、設定 MCP client、檢查 runtime、確認 VS Code extension 或 stdio server 可用。</p>
    <p><a href="#/getting-started">快速開始</a> · <a href="#/vs-code-extension">VSIX / MCP 設定</a></p>
  </section>
  <section class="path-card">
    <p class="card-kicker">Path 2</p>
    <h3>選文件流程</h3>
    <p>PDF、章節導覽、DOCX/DFM、A2T table 先分流，不混在同一頁。</p>
    <p><a href="#/workflow-chapters">流程章節</a> · <a href="#/pdf-workflow">PDF</a> · <a href="#/docx-dfm-workflow">DOCX</a></p>
  </section>
  <section class="path-card">
    <p class="card-kicker">Path 3</p>
    <h3>建立可驗證證據</h3>
    <p>所有 claim 都回到 span、locator、hash、context 與 citation bundle；LLM wiki 是呈現層。</p>
    <p><a href="#/citation-provenance">引用與證據</a> · <a href="#/llm-wiki">LLM Wiki</a> · <a href="#/knowledge-graph">KG</a></p>
  </section>
  <section class="path-card">
    <p class="card-kicker">Path 4</p>
    <h3>維運、reference 與上線 gates</h3>
    <p>長任務、ETL profile、精確 tool/resource contract、code 位置、release 檢查集中在這條路徑。</p>
    <p><a href="#/tool-chooser">Tool Chooser</a> · <a href="#/mcp-tools">MCP Tools</a> · <a href="#/release-testing">Release</a></p>
  </section>
</div>

## 最短路徑

| 你要做什麼 | 先讀 | 然後讀 |
|---|---|---|
| 第一次安裝 | [快速開始](#/getting-started) | [VS Code Extension And MCP Setup](#/vs-code-extension) |
| 處理 PDF | [流程章節](#/workflow-chapters) | [PDF Document Workflow](#/pdf-workflow) |
| 匯出 agent assets | [PDF Document Workflow](#/pdf-workflow) | [LLM Wiki Knowledge Base](#/llm-wiki) |
| 找章節與定位 | [Document Sections And Navigation](#/document-sections) | [Citation Provenance](#/citation-provenance) |
| 編輯 Word / DFM | [流程章節](#/workflow-chapters) | [DOCX DFM Workflow](#/docx-dfm-workflow) |
| 產出引用結論 | [Citation Provenance](#/citation-provenance) | [LLM Wiki Knowledge Base](#/llm-wiki) |
| 建立 LLM wiki | [LLM Wiki Knowledge Base](#/llm-wiki) | [Knowledge Graph](#/knowledge-graph) |
| 做表格 | [A2T Tables](#/a2t-tables) | [DOCX DFM Workflow](#/docx-dfm-workflow) |
| 查完整 API | [Tool Chooser](#/tool-chooser) | [MCP Tools](#/mcp-tools) |
| 追背景任務或 ETL | [Background Jobs](#/background-jobs) | [ETL Profiles](#/etl-profiles) |
| 準備發布 | [Release And Testing](#/release-testing) | [Git Harness Hygiene](#/git-harness-hygiene) |

## Code 對齊

網站內容由 `docs/wiki/**` 產生到 GitHub Pages payload。工具與 resource 數量來自
`src/presentation/tools/**`、`src/presentation/resources/**`，並由
`tests/unit/test_docs_site_reference_sync.py` 檢查 reference、metadata、連結與 endpoint 統計。
