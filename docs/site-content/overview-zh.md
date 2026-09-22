<!-- Generated from Home.md by scripts/build_docs_site.py -->

# Asset-Aware MCP Docs

Asset-Aware MCP 是給 AI agents 使用的 citation-ready 文件工作流伺服器。它把
PDF、DOCX/DFM、表格、圖片、section、citation index、Foam evidence pack 與選用
KG/RAG 串成可驗證的文件流程。

章節導覽依任務整理；本份文件對應 `1.4.1`。正式發布狀態以
[GitHub Releases](https://github.com/u9401066/asset-aware-mcp/releases) 為準。

## 進行中的產品方向

目標是 Agent 跨格式文件 CRUD、獨立表格創造與 wikilink 證據庫。
MCP 提供來源／版本、格式與操作結果的必要檢查；Agent 負責完整核對與修正。
1.4.1 整合了 PDF、DOCX、試算表、CSV／TSV 與 PPTX 的指定原生
操作，引用與 Wiki 保留來源版本；獨立圖片亦有影格／區域、衍生檔、候選版本
修改及 Wiki，並以真實 PDF 衍生圖片完成實際 Codex 核對。
版本維持 **1.4.x**，累積驗證後整合發布，不隨單一功能跳版。詳見
[能力與缺口分析](https://github.com/u9401066/asset-aware-mcp/blob/main/docs/agent-asset-gap-analysis.md)。

## 1.4.1 highlights

- PDF 頁面／區域、批註與表單欄位；DOCX 格網、頁首頁尾、註腳／尾註；PPTX 投影片、圖片與表格操作。
- XLSX／XLSM 工作表、格線、Table 與 A2T；ODS 儲存格及含相依檢查的工作表改名；CSV／TSV 字串與列欄 CRUD。
- 獨立圖片影格／區域、受檢查的候選版本，以及選用 Office 實際頁面預覽。
- 完整操作紀錄、不可變證據選取與衍生關係、文稿 CSL／自訂引用及可攜式 Wiki。
- 支援範圍依完整 runtime contract；任意 PDF 內文編輯及 ODS 工作表／格線生命週期仍待擴充。

自 1.4.0 起，native-contract-v2 支援完整分頁規格；本版沿用 MCP SDK 2。
操作、限制與歷史驗證見 [Native File Assets](#/native-file-assets) 及
[Release And Testing](#/release-testing)；較早版本內容見 GitHub Releases。

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
