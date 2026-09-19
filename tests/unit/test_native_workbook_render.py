"""Bounded converter failures and genuine PDF output with a frozen worksheet map."""

import hashlib

import pymupdf
import pytest

from src.domain.native_rendition import NativeWorkbookRendition
from src.infrastructure import native_workbook_render as rendering
from src.infrastructure.native_pdf import NativePdf
from tests.native_workbook_render_helpers import rendered_workbook


@pytest.mark.parametrize(
    "mode,calculation", [("print", "prefer_cache"), ("whole_sheet", "recalculate")]
)
def test_renderer_receipt_and_profile_match_explicit_intent(
    tmp_path, monkeypatch, mode, calculation
):
    source = rendered_workbook()
    pages = 4 if mode == "whole_sheet" else 2
    seen = []

    def office(command, root, timeout):
        assert timeout > 0
        profile = (root / "profile/user/registrymodifications.xcu").read_text()
        assert "DisableMacrosExecution" in profile
        assert "<value>true</value>" in profile
        assert (
            f'oor:name="OOXMLRecalcMode" oor:op="fuse"><value>{0 if calculation == "recalculate" else 1}</value>'
            in profile
        )
        assert (
            f'oor:name="SinglePageSheets" oor:op="fuse"><value>{str(mode == "whole_sheet").lower()}</value>'
            in profile
        )
        if "--version" in command:
            return "LibreOffice test fixture"
        assert "pdf:calc_pdf_Export" in command
        assert (root / "source.xlsx").read_bytes() == source
        with pymupdf.open() as pdf:
            for _ in range(pages):
                pdf.new_page()
            pdf.save(root / "source.pdf")
        seen.append(root)
        return "converted"

    monkeypatch.setattr(rendering, "office_binary", lambda _component: "test-office")
    monkeypatch.setattr(rendering, "run_office", office)
    monkeypatch.setattr(rendering, "ProcessNativePdf", lambda **_kw: NativePdf())
    pdf, receipt = rendering.LibreOfficeWorkbookRenderer().convert(
        source, NativeWorkbookRendition(mode=mode, calculation=calculation)
    )
    assert receipt["rendered_pdf_sha256"] == hashlib.sha256(pdf).hexdigest()
    assert receipt["page_count"] == pages and len(receipt["pages"]) == pages
    assert receipt["source_copy_unchanged"]
    if mode == "whole_sheet":
        assert [item["page_index"] for item in receipt["sheet_page_mapping"]] == [
            0,
            1,
            2,
            3,
        ]
    else:
        assert receipt["sheet_page_mapping"] is None
    assert all(not root.exists() for root in seen)


@pytest.mark.parametrize(
    "fault",
    [
        "version",
        "missing",
        "changed_source",
        "symlink_pdf",
        "bad_pdf",
        "page_count",
        "too_large",
    ],
)
def test_converter_failure_does_not_return_an_unverified_rendition(monkeypatch, fault):
    source = rendered_workbook()
    roots = []

    def office(command, root, timeout):
        roots.append(root)
        if "--version" in command:
            return "Unknown" if fault == "version" else "LibreOffice fixture"
        if fault == "missing":
            return "no output"
        with pymupdf.open() as pdf:
            for _ in range(1 if fault == "page_count" else 4):
                pdf.new_page()
            pdf.save(root / "source.pdf")
        if fault == "changed_source":
            (root / "source.xlsx").write_bytes(b"changed")
        elif fault == "symlink_pdf":
            (root / "source.pdf").rename(root / "other.pdf")
            (root / "source.pdf").symlink_to(root / "other.pdf")
        elif fault == "bad_pdf":
            (root / "source.pdf").write_bytes(b"bad pdf")
        elif fault == "too_large":
            monkeypatch.setattr(rendering, "MAX_NATIVE_BYTES", 1)
        return "output"

    monkeypatch.setattr(rendering, "office_binary", lambda _component: "test-office")
    monkeypatch.setattr(rendering, "run_office", office)
    monkeypatch.setattr(rendering, "ProcessNativePdf", lambda **_kw: NativePdf())
    with pytest.raises(ValueError):
        rendering.LibreOfficeWorkbookRenderer().convert(
            source,
            NativeWorkbookRendition(mode="whole_sheet", calculation="recalculate"),
        )
    assert roots and all(not root.exists() for root in roots)


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_timeout_must_be_finite_positive(timeout):
    with pytest.raises(ValueError, match="timeout"):
        rendering.LibreOfficeWorkbookRenderer(timeout)
