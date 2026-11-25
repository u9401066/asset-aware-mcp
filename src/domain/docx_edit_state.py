"""Domain rules for concurrent DFM/DOCX editing: content revisions and block leases.

Several agents (separate MCP server processes included) may edit one ingested
DOCX at the same time. Two mechanisms keep their work from being lost:

* **Content revisions** -- every saved document state has a content-addressed
  ``revision`` (a hash of the source checksum plus every block's persisted
  state). It is stamped into the DFM front matter, so a full-DFM save can prove
  which state it was based on. A stale save is either applied as a 3-way merge
  (only the blocks the submitter changed, none of which anyone else changed) or
  rejected with the conflicting block ids. It is never silently written over
  newer edits.
* **Block leases** -- an agent checks out the blocks it will edit, receives a
  secret lease token and each block's base hash, and later commits only those
  blocks on top of the then-current document. Other holders cannot check out or
  save the leased blocks until the lease is released, committed or expires.

This module contains only pure rules and value objects; persistence lives in
infrastructure and orchestration in the application layer.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

REVISION_PREFIX = "rev-"
BLOCK_HASH_PREFIX = "sha256:"
LEASE_ID_PREFIX = "lease-"

DEFAULT_LEASE_TTL_SECONDS = 900
MIN_LEASE_TTL_SECONDS = 1
MAX_LEASE_TTL_SECONDS = 3600
MAX_LEASE_BLOCKS = 500
MAX_LIVE_LEASES = 256
MAX_HOLDER_CHARS = 200
DEFAULT_REVISION_HISTORY_LIMIT = 50
MAX_LEASE_EVENTS = 500

# Revision record kinds.
REVISION_KIND_INGEST = "ingest"  # root taken from baseline_ir.json
REVISION_KIND_ADOPTED = "adopted"  # state found when tracking began
REVISION_KIND_SAVE = "save"  # full-DFM save_docx
REVISION_KIND_COMMIT = "commit"  # lease commit
REVISION_KIND_BLOCK_UPDATE = "block_update"  # e.g. docx_table_from_context
REVISION_KIND_EXTERNAL = "external"  # ir.json changed outside a tracked write

# Lease lifecycle events (kept as bounded tombstones for clear errors).
LEASE_EVENT_RELEASED = "released"
LEASE_EVENT_COMMITTED = "committed"
LEASE_EVENT_BROKEN = "broken"
LEASE_EVENT_RECLAIMED = "expired_reclaimed"


class DocxEditStateError(ValueError):
    """A revision/lease rule refused the operation; nothing was changed."""


class DocxDocumentBusyError(DocxEditStateError):
    """Another save/commit/checkout holds the document write lock too long."""


def canonical_json(value: Any) -> str:
    """Deterministic JSON used for every revision/block hash."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def block_state_hash(block_record: Mapping[str, Any]) -> str:
    """Hash of one block's persisted state (the ``ir.json`` block record)."""
    digest = hashlib.sha256(canonical_json(block_record).encode("utf-8"))
    return BLOCK_HASH_PREFIX + digest.hexdigest()


def content_revision(checksum: str, entries: Sequence[tuple[str, str]]) -> str:
    """Content-addressed document revision.

    ``checksum`` binds the revision to the source package; ``entries`` are the
    ordered ``(block_id, block_state_hash)`` pairs. Identical content always
    yields the same revision, so the value can be recomputed from ``ir.json``
    at any time (crash recovery needs no separate "current revision" pointer).
    """
    payload = canonical_json(
        {"checksum": checksum, "blocks": [[bid, h] for bid, h in entries]}
    )
    return REVISION_PREFIX + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def lease_token_hash(token: str) -> str:
    """Only the SHA-256 of a lease token is persisted."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def lease_id_for_token(token: str) -> str:
    """Public, non-secret lease identifier derived from the token hash."""
    return LEASE_ID_PREFIX + lease_token_hash(token)[:16]


def iso_utc(timestamp: float) -> str:
    """Render a POSIX timestamp as an ISO-8601 UTC string."""
    return (
        datetime.fromtimestamp(timestamp, tz=timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def validate_holder(holder: str | None) -> str:
    """Return a normalized lease holder name or raise ``DocxEditStateError``."""
    value = (holder or "").strip()
    if not value:
        raise DocxEditStateError(
            "holder is required: name the agent/session that will edit the blocks "
            "(for example 'claude-subagent-methods'). It becomes the default "
            "Track Changes author."
        )
    if len(value) > MAX_HOLDER_CHARS:
        raise DocxEditStateError(f"holder exceeds {MAX_HOLDER_CHARS} characters")
    if any(ord(char) < 32 for char in value):
        raise DocxEditStateError("holder must not contain control characters")
    return value


def validate_ttl(ttl_seconds: int | None) -> int:
    """Return a bounded lease TTL in seconds or raise ``DocxEditStateError``."""
    if ttl_seconds is None:
        return DEFAULT_LEASE_TTL_SECONDS
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int):
        raise DocxEditStateError("ttl_seconds must be an integer number of seconds")
    if not MIN_LEASE_TTL_SECONDS <= ttl_seconds <= MAX_LEASE_TTL_SECONDS:
        raise DocxEditStateError(
            f"ttl_seconds must be between {MIN_LEASE_TTL_SECONDS} and "
            f"{MAX_LEASE_TTL_SECONDS}; renew a live lease instead of holding a "
            "long one"
        )
    return ttl_seconds


@dataclass(frozen=True)
class BlockLease:
    """A live or expired checkout of a set of blocks by one holder."""

    lease_id: str
    holder: str
    block_ids: tuple[str, ...]
    base_hashes: Mapping[str, str]
    created_at: float
    expires_at: float
    ttl_seconds: int
    base_revision: str

    def is_live(self, now: float) -> bool:
        return now < self.expires_at

    def to_public_dict(self, now: float) -> dict[str, Any]:
        """Listing view; never contains the secret token."""
        live = self.is_live(now)
        return {
            "lease_id": self.lease_id,
            "holder": self.holder,
            "block_ids": list(self.block_ids),
            "status": "live" if live else "expired",
            "created_at": iso_utc(self.created_at),
            "expires_at": iso_utc(self.expires_at),
            "remaining_seconds": max(0, int(self.expires_at - now)) if live else 0,
            "ttl_seconds": self.ttl_seconds,
            "base_revision": self.base_revision,
        }


@dataclass(frozen=True)
class LeaseEvent:
    """Tombstone describing why a lease no longer exists."""

    lease_id: str
    holder: str
    event: str
    at: float
    detail: str = ""


@dataclass(frozen=True)
class RevisionRecord:
    """One retained document revision."""

    revision: str
    seq: int
    parent: str | None
    kind: str
    actor: str | None
    created_at: float
    changed_block_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ThreeWayPlan:
    """Outcome of merging a stale full-DFM save onto the current state."""

    apply_block_ids: frozenset[str]
    theirs_block_ids: frozenset[str]
    conflict_block_ids: frozenset[str]
    already_applied_block_ids: frozenset[str] = field(default_factory=frozenset)


def plan_three_way_merge(
    base_hashes: Mapping[str, str],
    current_hashes: Mapping[str, str],
    ours_changed: Iterable[str],
    already_applied: Iterable[str] = (),
) -> ThreeWayPlan:
    """Classify a stale save.

    * ``ours_changed``: blocks the submitter changed relative to its base revision.
    * ``theirs``: blocks whose current state differs from the base revision.
    * A block in both sets conflicts unless the submitter's result equals the
      current state (``already_applied``: identical edit, e.g. a retried save).
    """
    ours = frozenset(ours_changed)
    applied = frozenset(already_applied) & ours
    theirs = frozenset(
        block_id
        for block_id, current in current_hashes.items()
        if base_hashes.get(block_id) != current
    )
    overlap = ours & theirs
    conflicts = overlap - applied
    return ThreeWayPlan(
        apply_block_ids=ours - theirs,
        theirs_block_ids=theirs,
        conflict_block_ids=conflicts,
        already_applied_block_ids=overlap & applied,
    )


def lease_scope(
    ordered_block_ids: Sequence[str],
    parent_table_ids: Mapping[str, str | None],
    requested: Iterable[str],
) -> list[str]:
    """Expand a checkout to whole table families, in document order.

    A nested table's text lives inside its parent table's cell, so a parent table
    and every table nested in it (transitively) are leased as one unit. Other
    blocks lease individually.
    """

    def root_of(block_id: str) -> str:
        seen: set[str] = set()
        current = block_id
        while True:
            parent = parent_table_ids.get(current)
            if not parent or parent in seen or parent not in parent_table_ids:
                return current
            seen.add(current)
            current = parent

    roots = {root_of(block_id) for block_id in requested}
    return [block_id for block_id in ordered_block_ids if root_of(block_id) in roots]


class DocxEditSession(Protocol):
    """One serialized (cross-process) unit of work on a document's edit state.

    Implementations hold an exclusive document write lock for the lifetime of the
    session; all changes commit atomically when the session ends normally and are
    rolled back when it raises.
    """

    history_limit: int

    # -- revisions ---------------------------------------------------------
    def root(self) -> RevisionRecord | None: ...

    def create_root(
        self,
        revision: str,
        kind: str,
        entries: Sequence[tuple[str, str]],
        payloads: Mapping[str, Mapping[str, Any]],
        *,
        now: float,
    ) -> RevisionRecord: ...

    def revision(self, revision: str) -> RevisionRecord | None: ...

    def latest_revision(self) -> RevisionRecord | None: ...

    def revision_count(self) -> int: ...

    def revision_manifest(self, revision: str) -> dict[str, str] | None: ...

    def block_payload(self, block_hash: str) -> dict[str, Any] | None: ...

    def record_revision(
        self,
        revision: str,
        *,
        parent: str | None,
        kind: str,
        actor: str | None,
        changed_block_ids: Sequence[str],
        entries: Sequence[tuple[str, str]],
        payloads: Mapping[str, Mapping[str, Any]],
        now: float,
    ) -> RevisionRecord | None: ...

    def reset(self) -> None: ...

    # -- leases ------------------------------------------------------------
    def leases(self) -> list[BlockLease]: ...

    def lease(self, lease_id: str) -> BlockLease | None: ...

    def lease_by_token_hash(self, token_hash: str) -> BlockLease | None: ...

    def leases_covering(self, block_ids: Iterable[str]) -> list[BlockLease]: ...

    def insert_lease(self, lease: BlockLease, token_hash: str) -> None: ...

    def update_lease(
        self,
        lease_id: str,
        *,
        expires_at: float,
        ttl_seconds: int,
        base_hashes: Mapping[str, str] | None = None,
        base_revision: str | None = None,
    ) -> None: ...

    def delete_lease(
        self, lease_id: str, *, event: str, detail: str, now: float
    ) -> None: ...

    def lease_event(self, lease_id: str) -> LeaseEvent | None: ...

    # -- per-block Track Changes attribution -------------------------------
    def block_authors(self) -> dict[str, str]: ...

    def set_block_authors(
        self, block_ids: Iterable[str], author: str, revision: str
    ) -> None: ...

    def retain_block_authors(self, block_ids: Iterable[str]) -> None: ...
