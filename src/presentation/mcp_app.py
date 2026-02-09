"""
Presentation Layer - MCP Application Instance

FastMCP 實例的單一來源，供所有 tools/ 和 resources/ 模組引用。
"""

from mcp.server.fastmcp import FastMCP

# FastMCP 應用實例（全域單例）
mcp = FastMCP("Asset-Aware Medical RAG")
