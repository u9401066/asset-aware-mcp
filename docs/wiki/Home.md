# Asset-Aware MCP Docs

Asset-Aware MCP 是給 AI agents 使用的 citation-ready 文件工作流伺服器。它把
PDF、DOCX/DFM、表格、圖片、section、citation index、Foam evidence pack 與選用
KG/RAG 串成可驗證的文件流程。

這個網站改成章節式導覽：先選你正在做的任務，再進入對應的詳細頁或 reference。

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
    <p>PDF、DOCX/DFM、A2T table、background jobs、ETL profile 先分流，不混在同一頁。</p>
    <p><a href="#/workflow-chapters">流程章節</a> · <a href="#/pdf-workflow">PDF</a> · <a href="#/docx-dfm-workflow">DOCX</a></p>
  </section>
  <section class="path-card">
    <p class="card-kicker">Path 3</p>
    <h3>建立可驗證證據</h3>
    <p>所有 claim 都回到 span、locator、hash、context 與 citation bundle；KG 只做 discovery layer。</p>
    <p><a href="#/citation-provenance">引用與證據</a> · <a href="#/knowledge-graph">知識圖譜</a></p>
  </section>
  <section class="path-card">
    <p class="card-kicker">Path 4</p>
    <h3>查 reference 與上線 gates</h3>
    <p>需要精確 tool/resource contract、code 位置、release 檢查時，再進 reference。</p>
    <p><a href="#/mcp-tools">MCP Tools</a> · <a href="#/mcp-resources">Resources</a> · <a href="#/release-testing">Release</a></p>
  </section>
</div>

## 目前狀態

| 項目 | 目前值 |
|---|---|
| 版本 | `0.6.33` |
| MCP surface | 62 tools、13 resources，共 75 endpoints |
| PDF backend | PyMuPDF default；Marker 保留但因 Pillow 安全相容性暫停作為 packaged runtime |
| RAG default | CPU `granite4.1:3b`；GPU hint `granite4.1:8b` |
| KG | LightRAG/KG opt-in；CPU-only 或純文件流程不需要 KG |
| VS Code extension | MCP provider、Cline/Codex/Copilot config merge、assistant harness sync、artifact/citation viewer |

## 最短路徑

| 你要做什麼 | 先讀 | 然後讀 |
|---|---|---|
| 第一次安裝 | [快速開始](Getting-Started) | [VS Code Extension And MCP Setup](VS-Code-Extension-And-MCP-Setup) |
| 處理 PDF | [流程章節](Workflow-Chapters) | [PDF Document Workflow](PDF-Document-Workflow) |
| 編輯 Word / DFM | [流程章節](Workflow-Chapters) | [DOCX DFM Workflow](DOCX-DFM-Workflow) |
| 產出引用結論 | [Citation Provenance](Citation-Provenance) | [LLM Wiki Knowledge Base](LLM-Wiki-Knowledge-Base) |
| 建立 LLM wiki | [LLM Wiki Knowledge Base](LLM-Wiki-Knowledge-Base) | [Knowledge Graph](Knowledge-Graph) |
| 做表格 | [A2T Tables](A2T-Tables) | [DOCX DFM Workflow](DOCX-DFM-Workflow) |
| 查完整 API | [MCP Tools](MCP-Tools) | [MCP Resources](MCP-Resources) |
| 準備發布 | [Release And Testing](Release-And-Testing) | [Git Harness Hygiene](Git-Harness-Hygiene) |

## Code 對齊

網站內容由 `docs/wiki/**` 產生到 GitHub Pages payload。工具與 resource 數量來自
`src/presentation/tools/**`、`src/presentation/resources/**`，並由
`tests/unit/test_docs_site_reference_sync.py` 檢查 reference、metadata、連結與 endpoint 統計。
