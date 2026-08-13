<!-- Generated from Home.md by scripts/build_docs_site.py -->

# Asset-Aware MCP Docs

Asset-Aware MCP 是給 AI agents 使用的 citation-ready 文件工作流伺服器。它把
PDF、DOCX/DFM、表格、圖片、section、citation index、Foam evidence pack 與選用
KG/RAG 串成可驗證的文件流程。

這個網站改成章節式導覽：先選你正在做的任務，再進入對應的詳細頁或 reference。
目前內容對齊 `1.0.1` 正式文件。

## 1.0.1 highlights

- process-isolated PDF worker 改以 private、atomic、bounded MessagePack 結果檔
  交接，移除大型圖片塞滿 multiprocessing pipe 的 deadlock，也不再使用可執行
  pickle；partial、oversized、malformed 與 crash 都 fail closed。
- Codex managed config 會以真實 TOML 語意驗證並保留 custom／unrelated table，
  套用 180／900 秒 timeout、隔離 cwd 與 dotenv opt-out；credential value 不會
  落入 `config.toml`。
- 真實 MCP SDK 2 stdio 測試會拆出 text、table、超過 512 KiB 的 figure，驗證
  citation-ready evidence、每個 hash/locator、Foam notes、deterministic re-export
  與來源 PDF hash/mtime 不變。

## 1.0.0 highlights

- Runtime 已切換至官方 MCP Python SDK `>=2,<3` 與 `MCPServer`；MCP SDK v1
  不再支援，30 個 public tool schema 也不會外露 runtime `ctx` 參數。
- `document(op="preflight", pdf_path="...")` 在隔離 subprocess 中分類每頁
  是否需要 OCR，並建議 native、OCR 或 Docling route；輸出統一為 1-based、
  top-left 座標與來源 SHA-256。
- `document(op="export_assets", doc_id="...")` 產出 deterministic
  `manifest.json`、`assets.jsonl`、text/table/figure assets、citation locator
  與可攜式 Foam index/notes，供 agent 重複使用或接入 LightRAG。
- PDF、DOCX/DOC/ODT/ODS 混合批次攝入、來源 engine provenance、結構導覽與
  citation audit 仍維持在 30 tools / 43 endpoints 的 balanced surface。
- PyMuPDF4LLM 與 Docling 是目前可安裝的 structured engines。MinerU 與
  Marker adapter 保留，但 packaged extras 因上游 dependency security cap
  暫停，避免安裝已知有漏洞的 transformers／Pillow chain。

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
