"""Separate OS process that commits one DOCX block lease (cross-process tests).

Run as ``python -m tests.integration.docx_lease_worker spec.json`` from the
repository root. The JSON spec names the data directory, document, lease token
and edits, and optionally:

* ``go_file`` -- wait until this file exists before committing (start barrier);
* ``slow_seconds`` -- sleep inside the DOCX writer, i.e. while holding the
  document lock, so concurrent commits really contend;
* ``crash_after_ir`` -- hard-exit (``os._exit``) right after ``ir.json`` is
  replaced, before the edit-state transaction commits (crash simulation).

The commit result is written as JSON to ``result_file``.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

CRASH_EXIT_CODE = 17


def main(spec_path: str) -> int:
    spec: dict[str, Any] = json.loads(Path(spec_path).read_text(encoding="utf-8"))

    from src.application.docx_service import DocxService
    from src.infrastructure.file_storage import FileStorage

    service = DocxService(repository=FileStorage(base_dir=Path(spec["data_dir"])))

    slow = float(spec.get("slow_seconds") or 0)
    if slow:
        real_writer = service.adapter.ir_to_docx

        def slow_writer(*args: Any, **kwargs: Any) -> Any:
            time.sleep(slow)
            return real_writer(*args, **kwargs)

        service.adapter.ir_to_docx = slow_writer  # type: ignore[method-assign]

    if spec.get("crash_after_ir"):
        real_save_ir = service._save_ir

        def crashing_save_ir(ir: Any, path: Path) -> None:
            real_save_ir(ir, path)
            if Path(path).name == "ir.json":
                os._exit(CRASH_EXIT_CODE)

        service._save_ir = crashing_save_ir  # type: ignore[method-assign]

    go_file = spec.get("go_file")
    if go_file:
        deadline = time.monotonic() + 60
        while not Path(go_file).exists():
            if time.monotonic() > deadline:
                raise TimeoutError("start barrier never opened")
            time.sleep(0.01)

    result = asyncio.run(
        service.commit_block_lease(
            spec["doc_id"],
            spec["token"],
            spec["edits"],
            track_changes=bool(spec.get("track_changes")),
            output_path=spec.get("output_path"),
        )
    )
    Path(spec["result_file"]).write_text(
        json.dumps(result, ensure_ascii=False, default=str), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
