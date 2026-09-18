"""Canonical native DOCX block representations, separate from bounded previews."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.domain.native_assets import NativeDocxBlockLocator


def docx_block_record(
    block: dict[str, Any], asset_id: str, revision: str
) -> dict[str, Any]:
    locator = NativeDocxBlockLocator(
        block_id=block["id"], part=block.get("metadata", {}).get("source_part", "")
    ).model_dump()
    record = {
        "schema_version": "native-docx-block-v1",
        "block_id": block["id"],
        "kind": block["block_type"],
        "locator": locator,
        "representation": block,
    }
    canonical = json.dumps(
        record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    record["evidence"] = {
        "schema_version": "native-docx-block-ref-v1",
        "asset_id": asset_id,
        "revision": revision,
        "locator": locator,
        "value_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "verification_scope": "immutable_native_representation",
    }
    return record


def docx_block_summary(record: dict[str, Any]) -> dict[str, Any]:
    block = record["representation"]
    return {
        "id": record["block_id"],
        "type": record["kind"],
        "editable": block["editable"],
        "style": block.get("style_name"),
        "preview": block["text"][:80],
        "metadata": block.get("metadata", {}),
        "evidence": record["evidence"],
    }


def docx_block_excerpt(
    record: dict[str, Any], offset: int, limit: int
) -> dict[str, Any]:
    block = record["representation"]
    text = block["text"]
    start = min(offset, len(text))
    end = min(start + limit, len(text))
    metadata = block.get("metadata", {})
    return {
        "block_id": record["block_id"],
        "kind": record["kind"],
        "locator": record["locator"],
        "evidence": record["evidence"],
        "editable": block["editable"],
        "style": block.get("style_name"),
        "source_locator": {
            key: value
            for key, value in metadata.items()
            if key not in {"run_ranges"} and isinstance(value, (str, int))
        },
        "text_excerpt": text[start:end],
        "text_length": len(text),
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "excerpt_char_range": [start, end],
        "next_text_offset": end if end < len(text) else None,
        "text_complete": start == 0 and end == len(text),
        "representation_complete": False,
        "full_representation": "export_wiki records.jsonl; DFM text via read_docx",
    }
