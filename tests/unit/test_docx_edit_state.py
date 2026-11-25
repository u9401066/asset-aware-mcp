"""Unit tests for DOCX content revisions, 3-way merge rules and the lease store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.domain.docx_edit_state import (
    MAX_LEASE_TTL_SECONDS,
    BlockLease,
    DocxDocumentBusyError,
    DocxEditStateError,
    block_state_hash,
    content_revision,
    lease_id_for_token,
    lease_scope,
    lease_token_hash,
    plan_three_way_merge,
    validate_holder,
    validate_ttl,
)
from src.infrastructure.docx_edit_state_store import (
    EDIT_STATE_DB_FILENAME,
    SqliteDocxEditStateStore,
)


def _entries(**hashes: str) -> list[tuple[str, str]]:
    return list(hashes.items())


class TestRevisionRules:
    def test_content_revision_is_deterministic_and_content_addressed(self) -> None:
        entries = _entries(p001="sha256:a", p002="sha256:b")
        first = content_revision("sha256:src", entries)
        assert first == content_revision("sha256:src", list(entries))
        assert first.startswith("rev-") and len(first) == 4 + 32
        assert first != content_revision("sha256:other", entries)
        assert first != content_revision("sha256:src", list(reversed(entries)))
        assert first != content_revision(
            "sha256:src", _entries(p001="sha256:a", p002="sha256:c")
        )

    def test_block_hash_ignores_key_order(self) -> None:
        assert block_state_hash({"id": "p1", "content": "x"}) == block_state_hash(
            {"content": "x", "id": "p1"}
        )
        assert block_state_hash({"id": "p1", "content": "x"}) != block_state_hash(
            {"id": "p1", "content": "y"}
        )

    def test_three_way_plan_merges_disjoint_and_flags_overlap(self) -> None:
        base = {"p1": "a", "p2": "b", "p3": "c"}
        current = {"p1": "a2", "p2": "b", "p3": "c"}

        disjoint = plan_three_way_merge(base, current, {"p2"})
        overlap = plan_three_way_merge(base, current, {"p1", "p3"})
        retried = plan_three_way_merge(base, current, {"p1"}, already_applied={"p1"})

        assert disjoint.apply_block_ids == {"p2"}
        assert disjoint.theirs_block_ids == {"p1"}
        assert not disjoint.conflict_block_ids
        assert overlap.conflict_block_ids == {"p1"}
        assert overlap.apply_block_ids == {"p3"}
        assert not retried.conflict_block_ids
        assert retried.already_applied_block_ids == {"p1"}
        assert not retried.apply_block_ids

    def test_lease_scope_expands_table_families_in_document_order(self) -> None:
        order = ["p1", "t1", "t2", "t3", "p2", "t4"]
        parents = {
            "p1": None,
            "t1": None,
            "t2": "t1",
            "t3": "t2",
            "p2": None,
            "t4": None,
        }
        assert lease_scope(order, parents, ["t3"]) == ["t1", "t2", "t3"]
        assert lease_scope(order, parents, ["p2", "t1"]) == ["t1", "t2", "t3", "p2"]
        assert lease_scope(order, parents, ["t4"]) == ["t4"]
        # A corrupt parent cycle terminates instead of looping forever.
        cyclic = {"a": "b", "b": "a"}
        assert set(lease_scope(["a", "b"], cyclic, ["a"])) <= {"a", "b"}

    def test_holder_and_ttl_validation(self) -> None:
        assert validate_holder("  agent-1 ") == "agent-1"
        assert validate_ttl(None) == 900
        for bad in ("", "   ", "a" * 201, "bad\nname"):
            with pytest.raises(DocxEditStateError):
                validate_holder(bad)
        for bad_ttl in (0, MAX_LEASE_TTL_SECONDS + 1, True, 1.5):
            with pytest.raises(DocxEditStateError):
                validate_ttl(bad_ttl)  # type: ignore[arg-type]

    def test_public_lease_view_never_exposes_the_token(self) -> None:
        token = "secret-token-value"  # noqa: S105 - test token
        lease = BlockLease(
            lease_id=lease_id_for_token(token),
            holder="agent-1",
            block_ids=("p1",),
            base_hashes={"p1": "sha256:a"},
            created_at=100.0,
            expires_at=200.0,
            ttl_seconds=100,
            base_revision="rev-x",
        )
        live = lease.to_public_dict(150.0)
        expired = lease.to_public_dict(250.0)
        assert token not in json.dumps(live)
        assert lease_token_hash(token) not in json.dumps(live)
        assert live["status"] == "live" and live["remaining_seconds"] == 50
        assert expired["status"] == "expired" and expired["remaining_seconds"] == 0


def _payloads(**contents: str) -> tuple[list[tuple[str, str]], dict[str, dict]]:
    entries: list[tuple[str, str]] = []
    payloads: dict[str, dict] = {}
    for block_id, content in contents.items():
        record = {"id": block_id, "content": content}
        block_hash = block_state_hash(record)
        entries.append((block_id, block_hash))
        payloads[block_hash] = record
    return entries, payloads


class TestSqliteEditStateStore:
    def test_revisions_are_deltas_against_the_root(self, tmp_path: Path) -> None:
        store = SqliteDocxEditStateStore(tmp_path, history_limit=2)
        root_entries, root_payloads = _payloads(p1="a", p2="b", p3="c")
        with store.session() as session:
            session.create_root(
                "rev-root", "ingest", root_entries, root_payloads, now=1
            )
        revisions = []
        for index in range(4):
            entries, payloads = _payloads(p1="a", p2=f"b{index}", p3="c")
            revisions.append(f"rev-{index}")
            with store.session() as session:
                session.record_revision(
                    f"rev-{index}",
                    parent=None,
                    kind="save",
                    actor="tester",
                    changed_block_ids=["p2"],
                    entries=entries,
                    payloads=payloads,
                    now=2 + index,
                )

        with store.session(write=False) as session:
            retained = {
                rev for rev in ["rev-root", *revisions] if session.revision(rev)
            }
            manifest = session.revision_manifest("rev-3")
            assert manifest is not None
            restored = session.block_payload(manifest["p2"])
            stale_payload = session.block_payload(_payloads(p2="b0")[0][0][1])

        assert retained == {"rev-root", "rev-2", "rev-3"}
        assert list(manifest) == ["p1", "p2", "p3"]
        assert manifest["p1"] == root_entries[0][1]
        assert restored == {"id": "p2", "content": "b3"}
        assert stale_payload is None, "unreferenced payloads are garbage-collected"

    def test_recurring_content_moves_to_the_head(self, tmp_path: Path) -> None:
        store = SqliteDocxEditStateStore(tmp_path)
        entries, payloads = _payloads(p1="a")
        changed, changed_payloads = _payloads(p1="b")
        with store.session() as session:
            session.create_root("rev-a", "ingest", entries, payloads, now=1)
            session.record_revision(
                "rev-b",
                parent="rev-a",
                kind="save",
                actor=None,
                changed_block_ids=["p1"],
                entries=changed,
                payloads=changed_payloads,
                now=2,
            )
            session.record_revision(
                "rev-a",
                parent="rev-b",
                kind="save",
                actor=None,
                changed_block_ids=["p1"],
                entries=entries,
                payloads=payloads,
                now=3,
            )
            latest = session.latest_revision()
            count = session.revision_count()
        assert latest is not None and latest.revision == "rev-a"
        assert count == 2

    def test_skeleton_changes_are_not_recorded(self, tmp_path: Path) -> None:
        store = SqliteDocxEditStateStore(tmp_path)
        entries, payloads = _payloads(p1="a", p2="b")
        other, other_payloads = _payloads(p1="a", p9="b")
        with store.session() as session:
            session.create_root("rev-a", "ingest", entries, payloads, now=1)
            recorded = session.record_revision(
                "rev-x",
                parent="rev-a",
                kind="external",
                actor=None,
                changed_block_ids=[],
                entries=other,
                payloads=other_payloads,
                now=2,
            )
        assert recorded is None

    def test_failed_session_rolls_back(self, tmp_path: Path) -> None:
        store = SqliteDocxEditStateStore(tmp_path)
        lease = BlockLease(
            lease_id="lease-x",
            holder="agent-1",
            block_ids=("p1",),
            base_hashes={"p1": "sha256:a"},
            created_at=1,
            expires_at=100,
            ttl_seconds=99,
            base_revision="rev-a",
        )
        with pytest.raises(RuntimeError), store.session() as session:
            session.insert_lease(lease, lease_token_hash("t"))
            raise RuntimeError("crash inside the critical section")
        with store.session(write=False) as session:
            assert session.leases() == []

    def test_second_writer_times_out_as_busy(self, tmp_path: Path) -> None:
        holder = SqliteDocxEditStateStore(tmp_path)
        waiter = SqliteDocxEditStateStore(tmp_path, timeout_seconds=0.2)
        with holder.session(), pytest.raises(DocxDocumentBusyError), waiter.session():
            pass
        # Readers are not blocked by a pending writer.
        with holder.session(), waiter.session(write=False) as reader:
            assert reader.leases() == []

    def test_newer_schema_is_refused(self, tmp_path: Path) -> None:
        store = SqliteDocxEditStateStore(tmp_path)
        with store.session() as session:
            session.connection.execute(
                "UPDATE meta SET value='99' WHERE key='schema_version'"
            )
        with pytest.raises(DocxEditStateError, match="schema"), store.session():
            pass
        assert (tmp_path / EDIT_STATE_DB_FILENAME).exists()
