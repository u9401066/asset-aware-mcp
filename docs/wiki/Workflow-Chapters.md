# Workflow Chapters

這頁是文件網站的章節地圖。先從章節判斷你正在做的任務，再進入詳細頁或
MCP reference；不要一開始就從 62 個 tools 裡找入口。

## Chapter 1：啟動與環境確認

**目的**：確認 server、VS Code extension、MCP client、runtime defaults 可以跑。

| 要做的事 | 入口 | 驗證 |
|---|---|---|
| 安裝 Python/uv dependencies | [Getting Started](Getting-Started) | `uv run asset-aware-mcp doctor --json` |
| 設定 VSIX / Cline / Codex / Copilot | [VS Code Extension And MCP Setup](VS-Code-Extension-And-MCP-Setup) | extension status、MCP provider smoke |
| 確認安全預設 | [Knowledge Graph](Knowledge-Graph) | PyMuPDF default、Granite 3b/8b、KG opt-in |

## Chapter 2：PDF 文件攝入

**目的**：把 PDF 變成 manifest、markdown、blocks、assets、segmentation 與 citation artifacts。

| 階段 | 主要入口 | 產物 |
|---|---|---|
| 攝入 PDF | `document(op="ingest")` / `ingest_documents` | manifest、full markdown、assets、citation index |
| 結構解析 | `document(op="parse")` / `parse_pdf_structure` | Marker-required job 或明確 diagnostic |
| OCR | `ocr_pdf_document` | cleaned PDF job artifact |
| layout / segmentation | `export_document_segmentation`、`visualize_document_layout` | `segmentation.json`、page overlay |
| asset fetch | `document_asset(op="get")` / `fetch_document_asset` | table、figure、section、full text |

詳細頁：[PDF Document Workflow](PDF-Document-Workflow)。

## Chapter 3：章節、定位與證據

**目的**：先用 document sections 找候選內容，再用 citation evidence 驗證 claim。

| 問題 | 入口 | 注意 |
|---|---|---|
| 文件有哪些章節？ | `list_section_tree` 或 `document_asset(op="tree")` | 這是 section navigation，不是 source locator |
| 某章節有哪些 blocks？ | `get_section_blocks` 或 `document_asset(op="blocks")` | 回傳 page/bbox/block context |
| 找可引用 span | `evidence(op="find")` / `find_evidence_spans` | 回傳 span ID、locator、hash、context |
| 驗證 AssetRef | `evidence(op="verify")` / `verify_citation_ref` | locator/hash 缺失時 fail closed |
| 產 citation bundle | `evidence(op="bundle")` / `citation_bundle` | JSON / Markdown / Foam evidence pack |

詳細頁：[Citation Provenance](Citation-Provenance)。

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

## Chapter 6：KG / RAG discovery

**目的**：用 KG 找跨文件關係，但 citation-ready 結論仍回到 evidence bundle。

| 階段 | 入口 | 注意 |
|---|---|---|
| 查 KG | `knowledge(op="consult")` / `consult_knowledge_graph` | `verify_references=true` 可附 verified evidence |
| 匯出 graph | `knowledge(op="export")` / `export_knowledge_graph` | JSON / summary / visualization input |
| 建置 LLM wiki | [LLM Wiki Knowledge Base](LLM-Wiki-Knowledge-Base) | Foam notes、evidence packs、asset notes、health check |
| 寫 evidence note | `citation_bundle(output_format="foam")` 或 `document_asset(op="foam_notes")` | KG 是 discovery layer，不是唯一引用來源 |

詳細頁：[Knowledge Graph](Knowledge-Graph)、[LLM Wiki Knowledge Base](LLM-Wiki-Knowledge-Base)。

## Chapter 7：上線與 Reference

**目的**：準備 release、查完整 API surface、確認 docs/code 沒 drift。

| 任務 | 入口 |
|---|---|
| Release gates | [Release And Testing](Release-And-Testing) |
| 完整 tool contract | [MCP Tools](MCP-Tools) |
| Resource URI | [MCP Resources](MCP-Resources) |
| Code 位置 | [Code Map](Code-Map) |

## 章節心智模型

```text
Start -> PDF/DOCX ingest -> sections/assets -> evidence bundle -> table/KG/wiki -> release gates
```

每一層都要保留來源身分與 locator metadata；越接近 claim，越要回到
`evidence(...)` / `citation_bundle(...)` 做驗證。
