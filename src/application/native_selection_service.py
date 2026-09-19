"""Read exact selections from verified immutable native parent representations."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.domain.native_selection import (
    NativeSelectionReference,
    NativeSelectionSelector,
    canonical_selection,
    selection_record,
)

if TYPE_CHECKING:
    from src.application.native_evidence_service import NativeEvidenceService
    from src.domain.native_assets import NativeDocumentRequest
    from src.domain.native_selection import NativeSelectionParent

SELECTION_BOUNDARY = "Selection offsets address parsed JSON strings, not source-file bytes. Parent integrity does not prove extraction completeness, semantic support, rendering or formula results."


class NativeSelectionService:
    def __init__(self, evidence: NativeEvidenceService):
        self.evidence = evidence

    def record(
        self,
        reference: NativeSelectionParent | NativeSelectionReference,
        selector: NativeSelectionSelector | None = None,
    ) -> dict[str, Any]:
        if isinstance(reference, NativeSelectionReference):
            if selector is not None:
                raise ValueError("Cannot override an existing selection reference")
            parent = reference.parent
            selector = reference.selector
        else:
            parent = reference
            selector = selector or NativeSelectionSelector()
        representation = self.evidence.read_parent_record(parent)
        if representation.pop("evidence") != parent.model_dump(mode="json"):
            raise ValueError("Selection parent reference failed integrity verification")
        record = selection_record(parent, selector, representation)
        if isinstance(reference, NativeSelectionReference) and record[
            "evidence"
        ] != reference.model_dump(mode="json"):
            raise ValueError("Selection reference failed integrity verification")
        return record

    def read(self, request: NativeDocumentRequest) -> dict[str, Any]:
        from src.domain.native_file_reference import NativeFileReference

        reference = request.reference
        if reference is None or isinstance(reference, NativeFileReference):
            raise ValueError("Selections require a parsed native parent reference")
        record = self.record(reference, request.selection)
        data = canonical_selection(record)
        text = data.decode("utf-8")
        start = min(request.text_offset, len(text))
        end = min(start + request.text_limit, len(text))
        result = {
            "success": True,
            "schema_version": "native-selection-page-v1",
            "asset_id": reference.asset_id,
            "inspected_revision": reference.revision,
            "evidence": record["evidence"],
            "text_excerpt": text[start:end],
            "text_length": len(text),
            "text_sha256": hashlib.sha256(data).hexdigest(),
            "excerpt_char_range": [start, end],
            "next_text_offset": end if end < len(text) else None,
            "representation_complete": start == 0 and end == len(text),
            "serialization": "canonical-json; UTF-8 SHA-256",
            "source_written": False,
            "review_boundary": SELECTION_BOUNDARY,
        }
        while len(json.dumps(result, ensure_ascii=False, indent=2)) > 10_000:
            if end <= start:
                raise ValueError("Selection reference exceeds the MCP response budget")
            end = start + (end - start) // 2
            result.update(
                text_excerpt=text[start:end],
                excerpt_char_range=[start, end],
                next_text_offset=end if end < len(text) else None,
                representation_complete=start == 0 and end == len(text),
            )
        return result

    def verify(self, reference: NativeSelectionReference) -> dict[str, Any]:
        parent_proof = self.evidence.verify(reference.parent)
        valid = False
        if parent_proof["valid"]:
            record = self.record(reference.parent, reference.selector)
            valid = record["evidence"] == reference.model_dump(mode="json")
        return {
            **parent_proof,
            "valid": valid,
            "verification_scope": reference.verification_scope,
            "checks": {
                "revision_hash": True,
                "parent_reference": parent_proof["valid"],
                "selection_representation_hash": valid,
            },
            "review_boundary": SELECTION_BOUNDARY,
        }
