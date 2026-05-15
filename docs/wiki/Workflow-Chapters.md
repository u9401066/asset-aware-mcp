# Workflow Chapters

這頁是文件網站的章節地圖。先從章節判斷你正在做的任務，再進入詳細頁或
MCP reference；不要一開始就從 62 個 tools 裡找入口。

## Chapter 1：啟動與環境確認

**目的**：確認 server、VS Code extension、MCP client、runtime defaults 可以跑。

| 要做的事 | 入口 | 驗證 |
|---|---|---|
| 安裝 Python/uv dependencies | [Getting Started](Getting-Started) | `uv run asset-aware-mcp doctor --json` |
| 設定 VSIX / Cline / Codex / Copilot | [VS Code Extension And MCP Setup](VS-Code-Extension-And-MCP-Setup) | extension status、MCP provider smoke |
| 確認安全預設 | [Getting Started](Getting-Started) | PyMuPDF default、Granite 3b/8b、KG opt-in |

## Chapter 2：PDF 文件攝入

**目的**：把 PDF 變成 manifest、markdown、blocks、assets、segmentation 與 citation artifacts。

| 階段 | 主要入口 | 產物 |
|---|---|---|
| 攝入 PDF | `document(op="ingest")` / `ingest_documents` | manifest、full markdown、assets、citation index |
| 結構解析 | `document(op="parse")` / `parse_pdf_structure` | Marker-required job 或明確 diagnostic |
| OCR | `ocr_pdf_document` | cleaned PDF job artifact |
| layout / segmentation | `export_document_segmentation`、`visualize_document_layout` | `segmentation.json`、page overlay |
| asset fetch | `document_asset(op="get")` / `fetch_document_asset` | table、figure、section、full text |

詳細頁：[PDF Document Workflow](PDF-Document-Workflow)、[Document Sections And Navigation](Document-Sections-And-Navigation)。

## Chapter 3：章節、定位與證據

**目的**：先用 document sections 找候選內容，再用 citation evidence 驗證 claim。

| 問題 | 入口 | 注意 |
|---|---|---|
| 文件有哪些章節？ | `list_section_tree` 或 `document_asset(op="tree")` | 這是 section navigation，不是 source locator |
| 某章節有哪些 blocks？ | `get_section_blocks` 或 `document_asset(op="blocks")` | 回傳 page/bbox/block context |
| 找可引用 span | `evidence(op="find")` / `find_evidence_spans` | 回傳 span ID、locator、hash、context |
| 驗證 AssetRef | `evidence(op="verify")` / `verify_citation_ref` | locator/hash 缺失時 fail closed |
| 產 citation bundle | `evidence(op="bundle")` / `citation_bundle` | JSON / Markdown / Foam evidence pack |

詳細頁：[Document Sections And Navigation](Document-Sections-And-Navigation)、[Citation Provenance](Citation-Provenance)。

可照做的 section-to-block 順序：

```text
document_asset(op="tree", doc_id="doc_...", response_format="flat")
-> copy returned section path
-> document_asset(op="blocks", doc_id="doc_...", path="Results/Primary Outcome", include_children=true, limit=20)
-> evidence(op="locate", doc_id="doc_...", query="primary outcome", limit=5)
```

## Chapter 4：DOCX / DFM 編輯

**目的**：把 Word 文件轉成 DFM 可編輯格式，保留 block identity、table、media、format metadata。

| 階段 | 主要入口 | 驗證 |
|---|---|---|
| ingest DOCX/DOC/ODT | `docx(op="ingest")` / `ingest_docx` | DocxIR、DFM、assets |
| 讀取與修改 | `docx(op="get")`、`docx(op="save")` | stale source check、track changes |
| round trip | `docx(op="validate")` / `docx_validate_roundtrip` | strict validation |
| table bridge | `docx_table(op="to_context")` / `docx_table(op="from_context")` | TableContext write-back |
| edit plan | `docx_table(op="edit_plan")` | row/column/header 風險先審查 |

詳細頁：[DOCX DFM Workflow](DOCX-DFM-Workflow)。

## Chapter 5：A2T 表格

**目的**：把 PDF assets、DOCX tables、KG candidates 或人工輸入整理成可引用表格。

| 階段 | 入口 |
|---|---|
| 設計 schema / template | `plan_table` |
| 建立、預覽、render | `table_manage` |
| rows / cells | `table_data` |
| cell citation | `table_cite` |
| audit / token | `table_history` |
| draft / resume / commit | `table_draft` |
| source discovery | `discover_sources` |

詳細頁：[A2T Tables](A2T-Tables)。

## Chapter 6：LLM Wiki 知識庫

**目的**：把 verified evidence pack、table/figure note 與人工 topic note 放進同一個 Foam-compatible Markdown wiki。

| 階段 | 入口 | 注意 |
|---|---|---|
| 寫 evidence note | `citation_bundle(output_format="foam")` 或 `evidence(op="bundle")` | copy tool 回傳的 `wikilink` / `embed`，不要手寫不存在的 anchor |
| 寫 table/figure note | `document_asset(op="foam_notes")` | table/figure AssetRef 主要由 wiki health 回查 |
| 寫 topic note | 人工 Markdown + `[[wikilink]]` | topic note 是 synthesis layer，具體 claim 附近要有 evidence link |
| 掃 wiki health | `evidence(op="health")` | 驗證 embedded AssetRefs 與 `[[note#^anchor]]` link 是否 drift |

詳細頁：[LLM Wiki Knowledge Base](LLM-Wiki-Knowledge-Base)、[Citation Provenance](Citation-Provenance)。

## Chapter 7：KG / RAG discovery

**目的**：用 opt-in KG 找跨文件關係；citation-ready 結論仍回到 evidence bundle。

| 階段 | 入口 | 注意 |
|---|---|---|
| 開啟 KG backend | `ENABLE_LIGHTRAG=true` + restart MCP | CPU-only 或純文件流程可保持關閉 |
| 建立 KG index | `ingest_documents(index_knowledge_graph=true)` | 這一步是 opt-in；只 ingest 不會自動寫 KG |
| 檢查 graph 內容 | `export_knowledge_graph(format="summary")` | 先確認有 nodes/edges 再查詢 |
| 查 KG | `knowledge(op="consult")` / `consult_knowledge_graph` | `verify_references=true` 可附 verified evidence |
| 寫入 wiki | 回到 `citation_bundle(..., output_format="foam")` | KG answer 不是最終引用來源 |

詳細頁：[Knowledge Graph](Knowledge-Graph)、[LLM Wiki Knowledge Base](LLM-Wiki-Knowledge-Base)。

## Chapter 8：維運、上線與 Reference

**目的**：處理長任務、ETL profile、release gates、完整 API surface 與 code 位置。

| 任務 | 入口 |
|---|---|
| Background jobs | [Background Jobs](Background-Jobs) |
| ETL profiles | [ETL Profiles](ETL-Profiles) |
| Release gates | [Release And Testing](Release-And-Testing) |
| 依任務選 tool | [Tool Chooser](Tool-Chooser) |
| 完整 tool contract | [MCP Tools](MCP-Tools) |
| Resource URI | [MCP Resources](MCP-Resources) |
| Code 位置 | [Code Map](Code-Map) |

## 章節心智模型

```text
Start -> PDF/DOCX ingest -> sections/assets -> evidence bundle -> table/wiki/KG -> operations -> release gates
```

每一層都要保留來源身分與 locator metadata；越接近 claim，越要回到
`evidence(...)` / `citation_bundle(...)` 做驗證。
