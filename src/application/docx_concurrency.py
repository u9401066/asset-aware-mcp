"""Serialized edit sessions, content revisions and 3-way merge for DFM saves.

Every mutating DOCX/DFM operation (``save_docx``, lease checkout/commit/release,
``docx_table_from_context``, re-ingest) runs inside one :class:`DocxEditContext`:
a cross-process exclusive document lock (SQLite ``BEGIN IMMEDIATE``) during which
``ir.json`` is loaded, the current content revision is computed and recorded,
and all writes happen. See ``docs/dfm-spec.md`` section 12.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.application.docx_baseline import BASELINE_IR_FILENAME
from src.application.docx_ir_serialization import DocxIrSerializationMixin
from src.domain.docx_edit_state import (
    DEFAULT_REVISION_HISTORY_LIMIT,
    REVISION_KIND_ADOPTED,
    REVISION_KIND_EXTERNAL,
    REVISION_KIND_INGEST,
    BlockLease,
    DocxEditSession,
    DocxEditStateError,
    block_state_hash,
    content_revision,
    iso_utc,
    lease_scope,
    plan_three_way_merge,
)
from src.domain.docx_entities import DocxIR
from src.infrastructure.dfm_parser import DfmParseResult
from src.infrastructure.docx_edit_state_store import (
    DEFAULT_LOCK_TIMEOUT_SECONDS,
    SqliteDocxEditStateStore,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator
    from pathlib import Path

    from src.domain.docx_entities import DfmBlock
    from src.infrastructure.dfm_parser import DfmParser

logger = logging.getLogger(__name__)

_REOPEN_HINT = (
    'Re-open the current DFM (get_docx_content / docx(op="get")) and re-apply '
    'your edits, or use docx(op="checkout") / docx(op="commit") to edit only '
    "the blocks you need while other agents work on the rest."
)


@dataclass
class DocxEditContext:
    """State visible inside one serialized document edit session."""

    session: DocxEditSession
    doc_dir: Path
    ir: DocxIR
    revision: str
    entries: list[tuple[str, str]]
    payloads: dict[str, dict[str, Any]] = field(repr=False)
    now: float
    recorded_external: bool = False

    @property
    def block_hashes(self) -> dict[str, str]:
        return dict(self.entries)


@dataclass(frozen=True)
class RevisionResolution:
    """How a submitted full DFM relates to the current document revision."""

    parse_result: DfmParseResult
    mode: str  # current | merged | legacy
    base_revision: str
    merged_block_ids: tuple[str, ...] = ()
    theirs_block_ids: tuple[str, ...] = ()
    already_applied_block_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_result(self) -> dict[str, Any]:
        info: dict[str, Any] = {"mode": self.mode, "base_revision": self.base_revision}
        if self.mode == "merged":
            info["merged_block_ids"] = list(self.merged_block_ids)
            info["preserved_block_ids"] = list(self.theirs_block_ids)
            if self.already_applied_block_ids:
                info["already_applied_block_ids"] = list(self.already_applied_block_ids)
        return info


class DocxConcurrencyMixin(DocxIrSerializationMixin):
    """Revision tracking and serialized sessions for :class:`DocxService`."""

    _clock: Callable[[], float] = staticmethod(time.time)
    _edit_lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS
    _revision_history_limit: int = DEFAULT_REVISION_HISTORY_LIMIT

    if TYPE_CHECKING:
        parser: DfmParser

        def _expected_changed_block_ids(
            self, original_ir: DocxIR, parse_result: Any
        ) -> set[str]: ...

    # ------------------------------------------------------------------
    # Revision primitives
    # ------------------------------------------------------------------

    def _ir_block_records(self, ir: DocxIR) -> list[dict[str, Any]]:
        """Block records exactly as persisted in ``ir.json`` (JSON-normalized)."""
        return [
            json.loads(json.dumps(self._block_to_dict(block), ensure_ascii=False))
            for block in ir.blocks
        ]

    def _ir_revision_state(
        self, ir: DocxIR
    ) -> tuple[str, list[tuple[str, str]], dict[str, dict[str, Any]]]:
        records = self._ir_block_records(ir)
        entries: list[tuple[str, str]] = []
        payloads: dict[str, dict[str, Any]] = {}
        for record in records:
            block_hash = block_state_hash(record)
            entries.append((str(record["id"]), block_hash))
            payloads[block_hash] = record
        return content_revision(ir.checksum, entries), entries, payloads

    def ir_revision(self, ir: DocxIR) -> str:
        """Content revision of an IR state (stamped into DFM front matter)."""
        return self._ir_revision_state(ir)[0]

    def _stamp_revision(self, ir: DocxIR) -> str:
        """Compute and attach the revision the renderer writes to front matter."""
        revision = self.ir_revision(ir)
        ir.dfm_revision = revision
        return revision

    def _edit_state_store(self, doc_dir: Path) -> SqliteDocxEditStateStore:
        return SqliteDocxEditStateStore(
            doc_dir,
            timeout_seconds=self._edit_lock_timeout_seconds,
            history_limit=self._revision_history_limit,
        )

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    @contextmanager
    def _edit_context(self, doc_id: str) -> Iterator[DocxEditContext]:
        """Exclusive, cross-process edit session with the current IR loaded.

        Raises:
            DocxEditStateError: IR missing, document busy, or state unreadable.
        """
        doc_dir = self.repository.get_doc_dir(doc_id)
        store = self._edit_state_store(doc_dir)
        with store.session(write=True) as session:
            ir = self._load_ir(doc_id)
            if ir is None:
                raise DocxEditStateError(f"IR not found for {doc_id}")
            revision, entries, payloads = self._ir_revision_state(ir)
            context = DocxEditContext(
                session=session,
                doc_dir=doc_dir,
                ir=ir,
                revision=revision,
                entries=entries,
                payloads=payloads,
                now=self._clock(),
            )
            self._ensure_revision_tracking(context)
            yield context

    def _ensure_revision_tracking(self, context: DocxEditContext) -> None:
        """Create the root lazily and record an untracked current state."""
        session = context.session
        root = session.root()
        if root is None:
            baseline = self._tracking_baseline(context)
            if baseline is not None:
                base_revision, base_entries, base_payloads = baseline
                session.create_root(
                    base_revision,
                    REVISION_KIND_INGEST,
                    base_entries,
                    base_payloads,
                    now=context.now,
                )
            else:
                session.create_root(
                    context.revision,
                    REVISION_KIND_ADOPTED,
                    context.entries,
                    context.payloads,
                    now=context.now,
                )
        if session.revision(context.revision) is not None:
            return
        latest = session.latest_revision()
        previous = session.revision_manifest(latest.revision) if latest else None
        changed = [
            bid
            for bid, block_hash in context.entries
            if previous is None or previous.get(bid) != block_hash
        ]
        kind = REVISION_KIND_ADOPTED if root is None else REVISION_KIND_EXTERNAL
        recorded = session.record_revision(
            context.revision,
            parent=latest.revision if latest else None,
            kind=kind,
            actor=None,
            changed_block_ids=changed,
            entries=context.entries,
            payloads=context.payloads,
            now=context.now,
        )
        context.recorded_external = (
            recorded is not None and kind == REVISION_KIND_EXTERNAL
        )
        if context.recorded_external:
            logger.warning(
                "DOCX %s: ir.json changed outside a tracked write; recorded "
                "revision %s (%d block(s) changed)",
                context.ir.doc_id,
                context.revision,
                len(changed),
            )

    def _tracking_baseline(
        self, context: DocxEditContext
    ) -> tuple[str, list[tuple[str, str]], dict[str, dict[str, Any]]] | None:
        """Ingest baseline as revision root, when it provably matches the IR."""
        path = context.doc_dir / BASELINE_IR_FILENAME
        if not path.is_file():
            return None
        try:
            baseline = self._dict_to_ir(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError, TypeError):
            return None
        current = context.ir
        if (
            baseline.doc_id != current.doc_id
            or baseline.checksum != current.checksum
            or [b.id for b in baseline.blocks] != [b.id for b in current.blocks]
        ):
            return None
        return self._ir_revision_state(baseline)

    # ------------------------------------------------------------------
    # Persisting a new revision
    # ------------------------------------------------------------------

    def _record_revision_state(
        self,
        context: DocxEditContext,
        state: tuple[str, list[tuple[str, str]], dict[str, dict[str, Any]]],
        *,
        kind: str,
        actor: str | None,
        changed_block_ids: Iterable[str],
    ) -> str:
        """Retain the state computed by ``_ir_revision_state`` as a revision."""
        revision, entries, payloads = state
        if revision != context.revision:
            context.session.record_revision(
                revision,
                parent=context.revision,
                kind=kind,
                actor=actor,
                changed_block_ids=sorted(changed_block_ids),
                entries=entries,
                payloads=payloads,
                now=context.now,
            )
        return revision

    # ------------------------------------------------------------------
    # Stale full-DFM saves: 3-way merge
    # ------------------------------------------------------------------

    def _resolve_submitted_revision(
        self, context: DocxEditContext, parse_result: DfmParseResult
    ) -> RevisionResolution | dict[str, Any]:
        """Prove which document state a full DFM was based on.

        Returns a resolution whose ``parse_result`` holds only the edits that may
        be applied to the current IR, or an error result.
        """
        submitted = (parse_result.revision or "").strip()
        current = context.revision
        if submitted == current:
            return RevisionResolution(parse_result, "current", current)

        if not submitted:
            reason = self._legacy_dfm_rejection(context)
            if reason is None:
                return RevisionResolution(
                    parse_result,
                    "legacy",
                    current,
                    warnings=(
                        "DFM front matter has no `revision` (created before 1.5.0 "
                        "or hand-built); accepted because the document has not "
                        "been saved since ingest.",
                    ),
                )
            if not self._expected_changed_block_ids(context.ir, parse_result):
                # Identical to the current content: re-saving cannot overwrite
                # anyone's edit, it only regenerates the output.
                return RevisionResolution(parse_result, "legacy", current)
            return self._stale_error(
                "Stale DFM edit refused: this DFM has no `revision` in its front "
                f"matter, and {reason}, so it cannot be proven to include the "
                f"current content (revision {current}). {_REOPEN_HINT}"
            )

        record = context.session.revision(submitted)
        if record is not None:
            manifest = context.session.revision_manifest(submitted) or {}
            if list(manifest) != [block.id for block in context.ir.blocks]:
                return self._stale_error(
                    f"Cannot save {context.ir.doc_id}: the current ir.json does not "
                    "match the block structure of revision "
                    f"{submitted} this DFM was based on (blocks were added, removed "
                    "or renamed outside the DFM workflow). Writing would risk "
                    "losing or misplacing edits. Re-ingest the source DOCX with "
                    "ingest_docx and re-apply the edits (previous versions are "
                    "kept under .backups/)."
                )
        base_ir = self._ir_at_revision(context, submitted) if record else None
        if record is None or base_ir is None:
            limit = context.session.history_limit
            return self._stale_error(
                f"Stale DFM edit refused: revision {submitted} is not in this "
                f"document's retained revision history (the newest {limit} "
                f"revisions plus the root). The current revision is {current}. "
                f"{_REOPEN_HINT}"
            )

        base_manifest = context.session.revision_manifest(submitted) or {}
        ours_changed = self._expected_changed_block_ids(base_ir, parse_result)
        current_hashes = context.block_hashes
        overlap = {
            bid
            for bid in ours_changed
            if base_manifest.get(bid) != current_hashes.get(bid)
        }
        already_applied = {
            bid
            for bid in overlap
            if self._edit_reproduces_current(base_ir, parse_result, bid, current_hashes)
        }
        plan = plan_three_way_merge(
            base_manifest, current_hashes, ours_changed, already_applied
        )
        if plan.conflict_block_ids:
            conflicts = sorted(plan.conflict_block_ids)
            return {
                "success": False,
                "error": (
                    "Stale DFM edit refused: it was based on revision "
                    f"{submitted}, but block(s) {', '.join(conflicts)} were changed "
                    "by another save/commit since then (current revision "
                    f"{current}). Nothing was written. Re-open the current DFM, "
                    "merge your changes to those blocks by hand and save again; "
                    "blocks only you changed would have been merged automatically."
                ),
                "conflict_block_ids": conflicts,
                "base_revision": submitted,
                "current_revision": current,
                "warnings": [
                    "Saving was aborted before applying edits to prevent "
                    "overwriting a newer DFM/IR session."
                ],
            }

        apply_ids = plan.apply_block_ids
        merged = DfmParseResult(
            doc_id=parse_result.doc_id,
            source=parse_result.source,
            checksum=parse_result.checksum,
            style_info=parse_result.style_info,
            edits=[edit for edit in parse_result.edits if edit.block_id in apply_ids],
            errors=list(parse_result.errors),
            revision=submitted,
        )
        return RevisionResolution(
            merged,
            "merged",
            submitted,
            merged_block_ids=tuple(sorted(apply_ids)),
            theirs_block_ids=tuple(sorted(plan.theirs_block_ids)),
            already_applied_block_ids=tuple(sorted(plan.already_applied_block_ids)),
            warnings=(
                f"DFM was based on revision {submitted}; merged onto current "
                f"revision {current}: applied {len(apply_ids)} block(s) you changed "
                f"and kept {len(plan.theirs_block_ids)} block(s) changed by "
                "others since your base.",
            ),
        )

    @staticmethod
    def _stale_error(message: str) -> dict[str, Any]:
        logger.warning("%s", message)
        return {
            "success": False,
            "error": message,
            "warnings": [
                "Saving was aborted before applying edits to prevent "
                "overwriting a newer DFM/IR session."
            ],
        }

    def _legacy_dfm_rejection(self, context: DocxEditContext) -> str | None:
        """Why a DFM without ``revision`` cannot be trusted (None = accept)."""
        session = context.session
        root = session.root()
        if session.revision_count() > 1:
            return "the document has been saved since ingest"
        if root is None or root.revision != context.revision:
            return "the document content differs from its ingest state"
        backups = context.doc_dir / ".backups"
        if backups.is_dir() and any(backups.iterdir()):
            return "earlier saves were recorded under .backups/"
        return None

    def _ir_at_revision(self, context: DocxEditContext, revision: str) -> DocxIR | None:
        """Reconstruct a retained revision's IR from the current skeleton."""
        manifest = context.session.revision_manifest(revision)
        if manifest is None:
            return None
        current = context.ir
        if list(manifest) != [block.id for block in current.blocks]:
            return None
        base = deepcopy(current)
        current_hashes = context.block_hashes
        for index, block in enumerate(base.blocks):
            wanted = manifest[block.id]
            if wanted == current_hashes.get(block.id):
                continue
            payload = context.session.block_payload(wanted)
            if payload is None:
                return None
            base.blocks[index] = self._block_from_record(current, payload)
        return base

    def _block_from_record(self, ir: DocxIR, record: dict[str, Any]) -> DfmBlock:
        rebuilt = self._dict_to_ir({"doc_id": ir.doc_id, "blocks": [record]})
        return rebuilt.blocks[0]

    def _edit_reproduces_current(
        self,
        base_ir: DocxIR,
        parse_result: DfmParseResult,
        block_id: str,
        current_hashes: dict[str, str],
    ) -> bool:
        """True when applying our edit to the base yields the current block."""
        block = base_ir.find_block(block_id)
        if block is None:
            return False
        probe = DocxIR(
            doc_id=base_ir.doc_id,
            source_path=base_ir.source_path,
            checksum=base_ir.checksum,
            blocks=[deepcopy(block)],
        )
        single = DfmParseResult(
            doc_id=parse_result.doc_id,
            source=parse_result.source,
            checksum=parse_result.checksum,
            edits=[edit for edit in parse_result.edits if edit.block_id == block_id],
        )
        self.parser.apply_edits(probe, single)
        record = json.loads(
            json.dumps(self._block_to_dict(probe.blocks[0]), ensure_ascii=False)
        )
        return block_state_hash(record) == current_hashes.get(block_id)

    # ------------------------------------------------------------------
    # Lease gate shared by save_docx and IR block updates
    # ------------------------------------------------------------------

    @staticmethod
    def _lease_scope_ids(ir: DocxIR, block_ids: Iterable[str]) -> list[str]:
        ordered = [block.id for block in ir.blocks]
        parents = {
            block.id: (
                str(block.metadata.get("parent_table_id"))
                if block.metadata.get("parent_table_id")
                else None
            )
            for block in ir.blocks
        }
        return lease_scope(ordered, parents, block_ids)

    def _live_lease_conflicts(
        self,
        context: DocxEditContext,
        block_ids: Iterable[str],
        *,
        exclude_lease_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Live leases (other than ``exclude_lease_id``) covering these blocks."""
        scope = self._lease_scope_ids(context.ir, block_ids)
        if not scope:
            return []
        conflicts: list[dict[str, Any]] = []
        for lease in context.session.leases_covering(scope):
            if lease.lease_id == exclude_lease_id or not lease.is_live(context.now):
                continue
            conflicts.append(self._lease_conflict(lease, scope, context.now))
        return conflicts

    @staticmethod
    def _lease_conflict(
        lease: BlockLease, scope: Iterable[str], now: float
    ) -> dict[str, Any]:
        wanted = set(scope)
        return {
            "lease_id": lease.lease_id,
            "holder": lease.holder,
            "block_ids": [bid for bid in lease.block_ids if bid in wanted],
            "expires_at": iso_utc(lease.expires_at),
            "remaining_seconds": max(0, int(lease.expires_at - now)),
        }

    @staticmethod
    def _describe_lease_conflicts(conflicts: list[dict[str, Any]]) -> str:
        return "; ".join(
            f"{', '.join(item['block_ids'])} leased by {item['holder']!r} "
            f"({item['lease_id']}) until {item['expires_at']}"
            for item in conflicts
        )
