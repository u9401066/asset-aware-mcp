from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

RETIRED_RASTER_ROOTS = (
    ROOT / "docs" / "diagrams",
    ROOT / "docs" / "images",
    ROOT / "docs" / "wiki" / "assets",
)

RETIRED_PUBLIC_REFERENCES = (
    "overview-architecture.jpg",
    "mcp-endpoint-map.jpg",
    "pdf-document-workflow.jpg",
    "architecture-overview.jpg",
    "01-system-architecture.jpg",
    "02-data-layout.jpg",
    "03-pdf-ingestion-pipeline.jpg",
    "04-docx-edit-pipeline.jpg",
    "05-knowledge-graph-search.jpg",
    "06-installation-steps.jpg",
    "07-pdf-etl-pipeline.jpg",
    "08-knowledge-graph-architecture.jpg",
    "09-agent-harness-concept.jpg",
)

PRIVATE_OR_STALE_TOPOLOGY = (
    "192.168.1.2:30133",
    "/home/eric/",
    "Telegram → Gateway",
    "62 tools in 7 categories",
)

RETIRED_PUBLIC_CONTRACTS = (
    "`document://{doc_id}/blocks`",
    "`table://{table_id}/preview`",
    "只是偏好 Marker",
)


def _public_text_sources() -> list[Path]:
    sources = [
        ROOT / "README.md",
        ROOT / "README.zh-TW.md",
        ROOT / "docs" / "index.html",
        ROOT / "docs" / "site.js",
        ROOT / "docs" / "site.css",
        ROOT / "scripts" / "build_docs_site.py",
    ]
    sources.extend(sorted((ROOT / "docs" / "wiki").glob("*.md")))
    sources.extend(sorted((ROOT / "docs" / "site-content").glob("*.md")))
    return sources


def test_obsolete_public_document_rasters_stay_retired() -> None:
    remaining = [
        str(path.relative_to(ROOT))
        for root in RETIRED_RASTER_ROOTS
        if root.exists()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
    ]
    assert remaining == []


def test_public_document_sources_do_not_restore_stale_images_or_private_topology() -> (
    None
):
    violations: list[str] = []
    for path in _public_text_sources():
        text = path.read_text(encoding="utf-8")
        for needle in (
            *RETIRED_PUBLIC_REFERENCES,
            *PRIVATE_OR_STALE_TOPOLOGY,
            *RETIRED_PUBLIC_CONTRACTS,
        ):
            if needle in text:
                violations.append(f"{path.relative_to(ROOT)}: {needle}")

    assert violations == []


def test_public_citation_docs_explain_bounded_preview_contract() -> None:
    tool_catalog = (ROOT / "docs" / "wiki" / "MCP-Tools.md").read_text(encoding="utf-8")
    provenance = (ROOT / "docs" / "wiki" / "Citation-Provenance.md").read_text(
        encoding="utf-8"
    )

    assert "超過 1,000 字元" in tool_catalog
    assert "asset-ref-preview-v1" in provenance
    assert "canonical_asset_ref=false" in provenance
    assert "不能拿去 verify" in provenance
