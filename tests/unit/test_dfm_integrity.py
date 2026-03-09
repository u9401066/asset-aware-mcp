from src.application.dfm_integrity import DfmIntegrityChecker
from src.domain.docx_entities import DfmBlock, DocxIR
from src.domain.docx_value_objects import DfmBlockType
from src.infrastructure.dfm_parser import BlockEdit, DfmParseResult


def test_check_pre_save_does_not_warn_for_unchanged_protected_block():
    checker = DfmIntegrityChecker()
    ir = DocxIR(
        doc_id="docx_123",
        source_path="/workspace/demo.docx",
        blocks=[
            DfmBlock(
                id="toc001", block_type=DfmBlockType.TOC, content="Table of Contents"
            ),
        ],
    )
    parse_result = DfmParseResult(
        doc_id="docx_123",
        source="demo.docx",
        checksum="",
        edits=[BlockEdit(block_id="toc001", new_content="Table of Contents")],
    )

    report = checker.check_pre_save(ir, parse_result)

    assert report.warning_count == 0


def test_check_pre_save_warns_for_changed_protected_block():
    checker = DfmIntegrityChecker()
    ir = DocxIR(
        doc_id="docx_123",
        source_path="/workspace/demo.docx",
        blocks=[
            DfmBlock(
                id="toc001", block_type=DfmBlockType.TOC, content="Table of Contents"
            ),
        ],
    )
    parse_result = DfmParseResult(
        doc_id="docx_123",
        source="demo.docx",
        checksum="",
        edits=[BlockEdit(block_id="toc001", new_content="Hacked TOC")],
    )

    report = checker.check_pre_save(ir, parse_result)

    assert report.warning_count == 1
    assert "protected block toc001" in report.issues[0].message
