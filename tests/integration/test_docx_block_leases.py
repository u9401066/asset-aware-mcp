"""Regression tests: concurrent multi-agent DFM/DOCX editing never loses work.

Before 1.5.0 two clients that read the same ``content.dfm`` could both save:
the stale-session check compared the DFM ``checksum`` (the *original* file's
SHA-256, which never changes) with the IR checksum, so client B's full DFM
silently reverted client A's saved edit while both saves reported success.

These tests cover the content-revision lost-update protection (3-way merge or
refusal) and the block checkout/lease workflow, including two real OS
processes committing concurrently and crash recovery.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest
from docx import Document
from docx.shared import Pt
from lxml import etree

from src.application.docx_service import DocxService
from src.infrastructure.docx_edit_state_store import EDIT_STATE_DB_FILENAME
from src.infrastructure.file_storage import FileStorage

REPO_ROOT = Path(__file__).resolve().parents[2]
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = {"w": W_NS}

EDIT_5 = "Section 5 rewritten by agent A."
EDIT_7 = "Section 7 rewritten by agent B."
CLOSING = "Closing remarks stay untouched."


def _section(index: int) -> str:
    return f"Section {index} original sentence for agent review."


def _build_agents_docx(path: Path) -> None:
    """Heading, eight paragraphs (p001-p008), a table with a nested table, p009."""
    doc = Document()
    doc.add_heading("Multi-agent protocol draft", level=1)
    for index in range(1, 9):
        paragraph = doc.add_paragraph()
        run = paragraph.add_run(_section(index))
        if index % 2:
            run.font.size = Pt(11)
    table = doc.add_table(rows=2, cols=2)
    table.style = "Table Grid"
    table.cell(0, 0).text = "Arm"
    table.cell(0, 1).text = "Size"
    table.cell(1, 0).text = "Control"
    table.cell(1, 1).text = "40"
    nested = table.cell(1, 0).add_table(rows=1, cols=1)
    nested.cell(0, 0).text = "Nested note"
    doc.add_paragraph(CLOSING)
    doc.save(path)


class FakeClock:
    def __init__(self, now: float = 1_800_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def lease_env(temp_dir: Path):
    service = DocxService(repository=FileStorage(base_dir=temp_dir / "data"))
    source = temp_dir / "agents.docx"
    _build_agents_docx(source)
    return service, source


async def _ingest(service: DocxService, source: Path) -> tuple[str, Path]:
    result = await service.ingest_docx(str(source))
    assert result["success"] is True, result
    doc_id = str(result["doc_id"])
    return doc_id, service.repository.get_doc_dir(doc_id)


def _zip_parts(path: Path) -> dict[str, bytes]:
    with ZipFile(path) as zf:
        return {name: zf.read(name) for name in zf.namelist()}


def _body_elements(path: Path) -> list[etree._Element]:
    with ZipFile(path) as zf:
        tree = etree.fromstring(zf.read("word/document.xml"))
    body = tree.find(f"{{{W_NS}}}body")
    assert body is not None
    return list(body)


def _visible_text(element: etree._Element) -> str:
    parts: list[str] = []
    for node in element.iter(f"{{{W_NS}}}t"):
        ancestor = node.getparent()
        deleted = False
        while ancestor is not None:
            if ancestor.tag == f"{{{W_NS}}}del":
                deleted = True
                break
            ancestor = ancestor.getparent()
        if not deleted:
            parts.append(node.text or "")
    return "".join(parts)


def _document_text(path: Path) -> str:
    return "\n".join(_visible_text(element) for element in _body_elements(path))


def _fragment(checkout: dict, block_id: str) -> str:
    return next(b["dfm"] for b in checkout["blocks"] if b["block_id"] == block_id)


def _edited(checkout: dict, block_id: str, old: str, new: str) -> dict[str, str]:
    fragment = _fragment(checkout, block_id)
    assert old in fragment
    return {block_id: fragment.replace(old, new)}


def _artifacts(doc_dir: Path) -> dict[str, bytes]:
    names = ("ir.json", "content.dfm", "content.md", "format.yaml", "output.docx")
    return {
        name: (doc_dir / name).read_bytes()
        for name in names
        if (doc_dir / name).exists()
    }


def _stray_files(doc_dir: Path) -> list[str]:
    return sorted(
        path.name
        for path in doc_dir.iterdir()
        if path.name.endswith((".tmp.docx", ".tmp.prev", ".tmp"))
    )


def _db_rows(doc_dir: Path, query: str) -> list[tuple]:
    connection = sqlite3.connect(str(doc_dir / EDIT_STATE_DB_FILENAME))
    try:
        return connection.execute(query).fetchall()
    finally:
        connection.close()


def _strip_revision(dfm: str) -> str:
    lines = dfm.split("\n")
    assert any(line.startswith("revision: ") for line in lines[:12])
    return "\n".join(line for line in lines if not line.startswith("revision: "))


# ============================================================================
# (a) Lost-update protection for full-DFM saves
# ============================================================================


class TestStaleFullDfmSaves:
    @pytest.mark.asyncio
    async def test_dfm_front_matter_carries_a_stable_content_revision(
        self, lease_env
    ) -> None:
        service, source = lease_env
        result = await service.ingest_docx(str(source))
        doc_id = result["doc_id"]
        dfm = await service.get_dfm(doc_id)
        assert dfm is not None
        ir = service._load_ir(doc_id)
        assert ir is not None
        assert f"revision: {result['revision']}" in dfm
        assert service.ir_revision(ir) == result["revision"]
        parsed = service.parser.parse(dfm)
        assert parsed.revision == result["revision"]
        # The original checksum keeps its source-identity meaning.
        assert parsed.checksum == ir.checksum

    @pytest.mark.asyncio
    async def test_reported_lost_update_is_merged_and_keeps_first_edit(
        self, lease_env
    ) -> None:
        """A and B read the same DFM; A saves p005, then B saves p007 (stale)."""
        service, source = lease_env
        doc_id, doc_dir = await _ingest(service, source)
        shared = await service.get_dfm(doc_id)
        assert shared is not None

        first = await service.save_docx(doc_id, shared.replace(_section(5), EDIT_5))
        assert first["success"] is True, first
        second = await service.save_docx(doc_id, shared.replace(_section(7), EDIT_7))

        assert second["success"] is True, second
        merge = second["revision_merge"]
        assert merge["mode"] == "merged"
        assert merge["base_revision"] == first["previous_revision"]
        assert merge["merged_block_ids"] == ["p007"]
        assert merge["preserved_block_ids"] == ["p005"]
        assert second["previous_revision"] == first["revision"]
        text = _document_text(Path(second["output_path"]))
        assert EDIT_5 in text, "A's edit was silently reverted"
        assert EDIT_7 in text
        saved_dfm = (doc_dir / "content.dfm").read_text(encoding="utf-8")
        assert EDIT_5 in saved_dfm
        assert EDIT_7 in saved_dfm
        assert f"revision: {second['revision']}" in saved_dfm

    @pytest.mark.asyncio
    async def test_conflicting_stale_save_is_refused_and_nothing_is_written(
        self, lease_env
    ) -> None:
        service, source = lease_env
        doc_id, doc_dir = await _ingest(service, source)
        shared = await service.get_dfm(doc_id)
        assert shared is not None
        first = await service.save_docx(doc_id, shared.replace(_section(5), EDIT_5))
        assert first["success"] is True, first
        before = _artifacts(doc_dir)

        conflicting = shared.replace(_section(5), "Section 5 by agent B.").replace(
            _section(7), EDIT_7
        )
        result = await service.save_docx(doc_id, conflicting)

        assert result["success"] is False
        assert result["conflict_block_ids"] == ["p005"]
        assert "p005" in result["error"]
        assert result["current_revision"] == first["revision"]
        assert _artifacts(doc_dir) == before
        assert EDIT_5 in _document_text(doc_dir / "output.docx")

    @pytest.mark.asyncio
    async def test_force_does_not_bypass_a_revision_conflict(self, lease_env) -> None:
        service, source = lease_env
        doc_id, doc_dir = await _ingest(service, source)
        shared = await service.get_dfm(doc_id)
        assert shared is not None
        await service.save_docx(doc_id, shared.replace(_section(5), EDIT_5))

        result = await service.save_docx(
            doc_id, shared.replace(_section(5), "Overwrite attempt."), force=True
        )

        assert result["success"] is False
        assert result["conflict_block_ids"] == ["p005"]
        assert EDIT_5 in (doc_dir / "content.dfm").read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_identical_stale_edit_is_already_applied(self, lease_env) -> None:
        """Retrying the same save from the old DFM is not a conflict."""
        service, source = lease_env
        doc_id, _doc_dir = await _ingest(service, source)
        shared = await service.get_dfm(doc_id)
        assert shared is not None
        edited = shared.replace(_section(5), EDIT_5)
        first = await service.save_docx(doc_id, edited)
        assert first["success"] is True, first

        retry = await service.save_docx(doc_id, edited)

        assert retry["success"] is True, retry
        assert retry["revision_merge"]["already_applied_block_ids"] == ["p005"]
        assert retry["edited_block_ids"] == []
        assert retry["revision"] == first["revision"]

    @pytest.mark.asyncio
    async def test_unknown_revision_is_refused(self, lease_env) -> None:
        service, source = lease_env
        doc_id, _doc_dir = await _ingest(service, source)
        dfm = await service.get_dfm(doc_id)
        assert dfm is not None
        ir = service._load_ir(doc_id)
        assert ir is not None
        bogus = dfm.replace(
            service.ir_revision(ir), "rev-00000000000000000000000000000000"
        )

        result = await service.save_docx(doc_id, bogus.replace(_section(1), "x"))

        assert result["success"] is False
        assert "retained revision history" in result["error"]

    @pytest.mark.asyncio
    async def test_revision_history_is_capped_and_pruned(self, lease_env) -> None:
        service, source = lease_env
        service._revision_history_limit = 3
        doc_id, doc_dir = await _ingest(service, source)
        oldest: str | None = None
        for round_no in range(5):
            current = await service.get_dfm(doc_id)
            assert current is not None
            if round_no == 1:
                oldest = current  # based on the first saved revision
            marker = _section(1) if round_no == 0 else f"Round {round_no - 1}."
            result = await service.save_docx(
                doc_id, current.replace(marker, f"Round {round_no}.")
            )
            assert result["success"] is True, result
        assert oldest is not None

        stale = await service.save_docx(doc_id, oldest.replace(_section(8), "late"))

        assert stale["success"] is False
        assert "retained revision history" in stale["error"]
        kinds = _db_rows(doc_dir, "SELECT kind FROM revisions")
        assert len(kinds) == 4  # root + the newest 3
        payloads = _db_rows(doc_dir, "SELECT COUNT(*) FROM block_payloads")[0][0]
        root_blocks = _db_rows(doc_dir, "SELECT COUNT(*) FROM root_manifest")[0][0]
        assert payloads <= root_blocks + 3


# ============================================================================
# (b)-(e), (h) Block checkout / commit / release
# ============================================================================


class TestBlockLeases:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("order", ["A-then-B", "B-then-A"])
    async def test_two_leases_commit_in_either_order(self, lease_env, order) -> None:
        service, source = lease_env
        doc_id, doc_dir = await _ingest(service, source)
        original = doc_dir / "original.docx"
        lease_a = await service.checkout_blocks(doc_id, ["p005"], holder="agent-A")
        lease_b = await service.checkout_blocks(doc_id, ["p007"], holder="agent-B")
        assert lease_a["success"] and lease_b["success"], (lease_a, lease_b)
        assert lease_a["revision"] == lease_b["revision"]
        commits = {
            "A": (lease_a, _edited(lease_a, "p005", _section(5), EDIT_5)),
            "B": (lease_b, _edited(lease_b, "p007", _section(7), EDIT_7)),
        }
        sequence = ["A", "B"] if order == "A-then-B" else ["B", "A"]

        results = []
        for name in sequence:
            lease, edits = commits[name]
            result = await service.commit_block_lease(
                doc_id, lease["lease_token"], edits
            )
            assert result["success"] is True, result
            assert "PASS" in result["integrity"]
            assert result["lease_released"] is True
            results.append(result)

        assert results[1]["previous_revision"] == results[0]["revision"]
        output = Path(results[1]["output_path"])
        text = _document_text(output)
        assert EDIT_5 in text
        assert EDIT_7 in text
        assert sorted(results[1]["changed_block_ids"]) == ["p005", "p007"]
        # Only word/document.xml changes; unedited body elements are identical.
        original_parts = _zip_parts(original)
        output_parts = _zip_parts(output)
        assert {
            name
            for name in original_parts
            if original_parts[name] != output_parts[name]
        } == {"word/document.xml"}
        before = _body_elements(original)
        after = _body_elements(output)
        assert len(before) == len(after)
        edited = {
            index
            for index, element in enumerate(after)
            if _visible_text(element) in {EDIT_5, EDIT_7}
        }
        assert len(edited) == 2
        for index, (old, new) in enumerate(zip(before, after, strict=True)):
            if index not in edited:
                assert etree.tostring(old) == etree.tostring(new), index
        listing = await service.list_block_leases(doc_id)
        assert listing["leases"] == []
        assert listing["revision"] == results[1]["revision"]

    @pytest.mark.asyncio
    async def test_overlapping_checkout_is_refused(self, lease_env) -> None:
        service, source = lease_env
        doc_id, _doc_dir = await _ingest(service, source)
        first = await service.checkout_blocks(
            doc_id, ["p005", "p006"], holder="agent-A", ttl_seconds=120
        )
        assert first["success"] is True, first

        second = await service.checkout_blocks(
            doc_id, ["p006", "p007"], holder="agent-B"
        )

        assert second["success"] is False
        conflict = second["conflicts"][0]
        assert conflict["holder"] == "agent-A"
        assert conflict["block_ids"] == ["p006"]
        assert conflict["lease_id"] == first["lease_id"]
        assert "expires_at" in conflict
        listing = await service.list_block_leases(doc_id)
        assert [lease["holder"] for lease in listing["leases"]] == ["agent-A"]
        assert "lease_token" not in json.dumps(listing)
        assert first["lease_token"] not in json.dumps(listing)

    @pytest.mark.asyncio
    async def test_nested_table_family_is_leased_as_one_unit(self, lease_env) -> None:
        service, source = lease_env
        doc_id, _doc_dir = await _ingest(service, source)

        nested = await service.checkout_blocks(doc_id, ["t002"], holder="agent-A")
        parent = await service.checkout_blocks(doc_id, ["t001"], holder="agent-B")

        assert nested["success"] is True, nested
        assert nested["block_ids"] == ["t001", "t002"]
        assert nested["expanded_block_ids"] == ["t001"]
        assert parent["success"] is False
        assert parent["conflicts"][0]["holder"] == "agent-A"

    @pytest.mark.asyncio
    async def test_protected_or_unknown_blocks_cannot_be_leased(
        self, lease_env
    ) -> None:
        service, source = lease_env
        doc_id, _doc_dir = await _ingest(service, source)

        unknown = await service.checkout_blocks(doc_id, ["p404"], holder="agent-A")
        no_holder = await service.checkout_blocks(doc_id, ["p001"], holder=" ")
        too_long = await service.checkout_blocks(
            doc_id, ["p001"], holder="agent-A", ttl_seconds=7200
        )
        blocking = await service.checkout_blocks(
            doc_id, ["p001"], holder="agent-A", wait=True
        )

        assert unknown["success"] is False and "p404" in unknown["error"]
        assert no_holder["success"] is False and "holder" in no_holder["error"]
        assert too_long["success"] is False and "ttl_seconds" in too_long["error"]
        assert blocking["success"] is False and "wait=true" in blocking["error"]

    @pytest.mark.asyncio
    async def test_commit_to_a_non_leased_block_is_refused(self, lease_env) -> None:
        service, source = lease_env
        doc_id, doc_dir = await _ingest(service, source)
        lease = await service.checkout_blocks(doc_id, ["p005"], holder="agent-A")
        before = _artifacts(doc_dir)

        other_block = await service.commit_block_lease(
            doc_id,
            lease["lease_token"],
            {"p006": f"<!-- @b:p006 -->\n{EDIT_7}"},
        )
        smuggled = await service.commit_block_lease(
            doc_id,
            lease["lease_token"],
            {"p005": f"<!-- @b:p005 -->\n{EDIT_5}\n\n<!-- @b:p006 -->\nsmuggled"},
        )
        kind_change = await service.commit_block_lease(
            doc_id,
            lease["lease_token"],
            {"p005": "<!-- dfm:table @b:p005 -->\n| a |\n| - |\n<!-- /dfm:table -->"},
        )

        assert other_block["success"] is False
        assert "p006" in other_block["error"] and "not in lease" in other_block["error"]
        assert smuggled["success"] is False
        assert "exactly one block marker" in smuggled["error"]
        assert kind_change["success"] is False
        assert "block kind" in kind_change["error"]
        assert _artifacts(doc_dir) == before
        listing = await service.list_block_leases(doc_id)
        assert listing["live_leases"] == 1

    @pytest.mark.asyncio
    async def test_commit_accepts_marker_less_text_and_keeps_lease(
        self, lease_env
    ) -> None:
        service, source = lease_env
        doc_id, _doc_dir = await _ingest(service, source)
        lease = await service.checkout_blocks(
            doc_id, ["p005"], holder="agent-A", ttl_seconds=300
        )

        first = await service.commit_block_lease(
            doc_id, lease["lease_token"], {"p005": EDIT_5}, keep_lease=True
        )
        second = await service.commit_block_lease(
            doc_id, lease["lease_token"], {"p005": EDIT_5 + " Again."}
        )

        assert first["success"] is True, first
        assert first["lease_released"] is False
        assert second["success"] is True, second
        assert "Again." in _document_text(Path(second["output_path"]))

    @pytest.mark.asyncio
    async def test_table_shape_changes_are_refused_with_guidance(
        self, lease_env
    ) -> None:
        service, source = lease_env
        doc_id, _doc_dir = await _ingest(service, source)
        lease = await service.checkout_blocks(doc_id, ["t001"], holder="agent-A")
        fragment = _fragment(lease, "t001")
        widened = fragment.replace(
            "<!-- /dfm:table -->", "| Extra | row |\n<!-- /dfm:table -->"
        )

        refused = await service.commit_block_lease(
            doc_id, lease["lease_token"], {"t001": widened}
        )
        cell_edit = await service.commit_block_lease(
            doc_id, lease["lease_token"], {"t001": fragment.replace("40 ", "60 ")}
        )

        assert refused["success"] is False
        assert "Table structural edits" in refused["error"]
        assert "update_docx_table_grid" in refused["error"]
        assert cell_edit["success"] is True, cell_edit
        assert "60" in _document_text(Path(cell_edit["output_path"]))


class TestLeaseLifecycle:
    @pytest.mark.asyncio
    async def test_expired_lease_cannot_commit_and_is_reclaimed(
        self, lease_env
    ) -> None:
        service, source = lease_env
        clock = FakeClock()
        service._clock = clock
        doc_id, _doc_dir = await _ingest(service, source)
        lease = await service.checkout_blocks(
            doc_id, ["p005"], holder="agent-A", ttl_seconds=60
        )
        clock.advance(61)

        expired = await service.commit_block_lease(
            doc_id, lease["lease_token"], {"p005": EDIT_5}
        )
        listing = await service.list_block_leases(doc_id)
        taken = await service.checkout_blocks(doc_id, ["p005"], holder="agent-B")
        after_reclaim = await service.commit_block_lease(
            doc_id, lease["lease_token"], {"p005": EDIT_5}
        )

        assert expired["success"] is False and "expired" in expired["error"]
        assert listing["leases"][0]["status"] == "expired"
        assert listing["live_leases"] == 0
        assert taken["success"] is True, taken
        assert taken["reclaimed_expired_leases"] == [lease["lease_id"]]
        assert after_reclaim["success"] is False
        assert "reclaimed" in after_reclaim["error"]

    @pytest.mark.asyncio
    async def test_release_frees_blocks_and_retires_the_token(self, lease_env) -> None:
        service, source = lease_env
        doc_id, _doc_dir = await _ingest(service, source)
        lease = await service.checkout_blocks(doc_id, ["p005"], holder="agent-A")

        released = await service.release_block_lease(doc_id, lease["lease_token"])
        reused = await service.commit_block_lease(
            doc_id, lease["lease_token"], {"p005": EDIT_5}
        )
        other = await service.checkout_blocks(doc_id, ["p005"], holder="agent-B")

        assert released["success"] is True
        assert released["released_block_ids"] == ["p005"]
        assert reused["success"] is False and "was released" in reused["error"]
        assert other["success"] is True, other

    @pytest.mark.asyncio
    async def test_renew_extends_only_live_leases(self, lease_env) -> None:
        service, source = lease_env
        clock = FakeClock()
        service._clock = clock
        doc_id, _doc_dir = await _ingest(service, source)
        lease = await service.checkout_blocks(
            doc_id, ["p005"], holder="agent-A", ttl_seconds=60
        )
        clock.advance(50)

        renewed = await service.renew_block_lease(doc_id, lease["lease_token"], 120)
        clock.advance(100)
        still_live = await service.commit_block_lease(
            doc_id, lease["lease_token"], {"p005": EDIT_5}, keep_lease=True
        )
        clock.advance(500)
        too_late = await service.renew_block_lease(doc_id, lease["lease_token"])

        assert renewed["success"] is True and renewed["ttl_seconds"] == 120
        assert still_live["success"] is True, still_live
        assert too_late["success"] is False and "expired" in too_late["error"]

    @pytest.mark.asyncio
    async def test_break_lease_requires_expiry_or_force(self, lease_env) -> None:
        service, source = lease_env
        clock = FakeClock()
        service._clock = clock
        doc_id, _doc_dir = await _ingest(service, source)
        live = await service.checkout_blocks(doc_id, ["p005"], holder="agent-A")
        stale = await service.checkout_blocks(
            doc_id, ["p007"], holder="agent-B", ttl_seconds=10
        )
        clock.advance(11)

        refused = await service.break_block_lease(doc_id, live["lease_id"])
        broken_expired = await service.break_block_lease(doc_id, stale["lease_id"])
        broken_live = await service.break_block_lease(
            doc_id, live["lease_id"], force=True
        )
        holder_commit = await service.commit_block_lease(
            doc_id, live["lease_token"], {"p005": EDIT_5}
        )

        assert refused["success"] is False and "force=true" in refused["error"]
        assert broken_expired["success"] is True
        assert broken_expired["was_live"] is False
        assert broken_live["success"] is True and broken_live["was_live"] is True
        assert holder_commit["success"] is False
        assert "broken" in holder_commit["error"]

    @pytest.mark.asyncio
    async def test_reingest_refuses_to_discard_live_leases(self, lease_env) -> None:
        service, source = lease_env
        doc_id, _doc_dir = await _ingest(service, source)
        lease = await service.checkout_blocks(doc_id, ["p005"], holder="agent-A")

        refused = await service.ingest_docx(str(source))
        await service.release_block_lease(doc_id, lease["lease_token"])
        accepted = await service.ingest_docx(str(source))

        assert refused["success"] is False
        assert "agent-A" in refused["error"]
        assert accepted["success"] is True, accepted


# ============================================================================
# (f) Full-DFM saves and IR-only writes respect leases
# ============================================================================


class TestLeasesAcrossApis:
    @pytest.mark.asyncio
    async def test_full_dfm_save_refuses_blocks_leased_by_another_agent(
        self, lease_env
    ) -> None:
        service, source = lease_env
        doc_id, doc_dir = await _ingest(service, source)
        dfm = await service.get_dfm(doc_id)
        assert dfm is not None
        lease = await service.checkout_blocks(doc_id, ["p005"], holder="agent-A")
        before = _artifacts(doc_dir)

        refused = await service.save_docx(doc_id, dfm.replace(_section(5), "B"))
        after_refusal = _artifacts(doc_dir)
        allowed = await service.save_docx(doc_id, dfm.replace(_section(7), EDIT_7))
        commit = await service.commit_block_lease(
            doc_id, lease["lease_token"], {"p005": EDIT_5}
        )

        assert refused["success"] is False
        assert refused["leased_blocks"][0]["holder"] == "agent-A"
        assert refused["leased_blocks"][0]["block_ids"] == ["p005"]
        assert after_refusal == before
        assert allowed["success"] is True, allowed
        assert commit["success"] is True, commit
        text = _document_text(Path(commit["output_path"]))
        assert EDIT_5 in text and EDIT_7 in text

    @pytest.mark.asyncio
    async def test_ir_block_updates_respect_leases_and_sync_artifacts(
        self, lease_env
    ) -> None:
        service, source = lease_env
        doc_id, doc_dir = await _ingest(service, source)
        lease = await service.checkout_blocks(doc_id, ["t002"], holder="agent-A")

        def set_cell(ir) -> None:
            table = ir.find_block("t001")
            table.content = table.content.replace("40 ", "75 ")

        refused = await service.update_ir_blocks(
            doc_id, ["t001"], set_cell, actor="TableContext x"
        )
        await service.release_block_lease(doc_id, lease["lease_token"])
        applied = await service.update_ir_blocks(
            doc_id, ["t001"], set_cell, actor="TableContext x"
        )

        assert refused["success"] is False
        assert "agent-A" in refused["error"]
        assert applied["success"] is True, applied
        assert applied["changed_block_ids"] == ["t001"]
        for name in ("content.dfm", "format.yaml"):
            text = (doc_dir / name).read_text(encoding="utf-8")
            assert f"revision: {applied['revision']}" in text, name
        assert "75" in (doc_dir / "content.md").read_text(encoding="utf-8")
        saved = await service.save_docx(doc_id)
        assert saved["success"] is True, saved
        assert "75" in _document_text(Path(saved["output_path"]))


# ============================================================================
# (h) Track Changes attribute each block to its lease holder
# ============================================================================


class TestTrackChangesPerHolder:
    @pytest.mark.asyncio
    async def test_tracked_commits_keep_distinct_authors(self, lease_env) -> None:
        service, source = lease_env
        doc_id, doc_dir = await _ingest(service, source)
        lease_a = await service.checkout_blocks(doc_id, ["p005"], holder="agent-A")
        lease_b = await service.checkout_blocks(doc_id, ["p007"], holder="agent-B")

        first = await service.commit_block_lease(
            doc_id,
            lease_a["lease_token"],
            _edited(lease_a, "p005", _section(5), EDIT_5),
            track_changes=True,
        )
        second = await service.commit_block_lease(
            doc_id,
            lease_b["lease_token"],
            _edited(lease_b, "p007", _section(7), EDIT_7),
            track_changes=True,
        )

        assert first["success"] and second["success"], (first, second)
        assert first["revision_author"] == "agent-A"
        assert second["revision_authors"] == {"p005": "agent-A", "p007": "agent-B"}
        with ZipFile(second["output_path"]) as zf:
            tree = etree.fromstring(zf.read("word/document.xml"))
        inserted: dict[str, str] = {}
        for ins in tree.iterfind(".//w:ins", namespaces=W):
            author = ins.get(f"{{{W_NS}}}author")
            text = "".join(t.text or "" for t in ins.iterfind(".//w:t", namespaces=W))
            inserted[author] = inserted.get(author, "") + text
        assert set(inserted) == {"agent-A", "agent-B"}
        # Token-level revisions: equal tokens/spaces stay outside w:ins.
        assert (
            inserted["agent-A"].startswith("rewritten") and "A." in inserted["agent-A"]
        )
        assert (
            inserted["agent-B"].startswith("rewritten") and "B." in inserted["agent-B"]
        )
        records = [
            json.loads(line)
            for line in (doc_dir / "revisions.jsonl").read_text("utf-8").splitlines()
        ]
        authors = {record["block_id"]: record["revision_author"] for record in records}
        assert authors == {"p005": "agent-A", "p007": "agent-B"}


# ============================================================================
# (i) Legacy DFMs without `revision`
# ============================================================================


class TestLegacyDfmWithoutRevision:
    @pytest.mark.asyncio
    async def test_accepted_when_never_saved_since_ingest(self, lease_env) -> None:
        service, source = lease_env
        doc_id, _doc_dir = await _ingest(service, source)
        dfm = await service.get_dfm(doc_id)
        assert dfm is not None

        result = await service.save_docx(
            doc_id, _strip_revision(dfm).replace(_section(5), EDIT_5)
        )

        assert result["success"] is True, result
        assert result["revision_merge"]["mode"] == "legacy"
        assert any("no `revision`" in w for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_refused_with_guidance_after_a_save(self, lease_env) -> None:
        service, source = lease_env
        doc_id, doc_dir = await _ingest(service, source)
        legacy = _strip_revision(await service.get_dfm(doc_id) or "")
        current = await service.get_dfm(doc_id)
        assert current is not None
        saved = await service.save_docx(doc_id, current.replace(_section(5), EDIT_5))
        assert saved["success"] is True, saved

        refused = await service.save_docx(doc_id, legacy.replace(_section(7), EDIT_7))
        unchanged = await service.save_docx(
            doc_id, _strip_revision(await service.get_dfm(doc_id) or "")
        )

        assert refused["success"] is False
        assert "no `revision`" in refused["error"]
        assert "saved since ingest" in refused["error"]
        assert 'docx(op="checkout")' in refused["error"]
        assert EDIT_5 in (doc_dir / "content.dfm").read_text(encoding="utf-8")
        # A legacy DFM identical to the current content cannot lose anything.
        assert unchanged["success"] is True, unchanged

    @pytest.mark.asyncio
    async def test_pre_revision_workspace_is_adopted(self, lease_env) -> None:
        """A 1.4.2 directory (saved edits, no edit-state DB) keeps working."""
        service, source = lease_env
        doc_id, doc_dir = await _ingest(service, source)
        dfm = await service.get_dfm(doc_id)
        assert dfm is not None
        saved = await service.save_docx(doc_id, dfm.replace(_section(5), EDIT_5))
        assert saved["success"] is True, saved
        (doc_dir / EDIT_STATE_DB_FILENAME).unlink()
        current = await service.get_dfm(doc_id)
        assert current is not None

        legacy = await service.save_docx(
            doc_id, _strip_revision(current).replace(_section(7), EDIT_7)
        )
        revisioned = await service.save_docx(
            doc_id, current.replace(_section(7), EDIT_7)
        )

        assert legacy["success"] is False
        assert revisioned["success"] is True, revisioned
        text = _document_text(Path(revisioned["output_path"]))
        assert EDIT_5 in text and EDIT_7 in text
        kinds = [
            row[0]
            for row in _db_rows(doc_dir, "SELECT kind FROM revisions ORDER BY seq")
        ]
        assert kinds == ["ingest", "adopted", "save"]


# ============================================================================
# (g) Two OS processes, (j) crash safety
# ============================================================================


def _spawn_worker(spec: dict, spec_path: Path) -> subprocess.Popen:
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.Popen(
        [sys.executable, "-m", "tests.integration.docx_lease_worker", str(spec_path)],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _finish(process: subprocess.Popen) -> tuple[int, str]:
    output, _ = process.communicate(timeout=180)
    return process.returncode, output.decode("utf-8", "replace")


class TestCrossProcessCommits:
    @pytest.mark.asyncio
    async def test_concurrent_commits_from_two_processes_keep_both_edits(
        self, lease_env, temp_dir: Path
    ) -> None:
        service, source = lease_env
        doc_id, doc_dir = await _ingest(service, source)
        lease_a = await service.checkout_blocks(doc_id, ["p005"], holder="proc-A")
        lease_b = await service.checkout_blocks(doc_id, ["p007"], holder="proc-B")
        go_file = temp_dir / "go"
        processes = []
        for name, lease, edits in (
            ("a", lease_a, _edited(lease_a, "p005", _section(5), EDIT_5)),
            ("b", lease_b, _edited(lease_b, "p007", _section(7), EDIT_7)),
        ):
            spec = {
                "data_dir": str(temp_dir / "data"),
                "doc_id": doc_id,
                "token": lease["lease_token"],
                "edits": edits,
                "go_file": str(go_file),
                "slow_seconds": 1.0,
                "result_file": str(temp_dir / f"result-{name}.json"),
            }
            processes.append(_spawn_worker(spec, temp_dir / f"spec-{name}.json"))
        go_file.write_text("go", encoding="utf-8")

        outcomes = [_finish(process) for process in processes]

        assert [code for code, _ in outcomes] == [0, 0], outcomes
        results = [
            json.loads((temp_dir / f"result-{name}.json").read_text("utf-8"))
            for name in ("a", "b")
        ]
        assert all(result["success"] for result in results), results
        # Serialized: one commit was built on top of the other's revision.
        revisions = {result["revision"] for result in results}
        previous = {result["previous_revision"] for result in results}
        assert len(revisions & previous) == 1
        ir_text = (doc_dir / "ir.json").read_text(encoding="utf-8")
        assert EDIT_5 in ir_text and EDIT_7 in ir_text
        final = (await service.list_block_leases(doc_id))["revision"]
        last = next(result for result in results if result["revision"] == final)
        text = _document_text(Path(last["output_path"]))
        assert EDIT_5 in text and EDIT_7 in text
        assert _db_rows(doc_dir, "PRAGMA integrity_check") == [("ok",)]
        assert sorted(
            row[0]
            for row in _db_rows(
                doc_dir, "SELECT actor FROM revisions WHERE kind='commit'"
            )
        ) == ["proc-A", "proc-B"]
        assert _db_rows(doc_dir, "SELECT COUNT(*) FROM leases") == [(0,)]
        assert _stray_files(doc_dir) == []


class TestCrashSafety:
    @pytest.mark.asyncio
    async def test_failed_write_leaves_files_and_lease_untouched(
        self, lease_env, monkeypatch
    ) -> None:
        service, source = lease_env
        doc_id, doc_dir = await _ingest(service, source)
        warmup = await service.save_docx(doc_id)
        assert warmup["success"] is True, warmup
        lease = await service.checkout_blocks(doc_id, ["p005"], holder="agent-A")
        before = _artifacts(doc_dir)
        history = _db_rows(doc_dir, "SELECT COUNT(*) FROM revisions")

        def broken_writer(*args, **kwargs):
            raise RuntimeError("disk full while writing DOCX")

        monkeypatch.setattr(service.adapter, "ir_to_docx", broken_writer)
        failed = await service.commit_block_lease(
            doc_id, lease["lease_token"], {"p005": EDIT_5}
        )
        monkeypatch.undo()

        assert failed["success"] is False
        assert "disk full" in failed["error"]
        assert _artifacts(doc_dir) == before
        assert _db_rows(doc_dir, "SELECT COUNT(*) FROM revisions") == history
        assert (await service.list_block_leases(doc_id))["live_leases"] == 1
        assert _stray_files(doc_dir) == []
        retried = await service.commit_block_lease(
            doc_id, lease["lease_token"], {"p005": EDIT_5}
        )
        assert retried["success"] is True, retried

    @pytest.mark.asyncio
    async def test_failure_at_the_commit_point_restores_the_output(
        self, lease_env, monkeypatch
    ) -> None:
        service, source = lease_env
        doc_id, doc_dir = await _ingest(service, source)
        warmup = await service.save_docx(doc_id)
        assert warmup["success"] is True, warmup
        lease = await service.checkout_blocks(doc_id, ["p005"], holder="agent-A")
        before = _artifacts(doc_dir)
        real_save_ir = service._save_ir

        def failing_save_ir(ir, path):
            if Path(path).name == "ir.json":
                raise OSError("ir.json is locked")
            real_save_ir(ir, path)

        monkeypatch.setattr(service, "_save_ir", failing_save_ir)
        failed = await service.commit_block_lease(
            doc_id, lease["lease_token"], {"p005": EDIT_5}
        )
        monkeypatch.undo()

        assert failed["success"] is False
        assert "ir.json is locked" in failed["error"]
        assert _artifacts(doc_dir) == before, "output.docx must be restored"
        listing = await service.list_block_leases(doc_id)
        assert listing["live_leases"] == 1
        assert listing["last_recorded_revision"] == listing["revision"]
        assert _stray_files(doc_dir) == []

    @pytest.mark.asyncio
    async def test_process_crash_after_ir_write_is_recovered(
        self, lease_env, temp_dir: Path
    ) -> None:
        """Kill the committing process between ir.json and the DB commit."""
        service, source = lease_env
        doc_id, doc_dir = await _ingest(service, source)
        lease = await service.checkout_blocks(doc_id, ["p005"], holder="agent-A")
        edits = _edited(lease, "p005", _section(5), EDIT_5)
        spec = {
            "data_dir": str(temp_dir / "data"),
            "doc_id": doc_id,
            "token": lease["lease_token"],
            "edits": edits,
            "crash_after_ir": True,
            "result_file": str(temp_dir / "crash-result.json"),
        }

        code, output = _finish(_spawn_worker(spec, temp_dir / "crash-spec.json"))

        assert code == 17, output
        assert EDIT_5 in (doc_dir / "ir.json").read_text(encoding="utf-8")
        listing = await service.list_block_leases(doc_id)
        assert listing["live_leases"] == 1, "the crashed commit must roll back"
        assert listing["last_recorded_revision"] != listing["revision"]
        assert _db_rows(doc_dir, "PRAGMA integrity_check") == [("ok",)]

        # A stale DFM reader keeps working: the next save merges around it.
        stale_dfm = (doc_dir / "content.dfm").read_text(encoding="utf-8")
        retried = await service.commit_block_lease(doc_id, lease["lease_token"], edits)
        assert retried["success"] is True, retried
        assert retried["already_applied_block_ids"] == ["p005"]
        assert EDIT_5 in _document_text(Path(retried["output_path"]))
        merged = await service.save_docx(doc_id, stale_dfm.replace(_section(7), EDIT_7))
        assert merged["success"] is True, merged
        text = _document_text(Path(merged["output_path"]))
        assert EDIT_5 in text and EDIT_7 in text
        kinds = [
            row[0]
            for row in _db_rows(doc_dir, "SELECT kind FROM revisions ORDER BY seq")
        ]
        assert kinds[-2:] == ["external", "save"]
