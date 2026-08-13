from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

from src.application.agent_asset_bundle_format import (
    AgentAssetBundleLimitError,
    canonical_json,
)
from src.application.agent_asset_bundle_service import AgentAssetBundleService
from src.application.agent_asset_record_builder import AgentAssetRecordBuilder
from src.application.segmentation_service import SegmentationService
from src.domain.citation import build_evidence_spans
from src.domain.entities import (
    DocumentAssets,
    DocumentManifest,
    FigureAsset,
    SectionAsset,
    TableAsset,
)
from src.infrastructure.file_storage import FileStorage
from src.presentation.tools.citation_support import asset_ref_from_span
from src.presentation.tools.document_evidence_support import (
    _asset_ref_from_manifest_asset,
)


def _fixture(tmp_path: Path) -> tuple[AgentAssetBundleService, FileStorage, str]:
    repository = FileStorage(tmp_path / "data")
    doc_id = "doc_agent_bundle"
    markdown = """# Findings
Alpha finding supports the claim.

| Drug | Dose |
| --- | --- |
| A | 5 mg |

Figure 1. Treatment flow.
"""
    blocks = [
        {
            "block_id": "blk_heading",
            "block_type": "SectionHeader",
            "page": 1,
            "text": "Findings",
            "section_hierarchy": {"1": "Findings"},
            "metadata": {"line_start": 0, "line_end": 1, "source_order": 1},
        },
        {
            "block_id": "blk_text",
            "block_type": "Text",
            "page": 1,
            "text": "Alpha finding supports the claim.",
            "section_hierarchy": {"1": "Findings"},
            "metadata": {"line_start": 1, "line_end": 2, "source_order": 2},
        },
        {
            "block_id": "blk_table",
            "block_type": "Table",
            "page": 1,
            "text": "| Drug | Dose |\n| --- | --- |\n| A | 5 mg |",
            "section_hierarchy": {"1": "Findings"},
            "metadata": {"line_start": 3, "line_end": 6, "source_order": 3},
        },
        {
            "block_id": "blk_figure",
            "block_type": "Picture",
            "page": 1,
            "text": "Figure 1. Treatment flow.",
            "section_hierarchy": {"1": "Findings"},
            "metadata": {"line_start": 7, "line_end": 8, "source_order": 4},
        },
    ]
    image_path = repository.save_image(doc_id, "fig_1", b"stable-image-bytes", "png")
    manifest = DocumentManifest(
        doc_id=doc_id,
        filename="trial.pdf",
        title="Trial findings",
        source_engine="docling",
        source_pdf_sha256="f" * 64,
        selected_page_map=[1],
        page_count=1,
        assets=DocumentAssets(
            sections=[
                SectionAsset(
                    id="sec_findings",
                    title="Findings",
                    page=1,
                    start_line=0,
                    end_line=2,
                )
            ],
            tables=[
                TableAsset(
                    id="tab_1",
                    page=1,
                    caption="Dose table",
                    markdown="| Drug | Dose |\n| --- | --- |\n| A | 5 mg |",
                    preview="A: 5 mg",
                    row_count=1,
                    col_count=2,
                    source="docling",
                    source_block_id="blk_table",
                    source_order=3,
                    line_start=3,
                    line_end=6,
                    section_id="sec_findings",
                    section_title="Findings",
                )
            ],
            figures=[
                FigureAsset(
                    id="fig_1",
                    page=1,
                    path=str(image_path),
                    ext="png",
                    caption="Treatment flow",
                    width=640,
                    height=480,
                    source="docling",
                    source_block_id="blk_figure",
                    source_order=4,
                    line_start=7,
                    line_end=8,
                    section_id="sec_findings",
                    section_title="Findings",
                )
            ],
        ),
    )
    repository.save_markdown(doc_id, markdown)
    repository.save_blocks(doc_id, blocks)
    repository.save_manifest(manifest)
    repository.save_citation_index(
        doc_id,
        build_evidence_spans(
            doc_id=doc_id,
            markdown=markdown,
            blocks=blocks,
            source_backend="docling",
        ),
    )
    return (
        AgentAssetBundleService(repository, SegmentationService(repository)),
        repository,
        doc_id,
    )


async def _export(
    service: AgentAssetBundleService, doc_id: str, output_dir: str
) -> dict[str, object]:
    return await service.export(
        doc_id,
        output_dir=output_dir,
        span_ref_factory=asset_ref_from_span,
        asset_ref_factory=_asset_ref_from_manifest_asset,
    )


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    }


def _records(bundle: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (bundle / "assets.jsonl").read_text(encoding="utf-8").splitlines()
    ]


@pytest.mark.asyncio
async def test_agent_asset_bundle_is_deterministic_and_atomic(tmp_path: Path) -> None:
    service, repository, doc_id = _fixture(tmp_path)
    source_image = repository.get_doc_dir(doc_id) / "images" / "fig_1.png"
    source_before = source_image.read_bytes()

    first = await _export(service, doc_id, "bundle-one")
    first_root = Path(str(first["output_dir"]))
    first_snapshot = _snapshot(first_root)

    await _export(service, doc_id, "bundle-one")
    second = await _export(service, doc_id, "bundle-two")

    assert _snapshot(first_root) == first_snapshot
    assert _snapshot(Path(str(second["output_dir"]))) == first_snapshot
    assert source_image.read_bytes() == source_before
    assert not list(repository.get_doc_dir(doc_id).glob(".*.staging-*"))
    assert not list(repository.get_doc_dir(doc_id).glob(".*.backup-*"))


@pytest.mark.asyncio
async def test_agent_asset_bundle_rejects_traversal_and_source_directory(
    tmp_path: Path,
) -> None:
    service, repository, doc_id = _fixture(tmp_path)

    with pytest.raises(ValueError, match="must stay within"):
        await _export(service, doc_id, "../escaped")
    with pytest.raises(ValueError, match="must be a child"):
        await _export(service, doc_id, ".")
    with pytest.raises(ValueError, match="protected document artifacts"):
        await _export(service, doc_id, "images")

    assert not (repository.base_dir / "escaped").exists()
    assert (repository.get_doc_dir(doc_id) / "images" / "fig_1.png").exists()


@pytest.mark.asyncio
async def test_agent_asset_bundle_rejects_forged_marker_in_source_directory(
    tmp_path: Path,
) -> None:
    service, repository, doc_id = _fixture(tmp_path)
    images = repository.get_doc_dir(doc_id) / "images"
    source_image = images / "fig_1.png"
    source_before = source_image.read_bytes()
    (images / "manifest.json").write_text(
        json.dumps({"bundle_version": "agent-asset-bundle-v1", "doc_id": doc_id}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="protected document artifacts"):
        await _export(service, doc_id, "images")

    assert source_image.read_bytes() == source_before
    assert repository.load_manifest(doc_id) is not None
    assert not list(repository.get_doc_dir(doc_id).glob(".images.staging-*"))
    assert not list(repository.get_doc_dir(doc_id).glob(".images.backup-*"))


@pytest.mark.asyncio
async def test_agent_asset_bundle_preserves_citation_and_hash_fields(
    tmp_path: Path,
) -> None:
    service, _repository, doc_id = _fixture(tmp_path)
    result = await _export(service, doc_id, "bundle")
    root = Path(str(result["output_dir"]))
    records = _records(root)

    assert {record["asset_type"] for record in records} == {
        "text",
        "table",
        "figure",
    }
    table = next(record for record in records if record["asset_key"] == "table:tab_1")
    assert table["source_identity"]["source_sha256"] == "f" * 64
    assert table["source_identity"]["source_kind"] == "pdf"
    assert table["source_identity"]["source_media_type"] == "application/pdf"
    assert "source_pdf_sha256" not in table["source_identity"]
    assert table["locator"]["block_id"] == "blk_table"
    assert table["citation"]["asset_ref"]["source_type"] == "table"
    assert table["citation"]["asset_ref"]["locator_source_sha256"]
    evidence_ref = table["citation"]["evidence_refs"][0]
    assert evidence_ref["source_revision_id"]
    assert evidence_ref["locator_version"] == "citation-span-v1"
    assert evidence_ref["locator_source_sha256"]
    assert evidence_ref["quote_sha256"]

    figure = next(record for record in records if record["asset_key"] == "figure:fig_1")
    media_path = root / str(figure["content"]["media_path"])
    media_sha256 = hashlib.sha256(media_path.read_bytes()).hexdigest()
    assert figure["content"]["media_sha256"] == media_sha256
    assert figure["content_sha256"] == media_sha256

    for record in records:
        expected = dict(record)
        record_hash = str(expected.pop("record_sha256"))
        assert (
            hashlib.sha256(canonical_json(expected).encode()).hexdigest() == record_hash
        )

    bundle_manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert bundle_manifest["bundle_version"] == "agent-asset-bundle-v1"
    assert bundle_manifest["counts"] == {"figure": 1, "table": 1, "text": 2}
    expected_manifest = dict(bundle_manifest)
    bundle_hash = expected_manifest.pop("bundle_sha256")
    assert (
        hashlib.sha256(canonical_json(expected_manifest).encode()).hexdigest()
        == bundle_hash
    )
    artifact_paths = [item["path"] for item in bundle_manifest["artifacts"]]
    assert artifact_paths == sorted(artifact_paths)
    for artifact in bundle_manifest["artifacts"]:
        data = (root / artifact["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == artifact["sha256"]
        assert len(data) == artifact["size_bytes"]


@pytest.mark.asyncio
async def test_agent_asset_bundle_rebuilds_stale_citation_index(
    tmp_path: Path,
) -> None:
    service, repository, doc_id = _fixture(tmp_path)
    stale_revision = repository.load_citation_index(doc_id)[0].source_revision_id
    markdown = repository.load_markdown(doc_id)
    assert markdown is not None
    repository.save_markdown(doc_id, f"{markdown}\nUpdated appendix.\n")

    result = await _export(service, doc_id, "bundle")
    root = Path(str(result["output_dir"]))
    source_identity = json.loads((root / "manifest.json").read_text(encoding="utf-8"))[
        "source_identity"
    ]
    evidence_refs = [
        ref for record in _records(root) for ref in record["citation"]["evidence_refs"]
    ]

    assert evidence_refs
    assert source_identity["canonical_markdown_sha256"] != stale_revision
    assert {ref["source_revision_id"] for ref in evidence_refs} == {
        source_identity["canonical_markdown_sha256"]
    }
    assert {ref["locator_source_sha256"] for ref in evidence_refs} == {
        source_identity["locator_source_sha256"]
    }
    assert {
        span.source_revision_id for span in repository.load_citation_index(doc_id)
    } == {source_identity["canonical_markdown_sha256"]}


@pytest.mark.asyncio
async def test_agent_asset_bundle_rejects_manifest_change_during_export(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, repository, doc_id = _fixture(tmp_path)
    original_export = service.segmentation_service.export_document_segmentation
    calls = 0

    async def export_and_change_manifest(current_doc_id: str):
        nonlocal calls
        result = await original_export(current_doc_id)
        calls += 1
        if calls == 1:
            changed = repository.load_manifest(doc_id)
            assert changed is not None
            changed.source_pdf_sha256 = "e" * 64
            repository.save_manifest(changed)
        return result

    monkeypatch.setattr(
        service.segmentation_service,
        "export_document_segmentation",
        export_and_change_manifest,
    )

    with pytest.raises(ValueError, match="source artifacts changed"):
        await _export(service, doc_id, "bundle")

    assert not (repository.get_doc_dir(doc_id) / "bundle").exists()
    assert not list(repository.get_doc_dir(doc_id).glob(".bundle.staging-*"))


@pytest.mark.asyncio
async def test_agent_asset_bundle_foam_links_resolve_to_real_notes(
    tmp_path: Path,
) -> None:
    service, _repository, doc_id = _fixture(tmp_path)
    result = await _export(service, doc_id, "bundle")
    root = Path(str(result["output_dir"]))
    assert result["foam_subtree"] == {
        "portable": True,
        "root": str(root),
        "index": str(root / "index.md"),
        "notes": str(root / "notes"),
    }
    index = (root / "index.md").read_text(encoding="utf-8")
    assert "Portable Foam subtree" in index
    links = re.findall(r"\[\[([^#|]+)#\^(asset-[^|]+)\|[^]]+]]", index)

    assert links
    for note_ref, anchor in links:
        note = root / f"{note_ref}.md"
        assert note.exists()
        note_text = note.read_text(encoding="utf-8")
        assert f"^{anchor}" in note_text
        assert note_text.count("\n# ") == 1


@pytest.mark.asyncio
async def test_agent_asset_bundle_default_output_stays_in_document_dir(
    tmp_path: Path,
) -> None:
    service, repository, doc_id = _fixture(tmp_path)

    result = await service.export(
        doc_id,
        output_dir=None,
        span_ref_factory=asset_ref_from_span,
        asset_ref_factory=_asset_ref_from_manifest_asset,
    )

    assert Path(str(result["output_dir"])) == (
        repository.get_doc_dir(doc_id) / "agent-assets"
    )


@pytest.mark.asyncio
async def test_agent_asset_bundle_reports_document_not_found_without_writing(
    tmp_path: Path,
) -> None:
    repository = FileStorage(tmp_path / "data")
    service = AgentAssetBundleService(repository, SegmentationService(repository))

    result = await _export(service, "doc_missing", "bundle")

    assert result == {
        "success": False,
        "doc_id": "doc_missing",
        "error": "Document not found",
    }
    assert not (repository.base_dir / "doc_missing").exists()


@pytest.mark.asyncio
async def test_agent_asset_bundle_requires_valid_source_hash(tmp_path: Path) -> None:
    service, repository, doc_id = _fixture(tmp_path)
    manifest = repository.load_manifest(doc_id)
    assert manifest is not None
    manifest.source_pdf_sha256 = "legacy-missing-hash"
    repository.save_manifest(manifest)

    with pytest.raises(ValueError, match="valid source SHA-256"):
        await _export(service, doc_id, "bundle")

    assert not (repository.get_doc_dir(doc_id) / "bundle").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limits", "metric"),
    [
        ({"max_spans": 1}, "spans"),
        ({"max_records": 2}, "records"),
        ({"max_output_bytes": 8}, "output_bytes"),
    ],
)
async def test_agent_asset_bundle_fails_closed_on_explicit_resource_limits(
    tmp_path: Path,
    limits: dict[str, int],
    metric: str,
) -> None:
    _service, repository, doc_id = _fixture(tmp_path)
    service = AgentAssetBundleService(
        repository,
        SegmentationService(repository),
        **limits,
    )

    with pytest.raises(
        AgentAssetBundleLimitError,
        match=rf"bundle {metric} limit exceeded",
    ):
        await _export(service, doc_id, "bounded-bundle")

    assert not (repository.get_doc_dir(doc_id) / "bounded-bundle").exists()
    assert not list(repository.get_doc_dir(doc_id).glob(".bounded-bundle.staging-*"))


def test_agent_asset_evidence_index_performs_one_linear_span_scan() -> None:
    accesses = {"block_id": 0, "asset_id": 0}

    class CountingSpan:
        def __init__(self, index: int) -> None:
            self.index = index
            self.span_id = f"span_{index}"

        @property
        def block_id(self) -> str:
            accesses["block_id"] += 1
            return f"block_{self.index}"

        @property
        def asset_id(self) -> str:
            accesses["asset_id"] += 1
            return f"asset_{self.index}"

    spans = [CountingSpan(index) for index in range(200)]
    builder = AgentAssetRecordBuilder(
        lambda span: {"span_id": span.span_id},
        lambda *_args: {},
    )

    evidence_index = builder._index_evidence(spans)
    refs = [
        builder._evidence_refs(evidence_index, f"block_{index}", f"asset_{index}")
        for index in range(len(spans))
    ]

    assert accesses == {"block_id": len(spans), "asset_id": len(spans)}
    assert refs[0] == [{"span_id": "span_0"}]
    assert refs[-1] == [{"span_id": "span_199"}]


@pytest.mark.asyncio
async def test_agent_asset_bundle_rejects_figure_source_change_during_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, repository, doc_id = _fixture(tmp_path)
    source = (repository.get_doc_dir(doc_id) / "images" / "fig_1.png").resolve()
    real_open = Path.open
    mutated = False

    class RacingReader:
        def __init__(self, handle: Any) -> None:
            self.handle = handle

        def __enter__(self) -> RacingReader:
            self.handle.__enter__()
            return self

        def __exit__(self, *args: object) -> object:
            return self.handle.__exit__(*args)

        def fileno(self) -> int:
            return self.handle.fileno()

        def read(self, size: int = -1) -> bytes:
            nonlocal mutated
            data = self.handle.read(size)
            if data and not mutated:
                mutated = True
                with real_open(source, "wb") as writer:
                    writer.write(b"changed-while-copying")
            return data

    def racing_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        handle = real_open(path, *args, **kwargs)
        mode = str(args[0] if args else kwargs.get("mode", "r"))
        if path.resolve() == source and mode == "rb":
            return RacingReader(handle)
        return handle

    monkeypatch.setattr(Path, "open", racing_open)

    with pytest.raises(ValueError, match="Figure source changed during"):
        await _export(service, doc_id, "racing-bundle")

    assert mutated is True
    assert not (repository.get_doc_dir(doc_id) / "racing-bundle").exists()
    assert not list(repository.get_doc_dir(doc_id).glob(".racing-bundle.staging-*"))


@pytest.mark.asyncio
async def test_document_facade_dispatches_export_assets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.presentation.tools import document_tools

    captured: dict[str, object] = {}

    class FakeExporter:
        def __init__(self, repository: object, segmentation_service: object) -> None:
            captured["repository"] = repository
            captured["segmentation_service"] = segmentation_service

        async def export(self, doc_id: str, **kwargs: object) -> dict[str, object]:
            captured.update({"doc_id": doc_id, **kwargs})
            return {"success": True, "operation": "export_assets"}

    monkeypatch.setattr(document_tools, "AgentAssetBundleService", FakeExporter)
    result = await document_tools.document(
        "export_assets", doc_id="doc_facade", output_dir="agent-assets"
    )

    assert result == {"success": True, "operation": "export_assets"}
    assert captured["doc_id"] == "doc_facade"
    assert captured["output_dir"] == "agent-assets"
    assert captured["span_ref_factory"] is document_tools.asset_ref_from_span
    assert (
        captured["asset_ref_factory"] is document_tools._asset_ref_from_manifest_asset
    )
