"""Real workbook fixtures and request helpers shared by native format regressions."""

from __future__ import annotations

import io
import zipfile

import xlsxwriter

from src.application.native_document_service import NativeDocumentService
from src.domain.native_assets import NativeCellEdit, NativeDocumentRequest


def _parts(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _replace(data: bytes, replacements: dict[str, bytes]) -> bytes:
    parts = _parts(data)
    parts.update(replacements)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in parts.items():
            archive.writestr(name, value)
    return output.getvalue()


def build_workbook() -> bytes:
    output = io.BytesIO()
    with xlsxwriter.Workbook(output, {"in_memory": True}) as book:
        data = book.add_worksheet("Data")
        other = book.add_worksheet("Other")
        bold = book.add_format({"bold": True, "bg_color": "#FFCC00"})
        money = book.add_format({"num_format": "$0.00"})
        data.write_string("A1", "Original", bold)
        data.write_number("A2", 10, money)
        data.write_number("A3", 20, money)
        data.write_formula("B2", "=A2*2", money, 20)
        data.write_rich_string("D2", bold, "Bold", " normal")
        data.merge_range("A5:D6", "Merged", bold)
        data.write_comment("A1", "Keep this comment")
        data.write_url("C3", "https://example.com", string="Link")
        data.add_table(
            "A8:B10",
            {
                "data": [[1, 2], [3, 4]],
                "columns": [{"header": "First"}, {"header": "Second"}],
            },
        )
        chart = book.add_chart({"type": "column"})
        chart.add_series({"values": "=Data!$A$2:$A$3"})
        data.insert_chart("H1", chart)
        other.write_string("A1", "Do not change")
        other.write_formula("B1", "=Data!A2")
        other.protect()
    return _replace(
        output.getvalue(),
        {"customXml/item1.xml": b"<custom keep='exact'>  text </custom>"},
    )


def _edit(
    cell: str, value: object, kind: str = "string", sheet: str = "Data"
) -> NativeCellEdit:
    return NativeCellEdit.model_validate(
        {"sheet": sheet, "cell": cell, "kind": kind, "value": value}
    )


def _call(service: NativeDocumentService, **request: object) -> dict:
    return service.execute(NativeDocumentRequest.model_validate(request))
