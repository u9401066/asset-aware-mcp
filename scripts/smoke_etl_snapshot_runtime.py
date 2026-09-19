"""Replay retained actual ETL evidence with the installed runtime, outside checkout.

Input is the workspace from tests.codex_etl_csl.run. Writes only to a fresh temporary
Wiki; source snapshots/native revisions are read-only and their bytes stay intact.
"""

import argparse
import hashlib
import io
import json
import tempfile
from pathlib import Path

import pymupdf
from PIL import Image, ImageChops

import src
from src.application.csl_citation_service import CslCitationService, canonical
from src.application.etl_evidence_service import EtlEvidenceService
from src.application.native_evidence_service import NativeEvidenceService
from src.domain.csl_citations import CslDocument
from src.domain.etl_evidence import EtlEvidenceReference
from src.infrastructure.csl_processor import NodeCslProcessor
from src.infrastructure.etl_evidence_store import (
    FileEtlSnapshotRepository,
    FileEtlSourceReader,
)
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_pdf import NativePdf
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    files = list((workspace / "citation-wiki").glob("*/citations.json"))
    assert len(files) == 1
    expected_bytes = files[0].read_bytes()
    expected = json.loads(expected_bytes)
    etl = EtlEvidenceService(
        FileEtlSourceReader(workspace / "absent-extraction"),
        FileEtlSnapshotRepository(workspace / "data/citation-sources"),
        NativePdf(),
    )
    images = 0
    for source in expected["sources"].values():
        if source["reference"]["schema_version"] != "etl-citation-ref-v1":
            continue
        reference = EtlEvidenceReference.model_validate(source["reference"])
        assert not (workspace / "data" / reference.doc_id).exists()
        read = etl.read(reference)
        assert read["record"] == source["evidence_record"]
        record, snapshot = etl.resolve(reference)
        image = etl.view(reference, 640)
        with pymupdf.open(stream=snapshot["original.pdf"], filetype="pdf") as pdf:
            page = pdf[record["source_reference"]["page"] - 1]
            scale = 640 / max(page.rect.width, page.rect.height)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        actual = Image.open(io.BytesIO(image["image_png"])).convert("RGB")
        truth = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        assert actual.size == truth.size
        assert ImageChops.difference(actual, truth).getbbox() is None
        images += 1
    assert images == 3
    evidence = NativeEvidenceService(
        FileNativeAssetRepository(workspace / "data/native-assets"),
        SpreadsheetFileAdapter(),
    )
    service = CslCitationService(
        NodeCslProcessor(), evidence, FileNativeWikiPublisher(), etl=etl
    )
    with tempfile.TemporaryDirectory(prefix="etl-snapshot-runtime-") as output:
        rendered, publication = service.render(
            CslDocument.model_validate(expected["document"]),
            output,
            hashlib.sha256(expected_bytes).hexdigest(),
        )
        assert canonical(rendered) == expected_bytes and publication["success"]
        root = Path(publication["output_dir"])
        assert {p.name: p.read_bytes() for p in root.iterdir()} == {
            p.name: p.read_bytes() for p in files[0].parent.iterdir()
        }
    source_root = Path(src.__file__).parent
    fingerprint = hashlib.sha256(
        "\n".join(
            f"src/{p.relative_to(source_root).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}"
            for p in sorted(source_root.rglob("*.py"))
        ).encode()
    ).hexdigest()
    print(
        json.dumps(
            {
                "passed": True,
                "source_path": str(source_root),
                "source_sha256": fingerprint,
                "historical_images": images,
                "exact_citation_and_wiki_replay": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
