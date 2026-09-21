import json
import shutil
from pathlib import Path

import pytest

from src.application.csl_citation_service import CslCitationService
from src.domain.csl_citations import CslDocument
from src.infrastructure.csl_processor import NodeCslProcessor
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_derivation_helpers import pair, record
from tests.native_image_service_helpers import frame, update
from tests.native_workbook_helpers import _call
from tests.unit.test_csl_processor import document
from tests.unit.test_native_image_service import managed_image as _managed_image
from tests.unit.test_native_image_wiki import export

managed_image = _managed_image


def test_frame_region_and_selection_derivations_export_complete_raster_evidence(
    managed_image, tmp_path
):
    service, asset, source = managed_image
    reference = frame(service, asset)["evidence"]
    region = _call(
        service,
        op="read_image_region",
        reference=reference,
        image_region={"rect": [0.1, 0.1, 0.6, 0.7]},
    )["reference"]
    selected = _call(
        service,
        op="read_selection",
        reference=region,
        selection={"pointer": "/source_pixel_bounds"},
    )["evidence"]
    workbook, claim = pair(service)
    claim["sources"] = [reference, region, selected]
    claim["review"] = {"notes": "Synthetic fixture; semantic accuracy not reviewed"}
    created = record(service, workbook, claim)
    root, manifest = export(
        service,
        workbook,
        tmp_path / "wiki",
        citation_metadata={"authors": "Target author", "year": "2026"},
    )
    extra = manifest["derivations"]
    assert len(extra["image_records"]) == 2
    assert len(extra["selection_records"]) == 1
    original = {p.name: p.read_bytes() for p in root.iterdir()}
    for item in extra["image_records"].values():
        saved = json.loads((root / item["record_file"]).read_text())
        assert saved["evidence"] in (reference, region)
        assert saved["citation_metadata"].get("authors") != "Target author"
        assert (root / saved["source_attachment"]).read_bytes() == source.read_bytes()
        assert (root / item["preview_attachment"]).read_bytes().startswith(b"\x89PNG")
    candidate = _call(
        service,
        op="create_image",
        image_create={
            "name": "new.png",
            "width": 2,
            "height": 2,
            "rgba": [0, 0, 0, 255],
        },
    )["asset"]
    after = frame(service, candidate)["evidence"]
    update(
        service,
        asset,
        candidate,
        [
            {
                "op": "map",
                "before": reference,
                "after": after,
                "pixels": "replace",
                "metadata": "replace",
            }
        ],
    )
    verified = _call(
        service,
        op="verify_derivation",
        asset_id=workbook["asset_id"],
        derivation_id=created["derivation_id"],
    )
    assert verified["references_valid"] and verified["active"]
    reused, _ = export(
        service,
        workbook,
        tmp_path / "wiki",
        citation_metadata={"authors": "Target author", "year": "2026"},
    )
    assert reused == root and original == {
        p.name: p.read_bytes() for p in root.iterdir()
    }


def test_csl_image_references_retain_exact_historical_source(managed_image, tmp_path):
    if not shutil.which("node"):
        pytest.skip("CSL requires optional Node.js")
    service, asset, source = managed_image
    reference = frame(service, asset)["evidence"]
    region = _call(
        service,
        op="read_image_region",
        reference=reference,
        image_region={"rect": [0.0, 0.0, 1.0, 1.0]},
    )["reference"]
    raw = document().model_dump()
    raw["sources"] = {"frame": reference, "region": region}
    raw["clusters"][0]["cites"][0]["source_keys"] = ["frame", "region"]
    csl = CslCitationService(
        NodeCslProcessor(), service.evidence, FileNativeWikiPublisher()
    )
    result, published = csl.render(
        CslDocument.model_validate(raw), str(tmp_path / "citations")
    )
    root = Path(published["output_dir"])
    for key, ref in (("frame", reference), ("region", region)):
        record = result["sources"][key]
        assert (
            record["reference"] == ref and record["semantic_support"] == "not_checked"
        )
        assert (root / record["attachment"]["name"]).read_bytes() == source.read_bytes()
