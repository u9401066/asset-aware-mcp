"""
Presentation Layer - MCP Tools

拆分自 server.py，按領域分模組：
- document_tools: ETL + 文件管理工具 (11)
- docx_tools: Docx ↔ DFM 編輯 + 驗證 + Bridge 工具 (13)
- section_tools: Section 導航工具 (5)
- job_tools: 非同步 Job 管理工具 (3)
- knowledge_tools: 知識圖譜工具 (2)
- table_tools: A2T 表格工具 (7) — v0.2.14 合併版
- profile_tools: ETL Profile 設定工具 (5)

Total: 46 tools
"""

# Import all tools to register them with mcp
from src.presentation.tools.document_tools import (
    convert_pdf_to_docx,
    delete_document,
    export_document_segmentation,
    fetch_document_asset,
    ingest_documents,
    inspect_document_manifest,
    list_documents,
    ocr_pdf_document,
    parse_pdf_structure,
    search_source_location,
    visualize_document_layout,
)
from src.presentation.tools.docx_tools import (
    convert_docx_to_doc,
    convert_docx_to_pdf,
    delete_docx,
    docx_chart_data,
    docx_table_from_context,
    docx_table_to_context,
    docx_validate_roundtrip,
    export_markdown,
    get_docx_content,
    ingest_docx,
    list_docx_blocks,
    list_docx_documents,
    save_docx,
)
from src.presentation.tools.job_tools import (
    cancel_job,
    get_job_status,
    list_jobs,
)
from src.presentation.tools.knowledge_tools import (
    consult_knowledge_graph,
    export_knowledge_graph,
)
from src.presentation.tools.profile_tools import (
    get_current_etl_profile,
    get_etl_profile,
    list_etl_profiles,
    load_etl_profile_from_json,
    set_etl_profile,
)
from src.presentation.tools.section_tools import (
    get_section_blocks,
    get_section_content,
    get_section_detail,
    list_section_tree,
    search_sections,
)
from src.presentation.tools.table_tools import (
    discover_sources,
    plan_table,
    table_cite,
    table_data,
    table_draft,
    table_history,
    table_manage,
)

__all__ = [
    "cancel_job",
    "consult_knowledge_graph",
    "convert_docx_to_doc",
    "convert_docx_to_pdf",
    "convert_pdf_to_docx",
    "delete_document",
    "delete_docx",
    "discover_sources",
    "docx_chart_data",
    "docx_table_from_context",
    "docx_table_to_context",
    "docx_validate_roundtrip",
    "export_document_segmentation",
    "export_knowledge_graph",
    "export_markdown",
    "fetch_document_asset",
    "get_current_etl_profile",
    "get_docx_content",
    "get_etl_profile",
    "get_job_status",
    "get_section_blocks",
    "get_section_content",
    "get_section_detail",
    "ingest_documents",
    "ingest_docx",
    "inspect_document_manifest",
    "list_documents",
    "list_docx_blocks",
    "list_docx_documents",
    "list_etl_profiles",
    "list_jobs",
    "list_section_tree",
    "load_etl_profile_from_json",
    "ocr_pdf_document",
    "parse_pdf_structure",
    "plan_table",
    "save_docx",
    "search_sections",
    "search_source_location",
    "set_etl_profile",
    "table_cite",
    "table_data",
    "table_draft",
    "table_history",
    "table_manage",
    "visualize_document_layout",
]
