"""Complete native capability metadata with bounded, hash-pinned delivery."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.native_assets import NativeDocumentRequest


def deliver_contract(
    result: dict[str, Any], request: NativeDocumentRequest | None
) -> dict[str, Any]:
    text = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(text.encode()).hexdigest()
    if request is not None and request.op == "contract_details":
        if request.contract_sha256 != digest:
            raise ValueError(
                "Native contract changed or scope differs; discover contract again"
            )
        start = min(request.text_offset, len(text))
        end = min(start + request.text_limit, len(text))
        while len(json.dumps(text[start:end], ensure_ascii=False)) > 8000:
            end = start + (end - start) // 2
        return {
            "success": True,
            "for_op": request.for_op,
            "contract_sha256": digest,
            "text_sha256": digest,
            "text_length": len(text),
            "text_excerpt": text[start:end],
            "excerpt_char_range": [start, end],
            "next_text_offset": end if end < len(text) else None,
            "representation_complete": start == 0 and end == len(text),
            "serialization": "canonical-json; UTF-8 SHA-256",
        }
    delivery = {
        "contract_delivery": "inline",
        "contract_sha256": digest,
        "contract_request": {
            "op": "contract_details",
            "contract_sha256": digest,
            **(
                {"for_op": request.for_op}
                if request is not None and request.for_op is not None
                else {}
            ),
        },
    }
    if len(json.dumps({**result, **delivery}, ensure_ascii=False, indent=2)) <= 10_000:
        return {**result, **delivery}
    # Keep every enabled flag, format/operation inventory, renderer and schema
    # continuation. Complete policies remain available at the advertised hash.
    summary = {
        key: value for key, value in result.items() if not key.endswith("_policy")
    }
    for key in ["docx_rendering", "pptx_rendering", "workbook_rendering"]:
        if key in summary:
            summary[key] = {k: v for k, v in summary[key].items() if k != "policy"}
    delivery["contract_delivery"] = "paged"
    return {
        **summary,
        **delivery,
        "contract_note": "Complete operation policies are in contract_request; assemble all pages at contract_sha256 before operating. Schema pages remain separate.",
    }
