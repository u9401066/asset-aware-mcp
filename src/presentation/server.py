"""
Presentation Layer - MCP Server

FastMCP server entry point. All tools and resources are defined in submodules.

Structure:
- mcp_app.py: FastMCP instance
- dependencies.py: DI container (Composition Root)
- tools/: MCP tools by domain
- resources/: MCP resources by domain
"""

from __future__ import annotations

# Register all tools (side-effect imports)
# Register all resources (side-effect imports)
from src.presentation import (
    resources,  # noqa: F401
    tools,  # noqa: F401
)

# Import mcp instance
from src.presentation.mcp_app import mcp


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
