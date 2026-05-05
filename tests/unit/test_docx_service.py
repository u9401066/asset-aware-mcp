from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dfm_integrity import IntegrityIssue, IntegrityReport
from src.application.docx_service import DocxService
from src.domain.docx_entities import DfmBlock, DocxIR
from src.domain.docx_value_objects import DfmBlockType
from src.infrastructure.dfm_parser import BlockEdit, DfmParseResult


def test_find_libreoffice_binary_prefers_env_var(monkeypatch, tmp_path):
    fake_bin = tmp_path / "soffice"
    fake_bin.touch()
    monkeypatch.setenv("LIBREOFFICE_BIN", str(fake_bin))
    monkeypatch.setattr("src.application.docx_service.shutil.which", lambda _name: None)

    assert DocxService._find_libreoffice_binary() == str(fake_bin)


def test_find_libreoffice_binary_uses_soffice_on_macos(monkeypatch):
    monkeypatch.delenv("LIBREOFFICE_BIN", raising=False)

    def fake_which(name: str):
        if name == "soffice":
            return "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        return None

    monkeypatch.setattr("src.application.docx_service.shutil.which", fake_which)

    assert (
        DocxService._find_libreoffice_binary()
        == "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    )


@pytest.mark.asyncio
async def test_delete_docx_success():
    repository = MagicMock()
    repository.list_docx_documents.return_value = [
        {"doc_id": "docx_123", "filename": "demo.docx"}
    ]
    repository.delete_document.return_value = True

    service = DocxService(repository=repository)

    result = await service.delete_docx("docx_123")

    assert result == {"success": True, "doc_id": "docx_123", "filename": "demo.docx"}
    repository.delete_document.assert_called_once_with("docx_123")


@pytest.mark.asyncio
async def test_delete_docx_not_found():
    repository = MagicMock()
    repository.list_docx_documents.return_value = []

    service = DocxService(repository=repository)

    result = await service.delete_docx("missing")

    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_convert_to_pdf_rejects_non_fidelity_mode():
    service = DocxService(repository=MagicMock())

    result = await service.convert_to_pdf("docx_123", mode="content")

    assert result["success"] is False
    assert "fidelity mode only" in result["error"]


@pytest.mark.asyncio
async def test_convert_to_pdf_success(monkeypatch, tmp_path: Path):
    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path
    (tmp_path / "ir.json").write_text("{}", encoding="utf-8")

    service = DocxService(repository=repository)
    service.get_dfm = AsyncMock(return_value="# title")
    service.save_docx = AsyncMock(
        return_value={"success": True, "output_path": str(tmp_path / "tmp.docx")}
    )

    output_pdf = tmp_path / "result.pdf"

    def write_fake_pdf(cls, docx_path, output_path):
        output_path.write_bytes(b"%PDF fake")
        return output_path

    monkeypatch.setattr(
        DocxService,
        "_convert_docx_file_to_pdf",
        classmethod(write_fake_pdf),
    )

    result = await service.convert_to_pdf("docx_123", str(output_pdf))

    assert result == {
        "success": True,
        "doc_id": "docx_123",
        "output_path": str(output_pdf),
        "mode": "fidelity",
    }
    service.save_docx.assert_awaited_once()


@pytest.mark.asyncio
async def test_convert_to_doc_rejects_non_fidelity_mode():
    service = DocxService(repository=MagicMock())

    result = await service.convert_to_doc("docx_123", mode="content")

    assert result["success"] is False
    assert "fidelity mode only" in result["error"]


@pytest.mark.asyncio
async def test_convert_to_doc_success(monkeypatch, tmp_path: Path):
    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path
    (tmp_path / "ir.json").write_text("{}", encoding="utf-8")

    service = DocxService(repository=repository)
    service.get_dfm = AsyncMock(return_value="# title")
    service.save_docx = AsyncMock(
        return_value={"success": True, "output_path": str(tmp_path / "tmp.docx")}
    )

    output_doc = tmp_path / "result.doc"

    def write_fake_doc(cls, docx_path, output_path):
        output_path.write_bytes(b"DOC fake")
        return output_path

    monkeypatch.setattr(
        DocxService,
        "_convert_docx_file_to_doc",
        classmethod(write_fake_doc),
    )

    result = await service.convert_to_doc("docx_123", str(output_doc))

    assert result == {
        "success": True,
        "doc_id": "docx_123",
        "output_path": str(output_doc),
        "mode": "fidelity",
    }
    service.save_docx.assert_awaited_once()


def test_detect_unedited_block_mutations():
    repository = MagicMock()
    service = DocxService(repository=repository)

    original_ir = DocxIR(
        doc_id="docx_123",
        source_path="/workspace/original.docx",
        blocks=[
            DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="A"),
            DfmBlock(id="p002", block_type=DfmBlockType.PARAGRAPH, content="B"),
        ],
    )
    updated_ir = DocxIR(
        doc_id="docx_123",
        source_path="/workspace/original.docx",
        blocks=[
            DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="A2"),
            DfmBlock(id="p002", block_type=DfmBlockType.PARAGRAPH, content="BROKEN"),
        ],
    )

    issues = service._detect_unedited_block_mutations(
        original_ir,
        updated_ir,
        {"p001"},
    )

    assert issues == ["Block p002 changed without an explicit edit request"]


@pytest.mark.asyncio
async def test_save_docx_fails_when_unedited_block_changes(monkeypatch, tmp_path: Path):
    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path

    service = DocxService(repository=repository)
    ir = DocxIR(
        doc_id="docx_123",
        source_path="/workspace/original.docx",
        blocks=[
            DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="Before"),
            DfmBlock(id="p002", block_type=DfmBlockType.PARAGRAPH, content="Safe"),
        ],
    )
    parse_result = DfmParseResult(
        doc_id="docx_123",
        source="demo.docx",
        checksum="",
        edits=[BlockEdit(block_id="p001", new_content="After")],
    )

    monkeypatch.setattr(service, "_load_ir", lambda doc_id: ir)
    monkeypatch.setattr(service.parser, "parse", lambda dfm_text: parse_result)
    monkeypatch.setattr(
        service.integrity,
        "check_pre_save",
        lambda ir, parse_result: IntegrityReport(),
    )

    def mutate_unedited(ir_obj, parsed):
        ir_obj.find_block("p001").content = "After"
        ir_obj.find_block("p002").content = "Corrupted"
        return ir_obj

    monkeypatch.setattr(service.parser, "apply_edits", mutate_unedited)

    result = await service.save_docx("docx_123", "dummy")

    assert result["success"] is False
    assert "Unexpected changes detected in unedited blocks" in result["error"]
    assert any("p002" in warning for warning in result["warnings"])


def test_detect_content_drift_ignores_table_padding_only_changes():
    old_md = "\n".join(
        [
            "| Name     | Score |",
            "| -------- | ----- |",
            "| Alice    | 10    |",
            "| Bob      | 9     |",
        ]
    )
    new_md = "\n".join(
        [
            "| Name | Score |",
            "| --- | --- |",
            "| Alice | 10 |",
            "| Bob | 9 |",
        ]
    )

    assert DocxService._detect_content_drift(old_md, new_md) == []


@pytest.mark.asyncio
async def test_save_docx_does_not_overwrite_artifacts_when_post_save_fails(
    monkeypatch,
    tmp_path: Path,
):
    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path

    (tmp_path / "original.docx").write_bytes(b"original")
    output = tmp_path / "output.docx"
    output.write_bytes(b"previous-output")
    (tmp_path / "content.md").write_text("Before line\n", encoding="utf-8")
    (tmp_path / "content.dfm").write_text("Before DFM\n", encoding="utf-8")
    (tmp_path / "format.yaml").write_text("blocks: {}\n", encoding="utf-8")
    (tmp_path / "ir.json").write_text("{}", encoding="utf-8")

    service = DocxService(repository=repository)
    ir = DocxIR(
        doc_id="docx_123",
        source_path=str(tmp_path / "original.docx"),
        blocks=[
            DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="Before")
        ],
    )
    parse_result = DfmParseResult(
        doc_id="docx_123",
        source="demo.docx",
        checksum="",
        edits=[BlockEdit(block_id="p001", new_content="After")],
    )
    post_report = IntegrityReport()
    post_report.add(
        IntegrityIssue(
            severity="error",
            stage="post_save",
            message="Round-trip fidelity: 10.0% (degraded)",
        )
    )
    backup_mock = MagicMock()

    monkeypatch.setattr(service, "_load_ir", lambda doc_id: ir)
    monkeypatch.setattr(service.parser, "parse", lambda dfm_text: parse_result)
    monkeypatch.setattr(
        service.integrity,
        "check_pre_save",
        lambda ir, parse_result: IntegrityReport(),
    )
    monkeypatch.setattr(
        service.integrity,
        "check_post_save",
        lambda original_path, result_path: post_report,
    )
    monkeypatch.setattr(service, "_backup_before_overwrite", backup_mock)
    monkeypatch.setattr(service.renderer, "render", lambda ir_obj: "After DFM\n")
    monkeypatch.setattr(
        service.renderer,
        "render_split",
        lambda ir_obj: ("After line\n", "blocks: {}\n"),
    )

    def apply_edits(ir_obj, parsed):
        ir_obj.find_block("p001").content = "After"
        return ir_obj

    def write_staged_docx(ir_obj, doc_dir, output_path, **kwargs):
        output_path.write_bytes(b"corrupted-output")
        return output_path

    monkeypatch.setattr(service.parser, "apply_edits", apply_edits)
    monkeypatch.setattr(service.adapter, "ir_to_docx", write_staged_docx)

    result = await service.save_docx("docx_123", "dummy", str(output))

    assert result["success"] is False
    assert "Post-save integrity check failed" in result["error"]
    assert output.read_bytes() == b"previous-output"
    assert (tmp_path / "content.md").read_text(encoding="utf-8") == "Before line\n"
    assert not list(tmp_path.glob(".*.tmp.docx"))
    backup_mock.assert_not_called()
