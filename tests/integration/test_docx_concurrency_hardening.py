"""Regression tests for the 1.5.0 review of concurrent DFM/DOCX editing.

Each class maps to one finding of the independent review of
``feature/docx-block-leases`` (numbers in the class docstrings).
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
import time
from pathlib import Path

import pytest

import src.infrastructure.docx_edit_state_store as edit_state_store
from src.application.docx_service import DocxService
from src.domain.docx_edit_state import DocxDocumentBusyError
from src.infrastructure.docx_edit_state_store import (
    EDIT_STATE_DB_FILENAME,
    SqliteDocxEditStateStore,
)
from src.infrastructure.file_storage import FileStorage
from tests.integration.test_docx_block_leases import (
    EDIT_5,
    EDIT_7,
    _build_agents_docx,
    _document_text,
    _edited,
    _ingest,
    _section,
    _strip_revision,
)


@pytest.fixture
def env(temp_dir: Path):
    service = DocxService(repository=FileStorage(base_dir=temp_dir / "data"))
    source = temp_dir / "agents.docx"
    _build_agents_docx(source)
    return service, source


async def _commit_p005(service: DocxService, doc_id: str, text: str = EDIT_5) -> dict:
    lease = await service.checkout_blocks(doc_id, ["p005"], holder="agent-B")
    assert lease["success"] is True, lease
    result = await service.commit_block_lease(
        doc_id, lease["lease_token"], _edited(lease, "p005", _section(5), text)
    )
    assert result["success"] is True, result
    return result


class TestSplitSaveBaseRevision:
    """#1: content.md without `revision` must not inherit format.yaml's."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("damage", ["revision_line", "front_matter"])
    async def test_revisionless_content_md_cannot_overwrite_newer_commits(
        self, env, damage
    ) -> None:
        service, source = env
        doc_id, doc_dir = await _ingest(service, source)
        md_path = doc_dir / "content.md"
        human = md_path.read_text(encoding="utf-8")
        await _commit_p005(service, doc_id)
        if damage == "revision_line":
            human = _strip_revision(human)
        else:
            human = human.split("---", 2)[2]
        md_path.write_text(human.replace(_section(7), EDIT_7), encoding="utf-8")

        result = await service.save_docx(doc_id, from_md=True)

        assert result["success"] is False, result
        assert "no `revision`" in result["error"]
        assert EDIT_5 in (doc_dir / "ir.json").read_text(encoding="utf-8")


class TestIdempotentIngest:
    """#2: re-ingesting the same source never silently discards edits."""

    @pytest.mark.asyncio
    async def test_reingest_returns_existing_state_with_committed_edits(
        self, env
    ) -> None:
        service, source = env
        doc_id, doc_dir = await _ingest(service, source)
        commit = await _commit_p005(service, doc_id)
        output_before = (doc_dir / "output.docx").read_bytes()

        again = await service.ingest_docx(str(source))

        assert again["success"] is True, again
        assert again["doc_id"] == doc_id
        assert again["existing"] is True
        assert again["revision"] == commit["revision"]
        assert again["changed_block_ids"] == ["p005"]
        assert "reset=true" in again["note"]
        assert EDIT_5 in (doc_dir / "ir.json").read_text(encoding="utf-8")
        assert (doc_dir / "output.docx").read_bytes() == output_before
        dfm = await service.get_dfm(doc_id)
        saved = await service.save_docx(doc_id, (dfm or "").replace(_section(2), "C"))
        assert saved["success"] is True, saved
        assert EDIT_5 in _document_text(Path(saved["output_path"]))

    @pytest.mark.asyncio
    async def test_explicit_reset_discards_edits_but_not_live_leases(self, env) -> None:
        service, source = env
        doc_id, doc_dir = await _ingest(service, source)
        await _commit_p005(service, doc_id)
        lease = await service.checkout_blocks(doc_id, ["p007"], holder="agent-C")

        refused = await service.ingest_docx(str(source), reset=True)
        await service.release_block_lease(doc_id, lease["lease_token"])
        reset = await service.ingest_docx(str(source), reset=True)

        assert refused["success"] is False and "agent-C" in refused["error"]
        assert reset["success"] is True, reset
        assert reset.get("existing") is not True
        assert reset["discarded_block_ids"] == ["p005"]
        assert EDIT_5 not in (doc_dir / "ir.json").read_text(encoding="utf-8")
        assert any((doc_dir / ".backups").iterdir())


class TestInPlaceEditsArePreserved:
    """#3: shared artifacts with unsaved in-place edits are never clobbered."""

    @pytest.mark.asyncio
    async def test_commit_keeps_in_place_markdown_edit_and_merges_later(
        self, env
    ) -> None:
        service, source = env
        doc_id, doc_dir = await _ingest(service, source)
        md_path = doc_dir / "content.md"
        edited = md_path.read_text(encoding="utf-8").replace(
            _section(3), "Section 3 edited in place."
        )
        md_path.write_text(edited, encoding="utf-8")
        yaml_before = (doc_dir / "format.yaml").read_text(encoding="utf-8")

        commit = await _commit_p005(service, doc_id)

        assert md_path.read_text(encoding="utf-8") == edited
        assert (doc_dir / "format.yaml").read_text(encoding="utf-8") == yaml_before
        current = (doc_dir / "content.current.md").read_text(encoding="utf-8")
        assert EDIT_5 in current
        assert any("content.md" in w and "in-place" in w for w in commit["warnings"])
        saved = await service.save_docx(doc_id, from_md=True)
        assert saved["success"] is True, saved
        text = _document_text(Path(saved["output_path"]))
        assert "Section 3 edited in place." in text and EDIT_5 in text
        # The consumed in-place edit is replaced by the fresh render.
        assert f"revision: {saved['revision']}" in md_path.read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_commit_keeps_in_place_dfm_edit(self, env) -> None:
        service, source = env
        doc_id, doc_dir = await _ingest(service, source)
        dfm_path = doc_dir / "content.dfm"
        edited = dfm_path.read_text(encoding="utf-8").replace(_section(2), "In place.")
        dfm_path.write_text(edited, encoding="utf-8")

        commit = await _commit_p005(service, doc_id)

        assert dfm_path.read_text(encoding="utf-8") == edited
        assert EDIT_5 in (doc_dir / "content.current.dfm").read_text(encoding="utf-8")
        assert any("content.dfm" in w for w in commit["warnings"])
        saved = await service.save_docx(doc_id)  # reads the edited content.dfm
        assert saved["success"] is True, saved
        text = _document_text(Path(saved["output_path"]))
        assert "In place." in text and EDIT_5 in text

    @pytest.mark.asyncio
    async def test_large_in_progress_markdown_does_not_trip_shrink_fail_safe(
        self, env
    ) -> None:
        service, source = env
        doc_id, doc_dir = await _ingest(service, source)
        md_path = doc_dir / "content.md"
        draft = md_path.read_text(encoding="utf-8").replace(
            _section(3), _section(3) + " Draft addition." * 400
        )
        md_path.write_text(draft, encoding="utf-8")

        commit = await _commit_p005(service, doc_id)

        assert commit["success"] is True
        assert md_path.read_text(encoding="utf-8") == draft

    def test_backup_slots_do_not_collide_within_one_second(
        self, temp_dir: Path
    ) -> None:
        doc_dir = temp_dir / "doc"
        doc_dir.mkdir()
        for index in range(3):
            (doc_dir / "content.md").write_text(f"version {index}", encoding="utf-8")
            DocxService._backup_before_overwrite(doc_dir)
        slots = sorted((doc_dir / ".backups").iterdir())
        contents = {(slot / "content.md").read_text(encoding="utf-8") for slot in slots}
        assert contents == {"version 0", "version 1", "version 2"}


class TestMergedSavesKeepValidation:
    """#4: a stale (merged) save must not drop edits a current save refuses."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("stale", [False, True])
    async def test_unknown_block_marker_is_refused_in_both_modes(
        self, env, stale
    ) -> None:
        service, source = env
        doc_id, _doc_dir = await _ingest(service, source)
        shared = await service.get_dfm(doc_id) or ""
        if stale:
            first = await service.save_docx(doc_id, shared.replace(_section(1), "B"))
            assert first["success"] is True, first
        anchor = _section(4)
        index = shared.index(anchor) + len(anchor)
        dfm = (
            shared[:index]
            + "\n\n<!-- @b:p900 -->\nA brand new paragraph."
            + shared[index:]
        ).replace(_section(3), "Section 3 by A.")

        result = await service.save_docx(doc_id, dfm)

        assert result["success"] is False, result
        assert any("p900" in w for w in result.get("warnings", []))


class TestUnmarkedTextIsReported:
    """#4 (follow-up): text outside every block marker is not dropped silently."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("stale", [False, True])
    async def test_unmarked_paragraph_produces_a_warning(self, env, stale) -> None:
        service, source = env
        doc_id, _doc_dir = await _ingest(service, source)
        shared = await service.get_dfm(doc_id) or ""
        clean = await service.save_docx(doc_id, shared)
        assert not any("UNMARKED_TEXT" in w for w in clean.get("warnings", []))
        if stale:
            first = await service.save_docx(doc_id, shared.replace(_section(1), "B"))
            assert first["success"] is True, first
        anchor = _section(4)
        index = shared.index(anchor) + len(anchor)
        dfm = shared[:index] + "\n\n\nA brand new paragraph." + shared[index:]

        result = await service.save_docx(doc_id, dfm.replace(_section(3), "S3 by A."))

        assert result["success"] is True, result
        assert any("UNMARKED_TEXT" in w for w in result["warnings"])


class TestIterativeSavesFromOneBuffer:
    """#5: conflicts caused by the caller's own earlier save are explained."""

    @pytest.mark.asyncio
    async def test_own_earlier_save_is_named_and_revision_line_returned(
        self, env
    ) -> None:
        service, source = env
        doc_id, _doc_dir = await _ingest(service, source)
        buffer = (await service.get_dfm(doc_id) or "").replace(
            _section(1), "Section 1 draft one."
        )
        first = await service.save_docx(doc_id, buffer)
        assert first["revision_front_matter"] == f"revision: {first['revision']}"
        buffer = buffer.replace(_section(2), "Section 2 draft one.")
        second = await service.save_docx(doc_id, buffer)
        assert second["success"] is True, second
        buffer = buffer.replace("Section 1 draft one.", "Section 1 draft two.")

        third = await service.save_docx(doc_id, buffer)
        old_line = next(
            line for line in buffer.splitlines() if line.startswith("revision: ")
        )
        fixed = await service.save_docx(
            doc_id, buffer.replace(old_line, second["revision_front_matter"])
        )

        assert third["success"] is False
        assert third["conflict_block_ids"] == ["p001"]
        assert "your own earlier save" in third["error"]
        assert second["revision"] in third["error"]
        assert fixed["success"] is True, fixed


class TestUpgradeFromPreRevisionWorkspace:
    """#6: a 1.4.x workspace stays usable after upgrading."""

    @staticmethod
    async def _workspace_1_4(service: DocxService, source: Path) -> tuple[str, Path]:
        doc_id, doc_dir = await _ingest(service, source)
        dfm = await service.get_dfm(doc_id) or ""
        saved = await service.save_docx(doc_id, dfm.replace(_section(5), EDIT_5))
        assert saved["success"] is True, saved
        (doc_dir / EDIT_STATE_DB_FILENAME).unlink()
        for name in ("content.dfm", "content.md", "format.yaml"):
            path = doc_dir / name
            path.write_text(_strip_revision(path.read_text("utf-8")), encoding="utf-8")
        return doc_id, doc_dir

    @pytest.mark.asyncio
    async def test_revisionless_dfm_edit_after_upgrade_is_accepted(self, env) -> None:
        service, source = env
        doc_id, _doc_dir = await self._workspace_1_4(service, source)
        dfm = await service.get_dfm(doc_id) or ""
        assert "revision:" not in dfm

        result = await service.save_docx(doc_id, dfm.replace(_section(7), EDIT_7))

        assert result["success"] is True, result
        text = _document_text(Path(result["output_path"]))
        assert EDIT_5 in text and EDIT_7 in text

    @pytest.mark.asyncio
    async def test_in_place_markdown_edit_after_upgrade_is_accepted(self, env) -> None:
        service, source = env
        doc_id, doc_dir = await self._workspace_1_4(service, source)
        md_path = doc_dir / "content.md"
        md_path.write_text(
            md_path.read_text("utf-8").replace(_section(3), "Section 3 md edit"),
            encoding="utf-8",
        )

        result = await service.save_docx(doc_id, from_md=True)

        assert result["success"] is True, result
        assert "Section 3 md edit" in _document_text(Path(result["output_path"]))

    @pytest.mark.asyncio
    async def test_first_locked_operation_stamps_pristine_artifacts(self, env) -> None:
        service, source = env
        doc_id, doc_dir = await self._workspace_1_4(service, source)

        lease = await service.checkout_blocks(doc_id, ["p001"], holder="agent")

        assert lease["success"] is True
        for name in ("content.dfm", "content.md", "format.yaml"):
            text = (doc_dir / name).read_text(encoding="utf-8")
            assert f"revision: {lease['revision']}" in text, name


class TestEventLoopStaysResponsive:
    """#7: waiting for the document lock must not block the event loop."""

    @pytest.mark.asyncio
    async def test_checkout_waiting_for_the_lock_yields_to_the_loop(self, env) -> None:
        service, source = env
        doc_id, doc_dir = await _ingest(service, source)
        warm = await service.checkout_blocks(doc_id, ["p001"], holder="warm")
        assert warm["success"] is True
        store = SqliteDocxEditStateStore(doc_dir)
        held = threading.Event()

        def hold() -> None:
            with store.session():
                held.set()
                time.sleep(1.5)

        holder = threading.Thread(target=hold)
        holder.start()
        held.wait()
        ticks: list[float] = []

        async def ticker() -> None:
            while True:
                ticks.append(time.monotonic())
                await asyncio.sleep(0.05)

        task = asyncio.create_task(ticker())
        start = time.monotonic()
        result = await service.checkout_blocks(doc_id, ["p002"], holder="waiter")
        end = time.monotonic()
        task.cancel()
        holder.join()

        assert result["success"] is True, result
        assert end - start >= 1.0
        assert sum(1 for tick in ticks if start < tick < end) >= 10


class _CommitFailingConnection:
    def __init__(self, connection: sqlite3.Connection, fail: dict) -> None:
        self._connection = connection
        self._fail = fail

    def execute(self, sql: str, *args):
        if sql == "COMMIT" and self._fail["on"]:
            raise sqlite3.OperationalError("disk I/O error")
        return self._connection.execute(sql, *args)

    def __getattr__(self, name: str):
        return getattr(self._connection, name)


class TestPublishedButUncommittedIsReported:
    """#8 + #14: report the real error and that content was published."""

    @pytest.mark.asyncio
    async def test_commit_failure_after_publish_reports_committed_content(
        self, env, monkeypatch
    ) -> None:
        service, source = env
        doc_id, doc_dir = await _ingest(service, source)
        lease = await service.checkout_blocks(doc_id, ["p005"], holder="agent-A")
        fail = {"on": False}
        real_connect = sqlite3.connect

        class FakeSqlite:
            OperationalError = sqlite3.OperationalError

            @staticmethod
            def connect(*args, **kwargs):
                return _CommitFailingConnection(real_connect(*args, **kwargs), fail)

        monkeypatch.setattr(edit_state_store, "sqlite3", FakeSqlite)
        fail["on"] = True
        result = await service.commit_block_lease(
            doc_id, lease["lease_token"], {"p005": EDIT_5}
        )
        fail["on"] = False
        monkeypatch.undo()

        assert result["success"] is False
        assert result["committed"] is True
        assert "disk I/O error" in result["error"]
        assert "nothing was committed" not in result["error"]
        assert EDIT_5 in (doc_dir / "ir.json").read_text(encoding="utf-8")
        assert result["revision"] == service.ir_revision(service._load_ir(doc_id))
        retried = await service.commit_block_lease(
            doc_id, lease["lease_token"], {"p005": EDIT_5}
        )
        assert retried["success"] is True, retried
        assert retried["already_applied_block_ids"] == ["p005"]

    @pytest.mark.asyncio
    async def test_ir_block_update_reports_published_content(
        self, env, monkeypatch
    ) -> None:
        service, source = env
        doc_id, doc_dir = await _ingest(service, source)
        import src.application.docx_concurrency as concurrency_module

        def broken(path, text, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(concurrency_module, "write_utf8_text_atomic", broken)

        def set_cell(ir) -> None:
            table = ir.find_block("t001")
            table.content = table.content.replace("40 ", "75 ")

        result = await service.update_ir_blocks(
            doc_id, ["t001"], set_cell, actor="TableContext x"
        )

        assert result["success"] is False
        assert result["committed"] is True
        assert "75" in (doc_dir / "ir.json").read_text(encoding="utf-8")


class TestDeleteRespectsLeases:
    """#9: delete runs under the lock and refuses live leases."""

    @pytest.mark.asyncio
    async def test_delete_refuses_live_leases_unless_forced(self, env) -> None:
        service, source = env
        doc_id, doc_dir = await _ingest(service, source)
        await service.checkout_blocks(doc_id, ["p005"], holder="agent-A")

        refused = await service.delete_docx(doc_id)
        forced = await service.delete_docx(doc_id, force=True)

        assert refused["success"] is False and "agent-A" in refused["error"]
        assert forced["success"] is True, forced
        assert not doc_dir.exists()
        leftovers = [p.name for p in doc_dir.parent.iterdir() if doc_id in p.name]
        assert leftovers == []


class TestSplitInputIsReadUnderTheLock:
    """#10: split input is parsed while holding the document lock."""

    @pytest.mark.asyncio
    async def test_parse_runs_inside_the_edit_session(self, env, monkeypatch) -> None:
        service, source = env
        doc_id, doc_dir = await _ingest(service, source)
        seen: list[bool] = []
        real_parse = service._parse_save_input

        def probing_parse(*args, **kwargs):
            probe = SqliteDocxEditStateStore(doc_dir, timeout_seconds=0.05)
            try:
                with probe.session():
                    seen.append(False)
            except DocxDocumentBusyError:
                seen.append(True)
            return real_parse(*args, **kwargs)

        monkeypatch.setattr(service, "_parse_save_input", probing_parse)
        result = await service.save_docx(doc_id, from_md=True)

        assert result["success"] is True, result
        assert seen == [True]


class TestUnlockedWritersAreDetected:
    """#11: an ir.json change by a lock-less writer is never overwritten."""

    @pytest.mark.asyncio
    async def test_save_aborts_when_ir_changes_during_write_back(
        self, env, monkeypatch
    ) -> None:
        service, source = env
        doc_id, doc_dir = await _ingest(service, source)
        dfm = await service.get_dfm(doc_id) or ""
        ir_path = doc_dir / "ir.json"
        real_writer = service.adapter.ir_to_docx

        def legacy_server_writes(*args, **kwargs):
            data = json.loads(ir_path.read_text(encoding="utf-8"))
            for block in data["blocks"]:
                if block["id"] == "p001":
                    block["content"] = "Written by a 1.4.x server."
            ir_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return real_writer(*args, **kwargs)

        monkeypatch.setattr(service.adapter, "ir_to_docx", legacy_server_writes)
        result = await service.save_docx(doc_id, dfm.replace(_section(7), EDIT_7))

        assert result["success"] is False
        assert "outside the document lock" in result["error"]
        text = ir_path.read_text(encoding="utf-8")
        assert "Written by a 1.4.x server." in text
        assert EDIT_7 not in text


class TestStorageLocationWarning:
    """#12: cloud-synced or network DATA_DIR produces a warning, never a refusal."""

    @pytest.mark.asyncio
    async def test_results_carry_the_storage_warning(self, env, monkeypatch) -> None:
        service, source = env
        import src.application.docx_concurrency as concurrency

        monkeypatch.setattr(
            concurrency,
            "describe_storage_risk",
            lambda path: "DATA_DIR is on Google Drive (test)",
        )
        doc_id, _doc_dir = await _ingest(service, source)
        dfm = await service.get_dfm(doc_id) or ""

        saved = await service.save_docx(doc_id, dfm.replace(_section(7), EDIT_7))
        lease = await service.checkout_blocks(doc_id, ["p001"], holder="agent")

        assert saved["success"] is True, saved
        assert saved["storage_warning"] == "DATA_DIR is on Google Drive (test)"
        assert lease["success"] is True
        assert lease["storage_warning"] == "DATA_DIR is on Google Drive (test)"


class TestIdempotentCheckout:
    """#13: a retried checkout recovers its lease; the token is never dropped."""

    @pytest.mark.asyncio
    async def test_request_id_replays_the_same_lease_with_a_fresh_token(
        self, env
    ) -> None:
        service, source = env
        doc_id, _doc_dir = await _ingest(service, source)

        first = await service.checkout_blocks(
            doc_id, ["p005"], holder="agent-A", request_id="req-1"
        )
        replay = await service.checkout_blocks(
            doc_id, ["p005"], holder="agent-A", request_id="req-1"
        )
        stale_token = await service.commit_block_lease(
            doc_id, first["lease_token"], {"p005": EDIT_5}
        )
        commit = await service.commit_block_lease(
            doc_id, replay["lease_token"], {"p005": EDIT_5}
        )

        assert first["success"] and replay["success"], (first, replay)
        assert replay["lease_id"] == first["lease_id"]
        assert replay["replayed"] is True
        assert replay["lease_token"] != first["lease_token"]
        assert stale_token["success"] is False
        assert commit["success"] is True, commit

    @pytest.mark.asyncio
    async def test_tiny_response_limit_keeps_the_lease_token(self, env) -> None:
        service, source = env
        doc_id, _doc_dir = await _ingest(service, source)
        from unittest.mock import patch

        from src.presentation.tools import docx_tools

        with patch.object(docx_tools, "docx_service", service):
            result = await docx_tools.docx(
                "checkout",
                doc_id=doc_id,
                block_ids=["t001"],
                holder="agent-A",
                max_chars=200,
            )

        assert isinstance(result, dict)
        assert result["lease_token"]
        assert result["lease_id"]
        assert result.get("response_truncated") is True


class TestForceAndChecksum:
    """#15: force does not bypass a source checksum mismatch."""

    @pytest.mark.asyncio
    async def test_checksum_mismatch_is_refused_even_with_force(self, env) -> None:
        service, source = env
        doc_id, _doc_dir = await _ingest(service, source)
        dfm = await service.get_dfm(doc_id) or ""
        ir = service._load_ir(doc_id)
        assert ir is not None
        forged = dfm.replace(ir.checksum, "sha256:" + "0" * 64)

        result = await service.save_docx(
            doc_id, forged.replace(_section(1), "x"), force=True
        )

        assert result["success"] is False
        assert "checksum" in result["error"]
        assert "use force=True" not in result["error"]


class TestRevisionSidecarCarriesContentRevision:
    """#16: revisions.jsonl names the content revision it describes."""

    @pytest.mark.asyncio
    async def test_records_include_content_revision(self, env) -> None:
        service, source = env
        doc_id, doc_dir = await _ingest(service, source)
        dfm = await service.get_dfm(doc_id) or ""

        result = await service.save_docx(
            doc_id, dfm.replace(_section(7), EDIT_7), track_changes=True
        )

        assert result["success"] is True, result
        records = [
            json.loads(line)
            for line in (doc_dir / "revisions.jsonl").read_text("utf-8").splitlines()
        ]
        assert records
        assert {record["content_revision"] for record in records} == {
            result["revision"]
        }
