from src.infrastructure.dfm_parser import DfmParser


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