from pathlib import Path

from lxml import etree

from src.domain.docx_entities import DfmBlock, DocxIR
from src.domain.docx_value_objects import DfmBlockType
from src.infrastructure.docx_adapter import DocxAdapter

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _w(name: str) -> str:
    return f"{{{NS_W}}}{name}"


def _p(*runs: str) -> etree._Element:
    paragraph = etree.Element(_w("p"))
    for text in runs:
        run = etree.SubElement(paragraph, _w("r"))
        text_elem = etree.SubElement(run, _w("t"))
        text_elem.text = text
    return paragraph


def _tc(
    paragraphs: list[tuple[str, ...]],
    *,
    grid_span: int | None = None,
    v_merge: str | None = None,
) -> etree._Element:
    cell = etree.Element(_w("tc"))
    if grid_span is not None or v_merge is not None:
        tc_pr = etree.SubElement(cell, _w("tcPr"))
        if grid_span is not None:
            etree.SubElement(tc_pr, _w("gridSpan"), {_w("val"): str(grid_span)})
        if v_merge is not None:
            attrs = {_w("val"): v_merge} if v_merge else {}
            etree.SubElement(tc_pr, _w("vMerge"), attrs)
    for paragraph_runs in paragraphs:
        cell.append(_p(*paragraph_runs))
    return cell


def _table_with_horizontal_merge() -> etree._Element:
    table = etree.Element(_w("tbl"))
    grid = etree.SubElement(table, _w("tblGrid"))
    for _ in range(3):
        etree.SubElement(grid, _w("gridCol"), {_w("w"): "1200"})

    first_row = etree.SubElement(table, _w("tr"))
    first_row.append(_tc([("Group",)], grid_span=2))
    first_row.append(_tc([("Tail",)]))

    second_row = etree.SubElement(table, _w("tr"))
    second_row.append(_tc([("A",)]))
    second_row.append(_tc([("B",)]))
    second_row.append(_tc([("C",)]))
    return table


def _cell_paragraph_texts(cell: etree._Element) -> list[list[str]]:
    return [
        [text.text or "" for text in paragraph.findall(f".//{_w('t')}")]
        for paragraph in cell.findall(_w("p"))
    ]


def test_merged_table_parse_preserves_logical_columns(tmp_path: Path):
    adapter = DocxAdapter()
    table = _table_with_horizontal_merge()
    ir = DocxIR(doc_id="docx_123", source_path="source.docx")
    assets_dir = tmp_path / "assets"
    parts_dir = tmp_path / "parts"
    assets_dir.mkdir()
    parts_dir.mkdir()

    block, nested_blocks = adapter._build_table_block(
        table,
        ir,
        {},
        assets_dir,
        parts_dir,
    )

    rows = adapter._parse_md_table(block.content)
    assert nested_blocks == []
    assert rows == [["Group", "", "Tail"], ["A", "B", "C"]]
    assert [cell.to_dict() for cell in block.merged_cells] == [
        {"row": 0, "col": 0, "row_span": 1, "col_span": 2}
    ]


def test_merged_table_edit_updates_correct_logical_cell():
    adapter = DocxAdapter()
    table = _table_with_horizontal_merge()
    block = DfmBlock(
        id="t001",
        block_type=DfmBlockType.TABLE,
        content="\n".join(
            [
                "| Group |  | Tail edited |",
                "| --- | --- | --- |",
                "| A | B | C |",
            ]
        ),
    )

    adapter._update_table_text(table, block, {}, {"t001"})

    first_row_cells = table.findall(_w("tr"))[0].findall(_w("tc"))
    assert _cell_paragraph_texts(first_row_cells[0]) == [["Group"]]
    assert _cell_paragraph_texts(first_row_cells[1]) == [["Tail edited"]]


def test_table_writeback_preserves_unchanged_multi_paragraph_cell_runs():
    adapter = DocxAdapter()
    table = etree.Element(_w("tbl"))

    header_row = etree.SubElement(table, _w("tr"))
    header_row.append(_tc([("Key",)]))
    header_row.append(_tc([("Value",)]))

    data_row = etree.SubElement(table, _w("tr"))
    data_row.append(_tc([("Item",)]))
    data_row.append(_tc([("Line", " 1"), ("Line 2",)]))

    block = DfmBlock(
        id="t001",
        block_type=DfmBlockType.TABLE,
        content="\n".join(
            [
                "| Key | Value |",
                "| --- | --- |",
                "| Item | Line 1<br>Line 2 |",
            ]
        ),
    )

    adapter._update_table_text(table, block, {}, {"t001"})

    value_cell = table.findall(_w("tr"))[1].findall(_w("tc"))[1]
    assert _cell_paragraph_texts(value_cell) == [["Line", " 1"], ["Line 2"]]
