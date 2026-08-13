"""
Presentation Layer - MCP Application Instance

AssetAwareMCPServer 實例的單一來源，供所有 tools/ 和 resources/ 模組引用。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.server.mcpserver import MCPServer

if TYPE_CHECKING:
    from collections.abc import Callable

    from mcp.types import Icon, ToolAnnotations


class AssetAwareMCPServer(MCPServer):
    """MCP v2 server that tracks registrations through the public SDK API."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.registered_tool_names: set[str] = set()
        super().__init__(*args, **kwargs)

    def add_tool(
        self,
        fn: Callable[..., Any],
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        annotations: ToolAnnotations | None = None,
        icons: list[Icon] | None = None,
        meta: dict[str, Any] | None = None,
        structured_output: bool | None = None,
    ) -> None:
        super().add_tool(
            fn,
            name=name,
            title=title,
            description=description,
            annotations=annotations,
            icons=icons,
            meta=meta,
            structured_output=structured_output,
        )
        self.registered_tool_names.add(name or fn.__name__)

    def remove_tool(self, name: str) -> None:
        super().remove_tool(name)
        self.registered_tool_names.discard(name)


# MCPServer 應用實例（全域單例）
mcp = AssetAwareMCPServer("Asset-Aware Medical RAG")
