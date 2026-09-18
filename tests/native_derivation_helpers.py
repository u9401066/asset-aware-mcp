"""Native provenance fixtures use real files and the production repository/adapters."""

import hashlib
import json

from src.application.native_document_service import NativeDocumentService
from src.application.native_docx_bridge import NativeDocxBridge
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_derivation_store import FileNativeDerivationRepository
from src.infrastructure.native_docx_workspace import FileNativeDocxWorkspaces
from src.infrastructure.native_pdf import NativePdf
from src.infrastructure.native_pptx import NativePresentation
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_workbook_helpers import _call


def service_at(tmp_path):
    root = tmp_path / "store"
    assets = FileNativeAssetRepository(root)
    return NativeDocumentService(
        assets,
        SpreadsheetFileAdapter(),
        FileNativeWikiPublisher((root,)),
        NativeDocxBridge(FileNativeDocxWorkspaces()),
        NativePresentation(),
        NativePdf(),
        FileNativeDerivationRepository(root, assets),
    )


def pair(service):
    source = service.repository.create(
        "source.bin", b"source content", "bin", "application/octet-stream"
    )
    target = _call(
        service,
        op="create",
        workbook={"edits": [{"sheet": "Sheet1", "cell": "A1", "value": "007"}]},
    )["asset"]
    ref = _call(
        service, op="read_cell", asset_id=target["asset_id"], sheet="Sheet1", cell="A1"
    )["cell"]["evidence"]
    source_ref = _call(service, op="inspect", asset_id=source.asset_id)["asset"][
        "file_reference"
    ]
    return target, {
        "target": ref,
        "sources": [source_ref],
        "agent": "test agent",
        "activity": "Transcribe displayed count",
        "review": {"semantic_accuracy": "passed", "notes": "Caller assertion only"},
    }


def read_ledger(service, asset_id, text_limit=4000):
    chunks, offset, sha = [], 0, None
    while True:
        args = {"derivations_sha256": sha} if sha else {}
        result = _call(
            service,
            op="read_derivations",
            asset_id=asset_id,
            text_offset=offset,
            text_limit=text_limit,
            **args,
        )
        sha = sha or result["derivations_sha256"]
        assert result["derivations_sha256"] == sha
        chunks.append(result["text_excerpt"])
        if result["next_text_offset"] is None:
            break
        offset = result["next_text_offset"]
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == sha
    return json.loads(text), sha


def record(service, asset, claim, expected=None):
    if expected is None:
        _, expected = read_ledger(service, asset["asset_id"])
    return _call(
        service,
        op="record_derivation",
        asset_id=asset["asset_id"],
        expected_derivations_sha256=expected,
        derivation=claim,
    )
