<!-- Generated from PDF-Document-Workflow.md by scripts/build_docs_site.py -->

# PDF Document Workflow

![PDF document workflow](wiki/assets/pdf-document-workflow.jpg)

## 目的

PDF pipeline 將原始 PDF 轉成可檢索、可視覺化、可引用的文件 artifacts。它不是單純抽文字，而是同時保存 document identity、assets、section structure、layout locator、reading order、line/char/byte spans 與 citation hash。

來源：`src/application/document_service.py`、`src/infrastructure/pdf_extractor.py`、`src/infrastructure/marker_adapter.py`、`src/application/segmentation_service.py`、`src/presentation/tools/document_tools.py`。

## Ingest

主要工具：

- `ingest_documents(...)`
- `document(op="ingest", ...)`
- `parse_pdf_structure(...)`，Marker 專用 high-precision parse job

預設後端是 PyMuPDF。`0.6.30` 的 Marker extra 仍暫時為空，因為 `marker-pdf` 對 Pillow 的舊版 pin 會和安全 runtime 衝突。`parse_pdf_structure(...)` 是 Marker-required background job；security hold 或 backend unavailable 會出現在 job status/result 裡。一般 `ingest_documents(use_marker=true)` 會把 Marker preference 傳進 job，Marker 不可用時可退回 PyMuPDF；若 `require_marker=true` 則 fail closed。

## 產物

| Artifact | 用途 |
|---|---|
| `original.pdf` | 原始 PDF copy，layout overlay 與 locator 對照使用 |
| `{doc_id}_full.md` | 人可讀與 LLM chunk-friendly 全文 |
| `{doc_id}_manifest.json` | 文件 identity、pages、figures、tables、sections、metadata |
| `blocks.json` | block-level layout/text/source backend metadata |
| `segmentation.json` | reading order、line range、char/byte range、hash、source revision |
| `citation_index.jsonl` | citation-ready evidence spans |
| `citation_index.status.json` | citation index build/rebuild status |
| `images/` | 圖片與 page/region assets |
| `ocr/`, `pages/` | optional OCR、page image 或 conversion artifacts |

這些 artifact 預設落在 `$DATA_DIR/{doc_id}/`。A2T 的 durable table files 則位於 `$DATA_DIR/tables/`；PDF table 結構本身主要透過 manifest、blocks 與 segmentation 讀取。

## OCR

`ocr_pdf_document(...)` 會建立 background job，並透過 `src/infrastructure/ocr_processor.py` 包裝 `ocrmypdf`。支援：

- `language`
- `rotate_pages`
- `deskew`
- `output_path`

OCR 後的 PDF 可再進入正常 ingest。

在 background job 模式下，`ocr_pdf_document(output_path=...)` 保留為相容參數；實際可追蹤輸出以 job result/artifacts 為準。

## Segmentation

`export_document_segmentation(...)` 將 manifest、blocks、assets 與 reading order 合併成 schema。它同時保留：

- `reading_order`：內容理解順序。
- `line_start` / `line_end`：Markdown locator。
- `char_range` / `byte_range`：精準引用。
- `source_revision` / `locator_version`：locator schema 版本。
- `text_sha256` / `locator_source_sha256`：內容與 locator source hash。

## Layout Visualization

`visualize_document_layout(...)` 會產生 page overlay，用於檢查 bbox、block type、labels 與 reading order。它對 debugging same-page assets、wrong block pairing、OCR artifacts 特別有用。

## Search And Fetch

| Tool | 用途 |
|---|---|
| `search_source_location` | 依文字查 page/bbox/block |
| `find_evidence_spans` | 找 citation-ready spans |
| `verify_citation_ref` | 驗證引用 ref 是否仍有效 |
| `citation_bundle` | 匯出 verified evidence bundle，含 AssetRef、locator、hash、context 與 verification |
| `fetch_document_asset` | 擷取 table/figure/section/full_text |
| `document_asset(...)` | consolidated asset/search/section 入口 |

## Conversion

`convert_pdf_to_docx` 與 `convert_pdf_to_pptx` 以已攝入 artifacts 為來源，支援 `output_path`、conversion `mode` 與 `async_mode`。預設 `async_mode=true` 會建立 background conversion job，使用 `get_job_status(job_id)` 追蹤 output artifact；若需要舊式同步結果，可設 `async_mode=false`。

對於跨格式入口，使用 `convert_document(...)`；Markdown 直接輸出則使用 DOCX workflow 的 `export_markdown(...)`，同樣預設走 conversion job。
