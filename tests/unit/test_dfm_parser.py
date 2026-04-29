from src.domain.docx_entities import DfmBlock, DocxIR
from src.domain.docx_value_objects import DfmBlockType
from src.infrastructure.dfm_parser import BlockEdit, DfmParser, DfmParseResult


def test_parse_split_skips_protected_blocks():
    parser = DfmParser()
    md_text = """---
doc_id: docx_123
---

<!-- @toc001 -->
> 🔖 *[目錄 — 自動產生]*

<!-- @p001 -->
Editable paragraph
"""
    yaml_text = """doc_id: docx_123
blocks:
  toc001:
    type: toc
  p001:
    type: paragraph
"""

    result = parser.parse_split(md_text, yaml_text)

    assert [edit.block_id for edit in result.edits] == ["p001"]


def test_parse_dfm_skips_protected_compound_blocks():
    parser = DfmParser()
    dfm_text = """---
doc_id: docx_123
source: demo.docx
checksum: abc
---

<!-- dfm:toc @b:toc001 -->
> 🔖 *[目錄 — 自動產生]*
<!-- /dfm:toc -->

<!-- @b:p001 -->
Editable paragraph
"""

    result = parser.parse(dfm_text)

    assert [edit.block_id for edit in result.edits] == ["p001"]


def test_parse_dfm_skips_revision_review_blocks():
    parser = DfmParser()
    dfm_text = """---
doc_id: docx_123
source: demo.docx
checksum: abc
---

<!-- dfm:revision @b:rev001
type: delete
source_tag: w:del
-->
Edited review text should stay read-only
<!-- /dfm:revision -->

<!-- @b:p001 -->
Editable paragraph
"""

    result = parser.parse(dfm_text)

    assert [edit.block_id for edit in result.edits] == ["p001"]


def test_apply_edits_keeps_table_markdown_when_rows_are_semantically_unchanged():
    parser = DfmParser()
    original_table = (
        "| Header A | Header B |\n| -------- | -------- |\n| Value 1  | Value 2  |"
    )
    ir = DocxIR(
        doc_id="docx_123",
        source_path="demo.docx",
        blocks=[
            DfmBlock(
                id="t001",
                block_type=DfmBlockType.TABLE,
                content=original_table,
            )
        ],
    )
    parse_result = DfmParseResult(
        doc_id="docx_123",
        source="demo.docx",
        checksum="abc",
        edits=[
            BlockEdit(
                block_id="t001",
                new_content="",
                block_type=DfmBlockType.TABLE,
                table_rows=[["Header A", "Header B"], ["Value 1", "Value 2"]],
            )
        ],
    )

    updated = parser.apply_edits(ir, parse_result)

    assert updated.find_block("t001").content == original_table
