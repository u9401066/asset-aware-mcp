"""
Presentation Layer - ETL Profile Tools

MCP tools for managing ETL extraction profiles.
Allows users to list, view, and switch between profiles for different document formats.
"""

from __future__ import annotations

from src.domain.etl_profile import ETLProfileRegistry
from src.presentation.mcp_app import mcp


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
        profiles.append({
            "name": p.name,
            "description": p.description,
            "font_thresholds": {
                "h1": p.font_thresholds.h1,
                "h2": p.font_thresholds.h2,
                "h3": p.font_thresholds.h3,
            },
            "min_heading_length": p.min_heading_length,
        })

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
            "error": f"Failed to load profile: {str(e)}",
        }
