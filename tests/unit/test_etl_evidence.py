"""Captured ETL evidence survives mutable sources and rejects forged provenance."""

import hashlib
import io
import json
import shutil
from copy import deepcopy

import pymupdf
import pytest
from PIL import Image, ImageChops

from src.application.csl_citation_service import CslCitationService, canonical, digest
from src.application.etl_evidence_service import EtlEvidenceService
from src.application.etl_references import (
    _asset_ref_from_manifest_asset,
    asset_ref_from_span,
)
from src.application.native_document_service import NativeDocumentService
from src.domain.citation import build_evidence_spans
from src.domain.csl_citations import CslDocument
from src.domain.entities import DocumentManifest, FigureAsset, TableAsset
from src.domain.etl_evidence import EtlEvidenceReference, EtlSourceSelector
from src.infrastructure.csl_processor import NodeCslProcessor
from src.infrastructure.etl_evidence_store import (
    FileEtlSnapshotRepository,
    FileEtlSourceReader,
)
from src.infrastructure.file_storage import FileStorage
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_pdf import NativePdf
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_workbook_helpers import _call
from tests.unit.test_csl_processor import document


@pytest.fixture
def etl_context(tmp_path):
    storage = FileStorage(tmp_path / "etl")
    doc_id = "doc_citation_test"
    directory = storage.get_doc_dir(doc_id)
    pdf = pymupdf.open()
    pdf.new_page(width=300, height=400).insert_text((30, 60), "Captured source 007")
    original = pdf.tobytes()
    pdf.close()
    (directory / "original.pdf").write_bytes(original)
    image = directory / "images" / "figure.png"
    image.parent.mkdir()
    Image.new("RGB", (24, 18), (31, 75, 105)).save(image)
    markdown = "Evidence dose 007 µg.\n\n| Name | Value |\n| X | 007 |\n"
    blocks = [
        {
            "block_id": "block1",
            "block_type": "Text",
            "page": 1,
            "text": "Evidence dose 007 µg.",
            "bbox": [1.0, 2.0, 30.0, 40.0],
            "metadata": {"line_start": 0, "line_end": 1},
        }
    ]
    storage.save_markdown(doc_id, markdown)
    storage.save_blocks(doc_id, blocks)
    manifest = DocumentManifest(
        doc_id=doc_id, filename="Source.pdf", source_pdf_sha256=digest(original)
    )
    manifest.assets.tables = [
        TableAsset(
            id="table1",
            page=1,
            markdown="| X | 007 |",
            row_count=1,
            col_count=2,
            line_start=2,
            line_end=4,
        )
    ]
    manifest.assets.figures = [
        FigureAsset(
            id="figure1",
            page=1,
            path=str(image),
            caption="Source image",
            width=24,
            height=18,
        )
    ]
    storage.save_manifest(manifest)
    span = build_evidence_spans(
        doc_id=doc_id, markdown=markdown, blocks=blocks, source_backend="pymupdf"
    )[0]
    refs = {
        "span": asset_ref_from_span(span),
        "table": _asset_ref_from_manifest_asset(
            manifest, "table", manifest.assets.tables[0]
        ),
        "figure": _asset_ref_from_manifest_asset(
            manifest, "figure", manifest.assets.figures[0]
        ),
    }
    snapshots = FileEtlSnapshotRepository(tmp_path / "snapshots")
    service = EtlEvidenceService(
        FileEtlSourceReader(storage.base_dir), snapshots, NativePdf()
    )
    return service, storage, directory, refs, original


@pytest.mark.parametrize("kind", ["span", "table", "figure"])
def test_capture_is_complete_reusable_and_survives_extraction_deletion(
    etl_context, kind
):
    service, _, directory, refs, original = etl_context
    before = {
        p.relative_to(directory).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in directory.rglob("*")
        if p.is_file()
    }
    result = service.capture(refs[kind])
    reference = EtlEvidenceReference.model_validate(result["reference"])
    assert service.capture(refs[kind]) == result
    assert before == {
        p.relative_to(directory).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in directory.rglob("*")
        if p.is_file()
    }
    record, files = service.resolve(reference)
    assert (
        files["original.pdf"] == original and record["source_reference"] == refs[kind]
    )
    assert record["verification"]["valid"]
    if kind == "figure":
        assert files["figure.png"] == before["images/figure.png"][0]
    shutil.rmtree(directory)
    assert service.read(reference) == result
    preview = service.view(reference, 300)
    with pymupdf.open(stream=original, filetype="pdf") as pdf:
        pix = pdf[0].get_pixmap(matrix=pymupdf.Matrix(0.75, 0.75), alpha=False)
    actual = Image.open(io.BytesIO(preview["image_png"]))
    expected = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    assert (
        actual.size == expected.size
        and ImageChops.difference(actual, expected).getbbox() is None
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("quote", "forged"),
        ("quote_sha256", "0" * 64),
        ("quote_chars", True),
        ("quote_truncated", True),
        ("page", True),
        ("char_range", [0, 2]),
        ("byte_range", [0, 2]),
        ("locator_source_sha256", "0" * 64),
        ("source_revision_id", "0" * 64),
    ],
)
def test_forged_span_is_rejected_without_snapshot(etl_context, field, value):
    service, _, _, refs, _ = etl_context
    ref = deepcopy(refs["span"])
    ref[field] = value
    with pytest.raises(ValueError, match="verification"):
        service.capture(ref)
    assert not service.repository.root.exists()


def test_forged_index_is_not_a_canonical_oracle(etl_context):
    service, storage, directory, refs, _ = etl_context
    good = service.capture(refs["span"])
    span = build_evidence_spans(
        doc_id=refs["span"]["doc_id"],
        markdown=storage.load_markdown(refs["span"]["doc_id"]),
        blocks=storage.load_blocks(refs["span"]["doc_id"]),
        source_backend="pymupdf",
    )[0]
    span.text = "Forged cache content"
    span.text_sha256 = digest(span.text.encode())
    storage.save_citation_index(span.doc_id, [span])
    with pytest.raises(ValueError, match="verification"):
        service.capture(asset_ref_from_span(span))
    assert service.capture(refs["span"]) == good
    (directory / f"{span.doc_id}_full.md").write_text(
        "Changed content", encoding="utf-8"
    )
    with pytest.raises(ValueError):
        service.capture(refs["span"])
    assert service.read(EtlEvidenceReference.model_validate(good["reference"])) == good


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16"])
def test_raw_text_bytes_and_canonical_normalization_are_distinct(etl_context, encoding):
    service, storage, directory, refs, _ = etl_context
    doc_id = refs["span"]["doc_id"]
    text = storage.load_markdown(doc_id)
    raw = text.replace("\n", "\r\n").encode(encoding)
    (directory / f"{doc_id}_full.md").write_bytes(raw)
    captured = service.capture(refs["span"])
    ref = EtlEvidenceReference.model_validate(captured["reference"])
    record, files = service.resolve(ref)
    assert files["canonical.md"] == raw
    assert record["source_identity"]["canonical_markdown_sha256"] == digest(
        text.encode()
    )
    assert record["artifacts"]["canonical.md"]["sha256"] == digest(raw)


def test_bad_source_hash_and_expected_result_hash_do_not_publish(etl_context):
    service, _, directory, refs, original = etl_context
    with pytest.raises(ValueError, match="changed"):
        service.capture(refs["table"], "0" * 64)
    assert not service.repository.root.exists()
    (directory / "original.pdf").write_bytes(original + b"\nchanged")
    with pytest.raises(ValueError, match="source bytes"):
        service.capture(refs["table"])
    assert not service.repository.root.exists()


@pytest.mark.parametrize("mutation", ["missing", "extra", "bytes", "manifest"])
def test_snapshot_tampering_is_rejected(etl_context, mutation):
    service, _, _, refs, _ = etl_context
    result = service.capture(refs["figure"])
    ref = EtlEvidenceReference.model_validate(result["reference"])
    root = service.repository.root / ("native-" + ref.snapshot_id)
    if mutation == "missing":
        (root / "figure.png").unlink()
    elif mutation == "extra":
        (root / "unexpected.txt").write_text("extra", encoding="utf-8")
    elif mutation == "bytes":
        (root / "figure.png").write_bytes(b"changed")
    else:
        (root / "manifest.json").write_bytes(b"{}")
    with pytest.raises((ValueError, OSError)):
        service.read(ref)


def test_reference_identity_cannot_select_another_record(etl_context):
    service, _, _, refs, _ = etl_context
    result = service.capture(refs["table"])
    raw = result["reference"]
    raw["source_id"] = "another"
    with pytest.raises(ValueError, match="reference/content"):
        service.read(EtlEvidenceReference.model_validate(raw))


def test_source_changes_mid_capture_are_rejected(etl_context, monkeypatch):
    service, _, directory, refs, _ = etl_context
    from src.infrastructure import etl_evidence_store as module

    original = module._read_file

    def racing(path, limit):
        value = original(path, limit)
        if path.name == "original.pdf":
            (directory / "blocks.json").write_bytes(b"[]")
        return value

    monkeypatch.setattr(module, "_read_file", racing)
    with pytest.raises(ValueError, match="changed"):
        service.capture(refs["table"])
    assert not service.repository.root.exists()


@pytest.mark.parametrize("escape", ["outside", "symlink"])
def test_figure_paths_cannot_escape_source_directory(etl_context, tmp_path, escape):
    service, storage, directory, refs, _ = etl_context
    manifest = storage.load_manifest(refs["figure"]["doc_id"])
    outside = tmp_path / "outside.png"
    outside.write_bytes((directory / "images/figure.png").read_bytes())
    if escape == "symlink":
        link = directory / "images/link.png"
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip("Host does not allow test symlink creation")
        manifest.assets.figures[0].path = str(link)
    else:
        manifest.assets.figures[0].path = str(outside)
    storage.save_manifest(manifest)
    with pytest.raises(ValueError, match=r"escapes|symlink"):
        service.capture(refs["figure"])
    assert not service.repository.root.exists()


def test_mixed_native_etl_csl_wiki_keeps_every_original_attachment(
    etl_context, tmp_path
):
    if not shutil.which("node"):
        pytest.skip("CSL requires optional Node.js")
    service, _, directory, refs, _ = etl_context
    captured = service.capture(refs["figure"])
    publisher = FileNativeWikiPublisher((directory.parent, service.repository.root))
    native = NativeDocumentService(
        FileNativeAssetRepository(tmp_path / "native"),
        SpreadsheetFileAdapter(),
        publisher,
    )
    workbook = _call(
        native,
        op="create",
        workbook={
            "name": "Data.xlsx",
            "edits": [{"sheet": "Sheet1", "cell": "A1", "value": "007"}],
        },
    )["asset"]
    cell = _call(
        native, op="read_cell", asset_id=workbook["asset_id"], sheet="Sheet1", cell="A1"
    )["cell"]["evidence"]
    csl = CslCitationService(
        NodeCslProcessor(), native.evidence, publisher, etl=service
    )
    raw = document().model_dump()
    raw["sources"] = {"extracted": captured["reference"], "native": cell}
    raw["clusters"][0]["cites"][0]["source_keys"] = ["extracted", "native"]
    doc = CslDocument.model_validate(raw)
    preview, _ = csl.render(doc)
    result, published = csl.render(
        doc, str(tmp_path / "wiki"), digest(canonical(preview))
    )
    assert result == preview and published["success"]
    from pathlib import Path

    root = Path(published["output_dir"])
    source = result["sources"]["extracted"]
    _, files = service.resolve(
        EtlEvidenceReference.model_validate(captured["reference"])
    )
    for name, data in files.items():
        artifact = source["snapshot_artifacts"][name]
        assert (root / artifact["name"]).read_bytes() == data
        assert hashlib.sha256(data).hexdigest() == artifact["sha256"]
    shutil.rmtree(directory)
    historical, reused = csl.render(doc, str(tmp_path / "wiki"))
    assert historical == result and reused["reused"]
    assert (
        source["verification"]["verification_scope"] == "immutable_captured_extraction"
    )
    assert source["semantic_support"] == "not_checked"
    assert any(
        "Captured evidence" in p.read_text(encoding="utf-8") for p in root.glob("*.md")
    )
    inventory = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert {p.name for p in root.iterdir()} == set(inventory["files"]) | {
        "manifest.json"
    }


@pytest.mark.parametrize("kind", ["span", "table", "figure"])
def test_inspect_returns_complete_reference_without_creating_snapshot(
    etl_context, kind
):
    service, _, _, refs, _ = etl_context
    ref = refs[kind]
    selector = EtlSourceSelector(
        doc_id=ref["doc_id"],
        source_type=kind,
        source_id=ref["span_id"] if kind == "span" else ref["asset_id"],
    )
    inspected = service.inspect(selector)
    assert (
        inspected["asset_ref"] == ref and inspected["record"]["verification"]["valid"]
    )
    assert not service.repository.root.exists()


def test_capture_checks_resource_budgets_before_writing(etl_context, monkeypatch):
    service, _, _, refs, _ = etl_context
    from src.infrastructure import etl_evidence_store

    monkeypatch.setattr(etl_evidence_store, "MAX_ETL_METADATA_BYTES", 20)
    with pytest.raises(ValueError, match="byte limit"):
        service.capture(refs["table"])
    assert not service.repository.root.exists()


def test_forged_optional_locator_and_excerpt_are_not_certified(etl_context):
    service, _, _, refs, _ = etl_context
    for change in ({"char_range": [0, 20]}, {"excerpt": "Invented value"}):
        ref = {**refs["table"], **change}
        with pytest.raises(ValueError, match="verification"):
            service.capture(ref)
    assert not service.repository.root.exists()


@pytest.mark.parametrize("blocks", [None, {}, ["text"], [None]])
def test_inspect_rejects_malformed_blocks_without_snapshot(etl_context, blocks):
    service, _, directory, refs, _ = etl_context
    (directory / "blocks.json").write_text(json.dumps(blocks), encoding="utf-8")
    ref = refs["span"]
    with pytest.raises(ValueError, match="JSON array of objects"):
        service.inspect(
            EtlSourceSelector(
                doc_id=ref["doc_id"], source_type="span", source_id=ref["span_id"]
            )
        )
    assert not service.repository.root.exists()
