"""
MCP Tools Integration Test

測試 MCP Server 的所有工具是否正常運作。
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.presentation.server import mcp
from src.presentation.tools.document_tools import ingest_documents, list_documents
from src.presentation.tools.job_tools import cancel_job, get_job_status, list_jobs


async def test_job_system():
    """測試 Job System 工具。"""
    print("=" * 60)
    print("🧪 Testing Job System")
    print("=" * 60)

    # 1. Test list_jobs (empty)
    print("\n📋 1. Testing list_jobs (should be empty or have old jobs)...")
    result = await list_jobs(active_only=False)
    print(
        f"   Result: {result[:200]}..." if len(result) > 200 else f"   Result: {result}"
    )

    # 2. Test ingest_documents with async mode (non-existent file to test job creation)
    print("\n📄 2. Testing ingest_documents (async mode)...")
    # Use a test file path - will fail but should create a job
    test_file = "/tmp/test_document.pdf"  # noqa: S108 — test-only temp path

    # Create a dummy PDF for testing
    Path(test_file).write_bytes(b"%PDF-1.4 test")

    try:
        result = await ingest_documents(file_paths=[test_file], async_mode=True)
        print(f"   Result: {result}")

        # Extract job_id from result
        if "job_" in result:
            import re

            match = re.search(r"(job_\d{8}_\d{6}_[a-f0-9]+)", result)
            if match:
                job_id = match.group(1)
                print(f"   📌 Job ID: {job_id}")

                # 3. Test get_job_status
                print(f"\n⏳ 3. Testing get_job_status({job_id})...")
                await asyncio.sleep(0.5)  # Wait a bit for job to start
                status = await get_job_status(job_id=job_id)
                print(
                    f"   Status: {status[:300]}..."
                    if len(status) > 300
                    else f"   Status: {status}"
                )

                # 4. Test list_jobs again
                print("\n📋 4. Testing list_jobs (should show the job)...")
                jobs = await list_jobs(active_only=False)
                print(
                    f"   Jobs: {jobs[:300]}..."
                    if len(jobs) > 300
                    else f"   Jobs: {jobs}"
                )

                # 5. Test cancel_job (if still running)
                print(f"\n🚫 5. Testing cancel_job({job_id})...")
                cancel_result = await cancel_job(job_id=job_id)
                print(f"   Cancel result: {cancel_result}")

    except Exception as e:
        print(f"   ⚠️ Error (expected for dummy PDF): {e}")

    finally:
        # Cleanup
        Path(test_file).unlink(missing_ok=True)

    # 6. Test list_documents
    print("\n📚 6. Testing list_documents...")
    docs = await list_documents()
    print(
        f"   Documents: {docs[:200]}..." if len(docs) > 200 else f"   Documents: {docs}"
    )

    print("\n" + "=" * 60)
    print("✅ MCP Tools Test Complete!")
    print("=" * 60)


async def test_tool_registration():
    """驗證所有工具都已正確註冊。"""
    print("=" * 60)
    print("🔧 Checking Tool Registration")
    print("=" * 60)

    expected_tools = [
        "ingest_documents",
        "get_job_status",
        "list_jobs",
        "cancel_job",
        "list_documents",
        "inspect_document_manifest",
        "fetch_document_asset",
        "consult_knowledge_graph",
    ]

    registered_tools = [t.name for t in mcp._tool_manager._tools.values()]

    print(f"\n📋 Registered tools: {registered_tools}")

    missing = set(expected_tools) - set(registered_tools)
    extra = set(registered_tools) - set(expected_tools)

    if missing:
        print(f"❌ Missing tools: {missing}")
    if extra:
        print(f"ℹ️ Extra tools: {extra}")

    if not missing:
        print("✅ All expected tools are registered!")

    return len(missing) == 0


async def main():
    """Run all tests."""
    print("\n🚀 MCP Server Tools Test\n")

    # Test tool registration
    reg_ok = await test_tool_registration()

    # Test job system
    await test_job_system()

    return reg_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
