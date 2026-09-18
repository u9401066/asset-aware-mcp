"""Deliver native PDF previews as actual MCP images with pinned source metadata."""

from __future__ import annotations

import base64
import json
from typing import Any

from mcp.types import ImageContent, TextContent

from src.presentation.response_limits import (
    format_limited_json_response,
    image_exceeds_response_limit,
)


def native_pdf_image_response(
    payload: dict[str, Any],
) -> list[TextContent | ImageContent]:
    metadata = dict(payload)
    png = metadata.pop("image_png")
    encoded = base64.b64encode(png).decode("ascii")
    if image_exceeds_response_limit(encoded):
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        **metadata,
                        "success": False,
                        "image_omitted": True,
                        "error": "Native PDF preview exceeds the MCP image limit; retry with a smaller render_size.",
                    },
                    ensure_ascii=False,
                ),
            )
        ]
    formatted = format_limited_json_response(
        title="Native PDF page preview", payload=metadata
    )
    text = (
        formatted
        if isinstance(formatted, str)
        else json.dumps(formatted, ensure_ascii=False)
    )
    return [
        TextContent(
            type="text",
            text=text,
        ),
        ImageContent(type="image", data=encoded, mime_type="image/png"),
    ]
