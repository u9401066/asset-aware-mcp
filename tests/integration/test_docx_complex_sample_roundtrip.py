from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree

from src.application.docx_service import DocxService
from src.infrastructure.docx_validator import DocxValidator
from src.infrastructure.file_storage import FileStorage


def _sample_docx_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return next(repo_root.glob("2.KMUHIRB*.docx"))


@pytest.mark.asyncio
async def test_complex_sample_noop_roundtrip_is_binary_identical(
    temp_dir: Path,
) -> None:
    service = DocxService(repository=FileStorage(base_dir=temp_dir))

    ingest = await service.ingest_docx(str(_sample_docx_path()))

    assert ingest["success"] is True
    assert ingest["block_types"]["table"] == 4

    doc_id = str(ingest["doc_id"])
    ir = service._load_ir(doc_id)
    assert ir is not None

    nested_tables = [
        block
        for block in ir.blocks
        if block.block_type.value == "table" and block.parent_cell
    ]
    assert len(nested_tables) == 2
    assert {block.metadata.get("parent_table_id") for block in nested_tables} == {
        "t002"
    }

    output = temp_dir / "sample-roundtrip.docx"
    save = await service.save_docx(doc_id, output_path=str(output), from_md=True)

    assert save["success"] is True
    report = DocxValidator().validate(
        temp_dir / doc_id / "original.docx",
        output,
        strict=True,
    )
    assert report.binary_identical is True
    assert report.strict_passed is True


@pytest.mark.asyncio
async def test_complex_sample_nested_table_edit_writes_back(temp_dir: Path) -> None:
    service = DocxService(repository=FileStorage(base_dir=temp_dir))

    ingest = await service.ingest_docx(str(_sample_docx_path()))
    assert ingest["success"] is True

    doc_id = str(ingest["doc_id"])
    doc_dir = temp_dir / doc_id
    md_path = doc_dir / "content.md"
    old_value = "\u7b2c5\u6b21"
    new_value = "\u7b2c5\u6b21(\u4fee\u6b63)"

    md_text = md_path.read_text(encoding="utf-8")
    assert old_value in md_text
    md_path.write_text(md_text.replace(old_value, new_value, 1), encoding="utf-8")

    output = temp_dir / "sample-nested-edit.docx"
    save = await service.save_docx(doc_id, output_path=str(output), from_md=True)

    assert save["success"] is True

    with ZipFile(output) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    text_blob = "|".join(t.text for t in root.findall(".//w:t", ns) if t.text)
    assert new_value in text_blob

    report = DocxValidator().validate(doc_dir / "original.docx", output)
    assert report.structure_score == pytest.approx(1.0)
    assert report.media_score == pytest.approx(1.0)
    assert report.style_score == pytest.approx(1.0)
    assert report.table_score < 1.0
    assert report.table_diffs
