"""Convert one exact workbook revision once; retain the resulting PDF for review."""

from __future__ import annotations

import hashlib
import math
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from src.domain.native_asset_models import MAX_NATIVE_BYTES
from src.infrastructure.native_ods_render_source import rendering_source as ods_source
from src.infrastructure.native_office_process import (
    office_binary,
    prepare_profile,
    run_office,
)
from src.infrastructure.native_pdf_process import ProcessNativePdf
from src.infrastructure.native_workbook_render_source import rendering_source

if TYPE_CHECKING:
    from src.domain.native_rendition import NativeWorkbookRendition


def calc_profile(
    root: Path,
    request: NativeWorkbookRendition,
    *,
    source_format: Literal["xlsx", "ods"] = "xlsx",
) -> str:
    profile = prepare_profile(root)
    settings = root / "profile/user/registrymodifications.xcu"
    whole = str(request.mode == "whole_sheet").lower()
    recalc = 0 if request.calculation == "recalculate" else 1
    recalc_property = "ODFRecalcMode" if source_format == "ods" else "OOXMLRecalcMode"
    extra = f"""<item oor:path="/org.openoffice.Office.Calc/Formula/Load">
<prop oor:name="{recalc_property}" oor:op="fuse"><value>{recalc}</value></prop></item>
<item oor:path="/org.openoffice.Office.Common/Filter/PDF/Export">
<prop oor:name="SinglePageSheets" oor:op="fuse"><value>{whole}</value></prop>
<prop oor:name="ExportFormFields" oor:op="fuse"><value>false</value></prop></item>
<item oor:path="/org.openoffice.Office.Calc/Print/Other">
<prop oor:name="AllSheets" oor:op="fuse"><value>true</value></prop></item>
<item oor:path="/org.openoffice.Office.Calc/Print/Page">
<prop oor:name="EmptyPages" oor:op="fuse"><value>false</value></prop></item>"""
    if source_format == "ods":
        extra += """<item oor:path="/org.openoffice.Office.Calc/Content/Update">
<prop oor:name="Link" oor:op="fuse"><value>1</value></prop></item>"""
    settings.write_text(
        settings.read_text(encoding="utf-8").replace(
            "</oor:items>", extra + "</oor:items>"
        ),
        encoding="utf-8",
    )
    return profile


class LibreOfficeWorkbookRenderer:
    def __init__(self, timeout: float = 60):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Workbook render timeout must be finite and positive")
        self.timeout = timeout

    def convert(
        self, data: bytes, request: NativeWorkbookRendition
    ) -> tuple[bytes, dict[str, Any]]:
        return self._convert(data, request, rendering_source(data), "xlsx")

    def _convert(
        self,
        data: bytes,
        request: NativeWorkbookRendition,
        sheets: list[dict[str, Any]],
        source_format: Literal["xlsx", "ods"],
    ) -> tuple[bytes, dict[str, Any]]:
        binary = office_binary("Calc")
        deadline = time.monotonic() + self.timeout
        with tempfile.TemporaryDirectory(prefix="native-workbook-render-") as directory:
            root = Path(directory)
            profile = calc_profile(root, request, source_format=source_format)
            version = run_office(
                [binary, profile, "--headless", "--version"],
                root,
                deadline - time.monotonic(),
            )
            if "LibreOffice" not in version:
                raise ValueError("Could not identify the LibreOffice renderer version")
            source = root / f"source.{source_format}"
            source.write_bytes(data)
            run_office(
                [
                    binary,
                    profile,
                    "--headless",
                    "--norestore",
                    "--nodefault",
                    "--convert-to",
                    "pdf:calc_pdf_Export",
                    "--outdir",
                    str(root),
                    str(source),
                ],
                root,
                deadline - time.monotonic(),
            )
            pdf = root / "source.pdf"
            if not pdf.is_file() or pdf.is_symlink():
                raise ValueError(
                    f"LibreOffice produced no workbook PDF; check that Calc is installed and can open this {source_format.upper()}"
                )
            if not 0 < pdf.stat().st_size <= MAX_NATIVE_BYTES:
                raise ValueError("Rendered workbook PDF exceeds the byte limit")
            with pdf.open("rb") as handle:
                converted = handle.read(MAX_NATIVE_BYTES + 1)
            if len(converted) > MAX_NATIVE_BYTES:
                raise ValueError("Rendered workbook PDF exceeds the byte limit")
            if (
                source.is_symlink()
                or source.stat().st_size != len(data)
                or source.read_bytes() != data
            ):
                raise ValueError("Renderer changed its temporary source copy")
            metadata = ProcessNativePdf(timeout=deadline - time.monotonic()).inspect(
                converted
            )
        count = metadata["page_count"]
        if request.mode == "whole_sheet" and count != len(sheets):
            raise ValueError(
                "Whole-sheet PDF page count does not match source worksheet inventory"
            )
        return converted, {
            "renderer": {"name": "LibreOffice Calc", "version": version[:256]},
            "mode": request.mode,
            "calculation_requested": request.calculation,
            "rendered_pdf_sha256": hashlib.sha256(converted).hexdigest(),
            "page_count": count,
            "pages": metadata["pages"],
            "worksheets": sheets,
            "sheet_page_mapping": [
                {"worksheet": sheet["key"], "page_index": sheet["index"]}
                for sheet in sheets
            ]
            if request.mode == "whole_sheet"
            else None,
            "mapping_basis": "SinglePageSheets source order and verified page count"
            if request.mode == "whole_sheet"
            else "Unassigned; print ranges, hidden sheets and pagination can omit or split sheets",
            "source_copy_unchanged": True,
            "limitations": [
                "Static LibreOffice output depends on installed fonts; it does not certify Microsoft Excel fidelity."
                if source_format == "xlsx"
                else "Static LibreOffice output depends on installed fonts; it does not certify fidelity in other ODF readers.",
                "Whole-sheet output ignores print ranges, page settings and hidden state; blank pages may be tiny and overflowing text or objects may be clipped.",
                "Print output can omit hidden/blank sheets and cells outside print ranges; PDF pages are not cell locators.",
                "Calculation is a requested import policy, not a verified result. Missing caches, volatile and unsupported formulas require Agent review.",
                "This stored PDF never recalculates while reading pages. Source workbook caches remain unchanged.",
                "Comments, interactive content and full-resolution layout require separate review. No semantic or visual verdict is asserted.",
            ],
        }


class LibreOfficeODSRenderer(LibreOfficeWorkbookRenderer):
    def convert(
        self, data: bytes, request: NativeWorkbookRendition
    ) -> tuple[bytes, dict[str, Any]]:
        pdf, receipt = self._convert(data, request, ods_source(data), "ods")
        receipt.update(
            source_format="ods",
            calculation_setting="ODFRecalcMode",
            external_link_updates="disabled",
        )
        return pdf, receipt
