"""Run actual default-model Codex, sharing the isolated scan fixture harness."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from tests.codex_pdf.fixtures import build_pdf, sha256
from tests.codex_pdf.run import command, execute
from tests.codex_table_totals.audit import write_audit
from tests.codex_table_totals.scenario import prompt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    workspace = output / "workspace"
    workspace.mkdir()
    source = workspace / "source.pdf"
    build_pdf(source, "scanned")
    repo = Path(__file__).resolve().parents[2]
    expected = {
        "source_sha256": sha256(source),
        "source_mtime_ns": source.stat().st_mtime_ns,
        "server_source_sha256": hashlib.sha256(
            "\n".join(
                f"{p.relative_to(repo).as_posix()}:{sha256(p)}"
                for p in sorted((repo / "src").rglob("*.py"))
            ).encode()
        ).hexdigest(),
        "lock_sha256": sha256(repo / "uv.lock"),
        "codex_version": subprocess.check_output(
            [args.codex, "--version"], text=True
        ).strip(),
        "model_selection": "Codex default; not pinned by runner",
    }
    (output / "expected.json").write_text(json.dumps(expected, indent=2))
    text = prompt(workspace)
    (output / "prompt.txt").write_text(text)
    cli = command(args.codex, repo, workspace, output)
    cli[-1:-1] = ["-c", 'mcp_servers.asset_aware_under_test.enabled_tools=["document"]']
    status = execute(cli, text, output, 900)
    report = write_audit(output)
    print(
        json.dumps({**status, "audit_passed": report["passed"], "output": str(output)})
    )
    return 0 if status["returncode"] == 0 and report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
