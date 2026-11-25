"""Regression tests: DOCX write-back must be cumulative since ingest.

Before the fix, ``save_docx`` diffed the edited DFM against the *current*
``ir.json`` but patched the pristine ``original.docx``. Every save after the
first silently dropped the earlier edits (while ``content.dfm``/``ir.json``
still claimed them), and a Track Changes save of the current DFM wrote a plain
copy of ``original.docx`` with zero revisions -- all reported as success.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from zipfile import ZipFile

import pytest
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from lxml import etree

from src.application.docx_baseline import BASELINE_IR_FILENAME
from src.application.docx_service import DocxService
from src.infrastructure.file_storage import FileStorage

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = {"w": W_NS}

TITLE = "Study Protocol for Postoperative Awareness Monitoring"
P_STYLED = "Investigators will monitor every enrolled patient continuously."
P_EDIT_B = "Participants must be at least 20 years old."
P_EDIT_B_NEW = "Participants must be at least 18 years old."
P_EDIT_E2 = "The study period runs for twelve months."
P_EDIT_E2_NEW = "The study period runs for eighteen months."
P_UNTOUCHED = "Data will be stored on encrypted hospital servers."
CELL_OLD = "40 participants"
CELL_NEW = "60 participants"
FOOTER = "IRB draft v1 - confidential"


def _build_irb_docx(path: Path) -> None:
    """Small IRB-like document: heading, styled runs, table, footer."""
    doc = Document()
    doc.add_heading(TITLE, level=1)

    styled = doc.add_paragraph()
    styled.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    lead = styled.add_run("Investigators will monitor ")
    lead.bold = True
    lead.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    tail = styled.add_run("every enrolled patient continuously.")
    tail.italic = True
    tail.font.size = Pt(13)

    edit_b = doc.add_paragraph()
    edit_b.paragraph_format.space_after = Pt(9)
    run_b = edit_b.add_run(P_EDIT_B)
    run_b.font.name = "Arial"
    run_b.font.size = Pt(12)

    edit_e2 = doc.add_paragraph()
    run_e2 = edit_e2.add_run(P_EDIT_E2)
    run_e2.underline = True

    doc.add_paragraph(P_UNTOUCHED)

    table = doc.add_table(rows=3, cols=2)
    table.style = "Table Grid"
    table.cell(0, 0).text = "Item"
    table.cell(0, 1).text = "Value"
    table.cell(1, 0).text = "Arm"
    table.cell(1, 1).text = "Intervention"
    table.cell(2, 0).text = "Sample size"
    table.cell(2, 1).text = CELL_OLD
    bold_cell_run = table.cell(2, 1).paragraphs[0].runs[0]
    bold_cell_run.bold = True

    doc.sections[0].footer.paragraphs[0].text = FOOTER
    doc.save(path)


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
    """Accepted-view text: w:t outside w:del (tracked deletions excluded)."""
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


def _revision_texts(path: Path) -> tuple[str, str]:
    with ZipFile(path) as zf:
        tree = etree.fromstring(zf.read("word/document.xml"))
    deleted = "".join(
        node.text or "" for node in tree.iterfind(".//w:delText", namespaces=W)
    )
    inserted = "".join(
        node.text or ""
        for ins in tree.iterfind(".//w:ins", namespaces=W)
        for node in ins.iterfind(".//w:t", namespaces=W)
    )
    return deleted, inserted


def _paragraph_index(path: Path, needle: str) -> int:
    for index, element in enumerate(_body_elements(path)):
        if needle in _visible_text(element):
            return index
    raise AssertionError(f"{needle!r} not found in {path}")


@pytest.fixture
def docx_env(temp_dir: Path):
    service = DocxService(repository=FileStorage(base_dir=temp_dir / "data"))
    source = temp_dir / "irb-draft.docx"
    _build_irb_docx(source)
    return service, source


async def _ingest(service: DocxService, source: Path) -> tuple[str, Path]:
    result = await service.ingest_docx(str(source))
    assert result["success"] is True, result
    doc_id = str(result["doc_id"])
    return doc_id, service.repository.get_doc_dir(doc_id)


def _edit_b(dfm: str) -> str:
    assert P_EDIT_B in dfm
    assert CELL_OLD in dfm
    return dfm.replace(P_EDIT_B, P_EDIT_B_NEW).replace(CELL_OLD, CELL_NEW)


def _edit_e2(dfm: str) -> str:
    assert P_EDIT_E2 in dfm
    return dfm.replace(P_EDIT_E2, P_EDIT_E2_NEW)


async def _save_b(service: DocxService, doc_id: str) -> dict:
    dfm = await service.get_dfm(doc_id)
    assert dfm is not None
    result = await service.save_docx(doc_id, _edit_b(dfm))
    assert result["success"] is True, result
    return result


class TestCumulativeWriteback:
    @pytest.mark.asyncio
    async def test_ingest_writes_immutable_baseline_matching_original(
        self, docx_env
    ) -> None:
        service, source = docx_env
        doc_id, doc_dir = await _ingest(service, source)

        baseline = json.loads((doc_dir / BASELINE_IR_FILENAME).read_text("utf-8"))
        current = json.loads((doc_dir / "ir.json").read_text("utf-8"))
        assert baseline["checksum"] == current["checksum"]
        assert baseline["blocks"] == current["blocks"]

        await _save_b(service, doc_id)

        after = json.loads((doc_dir / BASELINE_IR_FILENAME).read_text("utf-8"))
        assert after == baseline, "baseline_ir.json must never change on save"

    @pytest.mark.asyncio
    async def test_second_save_keeps_first_save_edits(self, docx_env) -> None:
        """(a) save B, then E2 from the current DFM: output has B and E2."""
        service, source = docx_env
        doc_id, doc_dir = await _ingest(service, source)
        original = doc_dir / "original.docx"
        original_parts = _zip_parts(original)
        original_body = _body_elements(original)

        first = await _save_b(service, doc_id)

        current_dfm = await service.get_dfm(doc_id)
        assert current_dfm is not None
        assert P_EDIT_B_NEW in current_dfm
        second = await service.save_docx(doc_id, _edit_e2(current_dfm))

        assert second["success"] is True, second
        assert "PASS" in second["integrity"]
        output = Path(second["output_path"])
        text = _document_text(output)
        assert P_EDIT_B_NEW in text
        assert CELL_NEW in text
        assert P_EDIT_E2_NEW in text
        assert P_EDIT_B not in text
        assert CELL_OLD not in text
        assert P_EDIT_E2 not in text
        assert first["edited_block_ids"] == first["changed_block_ids"]
        assert len(second["edited_block_ids"]) == 1
        assert set(first["changed_block_ids"]) < set(second["changed_block_ids"])

        # Only word/document.xml may change; every other part is byte-identical.
        output_parts = _zip_parts(output)
        assert output_parts.keys() == original_parts.keys()
        changed_parts = {
            name
            for name in original_parts
            if original_parts[name] != output_parts[name]
        }
        assert changed_parts == {"word/document.xml"}

        # Unedited body blocks keep their exact XML; edited ones keep pPr/rPr.
        output_body = _body_elements(output)
        assert len(output_body) == len(original_body)
        edited_indexes = {
            _paragraph_index(output, P_EDIT_B_NEW),
            _paragraph_index(output, P_EDIT_E2_NEW),
            _paragraph_index(output, CELL_NEW),
        }
        for index, (before, after) in enumerate(
            zip(original_body, output_body, strict=True)
        ):
            if index in edited_indexes:
                for props in (".//w:pPr", ".//w:rPr", ".//w:tcPr", "w:tblPr"):
                    old_props = [
                        etree.tostring(node)
                        for node in before.iterfind(props, namespaces=W)
                    ]
                    new_props = [
                        etree.tostring(node)
                        for node in after.iterfind(props, namespaces=W)
                    ]
                    assert old_props == new_props, (index, props)
            else:
                assert etree.tostring(before) == etree.tostring(after), index

        # Persisted editable state and the DOCX agree.
        saved_dfm = (doc_dir / "content.dfm").read_text(encoding="utf-8")
        assert P_EDIT_B_NEW in saved_dfm
        assert P_EDIT_E2_NEW in saved_dfm

    @pytest.mark.asyncio
    async def test_noop_save_after_edits_still_reflects_edits(self, docx_env) -> None:
        """(d) Re-saving the unchanged current DFM must not revert to original."""
        service, source = docx_env
        doc_id, doc_dir = await _ingest(service, source)
        await _save_b(service, doc_id)

        result = await service.save_docx(doc_id, output_path="resave.docx")

        assert result["success"] is True, result
        output = Path(result["output_path"])
        assert output.read_bytes() != (doc_dir / "original.docx").read_bytes()
        text = _document_text(output)
        assert P_EDIT_B_NEW in text
        assert CELL_NEW in text
        assert result["edited_block_ids"] == []
        assert len(result["changed_block_ids"]) == 2

    @pytest.mark.asyncio
    async def test_reverting_all_edits_restores_original_bytes(self, docx_env) -> None:
        """Round trips stay reversible: undoing edits yields original.docx."""
        service, source = docx_env
        doc_id, doc_dir = await _ingest(service, source)
        await _save_b(service, doc_id)
        current_dfm = await service.get_dfm(doc_id)
        assert current_dfm is not None
        reverted = current_dfm.replace(P_EDIT_B_NEW, P_EDIT_B).replace(
            CELL_NEW, CELL_OLD
        )

        result = await service.save_docx(doc_id, reverted, output_path="undo.docx")

        assert result["success"] is True, result
        assert result["changed_block_ids"] == []
        assert (
            Path(result["output_path"]).read_bytes()
            == (doc_dir / "original.docx").read_bytes()
        )

    @pytest.mark.asyncio
    async def test_ir_only_table_writeback_reaches_next_save(self, docx_env) -> None:
        """IR edits made without a DOCX save (docx_table_from_context) persist."""
        service, source = docx_env
        doc_id, doc_dir = await _ingest(service, source)
        ir = service._load_ir(doc_id)
        assert ir is not None
        table = next(block for block in ir.blocks if block.id.startswith("t"))
        table.content = table.content.replace(CELL_OLD, CELL_NEW)
        service._save_ir(ir, doc_dir / "ir.json")
        (doc_dir / "content.dfm").write_text(
            service.renderer.render(ir), encoding="utf-8"
        )

        result = await service.save_docx(doc_id)

        assert result["success"] is True, result
        assert result["changed_block_ids"] == [table.id]
        assert CELL_NEW in _document_text(Path(result["output_path"]))


class TestTrackChangesRevisionBase:
    @pytest.mark.asyncio
    async def test_fresh_ingest_track_changes(self, docx_env) -> None:
        """(c) The fresh-ingest Track Changes path keeps working."""
        service, source = docx_env
        doc_id, _doc_dir = await _ingest(service, source)
        dfm = await service.get_dfm(doc_id)
        assert dfm is not None

        result = await service.save_docx(
            doc_id,
            _edit_b(dfm),
            output_path="tracked.docx",
            track_changes=True,
            revision_author="IRB Reviewer",
        )

        assert result["success"] is True, result
        assert result["track_change_blocks"] == 2
        deleted, inserted = _revision_texts(Path(result["output_path"]))
        assert "20" in deleted
        assert "40" in deleted
        assert "18" in inserted
        assert "60" in inserted
        assert result["revision_base"] == "original"

    @pytest.mark.asyncio
    async def test_track_changes_after_plain_save_shows_all_edits(
        self, docx_env
    ) -> None:
        """(b) Tracked save after a plain save: revisions for every edit."""
        service, source = docx_env
        doc_id, doc_dir = await _ingest(service, source)
        await _save_b(service, doc_id)
        current_dfm = await service.get_dfm(doc_id)
        assert current_dfm is not None

        result = await service.save_docx(
            doc_id,
            _edit_e2(current_dfm),
            output_path="tracked.docx",
            track_changes=True,
        )

        assert result["success"] is True, result
        assert result["track_change_blocks"] == 3
        output = Path(result["output_path"])
        assert output.read_bytes() != (doc_dir / "original.docx").read_bytes()
        deleted, inserted = _revision_texts(output)
        for old in ("20", "40", "twelve"):
            assert old in deleted
        for new in ("18", "60", "eighteen"):
            assert new in inserted
        text = _document_text(output)
        assert P_EDIT_B_NEW in text
        assert CELL_NEW in text
        assert P_EDIT_E2_NEW in text
        with ZipFile(output) as zf:
            settings = etree.fromstring(zf.read("word/settings.xml"))
        assert settings.find("w:trackRevisions", namespaces=W) is not None

        records = [
            json.loads(line)
            for line in Path(result["revision_sidecar_path"])
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        assert {record["block_id"] for record in records} == set(
            result["tracked_block_ids"]
        )
        assert {record["revision_base"] for record in records} == {"original"}

    @pytest.mark.asyncio
    async def test_track_changes_of_unchanged_current_dfm_is_not_a_copy(
        self, docx_env
    ) -> None:
        """Reported v1.4.1 symptom: 0 blocks and a byte copy of original.docx."""
        service, source = docx_env
        doc_id, doc_dir = await _ingest(service, source)
        await _save_b(service, doc_id)
        current_dfm = await service.get_dfm(doc_id)

        result = await service.save_docx(
            doc_id, current_dfm, output_path="tracked.docx", track_changes=True
        )

        assert result["success"] is True, result
        assert result["track_change_blocks"] == 2
        assert result["revision_records"] > 0
        output = Path(result["output_path"])
        assert output.read_bytes() != (doc_dir / "original.docx").read_bytes()
        deleted, inserted = _revision_texts(output)
        assert "20" in deleted
        assert "18" in inserted

    @pytest.mark.asyncio
    async def test_last_save_base_tracks_only_new_edits(self, docx_env) -> None:
        service, source = docx_env
        doc_id, _doc_dir = await _ingest(service, source)
        await _save_b(service, doc_id)
        current_dfm = await service.get_dfm(doc_id)
        assert current_dfm is not None

        result = await service.save_docx(
            doc_id,
            _edit_e2(current_dfm),
            output_path="round2.docx",
            track_changes=True,
            revision_base="last_save",
        )

        assert result["success"] is True, result
        assert result["revision_base"] == "last_save"
        assert result["track_change_blocks"] == 1
        assert len(result["changed_block_ids"]) == 3
        output = Path(result["output_path"])
        deleted, inserted = _revision_texts(output)
        assert "twelve" in deleted
        assert "eighteen" in inserted
        assert "20" not in deleted
        assert "40" not in deleted
        text = _document_text(output)
        assert P_EDIT_B_NEW in text
        assert CELL_NEW in text
        assert P_EDIT_E2_NEW in text

    @pytest.mark.asyncio
    async def test_last_save_base_without_new_edits_warns(self, docx_env) -> None:
        service, source = docx_env
        doc_id, _doc_dir = await _ingest(service, source)
        await _save_b(service, doc_id)

        result = await service.save_docx(
            doc_id,
            output_path="round2.docx",
            track_changes=True,
            revision_base="last_save",
        )

        assert result["success"] is True, result
        assert result["track_change_blocks"] == 0
        assert any("no Word revisions" in w for w in result["warnings"])
        assert P_EDIT_B_NEW in _document_text(Path(result["output_path"]))

    @pytest.mark.asyncio
    async def test_unknown_revision_base_is_rejected(self, docx_env) -> None:
        service, source = docx_env
        doc_id, _doc_dir = await _ingest(service, source)

        result = await service.save_docx(
            doc_id, track_changes=True, revision_base="previous"
        )

        assert result["success"] is False
        assert "revision_base" in result["error"]


class TestLostEditDetection:
    @pytest.mark.asyncio
    async def test_integrity_fails_when_writer_drops_an_earlier_edit(
        self, docx_env, monkeypatch
    ) -> None:
        """(e) Emulate the v1.4.1 writer (session-only ids): the save must fail."""
        service, source = docx_env
        doc_id, doc_dir = await _ingest(service, source)
        await _save_b(service, doc_id)
        artifacts_before = {
            name: (doc_dir / name).read_bytes()
            for name in ("ir.json", "content.dfm", "content.md", "output.docx")
        }
        real_ir_to_docx = service.adapter.ir_to_docx
        edited_now: set[str] = set()

        def session_only_writer(ir, data_dir, output_path, **kwargs):
            kwargs["changed_block_ids"] = set(edited_now)
            return real_ir_to_docx(ir, data_dir, output_path, **kwargs)

        monkeypatch.setattr(service.adapter, "ir_to_docx", session_only_writer)
        current_dfm = await service.get_dfm(doc_id)
        assert current_dfm is not None
        ir = service._load_ir(doc_id)
        assert ir is not None
        edited_now.add(
            next(block.id for block in ir.blocks if block.content == P_EDIT_E2)
        )

        result = await service.save_docx(doc_id, _edit_e2(current_dfm))

        assert result["success"] is False
        assert "Post-save integrity check failed" in result["error"]
        for name, data in artifacts_before.items():
            assert (doc_dir / name).read_bytes() == data, name
        assert not list(doc_dir.glob(".*.tmp.docx"))

    @pytest.mark.asyncio
    async def test_track_changes_without_revisions_fails(
        self, docx_env, monkeypatch
    ) -> None:
        """A tracked save that writes no w:ins/w:del must not report success."""
        service, source = docx_env
        doc_id, doc_dir = await _ingest(service, source)
        await _save_b(service, doc_id)

        def plain_writer(ir, data_dir, output_path, **kwargs):
            kwargs.pop("original_ir", None)
            kwargs.pop("accepted_ir", None)
            kwargs.pop("accepted_block_ids", None)
            kwargs["track_changes"] = False
            return type(service.adapter).ir_to_docx(
                service.adapter, ir, data_dir, output_path, **kwargs
            )

        monkeypatch.setattr(service.adapter, "ir_to_docx", plain_writer)

        result = await service.save_docx(
            doc_id, output_path="tracked.docx", track_changes=True
        )

        assert result["success"] is False
        assert any("no new Word revisions" in w for w in result["warnings"])
        assert not (doc_dir / "tracked.docx").exists()


class TestLegacyWorkspaceMigration:
    @staticmethod
    async def _legacy_dir_with_saved_edits(service, source) -> tuple[str, Path]:
        """Simulate a v1.4.1 doc dir: edits in ir.json, no baseline snapshot."""
        doc_id, doc_dir = await _ingest(service, source)
        await _save_b(service, doc_id)
        (doc_dir / BASELINE_IR_FILENAME).unlink()
        # v1.4.1 output.docx lacked earlier edits; make that state explicit.
        shutil.copy2(doc_dir / "original.docx", doc_dir / "output.docx")
        return doc_id, doc_dir

    @pytest.mark.asyncio
    async def test_legacy_diverged_dir_rebuilds_baseline_and_keeps_edits(
        self, docx_env
    ) -> None:
        """(f) Diverged legacy dir: rebuild baseline from original.docx."""
        service, source = docx_env
        doc_id, doc_dir = await self._legacy_dir_with_saved_edits(service, source)
        current_dfm = await service.get_dfm(doc_id)
        assert current_dfm is not None

        result = await service.save_docx(doc_id, _edit_e2(current_dfm))

        assert result["success"] is True, result
        assert result["baseline_rebuilt"] is True
        migration = next(w for w in result["warnings"] if "legacy" in w.lower())
        assert "2 block(s) already differed" in migration
        text = _document_text(Path(result["output_path"]))
        assert P_EDIT_B_NEW in text
        assert CELL_NEW in text
        assert P_EDIT_E2_NEW in text

        rebuilt = json.loads((doc_dir / BASELINE_IR_FILENAME).read_text("utf-8"))
        current = json.loads((doc_dir / "ir.json").read_text("utf-8"))
        assert rebuilt["checksum"] == current["checksum"]
        assert [b["id"] for b in rebuilt["blocks"]] == [
            b["id"] for b in current["blocks"]
        ]
        assert any(b["content"] == P_EDIT_B for b in rebuilt["blocks"])

        again = await service.save_docx(doc_id, output_path="again.docx")
        assert again["success"] is True, again
        assert "baseline_rebuilt" not in again

    @pytest.mark.asyncio
    async def test_legacy_dir_with_replaced_original_is_refused(
        self, docx_env, temp_dir: Path
    ) -> None:
        service, source = docx_env
        doc_id, doc_dir = await self._legacy_dir_with_saved_edits(service, source)
        other = temp_dir / "other.docx"
        doc = Document()
        doc.add_paragraph("A different document")
        doc.save(other)
        shutil.copy2(other, doc_dir / "original.docx")
        output_before = (doc_dir / "output.docx").read_bytes()

        result = await service.save_docx(doc_id)

        assert result["success"] is False
        assert "no longer matches the checksum recorded at ingest" in result["error"]
        assert "Re-ingest" in result["error"]
        assert (doc_dir / "output.docx").read_bytes() == output_before
        assert not (doc_dir / BASELINE_IR_FILENAME).exists()

    @pytest.mark.asyncio
    async def test_legacy_dir_with_mismatched_structure_is_refused(
        self, docx_env
    ) -> None:
        service, source = docx_env
        doc_id, doc_dir = await self._legacy_dir_with_saved_edits(service, source)
        ir_path = doc_dir / "ir.json"
        data = json.loads(ir_path.read_text(encoding="utf-8"))
        data["blocks"][1]["id"] = "p999"
        ir_path.write_text(json.dumps(data), encoding="utf-8")
        dfm = (doc_dir / "content.dfm").read_text(encoding="utf-8")
        assert "@b:p001" in dfm

        result = await service.save_docx(doc_id, dfm.replace("@b:p001", "@b:p999"))

        assert result["success"] is False
        assert "does not match the block structure" in result["error"]
        assert not (doc_dir / BASELINE_IR_FILENAME).exists()

    @pytest.mark.asyncio
    async def test_corrupt_baseline_is_refused(self, docx_env) -> None:
        service, source = docx_env
        doc_id, doc_dir = await _ingest(service, source)
        (doc_dir / BASELINE_IR_FILENAME).write_text("{not json", encoding="utf-8")

        result = await service.save_docx(doc_id)

        assert result["success"] is False
        assert BASELINE_IR_FILENAME in result["error"]


class TestImageProjection:
    @pytest.mark.asyncio
    async def test_image_markdown_projection_is_not_a_cumulative_edit(
        self, temp_dir: Path
    ) -> None:
        """An image block's DFM text must not count as an unwritable edit."""
        from docx.shared import Cm
        from PIL import Image

        picture = temp_dir / "figure.png"
        Image.new("RGB", (16, 16), "red").save(picture)
        source = temp_dir / "with-image.docx"
        doc = Document()
        doc.add_paragraph("Before the figure.")
        doc.add_picture(str(picture), width=Cm(2))
        doc.add_paragraph("After the figure.")
        doc.save(source)
        service = DocxService(repository=FileStorage(base_dir=temp_dir / "data"))
        doc_id, doc_dir = await _ingest(service, source)

        result = await service.save_docx(doc_id, output_path="noop.docx")

        assert result["success"] is True, result
        assert result["changed_block_ids"] == []
        assert "warnings" not in result
        assert (
            Path(result["output_path"]).read_bytes()
            == (doc_dir / "original.docx").read_bytes()
        )

        # v1.4.1 stored the Markdown projection as the image IR content.
        ir = service._load_ir(doc_id)
        assert ir is not None
        image = next(block for block in ir.blocks if block.id.startswith("i"))
        image.content = service.parser.image_markdown(image)
        service._save_ir(ir, doc_dir / "ir.json")
        (doc_dir / BASELINE_IR_FILENAME).unlink()

        legacy = await service.save_docx(doc_id, output_path="legacy.docx")

        assert legacy["success"] is True, legacy
        assert legacy["changed_block_ids"] == []
        assert not any("cannot write" in w for w in legacy.get("warnings", []))
