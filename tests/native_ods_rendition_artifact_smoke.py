"""Replay an actual ODS/Calc rendition through installed source and Wiki wiring."""

import argparse
import hashlib
import json
from pathlib import Path

import pymupdf

import src
from src.application.native_document_service import NativeDocumentService
from src.domain.native_assets import NativeDocumentRequest
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_ods import NativeODSFileAdapter
from src.infrastructure.native_ods_render_source import rendering_source
from src.infrastructure.native_pdf import NativePdf
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from src.infrastructure.native_workbook_render import LibreOfficeODSRenderer


def call(service, **fields):
    return service.execute(NativeDocumentRequest.model_validate(fields))


def receipt(service, asset):
    text, sha, offset = "", None, 0
    while True:
        page = call(
            service,
            op="read_rendition",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            text_offset=offset,
            text_limit=700,
        )
        sha = sha or page["text_sha256"]
        assert page["text_sha256"] == sha and page["excerpt_char_range"][0] == offset
        text += page["text_excerpt"]
        if page["next_text_offset"] is None:
            break
        offset = page["next_text_offset"]
    assert hashlib.sha256(text.encode()).hexdigest() == sha
    return json.loads(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-installed", action="store_true")
    parser.add_argument("--actual-calc", action="store_true")
    args = parser.parse_args()
    installed = Path(src.__file__).resolve().parent
    if args.require_installed:
        assert "site-packages" in str(installed) or "archive-v0" in str(installed), (
            installed
        )
    manifest = {
        str(p.relative_to(installed)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(installed.rglob("*.py"))
    }
    assert manifest == json.loads(args.source_manifest.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    data = (args.proof / "source.ods").read_bytes()
    expected_pdf = (args.proof / "actual.pdf").read_bytes()
    expected_render = json.loads((args.proof / "receipt.json").read_text())
    assert rendering_source(data) == expected_render["worksheets"]
    assert (
        hashlib.sha256(expected_pdf).hexdigest()
        == expected_render["rendered_pdf_sha256"]
    )

    class CapturedCalc:
        def convert(self, source, request):
            assert (
                source == data
                and request.mode == "print"
                and request.calculation == "recalculate"
            )
            return expected_pdf, expected_render

    root = args.output / "assets"

    def service_at(renderer=None):
        return NativeDocumentService(
            FileNativeAssetRepository(root),
            SpreadsheetFileAdapter(),
            FileNativeWikiPublisher((root,)),
            ods=NativeODSFileAdapter(),
            pdfs=NativePdf(),
            ods_renderer=renderer,
        )

    service = service_at(
        LibreOfficeODSRenderer() if args.actual_calc else CapturedCalc()
    )
    contract = call(service, op="contract", for_op="create_workbook_rendition")
    assert contract["workbook_rendering"]["source_formats"] == ["ods"]
    source = args.output / "source.ods"
    source.write_bytes(data)
    mtime = source.stat().st_mtime_ns
    asset = call(service, op="register", source_path=str(source))["asset"]
    created = call(
        service,
        op="create_workbook_rendition",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        workbook_rendition={"mode": "print", "calculation": "recalculate"},
    )
    pdf = created["asset"]
    full = receipt(service, pdf)
    assert full["changes"][0]["source_reference"] == asset["file_reference"]
    actual = service.repository.read(pdf["asset_id"], pdf["revision"])
    with (
        pymupdf.open(stream=actual, filetype="pdf") as a,
        pymupdf.open(stream=expected_pdf, filetype="pdf") as b,
    ):
        assert len(a) == len(b) == 1
        assert a[0].get_text() == b[0].get_text()
        assert a[0].get_pixmap().samples == b[0].get_pixmap().samples
    request = {
        "op": "export_wiki",
        "asset_id": pdf["asset_id"],
        "revision": pdf["revision"],
        "output_dir": str(args.output / "wiki"),
    }
    wiki = call(service, **request)
    directory = Path(wiki["output_dir"])
    files = {
        str(p.relative_to(directory)): p.read_bytes()
        for p in directory.rglob("*")
        if p.is_file()
    }
    snapshot = json.loads(files["manifest.json"])
    attachment = snapshot["rendition"]["source_attachment"]
    assert attachment.endswith(".ods") and files[attachment] == data
    assert json.loads(files["rendition.json"]) == full
    reopened = service_at()  # Historical PDF/receipt reads need no installed Calc.
    assert receipt(reopened, pdf) == full
    assert call(reopened, **request)["reused"]
    assert files == {
        str(p.relative_to(directory)): p.read_bytes()
        for p in directory.rglob("*")
        if p.is_file()
    }
    assert (source.read_bytes(), source.stat().st_mtime_ns) == (data, mtime)
    result = {
        "source_files": len(manifest),
        "installed_source": str(installed),
        "actual_calc": args.actual_calc,
        "captured_calc_replay": not args.actual_calc,
        "ods_resources_checked": True,
        "all_page_pixels_match": True,
        "full_receipt_and_wiki_survive_restart_without_renderer": True,
        "native_source_unchanged": True,
    }
    (args.output / "proof.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
