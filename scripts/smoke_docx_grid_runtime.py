"""Replay retained Codex grid records/Wiki with the installed runtime, no tests imports."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

import src
from src.application.native_document_service import NativeDocumentService
from src.application.native_docx_bridge import NativeDocxBridge
from src.domain.native_assets import NativeDocumentRequest
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_docx_structure import NativeDocxStructure
from src.infrastructure.native_docx_workspace import FileNativeDocxWorkspaces
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--table-revisions", type=int, default=3)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    output = workspace.parent
    expected = json.loads((output / "expected.json").read_text(encoding="utf-8"))
    final = json.loads((output / "last-message.txt").read_text(encoding="utf-8"))
    service = NativeDocumentService(
        FileNativeAssetRepository(workspace / "data/native-assets"),
        SpreadsheetFileAdapter(),
        wiki_publisher=FileNativeWikiPublisher(),
        docx=NativeDocxBridge(FileNativeDocxWorkspaces()),
        docx_structure=NativeDocxStructure(),
    )
    snapshots = {}
    for line in (output / "events.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        item = event.get("item", {})
        if event["type"] != "item.completed" or item.get("type") != "mcp_tool_call":
            continue
        fields = item["arguments"].get("native_request", {})
        if fields.get("op") != "read_docx_table":
            continue
        content = "".join(
            b.get("text", "") for b in item["result"]["content"] if b["type"] == "text"
        )
        result = json.loads(content)
        result = result.get("result", result)
        if not result.get("success"):
            continue
        page = result["table"]
        snapshots[fields["revision"]] = (
            fields["docx_table_reference"],
            page["text_sha256"],
        )
    assert len(snapshots) == args.table_revisions
    for revision, (reference, digest) in snapshots.items():
        chunks, offset = [], 0
        while True:
            result = service.execute(
                NativeDocumentRequest.model_validate(
                    {
                        "op": "read_docx_table",
                        "asset_id": final["docx_asset_id"],
                        "revision": revision,
                        "docx_table_reference": reference,
                        "text_offset": offset,
                        "text_limit": 4000,
                    }
                )
            )
            page = result["table"]
            assert page["text_sha256"] == digest
            chunks.append(page["text_excerpt"])
            offset = page["next_text_offset"]
            if offset is None:
                break
        assert hashlib.sha256("".join(chunks).encode()).hexdigest() == digest
        assert service.execute(
            NativeDocumentRequest.model_validate(
                {"op": "verify", "reference": reference}
            )
        )["valid"]
    with tempfile.TemporaryDirectory(prefix="docx-grid-runtime-") as root:
        result = service.execute(
            NativeDocumentRequest.model_validate(
                {
                    "op": "export_wiki",
                    "asset_id": final["docx_asset_id"],
                    "output_dir": root,
                }
            )
        )
        new = Path(result["output_dir"])
        old = next(
            p.parent
            for p in (workspace / "native-wiki").rglob("manifest.json")
            if json.loads(p.read_text(encoding="utf-8")).get("asset_id")
            == final["docx_asset_id"]
            and json.loads(p.read_text(encoding="utf-8")).get("revision")
            == service.repository.load(final["docx_asset_id"]).revision
        )
        assert {
            p.relative_to(new).as_posix(): p.read_bytes()
            for p in new.rglob("*")
            if p.is_file()
        } == {
            p.relative_to(old).as_posix(): p.read_bytes()
            for p in old.rglob("*")
            if p.is_file()
        }
    source_root = Path(src.__file__).parent
    fingerprint = hashlib.sha256(
        "\n".join(
            f"src/{p.relative_to(source_root).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}"
            for p in sorted(source_root.rglob("*.py"))
        ).encode()
    ).hexdigest()
    assert fingerprint == expected["server_source_sha256"]
    print(
        json.dumps(
            {
                "passed": True,
                "source_path": str(source_root),
                "source_sha256": fingerprint,
                "complete_table_revisions": len(snapshots),
                "exact_wiki_replay": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
