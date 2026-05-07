"""Isolated document ingestion worker for long-running Marker jobs.

The MCP server communicates over stdio, so Marker model loading and parsing must
not run in the server process when raw third-party stdout/stderr suppression is
active. This worker writes its structured result to a JSON file instead.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

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


def _write_result(path: Path, result: IngestResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")


async def run_worker(args: argparse.Namespace) -> int:
    result_path = Path(args.result_json)
    try:
        from src.presentation import dependencies

        if args.etl_profile:
            dependencies.rebuild_for_profile(args.etl_profile)

        if args.use_marker:
            try:
                dependencies.document_service.marker_extractor = (
                    dependencies.get_marker_extractor()
                )
            except Exception as exc:
                if args.require_marker:
                    raise RuntimeError(format_marker_failure(exc)) from exc

        results = await dependencies.document_service.ingest(
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
    return asyncio.run(run_worker(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
