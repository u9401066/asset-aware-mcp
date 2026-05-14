<!-- Generated from Home.md by scripts/build_docs_site.py -->

# Asset-Aware MCP Docs

![Asset-Aware MCP architecture overview](wiki/assets/overview-architecture.jpg)

Asset-Aware MCP 是一個 citation-ready 文件處理與知識工作流 MCP Server。這個文件站主要給人類閱讀：先用任務入口幫你找到路，再把完整工具、資源、程式碼位置與 release gate 留在 reference 頁查證。

<div class="path-grid">
  <section class="path-card">
    <p class="card-kicker">第一次使用</p>
    <h3>把 server 跑起來</h3>
    <p>安裝、設定 MCP client、確認 VS Code extension 與 stdio server 可用。</p>
    <p><a href="#/getting-started">開始使用</a> · <a href="#/vs-code-extension">VSIX / MCP 設定</a></p>
  </section>
  <section class="path-card">
    <p class="card-kicker">文件工作流</p>
    <h3>處理 PDF / DOCX / 表格</h3>
    <p>依照任務選 PDF ingest、DOCX/DFM round trip、citation evidence 或 A2T table。</p>
    <p><a href="#/pdf-workflow">PDF</a> · <a href="#/docx-dfm-workflow">DOCX/DFM</a> · <a href="#/a2t-tables">A2T</a></p>
  </section>
  <section class="path-card">
    <p class="card-kicker">查完整功能</p>
    <h3>確認目前公開 MCP surface</h3>
    <p>完整 62 tools、13 resources、程式碼地圖與 release checks 都放在 reference/developer 頁。</p>
    <p><a href="#/mcp-tools">MCP Tools</a> · <a href="#/mcp-resources">Resources</a> · <a href="#/code-map">Code Map</a></p>
  </section>
  <section class="path-card">
    <p class="card-kicker">網站設計</p>
    <h3>了解為什麼這樣排</h3>
    <p>這個站採任務導向首頁、左側資訊架構、頁內 outline、reference 分層查表。</p>
    <p><a href="#/design-ux">Design / UX Notes</a></p>
  </section>
</div>

目前版本真相：

| 項目 | 狀態 |
|---|---|
| 最新程式版本 | `0.6.32` |
| Python | `>=3.10`，以 `uv` 管理 |
| MCP endpoints | 62 tools、13 resources，共 75 endpoints |
| PDF 後端 | 預設 PyMuPDF；Marker backend 自 `0.6.28` 起因 `Pillow` 安全相容性暫時 hold |
| DOCX | DOCX/DOC/DFM round trip、Track Changes、LibreOffice conversion、strict validation |
| Knowledge graph | LightRAG (`lightrag-hku`) + Ollama/OpenAI，可選 verified citation bundle |
| VS Code extension | 內建 MCP provider、Cline/Codex/Copilot config merge、assistant harness sync、artifact/citation viewer |

來源錨點：`pyproject.toml`、`CHANGELOG.md`、`src/presentation/tools/**`、`src/presentation/resources/**`、`vscode-extension/src/**`。

## 怎麼讀這個站

- 想安裝與驗證：先看 [Getting Started](#/getting-started)，再看 [VS Code Extension And MCP Setup](#/vs-code-extension)。
- 想完成文件任務：從 [PDF Document Workflow](#/pdf-workflow)、[DOCX DFM Workflow](#/docx-dfm-workflow)、[Citation Provenance](#/citation-provenance)、[A2T Tables](#/a2t-tables) 選一條路。
- 想理解架構：看 [Architecture](#/architecture) 和 [Code Map](#/code-map)。
- 想查所有功能：看 [MCP Tools](#/mcp-tools) 和 [MCP Resources](#/mcp-resources)。
- 想維護或發布：看 [Developer Guide](#/developer-guide)、[Release And Testing](#/release-testing)、[Git Harness Hygiene](#/git-harness-hygiene)。
- 想知道網站 UX 原則：看 [Design And UX Notes](#/design-ux)。

## 主要工作流

| 工作流 | 用途 | 主要入口 |
|---|---|---|
| PDF ingestion | 產生 `{doc_id}_manifest.json`、`{doc_id}_full.md`、assets metadata 與 segmentation | `ingest_documents`、`document(op="ingest")` |
| Citation evidence | 找出可引用 span、驗證 AssetRef、匯出 verified bundle | `find_evidence_spans`、`verify_citation_ref`、`citation_bundle`、`evidence(...)` |
| DOCX/DFM editing | 將 Word 轉為 DFM、編輯後保真寫回 | `ingest_docx`、`save_docx`、`docx(...)` |
| Table extraction | 建立 A2T TableContext、附來源引用、渲染輸出 | `plan_table`、`table_manage`、`table_data`、`table_cite` |
| Knowledge graph | 跨文件 LightRAG 查詢、匯出與 evidence verification | `consult_knowledge_graph(verify_references=true)`、`export_knowledge_graph` |
| Async jobs | 將長任務與 conversion 移出 MCP request path | `get_job_status`、`list_jobs`、`cancel_job` |
| VSIX setup | 安裝 MCP provider 與 assistant harness | VS Code extension commands and settings |

## 文件更新原則

Wiki 以目前 `origin/master` 程式碼為準，不從記憶重建工具數量。工具與資源數量來自 `./scripts/count_tools.sh`，功能說明對應目前 `src/presentation/tools` 與 `src/presentation/resources` 的公開 MCP surface。
