"""Round-trip test: ingest → no edits → save → validate."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.application.docx_service import DocxService
from src.infrastructure.file_storage import FileStorage

DOCX = Path(
    r"D:\workspace260210"
    r"\特色發展計畫申請表(新案)-氣道AI_20260220 v2 (待修正).docx"
)


async def main() -> None:
    repo = FileStorage()
    svc = DocxService(repo)

    # 1. Ingest
    print("=== STEP 1: Ingest ===")
    result = await svc.ingest_docx(str(DOCX))
    if not result.get("success"):
        print(f"FAIL: {result}")
        return
    doc_id = result["doc_id"]
    print(f"  doc_id:    {doc_id}")
    print(f"  blocks:    {result.get('total_blocks')}")
    print(f"  editable:  {result.get('editable_blocks')}")
    print(f"  protected: {result.get('protected_blocks')}")
    print(f"  integrity: {result.get('integrity')}")
    print()

    # 2. Save without edits (pure round-trip)
    print("=== STEP 2: Save (no edits, round-trip) ===")
    doc_dir = repo.get_doc_dir(doc_id)
    output = str(doc_dir / "roundtrip_output.docx")
    save_result = await svc.save_docx(doc_id, output_path=output, from_md=True)
    print(f"  success:   {save_result.get('success')}")
    print(f"  output:    {save_result.get('output_path')}")
    print(f"  integrity: {save_result.get('integrity')}")
    if save_result.get("warnings"):
        for w in save_result["warnings"]:
            print(f"  warn: {w}")
    print()

    # 3. Detailed file-level validation
    print("=== STEP 3: Detailed Validation ===")
    from src.infrastructure.docx_validator import DocxValidator

    validator = DocxValidator()
    original = doc_dir / "original.docx"
    rebuilt = Path(output)
    report = validator.validate(original, rebuilt)
    print(report.to_markdown())


if __name__ == "__main__":
    asyncio.run(main())
