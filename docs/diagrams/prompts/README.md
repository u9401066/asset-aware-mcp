# Image Generation Prompts

These are the exact prompts used to generate all diagrams for Asset-Aware MCP. Every diagram was created using Google Gemini image generation API with consistent GitHub README style.

**Style Guide (applied to all diagrams):**
- Model: `google/gemini-3.1-flash-image-preview`
- Size: 1536x1024 (landscape)
- Background: #FFFFFF pure white
- Typography: Clean sans-serif
- Corners: Rounded
- Color palette: Navy `#1B2A4A`, Teal `#2196A6`, Green `#4CAF50`, Orange `#FF9800`, Coral coral `#FF6B6B`, Purple `#9C27B0`, Blue `#2196F3`, Red `#F44336`
- No gradients, no decorative noise

---

## 01 — System Architecture

```
A publication-quality architecture diagram for "Asset-Aware MCP — System Architecture".

Title at top center in bold, large: "Asset-Aware MCP Architecture"
Subtitle below title: "v0.6.3 | OpenClaw v2026.4.9"

LAYER 1 - TOP - User Layer (light blue):
A box with Telegram logo/paper airplane icon labeled "@Researchtillend_bot"
Subtitle: "Researchers group chat"

Arrow downward to Layer 2: label "API"

LAYER 2 - GATEWAY - Navy box (dark navy #1B2A4A, white text):
Large box "OpenClaw Gateway — port 18789"
Inside it, a smaller teal box (#2196A6): "MCP Adapter"
Sub-text in teal box: "238 tools total | mcp_call + mcp_search"

Three arrows pointing DOWN from MCP Adapter:
- Arrow 1 (green): points to asset-aware-mcp
- Arrow 2 (orange): points to drug-reco-mcp  
- Arrow 3 (blue): points to pubmed-search-mcp

LAYER 3 - THREE MCP SERVERS (side-by-side boxes):
Box A (green border): "asset-aware-mcp" · "48 tools" · "PDF/DOCX · Tables · Knowledge Graph"
Box B (orange border): "drug-reco-mcp" · "HTTP transport" · "YAML CRUD + medical knowledge"
Box C (blue border): "pubmed-search-mcp" · "37 tools" · "文獻搜尋 · PubMed API"

LAYER 4 - BOTTOM (two side-by-side boxes):
Box 4a (purple border): "asset-aware-data/" · path · tree: doc_xxx/ → manifest.json / images/ / tables/ / sections/
Box 4b (red border): "Ollama 192.168.1.2:30133" · gemma3:27b (LLM) · nomic-embed-text (Embedding) · lightrag-hku

Arrow Box 4a → Box 4b: label "HTTP API"

Footer: "238 tools total = PubMed (37) + Drug Reco + Asset-Aware (48) + Others"

Style: GitHub README architecture diagram, white background, rounded corners, clean flat design.
Size: 1536x1024
```

## 02 — Data Layout

```
A publication-quality data structure diagram for "Asset-Aware Data Layout"

Title: "Asset-Aware Data Layout"
Subtitle: "48 Tools · 7 Categories"

Layout: Tree structure on left, 7 category panels on right

LEFT — DATA TREE (asset-aware-data/doc_001/):
doc_001 → manifest.json (blue)
         → sections/ (teal): sec_001 Abstract, sec_002 Methods, sec_003 Results
         → tables/ (green): tbl_001 Demographics, tbl_002 Outcomes
         → images/ (orange): img_001 Figure 1, img_002 Table 1 visual

RIGHT — 7 TOOL CATEGORIES (vertical panels):
Panel 1 (blue): "📄 文件處理" 12 tools — ingest_documents, parse_pdf_structure, fetch_document_asset, OCR
Panel 2 (green): "📝 DOCX 雙向編輯" 14 tools — ingest_docx, get_docx_content, save_docx
Panel 3 (teal): "📑 Section 瀏覽" 5 tools — list_section_tree, get_section_detail, get_section_content
Panel 4 (coral): "📊 表格工具" 7 tools — plan_table, table_manage, table_data, table_cite
Panel 5 (purple): "🧠 知識圖譜" 2 tools — consult_knowledge_graph, export_knowledge_graph
Panel 6 (navy): "⚙️ ETL 設定" 5 tools — set_etl_profile, get_etl_profile
Panel 7 (gray): "🔧 任務管理" 3 tools — get_job_status, list_jobs, cancel_job

Arrows: doc_001 → sections panel (blue dashed)
        tables → table_data panel (green solid)
        images → fetch_asset panel (orange solid)

Footer: "48 tools · 7 categories · PDF + DOCX bidirectional"

Style: GitHub README technical diagram. Clean flat design, white background.
Size: 1536x1024
```

## 03 — PDF Ingestion Pipeline

```
A publication-quality workflow diagram for "Asset-Aware MCP — PDF Ingestion Pipeline"

Title: "PDF Ingestion Workflow"
Subtitle: "Process PDF → structured sections, tables, images, and knowledge graph"

Layout: Left-to-right 7-stage flow

Stage 1 (blue): "Upload PDF" — paper.pdf icon
Stage 2 (teal): "Ingest" — ingest_documents → returns doc_id
Stage 3 (green): "Parse Structure" — parse_pdf_structure (Marker), list_section_tree, get_section_blocks
Stage 4 (orange): "Extract Assets" — fetch_document_asset → sections/ tables/ images/
Stage 5 (coral): "Build Knowledge Graph" — consult_knowledge_graph, lightrag-hku (Ollama gemma3:27b)
Stage 6 (purple): "Query" — discover_sources, search_sections, get_section_content, table_cite
Stage 7 (navy): "Output" — convert_pdf_to_docx/pptx, export_markdown, save_docx

Arrows between stages: right-pointing teal arrows
Under Stage 4: asset-aware-data/doc_xxx/ storage icon
Under Stage 5: Ollama 192.168.1.2:30133 icon

Footer: "48 tools · PDF + DOCX · Tables + KG · v0.6.3"

Style: GitHub README workflow diagram. Clean flat design, color-coded stages.
Size: 1536x1024
```

## 04 — DOCX Bidirectional Edit Pipeline

```
A publication-quality workflow diagram for "Asset-Aware MCP — DOCX Bidirectional Editing Pipeline"

Title: "DOCX Bidirectional Editing Workflow"
Subtitle: "Ingest → Edit → Round-trip Save (48 tools)"

Layout: Left-to-right 6-stage flow with feedback loop

Stage 1 (green): "Ingest DOCX" — ingest_docx, DOCX → DFM format
Stage 2 (blue): "Explore Content" — list_docx_blocks, get_docx_content, list_docx_documents
Stage 3 (teal): "Table Workflow" — docx_table_to_context → TableContext → table_data → docx_table_from_context
Stage 4 (orange): "Chart Data" — docx_chart_data, Extract Excel data
Stage 5 (coral): "Validate" — docx_validate_roundtrip (Fidelity check)
Stage 6 (purple): "Save" — save_docx, convert to PDF/PPTX/ODT

Feedback loop: Stage 5 → Stage 2 (dashed coral arrow, "Iterate")
Down arrow from Stage 1: asset-aware-data/doc_xxx/ storage icon

Callout box: "14 DOCX Tools · Full round-trip fidelity · Table & Chart extraction"

Footer: "v0.6.3 | 48 tools total · 14 DOCX-specific"

Style: GitHub README workflow diagram with feedback loop. Color-coded stages, round arrows.
Size: 1536x1024
```

## 05 — Cross-Document Knowledge Graph Search

```
A publication-quality workflow diagram for "Asset-Aware MCP — Cross-Document Search via Knowledge Graph"

Title: "Cross-Document Search & Knowledge Graph"
Subtitle: "discover_sources · consult_knowledge_graph · table_cite"

Layout: Center-based with 3 parallel paths

TOP — Query Input: User query "remimazolam vs propofol PK parameters" splits into 3 paths

PATH 1 LEFT (green): "discover_sources" → search_sections → get_section_content
  → Returns matching sections from multiple ingested PDFs

PATH 2 CENTER (coral): "consult_knowledge_graph" → lightrag-hku (Ollama gemma3:27b)
  → Network graph: nodes propofol, remimazolam, PK, t1/2, Vd
  → Returns structured relationships · drug interactions · PK parameters

PATH 3 RIGHT (blue): "Table Analysis" — table_data → table_cite → table_draft → TableContext
  → Returns structured comparison tables with citations

BOTTOM — Knowledge Graph Builder (purple):
"lightrag-hku" · "Ollama 192.168.1.2:30133" · "nomic-embed-text (Embedding)"
Up arrows from all 3 paths → bottom box

Footer: "2 KG tools · 7 table tools · 5 section tools"

Style: GitHub README diagram. Clean flat design. Color-coded paths. Network graph for KG.
Size: 1536x1024
```
