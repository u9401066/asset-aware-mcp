"""
Tests for DocxValidator — docx round-trip fidelity validation.

Tests cover:
1. ValidationReport data structures and rendering
2. DocxValidator comparison logic (all 6 dimensions)
3. Full round-trip: programmatically create .docx → parse → rebuild → validate
4. Edge cases: empty docx, tables only, mixed formatting
"""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree

from src.infrastructure.docx_validator import (
    DocxValidator,
    FormatDiff,
    TextDiff,
    ValidationReport,
    _normalize_text,
)

# ============================================================================
# Helpers: Create minimal .docx files programmatically
# ============================================================================

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"

RELS_TYPE_DOC = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
)
CT_DOC = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
)


def _make_content_types() -> bytes:
    """Create [Content_Types].xml."""
    root = etree.Element(f"{{{NS_CT}}}Types")
    etree.SubElement(
        root,
        f"{{{NS_CT}}}Override",
        PartName="/word/document.xml",
        ContentType=CT_DOC,
    )
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")


def _make_rels() -> bytes:
    """Create _rels/.rels."""
    root = etree.Element(f"{{{NS_REL}}}Relationships")
    etree.SubElement(
        root,
        f"{{{NS_REL}}}Relationship",
        Id="rId1",
        Type=RELS_TYPE_DOC,
        Target="word/document.xml",
    )
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")


def _make_paragraph(
    text: str,
    bold: bool = False,
    italic: bool = False,
    style: str | None = None,
    font_name: str | None = None,
    font_size_half_pt: int | None = None,
    color: str | None = None,
) -> etree._Element:
    """Create a <w:p> element."""
    p = etree.SubElement(etree.Element("dummy"), f"{{{NS_W}}}p")

    # Paragraph properties
    if style:
        ppr = etree.SubElement(p, f"{{{NS_W}}}pPr")
        etree.SubElement(ppr, f"{{{NS_W}}}pStyle", {f"{{{NS_W}}}val": style})

    # Run
    r = etree.SubElement(p, f"{{{NS_W}}}r")

    # Run properties
    if bold or italic or font_name or font_size_half_pt or color:
        rpr = etree.SubElement(r, f"{{{NS_W}}}rPr")
        if bold:
            etree.SubElement(rpr, f"{{{NS_W}}}b")
        if italic:
            etree.SubElement(rpr, f"{{{NS_W}}}i")
        if font_name:
            etree.SubElement(
                rpr,
                f"{{{NS_W}}}rFonts",
                {f"{{{NS_W}}}ascii": font_name, f"{{{NS_W}}}hAnsi": font_name},
            )
        if font_size_half_pt:
            etree.SubElement(
                rpr, f"{{{NS_W}}}sz", {f"{{{NS_W}}}val": str(font_size_half_pt)}
            )
        if color:
            etree.SubElement(rpr, f"{{{NS_W}}}color", {f"{{{NS_W}}}val": color})

    t = etree.SubElement(r, f"{{{NS_W}}}t")
    t.text = text
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

    return p


def _make_runs_paragraph(runs: list[dict[str, object]]) -> etree._Element:
    """Create a paragraph with multiple formatted runs."""
    p = etree.SubElement(etree.Element("dummy"), f"{{{NS_W}}}p")
    for run in runs:
        r = etree.SubElement(p, f"{{{NS_W}}}r")
        rpr = etree.SubElement(r, f"{{{NS_W}}}rPr")
        if run.get("bold"):
            etree.SubElement(rpr, f"{{{NS_W}}}b")
        if run.get("italic"):
            etree.SubElement(rpr, f"{{{NS_W}}}i")
        if run.get("underline"):
            etree.SubElement(rpr, f"{{{NS_W}}}u", {f"{{{NS_W}}}val": "single"})
        if color := run.get("color"):
            etree.SubElement(rpr, f"{{{NS_W}}}color", {f"{{{NS_W}}}val": str(color)})
        if len(rpr) == 0:
            r.remove(rpr)
        t = etree.SubElement(r, f"{{{NS_W}}}t")
        t.text = str(run.get("text", ""))
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return p


def _make_table(rows: list[list[str]], style: str | None = None) -> etree._Element:
    """Create a <w:tbl> element."""
    tbl = etree.SubElement(etree.Element("dummy"), f"{{{NS_W}}}tbl")

    if style:
        tbl_pr = etree.SubElement(tbl, f"{{{NS_W}}}tblPr")
        etree.SubElement(tbl_pr, f"{{{NS_W}}}tblStyle", {f"{{{NS_W}}}val": style})

    for row_data in rows:
        tr = etree.SubElement(tbl, f"{{{NS_W}}}tr")
        for cell_text in row_data:
            tc = etree.SubElement(tr, f"{{{NS_W}}}tc")
            p = etree.SubElement(tc, f"{{{NS_W}}}p")
            r = etree.SubElement(p, f"{{{NS_W}}}r")
            t = etree.SubElement(r, f"{{{NS_W}}}t")
            t.text = cell_text
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

    return tbl


def _make_formatted_table(rows: list[list[list[dict[str, object]]]]) -> etree._Element:
    """Create a table whose cells contain explicitly formatted runs."""
    tbl = etree.SubElement(etree.Element("dummy"), f"{{{NS_W}}}tbl")

    for row_data in rows:
        tr = etree.SubElement(tbl, f"{{{NS_W}}}tr")
        for cell_runs in row_data:
            tc = etree.SubElement(tr, f"{{{NS_W}}}tc")
            tc.append(_make_runs_paragraph(cell_runs))

    return tbl


def _build_document_xml(
    paragraphs: list[etree._Element] | None = None,
    tables: list[etree._Element] | None = None,
    body_elements: list[etree._Element] | None = None,
) -> bytes:
    """Build a complete document.xml from paragraphs and tables."""
    doc = etree.Element(
        f"{{{NS_W}}}document",
        nsmap={"w": NS_W, "r": NS_R},
    )
    body = etree.SubElement(doc, f"{{{NS_W}}}body")

    if body_elements:
        for el in body_elements:
            body.append(el)
    else:
        if paragraphs:
            for p in paragraphs:
                body.append(p)
        if tables:
            for t in tables:
                body.append(t)

    return etree.tostring(doc, xml_declaration=True, encoding="UTF-8")


def _create_docx(
    path: Path,
    paragraphs: list[etree._Element] | None = None,
    tables: list[etree._Element] | None = None,
    body_elements: list[etree._Element] | None = None,
    media: dict[str, bytes] | None = None,
    extra_parts: dict[str, bytes] | None = None,
) -> None:
    """Create a minimal .docx file (zip) with given content."""
    doc_xml = _build_document_xml(paragraphs, tables, body_elements)

    with ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", _make_content_types())
        zf.writestr("_rels/.rels", _make_rels())
        zf.writestr("word/document.xml", doc_xml)

        if media:
            for filename, data in media.items():
                zf.writestr(f"word/media/{filename}", data)
        if extra_parts:
            for filename, data in extra_parts.items():
                zf.writestr(filename, data)


def _build_story_part_xml(root_name: str, paragraphs: list[etree._Element]) -> bytes:
    root = etree.Element(f"{{{NS_W}}}{root_name}", nsmap={"w": NS_W, "r": NS_R})
    for paragraph in paragraphs:
        root.append(paragraph)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")


def _build_footnotes_xml(footnotes: dict[int, list[etree._Element]]) -> bytes:
    root = etree.Element(f"{{{NS_W}}}footnotes", nsmap={"w": NS_W, "r": NS_R})
    for footnote_id, paragraphs in footnotes.items():
        footnote = etree.SubElement(
            root,
            f"{{{NS_W}}}footnote",
            {f"{{{NS_W}}}id": str(footnote_id)},
        )
        for paragraph in paragraphs:
            footnote.append(paragraph)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def validator() -> DocxValidator:
    return DocxValidator()


@pytest.fixture
def tmp_docx_dir(tmp_path: Path) -> Path:
    return tmp_path


# ============================================================================
# Tests: _normalize_text
# ============================================================================


class TestNormalizeText:
    def test_basic(self):
        assert _normalize_text("  hello  world  ") == "hello world"

    def test_newlines(self):
        assert _normalize_text("hello\n\nworld") == "hello world"

    def test_tabs(self):
        assert _normalize_text("hello\tworld") == "hello world"

    def test_empty(self):
        assert _normalize_text("") == ""


# ============================================================================
# Tests: ValidationReport
# ============================================================================


class TestValidationReport:
    def test_to_dict(self):
        report = ValidationReport(
            fidelity_score=0.95,
            structure_score=1.0,
            text_score=0.9,
            format_score=1.0,
            table_score=1.0,
            media_score=1.0,
            style_score=0.8,
        )
        d = report.to_dict()
        assert d["fidelity_score"] == 95.0
        assert d["scores"]["text"] == 90.0
        assert d["scores"]["style"] == 80.0

    def test_to_markdown_excellent(self):
        report = ValidationReport(fidelity_score=0.98)
        md = report.to_markdown()
        assert "EXCELLENT" in md
        assert "98.0%" in md

    def test_to_markdown_poor(self):
        report = ValidationReport(fidelity_score=0.3)
        md = report.to_markdown()
        assert "POOR" in md

    def test_to_markdown_with_diffs(self):
        report = ValidationReport(
            fidelity_score=0.75,
            text_diffs=[
                TextDiff(
                    index=0, location="paragraph 1", original="hello", rebuilt="helo"
                ),
            ],
            format_diffs=[
                FormatDiff(
                    index=0,
                    location="paragraph 1",
                    attribute="bold",
                    original="True",
                    rebuilt="None",
                ),
            ],
        )
        md = report.to_markdown()
        assert "文字差異" in md
        assert "格式差異" in md
        assert "hello" in md
        assert "bold" in md

    def test_to_markdown_grades(self):
        """Test all grade levels."""
        for score, expected in [
            (0.96, "EXCELLENT"),
            (0.85, "GOOD"),
            (0.65, "FAIR"),
            (0.40, "POOR"),
        ]:
            report = ValidationReport(fidelity_score=score)
            md = report.to_markdown()
            assert expected in md

    def test_to_markdown_with_strict_failures(self):
        report = ValidationReport(
            fidelity_score=0.9,
            strict_passed=False,
            strict_failures=["1 text differences detected"],
        )

        md = report.to_markdown()

        assert "Strict Gate" in md
        assert "STRICT FAIL" in md
        assert "1 text differences detected" in md


# ============================================================================
# Tests: DocxValidator — identical files
# ============================================================================


class TestValidateIdentical:
    def test_identical_paragraphs(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Comparing a file with itself should yield 100% fidelity."""
        docx_path = tmp_docx_dir / "test.docx"
        _create_docx(
            docx_path,
            paragraphs=[
                _make_paragraph("Hello World"),
                _make_paragraph("Second paragraph"),
            ],
        )

        report = validator.validate(docx_path, docx_path)

        assert report.fidelity_score == pytest.approx(1.0)
        assert report.text_score == pytest.approx(1.0)
        assert report.structure_score == pytest.approx(1.0)
        assert len(report.text_diffs) == 0

    def test_identical_with_table(self, validator: DocxValidator, tmp_docx_dir: Path):
        """File with tables compared with itself."""
        docx_path = tmp_docx_dir / "table.docx"
        _create_docx(
            docx_path,
            tables=[
                _make_table(
                    [
                        ["Name", "Age", "City"],
                        ["Alice", "30", "Taipei"],
                        ["Bob", "25", "Tokyo"],
                    ]
                ),
            ],
        )

        report = validator.validate(docx_path, docx_path)
        assert report.table_score == pytest.approx(1.0)
        assert report.fidelity_score == pytest.approx(1.0)

    def test_identical_with_media(self, validator: DocxValidator, tmp_docx_dir: Path):
        """File with images compared with itself."""
        docx_path = tmp_docx_dir / "media.docx"
        fake_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        _create_docx(
            docx_path,
            paragraphs=[_make_paragraph("Document with image")],
            media={"image1.png": fake_image},
        )

        report = validator.validate(docx_path, docx_path)
        assert report.media_score == pytest.approx(1.0)
        assert report.original_stats["media_files"] == 1

    def test_identical_strict_passes(
        self, validator: DocxValidator, tmp_docx_dir: Path
    ):
        """Strict mode should pass for identical documents."""
        docx_path = tmp_docx_dir / "strict.docx"
        _create_docx(
            docx_path,
            paragraphs=[_make_paragraph("Strict validation")],
        )

        report = validator.validate(docx_path, docx_path, strict=True)

        assert report.strict_passed is True
        assert report.strict_failures == []


# ============================================================================
# Tests: DocxValidator — text differences
# ============================================================================


class TestValidateTextDiffs:
    def test_modified_text(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Detect changed paragraph text."""
        original = tmp_docx_dir / "original.docx"
        modified = tmp_docx_dir / "modified.docx"

        _create_docx(
            original,
            paragraphs=[
                _make_paragraph("Hello World"),
                _make_paragraph("Original text here"),
            ],
        )
        _create_docx(
            modified,
            paragraphs=[
                _make_paragraph("Hello World"),
                _make_paragraph("Modified text here"),
            ],
        )

        report = validator.validate(original, modified)

        assert report.text_score < 1.0
        assert len(report.text_diffs) == 1
        assert report.text_diffs[0].location == "paragraph 2"
        assert "Original" in report.text_diffs[0].original
        assert "Modified" in report.text_diffs[0].rebuilt

    def test_added_paragraph(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Detect extra paragraph."""
        original = tmp_docx_dir / "original.docx"
        modified = tmp_docx_dir / "modified.docx"

        _create_docx(
            original,
            paragraphs=[_make_paragraph("Para 1")],
        )
        _create_docx(
            modified,
            paragraphs=[
                _make_paragraph("Para 1"),
                _make_paragraph("Para 2 (added)"),
            ],
        )

        report = validator.validate(original, modified)
        assert report.text_score < 1.0
        assert report.structure_score < 1.0
        assert any(d.category == "paragraphs" for d in report.structure_diffs)

    def test_empty_documents(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Two empty docx files should be 100% identical."""
        a = tmp_docx_dir / "a.docx"
        b = tmp_docx_dir / "b.docx"

        _create_docx(a, paragraphs=[])
        _create_docx(b, paragraphs=[])

        report = validator.validate(a, b)
        assert report.fidelity_score == pytest.approx(1.0)

    def test_modified_text_strict_fails(
        self, validator: DocxValidator, tmp_docx_dir: Path
    ):
        """Strict mode should fail on any text diff."""
        original = tmp_docx_dir / "orig.docx"
        modified = tmp_docx_dir / "rebuilt.docx"

        _create_docx(original, paragraphs=[_make_paragraph("Hello")])
        _create_docx(modified, paragraphs=[_make_paragraph("Hello world")])

        report = validator.validate(original, modified, strict=True)

        assert report.strict_passed is False
        assert "text differences detected" in report.strict_failures[0]


class TestValidateDocxStoryParts:
    def test_header_footer_text_differences_fail_strict_gate(
        self, validator: DocxValidator, tmp_docx_dir: Path
    ):
        """Strict mode compares header/footer text, not only document body text."""
        original = tmp_docx_dir / "original.docx"
        modified = tmp_docx_dir / "modified.docx"

        _create_docx(
            original,
            paragraphs=[_make_paragraph("Unchanged body")],
            extra_parts={
                "word/header1.xml": _build_story_part_xml(
                    "hdr", [_make_paragraph("Clinic header")]
                ),
                "word/footer1.xml": _build_story_part_xml(
                    "ftr", [_make_paragraph("Page footer")]
                ),
            },
        )
        _create_docx(
            modified,
            paragraphs=[_make_paragraph("Unchanged body")],
            extra_parts={
                "word/header1.xml": _build_story_part_xml(
                    "hdr", [_make_paragraph("Clinic header changed")]
                ),
                "word/footer1.xml": _build_story_part_xml(
                    "ftr", [_make_paragraph("Page footer changed")]
                ),
            },
        )

        report = validator.validate(original, modified, strict=True)

        assert report.strict_passed is False
        assert report.text_score < 1.0
        locations = {diff.location for diff in report.text_diffs}
        assert "header:word/header1.xml paragraph 1" in locations
        assert "footer:word/footer1.xml paragraph 1" in locations

    def test_footnote_text_differences_fail_strict_gate(
        self, validator: DocxValidator, tmp_docx_dir: Path
    ):
        """Strict mode compares word/footnotes.xml text."""
        original = tmp_docx_dir / "original.docx"
        modified = tmp_docx_dir / "modified.docx"

        _create_docx(
            original,
            paragraphs=[_make_paragraph("Body with footnote")],
            extra_parts={
                "word/footnotes.xml": _build_footnotes_xml(
                    {2: [_make_paragraph("Original footnote")]}
                ),
            },
        )
        _create_docx(
            modified,
            paragraphs=[_make_paragraph("Body with footnote")],
            extra_parts={
                "word/footnotes.xml": _build_footnotes_xml(
                    {2: [_make_paragraph("Modified footnote")]}
                ),
            },
        )

        report = validator.validate(original, modified, strict=True)

        assert report.strict_passed is False
        assert report.text_score < 1.0
        assert len(report.text_diffs) == 1
        assert report.text_diffs[0].location == "footnote:2 paragraph 1"

    def test_header_run_formatting_differences_fail_strict_gate(
        self, validator: DocxValidator, tmp_docx_dir: Path
    ):
        """Header run formatting regressions participate in strict validation."""
        original = tmp_docx_dir / "original.docx"
        modified = tmp_docx_dir / "modified.docx"

        _create_docx(
            original,
            paragraphs=[_make_paragraph("Unchanged body")],
            extra_parts={
                "word/header1.xml": _build_story_part_xml(
                    "hdr",
                    [_make_runs_paragraph([{"text": "Confidential", "italic": True}])],
                ),
            },
        )
        _create_docx(
            modified,
            paragraphs=[_make_paragraph("Unchanged body")],
            extra_parts={
                "word/header1.xml": _build_story_part_xml(
                    "hdr",
                    [_make_runs_paragraph([{"text": "Confidential"}])],
                ),
            },
        )

        report = validator.validate(original, modified, strict=True)

        assert report.strict_passed is False
        assert any(
            diff.location == "header:word/header1.xml paragraph 1/run 1"
            and diff.attribute == "italic"
            for diff in report.format_diffs
        )


# ============================================================================
# Tests: DocxValidator — formatting differences
# ============================================================================


class TestValidateFormattingDiffs:
    def test_bold_difference(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Detect bold formatting change."""
        original = tmp_docx_dir / "original.docx"
        modified = tmp_docx_dir / "modified.docx"

        _create_docx(
            original,
            paragraphs=[_make_paragraph("Bold text", bold=True)],
        )
        _create_docx(
            modified,
            paragraphs=[_make_paragraph("Bold text", bold=False)],
        )

        report = validator.validate(original, modified)
        assert report.format_score < 1.0
        assert any(d.attribute == "bold" for d in report.format_diffs)

    def test_font_size_difference(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Detect font size change."""
        original = tmp_docx_dir / "original.docx"
        modified = tmp_docx_dir / "modified.docx"

        _create_docx(
            original,
            paragraphs=[_make_paragraph("Normal", font_size_half_pt=24)],
        )
        _create_docx(
            modified,
            paragraphs=[_make_paragraph("Normal", font_size_half_pt=28)],
        )

        report = validator.validate(original, modified)
        assert report.format_score < 1.0
        assert any(d.attribute == "font_size" for d in report.format_diffs)

    def test_color_difference(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Detect color change."""
        original = tmp_docx_dir / "original.docx"
        modified = tmp_docx_dir / "modified.docx"

        _create_docx(
            original,
            paragraphs=[_make_paragraph("Red text", color="FF0000")],
        )
        _create_docx(
            modified,
            paragraphs=[_make_paragraph("Red text", color="0000FF")],
        )

        report = validator.validate(original, modified)
        assert report.format_score < 1.0
        assert any(d.attribute == "color" for d in report.format_diffs)

    def test_later_run_format_difference_fails_strict_gate(
        self, validator: DocxValidator, tmp_docx_dir: Path
    ):
        """Detect formatting regressions beyond the first run."""
        original = tmp_docx_dir / "original.docx"
        modified = tmp_docx_dir / "modified.docx"

        _create_docx(
            original,
            paragraphs=[
                _make_runs_paragraph(
                    [
                        {"text": "first "},
                        {"text": "second", "italic": True, "color": "FF0000"},
                    ]
                )
            ],
        )
        _create_docx(
            modified,
            paragraphs=[
                _make_runs_paragraph(
                    [
                        {"text": "first "},
                        {"text": "second", "color": "FF0000"},
                    ]
                )
            ],
        )

        report = validator.validate(original, modified, strict=True)
        assert report.format_score < 1.0
        assert report.strict_passed is False
        assert any(
            d.location == "paragraph 1/run 2" and d.attribute == "italic"
            for d in report.format_diffs
        )

    def test_table_cell_run_format_difference_fails_strict_gate(
        self, validator: DocxValidator, tmp_docx_dir: Path
    ):
        """Detect formatting regressions inside table cell runs."""
        original = tmp_docx_dir / "original.docx"
        modified = tmp_docx_dir / "modified.docx"

        _create_docx(
            original,
            tables=[
                _make_formatted_table(
                    [[[{"text": "Cell text", "bold": True, "color": "FF0000"}]]]
                )
            ],
        )
        _create_docx(
            modified,
            tables=[
                _make_formatted_table([[[{"text": "Cell text", "color": "FF0000"}]]])
            ],
        )

        report = validator.validate(original, modified, strict=True)

        assert report.strict_passed is False
        assert report.format_score < 1.0
        assert any(
            d.location == "table 1/row 1/col 1/run 1" and d.attribute == "bold"
            for d in report.format_diffs
        )


# ============================================================================
# Tests: DocxValidator — table differences
# ============================================================================


class TestValidateTableDiffs:
    def test_cell_content_change(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Detect changed cell content."""
        original = tmp_docx_dir / "original.docx"
        modified = tmp_docx_dir / "modified.docx"

        _create_docx(
            original,
            tables=[_make_table([["A", "B"], ["1", "2"]])],
        )
        _create_docx(
            modified,
            tables=[_make_table([["A", "B"], ["1", "99"]])],
        )

        report = validator.validate(original, modified)
        assert report.table_score < 1.0
        assert len(report.table_diffs) == 1
        assert "2" in report.table_diffs[0].original
        assert "99" in report.table_diffs[0].rebuilt

    def test_table_row_count_change(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Detect added row."""
        original = tmp_docx_dir / "original.docx"
        modified = tmp_docx_dir / "modified.docx"

        _create_docx(
            original,
            tables=[_make_table([["A"], ["1"]])],
        )
        _create_docx(
            modified,
            tables=[_make_table([["A"], ["1"], ["2"]])],
        )

        report = validator.validate(original, modified)
        assert report.table_score < 1.0


# ============================================================================
# Tests: DocxValidator — media differences
# ============================================================================


class TestValidateMediaDiffs:
    def test_missing_image(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Detect missing image in rebuilt."""
        original = tmp_docx_dir / "original.docx"
        modified = tmp_docx_dir / "modified.docx"

        _create_docx(
            original,
            paragraphs=[_make_paragraph("With image")],
            media={"photo.png": b"\x89PNG" + b"\x00" * 50},
        )
        _create_docx(
            modified,
            paragraphs=[_make_paragraph("With image")],
        )

        report = validator.validate(original, modified)
        assert report.media_score == 0.0
        assert any(d.status == "missing" for d in report.media_diffs)

    def test_changed_image(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Detect changed image content."""
        original = tmp_docx_dir / "original.docx"
        modified = tmp_docx_dir / "modified.docx"

        _create_docx(
            original,
            paragraphs=[_make_paragraph("Image")],
            media={"photo.png": b"\x89PNG" + b"\x00" * 50},
        )
        _create_docx(
            modified,
            paragraphs=[_make_paragraph("Image")],
            media={"photo.png": b"\x89PNG" + b"\xff" * 50},
        )

        report = validator.validate(original, modified)
        assert report.media_score == 0.0
        assert any(d.status == "changed" for d in report.media_diffs)


# ============================================================================
# Tests: DocxValidator — style differences
# ============================================================================


class TestValidateStyleDiffs:
    def test_style_change(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Detect paragraph style change."""
        original = tmp_docx_dir / "original.docx"
        modified = tmp_docx_dir / "modified.docx"

        _create_docx(
            original,
            paragraphs=[_make_paragraph("Title", style="Heading1")],
        )
        _create_docx(
            modified,
            paragraphs=[_make_paragraph("Title", style="Normal")],
        )

        report = validator.validate(original, modified)
        assert report.style_score < 1.0
        assert len(report.style_diffs) >= 1


# ============================================================================
# Tests: DocxValidator — error handling
# ============================================================================


class TestValidateErrors:
    def test_missing_original(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Handle missing original file gracefully."""
        report = validator.validate(
            tmp_docx_dir / "nonexistent.docx",
            tmp_docx_dir / "also_nonexistent.docx",
        )
        assert len(report.errors) > 0
        assert report.fidelity_score == 0.0

    def test_missing_rebuilt(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Handle missing rebuilt file."""
        original = tmp_docx_dir / "original.docx"
        _create_docx(original, paragraphs=[_make_paragraph("test")])

        report = validator.validate(original, tmp_docx_dir / "missing.docx")
        assert len(report.errors) > 0


# ============================================================================
# Tests: Full round-trip (DocxAdapter integration)
# ============================================================================


class TestFullRoundTrip:
    """Test the complete cycle: create .docx → parse_to_ir → ir_to_docx → validate."""

    def test_simple_paragraphs_roundtrip(
        self, validator: DocxValidator, tmp_docx_dir: Path
    ):
        """Simple paragraphs should survive round-trip perfectly."""
        from src.infrastructure.docx_adapter import DocxAdapter

        adapter = DocxAdapter()

        # Create a minimal docx
        original = tmp_docx_dir / "original.docx"
        _create_docx(
            original,
            paragraphs=[
                _make_paragraph("First paragraph"),
                _make_paragraph("Second paragraph"),
                _make_paragraph("Third paragraph with special chars: é à ü 中文"),
            ],
        )

        # Parse → IR → rebuild
        data_dir = tmp_docx_dir / "data"
        data_dir.mkdir()
        ir = adapter.parse_to_ir(original, data_dir)

        rebuilt = tmp_docx_dir / "rebuilt.docx"
        adapter.ir_to_docx(ir, data_dir, rebuilt)

        # Validate
        report = validator.validate(original, rebuilt)

        assert report.text_score == pytest.approx(1.0), (
            f"Text diffs: {[(d.location, d.original, d.rebuilt) for d in report.text_diffs]}"
        )
        assert report.structure_score == pytest.approx(1.0)
        assert report.fidelity_score >= 0.95

    def test_table_roundtrip(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Tables should preserve cell content through round-trip."""
        from src.infrastructure.docx_adapter import DocxAdapter

        adapter = DocxAdapter()

        original = tmp_docx_dir / "table.docx"
        _create_docx(
            original,
            tables=[
                _make_table(
                    [
                        ["Name", "Age", "City"],
                        ["Alice", "30", "Taipei"],
                        ["Bob", "25", "Tokyo"],
                    ]
                ),
            ],
        )

        data_dir = tmp_docx_dir / "data"
        data_dir.mkdir()
        ir = adapter.parse_to_ir(original, data_dir)
        rebuilt = tmp_docx_dir / "rebuilt.docx"
        adapter.ir_to_docx(ir, data_dir, rebuilt)

        report = validator.validate(original, rebuilt)
        assert report.table_score == pytest.approx(1.0), (
            f"Table diffs: {[(d.location, d.original, d.rebuilt) for d in report.table_diffs]}"
        )

    def test_mixed_content_roundtrip(
        self, validator: DocxValidator, tmp_docx_dir: Path
    ):
        """Document with paragraphs + tables should survive round-trip."""
        from src.infrastructure.docx_adapter import DocxAdapter

        adapter = DocxAdapter()

        original = tmp_docx_dir / "mixed.docx"
        body_elements = [
            _make_paragraph("Introduction", style="Heading1"),
            _make_paragraph("This is the body text."),
            _make_table(
                [
                    ["Header 1", "Header 2"],
                    ["Data A", "Data B"],
                ]
            ),
            _make_paragraph("Conclusion"),
        ]
        _create_docx(original, body_elements=body_elements)

        data_dir = tmp_docx_dir / "data"
        data_dir.mkdir()
        ir = adapter.parse_to_ir(original, data_dir)
        rebuilt = tmp_docx_dir / "rebuilt.docx"
        adapter.ir_to_docx(ir, data_dir, rebuilt)

        report = validator.validate(original, rebuilt)

        # Text and tables should be preserved
        assert report.text_score == pytest.approx(1.0), report.to_markdown()
        assert report.table_score == pytest.approx(1.0), report.to_markdown()
        assert report.style_score == pytest.approx(1.0), report.to_markdown()
        assert report.fidelity_score >= 0.95

    def test_formatted_text_roundtrip(
        self, validator: DocxValidator, tmp_docx_dir: Path
    ):
        """Bold/italic formatting should be preserved."""
        from src.infrastructure.docx_adapter import DocxAdapter

        adapter = DocxAdapter()

        original = tmp_docx_dir / "formatted.docx"
        _create_docx(
            original,
            paragraphs=[
                _make_paragraph("Bold text", bold=True),
                _make_paragraph("Italic text", italic=True),
                _make_paragraph(
                    "Styled text",
                    font_name="Arial",
                    font_size_half_pt=28,
                    color="FF0000",
                ),
            ],
        )

        data_dir = tmp_docx_dir / "data"
        data_dir.mkdir()
        ir = adapter.parse_to_ir(original, data_dir)
        rebuilt = tmp_docx_dir / "rebuilt.docx"
        adapter.ir_to_docx(ir, data_dir, rebuilt)

        report = validator.validate(original, rebuilt)

        # Template-based rebuild preserves formatting of original XML
        assert report.format_score == pytest.approx(1.0), (
            f"Format diffs: {[(d.location, d.attribute, d.original, d.rebuilt) for d in report.format_diffs]}"
        )

    def test_media_preserved_roundtrip(
        self, validator: DocxValidator, tmp_docx_dir: Path
    ):
        """Media files should be preserved in round-trip."""
        from src.infrastructure.docx_adapter import DocxAdapter

        adapter = DocxAdapter()

        original = tmp_docx_dir / "with_media.docx"
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x42" * 200
        _create_docx(
            original,
            paragraphs=[_make_paragraph("Document with image")],
            media={"image1.png": fake_png},
        )

        data_dir = tmp_docx_dir / "data"
        data_dir.mkdir()
        ir = adapter.parse_to_ir(original, data_dir)
        rebuilt = tmp_docx_dir / "rebuilt.docx"
        adapter.ir_to_docx(ir, data_dir, rebuilt)

        report = validator.validate(original, rebuilt)
        assert report.media_score == pytest.approx(1.0)

    def test_validate_ir_roundtrip_helper(
        self, validator: DocxValidator, tmp_docx_dir: Path
    ):
        """Test the convenience method validate_ir_roundtrip."""
        from src.infrastructure.docx_adapter import DocxAdapter

        adapter = DocxAdapter()

        original = tmp_docx_dir / "original.docx"
        _create_docx(
            original,
            paragraphs=[
                _make_paragraph("Hello"),
                _make_paragraph("World"),
            ],
        )

        data_dir = tmp_docx_dir / "data"
        data_dir.mkdir()

        report = validator.validate_ir_roundtrip(original, adapter, data_dir)

        assert report.fidelity_score >= 0.95
        assert report.text_score == pytest.approx(1.0)


# ============================================================================
# Tests: Edit + Round-Trip (DFM editing simulation)
# ============================================================================


class TestEditRoundTrip:
    """Test that edits via DFM are correctly reflected in rebuilt docx."""

    def test_text_edit_reflected(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Edit text in IR, rebuild, verify the change appears."""
        from src.infrastructure.docx_adapter import DocxAdapter

        adapter = DocxAdapter()

        original = tmp_docx_dir / "original.docx"
        _create_docx(
            original,
            paragraphs=[
                _make_paragraph("Before edit"),
                _make_paragraph("Keep this"),
            ],
        )

        data_dir = tmp_docx_dir / "data"
        data_dir.mkdir()
        ir = adapter.parse_to_ir(original, data_dir)

        # Simulate DFM edit: change first paragraph text
        ir.blocks[0].content = "After edit"

        rebuilt = tmp_docx_dir / "rebuilt.docx"
        adapter.ir_to_docx(ir, data_dir, rebuilt)

        # Validate against original — should show exactly 1 text diff
        report = validator.validate(original, rebuilt)
        assert len(report.text_diffs) == 1
        assert "Before edit" in report.text_diffs[0].original
        assert "After edit" in report.text_diffs[0].rebuilt

        # Second paragraph should be unchanged
        assert report.rebuilt_stats["paragraphs"] == report.original_stats["paragraphs"]

    def test_table_edit_reflected(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Edit table cell in IR, rebuild, verify change."""
        from src.infrastructure.docx_adapter import DocxAdapter

        adapter = DocxAdapter()

        original = tmp_docx_dir / "original.docx"
        _create_docx(
            original,
            tables=[_make_table([["Name", "Score"], ["Alice", "100"]])],
        )

        data_dir = tmp_docx_dir / "data"
        data_dir.mkdir()
        ir = adapter.parse_to_ir(original, data_dir)

        # Edit table content in IR (change "100" to "200")
        table_block = ir.blocks[0]
        table_block.content = table_block.content.replace("100", "200")

        rebuilt = tmp_docx_dir / "rebuilt.docx"
        adapter.ir_to_docx(ir, data_dir, rebuilt)

        report = validator.validate(original, rebuilt)

        # Should have exactly 1 table cell diff
        assert len(report.table_diffs) == 1
        assert "100" in report.table_diffs[0].original
        assert "200" in report.table_diffs[0].rebuilt


# ============================================================================
# Tests: Weighted score calculation
# ============================================================================


class TestWeightedScoring:
    def test_weights_sum_to_one(self, validator: DocxValidator):
        """Verify weights sum to 1.0."""
        total = sum(validator.WEIGHTS.values())
        assert total == pytest.approx(1.0)

    def test_text_dominates(self, validator: DocxValidator, tmp_docx_dir: Path):
        """Text has highest weight (0.35), so text errors should impact score most."""
        # Perfect structure/format/table/media/style but imperfect text
        ValidationReport(
            structure_score=1.0,
            text_score=0.0,  # All text wrong
            format_score=1.0,
            table_score=1.0,
            media_score=1.0,
            style_score=1.0,
        )
        # Manually compute
        expected = (
            0.15 * 1.0  # structure
            + 0.35 * 0.0  # text
            + 0.15 * 1.0  # format
            + 0.15 * 1.0  # table
            + 0.10 * 1.0  # media
            + 0.10 * 1.0  # style
        )
        assert expected == pytest.approx(0.65)
