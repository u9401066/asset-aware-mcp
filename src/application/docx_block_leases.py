"""Block checkout/lease editing so several agents can edit one DOCX at once.

Workflow (``docx`` tool operations):

1. ``checkout(doc_id, block_ids, holder, ttl_seconds)`` -> lease token, each
   block's DFM fragment and base hash, and the document revision. Fails fast
   (no blocking waits) when another live lease holds any requested block.
2. The agent edits only those fragments.
3. ``commit(doc_id, lease_token, edits)`` applies only the leased blocks on top
   of the *current* document (other holders' commits are kept), runs the same
   cumulative write-back and post-save verification as ``save_docx``, bumps the
   revision and releases the lease (or keeps it with ``keep_lease``).
4. ``release`` gives blocks back without editing; leases also expire.

Leases are stored in the per-document SQLite edit-state database and every
operation runs under the cross-process document lock (see
:mod:`src.application.docx_concurrency`).
"""

from __future__ import annotations

import json
import logging
import re
import secrets
from copy import deepcopy
from typing import TYPE_CHECKING, Any

import yaml

from src.application.docx_concurrency import DocxConcurrencyMixin
from src.domain.docx_edit_state import (
    LEASE_EVENT_BROKEN,
    LEASE_EVENT_COMMITTED,
    LEASE_EVENT_RECLAIMED,
    LEASE_EVENT_RELEASED,
    MAX_LEASE_BLOCKS,
    MAX_LIVE_LEASES,
    REVISION_KIND_BLOCK_UPDATE,
    REVISION_KIND_COMMIT,
    BlockLease,
    DocxEditStateError,
    block_state_hash,
    iso_utc,
    lease_id_for_token,
    lease_token_hash,
    validate_holder,
    validate_ttl,
)
from src.domain.docx_entities import DocxIR
from src.domain.docx_value_objects import DfmBlockType
from src.domain.native_docx import MAX_DFM_BYTES
from src.infrastructure.encoding_guard import (
    EncodingError,
    normalize_text_input,
    write_utf8_text_atomic,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping
    from pathlib import Path

    from src.application.docx_concurrency import DocxEditContext
    from src.infrastructure.dfm_parser import DfmParseResult
    from src.infrastructure.dfm_renderer import DfmRenderer

# Text/run edits within paragraphs, headings, list items, captions, mixed-format
# paragraphs and table cells are the scope of block leases.
LEASABLE_BLOCK_TYPES = frozenset(
    {
        DfmBlockType.PARAGRAPH,
        DfmBlockType.HEADING,
        DfmBlockType.LIST_ITEM,
        DfmBlockType.FORMAT,
        DfmBlockType.CAPTION,
        DfmBlockType.TABLE,
    }
)
logger = logging.getLogger(__name__)

_FRAGMENT_MARKER_RE = re.compile(r"<!--\s*(?:dfm:(\w+)\s+)?@b:(\S+)")
_FRAGMENT_CLOSE_RE = re.compile(r"<!--\s*/dfm:\w+\s*-->")
_TRIPLE_BLANK_RE = re.compile(r"\n[ \t]*\n[ \t]*\n")
_LEASE_GUIDANCE = (
    'Checkout -> edit -> commit -> release. Inspect leases with docx(op="leases").'
)


def _error(message: str, **extra: Any) -> dict[str, Any]:
    return {"success": False, "error": message, **extra}


class DocxBlockLeaseMixin(DocxConcurrencyMixin):
    """Lease operations for :class:`DocxService`."""

    if TYPE_CHECKING:
        renderer: DfmRenderer

        def _detect_unedited_block_mutations(
            self,
            original_ir: DocxIR,
            updated_ir: DocxIR,
            expected_changed_ids: set[str],
        ) -> list[str]: ...

        def _write_back_locked(
            self,
            context: DocxEditContext,
            parse_result: DfmParseResult,
            output_path: str | None,
            *,
            force: bool,
            track_changes: bool,
            revision_author: str,
            revision_base: str,
            kind: str,
            actor: str | None,
            save_warnings: list[str] | None = None,
            result_extra: dict[str, Any] | None = None,
            on_publish: Callable[[DocxEditContext, str, DocxIR, set[str]], None]
            | None = None,
            allow_external_output: bool = False,
        ) -> dict[str, Any]: ...

        def _backup_before_overwrite(
            self, doc_dir: Path, max_backups: int = 5
        ) -> None: ...

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _guarded(self, run: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        """Turn failures into results; the edit-state transaction is rolled back."""
        try:
            return run()
        except DocxEditStateError as exc:
            return _error(str(exc))
        except Exception as exc:
            logger.exception("DOCX lease operation failed")
            return _error(
                f"{exc} (nothing was committed; files, revision and leases are "
                "unchanged)"
            )

    @staticmethod
    def _normalize_block_ids(block_ids: Iterable[str] | None) -> list[str]:
        if block_ids is None or isinstance(block_ids, str):
            raise DocxEditStateError(
                "block_ids must be a non-empty list of block ids "
                '(see docx(op="list_blocks"))'
            )
        ordered: list[str] = []
        for value in block_ids:
            if not isinstance(value, str) or not value.strip():
                raise DocxEditStateError("block_ids must contain non-empty strings")
            if value.strip() not in ordered:
                ordered.append(value.strip())
        if not ordered:
            raise DocxEditStateError("block_ids must not be empty")
        if len(ordered) > MAX_LEASE_BLOCKS:
            raise DocxEditStateError(
                f"A lease covers at most {MAX_LEASE_BLOCKS} blocks; split the work"
            )
        return ordered

    def _block_hash(self, block: Any) -> str:
        record = json.loads(json.dumps(self._block_to_dict(block), ensure_ascii=False))
        return block_state_hash(record)

    def _lease_for_token(
        self, context: DocxEditContext, lease_token: str | None
    ) -> BlockLease | dict[str, Any]:
        token = (lease_token or "").strip()
        if not token:
            return _error("lease_token is required (returned by checkout)")
        lease = context.session.lease_by_token_hash(lease_token_hash(token))
        if lease is not None:
            return lease
        lease_id = lease_id_for_token(token)
        event = context.session.lease_event(lease_id)
        if event is None:
            return _error(
                f"Unknown lease token for {context.ir.doc_id} ({lease_id}); it was "
                "never issued for this document or the document was re-ingested. "
                + _LEASE_GUIDANCE
            )
        reasons = {
            LEASE_EVENT_RELEASED: "was released",
            LEASE_EVENT_COMMITTED: "was already committed",
            LEASE_EVENT_BROKEN: "was broken by an administrator",
            LEASE_EVENT_RECLAIMED: "expired and its blocks were reclaimed",
        }
        reason = reasons.get(event.event, event.event)
        detail = f" ({event.detail})" if event.detail else ""
        return _error(
            f"Lease {lease_id} held by {event.holder!r} {reason} at "
            f"{iso_utc(event.at)}{detail}. Nothing was applied; check out the "
            "blocks again to continue.",
            lease_id=lease_id,
            lease_event=event.event,
        )

    # ------------------------------------------------------------------
    # checkout
    # ------------------------------------------------------------------

    async def checkout_blocks(
        self,
        doc_id: str,
        block_ids: list[str] | None,
        *,
        holder: str | None,
        ttl_seconds: int | None = None,
        wait: bool = False,
    ) -> dict[str, Any]:
        """Lease blocks for exclusive editing; fail fast on conflicts."""

        def run() -> dict[str, Any]:
            if wait:
                return _error(
                    "wait=true is not supported: checkout never blocks. Retry "
                    "after the conflicting lease is committed, released or expires "
                    '(see docx(op="leases")).'
                )
            name = validate_holder(holder)
            ttl = validate_ttl(ttl_seconds)
            requested = self._normalize_block_ids(block_ids)
            with self._edit_context(doc_id) as context:
                return self._checkout_in_context(context, requested, name, ttl)

        return self._guarded(run)

    def _checkout_in_context(
        self,
        context: DocxEditContext,
        requested: list[str],
        holder: str,
        ttl: int,
    ) -> dict[str, Any]:
        ir = context.ir
        now = context.now
        blocks = {block.id: block for block in ir.blocks}
        unknown = [bid for bid in requested if bid not in blocks]
        if unknown:
            return _error(
                f"Unknown block id(s) for {ir.doc_id}: {', '.join(unknown)}. "
                'List blocks with docx(op="list_blocks").'
            )
        scope = self._lease_scope_ids(ir, requested)
        not_leasable = [
            f"{bid} ({blocks[bid].block_type.value})"
            for bid in scope
            if blocks[bid].is_protected
            or blocks[bid].block_type not in LEASABLE_BLOCK_TYPES
        ]
        if not_leasable:
            return _error(
                "Only text/run edits of paragraphs, headings, list items, "
                "captions, mixed-format paragraphs and tables can be leased; "
                f"not leasable: {', '.join(not_leasable)}. Protected/structural "
                "blocks (charts, TOC, fields, images, breaks, headers, footers) "
                "are edited in Word or through native DOCX operations."
            )
        if len(scope) > MAX_LEASE_BLOCKS:
            return _error(
                f"The checkout expands to {len(scope)} blocks (table families are "
                f"leased whole); a lease covers at most {MAX_LEASE_BLOCKS}."
            )

        conflicts: list[dict[str, Any]] = []
        reclaim: list[BlockLease] = []
        for lease in context.session.leases_covering(scope):
            if lease.is_live(now):
                conflicts.append(self._lease_conflict(lease, scope, now))
            else:
                reclaim.append(lease)
        if conflicts:
            return _error(
                "Checkout refused: "
                + self._describe_lease_conflicts(conflicts)
                + ". Nothing was leased. Coordinate with the holder, pick other "
                "blocks, or retry after it commits, releases or expires.",
                conflicts=conflicts,
            )
        live = [lease for lease in context.session.leases() if lease.is_live(now)]
        if len(live) >= MAX_LIVE_LEASES:
            return _error(
                f"{ir.doc_id} already has {len(live)} live leases (limit "
                f"{MAX_LIVE_LEASES}); commit or release some first."
            )
        for lease in reclaim:
            context.session.delete_lease(
                lease.lease_id,
                event=LEASE_EVENT_RECLAIMED,
                detail=f"reclaimed by {holder!r}",
                now=now,
            )

        token = secrets.token_urlsafe(32)
        hashes = context.block_hashes
        lease = BlockLease(
            lease_id=lease_id_for_token(token),
            holder=holder,
            block_ids=tuple(scope),
            base_hashes={bid: hashes[bid] for bid in scope},
            created_at=now,
            expires_at=now + ttl,
            ttl_seconds=ttl,
            base_revision=context.revision,
        )
        context.session.insert_lease(lease, lease_token_hash(token))
        fragments = [
            {
                "block_id": bid,
                "type": blocks[bid].block_type.value,
                "base_hash": hashes[bid],
                "dfm": self.renderer.render_block(blocks[bid]) or "",
            }
            for bid in scope
        ]
        result: dict[str, Any] = {
            "success": True,
            "doc_id": ir.doc_id,
            "lease_token": token,
            "lease_id": lease.lease_id,
            "holder": holder,
            "revision": context.revision,
            "ttl_seconds": ttl,
            "expires_at": iso_utc(lease.expires_at),
            "block_ids": list(scope),
            "blocks": fragments,
            "wait": False,
            "next": (
                'Edit only these fragments, then docx(op="commit", doc_id, '
                "lease_token, edits={block_id: edited_fragment}). Keep each "
                "fragment's marker line. Release with op='release' if you stop; "
                "do not hold the lease while idle."
            ),
        }
        expanded = [bid for bid in scope if bid not in requested]
        if expanded:
            result["expanded_block_ids"] = expanded
        if reclaim:
            result["reclaimed_expired_leases"] = [lease.lease_id for lease in reclaim]
        return result

    # ------------------------------------------------------------------
    # commit
    # ------------------------------------------------------------------

    async def commit_block_lease(
        self,
        doc_id: str,
        lease_token: str | None,
        edits: Mapping[str, str] | None,
        *,
        output_path: str | None = None,
        track_changes: bool = False,
        revision_author: str | None = None,
        revision_base: str = "original",
        keep_lease: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Apply the leased blocks' edits on top of the current document."""
        from src.application.docx_service import REVISION_BASES

        def run() -> dict[str, Any]:
            if revision_base not in REVISION_BASES:
                return _error(
                    f"Unsupported revision_base {revision_base!r}; use one of: "
                    + ", ".join(sorted(REVISION_BASES))
                )
            checked, problem = self._validate_edit_payload(edits)
            if problem is not None or checked is None:
                return problem or _error("edits are invalid")
            with self._edit_context(doc_id) as context:
                return self._commit_in_context(
                    context,
                    lease_token,
                    checked,
                    output_path=output_path,
                    track_changes=track_changes,
                    revision_author=revision_author,
                    revision_base=revision_base,
                    keep_lease=keep_lease,
                    force=force,
                )

        return self._guarded(run)

    @staticmethod
    def _validate_edit_payload(
        edits: Mapping[str, str] | None,
    ) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
        """Return ``(edits, None)`` or ``(None, error_result)``."""
        if not isinstance(edits, dict) or not edits:
            return None, _error(
                "edits must be a non-empty mapping {block_id: edited DFM fragment}"
            )
        checked: dict[str, str] = {}
        total = 0
        for block_id, text in edits.items():
            if not isinstance(block_id, str) or not isinstance(text, str):
                return None, _error("edits keys and values must be strings")
            try:
                cleaned = normalize_text_input(text, hint=f"edits[{block_id}]")
            except EncodingError as exc:
                return None, _error(str(exc))
            total += len(cleaned.encode("utf-8"))
            checked[block_id.strip()] = cleaned
        if total > MAX_DFM_BYTES:
            return None, _error("edits exceed the 4 MiB UTF-8 limit")
        if len(checked) > MAX_LEASE_BLOCKS:
            return None, _error(f"A commit carries at most {MAX_LEASE_BLOCKS} blocks")
        return checked, None

    def _commit_in_context(
        self,
        context: DocxEditContext,
        lease_token: str | None,
        edits: dict[str, str],
        *,
        output_path: str | None,
        track_changes: bool,
        revision_author: str | None,
        revision_base: str,
        keep_lease: bool,
        force: bool,
    ) -> dict[str, Any]:
        now = context.now
        lease = self._lease_for_token(context, lease_token)
        if isinstance(lease, dict):
            return lease
        if not lease.is_live(now):
            return _error(
                f"Lease {lease.lease_id} held by {lease.holder!r} expired at "
                f"{iso_utc(lease.expires_at)}. Nothing was applied. Check out the "
                "blocks again (renew live leases before they expire).",
                lease_id=lease.lease_id,
            )
        not_leased = sorted(set(edits) - set(lease.block_ids))
        if not_leased:
            return _error(
                f"Commit refused: block(s) {', '.join(not_leased)} are not in lease "
                f"{lease.lease_id} (it covers {', '.join(lease.block_ids)}). "
                "Nothing was applied; check them out first.",
                lease_id=lease.lease_id,
            )

        parse_result = self._parse_lease_fragments(context, edits)
        if isinstance(parse_result, dict):
            return parse_result

        # Leased blocks can only change through this lease, so each must still
        # be in its checked-out state. An identical edit already present (an
        # interrupted earlier commit) is accepted as already applied.
        hashes = context.block_hashes
        already_applied: list[str] = []
        for block_id in edits:
            if hashes.get(block_id) == lease.base_hashes.get(block_id):
                continue
            if self._edit_is_noop(context.ir, parse_result, block_id):
                already_applied.append(block_id)
                continue
            return _error(
                f"Commit refused: block {block_id} changed since checkout (base "
                f"{lease.base_hashes.get(block_id)}, current {hashes.get(block_id)}). "
                "Leased blocks change only through their lease, so this indicates "
                "an external ir.json edit. Release this lease, check out again and "
                "re-apply your edit.",
                lease_id=lease.lease_id,
            )
        if already_applied:
            parse_result.edits = [
                edit
                for edit in parse_result.edits
                if edit.block_id not in already_applied
            ]

        author = (revision_author or "").strip() or lease.holder
        ttl = lease.ttl_seconds

        def on_publish(
            ctx: DocxEditContext, new_revision: str, new_ir: DocxIR, _edited: set[str]
        ) -> None:
            if keep_lease:
                new_hashes = {
                    block.id: self._block_hash(block)
                    for block in new_ir.blocks
                    if block.id in lease.base_hashes
                }
                ctx.session.update_lease(
                    lease.lease_id,
                    expires_at=now + ttl,
                    ttl_seconds=ttl,
                    base_hashes=new_hashes,
                    base_revision=new_revision,
                )
            else:
                ctx.session.delete_lease(
                    lease.lease_id,
                    event=LEASE_EVENT_COMMITTED,
                    detail=f"committed revision {new_revision}",
                    now=now,
                )

        result = self._write_back_locked(
            context,
            parse_result,
            output_path,
            force=force,
            track_changes=track_changes,
            revision_author=author,
            revision_base=revision_base,
            kind=REVISION_KIND_COMMIT,
            actor=lease.holder,
            result_extra={
                "lease_id": lease.lease_id,
                "holder": lease.holder,
                "committed_block_ids": sorted(edits),
            },
            on_publish=on_publish,
        )
        if result.get("success"):
            result["lease_released"] = not keep_lease
            if keep_lease:
                result["lease_expires_at"] = iso_utc(now + ttl)
            if already_applied:
                result["already_applied_block_ids"] = sorted(already_applied)
        return result

    def _parse_lease_fragments(
        self, context: DocxEditContext, edits: dict[str, str]
    ) -> DfmParseResult | dict[str, Any]:
        """Parse edited fragments, accepting each block's own marker only."""
        ir = context.ir
        blocks = {block.id: block for block in ir.blocks}
        fragments: list[str] = []
        order = [block.id for block in ir.blocks if block.id in edits]
        for block_id in order:
            block = blocks[block_id]
            text = edits[block_id].strip("\n")
            expected = (
                "table"
                if block.block_type == DfmBlockType.TABLE
                else "format"
                if block.block_type == DfmBlockType.FORMAT
                else None
            )
            markers = _FRAGMENT_MARKER_RE.findall(text)
            if markers:
                kinds = {kind or None for kind, _ in markers}
                ids = {bid for _, bid in markers}
                if len(markers) != 1 or ids != {block_id}:
                    return _error(
                        f"edits[{block_id}] must contain exactly one block marker, "
                        f"its own (<!-- ... @b:{block_id} ... -->); found "
                        f"{', '.join(sorted(ids))}. Edits to other blocks need "
                        "their own lease."
                    )
                if kinds != {expected}:
                    return _error(
                        f"edits[{block_id}] changes the block kind; keep the marker "
                        "returned by checkout (structural edits are not supported)."
                    )
                if not text.lstrip().startswith("<!--"):
                    return _error(
                        f"edits[{block_id}] must start with its marker line as "
                        "returned by checkout."
                    )
                fragment = text
                body = text.split("\n", 1)[1] if "\n" in text else ""
            else:
                if _FRAGMENT_CLOSE_RE.search(text):
                    return _error(
                        f"edits[{block_id}] has a closing marker without its "
                        "opening marker; send the fragment as returned by checkout."
                    )
                body = text
                if expected == "table":
                    fragment = (
                        f"<!-- dfm:table @b:{block_id} -->\n{text}\n<!-- /dfm:table -->"
                    )
                elif expected == "format":
                    fragment = f"<!-- dfm:format @b:{block_id} -->\n{text}\n<!-- /dfm:format -->"
                else:
                    fragment = f"<!-- @b:{block_id} -->\n{text}"
            if expected is None and _TRIPLE_BLANK_RE.search(body):
                return _error(
                    f"edits[{block_id}] contains two consecutive blank lines, which "
                    "end a DFM block; keep paragraph text contiguous."
                )
            fragments.append(fragment)

        header = yaml.safe_dump(
            {"doc_id": ir.doc_id, "checksum": ir.checksum}, allow_unicode=True
        )
        dfm = "---\n" + header + "---\n\n" + "\n\n".join(fragments) + "\n"
        parse_result = self.parser.parse(dfm)
        if parse_result.errors:
            return _error(
                "Could not parse the edited fragments: "
                + "; ".join(parse_result.errors[:5])
            )
        parsed_ids = [edit.block_id for edit in parse_result.edits]
        if sorted(parsed_ids) != sorted(order):
            return _error(
                "Edited fragments must yield exactly one edit per submitted block "
                f"(expected {', '.join(order)}, parsed {', '.join(parsed_ids) or 'none'})."
            )
        parse_result.revision = context.revision
        return parse_result

    def _edit_is_noop(
        self, ir: DocxIR, parse_result: DfmParseResult, block_id: str
    ) -> bool:
        block = ir.find_block(block_id)
        if block is None:
            return False
        probe = DocxIR(
            doc_id=ir.doc_id,
            source_path=ir.source_path,
            checksum=ir.checksum,
            blocks=[deepcopy(block)],
        )
        single = deepcopy(parse_result)
        single.edits = [edit for edit in single.edits if edit.block_id == block_id]
        return not self._expected_changed_block_ids(probe, single)

    # ------------------------------------------------------------------
    # release / renew / list / break
    # ------------------------------------------------------------------

    async def release_block_lease(
        self, doc_id: str, lease_token: str | None
    ) -> dict[str, Any]:
        """Give leased blocks back without editing (expired leases too)."""

        def run() -> dict[str, Any]:
            with self._edit_context(doc_id) as context:
                lease = self._lease_for_token(context, lease_token)
                if isinstance(lease, dict):
                    return lease
                was_live = lease.is_live(context.now)
                context.session.delete_lease(
                    lease.lease_id,
                    event=LEASE_EVENT_RELEASED,
                    detail="released by holder"
                    if was_live
                    else "released after expiry",
                    now=context.now,
                )
                return {
                    "success": True,
                    "doc_id": context.ir.doc_id,
                    "lease_id": lease.lease_id,
                    "holder": lease.holder,
                    "released_block_ids": list(lease.block_ids),
                    "was_expired": not was_live,
                }

        return self._guarded(run)

    async def renew_block_lease(
        self, doc_id: str, lease_token: str | None, ttl_seconds: int | None = None
    ) -> dict[str, Any]:
        """Extend a live lease to ``now + ttl_seconds`` (default: its own TTL)."""

        def run() -> dict[str, Any]:
            with self._edit_context(doc_id) as context:
                lease = self._lease_for_token(context, lease_token)
                if isinstance(lease, dict):
                    return lease
                if not lease.is_live(context.now):
                    return _error(
                        f"Lease {lease.lease_id} expired at "
                        f"{iso_utc(lease.expires_at)} and cannot be renewed; check "
                        "the blocks out again.",
                        lease_id=lease.lease_id,
                    )
                ttl = validate_ttl(
                    ttl_seconds if ttl_seconds is not None else lease.ttl_seconds
                )
                expires_at = context.now + ttl
                context.session.update_lease(
                    lease.lease_id, expires_at=expires_at, ttl_seconds=ttl
                )
                return {
                    "success": True,
                    "doc_id": context.ir.doc_id,
                    "lease_id": lease.lease_id,
                    "holder": lease.holder,
                    "block_ids": list(lease.block_ids),
                    "ttl_seconds": ttl,
                    "expires_at": iso_utc(expires_at),
                }

        return self._guarded(run)

    async def list_block_leases(self, doc_id: str) -> dict[str, Any]:
        """List live and expired leases (never tokens) plus the revision."""

        def run() -> dict[str, Any]:
            ir = self._load_ir(doc_id)
            if ir is None:
                return _error(f"IR not found for {doc_id}")
            store = self._edit_state_store(self.repository.get_doc_dir(doc_id))
            now = self._clock()
            with store.session(write=False) as session:
                leases = [lease.to_public_dict(now) for lease in session.leases()]
                latest = session.latest_revision()
                history = session.revision_count()
            return {
                "success": True,
                "doc_id": doc_id,
                "revision": self.ir_revision(ir),
                "last_recorded_revision": latest.revision if latest else None,
                "last_change": (
                    {
                        "kind": latest.kind,
                        "actor": latest.actor,
                        "at": iso_utc(latest.created_at),
                        "changed_block_ids": list(latest.changed_block_ids),
                    }
                    if latest
                    else None
                ),
                "retained_revisions": history,
                "leases": leases,
                "live_leases": sum(1 for lease in leases if lease["status"] == "live"),
            }

        return self._guarded(run)

    async def break_block_lease(
        self, doc_id: str, lease_id: str | None, *, force: bool = False
    ) -> dict[str, Any]:
        """Administrative removal of an expired (or, with force, live) lease."""

        def run() -> dict[str, Any]:
            wanted = (lease_id or "").strip()
            if not wanted:
                return _error('lease_id is required (see docx(op="leases"))')
            with self._edit_context(doc_id) as context:
                lease = context.session.lease(wanted)
                if lease is None:
                    event = context.session.lease_event(wanted)
                    suffix = (
                        f"; it was {event.event} at {iso_utc(event.at)}"
                        if event
                        else ""
                    )
                    return _error(f"No lease {wanted} on {doc_id}{suffix}.")
                live = lease.is_live(context.now)
                if live and not force:
                    return _error(
                        f"Lease {wanted} held by {lease.holder!r} is live until "
                        f"{iso_utc(lease.expires_at)}. Breaking it makes the holder's "
                        "pending commit fail. Ask the holder to release it or wait "
                        "for expiry; pass force=true only after confirming the "
                        "holder is gone.",
                        lease=lease.to_public_dict(context.now),
                    )
                context.session.delete_lease(
                    wanted,
                    event=LEASE_EVENT_BROKEN,
                    detail="live lease broken with force"
                    if live
                    else "expired lease broken",
                    now=context.now,
                )
                return {
                    "success": True,
                    "doc_id": doc_id,
                    "lease_id": wanted,
                    "holder": lease.holder,
                    "released_block_ids": list(lease.block_ids),
                    "was_live": live,
                }

        return self._guarded(run)

    # ------------------------------------------------------------------
    # Lease-aware IR-only block updates (docx_table_from_context)
    # ------------------------------------------------------------------

    async def update_ir_blocks(
        self,
        doc_id: str,
        block_ids: list[str],
        mutate: Callable[[DocxIR], None],
        *,
        actor: str,
        write_dfm: bool = True,
    ) -> dict[str, Any]:
        """Mutate named blocks of the current IR under the document lock.

        ``mutate`` may raise ``ValueError`` to abort without writing. Blocks
        leased by any holder are refused; other blocks must stay unchanged.
        The new state is recorded as a revision, so stale DFMs merge around it.
        """

        def run() -> dict[str, Any]:
            with self._edit_context(doc_id) as context:
                conflicts = self._live_lease_conflicts(context, block_ids)
                if conflicts:
                    return _error(
                        "Update refused: "
                        + self._describe_lease_conflicts(conflicts)
                        + ". Commit through that lease or wait for its release.",
                        leased_blocks=conflicts,
                    )
                ir = context.ir
                before = deepcopy(ir)
                try:
                    mutate(ir)
                except ValueError as exc:
                    return _error(str(exc))
                unexpected = self._detect_unedited_block_mutations(
                    before, ir, set(block_ids)
                )
                if unexpected:
                    return _error(
                        "Update touched blocks outside its target; nothing written.",
                        warnings=unexpected,
                    )
                state = self._ir_revision_state(ir)
                ir.dfm_revision = state[0]
                previous = context.block_hashes
                changed = [bid for bid, h in state[1] if previous.get(bid) != h]
                revision = self._record_revision_state(
                    context,
                    state,
                    kind=REVISION_KIND_BLOCK_UPDATE,
                    actor=actor,
                    changed_block_ids=changed,
                )
                doc_dir = context.doc_dir
                self._backup_before_overwrite(doc_dir)
                self._save_ir(ir, doc_dir / "ir.json")
                written: list[str] = [str(doc_dir / "ir.json")]
                if write_dfm:
                    dfm_text = self.renderer.render(ir)
                    md_text, yaml_text = self.renderer.render_split(ir)
                    for name, text in (
                        ("content.dfm", dfm_text),
                        ("content.md", md_text),
                        ("format.yaml", yaml_text),
                    ):
                        write_utf8_text_atomic(doc_dir / name, text, hint=name)
                        written.append(str(doc_dir / name))
                return {
                    "success": True,
                    "doc_id": doc_id,
                    "revision": revision,
                    "previous_revision": context.revision,
                    "changed_block_ids": changed,
                    "written": written,
                }

        return self._guarded(run)
