"""Debug script for LightRAG integration."""

import asyncio
import sys

sys.path.insert(0, ".")

from src.infrastructure.config import settings
from src.infrastructure.lightrag_adapter import LightRAGAdapter


async def test_lightrag():
    """Test LightRAG directly."""
    print("=" * 60)
    print("LightRAG Debug Test")
    print("=" * 60)

    # Check settings
    print("\n1. Settings:")
    print(f"   - enable_lightrag: {settings.enable_lightrag}")
    print(f"   - llm_backend: {settings.llm_backend}")
    print(f"   - ollama_host: {settings.ollama_host}")
    print(f"   - ollama_model: {settings.ollama_model}")
    print(f"   - ollama_embedding_model: {settings.ollama_embedding_model}")
    print(f"   - lightrag_working_dir: {settings.lightrag_working_dir}")

    # Create adapter
    adapter = LightRAGAdapter()
    print(f"\n2. Adapter available: {adapter.is_available}")

    if not adapter.is_available:
        print("   ERROR: LightRAG not available!")
        return

    # Test insert
    test_text = """
    [Document: test_doc_001]

    This is a test document about FOXP3 and regulatory T cells.
    FOXP3 is a transcription factor that is crucial for the development
    and function of regulatory T cells (Tregs).
    Tregs play an important role in maintaining immune tolerance.
    """

    print("\n3. Testing insert...")
    try:
        await adapter.insert("test_doc_001", test_text)
        print("   ✅ Insert successful!")
    except Exception as e:
        print(f"   ❌ Insert failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test query
    print("\n4. Testing query...")
    try:
        result = await adapter.query("What is FOXP3?", mode="hybrid")
        print(f"   Result: {result[:200] if result else 'No result'}...")
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        import traceback
        traceback.print_exc()

    # Test entity extraction
    print("\n5. Testing entity extraction...")
    try:
        entities = await adapter.extract_entities(test_text)
        print(f"   Entities: {entities}")
    except Exception as e:
        print(f"   ❌ Entity extraction failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Debug complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_lightrag())
