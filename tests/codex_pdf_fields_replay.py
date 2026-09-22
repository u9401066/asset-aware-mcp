"""Replay audited real-form mutations through an installed native document service."""

import argparse
import json
import shutil
import sys
from pathlib import Path

import src
from src.application.native_document_service import NativeDocumentService
from src.domain.native_assets import NativeDocumentRequest
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_pdf import NativePdf
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.codex_native_pdf.artifacts import load_asset, read_json
from tests.codex_native_pdf.trace import canonical, digest, payload
from tests.codex_pdf.trace import require
from tests.codex_pdf_fields_audit import calls_from
from tests.codex_pdf_fields_checks import check_states


def remap(value, old, new):
    if isinstance(value, dict):
        return {
            key: new if key == "asset_id" and item == old else remap(item, old, new)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [remap(item, old, new) for item in value]
    return value


def invoke(service, **request):
    result = service.execute(NativeDocumentRequest.model_validate(request))
    require(result.get("success", True), f"Operation failed: {result}")
    return result


def complete(service, **request):
    chunks, offset, sha = [], 0, None
    while True:
        result = invoke(
            service,
            **request,
            text_offset=offset,
            text_limit=4000,
            **({"pdf_field_text_sha256": sha} if sha else {}),
        )
        sha = sha or result["text_sha256"]
        start, end = result["excerpt_char_range"]
        require(
            sha == result["text_sha256"]
            and start == offset
            and end - start == len(result["text_excerpt"]),
            "Incomplete field read",
        )
        chunks.append(result["text_excerpt"])
        offset = result["next_text_offset"]
        if offset is None:
            break
        require(offset == end and end > start, "Nonprogressing continuation")
    text = "".join(chunks)
    require(
        len(text) == result["text_length"] and digest(text.encode()) == sha,
        "Read hash differs",
    )
    return json.loads(text)


def replay(trace, output):
    require(
        read_json(trace / "audit.json")["passed"],
        "Trace must pass independent audit first",
    )
    expected = load_asset(
        trace / "workspace", read_json(trace / "last-message.txt")["pdf_asset_id"]
    )
    old_id = expected["asset_id"]
    old_root = trace / "workspace/data/native-assets" / old_id
    original = trace / "workspace/source.pdf"
    original_state = (digest(original.read_bytes()), original.stat().st_mtime_ns)
    output.mkdir(parents=True, exist_ok=False)
    source = output / "source.pdf"
    shutil.copy2(original, source)
    repository = FileNativeAssetRepository(output / "store")
    service = NativeDocumentService(
        repository,
        SpreadsheetFileAdapter(),
        FileNativeWikiPublisher((output / "store",)),
        pdfs=NativePdf(),
    )
    current = invoke(service, op="register", source_path=str(source))["asset"]
    new_id = current["asset_id"]
    calls = calls_from(
        [json.loads(line) for line in (trace / "events.jsonl").read_text().splitlines()]
    )
    edits = [
        call
        for call in calls
        if call["arguments"]["native_request"]["op"] == "update_pdf_fields"
    ]
    require(
        len(edits) == len(expected["history"]) - 1 == 3, "Expected three real mutations"
    )
    snapshots, historical, observations = [], [], []
    for index in range(len(edits) + 1):
        entry = expected["history"][index]
        require(current["revision"] == entry["sha256"], "Managed revision differs")
        raw = repository.read(new_id, current["revision"])
        require(
            raw == (old_root / "revisions" / entry["sha256"]).read_bytes(),
            "Native bytes differ",
        )
        snapshots.append(raw)
        request = {"asset_id": new_id, "revision": current["revision"]}
        catalog = complete(service, op="read_pdf_fields", **request)
        receipt = remap(entry.get("result"), old_id, new_id)
        require(
            catalog["operation_result"] == receipt, "Complete managed receipt differs"
        )
        for field in catalog["catalog"]["fields"]:
            record = complete(
                service,
                op="read_pdf_field",
                **request,
                pdf_field_locator=field["locator"],
            )["field"]
            require(
                invoke(service, op="verify", reference=record["evidence"])["valid"],
                "Field verification failed",
            )
            historical.append((request, record))
        observations.append(
            {
                "revision": current["revision"],
                "field_count": len(catalog["catalog"]["fields"]),
                "exact_pdf_and_receipt": True,
            }
        )
        if index < len(edits):
            args = remap(edits[index]["arguments"]["native_request"], old_id, new_id)
            result = invoke(service, **args)
            require(
                result["asset"]["revision"]
                == payload(edits[index])["asset"]["revision"],
                "Mutation result differs",
            )
            current = result["asset"]
    check_states(snapshots)
    for request, record in historical:
        require(
            complete(
                service,
                op="read_pdf_field",
                **request,
                pdf_field_locator=record["locator"],
            )["field"]
            == record,
            "Historical field changed",
        )
    exported = invoke(
        service,
        op="export_wiki",
        asset_id=new_id,
        revision=current["revision"],
        output_dir=str(output / "wiki"),
        citation_contract={
            "name": "fields",
            "inline_template": "Field [{locator}]",
            "reference_template": "{title} | {locator}",
        },
    )
    directory = Path(exported["output_dir"])
    manifest = read_json(directory / "manifest.json")
    require(
        manifest["projection"].startswith("pdf-fields-v1:"),
        "Wrong field Wiki projection",
    )
    require(
        (directory / manifest["source_attachment"]).read_bytes() == snapshots[-1],
        "Wiki PDF differs",
    )
    require(
        read_json(directory / manifest["operation_result_file"]) == receipt,
        "Wiki receipt differs",
    )
    records = [
        json.loads(line)
        for line in (directory / manifest["field_records"]).read_text().splitlines()
    ]
    require(
        manifest["field_count"] == len(records) == observations[-1]["field_count"],
        "Missing Wiki fields",
    )
    for record in records:
        full = complete(
            service,
            op="read_pdf_field",
            asset_id=new_id,
            revision=current["revision"],
            pdf_field_locator=record["locator"],
        )["field"]
        require({key: record[key] for key in full} == full, "Wiki field differs")
        require(
            record["citation_presentation"]["inline"].startswith(
                "Field [PDF field path"
            ),
            "Custom citation missing",
        )
    for path in [original, source]:
        require(
            (digest(path.read_bytes()), path.stat().st_mtime_ns) == original_state,
            "Source changed",
        )
    return {
        "passed": True,
        "revisions": observations,
        "historical_field_records": len(historical),
        "wiki_fields": len(records),
        "source_unchanged": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--installed-dir", type=Path, required=True)
    args = parser.parse_args()
    installed = Path(src.__file__).resolve().parent
    require(
        installed == args.installed_dir.resolve(),
        "Runtime came from the wrong installation",
    )
    actual = {
        str(p.relative_to(installed)): digest(p.read_bytes())
        for p in sorted(installed.rglob("*.py"))
    }
    require(
        actual == read_json(args.manifest),
        "Installed source differs from verified checkout",
    )
    report = replay(args.trace, args.output)
    report.update(
        installed_source=str(installed), source_files=len(actual), python=sys.version
    )
    (args.output / "replay.json").write_bytes(canonical(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
