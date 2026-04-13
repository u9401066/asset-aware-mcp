from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dfm_integrity import IntegrityReport
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
    monkeypatch.setattr(
        DocxService,
        "_convert_docx_file_to_pdf",
        classmethod(lambda cls, docx_path, output_path: (output_path.write_bytes(b"%PDF-1.4\n"), output_path)[1]),
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
    monkeypatch.setattr(
        DocxService,
        "_convert_docx_file_to_doc",
        classmethod(lambda cls, docx_path, output_path: (output_path.write_bytes(b"fake-doc"), output_path)[1]),
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


def test_detect_content_drift_ignores_table_padding_only_changes():
    old_md = (
        "---\n"
        "doc_id: docx_123\n"
        "---\n\n"
        "<!-- @t001 -->\n"
        "| Very long heading                 | col_1      |\n"
        "| --------------------------------- | ---------- |\n"
        "| Item                              | Old value  |\n"
    )
    new_md = (
        "---\n"
        "doc_id: docx_123\n"
        "---\n\n"
        "<!-- @t001 -->\n"
        "| Very long heading | col_1 |\n"
        "| --- | --- |\n"
        "| Item | Old value |\n"
    )

    issues = DocxService._detect_content_drift(old_md, new_md)

    assert issues == []


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


@pytest.mark.asyncio
async def test_save_docx_uses_persisted_dfm_when_no_inline_content(
    monkeypatch, tmp_path: Path
):
    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path

    service = DocxService(repository=repository)
    ir = DocxIR(
        doc_id="docx_123",
        source_path="/workspace/original.docx",
        blocks=[
            DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="Before"),
        ],
    )
    (tmp_path / "content.dfm").write_text("persisted dfm", encoding="utf-8")
    (tmp_path / "original.docx").write_bytes(b"docx")

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
    monkeypatch.setattr(service.parser, "apply_edits", lambda ir_obj, parsed: ir_obj)
    monkeypatch.setattr(service, "_expected_changed_block_ids", lambda *_args: set())
    monkeypatch.setattr(
        service,
        "_detect_unedited_block_mutations",
        lambda *_args: [],
    )
    monkeypatch.setattr(
        service.adapter,
        "ir_to_docx",
        lambda ir_obj, doc_dir, out: (out.write_bytes(b"docx"), out)[1],
    )
    monkeypatch.setattr(service, "_save_ir", lambda *_args: None)
    monkeypatch.setattr(service, "_backup_before_overwrite", lambda *_args: None)
    monkeypatch.setattr(service.renderer, "render", lambda ir_obj: "updated dfm")
    monkeypatch.setattr(
        service.renderer,
        "render_split",
        lambda ir_obj: ("updated md", "updated yaml"),
    )
    monkeypatch.setattr(service, "_detect_content_drift", lambda *_args: [])
    monkeypatch.setattr(
        service.integrity,
        "check_post_save",
        lambda *_args: IntegrityReport(),
    )

    result = await service.save_docx("docx_123")

    assert result["success"] is True


@pytest.mark.asyncio
async def test_save_docx_does_not_overwrite_artifacts_when_shrinkage_detected(
    monkeypatch, tmp_path: Path
):
    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path

    service = DocxService(repository=repository)
    ir = DocxIR(
        doc_id="docx_123",
        source_path="/workspace/original.docx",
        blocks=[
            DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="Before"),
        ],
    )

    original_md = (
        "---\n"
        "doc_id: docx_123\n"
        "---\n\n"
        "<!-- @p001 -->\n"
        + ("Long original content " * 8)
        + "\n"
    )
    original_dfm = "original dfm"
    original_yaml = "doc_id: docx_123\nblocks: {}\n"
    original_ir_text = "{\"doc_id\": \"docx_123\"}"

    (tmp_path / "content.md").write_text(original_md, encoding="utf-8")
    (tmp_path / "content.dfm").write_text(original_dfm, encoding="utf-8")
    (tmp_path / "format.yaml").write_text(original_yaml, encoding="utf-8")
    (tmp_path / "ir.json").write_text(original_ir_text, encoding="utf-8")
    (tmp_path / "original.docx").write_bytes(b"docx")

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
        lambda ir_obj, parsed: IntegrityReport(),
    )

    def apply_edit(ir_obj, parsed):
        ir_obj.find_block("p001").content = "After"
        return ir_obj

    monkeypatch.setattr(service.parser, "apply_edits", apply_edit)
    monkeypatch.setattr(
        service,
        "_expected_changed_block_ids",
        lambda *_args: {"p001"},
    )
    monkeypatch.setattr(
        service,
        "_detect_unedited_block_mutations",
        lambda *_args: [],
    )

    def stage_docx(_ir_obj, _doc_dir, out_path):
        out_path.write_bytes(b"docx")
        return out_path

    monkeypatch.setattr(service.adapter, "ir_to_docx", stage_docx)
    save_ir_mock = MagicMock()
    backup_mock = MagicMock()
    monkeypatch.setattr(service, "_save_ir", save_ir_mock)
    monkeypatch.setattr(service, "_backup_before_overwrite", backup_mock)
    monkeypatch.setattr(service.renderer, "render", lambda ir_obj: "updated dfm")
    monkeypatch.setattr(
        service.renderer,
        "render_split",
        lambda ir_obj: ("tiny", "updated yaml"),
    )
    monkeypatch.setattr(
        service.integrity,
        "check_post_save",
        lambda *_args: IntegrityReport(),
    )

    output_path = tmp_path / "output.docx"
    result = await service.save_docx("docx_123", "dummy", str(output_path))

    assert result["success"] is False
    assert "Content shrunk by" in result["error"]
    assert (tmp_path / "content.md").read_text(encoding="utf-8") == original_md
    assert (tmp_path / "content.dfm").read_text(encoding="utf-8") == original_dfm
    assert (tmp_path / "format.yaml").read_text(encoding="utf-8") == original_yaml
    assert (tmp_path / "ir.json").read_text(encoding="utf-8") == original_ir_text
    assert not output_path.exists()
    save_ir_mock.assert_not_called()
    backup_mock.assert_not_called()


@pytest.mark.asyncio
async def test_save_docx_does_not_fail_on_table_padding_normalization(
    monkeypatch, tmp_path: Path
):
    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path

    service = DocxService(repository=repository)
    ir = DocxIR(
        doc_id="docx_123",
        source_path="/workspace/original.docx",
        blocks=[
            DfmBlock(
                id="t001",
                block_type=DfmBlockType.TABLE,
                content="| Very long heading | col_1 |\n| --- | --- |\n| Item | Old value |",
            ),
        ],
    )

    padded_md = (
        "---\n"
        "doc_id: docx_123\n"
        "---\n\n"
        "<!-- @t001 -->\n"
        "| Very long heading                 | col_1      |\n"
        "| --------------------------------- | ---------- |\n"
        "| Item                              | Old value  |\n"
    )

    (tmp_path / "content.md").write_text(padded_md, encoding="utf-8")
    (tmp_path / "content.dfm").write_text("persisted dfm", encoding="utf-8")
    (tmp_path / "format.yaml").write_text("doc_id: docx_123\nblocks: {}\n", encoding="utf-8")
    (tmp_path / "ir.json").write_text('{"doc_id": "docx_123"}', encoding="utf-8")
    (tmp_path / "original.docx").write_bytes(b"docx")

    parse_result = DfmParseResult(doc_id="docx_123", source="demo.docx", checksum="", edits=[])

    monkeypatch.setattr(service, "_load_ir", lambda _doc_id: ir)
    monkeypatch.setattr(service.parser, "parse", lambda _dfm_text: parse_result)
    monkeypatch.setattr(
        service.integrity,
        "check_pre_save",
        lambda _ir_obj, _parsed: IntegrityReport(),
    )
    monkeypatch.setattr(service.parser, "apply_edits", lambda ir_obj, _parsed: ir_obj)
    monkeypatch.setattr(service, "_expected_changed_block_ids", lambda *_args: set())
    monkeypatch.setattr(service, "_detect_unedited_block_mutations", lambda *_args: [])
    monkeypatch.setattr(
        service.adapter,
        "ir_to_docx",
        lambda _ir_obj, _doc_dir, out: (out.write_bytes(b"docx"), out)[1],
    )
    monkeypatch.setattr(service, "_save_ir", lambda *_args: None)
    monkeypatch.setattr(service, "_backup_before_overwrite", lambda *_args: None)
    monkeypatch.setattr(service.renderer, "render", lambda _ir_obj: "updated dfm")
    monkeypatch.setattr(
        service.renderer,
        "render_split",
        lambda _ir_obj: (
            "---\ndoc_id: docx_123\n---\n\n<!-- @t001 -->\n| Very long heading | col_1 |\n| --- | --- |\n| Item | Old value |\n",
            "doc_id: docx_123\nblocks: {}\n",
        ),
    )
    monkeypatch.setattr(
        service.integrity,
        "check_post_save",
        lambda *_args: IntegrityReport(),
    )

    result = await service.save_docx("docx_123", "dummy", str(tmp_path / "output.docx"))

    assert result["success"] is True


@pytest.mark.asyncio
async def test_save_docx_from_md_normalizes_multilingual_split_files(
    monkeypatch, tmp_path: Path
):
    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path

    service = DocxService(repository=repository)
    ir = DocxIR(
        doc_id="docx_123",
        source_path="/workspace/original.docx",
        blocks=[
            DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="原始內容"),
        ],
    )
    (tmp_path / "content.md").write_bytes(
        b"\xef\xbb\xbf"
        b"---\r\n"
        b"doc_id: docx_123\r\n"
        b"---\r\n\r\n"
        b"<!-- @p001 -->\r\n"
        + "病歷摘要：王小明 / 山田太郎 / 홍길동\r\n".encode()
    )
    (tmp_path / "format.yaml").write_bytes(
        b"\xef\xbb\xbf"
        b"doc_id: docx_123\r\n"
        b"source: demo.docx\r\n"
        b"checksum: abc123\r\n"
        b"blocks:\r\n"
        b"  p001:\r\n"
        b"    type: paragraph\r\n"
    )
    (tmp_path / "original.docx").write_bytes(b"docx")

    captured: dict[str, str] = {}
    parse_result = DfmParseResult(
        doc_id="docx_123",
        source="demo.docx",
        checksum="abc123",
        edits=[BlockEdit(block_id="p001", new_content="病歷摘要：王小明 / 山田太郎 / 홍길동")],
    )

    monkeypatch.setattr(service, "_load_ir", lambda doc_id: ir)

    def fake_parse_split(md_content: str, yaml_content: str) -> DfmParseResult:
        captured["md_content"] = md_content
        captured["yaml_content"] = yaml_content
        return parse_result

    monkeypatch.setattr(service.parser, "parse_split", fake_parse_split)
    monkeypatch.setattr(
        service.integrity,
        "check_pre_save",
        lambda ir_obj, parsed: IntegrityReport(),
    )
    monkeypatch.setattr(service.parser, "apply_edits", lambda ir_obj, parsed: ir_obj)
    monkeypatch.setattr(service, "_expected_changed_block_ids", lambda *_args: set())
    monkeypatch.setattr(
        service,
        "_detect_unedited_block_mutations",
        lambda *_args: [],
    )
    monkeypatch.setattr(
        service.adapter,
        "ir_to_docx",
        lambda ir_obj, doc_dir, out: (out.write_bytes(b"docx"), out)[1],
    )
    monkeypatch.setattr(service, "_save_ir", lambda *_args: None)
    monkeypatch.setattr(service, "_backup_before_overwrite", lambda *_args: None)
    monkeypatch.setattr(service.renderer, "render", lambda ir_obj: "\ufeff更新後 DFM\r\n第二行\r\n")
    monkeypatch.setattr(
        service.renderer,
        "render_split",
        lambda ir_obj: (
            "\ufeff# 病歷摘要\r\n\r\n患者：王小明 / 山田太郎 / 홍길동\r\n",
            "\ufeffdoc_id: docx_123\r\nblocks: {}\r\n",
        ),
    )
    monkeypatch.setattr(service, "_detect_content_drift", lambda *_args: [])
    monkeypatch.setattr(
        service.integrity,
        "check_post_save",
        lambda *_args: IntegrityReport(),
    )

    result = await service.save_docx("docx_123", from_md=True)

    assert result["success"] is True
    assert captured["md_content"].startswith("---\n")
    assert "\r" not in captured["md_content"]
    assert captured["yaml_content"].startswith("doc_id: docx_123\n")
    assert "\r" not in captured["yaml_content"]
    assert not (tmp_path / "content.dfm").read_bytes().startswith(b"\xef\xbb\xbf")
    assert (tmp_path / "content.md").read_text(encoding="utf-8") == (
        "# 病歷摘要\n\n患者：王小明 / 山田太郎 / 홍길동\n"
    )
    assert (tmp_path / "format.yaml").read_text(encoding="utf-8") == (
        "doc_id: docx_123\nblocks: {}\n"
    )


@pytest.mark.asyncio
async def test_save_docx_from_md_rejects_mixed_encoded_markdown(
    monkeypatch, tmp_path: Path
):
    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path

    service = DocxService(repository=repository)
    ir = DocxIR(
        doc_id="docx_123",
        source_path="/workspace/original.docx",
        blocks=[
            DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="原始內容"),
        ],
    )
    (tmp_path / "content.md").write_bytes("繁體中文".encode() + "報告".encode("big5"))
    (tmp_path / "format.yaml").write_text(
        "doc_id: docx_123\nsource: demo.docx\nchecksum: abc123\nblocks: {}\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(service, "_load_ir", lambda doc_id: ir)

    result = await service.save_docx("docx_123", from_md=True)

    assert result["success"] is False
    assert "not valid UTF-8" in result["error"]


@pytest.mark.asyncio
async def test_save_docx_from_md_rejects_mixed_encoded_yaml(
    monkeypatch, tmp_path: Path
):
    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path

    service = DocxService(repository=repository)
    ir = DocxIR(
        doc_id="docx_123",
        source_path="/workspace/original.docx",
        blocks=[
            DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="原始內容"),
        ],
    )
    (tmp_path / "content.md").write_text(
        "---\ndoc_id: docx_123\n---\n\n<!-- @p001 -->\n病歷摘要\n",
        encoding="utf-8",
    )
    (tmp_path / "format.yaml").write_bytes(
        b"doc_id: docx_123\nsource: demo.docx\nchecksum: abc123\nblocks:\n" + "報告".encode("big5")
    )

    monkeypatch.setattr(service, "_load_ir", lambda doc_id: ir)

    result = await service.save_docx("docx_123", from_md=True)

    assert result["success"] is False
    assert "not valid UTF-8" in result["error"]
