"""
Docx Tools - Docx ↔ DFM 雙向轉換 + Table Bridge MCP 工具

包含：
- ingest_docx: 攝入 .docx 文件，轉換為 DFM 格式
- get_docx_content: 取得可編輯的 DFM 內容
- save_docx: 將編輯後的 DFM 存回 .docx
- list_docx_blocks: 列出文件中所有區塊的摘要
- list_docx_documents: 列出所有已攝入的 DOCX/DFM 文件
- delete_docx: 刪除已攝入的 DOCX/DFM 文件及其本地 artifacts
- convert_docx_to_doc: 將目前 DOCX/DFM 狀態轉為 DOC（保真模式）
- convert_docx_to_pdf: 將目前 DOCX/DFM 狀態轉為 PDF（保真模式）
- export_markdown: 將 Markdown 直接匯出為 DOCX/PDF/DOC（無需 ingest）
- docx_table_to_context: 將 DFM 表格區塊轉為 TableContext（可用 table_manage/table_data 編輯）
- docx_table_from_context: 將 TableContext 寫回 DFM 表格區塊
- docx_chart_data: 提取圖表的底層資料為表格格式
- docx(op="checkout"/"commit"/"release"/"renew"/"leases"/"break_lease"):
  區塊租約（lease），讓多個 agent 同時編輯同一份文件的不同區塊
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Any, cast

from mcp.server.mcpserver import Context  # noqa: TC002 - runtime injection marker

from src.application.output_paths import resolve_document_output_path
from src.infrastructure.encoding_guard import read_text_file
from src.presentation.dependencies import (
    dfm_table_bridge,
    docx_service,
    docx_validator,
    job_service,
    table_service,
)
from src.presentation.markdown_utils import escape_table_cell
from src.presentation.mcp_app import mcp
from src.presentation.mcp_context import log_message, report_progress
from src.presentation.response_limits import (
    format_limited_text_response,
    max_text_response_chars,
    text_exceeds_response_limit,
    text_sha256,
)
from src.presentation.tools.conversion_job_support import (
    conversion_result_payload,
    create_conversion_job_response,
)

if TYPE_CHECKING:
    from src.domain.table_entities import TableContext

logger = logging.getLogger(__name__)


def _normalize_op(op: str) -> str:
    return op.strip().lower().replace("-", "_")


def _unsupported_docx_op(kind: str, op: str, allowed: set[str]) -> str:
    allowed_ops = ", ".join(sorted(allowed))
    return f"Unsupported {kind} op `{op}`. Supported operations: {allowed_ops}."


def _missing_docx_param(name: str) -> str:
    return f"Missing required parameter: {name} is required."


def _escape_preview_cell(value: object, max_chars: int) -> str:
    return str(value).replace("|", "\\|")[:max_chars]


def _format_docx_locator(metadata: dict[str, Any] | None) -> str:
    """Return a compact DOCX source locator for block listings."""
    if not metadata:
        return ""
    parts: list[str] = []
    source_part = metadata.get("source_part")
    if source_part:
        parts.append(str(source_part))
    source_story = metadata.get("source_story")
    if source_story and source_story != "body":
        parts.append(str(source_story))
    if "paragraph_index" in metadata:
        parts.append(f"p#{metadata['paragraph_index']}")
    if "table_index" in metadata:
        parts.append(f"t#{metadata['table_index']}")
    if "parent_cell" in metadata:
        parts.append(f"cell {metadata['parent_cell']}")
    return " ".join(parts)


def _summarize_large_docx_metadata(metadata: Any) -> dict[str, Any]:
    """Return a bounded summary of large DOCX locator metadata."""
    if not isinstance(metadata, dict):
        return {"type": type(metadata).__name__, "preview": str(metadata)[:200]}

    summary: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, str):
            summary[key] = value if len(value) <= 200 else value[:200]
        elif isinstance(value, (int, float, bool)) or value is None:
            summary[key] = value
        elif isinstance(value, list):
            summary[f"{key}_count"] = len(value)
            summary[f"{key}_sample"] = value[:3]
        elif isinstance(value, dict):
            summary[f"{key}_count"] = len(value)
            summary[f"{key}_sample_keys"] = list(value.keys())[:10]
        else:
            summary[f"{key}_type"] = type(value).__name__
    return summary


def _docx_artifact_path(doc_id: str, filename: str) -> str | None:
    try:
        return str(docx_service.repository.get_doc_dir(doc_id) / filename)
    except Exception:
        return None


def _get_pending_table_contexts(doc_id: str) -> list[TableContext]:
    """Collect doc-linked TableContext instances pending write-back."""
    pending: list[TableContext] = []
    for candidate in table_service._tables.values():
        if getattr(candidate, "source_doc_id", "") != doc_id:
            continue
        if not getattr(candidate, "source_block_id", ""):
            continue
        pending.append(cast("TableContext", candidate))
    return pending


def _prepare_merged_save_input(
    doc_id: str,
    dfm_content: str | None,
    from_md: bool,
) -> tuple[str | None, bool, list[str], list[str]]:
    """Merge editor/disk edits with pending TableContext changes before save."""
    pending = _get_pending_table_contexts(doc_id)
    if not pending:
        return dfm_content, from_md, [], []

    ir = docx_service._load_ir(doc_id)
    if ir is None:
        return dfm_content, from_md, [], []

    working_ir = deepcopy(ir)
    doc_dir = docx_service.repository.get_doc_dir(doc_id)
    # The merged DFM must keep the revision its edits were based on, so a
    # stale editor DFM is still 3-way merged (never stamped as current).
    base_revision: object = ""

    if from_md:
        md_path = doc_dir / "content.md"
        yaml_path = doc_dir / "format.yaml"
        if not md_path.exists() or not yaml_path.exists():
            return dfm_content, from_md, [], []

        md_content = read_text_file(md_path, hint=str(md_path))
        yaml_content = read_text_file(yaml_path, hint=str(yaml_path))
        split_report = docx_service.integrity.check_split_consistency(
            md_content, yaml_content
        )
        if split_report.error_count:
            return dfm_content, from_md, [], []

        parse_result = docx_service.parser.parse_split(md_content, yaml_content)
        base_revision = getattr(parse_result, "revision", "")
        working_ir = docx_service.parser.apply_edits(working_ir, parse_result)
    elif dfm_content is not None:
        parse_result = docx_service.parser.parse(dfm_content)
        fatal_errors = [
            e
            for e in parse_result.errors
            if e.startswith(("FORMAT_MISMATCH", "DUPLICATE_ID"))
        ]
        if fatal_errors:
            return dfm_content, from_md, [], []
        base_revision = getattr(parse_result, "revision", "")
        working_ir = docx_service.parser.apply_edits(working_ir, parse_result)
    else:
        base_revision = docx_service.ir_revision(ir)

    synced_table_ids: list[str] = []
    merge_warnings: list[str] = []
    for tc in pending:
        try:
            dfm_table_bridge.apply_table_context_to_ir(
                working_ir, tc.source_block_id, tc
            )
        except ValueError as e:
            warning = (
                f"Skipped pending TableContext `{tc.id}` for block "
                f"`{tc.source_block_id}` before save_docx: {e}"
            )
            merge_warnings.append(warning)
            logger.warning(
                "Skipping TableContext merge before save_docx | doc_id=%s | table_id=%s | block_id=%s",
                doc_id,
                tc.id,
                tc.source_block_id,
                exc_info=True,
            )
            continue
        synced_table_ids.append(tc.id)

    if not synced_table_ids:
        return dfm_content, from_md, [], merge_warnings

    working_ir.dfm_revision = base_revision if isinstance(base_revision, str) else ""
    merged_dfm = docx_service.renderer.render(working_ir)
    return merged_dfm, False, synced_table_ids, merge_warnings


@mcp.tool()
async def ingest_docx(
    file_path: str, reset: bool = False, ctx: Context | None = None
) -> str:
    """
    攝入 .docx / .doc 文件，轉換為 DFM (Docx-Flavored Markdown) 格式。

    同一份來源檔若已攝入過，會直接回傳既有文件狀態（保留所有已儲存/已 commit
    的編輯與目前 revision），不會重新解析；只有 reset=True 才會明確捨棄所有編輯、
    從來源檔重建（有其他 agent 持有有效租約時拒絕，並先備份）。

    將 docx 解析為中間表示 (IR)，再轉換為可在 VS Code 中編輯的 DFM 格式。
    支援複雜元素：合併表格、圖表、頁首頁尾、巨集、目錄等。
    **支援舊版 .doc 格式**（自動透過 LibreOffice 轉換為 .docx）。

    輸出目錄結構：
    ```
    data/{doc_id}/
    ├── content.dfm      # 可編輯的 Markdown + YAML 標注
    ├── ir.json          # 目前 IR（每次 save_docx 更新）
    ├── baseline_ir.json # ingest 時的不可變 IR（累積回寫的比對基準）
    ├── original.docx    # 原始檔案備份（永不修改）
    ├── parts/           # 保留的 XML 零件
    └── assets/          # 圖片和二進位資產
    ```

    Args:
        file_path: .docx 或 .doc 檔案的絕對路徑
        reset: 若為 True，捨棄既有文件的所有編輯並從來源檔重新攝入

    Returns:
        攝入結果摘要（doc_id、區塊數量等）
    """
    await log_message(ctx, "info", f"ingest_docx start: {file_path}")
    await report_progress(ctx, 10, message="Preparing DOCX ingest")
    result = await docx_service.ingest_docx(file_path, reset=reset)
    logger.info("ingest_docx | file=%s | success=%s", file_path, result.get("success"))

    if not result.get("success"):
        await log_message(ctx, "error", f"ingest_docx failed: {file_path}")
        return f"❌ 攝入失敗：{result.get('error', '未知錯誤')}"

    await report_progress(ctx, 100, message=f"Finished ingesting {file_path}")
    await log_message(ctx, "info", f"ingest_docx complete: {result.get('doc_id', '')}")

    existing = bool(result.get("existing"))
    lines = [
        "✅ 文件已攝入（沿用既有狀態，未重新解析）" if existing else "✅ Docx 攝入成功",
        "",
        f"- **doc_id**: `{result.get('doc_id', '')}`",
        f"- **來源**: {result.get('source', '')}",
        f"- **總區塊數**: {result.get('total_blocks', 0)}",
        f"- **可編輯區塊**: {result.get('editable_blocks', 0)}",
        f"- **受保護區塊**: {result.get('protected_blocks', 0)}",
        f"- **資產數**: {result.get('assets', 0)}",
        f"- **DFM 路徑**: `{result.get('dfm_path', '')}`",
        f"- **完整性**: {result.get('integrity', 'N/A')}",
    ]
    if result.get("revision"):
        lines.append(f"- **內容版本 (revision)**: `{result.get('revision')}`")
    if existing:
        changed = result.get("changed_block_ids") or []
        lines.append(
            f"- **自 ingest 以來已編輯的區塊**: {len(changed)}"
            + (f"（{', '.join(changed[:20])}）" if changed else "")
        )
        lines.append(f"- **說明**: {result.get('note', '')}")
    if result.get("reset"):
        discarded = result.get("discarded_block_ids") or []
        lines.append(
            f"- **reset**: 已捨棄 {len(discarded)} 個區塊的編輯並重建（備份於 .backups/）"
        )
    if result.get("storage_warning"):
        lines.append(f"- ⚠️ **儲存位置**: {result.get('storage_warning')}")
    for warning in result.get("warnings", []) or []:
        lines.append(f"- ⚠️ {warning}")

    block_types = result.get("block_types", {})
    if block_types:
        lines.append("")
        lines.append("**區塊類型分布**：")
        for bt, count in sorted(block_types.items()):
            lines.append(f"  - {bt}: {count}")

    return "\n".join(lines)


@mcp.tool()
async def get_docx_content(
    doc_id: str,
    block_id: str | None = None,
    max_chars: int | None = None,
) -> str:
    """
    取得 docx 文件的可編輯 DFM 內容。

    若指定 block_id，只回傳該區塊的內容；否則回傳完整 DFM。

    Args:
        doc_id: 文件 ID（由 ingest_docx 產生）
        block_id: 可選，特定區塊 ID（如 p001, t001, h001）

    Returns:
        DFM 內容或特定區塊資訊
    """
    if block_id:
        block = await docx_service.get_block_content(doc_id, block_id)
        if block is None:
            return f"❌ 找不到區塊 {block_id}（doc_id={doc_id}）"
        content = block.get("content")
        if isinstance(content, str) and text_exceeds_response_limit(content, max_chars):
            limit = min(max_text_response_chars(max_chars), 2_000)
            block = dict(block)
            block["content"] = content[:limit]
            block["content_truncated"] = True
            block["content_chars"] = len(content)
            block["content_sha256"] = text_sha256(content)
        metadata = block.get("metadata")
        metadata_json = json.dumps(metadata, ensure_ascii=False, default=str)
        if metadata is not None and text_exceeds_response_limit(
            metadata_json,
            max_chars,
        ):
            block = dict(block)
            block["metadata"] = _summarize_large_docx_metadata(metadata)
            block["metadata_truncated"] = True
            block["metadata_chars"] = len(metadata_json)
            block["metadata_sha256"] = text_sha256(metadata_json)
            artifact_path = _docx_artifact_path(doc_id, "ir.json")
            if artifact_path:
                block["metadata_artifact_path"] = artifact_path
        payload = json.dumps(block, ensure_ascii=False, indent=2)
        return format_limited_text_response(
            title=f"DOCX Block: {doc_id}/{block_id}",
            text=payload,
            source_path=_docx_artifact_path(doc_id, "ir.json"),
            max_chars=max_chars,
            language="json",
            guidance="request a smaller block or inspect the persisted `ir.json` artifact",
        )

    dfm = await docx_service.get_dfm(doc_id)
    if dfm is None:
        return f"❌ 找不到文件 {doc_id}，請先使用 ingest_docx 攝入。"
    source_path = _docx_artifact_path(doc_id, "content.dfm")
    return format_limited_text_response(
        title=f"DFM Content Preview: {doc_id}",
        text=dfm,
        source_path=source_path,
        max_chars=max_chars,
        language="markdown",
        guidance='use `list_docx_blocks` then `get_docx_content(doc_id, block_id="<id>")` for focused reads',
    )


@mcp.tool()
async def save_docx(
    doc_id: str,
    dfm_content: str | None = None,
    output_path: str | None = None,
    from_md: bool = False,
    force: bool = False,
    track_changes: bool = False,
    revision_author: str = "Asset-Aware MCP",
    revision_base: str = "original",
    ctx: Context | None = None,
) -> str:
    """
    將編輯後的內容存回 .docx 檔案。

    支援兩種模式：
    - DFM 模式（預設）：傳入 dfm_content（.dfm 格式全文）
    - MD 模式（from_md=True）：從磁碟讀取 content.md + format.yaml

    回寫流程：
    1. 解析 DFM/MD → 提取修改，套用到目前 IR（ir.json）
    2. 與 ingest 時的不可變基準（baseline_ir.json）比對，取得「自 ingest
       以來」所有變更區塊（累積回寫）
    3. 以 original.docx 為底，只改寫這些區塊；未編輯區塊與其他 package
       parts 保持位元組不變
    4. Post-save 完整性檢查逐一確認每個預期變更都出現在輸出中；
       若有任何先前的編輯遺失，儲存會失敗而不是回報成功

    每次儲存都包含先前所有儲存過的編輯（不需要重新套用）。由 v1.4.1
    以前建立、沒有 baseline_ir.json 的文件目錄，會自動從 original.docx
    重建基準（並在警告中列出先前已存在的編輯）；無法驗證時拒絕儲存。

    多 agent 併發安全：DFM front matter 的 `revision` 證明這份 DFM based on
    哪個內容版本。若期間有人已儲存，save_docx 會做 3-way merge：只套用你
    相對於 base 改過的區塊；若同一區塊也被別人改過，拒絕並列出衝突區塊 id，
    絕不默默覆蓋別人的編輯。被其他 agent 以 docx(op="checkout") 租用的區塊
    也會被拒絕。沒有 `revision` 的舊 DFM 只在 ingest 後從未儲存時接受。
    force=True 不會略過 revision 或 lease 檢查。

    安全機制：若內容萎縮 > 50%，預設拒絕輸出（疑似資料遺失）。
    使用 force=True 強制輸出。

    若 track_changes=True，會將修改以真正 Word Track Changes
    (`w:del`/`w:ins`) 寫回，供使用者在 Word 中逐項審查：
    - revision_base="original"（預設）：顯示自 ingest 以來「所有」編輯，
      相對於原始文件（IRB/PI 審查通常需要的版本）。
    - revision_base="last_save"：先前儲存的編輯以已接受的純文字寫入，
      只把本次相對於上次儲存狀態的變更標成修訂。
    要求追蹤修訂但輸出沒有新增任何 w:ins/w:del 時，儲存會失敗。

    output_path 只能位於文件目錄（data/{doc_id}/）內；目錄外的路徑會回傳
    「Output path must stay within document directory」錯誤。要寫回使用者
    的原始檔案，請改用 document(op="native")：register 來源檔 →
    read_docx / update_docx → writeback（需 expected_revision 與
    expected_source_sha256，會檢查來源 hash/stat 是否過期並保留備份），
    或用 publish 建立新的外部檔案。

    Args:
        doc_id: 文件 ID
        dfm_content: 編輯後的 DFM 全文（from_md=True 時可省略）
        output_path: 輸出路徑（預設為 data/{doc_id}/output.docx；必須位於
            data/{doc_id}/ 內，不可覆寫 original.docx 等保留檔）
        from_md: 若為 True，從磁碟讀取 content.md + format.yaml 而非使用 dfm_content
        force: 若為 True，即使偵測到嚴重內容萎縮或 post-save 檢查失敗仍強制
            輸出（不會略過 revision 衝突與 lease）
        track_changes: 若為 True，以 Word Track Changes 寫入文字 diff
        revision_author: 產生追蹤修訂時使用的作者名稱
        revision_base: 追蹤修訂的比較基準："original"（預設，相對原始文件）
            或 "last_save"（相對上次儲存狀態）

    Returns:
        儲存結果
    """
    logger.info(
        "save_docx | doc_id=%s | from_md=%s | output=%s",
        doc_id,
        from_md,
        output_path,
    )
    await log_message(ctx, "info", f"save_docx start: {doc_id}")
    await report_progress(ctx, 10, message=f"Preparing merged save for {doc_id}")
    dfm_content, from_md, synced_table_ids, merge_warnings = _prepare_merged_save_input(
        doc_id,
        dfm_content,
        from_md,
    )
    await report_progress(ctx, 45, message=f"Writing DOCX for {doc_id}")
    result = await docx_service.save_docx(
        doc_id,
        dfm_content,
        output_path,
        from_md=from_md,
        force=force,
        track_changes=track_changes,
        revision_author=revision_author,
        revision_base=revision_base,
    )
    logger.info(
        "save_docx done | doc_id=%s | success=%s | integrity=%s",
        doc_id,
        result.get("success"),
        result.get("integrity", "N/A"),
    )

    if not result.get("success"):
        await log_message(ctx, "error", f"save_docx failed: {doc_id}")
        lines = [f"❌ 儲存失敗：{result.get('error', '未知錯誤')}"]
        if result.get("committed"):
            lines.append(
                f"- **內容已發布**: revision `{result.get('revision', '')}`（見上方說明）"
            )
        if result.get("conflict_block_ids"):
            lines.append(
                "- **衝突區塊**: " + ", ".join(result.get("conflict_block_ids", []))
            )
        warnings = [*merge_warnings, *result.get("warnings", [])]
        if warnings:
            lines.append("")
            lines.append("⚠️ 診斷：")
            lines.extend(f"  - {warning}" for warning in warnings[:10])
        return "\n".join(lines)

    await report_progress(ctx, 100, message=f"Finished saving {doc_id}")
    await log_message(ctx, "info", f"save_docx complete: {doc_id}")

    lines = [
        "✅ Docx 儲存成功",
        f"- **輸出路徑**: `{result.get('output_path', '')}`",
        f"- **完整性**: {result.get('integrity', 'N/A')}",
    ]
    if "changed_block_ids" in result:
        changed = result.get("changed_block_ids") or []
        edited = result.get("edited_block_ids") or []
        lines.append(
            f"- **相對原始文件的變更區塊**: {len(changed)}（本次編輯 {len(edited)}）"
        )
    if result.get("baseline_rebuilt"):
        lines.append("- **基準**: 已從 original.docx 重建 baseline_ir.json（舊版目錄）")
    if result.get("revision"):
        lines.append(f"- **內容版本 (revision)**: `{result.get('revision')}`")
    if result.get("revision_front_matter"):
        lines.append(
            "- **繼續編輯同一份 DFM 時**: 把 front matter 的 revision 行換成 "
            f"`{result.get('revision_front_matter')}`（或重新讀取 DFM）"
        )
    if result.get("reopen_before_next_save"):
        lines.append("- **下次編輯前請重新讀取 DFM**（已合併其他 agent 的區塊）")
    if result.get("storage_warning"):
        lines.append(f"- ⚠️ **儲存位置**: {result.get('storage_warning')}")
    merge = result.get("revision_merge")
    if isinstance(merge, dict) and merge.get("mode") == "merged":
        lines.append(
            "- **3-way merge**: 以 "
            f"`{merge.get('base_revision')}` 為基準合併；套用你改的區塊 "
            f"{', '.join(merge.get('merged_block_ids') or []) or '（無）'}，"
            f"保留他人已改的區塊 "
            f"{', '.join(merge.get('preserved_block_ids') or []) or '（無）'}"
        )

    if synced_table_ids:
        lines.append(
            f"- **自動同步的表格變更**: {len(synced_table_ids)} 個 TableContext"
        )

    if result.get("track_changes"):
        lines.append(
            "- **追蹤修訂**: 已寫入 Word Track Changes "
            f"({result.get('track_change_blocks', 0)} 個區塊, "
            f"base={result.get('revision_base', revision_base)}, "
            f"author={result.get('revision_author', revision_author)})"
        )
        if result.get("revision_sidecar_path"):
            lines.append(
                "- **修訂 sidecar**: "
                f"`{result.get('revision_sidecar_path')}` "
                f"({result.get('revision_records', 0)} records)"
            )

    warnings = [*merge_warnings, *result.get("warnings", [])]
    if warnings:
        lines.append("")
        lines.append("⚠️ 警告：")
        lines.extend(f"  - {w}" for w in warnings)

    return "\n".join(lines)


@mcp.tool()
async def list_docx_blocks(doc_id: str, limit: int | None = None) -> str:
    """
    列出 docx 文件中所有區塊的摘要。

    顯示每個區塊的 ID、類型、是否可編輯、樣式名稱和內容預覽。

    Args:
        doc_id: 文件 ID

    Returns:
        區塊摘要列表
    """
    blocks = await docx_service.list_blocks(doc_id)
    if blocks is None:
        return f"❌ 找不到文件 {doc_id}"

    if not blocks:
        return "文件中沒有任何區塊。"

    lines = [f"📄 文件 `{doc_id}` — 共 {len(blocks)} 個區塊\n"]
    lines.append("| ID | 類型 | 可編輯 | Locator | 樣式 | 預覽 |")
    lines.append("|---|---|---|---|---|---|")

    effective_limit = 100 if limit is None else max(1, min(limit, 1_000))
    visible_blocks = blocks[:effective_limit]
    for b in visible_blocks:
        editable = "✅" if b["editable"] else "🔒"
        locator = _format_docx_locator(b.get("metadata"))
        style = escape_table_cell(b.get("style") or "")
        preview = _escape_preview_cell(b.get("preview", ""), 50)
        lines.append(
            "| {id} | {type} | {editable} | {locator} | {style} | {preview} |".format(
                id=escape_table_cell(b["id"]),
                type=escape_table_cell(b["type"]),
                editable=escape_table_cell(editable),
                locator=escape_table_cell(locator),
                style=style,
                preview=preview,
            )
        )

    if len(blocks) > len(visible_blocks):
        lines.append(
            f"\n_Showing first {len(visible_blocks)} of {len(blocks)} blocks. "
            "Pass `limit` or read a focused `block_id`._"
        )

    return format_limited_text_response(
        title=f"DOCX Blocks: {doc_id}",
        text="\n".join(lines),
        source_path=_docx_artifact_path(doc_id, "ir.json"),
        language="markdown",
        guidance="use `get_docx_content(doc_id, block_id=...)` for focused block reads",
    )


@mcp.tool()
async def list_docx_documents() -> str:
    """
    列出所有已攝入的 DOCX/DFM 文件。

    Returns:
        DOCX 文件摘要列表
    """
    documents = await docx_service.list_documents()
    if not documents:
        return "No DOCX documents found. Use `ingest_docx` to process .doc/.docx files."

    lines = [f"# DOCX Documents ({len(documents)} total)\n"]
    lines.append("| doc_id | filename | blocks | output.docx | output.pdf | updated |")
    lines.append("|---|---|---:|:---:|:---:|---|")

    for doc in documents:
        lines.append(
            "| {doc_id} | {filename} | {total_blocks} | {has_docx} | {has_pdf} | {updated_at} |".format(
                doc_id=escape_table_cell(doc.get("doc_id", "")),
                filename=escape_table_cell(doc.get("filename", "")),
                total_blocks=escape_table_cell(doc.get("total_blocks", 0)),
                has_docx="✅" if doc.get("has_output_docx") else "-",
                has_pdf="✅" if doc.get("has_output_pdf") else "-",
                updated_at=escape_table_cell(doc.get("updated_at", "")),
            )
        )

    return "\n".join(lines)


@mcp.tool()
async def delete_docx(doc_id: str, force: bool = False) -> str:
    """
    刪除已攝入的 DOCX/DFM 文件及其本地 artifacts。

    會移除 data/{doc_id}/ 下的 IR、DFM、原始 DOCX、輸出檔與備份。有其他 agent
    持有有效租約時拒絕；確認 holder 已不存在後才用 force=True。
    """
    result = await docx_service.delete_docx(doc_id, force=force)
    if not result.get("success"):
        return f"❌ 刪除失敗：{result.get('error', '未知錯誤')}"

    return (
        "✅ DOCX 文件已刪除\n"
        f"- **doc_id**: `{result.get('doc_id', '')}`\n"
        f"- **filename**: {result.get('filename', '')}"
    )


@mcp.tool()
async def convert_docx_to_doc(
    doc_id: str,
    output_path: str | None = None,
    mode: str = "fidelity",
    async_mode: bool = True,
    ctx: Context | None = None,
) -> str:
    """
    將已攝入的 DOCX/DFM 文件轉為 DOC。

    轉換範圍：
    - `fidelity`：保真模式。以目前 DFM 狀態重建 DOCX，再用 LibreOffice 輸出 DOC。
    - `content`：目前不支援；DOCX → DOC 應以保真輸出為主。
    - `async_mode`：預設建立背景 conversion job；設為 False 可沿用同步回傳。
    """
    await log_message(ctx, "info", f"convert_docx_to_doc start: {doc_id}")
    if async_mode:
        parameters = {
            "operation": "docx_to_doc",
            "source": doc_id,
            "target_format": "doc",
            "output_path": output_path,
            "mode": mode,
        }

        async def handler(progress: Any) -> dict[str, Any]:
            await progress.report(
                step=2,
                phase="Converting",
                message=f"Converting {doc_id} to DOC",
            )
            result = await docx_service.convert_to_doc(
                doc_id,
                output_path,
                mode=mode,
            )
            await progress.report(
                step=3,
                phase="Packaging",
                message=f"Finalizing DOC conversion for {doc_id}",
            )
            return conversion_result_payload(
                result,
                operation="docx_to_doc",
                source=doc_id,
                target_format="doc",
            )

        return await create_conversion_job_response(
            job_service,
            operation="docx_to_doc",
            source=doc_id,
            target_format="doc",
            parameters=parameters,
            handler=handler,
            ctx=ctx,
        )

    await report_progress(ctx, 10, message=f"Converting {doc_id} to DOC")
    result = await docx_service.convert_to_doc(doc_id, output_path, mode=mode)
    if not result.get("success"):
        await log_message(ctx, "error", f"convert_docx_to_doc failed: {doc_id}")
        return f"❌ 轉換失敗：{result.get('error', '未知錯誤')}"

    await report_progress(ctx, 100, message=f"Finished DOC conversion for {doc_id}")

    return (
        "✅ DOCX → DOC 轉換成功\n"
        f"- **doc_id**: `{result.get('doc_id', '')}`\n"
        f"- **mode**: {result.get('mode', mode)}\n"
        f"- **output_path**: `{result.get('output_path', '')}`"
    )


@mcp.tool()
async def convert_docx_to_pdf(
    doc_id: str,
    output_path: str | None = None,
    mode: str = "fidelity",
    async_mode: bool = True,
    ctx: Context | None = None,
) -> str:
    """
    將已攝入的 DOCX/DFM 文件轉為 PDF。

    轉換範圍：
    - `fidelity`：保真模式。以目前 DFM 狀態重建 DOCX，再用 LibreOffice 輸出 PDF。
    - `content`：目前不支援；DOCX → PDF 應以保真輸出為主。
    - `async_mode`：預設建立背景 conversion job；設為 False 可沿用同步回傳。
    """
    await log_message(ctx, "info", f"convert_docx_to_pdf start: {doc_id}")
    if async_mode:
        parameters = {
            "operation": "docx_to_pdf",
            "source": doc_id,
            "target_format": "pdf",
            "output_path": output_path,
            "mode": mode,
        }

        async def handler(progress: Any) -> dict[str, Any]:
            await progress.report(
                step=2,
                phase="Converting",
                message=f"Converting {doc_id} to PDF",
            )
            result = await docx_service.convert_to_pdf(
                doc_id,
                output_path,
                mode=mode,
            )
            await progress.report(
                step=3,
                phase="Packaging",
                message=f"Finalizing PDF conversion for {doc_id}",
            )
            return conversion_result_payload(
                result,
                operation="docx_to_pdf",
                source=doc_id,
                target_format="pdf",
            )

        return await create_conversion_job_response(
            job_service,
            operation="docx_to_pdf",
            source=doc_id,
            target_format="pdf",
            parameters=parameters,
            handler=handler,
            ctx=ctx,
        )

    await report_progress(ctx, 10, message=f"Converting {doc_id} to PDF")
    result = await docx_service.convert_to_pdf(doc_id, output_path, mode=mode)
    if not result.get("success"):
        await log_message(ctx, "error", f"convert_docx_to_pdf failed: {doc_id}")
        return f"❌ 轉換失敗：{result.get('error', '未知錯誤')}"

    await report_progress(ctx, 100, message=f"Finished PDF conversion for {doc_id}")

    return (
        "✅ DOCX → PDF 轉換成功\n"
        f"- **doc_id**: `{result.get('doc_id', '')}`\n"
        f"- **mode**: {result.get('mode', mode)}\n"
        f"- **output_path**: `{result.get('output_path', '')}`"
    )


@mcp.tool()
async def convert_docx_to_odt(
    doc_id: str,
    output_path: str | None = None,
    mode: str = "fidelity",
    async_mode: bool = True,
    ctx: Context | None = None,
) -> str:
    """
    將已攝入的 DOCX/DFM 文件轉為 ODT (OpenDocument Text)。

    轉換範圍：
    - `fidelity`：保真模式。以目前 DFM 狀態重建 DOCX，再用 LibreOffice 輸出 ODT。
    - `content`：目前不支援。
    - `async_mode`：預設建立背景 conversion job；設為 False 可沿用同步回傳。

    用途：
    - 匯出為 OpenDocument 格式以便在 LibreOffice Writer 中編輯。
    - 與 ODT/ODS 攝入功能搭配，實現 DOCX ↔ ODT 雙向轉換。

    注意：
    - 攝入支援 .odt 和 .ods（LibreOffice 自動轉為 .docx）。
    - 匯出僅支援 ODT（非 ODS），因 DOCX 是文書處理格式、ODS 是試算表格式，無法直接互轉。
    """
    await log_message(ctx, "info", f"convert_docx_to_odt start: {doc_id}")
    if async_mode:
        parameters = {
            "operation": "docx_to_odt",
            "source": doc_id,
            "target_format": "odt",
            "output_path": output_path,
            "mode": mode,
        }

        async def handler(progress: Any) -> dict[str, Any]:
            await progress.report(
                step=2,
                phase="Converting",
                message=f"Converting {doc_id} to ODT",
            )
            result = await docx_service.convert_to_odt(
                doc_id,
                output_path,
                mode=mode,
            )
            await progress.report(
                step=3,
                phase="Packaging",
                message=f"Finalizing ODT conversion for {doc_id}",
            )
            return conversion_result_payload(
                result,
                operation="docx_to_odt",
                source=doc_id,
                target_format="odt",
            )

        return await create_conversion_job_response(
            job_service,
            operation="docx_to_odt",
            source=doc_id,
            target_format="odt",
            parameters=parameters,
            handler=handler,
            ctx=ctx,
        )

    await report_progress(ctx, 10, message=f"Converting {doc_id} to ODT")
    result = await docx_service.convert_to_odt(doc_id, output_path, mode=mode)
    if not result.get("success"):
        await log_message(ctx, "error", f"convert_docx_to_odt failed: {doc_id}")
        return f"❌ 轉換失敗：{result.get('error', '未知錯誤')}"

    await report_progress(ctx, 100, message=f"Finished ODT conversion for {doc_id}")

    return (
        "✅ DOCX → ODT 轉換成功\n"
        f"- **doc_id**: `{result.get('doc_id', '')}`\n"
        f"- **mode**: {result.get('mode', mode)}\n"
        f"- **output_path**: `{result.get('output_path', '')}`"
    )


@mcp.tool()
async def docx_validate_roundtrip(
    doc_id: str,
    output_path: str | None = None,
    strict: bool = False,
    ctx: Context | None = None,
) -> str:
    """
    驗證 docx → DFM → docx 的往返保真度 (Round-Trip Fidelity)。

    此工具程式化地比對原始 .docx 與重建後的 .docx，產生結構化報告。
    AI agent 無法直接查看 docx 渲染結果，因此使用此工具驗證編輯後的 docx
    是否正確保留了所有內容。

    比對六大維度：
    1. 結構 (Structure): 段落數、表格數、圖片數
    2. 文字 (Text): 逐段逐段純文字比對
    3. 格式 (Formatting): bold/italic/font/size/color
    4. 表格 (Table): 逐儲存格內容比對
    5. 媒體 (Media): 圖片 hash 比對
    6. 樣式 (Style): 段落樣式名稱比對

    使用方式：
    1. 先用 ingest_docx 攝入原始 docx
    2. 可選：用 get_docx_content / save_docx 做些編輯
    3. 呼叫此工具，取得結構化比對報告

    Args:
        doc_id: 文件 ID（由 ingest_docx 產生）
        output_path: 可選，指定輸出的 .docx 路徑。預設使用 data/{doc_id}/output.docx
        strict: 若為 True，啟用 fail-closed 嚴格驗證；任何結構/文字/格式/表格/媒體/樣式差異都視為失敗

    Returns:
        Markdown 格式的驗證報告（含保真度分數和差異列表）
    """
    await log_message(ctx, "info", f"docx_validate_roundtrip start: {doc_id}")
    await report_progress(ctx, 10, message=f"Loading original DOCX for {doc_id}")
    doc_dir = docx_service.repository.get_doc_dir(doc_id)
    original_path = doc_dir / "original.docx"

    if not original_path.exists():
        return (
            f"❌ 找不到原始檔案：{original_path}\n請先用 ingest_docx 攝入 .docx 文件。"
        )

    # Load IR
    ir = docx_service._load_ir(doc_id)
    if ir is None:
        return f"❌ 找不到 IR：{doc_id}\n請先用 ingest_docx 攝入。"

    # Determine output path
    try:
        rebuilt_path = resolve_document_output_path(
            doc_dir,
            output_path,
            default_name="roundtrip_validation.docx",
            allowed_suffixes={".docx"},
        )
    except ValueError as e:
        return f"❌ {e!s}"

    # Rebuild docx from current IR state
    try:
        await report_progress(
            ctx, 50, message=f"Rebuilding round-trip DOCX for {doc_id}"
        )
        docx_service.adapter.ir_to_docx(ir, doc_dir, rebuilt_path)
    except Exception as e:
        return f"❌ 重建 docx 失敗：{e}"

    # Validate
    await report_progress(ctx, 80, message=f"Validating rebuilt DOCX for {doc_id}")
    report = docx_validator.validate(original_path, rebuilt_path, strict=strict)
    await report_progress(
        ctx, 100, message=f"Finished round-trip validation for {doc_id}"
    )

    return format_limited_text_response(
        title=f"DOCX Roundtrip Validation: {doc_id}",
        text=report.to_markdown(),
        source_path=rebuilt_path,
        language="markdown",
        guidance="inspect the rebuilt DOCX artifact or rerun with focused validation inputs",
    )


_LEASE_RESULT_GUIDANCE = (
    "Check out fewer blocks (or read one with docx(op='get', block_id=...)); the "
    "lease_token is kept in this summary so you can still commit or release."
)


_LEASE_ESSENTIAL_KEYS = (
    "success",
    "error",
    "committed",
    "doc_id",
    "lease_token",
    "lease_id",
    "holder",
    "revision",
    "previous_revision",
    "expires_at",
    "ttl_seconds",
    "block_ids",
    "replayed",
    "lease_released",
    "output_path",
    "integrity",
    "storage_warning",
)


def _lease_response(title: str, payload: dict[str, Any], max_chars: int | None) -> Any:
    """Bound a lease result without ever dropping the lease token."""
    text = json.dumps(payload, ensure_ascii=False, default=str, indent=2)
    if not text_exceeds_response_limit(text, max_chars):
        return payload
    summary: dict[str, Any] = {
        key: payload[key] for key in _LEASE_ESSENTIAL_KEYS if key in payload
    }
    if isinstance(payload.get("blocks"), list):
        summary["blocks"] = [
            {key: block.get(key) for key in ("block_id", "type", "base_hash")}
            for block in payload["blocks"]
            if isinstance(block, dict)
        ]
    summary.update(
        {
            "response_truncated": True,
            "content_chars": len(text),
            "sha256": text_sha256(text),
            "title": title,
            "next": _LEASE_RESULT_GUIDANCE,
        }
    )
    return summary


@mcp.tool()
async def docx(
    op: str,
    file_path: str | None = None,
    doc_id: str | None = None,
    block_id: str | None = None,
    dfm_content: str | None = None,
    output_path: str | None = None,
    from_md: bool = False,
    force: bool = False,
    track_changes: bool = False,
    revision_author: str | None = None,
    revision_base: str = "original",
    strict: bool = False,
    max_chars: int | None = None,
    block_ids: list[str] | None = None,
    holder: str | None = None,
    ttl_seconds: int | None = None,
    lease_token: str | None = None,
    lease_id: str | None = None,
    edits: dict[str, str] | None = None,
    keep_lease: bool = False,
    wait: bool = False,
    reset: bool = False,
    request_id: str | None = None,
    ctx: Context | None = None,
) -> Any:
    """
    Consolidated DOCX/DFM entrypoint.

    The legacy DOCX tools remain registered and keep their original parameters
    and output formats. This wrapper adds an operation-based facade.

    Operation -> parameters:
    - ``ingest``: file_path. An already ingested file returns its existing state
      (edits kept, current revision); reset=true discards every edit.
    - ``get``: doc_id (block_id, max_chars optional).
    - ``save``: doc_id, dfm_content (or from_md), output_path, force,
      track_changes, revision_author (default "Asset-Aware MCP"), revision_base.
      A DFM based on an older ``revision`` is 3-way merged or refused with the
      conflicting block ids; blocks leased by another agent are refused.
    - ``list`` / ``list_blocks`` / ``validate``: as before. ``delete``: doc_id;
      refused while another agent holds a live lease unless force=true.

    Multi-agent block leases (several agents edit one document concurrently):
    - ``checkout``: doc_id, block_ids, holder (agent name), ttl_seconds
      (default 900, max 3600), optional request_id (retrying with the same
      request_id returns the same lease with a fresh token). Returns lease_token
      (secret, never dropped from the response), lease_id, each block's DFM
      fragment and base_hash, and the document revision. Fails fast if another
      live lease holds any block (wait=true is not supported). Tables nested in
      a table are leased with their parent table.
    - ``commit``: doc_id, lease_token, edits={block_id: edited fragment}; only
      leased blocks, applied on top of the current document (others' commits are
      kept); same cumulative write-back and post-save verification as save;
      optional output_path, track_changes, revision_author (default: holder, so
      Word shows which agent changed which block), revision_base, keep_lease,
      force (content-shrink/post-save override only).
    - ``release``: doc_id, lease_token. ``renew``: doc_id, lease_token,
      ttl_seconds. ``leases``: doc_id (holders, blocks, expiry; never tokens).
    - ``break_lease``: doc_id, lease_id; expired leases only unless force=true
      (administrative; the holder's pending commit will fail).

    Do not hold leases while idle: commit or release promptly and renew only
    while actively editing.
    """
    operation = _normalize_op(op)
    if operation in {"ingest", "import"}:
        if not file_path:
            return _missing_docx_param("file_path")
        if reset:
            return await ingest_docx(file_path, reset=True, ctx=ctx)
        return await ingest_docx(file_path, ctx=ctx)
    if operation in {"get", "content", "read"}:
        if not doc_id:
            return _missing_docx_param("doc_id")
        return await get_docx_content(doc_id, block_id=block_id, max_chars=max_chars)
    if operation == "save":
        if not doc_id:
            return _missing_docx_param("doc_id")
        return await save_docx(
            doc_id,
            dfm_content=dfm_content,
            output_path=output_path,
            from_md=from_md,
            force=force,
            track_changes=track_changes,
            revision_author=revision_author or "Asset-Aware MCP",
            revision_base=revision_base,
            ctx=ctx,
        )
    if operation in {"list", "list_documents"}:
        return await list_docx_documents()
    if operation == "delete":
        if not doc_id:
            return _missing_docx_param("doc_id")
        if force:
            return await delete_docx(doc_id, force=True)
        return await delete_docx(doc_id)
    if operation in {"list_blocks", "blocks"}:
        if not doc_id:
            return _missing_docx_param("doc_id")
        return await list_docx_blocks(doc_id)
    if operation in {"validate", "validate_roundtrip"}:
        if not doc_id:
            return _missing_docx_param("doc_id")
        return await docx_validate_roundtrip(
            doc_id,
            output_path=output_path,
            strict=strict,
            ctx=ctx,
        )
    if operation in _LEASE_OPS:
        if not doc_id:
            return _missing_docx_param("doc_id")
        return await _docx_lease_op(
            operation,
            doc_id,
            block_ids=block_ids,
            holder=holder,
            ttl_seconds=ttl_seconds,
            lease_token=lease_token,
            lease_id=lease_id,
            edits=edits,
            output_path=output_path,
            track_changes=track_changes,
            revision_author=revision_author,
            revision_base=revision_base,
            keep_lease=keep_lease,
            force=force,
            wait=wait,
            request_id=request_id,
            max_chars=max_chars,
            ctx=ctx,
        )

    return _unsupported_docx_op(
        "docx",
        op,
        {
            "delete",
            "get",
            "ingest",
            "list",
            "list_blocks",
            "save",
            "validate",
            *_LEASE_OPS,
        },
    )


_LEASE_OPS = frozenset(
    {"checkout", "commit", "release", "renew", "leases", "break_lease"}
)


async def _docx_lease_op(
    operation: str,
    doc_id: str,
    *,
    block_ids: list[str] | None,
    holder: str | None,
    ttl_seconds: int | None,
    lease_token: str | None,
    lease_id: str | None,
    edits: dict[str, str] | None,
    output_path: str | None,
    track_changes: bool,
    revision_author: str | None,
    revision_base: str,
    keep_lease: bool,
    force: bool,
    wait: bool,
    max_chars: int | None,
    ctx: Context | None,
    request_id: str | None = None,
) -> Any:
    """Route block-lease operations to the application service."""
    if operation == "checkout":
        result = await docx_service.checkout_blocks(
            doc_id,
            block_ids,
            holder=holder,
            ttl_seconds=ttl_seconds,
            wait=wait,
            request_id=request_id,
        )
        return _lease_response(f"DOCX checkout: {doc_id}", result, max_chars)
    if operation == "commit":
        if not lease_token:
            return _missing_docx_param("lease_token")
        await log_message(ctx, "info", f"docx commit start: {doc_id}")
        result = await docx_service.commit_block_lease(
            doc_id,
            lease_token,
            edits,
            output_path=output_path,
            track_changes=track_changes,
            revision_author=revision_author,
            revision_base=revision_base,
            keep_lease=keep_lease,
            force=force,
        )
        if result.get("success"):
            await log_message(ctx, "info", f"docx commit done: {doc_id}")
        else:
            await log_message(ctx, "error", f"docx commit failed: {doc_id}")
        return _lease_response(f"DOCX commit: {doc_id}", result, max_chars)
    if operation == "release":
        if not lease_token:
            return _missing_docx_param("lease_token")
        return await docx_service.release_block_lease(doc_id, lease_token)
    if operation == "renew":
        if not lease_token:
            return _missing_docx_param("lease_token")
        return await docx_service.renew_block_lease(doc_id, lease_token, ttl_seconds)
    if operation == "leases":
        result = await docx_service.list_block_leases(doc_id)
        return _lease_response(f"DOCX leases: {doc_id}", result, max_chars)
    if not lease_id:
        return _missing_docx_param("lease_id")
    return await docx_service.break_block_lease(doc_id, lease_id, force=force)


# ============================================================================
# DFM ↔ Table Bridge Tools
# ============================================================================


@mcp.tool()
async def docx_table_to_context(
    doc_id: str,
    block_id: str,
    register: bool = True,
) -> str:
    """
    將 docx 中的表格區塊轉為 TableContext，使其可用 table_manage/table_data 工具結構化編輯。

    這是 DFM 表格與 A2T（Anything-to-Table）系統的橋樑：
    - DFM 表格 → TableContext → table_data (add_rows/update_cell) → table_cite (引用) → 寫回

    轉換後的 TableContext 自動註冊到 table_service，可直接使用以下工具操作：
    - table_data: add_rows, update_cell, delete_row
    - table_cite: add/remove citations
    - table_history: 查看變更歷史
    - table_manage: render (匯出 Excel/Markdown/HTML)

    Args:
        doc_id: 文件 ID（由 ingest_docx 產生）
        block_id: 表格區塊 ID（如 t001, t002）
        register: 是否自動註冊到 table_service（預設 True）

    Returns:
        TableContext 摘要（table_id + 欄位 + 行數）
    """
    ir = docx_service._load_ir(doc_id)
    if ir is None:
        return f"❌ 找不到文件 {doc_id}，請先 ingest_docx。"

    block = ir.find_block(block_id)
    if block is None:
        return f"❌ 找不到區塊 {block_id}（doc_id={doc_id}）"

    try:
        tc = dfm_table_bridge.block_to_table_context(
            block,
            doc_id=doc_id,
            source_description=f"Table {block_id} from {ir.source_filename}",
            source_revision_id=ir.checksum,
        )
    except ValueError as e:
        return f"❌ 轉換失敗：{e}"

    # Register to table_service for subsequent tool operations
    if register:
        table_service._tables[tc.id] = tc

    lines = [
        "✅ 表格區塊已轉為 TableContext",
        "",
        f"- **table_id**: `{tc.id}`",
        f"- **來源區塊**: `{block_id}`",
        f"- **欄位數**: {len(tc.columns)}",
        f"- **行數**: {tc.row_count}",
        "",
        "**欄位定義**：",
    ]
    lines.extend(f"  - `{col.name}` ({col.type})" for col in tc.columns)

    if tc.rows:
        lines.append("")
        lines.append("**前 3 行預覽**：")
        preview_rows = tc.rows[:3]
        col_names = tc.column_names
        lines.append("| " + " | ".join(escape_table_cell(c) for c in col_names) + " |")
        lines.append("| " + " | ".join("---" for _ in col_names) + " |")
        for row in preview_rows:
            cells = [_escape_preview_cell(row.get(c, ""), 30) for c in col_names]
            lines.append("| " + " | ".join(cells) + " |")

    if register:
        lines.append("")
        lines.append("💡 **接下來可用以下工具操作此表格**：")
        lines.append(f"  - `table_data(op='add_rows', table_id='{tc.id}', ...)`")
        lines.append(f"  - `table_data(op='update_cell', table_id='{tc.id}', ...)`")
        lines.append(f"  - `table_cite(op='add', table_id='{tc.id}', ...)`")
        lines.append(
            f"  - `table_manage(op='render', table_id='{tc.id}', format='excel')`"
        )
        lines.append(
            f"  - 完成後用 `docx_table_from_context(doc_id='{doc_id}', block_id='{block_id}', table_id='{tc.id}')` 寫回"
        )

    return "\n".join(lines)


@mcp.tool()
async def docx_table_from_context(
    doc_id: str,
    block_id: str,
    table_id: str,
    save_dfm: bool = True,
) -> str:
    """
    將 TableContext 的資料寫回 docx 的 DFM 表格區塊。

    這是 docx_table_to_context 的反向操作：
    TableContext (已用 table_data 等工具編輯) → 覆蓋 DFM 表格內容

    保留原始的 Word 表格樣式、欄位寬度、合併儲存格等格式資訊，僅更新文字內容。

    Args:
        doc_id: 文件 ID
        block_id: 表格區塊 ID（如 t001）
        table_id: TableContext 的 table_id（由 docx_table_to_context 產生）
        save_dfm: 是否自動更新 content.dfm 檔案（預設 True）

    Returns:
        操作結果
    """
    tc = table_service._tables.get(table_id)
    if tc is None:
        return (
            f"❌ 找不到 TableContext `{table_id}`，請先用 docx_table_to_context 轉換。"
        )
    if getattr(tc, "source_doc_id", "") and tc.source_doc_id != doc_id:
        return (
            f"❌ 寫回失敗：TableContext `{table_id}` 屬於文件 "
            f"`{tc.source_doc_id}`，不能寫入 `{doc_id}`。"
        )
    if getattr(tc, "source_block_id", "") and tc.source_block_id != block_id:
        return (
            f"❌ 寫回失敗：TableContext `{table_id}` 來源區塊是 "
            f"`{tc.source_block_id}`，不能寫入 `{block_id}`。"
        )

    if docx_service._load_ir(doc_id) is None:
        return f"❌ 找不到文件 {doc_id}"

    def apply_table(ir: Any) -> None:
        dfm_table_bridge.apply_table_context_to_ir(ir, block_id, tc)
        # --- Post-write validation: verify cell content survived serialization ---
        block_after = ir.find_block(block_id)
        if not (block_after and block_after.content):
            return
        from src.application.dfm_table_bridge import _parse_md_table

        written_rows = _parse_md_table(block_after.content)
        if written_rows is None:
            return
        # Skip header row (index 0) — compare data rows only
        written_data = written_rows[1:]
        source_nonempty = sum(
            1 for row in tc.rows for c in tc.column_names if str(row.get(c, "")).strip()
        )
        written_nonempty = sum(
            1 for row in written_data for cell in row if cell.strip()
        )
        if source_nonempty > 0 and written_nonempty == 0:
            raise ValueError(
                f"TableContext 有 {source_nonempty} 個非空 cell，"
                f"但序列化後全部遺失。請檢查 cell 內容格式。"
            )
        if source_nonempty > 0 and written_nonempty < source_nonempty * 0.5:
            raise ValueError(
                f"TableContext 有 {source_nonempty} 個非空 cell，"
                f"但序列化後僅剩 {written_nonempty} 個。疑似資料遺失。"
            )

    # Runs under the cross-process document lock, refuses blocks leased by
    # another agent and records a new content revision.
    update = await docx_service.update_ir_blocks(
        doc_id,
        [block_id],
        apply_table,
        actor=f"TableContext {table_id}",
        write_dfm=save_dfm,
    )
    if not update.get("success"):
        return f"❌ 寫回失敗：{update.get('error', '未知錯誤')}"

    doc_dir = docx_service.repository.get_doc_dir(doc_id)
    result_lines = [
        "✅ TableContext 已寫回 DFM 表格區塊",
        "",
        f"- **文件**: `{doc_id}`",
        f"- **區塊**: `{block_id}`",
        f"- **表格**: `{table_id}`",
        f"- **行數**: {tc.row_count}",
    ]
    if update.get("revision"):
        result_lines.append(f"- **內容版本 (revision)**: `{update.get('revision')}`")

    if save_dfm:
        result_lines.append(f"- **DFM 已更新**: `{doc_dir / 'content.dfm'}`")
        result_lines.append(f"- **Split Markdown 已更新**: `{doc_dir / 'content.md'}`")
        result_lines.append(f"- **Format YAML 已更新**: `{doc_dir / 'format.yaml'}`")

    result_lines.append("")
    result_lines.append(
        f"💡 用 `save_docx(doc_id='{doc_id}', ...)` 可將修改寫回 .docx 檔案。"
    )

    return "\n".join(result_lines)


@mcp.tool()
async def docx_chart_data(
    doc_id: str,
    block_id: str,
    register: bool = True,
) -> str:
    """
    提取 docx 圖表的底層資料為表格格式 (TableContext)。

    Word 圖表內嵌 Excel 資料。此工具提取該數據為結構化表格，
    可用 table_manage 的 render 功能匯出為 Excel/Markdown/HTML。

    如有原始 chart XML 可解析系列資料（長條圖、折線圖、圓餅圖等）。
    若無 XML，則回傳圖表的元資料摘要。

    Args:
        doc_id: 文件 ID
        block_id: 圖表區塊 ID（如 c001）
        register: 是否自動註冊到 table_service（預設 True）

    Returns:
        圖表資料的 TableContext 摘要
    """
    ir = docx_service._load_ir(doc_id)
    if ir is None:
        return f"❌ 找不到文件 {doc_id}"

    block = ir.find_block(block_id)
    if block is None:
        return f"❌ 找不到區塊 {block_id}（doc_id={doc_id}）"

    if block.block_type.value != "chart":
        return f"❌ 區塊 {block_id} 類型為 {block.block_type.value}，不是 chart"

    # Try to load chart XML from preserved parts
    chart_xml = None
    doc_dir = docx_service.repository.get_doc_dir(doc_id)
    if block.binary_ref:
        chart_path = doc_dir / block.binary_ref
        if chart_path.exists():
            import contextlib

            with contextlib.suppress(UnicodeDecodeError):
                chart_xml = read_text_file(chart_path, hint=str(chart_path))

    tc = dfm_table_bridge.extract_chart_data(block, chart_xml)
    if tc is None:
        return f"❌ 無法提取圖表 {block_id} 的資料"

    if register:
        table_service._tables[tc.id] = tc

    lines = [
        "✅ 圖表資料已轉為 TableContext",
        "",
        f"- **table_id**: `{tc.id}`",
        f"- **來源區塊**: `{block_id}`",
        f"- **圖表類型**: {block.chart_type or 'unknown'}",
        f"- **欄位數**: {len(tc.columns)}",
        f"- **行數**: {tc.row_count}",
    ]

    if tc.rows:
        lines.append("")
        col_names = tc.column_names
        lines.append("| " + " | ".join(escape_table_cell(c) for c in col_names) + " |")
        lines.append("| " + " | ".join("---" for _ in col_names) + " |")
        for row in tc.rows[:10]:
            cells = [_escape_preview_cell(row.get(c, ""), 20) for c in col_names]
            lines.append("| " + " | ".join(cells) + " |")
        if tc.row_count > 10:
            lines.append(f"... 共 {tc.row_count} 行")

    if register:
        lines.append("")
        lines.append("💡 **可用以下工具操作此資料**：")
        lines.append(
            f"  - `table_manage(op='render', table_id='{tc.id}', format='excel')` 匯出 Excel"
        )
        lines.append(
            f"  - `table_manage(op='render', table_id='{tc.id}', format='markdown')` 匯出 MD"
        )
        lines.append(
            f"  - `table_data(op='update_cell', table_id='{tc.id}', ...)` 修改數據"
        )

    return "\n".join(lines)


def _coerce_target_table(
    *,
    table_id: str | None,
    target_columns: list[str] | None,
    target_rows: list[dict[str, Any]] | None,
) -> tuple[list[str] | None, list[dict[str, Any]] | None, str]:
    if table_id:
        tc = table_service._tables.get(table_id)
        if tc is None:
            raise ValueError(f"TableContext `{table_id}` not found")
        return list(tc.column_names), [dict(row) for row in tc.rows], f"`{table_id}`"
    if target_columns is not None or target_rows is not None:
        return target_columns, target_rows, "inline target"
    return None, None, "current table"


@mcp.tool()
async def docx_table_edit_plan(
    doc_id: str,
    block_id: str,
    table_id: str | None = None,
    target_columns: list[str] | None = None,
    target_rows: list[dict[str, Any]] | None = None,
) -> str:
    """
    Plan a DOCX table write-back before applying structural changes.

    The current DFM bridge is safest for same-shape cell text updates. This
    plan separates safe cell updates from row/column/header structural changes
    so the caller can review risk before `docx_table_from_context`.
    """
    ir = docx_service._load_ir(doc_id)
    if ir is None:
        return f"❌ 找不到文件 {doc_id}"

    block = ir.find_block(block_id)
    if block is None:
        return f"❌ 找不到區塊 {block_id}（doc_id={doc_id}）"
    if block.block_type.value != "table":
        return f"❌ 區塊 {block_id} 類型為 {block.block_type.value}，不是 table"

    from src.application.dfm_table_bridge import _parse_md_table

    rows_2d = _parse_md_table(block.content)
    if not rows_2d:
        return f"❌ 區塊 {block_id} 沒有可解析的 Markdown table"

    current_columns = rows_2d[0]
    current_rows = [
        {
            column: row[index] if index < len(row) else ""
            for index, column in enumerate(current_columns)
        }
        for row in rows_2d[1:]
    ]

    try:
        resolved_columns, resolved_rows, target_label = _coerce_target_table(
            table_id=table_id,
            target_columns=target_columns,
            target_rows=target_rows,
        )
    except ValueError as e:
        return f"❌ 無法建立表格變更計畫：{e}"

    desired_columns = resolved_columns or current_columns
    desired_rows = resolved_rows if resolved_rows is not None else current_rows

    current_shape = (len(current_rows), len(current_columns))
    target_shape = (len(desired_rows), len(desired_columns))

    added_columns = [col for col in desired_columns if col not in current_columns]
    removed_columns = [col for col in current_columns if col not in desired_columns]
    renamed_columns: list[tuple[str, str]] = []
    if (
        len(current_columns) == len(desired_columns)
        and current_columns != desired_columns
    ):
        renamed_columns = [
            (old, new)
            for old, new in zip(current_columns, desired_columns, strict=False)
            if old != new
        ]

    add_rows = max(0, len(desired_rows) - len(current_rows))
    delete_rows = max(0, len(current_rows) - len(desired_rows))
    shared_rows = min(len(current_rows), len(desired_rows))
    shared_columns = [col for col in current_columns if col in desired_columns]
    update_cells = 0
    for row_index in range(shared_rows):
        for column in shared_columns:
            if str(current_rows[row_index].get(column, "")) != str(
                desired_rows[row_index].get(column, "")
            ):
                update_cells += 1

    structural_changes = bool(
        added_columns or removed_columns or renamed_columns or add_rows or delete_rows
    )
    safe_write_supported = not structural_changes

    lines = [
        "# DOCX Table Structural Edit Plan",
        "",
        f"- **doc_id:** `{doc_id}`",
        f"- **block_id:** `{block_id}`",
        f"- **target:** {target_label}",
        f"- **current_shape:** {current_shape[0]} rows x {current_shape[1]} columns",
        f"- **target_shape:** {target_shape[0]} rows x {target_shape[1]} columns",
        f"- **safe_write_back:** {'yes' if safe_write_supported else 'review required'}",
        "",
        "## Planned Operations",
        "",
        f"- `update_cell`: {update_cells}",
        f"- `add_rows`: {add_rows}",
        f"- `delete_rows`: {delete_rows}",
        f"- `add_columns`: {len(added_columns)}",
        f"- `delete_columns`: {len(removed_columns)}",
        f"- `rename_columns`: {len(renamed_columns)}",
    ]

    if added_columns:
        lines.append(f"  - added: {', '.join(f'`{c}`' for c in added_columns)}")
    if removed_columns:
        lines.append(f"  - removed: {', '.join(f'`{c}`' for c in removed_columns)}")
    if renamed_columns:
        renamed = ", ".join(f"`{old}` → `{new}`" for old, new in renamed_columns)
        lines.append(f"  - renamed: {renamed}")

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
        ]
    )
    if safe_write_supported:
        lines.append(
            "Same-shape update only. `docx_table_from_context` can write back "
            "cell text while preserving the existing table structure."
        )
    else:
        lines.append(
            "Structural change detected. Review this plan before write-back, keep "
            "a separate output copy, then run `save_docx(...)` followed by "
            "`docx_validate_roundtrip(strict=True)` after applying changes."
        )

    if block.merged_cells:
        lines.append("")
        lines.append(
            "⚠️ Existing merged cells are present; column/row changes need extra review."
        )

    return "\n".join(lines)


@mcp.tool()
async def docx_table(
    op: str,
    doc_id: str | None = None,
    block_id: str | None = None,
    table_id: str | None = None,
    target_columns: list[str] | None = None,
    target_rows: list[dict[str, Any]] | None = None,
    register: bool = True,
    save_dfm: bool = True,
) -> Any:
    """
    Consolidated DOCX table bridge entrypoint.

    Existing docx_table_* tools remain available for clients that rely on their
    names or generated allow-lists.
    """
    operation = _normalize_op(op)
    if operation in {"to_context", "extract"}:
        if not doc_id:
            return _missing_docx_param("doc_id")
        if not block_id:
            return _missing_docx_param("block_id")
        return await docx_table_to_context(doc_id, block_id, register=register)
    if operation in {"from_context", "apply"}:
        if not doc_id:
            return _missing_docx_param("doc_id")
        if not block_id:
            return _missing_docx_param("block_id")
        if not table_id:
            return _missing_docx_param("table_id")
        return await docx_table_from_context(
            doc_id,
            block_id,
            table_id,
            save_dfm=save_dfm,
        )
    if operation in {"chart_data", "chart"}:
        if not doc_id:
            return _missing_docx_param("doc_id")
        if not block_id:
            return _missing_docx_param("block_id")
        return await docx_chart_data(doc_id, block_id, register=register)
    if operation in {"edit_plan", "plan", "plan_structure", "structure_plan"}:
        if not doc_id:
            return _missing_docx_param("doc_id")
        if not block_id:
            return _missing_docx_param("block_id")
        return await docx_table_edit_plan(
            doc_id,
            block_id,
            table_id=table_id,
            target_columns=target_columns,
            target_rows=target_rows,
        )

    return _unsupported_docx_op(
        "docx_table",
        op,
        {"chart_data", "edit_plan", "from_context", "to_context"},
    )


@mcp.tool()
async def export_markdown(
    md_text: str | None = None,
    md_path: str | None = None,
    output_path: str | None = None,
    output_format: str = "docx",
    async_mode: bool = True,
    ctx: Context | None = None,
) -> str:
    """
    將 Markdown 文字或檔案直接匯出為 DOCX / PDF / DOC。

    此工具不需要事先 ingest_docx — 直接從 Markdown 建立新文件。
    適用於：
    - 從 AI 生成的 Markdown 內容製作正式文件
    - 將 .md 筆記轉換為可分享的 Word/PDF 格式
    - 快速製作報告、提案、文件

    支援的 Markdown 語法：
    - 標題（# ~ ######）
    - 段落、粗體、斜體、刪除線、行內程式碼
    - 有序/無序列表
    - 表格（含多行 cell，使用 <br> 換行）
    - 程式碼區塊（```）
    - 引用區塊（>）
    - 圖片（![alt](path)，需本地檔案）
    - 水平線（--- / ***）

    轉換流程：
    - DOCX：直接用 python-docx 生成
    - PDF/DOC：先生成 DOCX，再經由 LibreOffice 轉換

    Args:
        md_text: Markdown 內容字串（與 md_path 二擇一）
        md_path: .md 檔案路徑（與 md_text 二擇一）
        output_path: 輸出檔案路徑（預設依據 md_path 或 output.{format}）
        output_format: 輸出格式，"docx"（預設）、"pdf"、"doc"
        async_mode: 預設建立背景 conversion job；設為 False 可沿用同步回傳。
    """
    logger.info(
        "export_markdown | format=%s | md_path=%s | output=%s",
        output_format,
        md_path,
        output_path,
    )
    await log_message(ctx, "info", f"export_markdown start: format={output_format}")
    if async_mode:
        source = md_path or "<inline markdown>"
        parameters = {
            "operation": "markdown_export",
            "source": source,
            "target_format": output_format,
            "output_path": output_path,
            "md_path": md_path,
            "md_text_length": len(md_text or ""),
        }

        async def handler(progress: Any) -> dict[str, Any]:
            await progress.report(
                step=2,
                phase="Converting",
                message=f"Exporting Markdown to {output_format.upper()}",
            )
            result = await docx_service.export_from_markdown(
                md_text=md_text,
                md_path=md_path,
                output_path=output_path,
                output_format=output_format,
            )
            await progress.report(
                step=3,
                phase="Packaging",
                message=f"Finalizing Markdown export to {output_format.upper()}",
            )
            return conversion_result_payload(
                result,
                operation="markdown_export",
                source=source,
                target_format=output_format,
            )

        return await create_conversion_job_response(
            job_service,
            operation="markdown_export",
            source=source,
            target_format=output_format,
            parameters=parameters,
            handler=handler,
            input_files=[md_path] if md_path else [],
            ctx=ctx,
        )

    await report_progress(
        ctx, 10, message=f"Exporting Markdown to {output_format.upper()}"
    )

    result = await docx_service.export_from_markdown(
        md_text=md_text,
        md_path=md_path,
        output_path=output_path,
        output_format=output_format,
    )

    if not result.get("success"):
        await log_message(
            ctx, "error", f"export_markdown failed: format={output_format}"
        )
        return f"❌ 匯出失敗：{result.get('error', '未知錯誤')}"

    await report_progress(
        ctx, 100, message=f"Finished Markdown export to {result['format'].upper()}"
    )

    return (
        f"✅ Markdown → {result['format'].upper()} 匯出成功\n"
        f"- **output_path**: `{result['output_path']}`\n"
        f"- **format**: {result['format']}"
    )
