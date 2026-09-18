"""Verify immutable endpoints and retain separately attributed derivation claims."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from src.domain.native_derivation import (
    NativeDerivationRecord,
    canonical,
    fingerprint,
)

if TYPE_CHECKING:
    from src.application.native_evidence_service import NativeEvidenceService
    from src.domain.native_assets import NativeDocumentRequest
    from src.domain.native_derivation import (
        NativeDerivationEvent,
        NativeDerivationLedger,
        NativeDerivationRepository,
        NativeReference,
    )

REVIEW_BOUNDARY = "Agent identity, activity and review are caller assertions; verified references do not prove semantic support, visual fidelity or source freshness."


class NativeDerivationService:
    def __init__(
        self, repository: NativeDerivationRepository, evidence: NativeEvidenceService
    ):
        self.repository = repository
        self.evidence = evidence

    def ledger(
        self, asset_id: str, expected: str | None = None
    ) -> NativeDerivationLedger:
        ledger = self.repository.load(asset_id)
        if expected is not None and fingerprint(ledger) != expected:
            raise ValueError("Derivation ledger changed; restart the pinned read")
        return ledger

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        if request.op == "read_derivations":
            return self._read(request)
        if request.op == "verify_derivation":
            return self._verify(request)
        assert request.expected_derivations_sha256 is not None
        event: NativeDerivationEvent
        if request.op == "record_derivation":
            assert request.derivation is not None
            if request.derivation.target.asset_id != request.asset_id:
                raise ValueError("Derivation target belongs to a different asset")
            for reference in [request.derivation.target, *request.derivation.sources]:
                self.require_valid(reference)
            event = NativeDerivationRecord(
                derivation_id=fingerprint(request.derivation),
                derivation=request.derivation,
            )
        else:
            assert request.retraction is not None
            event = request.retraction
        ledger = self.repository.append(
            request.asset_id, request.expected_derivations_sha256, event
        )
        return {
            "success": True,
            "asset_id": request.asset_id,
            "derivation_id": event.derivation_id,
            "derivations_sha256": fingerprint(ledger),
            "event_count": len(ledger.events),
            "native_file_written": False,
            "source_written": False,
            "review_boundary": REVIEW_BOUNDARY,
        }

    def require_valid(self, reference: NativeReference) -> None:
        if not self.evidence.verify(reference)["valid"]:
            raise ValueError(
                "Derivation endpoint reference failed integrity verification"
            )

    def _read(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        ledger = self.ledger(request.asset_id, request.derivations_sha256)
        text = canonical(ledger).decode("utf-8")
        start = min(request.text_offset, len(text))
        end = min(start + request.text_limit, len(text))
        while len(json.dumps(text[start:end], ensure_ascii=False)) > 8000:
            end = start + (end - start) // 2
        return {
            "success": True,
            "asset_id": request.asset_id,
            "schema_version": "native-derivations-page-v1",
            "derivations_sha256": fingerprint(ledger),
            "event_count": len(ledger.events),
            "text_excerpt": text[start:end],
            "text_length": len(text),
            "excerpt_char_range": [start, end],
            "next_text_offset": end if end < len(text) else None,
            "representation_complete": start == 0 and end == len(text),
            "serialization": "canonical-json; UTF-8 SHA-256",
            "review_boundary": REVIEW_BOUNDARY,
        }

    def _check(self, ref: NativeReference) -> dict[str, Any]:
        try:
            result = self.evidence.verify(ref)
            return {
                key: result[key]
                for key in (
                    "valid",
                    "is_current_managed_revision",
                    "archived",
                    "verification_scope",
                )
            }
        except (ValueError, OSError, KeyError) as exc:
            return {"valid": False, "error_excerpt": str(exc)[:120]}

    def _verify(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        ledger = self.ledger(request.asset_id, request.derivations_sha256)
        record = next(
            (
                e
                for e in ledger.events
                if isinstance(e, NativeDerivationRecord)
                and e.derivation_id == request.derivation_id
            ),
            None,
        )
        if record is None:
            raise ValueError("Unknown native derivation")
        target = self._check(record.derivation.target)
        sources = [self._check(ref) for ref in record.derivation.sources]
        start = min(request.offset, len(sources))
        end = min(start + min(request.limit, 10), len(sources))
        return {
            "success": True,
            "derivation_id": record.derivation_id,
            "derivations_sha256": fingerprint(ledger),
            "active": record.derivation_id in ledger.active_records(),
            "references_valid": target["valid"] and all(s["valid"] for s in sources),
            "target": target,
            "sources": sources[start:end],
            "source_offset": start,
            "source_count": len(sources),
            "next_offset": end if end < len(sources) else None,
            "agent_review": record.derivation.review.model_dump(exclude={"notes"}),
            "review_notes_request": {
                "op": "read_derivations",
                "asset_id": request.asset_id,
                "derivations_sha256": fingerprint(ledger),
            },
            "review_boundary": REVIEW_BOUNDARY,
        }
