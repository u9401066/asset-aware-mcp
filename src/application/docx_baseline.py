"""Immutable ingest baseline for cumulative DOCX write-back.

``save_docx`` always patches the pristine ``original.docx`` package, so the set
of blocks it rewrites (and the post-save integrity expectations) must be
computed against the IR parsed from that same package -- not against the
current, already-edited ``ir.json``. Diffing against ``ir.json`` made every
save after the first one silently drop the earlier edits.

This mixin persists that ingest snapshot as ``baseline_ir.json`` next to
``original.docx``, verifies it before every save, and rebuilds it from
``original.docx`` for document directories created before the snapshot existed
(v1.4.1 and earlier). It never guesses: when the snapshot cannot be proven to
describe ``original.docx`` and the current IR, the save is refused.
"""

from __future__ import annotations

import hashlib
import json
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.application.docx_ir_serialization import DocxIrSerializationMixin
from src.domain.docx_value_objects import DfmBlockType
from src.infrastructure.dfm_parser import BlockEdit, DfmParseResult

if TYPE_CHECKING:
    from src.domain.docx_entities import DocxIR
    from src.infrastructure.dfm_parser import DfmParser
    from src.infrastructure.docx_adapter import DocxAdapter

logger = logging.getLogger(__name__)

BASELINE_IR_FILENAME = "baseline_ir.json"
ORIGINAL_DOCX_FILENAME = "original.docx"
_HASH_CHUNK_SIZE = 1024 * 1024
_REINGEST_HINT = (
    "No output or editable artifact was written. Re-ingest the source DOCX with "
    "ingest_docx and re-apply the edits from content.dfm (previous versions are "
    "kept under .backups/)."
)


class DocxBaselineError(ValueError):
    """Raised when the ingest baseline cannot be trusted for write-back."""


@dataclass(frozen=True)
class DocxSaveBaseline:
    """Ingest-time IR that describes ``original.docx`` exactly."""

    ir: DocxIR
    rebuilt: bool = False


def _sha256_checksum(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_HASH_CHUNK_SIZE):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


class DocxBaselineMixin(DocxIrSerializationMixin):
    """Persist, verify and diff against the immutable DOCX ingest baseline."""

    if TYPE_CHECKING:
        adapter: DocxAdapter
        parser: DfmParser

        def _expected_changed_block_ids(
            self, original_ir: DocxIR, parse_result: Any
        ) -> set[str]: ...

    def _save_baseline_ir(self, ir: DocxIR, doc_dir: Path) -> Path:
        """Write the immutable ingest snapshot next to ``original.docx``."""
        path = doc_dir / BASELINE_IR_FILENAME
        self._save_ir(ir, path)
        return path

    def _load_save_baseline(
        self, doc_dir: Path, current_ir: DocxIR
    ) -> DocxSaveBaseline:
        """Return a verified baseline IR for ``original.docx``.

        Legacy document directories without ``baseline_ir.json`` are migrated by
        re-parsing ``original.docx``; the caller persists the rebuilt snapshot
        only after a successful save.

        Raises:
            DocxBaselineError: when ``original.docx`` or the snapshot cannot be
                proven to match the current IR.
        """
        original_path = doc_dir / ORIGINAL_DOCX_FILENAME
        if not original_path.is_file():
            raise DocxBaselineError(
                f"Cannot save {current_ir.doc_id}: {ORIGINAL_DOCX_FILENAME} is "
                "missing from the document directory, so the edits cannot be "
                f"applied to a known base package. {_REINGEST_HINT}"
            )

        original_checksum = _sha256_checksum(original_path)
        if current_ir.checksum != original_checksum:
            raise DocxBaselineError(
                f"Cannot save {current_ir.doc_id}: {ORIGINAL_DOCX_FILENAME} "
                f"({original_checksum}) no longer matches the checksum recorded "
                f"at ingest ({current_ir.checksum}). Refusing to patch an "
                f"unverified base package. {_REINGEST_HINT}"
            )

        baseline_path = doc_dir / BASELINE_IR_FILENAME
        rebuilt = not baseline_path.exists()
        if rebuilt:
            baseline = self._rebuild_baseline_from_original(original_path, current_ir)
            logger.warning(
                "Legacy DOCX workspace without %s: rebuilt ingest baseline for %s "
                "from %s",
                BASELINE_IR_FILENAME,
                current_ir.doc_id,
                original_path,
            )
        else:
            try:
                data = json.loads(baseline_path.read_text(encoding="utf-8"))
                baseline = self._dict_to_ir(data)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise DocxBaselineError(
                    f"Cannot save {current_ir.doc_id}: {BASELINE_IR_FILENAME} is "
                    f"unreadable ({exc}). {_REINGEST_HINT}"
                ) from exc
            if baseline.checksum != original_checksum:
                raise DocxBaselineError(
                    f"Cannot save {current_ir.doc_id}: {BASELINE_IR_FILENAME} "
                    f"describes {baseline.checksum}, but {ORIGINAL_DOCX_FILENAME} "
                    f"is {original_checksum}. {_REINGEST_HINT}"
                )

        mismatches = self._baseline_structure_mismatches(baseline, current_ir)
        if mismatches:
            source = (
                f"{ORIGINAL_DOCX_FILENAME} (legacy migration)"
                if rebuilt
                else BASELINE_IR_FILENAME
            )
            raise DocxBaselineError(
                f"Cannot save {current_ir.doc_id}: the ingest baseline from "
                f"{source} does not match the block structure of ir.json "
                f"({'; '.join(mismatches[:5])}). Writing would risk losing or "
                f"misplacing edits. {_REINGEST_HINT}"
            )

        return DocxSaveBaseline(ir=baseline, rebuilt=rebuilt)

    def _rebuild_baseline_from_original(
        self, original_path: Path, current_ir: DocxIR
    ) -> DocxIR:
        """Re-parse ``original.docx`` in isolation (no doc-dir side effects).

        The rebuilt IR is round-tripped through the same JSON serialization as
        ``ir.json`` so that both sides of the diff are normalized identically.
        """
        try:
            with tempfile.TemporaryDirectory(prefix="aamcp-docx-baseline-") as tmp:
                parsed = self.adapter.parse_to_ir(original_path, Path(tmp))
                snapshot = Path(tmp) / BASELINE_IR_FILENAME
                self._save_ir(parsed, snapshot)
                rebuilt = self._dict_to_ir(
                    json.loads(snapshot.read_text(encoding="utf-8"))
                )
        except Exception as exc:
            raise DocxBaselineError(
                f"Cannot save {current_ir.doc_id}: this document directory predates "
                f"{BASELINE_IR_FILENAME} and {ORIGINAL_DOCX_FILENAME} could not be "
                f"re-parsed to rebuild the ingest baseline ({exc}). {_REINGEST_HINT}"
            ) from exc
        rebuilt.doc_id = current_ir.doc_id
        rebuilt.source_path = current_ir.source_path
        rebuilt.source_filename = current_ir.source_filename
        rebuilt.created_at = current_ir.created_at
        rebuilt.updated_at = current_ir.created_at
        return rebuilt

    @staticmethod
    def _baseline_structure_mismatches(
        baseline: DocxIR, current_ir: DocxIR
    ) -> list[str]:
        """Prove that edits only changed text, never the block skeleton."""
        if baseline.doc_id != current_ir.doc_id:
            return [f"doc_id {baseline.doc_id!r} != {current_ir.doc_id!r}"]
        if len(baseline.blocks) != len(current_ir.blocks):
            return [
                f"{len(baseline.blocks)} baseline blocks vs "
                f"{len(current_ir.blocks)} current blocks"
            ]

        mismatches: list[str] = []
        for index, (base, current) in enumerate(
            zip(baseline.blocks, current_ir.blocks, strict=True)
        ):
            base_shape = (
                base.id,
                base.block_type,
                base.parent_cell,
                base.metadata.get("parent_table_id"),
            )
            current_shape = (
                current.id,
                current.block_type,
                current.parent_cell,
                current.metadata.get("parent_table_id"),
            )
            if base_shape != current_shape:
                mismatches.append(
                    f"block #{index + 1}: baseline {base.id}/{base.block_type.value} "
                    f"vs current {current.id}/{current.block_type.value}"
                )
            elif base.is_protected and base.content != current.content:
                mismatches.append(
                    f"protected block {base.id} content differs from the baseline"
                )
        return mismatches

    def _net_edits_since_baseline(
        self, baseline: DocxIR, updated_ir: DocxIR
    ) -> DfmParseResult:
        """Express the current IR as one edit set applied to the ingest baseline.

        Feeding this into the same change detection used for a DFM edit keeps
        cumulative write-back semantics identical to a fresh single save.
        """
        baseline_ids = {block.id for block in baseline.blocks}
        edits: list[BlockEdit] = []
        for block in updated_ir.blocks:
            if block.is_protected or block.id not in baseline_ids:
                continue
            if block.block_type == DfmBlockType.TABLE:
                edits.append(
                    BlockEdit(
                        block_id=block.id,
                        new_content=block.content,
                        block_type=block.block_type,
                        table_rows=self.parser._parse_md_table(block.content),
                    )
                )
            elif block.runs:
                edits.append(
                    BlockEdit(
                        block_id=block.id,
                        new_content=block.content,
                        block_type=block.block_type,
                        updated_runs=list(block.runs),
                    )
                )
            else:
                edits.append(
                    BlockEdit(
                        block_id=block.id,
                        new_content=block.content,
                        block_type=block.block_type,
                    )
                )
        return DfmParseResult(
            doc_id=updated_ir.doc_id,
            source=updated_ir.source_filename,
            checksum=updated_ir.checksum,
            edits=edits,
        )

    def _changed_since_baseline(
        self, baseline: DocxIR, updated_ir: DocxIR
    ) -> tuple[set[str], DfmParseResult]:
        """Return block ids that differ from ``original.docx`` plus the net edits."""
        net_edits = self._net_edits_since_baseline(baseline, updated_ir)
        return self._expected_changed_block_ids(baseline, net_edits), net_edits
