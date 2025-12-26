# Asset-Aware MCP Server Entry Point
"""
Convenience module for running the MCP server.

This allows running with: python -m src.server
or via the pyproject.toml entry point: asset-aware-mcp
"""

from src.presentation.server import main

if __name__ == "__main__":
    main()
