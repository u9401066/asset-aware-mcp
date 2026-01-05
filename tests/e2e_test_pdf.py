"""
End-to-end test: Ingest a real PDF and verify the pipeline.
"""

import asyncio
from pathlib import Path

from src.application.document_service import DocumentService
from src.infrastructure.config import settings
from src.infrastructure.file_storage import FileStorage
from src.infrastructure.pdf_extractor import PyMuPDFExtractor


async def test_ingest_real_pdf():
    """Test ingesting a real PDF file."""

    # Setup
    pdf_path = Path("data/samples/attention_is_all_you_need.pdf")

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return

    print(f"📄 Testing with: {pdf_path.name}")
    print(f"   Size: {pdf_path.stat().st_size / 1024:.1f} KB")

    # Initialize services
    repository = FileStorage(base_dir=settings.data_dir)
    pdf_extractor = PyMuPDFExtractor()

    service = DocumentService(
        repository=repository,
        pdf_extractor=pdf_extractor,
        knowledge_graph=None,  # Skip LightRAG for quick test
    )

    # Ingest
    print("\n🔄 Ingesting PDF...")
    results = await service.ingest([str(pdf_path)])

    result = results[0]

    if not result.success:
        print(f"❌ Ingest failed: {result.error}")
        return

    print("✅ Ingest successful!")
    print(f"   doc_id: {result.doc_id}")
    print(f"   title: {result.title}")
    print(f"   pages: {result.pages_processed}")
    print(f"   tables: {result.tables_found}")
    print(f"   figures: {result.figures_found}")
    print(f"   sections: {result.sections_found}")
    print(f"   time: {result.processing_time_seconds:.2f}s")

    # Load manifest
    print("\n📋 Loading Manifest...")
    manifest = await service.get_manifest(result.doc_id)

    if manifest:
        print(f"   TOC: {manifest.toc[:5]}...")

        if manifest.assets.tables:
            print("\n   📊 Tables:")
            for t in manifest.assets.tables[:3]:
                print(f"      - {t.id} (page {t.page}): {t.preview[:50]}...")

        if manifest.assets.figures:
            print("\n   🖼️ Figures:")
            for f in manifest.assets.figures[:5]:
                print(f"      - {f.id} (page {f.page}): {f.width}x{f.height}")

        if manifest.assets.sections:
            print("\n   📑 Sections:")
            for s in manifest.assets.sections[:5]:
                print(f"      - [{s.level}] {s.title}")

    print("\n✅ Test complete!")
    print(f"   Data saved to: {settings.data_dir / result.doc_id}")


if __name__ == "__main__":
    asyncio.run(test_ingest_real_pdf())
