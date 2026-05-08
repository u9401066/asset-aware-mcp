"""Pure helpers for isolated document ingestion workers.

The presentation worker CLI owns composition/root imports. This module stays in
the application layer and only provides injectable JSON/progress primitives.
"""

from __future__ import annotations

import argparse
import json
import time
import traceback
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

from src.domain.entities import IngestResult
from src.domain.marker_errors import format_marker_failure


def _parse_page_ranges(raw_value: str) -> list[str]:
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _write_json_atomic(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _write_result(path: Path, result: IngestResult) -> None:
    _write_json_atomic(path, result.model_dump_json(indent=2))


def _make_progress_callback(
    progress_path: Path,
) -> Callable[[int, int, str, str], Awaitable[None]]:
    async def callback(step: int, total: int, phase: str, message: str) -> None:
        payload: dict[str, Any] = {
            "step": step,
            "total": total,
            "phase": phase,
            "message": message,
            "ts": time.time(),
        }
        _write_json_atomic(progress_path, json.dumps(payload, ensure_ascii=False))

    return callback


async def run_worker(
    args: argparse.Namespace,
    *,
    document_service: Any,
    rebuild_for_profile: Callable[[str], Any] | None = None,
    marker_extractor_factory: Callable[[], Any] | None = None,
) -> int:
    result_path = Path(args.result_json)
    progress_callback = (
        _make_progress_callback(Path(args.progress_json))
        if args.progress_json
        else None
    )
    try:
        if args.etl_profile and rebuild_for_profile is not None:
            rebuild_for_profile(args.etl_profile)

        if args.use_marker:
            try:
                if marker_extractor_factory is None:
                    raise RuntimeError("Marker extractor factory is not configured.")
                document_service.marker_extractor = marker_extractor_factory()
            except Exception as exc:
                if args.require_marker:
                    raise RuntimeError(format_marker_failure(exc)) from exc

        results = await document_service.ingest(
            [args.file],
            use_marker=args.use_marker,
            ocr_enabled=args.ocr_enabled,
            ocr_language=args.ocr_language,
            rotate_pages=args.rotate_pages,
            deskew=args.deskew,
            marker_max_pages_per_chunk=args.marker_max_pages_per_chunk,
            extract_figures=args.extract_figures,
            page_ranges=_parse_page_ranges(args.page_ranges_json) or None,
            require_marker=args.require_marker,
            progress_callback=progress_callback,
        )
        result = (
            results[0]
            if results
            else IngestResult(
                doc_id="",
                filename=Path(args.file).name,
                success=False,
                error="Isolated ingest worker returned no result",
            )
        )
        _write_result(result_path, result)
        return 0
    except Exception as exc:
        traceback.print_exc()
        _write_result(
            result_path,
            IngestResult(
                doc_id="",
                filename=Path(args.file).name,
                success=False,
                error=str(exc),
            ),
        )
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True)
    parser.add_argument("--result-json", required=True)
    parser.add_argument("--progress-json", default="")
    parser.add_argument("--use-marker", action="store_true")
    parser.add_argument("--require-marker", action="store_true")
    parser.add_argument("--ocr-enabled", action="store_true")
    parser.add_argument("--ocr-language", default="eng")
    parser.add_argument("--rotate-pages", action="store_true")
    parser.add_argument("--deskew", action="store_true")
    parser.add_argument("--marker-max-pages-per-chunk", type=int, default=0)
    parser.add_argument("--extract-figures", action="store_true")
    parser.add_argument("--page-ranges-json", default="[]")
    parser.add_argument("--etl-profile", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    raise RuntimeError(
        "src.application.ingest_worker is a pure runner. "
        "Use src.presentation.ingest_worker_main as the executable entrypoint."
    )


if __name__ == "__main__":
    raise SystemExit(main())
