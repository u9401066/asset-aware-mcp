"""Presentation composition root for the isolated ingest worker process."""

from __future__ import annotations

import asyncio

from src.application.ingest_worker import build_parser, run_worker
from src.presentation import dependencies


async def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.etl_profile:
        dependencies.rebuild_for_profile(args.etl_profile)
    return await run_worker(
        args,
        document_service=dependencies.document_service,
        marker_extractor_factory=dependencies.get_marker_extractor,
    )


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(run(argv))


if __name__ == "__main__":
    raise SystemExit(main())
