"""
Presentation Layer - MCP Server

MCP v2 server entry point. All tools and resources are defined in submodules.

Structure:
- mcp_app.py: MCPServer instance
- dependencies.py: DI container (Composition Root)
- tools/: MCP tools by domain
- resources/: MCP resources by domain
"""

from __future__ import annotations

import logging
import sys

# Register all tools (side-effect imports)
# Register all resources (side-effect imports)
from src.presentation import (
    resources,  # noqa: F401
    tools,  # noqa: F401
)

# Import mcp instance
from src.presentation.mcp_app import mcp
from src.presentation.tool_surface import apply_tool_surface_policy

apply_tool_surface_policy(mcp)

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure structured logging for production."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        stream=sys.stderr,
    )
    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("lightrag").setLevel(logging.WARNING)


def main() -> None:
    """Run the MCP server."""
    configure_logging()
    logger.info("Starting Asset-Aware MCP server")
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception:
        logger.exception("Server crashed with unhandled exception")
        raise


if __name__ == "__main__":
    main()
