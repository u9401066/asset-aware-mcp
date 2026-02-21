#!/usr/bin/env python3
"""
DFM CLI — Docx ↔ DFM 互動式轉換工具

提供互動式選單讓使用者直接操作 docx 文件的轉換、編輯與存檔。

用法:
    python scripts/dfm_cli.py              # 互動式選單
    python scripts/dfm_cli.py ingest FILE  # 直接匯入
    python scripts/dfm_cli.py save DOC_ID  # 存回 docx
    python scripts/dfm_cli.py list         # 列出已匯入文件
    python scripts/dfm_cli.py validate ID  # 驗證 round-trip
    python scripts/dfm_cli.py open DOC_ID  # 用 VS Code 開啟 DFM
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from src.application.docx_service import DocxService  # noqa: E402
from src.infrastructure.file_storage import FileStorage  # noqa: E402

# ============================================================================
# Service setup
# ============================================================================

DATA_DIR = PROJECT_ROOT / "data"


def _create_service() -> DocxService:
    repository = FileStorage(DATA_DIR)
    return DocxService(repository=repository)


# ============================================================================
# Commands
# ============================================================================


async def cmd_ingest(file_path: str) -> str | None:
    """匯入 .docx → DFM"""
    service = _create_service()
    path = Path(file_path).resolve()
    if not path.exists():
        print(f"❌ 檔案不存在: {path}")
        return None

    print(f"📥 匯入中: {path.name}")
    result = await service.ingest_docx(str(path))

    if not result.get("success"):
        print(f"❌ 匯入失敗: {result.get('error')}")
        return None

    doc_id = result.get("doc_id", "")
    dfm_path = result.get("dfm_path", "")
    print(f"✅ 匯入成功!")
    print(f"   doc_id:     {doc_id}")
    print(f"   區塊數:     {result.get('total_blocks', '?')}")
    print(f"   可編輯:     {result.get('editable_blocks', '?')}")
    print(f"   MD  路徑:  {result.get('md_path', '')}")
    print(f"   DFM 路徑:  {dfm_path}")
    print()
    print("💡 下一步: 用 VS Code 開啟 content.md 進行編輯，編輯完成後選擇「存回 docx」")
    return doc_id


async def cmd_save(doc_id: str, output_path: str | None = None) -> None:
    """將編輯後的 MD 存回 .docx"""
    service = _create_service()

    # Check if content.md exists (split format)
    md_path = DATA_DIR / doc_id / "content.md"
    use_md = md_path.exists()
    dfm_text: str | None = None

    if use_md:
        print(f"📄 使用分離格式: content.md + format.yaml")
    else:
        # Fallback to DFM
        dfm_text = await service.get_dfm(doc_id)
        if dfm_text is None:
            print(f"❌ 找不到文件: {doc_id}")
            return

    if output_path is None:
        # Default: save next to original
        doc_dir = DATA_DIR / doc_id
        ir_json = doc_dir / "ir.json"
        if ir_json.exists():
            import json

            ir_data = json.loads(ir_json.read_text(encoding="utf-8"))
            source = Path(ir_data.get("source_path", ""))
            if source.exists():
                output_path = str(
                    source.parent / f"{source.stem}_edited{source.suffix}"
                )
        if output_path is None:
            output_path = str(doc_dir / "output.docx")

    print(f"💾 存檔中: {output_path}")
    if use_md:
        result = await service.save_docx(doc_id, output_path=output_path, from_md=True)
    else:
        result = await service.save_docx(doc_id, dfm_text, output_path)

    if result.get("success"):
        print(f"✅ 存檔成功: {result.get('output_path')}")
        warnings = result.get("warnings", [])
        if warnings:
            print("⚠️ 警告:")
            for w in warnings:
                print(f"   - {w}")
    else:
        print(f"❌ 存檔失敗: {result.get('error')}")


async def cmd_validate(doc_id: str) -> None:
    """驗證 round-trip 保真度"""
    service = _create_service()

    dfm_text = await service.get_dfm(doc_id)
    if dfm_text is None:
        print(f"❌ 找不到文件: {doc_id}")
        return

    doc_dir = DATA_DIR / doc_id
    original = doc_dir / "original.docx"
    if not original.exists():
        print(f"❌ 找不到原始檔案: {original}")
        return

    print("🔍 驗證中...")

    # Rebuild to temp file
    temp_output = doc_dir / "validation_temp.docx"
    result = await service.save_docx(doc_id, dfm_text, str(temp_output))

    if not result.get("success"):
        print(f"❌ 重建失敗: {result.get('error')}")
        return

    # Run validator
    from src.application.docx_validator import DocxValidator

    validator = DocxValidator()
    report = validator.validate(original, temp_output)
    print(report.to_markdown())

    # Clean up
    if temp_output.exists():
        temp_output.unlink()


def cmd_list() -> None:
    """列出所有已匯入的文件"""
    if not DATA_DIR.exists():
        print("📭 尚未匯入任何文件")
        return

    docs = []
    for d in sorted(DATA_DIR.iterdir()):
        if d.is_dir() and d.name.startswith("docx_"):
            dfm_path = d / "content.dfm"
            original = d / "original.docx"
            docs.append(
                {
                    "id": d.name,
                    "has_dfm": dfm_path.exists(),
                    "has_original": original.exists(),
                    "dir": d,
                }
            )

    if not docs:
        print("📭 尚未匯入任何 docx 文件")
        return

    print(f"📂 已匯入 {len(docs)} 個文件:\n")
    for i, doc in enumerate(docs, 1):
        status = "✅" if doc["has_dfm"] else "⚠️"
        # Extract readable name from doc_id
        name = doc["id"].replace("docx_", "").rsplit("_", 1)[0]
        print(f"  {i}. {status} {name}")
        print(f"     ID: {doc['id']}")
    return docs


def cmd_open(doc_id: str) -> None:
    """用 VS Code 開啟 content.md 檔案"""
    # Prefer .md (clean), fallback to .dfm
    md_path = DATA_DIR / doc_id / "content.md"
    dfm_path = DATA_DIR / doc_id / "content.dfm"
    target = md_path if md_path.exists() else dfm_path

    if not target.exists():
        print(f"❌ 檔案不存在: {target}")
        return

    print(f"📝 開啟: {target}")
    try:
        subprocess.run(["code", str(target)], check=False)
    except FileNotFoundError:
        # Try code-insiders
        try:
            subprocess.run(["code-insiders", str(target)], check=False)
        except FileNotFoundError:
            print(f"⚠️ 找不到 VS Code。請手動開啟:\n   {target}")


async def cmd_blocks(doc_id: str) -> None:
    """列出文件中的所有區塊"""
    service = _create_service()
    blocks = await service.list_blocks(doc_id)
    if blocks is None:
        print(f"❌ 找不到文件: {doc_id}")
        return

    print(f"\n📄 共 {len(blocks)} 個區塊:\n")
    print(f"  {'ID':<8} {'類型':<12} {'可編輯':<6} {'樣式':<8} 預覽")
    print(f"  {'─' * 8} {'─' * 12} {'─' * 6} {'─' * 8} {'─' * 30}")
    for b in blocks:
        edit = "✅" if b["editable"] else "🔒"
        style = (b.get("style") or "")[:8]
        preview = (b.get("preview") or "")[:40]
        print(f"  {b['id']:<8} {b['type']:<12} {edit:<6} {style:<8} {preview}")


# ============================================================================
# Interactive menu
# ============================================================================


def _pick_file() -> str | None:
    """讓使用者選擇 .docx 檔案"""
    path = input("\n📁 請輸入 .docx 檔案路徑 (可拖放檔案到此): ").strip().strip('"')
    if not path:
        return None
    return path


def _pick_doc() -> str | None:
    """讓使用者選擇已匯入的文件"""
    docs = cmd_list()
    if not docs:
        return None
    print()
    choice = input("請輸入編號 (或直接輸入 doc_id): ").strip()
    if not choice:
        return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(docs):
            return docs[idx]["id"]
    except ValueError:
        pass
    # Treat as direct doc_id
    return choice


async def interactive_menu() -> None:
    """互動式操作選單"""
    print()
    print("╔══════════════════════════════════════╗")
    print("║   DFM — Docx ↔ Markdown 轉換工具     ║")
    print("╚══════════════════════════════════════╝")

    while True:
        print()
        print("┌──────────────────────────────────────┐")
        print("│  1. 📥 匯入 docx → DFM               │")
        print("│  2. 📝 開啟 DFM 編輯 (VS Code)        │")
        print("│  3. 💾 存回 docx                      │")
        print("│  4. 🔍 驗證 round-trip                │")
        print("│  5. 📋 列出已匯入文件                  │")
        print("│  6. 📄 列出文件區塊                    │")
        print("│  7. 🔄 一鍵流程 (匯入→編輯→存檔)       │")
        print("│  0. 🚪 離開                           │")
        print("└──────────────────────────────────────┘")
        choice = input("\n請選擇 [0-7]: ").strip()

        if choice == "0":
            print("👋 Bye!")
            break

        elif choice == "1":
            path = _pick_file()
            if path:
                await cmd_ingest(path)

        elif choice == "2":
            doc_id = _pick_doc()
            if doc_id:
                cmd_open(doc_id)

        elif choice == "3":
            doc_id = _pick_doc()
            if doc_id:
                custom = input("輸出路徑 (Enter = 預設): ").strip().strip('"')
                await cmd_save(doc_id, custom or None)

        elif choice == "4":
            doc_id = _pick_doc()
            if doc_id:
                await cmd_validate(doc_id)

        elif choice == "5":
            cmd_list()

        elif choice == "6":
            doc_id = _pick_doc()
            if doc_id:
                await cmd_blocks(doc_id)

        elif choice == "7":
            # One-click workflow
            print("\n🔄 一鍵流程：匯入 → 編輯 → 存檔")
            path = _pick_file()
            if not path:
                continue
            doc_id = await cmd_ingest(path)
            if not doc_id:
                continue

            cmd_open(doc_id)
            print("\n⏳ 請在 VS Code 中編輯 DFM 檔案...")
            input("✏️  編輯完成後按 Enter 繼續存檔...")

            custom = input("輸出路徑 (Enter = 預設): ").strip().strip('"')
            await cmd_save(doc_id, custom or None)

            validate_yn = input("\n是否驗證 round-trip? [y/N]: ").strip().lower()
            if validate_yn == "y":
                await cmd_validate(doc_id)

        else:
            print("❓ 無效選項，請重新輸入")


# ============================================================================
# CLI entry point
# ============================================================================


def main() -> None:
    args = sys.argv[1:]

    if not args:
        # Interactive mode
        asyncio.run(interactive_menu())
        return

    cmd = args[0].lower()

    if cmd == "ingest" and len(args) >= 2:
        asyncio.run(cmd_ingest(args[1]))
    elif cmd == "save" and len(args) >= 2:
        output = args[2] if len(args) >= 3 else None
        asyncio.run(cmd_save(args[1], output))
    elif cmd == "validate" and len(args) >= 2:
        asyncio.run(cmd_validate(args[1]))
    elif cmd == "list":
        cmd_list()
    elif cmd == "open" and len(args) >= 2:
        cmd_open(args[1])
    elif cmd == "blocks" and len(args) >= 2:
        asyncio.run(cmd_blocks(args[1]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
