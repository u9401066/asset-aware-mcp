"""Helpers for keeping MCP text responses small enough for stdio clients."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

TEXT_RESPONSE_LIMIT_ENV = "ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS"
IMAGE_RESPONSE_LIMIT_ENV = "ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS"
DEFAULT_TEXT_RESPONSE_MAX_CHARS = 12_000
DEFAULT_IMAGE_RESPONSE_MAX_CHARS = 750_000
_STREAM_CHARS = 64 * 1024


def text_sha256(text: str) -> str:
    """Return a stable content hash for omitted text."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def max_text_response_chars(max_chars: int | None = None) -> int:
    """Resolve the configured MCP text preview limit.

    A value of 0 means "return the full text" for explicit operator requests.
    """
    if max_chars is not None:
        return max(0, int(max_chars))

    raw = os.environ.get(TEXT_RESPONSE_LIMIT_ENV, "").strip()
    if not raw:
        return DEFAULT_TEXT_RESPONSE_MAX_CHARS
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_TEXT_RESPONSE_MAX_CHARS


def max_image_response_chars(max_chars: int | None = None) -> int:
    """Resolve the configured MCP image/base64 response limit."""
    if max_chars is not None:
        return max(0, int(max_chars))

    raw = os.environ.get(IMAGE_RESPONSE_LIMIT_ENV, "").strip()
    if not raw:
        return DEFAULT_IMAGE_RESPONSE_MAX_CHARS
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_IMAGE_RESPONSE_MAX_CHARS


def text_exceeds_response_limit(text: str, max_chars: int | None = None) -> bool:
    limit = max_text_response_chars(max_chars)
    return limit > 0 and len(text) > limit


def image_exceeds_response_limit(data: str, max_chars: int | None = None) -> bool:
    limit = max_image_response_chars(max_chars)
    return limit > 0 and len(data) > limit


def _safe_fence_text(text: str) -> str:
    return text.replace("```", "` ` `")


def _limited_preview_response(
    *,
    title: str,
    preview: str,
    content_chars: int,
    sha256: str,
    source_path: str | Path | None = None,
    limit: int,
    language: str,
    guidance: str | None,
) -> str:
    preview = _safe_fence_text(preview)
    lines = [
        f"# {title}",
        "",
        "Full content is stored as an artifact and was not inlined because it "
        "exceeds the MCP text response limit.",
        f"- content_chars: {content_chars}",
        f"- preview_chars: {len(preview)}",
        f"- omitted_chars: {max(0, content_chars - limit)}",
        f"- sha256: `{sha256}`",
    ]
    if source_path is not None:
        lines.append(f"- artifact_path: `{source_path}`")
    if guidance:
        lines.append(f"- next: {guidance}")
    lines.extend(
        [
            "",
            "## Preview",
            f"```{language}",
            preview,
            "```",
        ]
    )
    return "\n".join(lines)


def format_limited_text_response(
    *,
    title: str,
    text: str,
    source_path: str | Path | None = None,
    max_chars: int | None = None,
    language: str = "text",
    guidance: str | None = None,
) -> str:
    """Return *text* unchanged unless it exceeds the response limit.

    Large artifacts stay on disk; MCP clients receive a bounded preview plus
    enough identity metadata to verify and fetch the source artifact directly.
    """
    limit = max_text_response_chars(max_chars)
    if limit == 0 or len(text) <= limit:
        return text

    return _limited_preview_response(
        title=title,
        preview=text[:limit],
        content_chars=len(text),
        sha256=text_sha256(text),
        source_path=source_path,
        limit=limit,
        language=language,
        guidance=guidance,
    )


def format_limited_file_response(
    *,
    title: str,
    path: str | Path,
    max_chars: int | None = None,
    language: str = "text",
    guidance: str | None = None,
) -> str:
    """Return a bounded preview for a text artifact without reading it all."""
    source_path = Path(path)
    limit = max_text_response_chars(max_chars)
    if limit == 0:
        return source_path.read_text(encoding="utf-8")

    hasher = hashlib.sha256()
    preview_parts: list[str] = []
    content_chars = 0
    with source_path.open("r", encoding="utf-8") as handle:
        while True:
            chunk = handle.read(_STREAM_CHARS)
            if not chunk:
                break
            hasher.update(chunk.encode("utf-8"))
            if content_chars < limit:
                preview_parts.append(chunk[: max(0, limit - content_chars)])
            content_chars += len(chunk)

    text = "".join(preview_parts)
    if content_chars <= limit:
        return text

    return _limited_preview_response(
        title=title,
        preview=text,
        content_chars=content_chars,
        sha256="sha256:" + hasher.hexdigest(),
        source_path=source_path,
        limit=limit,
        language=language,
        guidance=guidance,
    )


def format_limited_json_response(
    *,
    title: str,
    payload: Any,
    source_path: str | Path | None = None,
    max_chars: int | None = None,
    guidance: str | None = None,
) -> Any:
    """Return payload unchanged unless its JSON representation is too large."""
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    limit = max_text_response_chars(max_chars)
    if limit == 0 or len(text) <= limit:
        return payload

    summary: dict[str, Any] = {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(value, str):
                if len(value) <= 2_000:
                    summary[key] = value
                else:
                    summary[f"{key}_chars"] = len(value)
                    summary[f"{key}_sha256"] = text_sha256(value)
                    summary[f"{key}_preview"] = _safe_fence_text(value[:2_000])
            elif isinstance(value, int | float | bool) or value is None:
                summary[key] = value

    summary.update(
        {
            "response_truncated": True,
            "content_chars": len(text),
            "preview_chars": limit,
            "omitted_chars": len(text) - limit,
            "sha256": text_sha256(text),
            "preview_json": _safe_fence_text(text[:limit]),
        }
    )
    if source_path is not None:
        summary["artifact_path"] = str(source_path)
    if guidance:
        summary["next"] = guidance
    if "success" not in summary and isinstance(payload, dict) and "success" in payload:
        summary["success"] = bool(payload.get("success"))
    summary.setdefault("title", title)
    return summary


def format_omitted_image_response(
    *,
    title: str,
    data: str,
    mime_type: str = "image/png",
    source_path: str | Path | None = None,
    max_chars: int | None = None,
    guidance: str | None = None,
) -> str:
    """Return a small text record for an image omitted from MCP response."""
    limit = max_image_response_chars(max_chars)
    lines = [
        f"# {title}",
        "",
        "Image data was not inlined because its base64 payload exceeds the MCP "
        "image response limit.",
        f"- image_base64_chars: {len(data)}",
        f"- image_response_limit_chars: {limit}",
        f"- mime_type: `{mime_type}`",
        f"- sha256: `{text_sha256(data)}`",
    ]
    if source_path is not None:
        lines.append(f"- artifact_path: `{source_path}`")
    if guidance:
        lines.append(f"- next: {guidance}")
    return "\n".join(lines)
