"""
Presentation Layer - ETL Profile Tools

MCP tools for managing ETL extraction profiles.
Allows users to list, view, and switch between profiles for different document formats.
"""

from __future__ import annotations

from typing import Any

from src.application.etl_profile_detector import (
    detect_profile_from_text,
    sample_pdf_text,
)
from src.domain.etl_profile import ETLProfileRegistry
from src.presentation.dependencies import repository
from src.presentation.mcp_app import mcp


def _normalize_op(op: str) -> str:
    return op.strip().lower().replace("-", "_")


def _profile_error(message: str) -> dict[str, Any]:
    return {"success": False, "error": message}


def _sync_profile_dependents() -> None:
    """Refresh modules that cache profile-dependent presentation services."""
    from src.presentation import dependencies
    from src.presentation.tools import document_tools, table_tools

    dependencies.job_service.set_document_service(dependencies.document_service)
    document_tools.document_service = dependencies.document_service
    document_tools.pdf_extractor = dependencies.pdf_extractor
    table_tools.document_service = dependencies.document_service

    try:
        from src.presentation.resources import document_resources
    except ImportError:
        return
    document_resources.document_service = dependencies.document_service


@mcp.tool()
async def list_etl_profiles() -> dict:
    """
    List all available ETL extraction profiles.

    Profiles define how PDFs are parsed: font thresholds for headings,
    noise filters, caption patterns, etc. Different journals/formats
    may need different profiles.

    Returns:
        Dict with:
        - profiles: List of profile info dicts
        - count: Total number of profiles
    """
    profiles = []
    for name in ETLProfileRegistry.list_profiles():
        p = ETLProfileRegistry.get(name)
        profiles.append(
            {
                "name": p.name,
                "description": p.description,
                "font_thresholds": {
                    "h1": p.font_thresholds.h1,
                    "h2": p.font_thresholds.h2,
                    "h3": p.font_thresholds.h3,
                },
                "min_heading_length": p.min_heading_length,
            }
        )

    return {
        "profiles": profiles,
        "count": len(profiles),
    }


@mcp.tool()
async def get_etl_profile(name: str) -> dict:
    """
    Get detailed configuration of a specific ETL profile.

    Args:
        name: Profile name (case-insensitive). Available: default, arxiv, nature, ieee, elsevier

    Returns:
        Full profile configuration as dict
    """
    try:
        p = ETLProfileRegistry.get(name)
        return {
            "success": True,
            "profile": p.to_dict(),
        }
    except KeyError as e:
        return {
            "success": False,
            "error": str(e),
            "available": ETLProfileRegistry.list_profiles(),
        }


@mcp.tool()
async def get_current_etl_profile() -> dict:
    """
    Get the currently active ETL profile used for document ingestion.

    Returns:
        Current profile name and summary
    """
    from src.presentation.dependencies import etl_profile

    return {
        "name": etl_profile.name,
        "description": etl_profile.description,
        "font_thresholds": {
            "h1": etl_profile.font_thresholds.h1,
            "h2": etl_profile.font_thresholds.h2,
            "h3": etl_profile.font_thresholds.h3,
        },
    }


@mcp.tool()
async def set_etl_profile(name: str) -> dict:
    """
    Switch the active ETL profile for subsequent document ingestion.

    This affects how PDFs are parsed: heading detection thresholds,
    noise filtering patterns, caption detection, etc.

    Args:
        name: Profile name to switch to. Available: default, arxiv, nature, ieee, elsevier

    Returns:
        Success status and new profile info

    Note:
        This only affects NEW document ingestions. Already processed documents
        retain their original extraction results.
    """
    from src.presentation.dependencies import rebuild_for_profile

    try:
        new_profile = rebuild_for_profile(name)
        _sync_profile_dependents()

        return {
            "success": True,
            "message": f"Switched to profile: {new_profile.name}",
            "profile": {
                "name": new_profile.name,
                "description": new_profile.description,
            },
        }

    except KeyError as e:
        return {
            "success": False,
            "error": str(e),
            "available": ETLProfileRegistry.list_profiles(),
        }


@mcp.tool()
async def load_etl_profile_from_json(json_path: str) -> dict:
    """
    Load a custom ETL profile from a JSON file and register it.

    The JSON file can specify a "base" field to inherit from an existing profile.
    Example JSON:
    {
        "base": "arxiv",
        "name": "my_journal",
        "description": "Custom settings for My Journal",
        "font_thresholds": {"h1": 18.0}
    }

    Args:
        json_path: Path to the JSON profile file

    Returns:
        Success status and loaded profile info
    """
    try:
        profile = ETLProfileRegistry.load_from_json(json_path)

        return {
            "success": True,
            "message": f"Loaded and registered profile: {profile.name}",
            "profile": {
                "name": profile.name,
                "description": profile.description,
            },
            "tip": f"Use set_etl_profile('{profile.name}') to activate it",
        }

    except FileNotFoundError:
        return {
            "success": False,
            "error": f"File not found: {json_path}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to load profile: {e!s}",
        }


@mcp.tool()
async def detect_etl_profile(
    pdf_path: str | None = None,
    doc_id: str | None = None,
    sample_text: str = "",
    sample_pages: int = 3,
    activate: bool = False,
) -> dict[str, Any]:
    """
    Auto-detect a suitable built-in ETL profile from a PDF or text sample.

    Detection is heuristic and returns reasons plus confidence. Set
    `activate=True` to switch the current profile after detection.
    """
    source = "sample_text"
    text = sample_text
    layout_hints: dict[str, Any] = {}
    file_name = pdf_path or doc_id or ""

    if not text and doc_id:
        markdown = repository.load_markdown(doc_id)
        if not markdown:
            return _profile_error(f"markdown not found for doc_id: {doc_id}")
        text = markdown[:12000]
        source = f"doc_id:{doc_id}"
        blocks = repository.load_blocks(doc_id) or []
        left = right = 0
        for block in blocks[:80]:
            bbox = block.get("bbox") if isinstance(block, dict) else None
            if not isinstance(bbox, list) or len(bbox) < 3:
                continue
            x0 = float(bbox[0])
            x1 = float(bbox[2])
            center = (x0 + x1) / 2
            if center < 300:
                left += 1
            elif center > 300:
                right += 1
        if left >= 5 and right >= 5:
            layout_hints["two_column"] = True

    if not text and pdf_path:
        try:
            text, layout_hints = sample_pdf_text(
                pdf_path,
                sample_pages=sample_pages,
            )
            source = pdf_path
        except Exception as e:
            return _profile_error(str(e))

    if not text:
        return _profile_error("Provide sample_text, doc_id, or pdf_path.")

    detection = detect_profile_from_text(
        text,
        file_name=file_name,
        layout_hints=layout_hints,
    )
    response: dict[str, Any] = {
        "success": True,
        "source": source,
        "sample_chars": len(text),
        "layout_hints": layout_hints,
        **detection,
    }
    if activate:
        selected = str(detection["recommended_profile"])
        response["activation"] = await set_etl_profile(selected)
    else:
        response["tip"] = (
            f"Use set_etl_profile('{detection['recommended_profile']}') "
            "or etl_profile(op='set', name=...) to activate."
        )
    return response


@mcp.tool()
async def etl_profile(
    op: str,
    name: str | None = None,
    json_path: str | None = None,
    pdf_path: str | None = None,
    doc_id: str | None = None,
    sample_text: str = "",
    sample_pages: int = 3,
    activate: bool = False,
) -> Any:
    """
    Consolidated ETL profile entrypoint.

    Existing profile tools stay registered for backwards compatibility.
    """
    operation = _normalize_op(op)
    if operation == "list":
        return await list_etl_profiles()
    if operation == "get":
        if not name:
            return _profile_error("name is required for etl_profile(op='get')")
        return await get_etl_profile(name)
    if operation == "current":
        return await get_current_etl_profile()
    if operation == "set":
        if not name:
            return _profile_error("name is required for etl_profile(op='set')")
        return await set_etl_profile(name)
    if operation == "load":
        if not json_path:
            return _profile_error("json_path is required for etl_profile(op='load')")
        return await load_etl_profile_from_json(json_path)
    if operation in {"detect", "auto", "auto_detect"}:
        return await detect_etl_profile(
            pdf_path=pdf_path,
            doc_id=doc_id,
            sample_text=sample_text,
            sample_pages=sample_pages,
            activate=activate,
        )
    return _profile_error(
        "Unsupported etl_profile op "
        f"`{op}`. Supported operations: current, detect, get, list, load, set."
    )
