"""Replay retained story records and both Wikis using installed code, no tests imports."""

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
from src.infrastructure.native_docx_stories import NativeDocxStories
from src.infrastructure.native_docx_workspace import FileNativeDocxWorkspaces
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    workspace = parser.parse_args().workspace.resolve()
    output = workspace.parent
    expected = json.loads((output / "expected.json").read_text(encoding="utf-8"))
    final = json.loads((output / "last-message.txt").read_text(encoding="utf-8"))
    service = NativeDocumentService(
        FileNativeAssetRepository(workspace / "data/native-assets"),
        SpreadsheetFileAdapter(),
        wiki_publisher=FileNativeWikiPublisher(),
        docx=NativeDocxBridge(FileNativeDocxWorkspaces()),
        docx_stories=NativeDocxStories(),
    )
    snapshots = {}
    for line in (output / "events.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        item = event.get("item", {})
        if event["type"] != "item.completed" or item.get("type") != "mcp_tool_call":
            continue
        fields = item["arguments"].get("native_request", {})
        if fields.get("op") not in {
            "read_docx_story",
            "read_docx_stories",
            "read_docx_story_structure",
        }:
            continue
        content = "".join(
            b.get("text", "")
            for b in (item.get("result") or {}).get("content", [])
            if b["type"] == "text"
        )
        if not content:
            continue
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            continue
        result = result.get("result", result)
        if not result.get("success"):
            continue
        key = (
            "story_structure"
            if fields["op"] == "read_docx_story_structure"
            else "story"
        )
        snapshots[fields["op"], fields["revision"], fields.get("docx_story_part")] = (
            result[key]["text_sha256"]
        )
    story_keys = {key for key in snapshots if key[0] == "read_docx_story"}
    assert len(story_keys) >= 8
    for (op, revision, part), digest in snapshots.items():
        chunks, offset = [], 0
        fields = {"op": op, "asset_id": final["docx_asset_id"], "revision": revision}
        if part:
            fields["docx_story_part"] = part
        while True:
            result = service.execute(
                NativeDocumentRequest.model_validate(
                    {**fields, "text_offset": offset, "text_limit": 4000}
                )
            )
            key = "story_structure" if op == "read_docx_story_structure" else "story"
            page = result[key]
            assert page["text_sha256"] == digest
            chunks.append(page["text_excerpt"])
            offset = page["next_text_offset"]
            if offset is None:
                break
        text = "".join(chunks)
        assert hashlib.sha256(text.encode()).hexdigest() == digest
        if part:
            reference = json.loads(text)["evidence"]
            assert service.execute(
                NativeDocumentRequest.model_validate(
                    {"op": "verify", "reference": reference}
                )
            )["valid"]
    manifests = list((workspace / "native-wiki").rglob("manifest.json"))
    assert len(manifests) == 2
    for path in manifests:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="docx-story-runtime-") as root:
            result = service.execute(
                NativeDocumentRequest.model_validate(
                    {
                        "op": "export_wiki",
                        "asset_id": final["docx_asset_id"],
                        "revision": manifest["revision"],
                        "output_dir": root,
                        "citation_contract": manifest["citation_contract"],
                        "citation_metadata": manifest["citation_metadata"],
                    }
                )
            )
            new, old = Path(result["output_dir"]), path.parent
            assert {
                p.relative_to(new): p.read_bytes()
                for p in new.rglob("*")
                if p.is_file()
            } == {
                p.relative_to(old): p.read_bytes()
                for p in old.rglob("*")
                if p.is_file()
            }
    source = Path(src.__file__).parent
    fingerprint = hashlib.sha256(
        "\n".join(
            f"src/{p.relative_to(source).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}"
            for p in sorted(source.rglob("*.py"))
        ).encode()
    ).hexdigest()
    assert fingerprint == expected["server_source_sha256"]
    print(
        json.dumps(
            {
                "passed": True,
                "source_path": str(source),
                "source_sha256": fingerprint,
                "complete_story_records": len(story_keys),
                "complete_catalogs": len(snapshots) - len(story_keys),
                "exact_historical_wikis": len(manifests),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
