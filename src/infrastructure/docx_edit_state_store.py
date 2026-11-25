"""SQLite persistence for DOCX content revisions and block leases.

One database lives in each DOCX document directory. Every session opens its own
connection and starts with ``BEGIN IMMEDIATE``, which takes SQLite's RESERVED
lock: only one writer per document can be inside a session at a time, across
threads *and* separate MCP server processes (Copilot, Cline and Codex may run
their own servers on the same DATA_DIR). The lock is waited for up to a bounded
busy timeout, never indefinitely, and is released by the OS if a process dies;
an interrupted transaction is rolled back from SQLite's journal on next open.

Storage is compact: the first tracked state (the root, normally the ingest
baseline) stores every block once; later revisions store only a delta of
``block_id -> block hash`` for blocks that differ from the root. Block payloads
are content-addressed, zlib-compressed JSON. Only the newest ``history_limit``
revisions (plus the root) are retained; unreferenced payloads are deleted.
"""

from __future__ import annotations

import json
import sqlite3
import zlib
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from src.domain.docx_edit_state import (
    DEFAULT_REVISION_HISTORY_LIMIT,
    MAX_LEASE_EVENTS,
    BlockLease,
    DocxDocumentBusyError,
    DocxEditStateError,
    LeaseEvent,
    RevisionRecord,
    canonical_json,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping, Sequence
    from pathlib import Path

EDIT_STATE_DB_FILENAME = "edit_state.sqlite3"
EDIT_STATE_SCHEMA_VERSION = "1"
DEFAULT_LOCK_TIMEOUT_SECONDS = 30.0

_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS block_payloads (
        hash TEXT PRIMARY KEY,
        data BLOB NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS root_manifest (
        position INTEGER PRIMARY KEY,
        block_id TEXT NOT NULL UNIQUE,
        hash TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS revisions (
        revision TEXT PRIMARY KEY,
        seq INTEGER NOT NULL UNIQUE,
        parent TEXT,
        kind TEXT NOT NULL,
        actor TEXT,
        created_at REAL NOT NULL,
        changed_blocks TEXT NOT NULL,
        delta BLOB NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS leases (
        lease_id TEXT PRIMARY KEY,
        token_sha256 TEXT NOT NULL UNIQUE,
        holder TEXT NOT NULL,
        created_at REAL NOT NULL,
        expires_at REAL NOT NULL,
        ttl_seconds INTEGER NOT NULL,
        base_revision TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS lease_blocks (
        block_id TEXT PRIMARY KEY,
        lease_id TEXT NOT NULL REFERENCES leases(lease_id) ON DELETE CASCADE,
        position INTEGER NOT NULL,
        base_hash TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS lease_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lease_id TEXT NOT NULL,
        holder TEXT NOT NULL,
        event TEXT NOT NULL,
        at REAL NOT NULL,
        detail TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS lease_events_lease ON lease_events(lease_id)",
    """
    CREATE TABLE IF NOT EXISTS block_authors (
        block_id TEXT PRIMARY KEY,
        author TEXT NOT NULL,
        revision TEXT NOT NULL
    )
    """,
)


_LEASE_COLUMNS = (
    "SELECT lease_id, holder, created_at, expires_at, ttl_seconds, base_revision "
    "FROM leases"
)
_LEASE_QUERIES = {
    "all": _LEASE_COLUMNS + " ORDER BY created_at, lease_id",
    "lease_id": _LEASE_COLUMNS + " WHERE lease_id=?",
    "token": _LEASE_COLUMNS + " WHERE token_sha256=?",
}


def _compress(value: Any) -> bytes:
    return zlib.compress(canonical_json(value).encode("utf-8"), 6)


def _decompress(blob: bytes) -> Any:
    return json.loads(zlib.decompress(blob).decode("utf-8"))


class SqliteDocxEditStateStore:
    """Factory for serialized edit-state sessions of one document directory."""

    def __init__(
        self,
        doc_dir: Path,
        *,
        timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
        history_limit: int = DEFAULT_REVISION_HISTORY_LIMIT,
    ):
        self.path = doc_dir / EDIT_STATE_DB_FILENAME
        self.timeout_seconds = timeout_seconds
        self.history_limit = max(1, history_limit)

    @contextmanager
    def session(self, *, write: bool = True) -> Iterator[SqliteDocxEditSession]:
        """Open one transaction; ``write`` sessions are exclusive per document."""
        if self.path.is_symlink():
            raise DocxEditStateError("DOCX edit-state database cannot be a symlink")
        connection = sqlite3.connect(
            str(self.path),
            timeout=self.timeout_seconds,
            isolation_level=None,
        )
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            try:
                connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            except sqlite3.OperationalError as exc:
                if _is_busy(exc):
                    raise DocxDocumentBusyError(
                        "Document is busy: another save/commit/checkout is still "
                        f"running after {self.timeout_seconds:.0f}s. Retry shortly; "
                        "nothing was changed."
                    ) from exc
                raise
            session = SqliteDocxEditSession(connection, self.history_limit)
            try:
                if write:
                    session.ensure_schema()
                elif not session.has_schema():
                    session.read_only_empty = True
                yield session
            except BaseException:
                connection.execute("ROLLBACK")
                raise
            try:
                connection.execute("COMMIT")
            except sqlite3.OperationalError as exc:
                connection.execute("ROLLBACK")
                if _is_busy(exc):
                    raise DocxDocumentBusyError(
                        "Document is busy: the edit-state commit timed out. Any "
                        "content already written is recorded as an external "
                        "revision by the next operation; retry (a retried commit "
                        "is recognised as already applied)."
                    ) from exc
                raise
        finally:
            connection.close()


def _is_busy(exc: sqlite3.OperationalError) -> bool:
    message = str(exc).lower()
    return "locked" in message or "busy" in message


class SqliteDocxEditSession:
    """Revision and lease operations inside one SQLite transaction."""

    def __init__(self, connection: sqlite3.Connection, history_limit: int):
        self.connection = connection
        self.history_limit = history_limit
        self.read_only_empty = False

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def has_schema(self) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='meta'"
        ).fetchone()
        return row is not None

    def ensure_schema(self) -> None:
        for statement in _SCHEMA:
            self.connection.execute(statement)
        row = self.connection.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
        if row is None:
            self.connection.execute(
                "INSERT INTO meta(key, value) VALUES('schema_version', ?)",
                (EDIT_STATE_SCHEMA_VERSION,),
            )
        elif row[0] != EDIT_STATE_SCHEMA_VERSION:
            raise DocxEditStateError(
                f"Unsupported DOCX edit-state schema {row[0]!r}; this server "
                f"supports {EDIT_STATE_SCHEMA_VERSION!r}. Upgrade asset-aware-mcp "
                "on every client that edits this document."
            )

    # ------------------------------------------------------------------
    # Revisions
    # ------------------------------------------------------------------

    @staticmethod
    def _record(row: Sequence[Any]) -> RevisionRecord:
        return RevisionRecord(
            revision=row[0],
            seq=row[1],
            parent=row[2],
            kind=row[3],
            actor=row[4],
            created_at=row[5],
            changed_block_ids=tuple(json.loads(row[6])),
        )

    _RECORD_COLUMNS = "revision, seq, parent, kind, actor, created_at, changed_blocks"

    def root(self) -> RevisionRecord | None:
        if self.read_only_empty:
            return None
        row = self.connection.execute(
            f"SELECT {self._RECORD_COLUMNS} FROM revisions "  # noqa: S608
            "WHERE revision=(SELECT value FROM meta WHERE key='root_revision')"
        ).fetchone()
        return self._record(row) if row else None

    def create_root(
        self,
        revision: str,
        kind: str,
        entries: Sequence[tuple[str, str]],
        payloads: Mapping[str, Mapping[str, Any]],
        *,
        now: float,
    ) -> RevisionRecord:
        if self.root() is not None:
            raise DocxEditStateError("Revision root already exists")
        self._store_payloads(payloads)
        self.connection.executemany(
            "INSERT INTO root_manifest(position, block_id, hash) VALUES(?, ?, ?)",
            [(index, bid, h) for index, (bid, h) in enumerate(entries)],
        )
        self.connection.execute(
            "INSERT INTO revisions(revision, seq, parent, kind, actor, created_at, "
            "changed_blocks, delta) VALUES(?, 1, NULL, ?, NULL, ?, '[]', ?)",
            (revision, kind, now, _compress({})),
        )
        self.connection.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('root_revision', ?)",
            (revision,),
        )
        record = self.revision(revision)
        assert record is not None
        return record

    def revision(self, revision: str) -> RevisionRecord | None:
        if self.read_only_empty:
            return None
        row = self.connection.execute(
            f"SELECT {self._RECORD_COLUMNS} FROM revisions WHERE revision=?",  # noqa: S608
            (revision,),
        ).fetchone()
        return self._record(row) if row else None

    def latest_revision(self) -> RevisionRecord | None:
        if self.read_only_empty:
            return None
        row = self.connection.execute(
            f"SELECT {self._RECORD_COLUMNS} FROM revisions "  # noqa: S608
            "ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        return self._record(row) if row else None

    def revision_count(self) -> int:
        if self.read_only_empty:
            return 0
        row = self.connection.execute("SELECT COUNT(*) FROM revisions").fetchone()
        return int(row[0])

    def _root_entries(self) -> list[tuple[str, str]]:
        return [
            (row[0], row[1])
            for row in self.connection.execute(
                "SELECT block_id, hash FROM root_manifest ORDER BY position"
            )
        ]

    def revision_manifest(self, revision: str) -> dict[str, str] | None:
        """Return ``block_id -> hash`` for a retained revision (root + delta)."""
        if self.read_only_empty:
            return None
        row = self.connection.execute(
            "SELECT delta FROM revisions WHERE revision=?", (revision,)
        ).fetchone()
        if row is None:
            return None
        manifest = dict(self._root_entries())
        manifest.update(_decompress(row[0]))
        return manifest

    def block_payload(self, block_hash: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT data FROM block_payloads WHERE hash=?", (block_hash,)
        ).fetchone()
        if row is None:
            return None
        payload = _decompress(row[0])
        return payload if isinstance(payload, dict) else None

    def _store_payloads(self, payloads: Mapping[str, Mapping[str, Any]]) -> None:
        self.connection.executemany(
            "INSERT OR IGNORE INTO block_payloads(hash, data) VALUES(?, ?)",
            [
                (block_hash, _compress(dict(data)))
                for block_hash, data in payloads.items()
            ],
        )

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
    ) -> RevisionRecord | None:
        """Retain a revision as a delta against the root.

        Returns ``None`` (nothing recorded) when the block skeleton differs from
        the root, because such a state cannot be expressed as a text delta; the
        DOCX write-back refuses skeleton changes anyway.
        """
        root_entries = self._root_entries()
        if [bid for bid, _ in root_entries] != [bid for bid, _ in entries]:
            return None
        root_hashes = dict(root_entries)
        delta = {bid: h for bid, h in entries if root_hashes.get(bid) != h}
        self._store_payloads({h: payloads[h] for h in delta.values() if h in payloads})
        missing = [
            h
            for h in delta.values()
            if self.connection.execute(
                "SELECT 1 FROM block_payloads WHERE hash=?", (h,)
            ).fetchone()
            is None
        ]
        if missing:
            raise DocxEditStateError(
                "Cannot retain revision: block payloads missing for "
                f"{len(missing)} changed block(s)"
            )
        next_seq = int(
            self.connection.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM revisions"
            ).fetchone()[0]
        )
        changed = json.dumps(list(changed_block_ids), ensure_ascii=False)
        if self.revision(revision) is not None:
            # Content-addressed: the same state recurred (e.g. an edit was undone).
            self.connection.execute(
                "UPDATE revisions SET seq=?, parent=?, kind=?, actor=?, "
                "created_at=?, changed_blocks=? WHERE revision=?",
                (next_seq, parent, kind, actor, now, changed, revision),
            )
        else:
            self.connection.execute(
                "INSERT INTO revisions(revision, seq, parent, kind, actor, "
                "created_at, changed_blocks, delta) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    revision,
                    next_seq,
                    parent,
                    kind,
                    actor,
                    now,
                    changed,
                    _compress(delta),
                ),
            )
        self._prune()
        return self.revision(revision)

    def _prune(self) -> None:
        root = self.root()
        root_revision = root.revision if root else None
        rows = self.connection.execute(
            "SELECT revision FROM revisions ORDER BY seq DESC"
        ).fetchall()
        keep = [row[0] for row in rows if row[0] != root_revision][: self.history_limit]
        drop = [
            row[0]
            for row in rows
            if row[0] != root_revision and row[0] not in set(keep)
        ]
        if not drop:
            return
        self.connection.executemany(
            "DELETE FROM revisions WHERE revision=?", [(rev,) for rev in drop]
        )
        referenced = {
            row[0] for row in self.connection.execute("SELECT hash FROM root_manifest")
        }
        for (blob,) in self.connection.execute("SELECT delta FROM revisions"):
            referenced.update(_decompress(blob).values())
        referenced.update(
            row[0]
            for row in self.connection.execute("SELECT base_hash FROM lease_blocks")
        )
        stored = [
            row[0] for row in self.connection.execute("SELECT hash FROM block_payloads")
        ]
        self.connection.executemany(
            "DELETE FROM block_payloads WHERE hash=?",
            [(h,) for h in stored if h not in referenced],
        )

    def reset(self) -> None:
        """Forget all revisions and attribution (re-ingest). Leases must be gone."""
        for table in (
            "revisions",
            "root_manifest",
            "block_payloads",
            "block_authors",
            "lease_blocks",
            "leases",
        ):
            self.connection.execute(f"DELETE FROM {table}")  # noqa: S608
        self.connection.execute("DELETE FROM meta WHERE key='root_revision'")

    # ------------------------------------------------------------------
    # Leases
    # ------------------------------------------------------------------

    def _load_leases(self, selector: str = "all", value: str = "") -> list[BlockLease]:
        if self.read_only_empty:
            return []
        query = _LEASE_QUERIES[selector]
        params: tuple[str, ...] = () if selector == "all" else (value,)
        rows = self.connection.execute(query, params).fetchall()
        leases: list[BlockLease] = []
        for row in rows:
            blocks = self.connection.execute(
                "SELECT block_id, base_hash FROM lease_blocks WHERE lease_id=? "
                "ORDER BY position",
                (row[0],),
            ).fetchall()
            leases.append(
                BlockLease(
                    lease_id=row[0],
                    holder=row[1],
                    block_ids=tuple(block[0] for block in blocks),
                    base_hashes={block[0]: block[1] for block in blocks},
                    created_at=row[2],
                    expires_at=row[3],
                    ttl_seconds=row[4],
                    base_revision=row[5],
                )
            )
        return leases

    def leases(self) -> list[BlockLease]:
        return self._load_leases()

    def lease(self, lease_id: str) -> BlockLease | None:
        found = self._load_leases("lease_id", lease_id)
        return found[0] if found else None

    def lease_by_token_hash(self, token_hash: str) -> BlockLease | None:
        found = self._load_leases("token", token_hash)
        return found[0] if found else None

    def leases_covering(self, block_ids: Iterable[str]) -> list[BlockLease]:
        if self.read_only_empty:
            return []
        wanted = sorted(set(block_ids))
        lease_ids: set[str] = set()
        for start in range(0, len(wanted), 500):
            chunk = wanted[start : start + 500]
            marks = ",".join("?" for _ in chunk)
            lease_ids.update(
                row[0]
                for row in self.connection.execute(
                    f"SELECT DISTINCT lease_id FROM lease_blocks WHERE block_id IN ({marks})",  # noqa: S608
                    chunk,
                )
            )
        return [lease for lease in self.leases() if lease.lease_id in lease_ids]

    def insert_lease(self, lease: BlockLease, token_hash: str) -> None:
        self.connection.execute(
            "INSERT INTO leases(lease_id, token_sha256, holder, created_at, "
            "expires_at, ttl_seconds, base_revision) VALUES(?, ?, ?, ?, ?, ?, ?)",
            (
                lease.lease_id,
                token_hash,
                lease.holder,
                lease.created_at,
                lease.expires_at,
                lease.ttl_seconds,
                lease.base_revision,
            ),
        )
        self.connection.executemany(
            "INSERT INTO lease_blocks(block_id, lease_id, position, base_hash) "
            "VALUES(?, ?, ?, ?)",
            [
                (block_id, lease.lease_id, index, lease.base_hashes[block_id])
                for index, block_id in enumerate(lease.block_ids)
            ],
        )

    def update_lease(
        self,
        lease_id: str,
        *,
        expires_at: float,
        ttl_seconds: int,
        base_hashes: Mapping[str, str] | None = None,
        base_revision: str | None = None,
    ) -> None:
        self.connection.execute(
            "UPDATE leases SET expires_at=?, ttl_seconds=?, "
            "base_revision=COALESCE(?, base_revision) WHERE lease_id=?",
            (expires_at, ttl_seconds, base_revision, lease_id),
        )
        if base_hashes:
            self.connection.executemany(
                "UPDATE lease_blocks SET base_hash=? WHERE lease_id=? AND block_id=?",
                [(h, lease_id, bid) for bid, h in base_hashes.items()],
            )

    def delete_lease(
        self, lease_id: str, *, event: str, detail: str, now: float
    ) -> None:
        lease = self.lease(lease_id)
        if lease is None:
            return
        self.connection.execute(
            "DELETE FROM lease_blocks WHERE lease_id=?", (lease_id,)
        )
        self.connection.execute("DELETE FROM leases WHERE lease_id=?", (lease_id,))
        self.connection.execute(
            "INSERT INTO lease_events(lease_id, holder, event, at, detail) "
            "VALUES(?, ?, ?, ?, ?)",
            (lease_id, lease.holder, event, now, detail),
        )
        self.connection.execute(
            "DELETE FROM lease_events WHERE id NOT IN "
            "(SELECT id FROM lease_events ORDER BY id DESC LIMIT ?)",
            (MAX_LEASE_EVENTS,),
        )

    def lease_event(self, lease_id: str) -> LeaseEvent | None:
        if self.read_only_empty:
            return None
        row = self.connection.execute(
            "SELECT lease_id, holder, event, at, detail FROM lease_events "
            "WHERE lease_id=? ORDER BY id DESC LIMIT 1",
            (lease_id,),
        ).fetchone()
        return LeaseEvent(*row) if row else None

    # ------------------------------------------------------------------
    # Per-block Track Changes attribution
    # ------------------------------------------------------------------

    def block_authors(self) -> dict[str, str]:
        if self.read_only_empty:
            return {}
        return {
            row[0]: row[1]
            for row in self.connection.execute(
                "SELECT block_id, author FROM block_authors"
            )
        }

    def set_block_authors(
        self, block_ids: Iterable[str], author: str, revision: str
    ) -> None:
        self.connection.executemany(
            "INSERT OR REPLACE INTO block_authors(block_id, author, revision) "
            "VALUES(?, ?, ?)",
            [(block_id, author, revision) for block_id in block_ids],
        )

    def retain_block_authors(self, block_ids: Iterable[str]) -> None:
        keep = set(block_ids)
        stale = [bid for bid in self.block_authors() if bid not in keep]
        self.connection.executemany(
            "DELETE FROM block_authors WHERE block_id=?", [(bid,) for bid in stale]
        )
