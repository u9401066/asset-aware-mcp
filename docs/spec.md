# Tech Spec: Medical RAG with Asset-Aware MCP

## 1. Project Goal

Build a local-first Model Context Protocol (MCP) server tailored for medical research. The system is designed to help an AI Agent (Copilot) write accurate reports from multiple PDFs. Instead of feeding full texts blindly, the system generates a structured "Document Manifest" (Map) allowing the Agent to precisely inspect structures and fetch specific assets (Tables, Sections) on demand.

## 2. Core Architecture

### 2.1 DDD (Domain-Driven Design) 分層架構

```text
┌─────────────────────────────────────────────────────────────┐
│                   Presentation Layer                         │
│                   (MCP Server Interface)                     │
│  server.py - FastMCP tools exposed to AI Agent              │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   Application Layer                          │
│                   (Use Cases / Services)                     │
│  DocumentService, AssetService, KnowledgeGraphService       │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                     Domain Layer                             │
│                   (Core Business Logic)                      │
│  Entities: Document, Manifest, Table, Figure, Section       │
│  Value Objects: AssetType, DocId                            │
│  Domain Services: ManifestGenerator, AssetParser            │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Infrastructure Layer                         │
│                 (External Dependencies)                      │
│  PDFExtractor (PyMuPDF), LightRAGAdapter, FileStorage       │
│  MistralOCRAdapter (optional)                               │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 ETL Pipeline: "The Mechanic"

- Uses PyMuPDF to extract images with page numbers
- Uses Mistral OCR (optional) to parse PDFs into high-fidelity Markdown
- Uses LightRAG to build a Knowledge Graph & Vector Index
- **CRITICAL**: Generates a `_manifest.json` for each document, listing available assets (tables, headers, figures, entities)

### 2.3 MCP Server: "The Interface"

- Exposes tools for the Agent to inspect the manifest and fetch raw assets
- Supports **base64 image transmission** for figures
- **Dynamic Resource** for real-time file updates

## 3. Tech Stack

| Category | Technology | Purpose |
| -------- | ---------- | ------- |
| Language | Python 3.10+ | Core runtime |
| MCP | `mcp` (Python SDK) | MCP server with FastMCP |
| PDF | PyMuPDF (`fitz`) | Image extraction + page tracking |
| OCR | Mistral AI SDK | Optional high-fidelity OCR |
| RAG | LightRAG (`lightrag-hku`) | Knowledge Graph & Vector Index |
| Validation | Pydantic | Data models & validation |
| Storage | Local filesystem | JSON/Markdown files |

## 4. Project Structure (DDD)

```text
asset-aware-mcp/
├── src/
│   ├── __init__.py
│   │
│   ├── domain/                      # 🔵 Domain Layer
│   │   ├── __init__.py
│   │   ├── entities.py              # Document, Manifest, Assets
│   │   ├── value_objects.py         # AssetType, DocId
│   │   ├── services.py              # ManifestGenerator, AssetParser
│   │   └── repositories.py          # Abstract repository interfaces
│   │
│   ├── application/                 # 🟢 Application Layer
│   │   ├── __init__.py
│   │   ├── document_service.py      # Document ingestion use cases
│   │   ├── asset_service.py         # Asset fetching use cases
│   │   └── knowledge_service.py     # Knowledge graph queries
│   │
│   ├── infrastructure/              # 🟠 Infrastructure Layer
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py         # PyMuPDF implementation
│   │   ├── mistral_ocr.py           # Mistral OCR adapter
│   │   ├── lightrag_adapter.py      # LightRAG integration
│   │   ├── file_storage.py          # Local file repository
│   │   └── config.py                # Settings & environment
│   │
│   └── presentation/                # 🔴 Presentation Layer
│       ├── __init__.py
│       └── server.py                # MCP Server (FastMCP)
│
├── data/                            # Document storage
│   └── {doc_id}/
│       ├── {doc_id}_full.md
│       ├── {doc_id}_manifest.json
│       └── images/
│           └── fig_1_1.png
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
├── docs/
│   └── spec.md                      # This file
│
├── pyproject.toml
├── .env.example
└── README.md
```

## 5. Implementation Details

### Module A: Domain Layer

#### Entities (domain/entities.py)

```python
class Document:
    doc_id: str
    filename: str
    title: str
    page_count: int
    markdown_path: Path
    manifest: Manifest

class Manifest:
    doc_id: str
    toc: list[str]
    assets: DocumentAssets
    lightrag_entities: list[str]

class DocumentAssets:
    tables: list[TableAsset]
    figures: list[FigureAsset]
    sections: list[SectionAsset]
```

#### Value Objects (domain/value_objects.py)

```python
class AssetType(Enum):
    TABLE = "table"
    FIGURE = "figure"
    SECTION = "section"
    FULL_TEXT = "full_text"

class DocId:
    """Validated document identifier"""
    value: str
```

### Module B: Application Layer (Use Cases)

#### DocumentService

```python
class DocumentService:
    async def ingest(self, file_paths: list[str]) -> list[IngestResult]
    async def list_documents(self) -> list[DocumentSummary]
    async def get_manifest(self, doc_id: str) -> Manifest
```

#### AssetService

```python
class AssetService:
    async def fetch_table(self, doc_id: str, table_id: str) -> str
    async def fetch_figure(self, doc_id: str, figure_id: str) -> FigureResult
    async def fetch_section(self, doc_id: str, section_id: str) -> str
    async def fetch_full_text(self, doc_id: str) -> str
```

### Module C: Infrastructure Layer

#### PDFExtractor (PyMuPDF)

```python
class PDFExtractor:
    def extract_text(self, pdf_path: Path) -> str
    def extract_images(self, pdf_path: Path) -> list[ExtractedImage]
    # ExtractedImage includes: page_number, image_bytes, dimensions
```

#### FileStorage

```python
class FileStorage:
    def save_manifest(self, doc_id: str, manifest: Manifest)
    def load_manifest(self, doc_id: str) -> Manifest | None
    def save_markdown(self, doc_id: str, content: str)
    def save_image(self, doc_id: str, image_id: str, data: bytes)
```

### Module D: Presentation Layer (MCP Server)

Implement the following tools using FastMCP:

#### Tool 1: `ingest_documents`

- **Input**: `file_paths: List[str]`
- **Action**: Triggers the ETL pipeline for the given files
- **Return**: List of generated `doc_ids` and Titles

#### Tool 2: `list_documents`

- **Input**: None
- **Action**: Returns all processed documents
- **Return**: List of `{doc_id, filename, title, asset_counts}`

#### Tool 3: `inspect_document_manifest` (The Map)

- **Input**: `doc_id: str`
- **Action**: Reads and returns the contents of `{doc_id}_manifest.json`
- **Purpose**: Allows the Agent to "see" what tables and sections exist before reading

#### Tool 4: `fetch_document_asset` (The Fetcher)

- **Input**:
  - `doc_id: str`
  - `asset_type: Enum["table", "figure", "section", "full_text"]`
  - `asset_id: str` (e.g., `"tab_1"`, `"fig_1_1"`, `"sec_introduction"`)
- **Action**:
  - If `table`: Returns Markdown table content
  - If `figure`: Returns **base64 encoded image** with page number for verification
  - If `section`: Extracts text under the specific Header
  - If `full_text`: Returns entire document
- **Purpose**: Precise data retrieval to save context window and reduce noise

#### Tool 5: `consult_knowledge_graph` (The Brain)

- **Input**: `query: str`
- **Action**: Calls `rag.query(query, param=QueryParam(mode="hybrid"))`
- **Purpose**: Gets high-level insights or cross-document comparisons

#### Resource: `document://{doc_id}/images/{image_id}` (Dynamic)

- **Purpose**: Expose images as MCP Resources for dynamic access
- **Auto-update**: New files automatically available

### Manifest JSON Schema

```json
{
  "doc_id": "doc_study_a_abc123",
  "filename": "study_a.pdf",
  "title": "Effects of Metformin on HbA1c Levels",
  "toc": ["Introduction", "Methods", "Results", "Discussion"],
  "assets": {
    "tables": [
      {
        "id": "tab_1",
        "page": 2,
        "preview": "Patient Demographics...",
        "row_count": 10,
        "col_count": 5
      }
    ],
    "figures": [
      {
        "id": "fig_1_1",
        "page": 5,
        "path": "./data/doc_study_a_abc123/images/fig_1_1.png",
        "width": 800,
        "height": 600,
        "caption": "Figure 1: Study flow diagram"
      }
    ],
    "sections": [
      {
        "id": "sec_introduction",
        "title": "Introduction",
        "level": 1,
        "page": 1,
        "preview": "Diabetes mellitus is a chronic..."
      }
    ]
  },
  "lightrag_entities": ["Metformin", "HbA1c", "Hypoglycemia", "Type 2 Diabetes", "BMI"],
  "page_count": 12,
  "created_at": "2025-12-26T10:00:00Z"
}
```

## 6. Image Handling (Base64 Transmission)

### 圖片提取 (PyMuPDF)

```python
# 使用 PyMuPDF 提取圖片，保留頁碼資訊
for page_num, page in enumerate(pdf_doc):
    images = page.get_images(full=True)
    for img_index, img in enumerate(images):
        xref = img[0]
        base_image = pdf_doc.extract_image(xref)
        # base_image contains: image bytes, ext, width, height
```

### Base64 傳輸格式

```python
# MCP Tool 回傳格式
{
    "type": "image",
    "data": "iVBORw0KGgoAAAANSUhEUgAA...",  # base64 string
    "mimeType": "image/png",
    "metadata": {
        "page": 5,
        "figure_id": "fig_1_1",
        "width": 800,
        "height": 600
    }
}
```

### 驗證機制

- 回傳 `page` 讓使用者可以對照原始 PDF 驗證
- 回傳 `width`, `height` 確保圖片未被截斷
- Agent 可透過描述圖片內容來驗證理解正確性

## 7. Constraints & Directives for Copilot

1. **DDD 原則**: 遵循分層架構，Domain Layer 不依賴 Infrastructure

2. **No On-the-fly Summarization in ETL**: ETL 只負責 parse 和 map，不呼叫 LLM 摘要

3. **PyMuPDF Priority**: 使用 PyMuPDF 提取圖片，保留頁碼資訊

4. **Manifest First**: Agent 必須先查看 Manifest 再取得資料

5. **Base64 Image**: 圖片透過 base64 傳輸，確保完整性

6. **Dependency Injection**: 使用依賴注入讓測試更容易
