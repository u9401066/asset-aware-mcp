"""
Presentation Layer - MCP Tools

拆分自 server.py，按領域分模組：
- document_tools: ETL + document management tools (19)
- docx_tools: DOCX/DFM editing, validation, conversion, bridge tools (17)
- section_tools: section navigation tools (6)
- job_tools: async job management tools (4)
- knowledge_tools: knowledge graph tools (3)
- table_tools: A2T operation-based table tools (7)
- profile_tools: ETL profile tools (7)

Decorator inventory: 63 tools; balanced runtime surface: 30 tools
"""

# Import all tools to register them with mcp
from src.presentation.tools.document_tools import (
    citation_bundle,
    convert_document,
    convert_pdf_to_docx,
    convert_pdf_to_pptx,
    delete_document,
    document,
    document_asset,
    evidence,
    export_document_segmentation,
    fetch_document_asset,
    find_evidence_spans,
    ingest_documents,
    inspect_document_manifest,
    list_documents,
    ocr_pdf_document,
    parse_pdf_structure,
    search_source_location,
    verify_citation_ref,
    visualize_document_layout,
)
from src.presentation.tools.docx_tools import (
    convert_docx_to_doc,
    convert_docx_to_odt,
    convert_docx_to_pdf,
    delete_docx,
    docx,
    docx_chart_data,
    docx_table,
    docx_table_edit_plan,
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
    job,
    list_jobs,
)
from src.presentation.tools.knowledge_tools import (
    consult_knowledge_graph,
    export_knowledge_graph,
    knowledge,
)
from src.presentation.tools.profile_tools import (
    detect_etl_profile,
    etl_profile,
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
    section,
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
    "citation_bundle",
    "consult_knowledge_graph",
    "convert_document",
    "convert_docx_to_doc",
    "convert_docx_to_odt",
    "convert_docx_to_pdf",
    "convert_pdf_to_docx",
    "convert_pdf_to_pptx",
    "delete_document",
    "delete_docx",
    "detect_etl_profile",
    "discover_sources",
    "document",
    "document_asset",
    "docx",
    "docx_chart_data",
    "docx_table",
    "docx_table_edit_plan",
    "docx_table_from_context",
    "docx_table_to_context",
    "docx_validate_roundtrip",
    "etl_profile",
    "evidence",
    "export_document_segmentation",
    "export_knowledge_graph",
    "export_markdown",
    "fetch_document_asset",
    "find_evidence_spans",
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
    "job",
    "knowledge",
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
    "section",
    "set_etl_profile",
    "table_cite",
    "table_data",
    "table_draft",
    "table_history",
    "table_manage",
    "verify_citation_ref",
    "visualize_document_layout",
]
