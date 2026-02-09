"""
Presentation Layer - MCP Tools

拆分自 server.py，按領域分模組：
- document_tools: ETL + 文件管理工具
- section_tools: Section 導航工具
- job_tools: 非同步 Job 管理工具
- knowledge_tools: 知識圖譜工具
- table_tools: A2T 表格工具
- profile_tools: ETL Profile 設定工具
"""

# Import all tools to register them with mcp
from src.presentation.tools.document_tools import (
    fetch_document_asset,
    ingest_documents,
    inspect_document_manifest,
    list_documents,
    parse_pdf_structure,
    search_source_location,
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
    get_section_detail,
    list_section_tree,
    search_sections,
)
from src.presentation.tools.table_tools import (
    add_rows,
    add_rows_to_draft,
    commit_draft_to_table,
    create_table,
    create_table_draft,
    delete_row,
    delete_table,
    estimate_tokens,
    get_section_content,
    list_drafts,
    list_tables,
    plan_table_schema,
    preview_table,
    render_table,
    resume_draft,
    resume_table,
    update_cell,
    update_row,
    update_table_draft,
)

__all__ = [
    # Document tools
    "parse_pdf_structure",
    "search_source_location",
    "ingest_documents",
    "list_documents",
    "inspect_document_manifest",
    "fetch_document_asset",
    # Section tools
    "list_section_tree",
    "get_section_detail",
    "get_section_blocks",
    "search_sections",
    # Job tools
    "get_job_status",
    "list_jobs",
    "cancel_job",
    # Knowledge tools
    "consult_knowledge_graph",
    "export_knowledge_graph",
    # Profile tools
    "list_etl_profiles",
    "get_etl_profile",
    "get_current_etl_profile",
    "set_etl_profile",
    "load_etl_profile_from_json",
    # Table tools
    "plan_table_schema",
    "get_section_content",
    "create_table_draft",
    "update_table_draft",
    "add_rows_to_draft",
    "commit_draft_to_table",
    "list_drafts",
    "resume_draft",
    "estimate_tokens",
    "create_table",
    "add_rows",
    "update_row",
    "delete_row",
    "delete_table",
    "list_tables",
    "update_cell",
    "resume_table",
    "preview_table",
    "render_table",
]
