"""
Presentation Layer - MCP Resources

拆分自 server.py，按領域分模組：
- document_resources: 文件 + 知識圖譜 Resources
- table_resources: A2T 表格 + 草稿 Resources
"""

# Import all resources to register them with mcp
from src.presentation.resources.document_resources import (
    resource_document_figures,
    resource_document_list,
    resource_document_manifest,
    resource_document_outline,
    resource_document_sections,
    resource_document_segmentation,
    resource_document_tables,
    resource_knowledge_graph_summary,
)
from src.presentation.resources.table_resources import (
    resource_draft_content,
    resource_draft_list,
    resource_table_content,
    resource_table_list,
    resource_table_status,
)

__all__ = [
    "resource_document_figures",
    "resource_document_list",
    "resource_document_manifest",
    "resource_document_outline",
    "resource_document_sections",
    "resource_document_segmentation",
    "resource_document_tables",
    "resource_draft_content",
    "resource_draft_list",
    "resource_knowledge_graph_summary",
    "resource_table_content",
    "resource_table_list",
    "resource_table_status",
]
