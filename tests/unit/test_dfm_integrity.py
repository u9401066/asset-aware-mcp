from src.application.dfm_integrity import DfmIntegrityChecker
from src.domain.docx_entities import DfmBlock, DocxIR
from src.domain.docx_value_objects import DfmBlockType
from src.infrastructure.dfm_parser import BlockEdit, DfmParseResult
from src.infrastructure.docx_validator import (
    FormatDiff,
    MediaDiff,
    StructureDiff,
    TextDiff,
    ValidationReport,
)


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


def test_check_post_save_allows_expected_content_diffs(monkeypatch, tmp_path):
    original_path = tmp_path / "original.docx"
    output_path = tmp_path / "output.docx"
    original_path.write_bytes(b"original")
    output_path.write_bytes(b"output")

    validation = ValidationReport(
        fidelity_score=0.575,
        structure_score=1.0,
        text_score=0.0,
        format_score=1.0,
        table_score=0.5,
        media_score=1.0,
        style_score=1.0,
    )
    validation.text_diffs.append(
        TextDiff(index=0, location="paragraph 1", original="Before", rebuilt="After")
    )
    validation.table_diffs.append(
        TextDiff(
            index=0,
            location="table 1/row 1/col 1",
            original="Old",
            rebuilt="New",
        )
    )

    class FakeValidator:
        def validate(self, original, rebuilt):
            return validation

    monkeypatch.setattr(
        "src.infrastructure.docx_validator.DocxValidator",
        lambda: FakeValidator(),
    )

    report = DfmIntegrityChecker().check_post_save(
        original_path,
        output_path,
        content_edits_expected=True,
        expected_text_diffs=1,
        expected_table_diffs=1,
        expected_text_diff_locations={"paragraph 1"},
        expected_table_diff_locations={"table 1/row 1/col 1"},
    )

    assert report.passed is True
    assert report.error_count == 0
    assert report.issues[0].severity == "info"
    assert report.issues[0].details["text_diffs"] == 1
    assert report.issues[0].details["table_diffs"] == 1


def test_check_post_save_requires_expected_content_diffs_to_appear(
    monkeypatch, tmp_path
):
    original_path = tmp_path / "original.docx"
    output_path = tmp_path / "output.docx"
    original_path.write_bytes(b"original")
    output_path.write_bytes(b"output")

    validation = ValidationReport(
        fidelity_score=1.0,
        structure_score=1.0,
        text_score=1.0,
        format_score=1.0,
        table_score=1.0,
        media_score=1.0,
        style_score=1.0,
    )

    class FakeValidator:
        def validate(self, original, rebuilt):
            return validation

    monkeypatch.setattr(
        "src.infrastructure.docx_validator.DocxValidator",
        lambda: FakeValidator(),
    )

    report = DfmIntegrityChecker().check_post_save(
        original_path,
        output_path,
        content_edits_expected=True,
        expected_text_diff_locations={"paragraph 1"},
        expected_table_diff_locations={"table 1/row 1/col 1"},
    )

    assert report.passed is False
    assert report.error_count == 1
    assert report.issues[0].details["missing_text_diffs"] == 1
    assert report.issues[0].details["missing_table_diffs"] == 1


def test_check_post_save_fails_closed_when_content_edits_have_no_scope(
    monkeypatch, tmp_path
):
    original_path = tmp_path / "original.docx"
    output_path = tmp_path / "output.docx"
    original_path.write_bytes(b"original")
    output_path.write_bytes(b"output")

    validation = ValidationReport(
        fidelity_score=0.5,
        structure_score=1.0,
        text_score=0.0,
        format_score=1.0,
        table_score=1.0,
        media_score=1.0,
        style_score=1.0,
    )
    validation.text_diffs.append(
        TextDiff(index=0, location="paragraph 1", original="Before", rebuilt="After")
    )

    class FakeValidator:
        def validate(self, original, rebuilt):
            return validation

    monkeypatch.setattr(
        "src.infrastructure.docx_validator.DocxValidator",
        lambda: FakeValidator(),
    )

    report = DfmIntegrityChecker().check_post_save(
        original_path,
        output_path,
        content_edits_expected=True,
    )

    assert report.passed is False
    assert report.error_count == 1
    assert report.issues[0].details["text_diffs"] == 1


def test_check_post_save_blocks_unexpected_extra_text_diffs(monkeypatch, tmp_path):
    original_path = tmp_path / "original.docx"
    output_path = tmp_path / "output.docx"
    original_path.write_bytes(b"original")
    output_path.write_bytes(b"output")

    validation = ValidationReport(
        fidelity_score=0.5,
        structure_score=1.0,
        text_score=0.0,
        format_score=1.0,
        table_score=1.0,
        media_score=1.0,
        style_score=1.0,
    )
    validation.text_diffs.extend(
        [
            TextDiff(
                index=0,
                location="paragraph 1",
                original="Expected before",
                rebuilt="Expected after",
            ),
            TextDiff(
                index=1,
                location="paragraph 2",
                original="Unexpected before",
                rebuilt="Unexpected after",
            ),
        ]
    )

    class FakeValidator:
        def validate(self, original, rebuilt):
            return validation

    monkeypatch.setattr(
        "src.infrastructure.docx_validator.DocxValidator",
        lambda: FakeValidator(),
    )

    report = DfmIntegrityChecker().check_post_save(
        original_path,
        output_path,
        content_edits_expected=True,
        expected_text_diffs=1,
        expected_table_diffs=0,
        expected_text_diff_locations={"paragraph 1"},
        expected_table_diff_locations=set(),
    )

    assert report.passed is False
    assert report.error_count == 1
    assert report.issues[0].details["text_diffs"] == 1


def test_check_post_save_blocks_unexpected_extra_table_diffs(monkeypatch, tmp_path):
    original_path = tmp_path / "original.docx"
    output_path = tmp_path / "output.docx"
    original_path.write_bytes(b"original")
    output_path.write_bytes(b"output")

    validation = ValidationReport(
        fidelity_score=0.5,
        structure_score=1.0,
        text_score=1.0,
        format_score=1.0,
        table_score=0.0,
        media_score=1.0,
        style_score=1.0,
    )
    validation.table_diffs.extend(
        [
            TextDiff(
                index=0,
                location="table 1/row 1/col 1",
                original="Expected before",
                rebuilt="Expected after",
            ),
            TextDiff(
                index=0,
                location="table 1/row 2/col 1",
                original="Unexpected before",
                rebuilt="Unexpected after",
            ),
        ]
    )

    class FakeValidator:
        def validate(self, original, rebuilt):
            return validation

    monkeypatch.setattr(
        "src.infrastructure.docx_validator.DocxValidator",
        lambda: FakeValidator(),
    )

    report = DfmIntegrityChecker().check_post_save(
        original_path,
        output_path,
        content_edits_expected=True,
        expected_text_diffs=0,
        expected_table_diffs=1,
        expected_text_diff_locations=set(),
        expected_table_diff_locations={"table 1/row 1/col 1"},
    )

    assert report.passed is False
    assert report.error_count == 1
    assert report.issues[0].details["table_diffs"] == 1


def test_check_post_save_still_blocks_structural_regression_for_content_edits(
    monkeypatch, tmp_path
):
    original_path = tmp_path / "original.docx"
    output_path = tmp_path / "output.docx"
    original_path.write_bytes(b"original")
    output_path.write_bytes(b"output")

    validation = ValidationReport(
        fidelity_score=0.7,
        structure_score=0.8,
        text_score=1.0,
        format_score=1.0,
        table_score=1.0,
        media_score=1.0,
        style_score=1.0,
    )
    validation.structure_diffs.append(
        StructureDiff(category="tables", original_count=1, rebuilt_count=0)
    )

    class FakeValidator:
        def validate(self, original, rebuilt):
            return validation

    monkeypatch.setattr(
        "src.infrastructure.docx_validator.DocxValidator",
        lambda: FakeValidator(),
    )

    report = DfmIntegrityChecker().check_post_save(
        original_path,
        output_path,
        content_edits_expected=True,
        expected_text_diffs=0,
        expected_table_diffs=0,
        expected_text_diff_locations=set(),
        expected_table_diff_locations=set(),
    )

    assert report.passed is False
    assert report.error_count == 1
    assert "non-content fidelity degraded" in report.issues[0].message


def test_check_post_save_allows_revision_markup_format_diffs(monkeypatch, tmp_path):
    original_path = tmp_path / "original.docx"
    output_path = tmp_path / "output.docx"
    original_path.write_bytes(b"original")
    output_path.write_bytes(b"output")

    validation = ValidationReport(
        fidelity_score=0.425,
        structure_score=1.0,
        text_score=0.0,
        format_score=0.0,
        table_score=0.5,
        media_score=1.0,
        style_score=1.0,
    )
    validation.text_diffs.append(
        TextDiff(index=0, location="paragraph 1", original="Before", rebuilt="After")
    )
    validation.table_diffs.append(
        TextDiff(
            index=0,
            location="table 1/row 1/col 1",
            original="Old",
            rebuilt="New",
        )
    )
    validation.format_diffs.append(
        FormatDiff(
            index=0,
            location="paragraph 1",
            attribute="run_count",
            original="1",
            rebuilt="2",
        )
    )
    validation.format_diffs.append(
        FormatDiff(
            index=1,
            location="table 1/row 1/col 1",
            attribute="run_count",
            original="1",
            rebuilt="2",
        )
    )

    class FakeValidator:
        def validate(self, original, rebuilt):
            return validation

    monkeypatch.setattr(
        "src.infrastructure.docx_validator.DocxValidator",
        lambda: FakeValidator(),
    )

    report = DfmIntegrityChecker().check_post_save(
        original_path,
        output_path,
        content_edits_expected=True,
        revision_markup_expected=True,
        expected_text_diffs=1,
        expected_table_diffs=1,
        expected_text_diff_locations={"paragraph 1"},
        expected_table_diff_locations={"table 1/row 1/col 1"},
    )

    assert report.passed is True
    assert report.error_count == 0
    assert report.issues[0].details["format_diffs"] == 2


def test_check_post_save_blocks_run_count_diff_outside_expected_text_scope(
    monkeypatch, tmp_path
):
    original_path = tmp_path / "original.docx"
    output_path = tmp_path / "output.docx"
    original_path.write_bytes(b"original")
    output_path.write_bytes(b"output")

    validation = ValidationReport(
        fidelity_score=0.8,
        structure_score=1.0,
        text_score=0.0,
        format_score=0.0,
        table_score=1.0,
        media_score=1.0,
        style_score=1.0,
    )
    validation.text_diffs.append(
        TextDiff(index=0, location="paragraph 1", original="Before", rebuilt="After")
    )
    validation.format_diffs.append(
        FormatDiff(
            index=1,
            location="paragraph 2",
            attribute="run_count",
            original="1",
            rebuilt="2",
        )
    )

    class FakeValidator:
        def validate(self, original, rebuilt):
            return validation

    monkeypatch.setattr(
        "src.infrastructure.docx_validator.DocxValidator",
        lambda: FakeValidator(),
    )

    report = DfmIntegrityChecker().check_post_save(
        original_path,
        output_path,
        content_edits_expected=True,
        revision_markup_expected=True,
        expected_text_diffs=1,
        expected_table_diffs=0,
        expected_text_diff_locations={"paragraph 1"},
        expected_table_diff_locations=set(),
    )

    assert report.passed is False
    assert report.error_count == 1
    assert report.issues[0].details["format_diffs"] == 1


def test_check_post_save_blocks_non_revision_format_regression_with_revision_markup(
    monkeypatch, tmp_path
):
    original_path = tmp_path / "original.docx"
    output_path = tmp_path / "output.docx"
    original_path.write_bytes(b"original")
    output_path.write_bytes(b"output")

    validation = ValidationReport(
        fidelity_score=0.8,
        structure_score=1.0,
        text_score=1.0,
        format_score=0.0,
        table_score=1.0,
        media_score=1.0,
        style_score=1.0,
    )
    validation.format_diffs.append(
        FormatDiff(
            index=0,
            location="paragraph 1/run 1",
            attribute="bold",
            original="True",
            rebuilt="False",
        )
    )

    class FakeValidator:
        def validate(self, original, rebuilt):
            return validation

    monkeypatch.setattr(
        "src.infrastructure.docx_validator.DocxValidator",
        lambda: FakeValidator(),
    )

    report = DfmIntegrityChecker().check_post_save(
        original_path,
        output_path,
        content_edits_expected=True,
        revision_markup_expected=True,
        expected_text_diffs=0,
        expected_table_diffs=0,
        expected_text_diff_locations=set(),
        expected_table_diff_locations=set(),
    )

    assert report.passed is False
    assert report.error_count == 1
    assert report.issues[0].details["format_diffs"] == 1


def test_check_post_save_blocks_format_regression_without_revision_markup(
    monkeypatch, tmp_path
):
    original_path = tmp_path / "original.docx"
    output_path = tmp_path / "output.docx"
    original_path.write_bytes(b"original")
    output_path.write_bytes(b"output")

    validation = ValidationReport(
        fidelity_score=0.8,
        structure_score=1.0,
        text_score=1.0,
        format_score=0.0,
        table_score=1.0,
        media_score=1.0,
        style_score=1.0,
    )
    validation.format_diffs.append(
        FormatDiff(
            index=0,
            location="paragraph 1",
            attribute="bold",
            original="True",
            rebuilt="False",
        )
    )

    class FakeValidator:
        def validate(self, original, rebuilt):
            return validation

    monkeypatch.setattr(
        "src.infrastructure.docx_validator.DocxValidator",
        lambda: FakeValidator(),
    )

    report = DfmIntegrityChecker().check_post_save(
        original_path,
        output_path,
        content_edits_expected=True,
        expected_text_diffs=0,
        expected_table_diffs=0,
        expected_text_diff_locations=set(),
        expected_table_diff_locations=set(),
    )

    assert report.passed is False
    assert report.error_count == 1


def test_check_post_save_blocks_media_and_style_regressions_for_content_edits(
    monkeypatch, tmp_path
):
    original_path = tmp_path / "original.docx"
    output_path = tmp_path / "output.docx"
    original_path.write_bytes(b"original")
    output_path.write_bytes(b"output")

    validation = ValidationReport(
        fidelity_score=0.8,
        structure_score=1.0,
        text_score=1.0,
        format_score=1.0,
        table_score=1.0,
        media_score=0.0,
        style_score=0.0,
    )
    validation.media_diffs.append(
        MediaDiff(filename="word/media/image1.png", status="missing")
    )
    validation.style_diffs.append(
        TextDiff(index=0, location="style Heading 1", original="blue", rebuilt="red")
    )

    class FakeValidator:
        def validate(self, original, rebuilt):
            return validation

    monkeypatch.setattr(
        "src.infrastructure.docx_validator.DocxValidator",
        lambda: FakeValidator(),
    )

    report = DfmIntegrityChecker().check_post_save(
        original_path,
        output_path,
        content_edits_expected=True,
        expected_text_diffs=0,
        expected_table_diffs=0,
        expected_text_diff_locations=set(),
        expected_table_diff_locations=set(),
    )

    assert report.passed is False
    assert report.error_count == 1
    assert report.issues[0].details["media_diffs"] == 1
    assert report.issues[0].details["style_diffs"] == 1
