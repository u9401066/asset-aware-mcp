"""Scheduled GitHub hygiene workflow and script regressions."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_TOPICS = """ai
agent-assets
citations
document-ai
document-processing
docx
etl
foam
knowledge-graph
layout-analysis
lightrag
llm
mcp
mcp-server
medical
ocr
pdf
python
rag
segmentation"""

EXPECTED_LABELS = """area:mcp\t5319e7\tMCP protocol, server, tools, resources, or clients
area:pdf\t1d76db\tPDF extraction, OCR, layout, or preflight routing
area:docx\t0e8a16\tDOCX, DFM, round-trip fidelity, or writeback
area:wiki\t8250df\tFoam, LightRAG, knowledge graph, or reusable agent assets
area:vsix\t006b75\tVS Code extension, packaging, installation, or UX
area:ci\tbfd4f2\tCI, smoke tests, release gates, or automation
dependencies\t0366d6\tDependency updates and compatibility maintenance
security\tb60205\tSecurity hardening, vulnerability, or supply-chain work
provenance\t0052cc\tCitation locators, hashes, identity, or evidence integrity
breaking-change\td93f0b\tRequires a major-version migration by consumers
release\tfbca04\tRelease preparation, publishing, or post-release verification
superseded\tc5def5\tReplaced by a newer implementation on the default branch
needs-reproduction\tf9d0c4\tNeeds a minimal reproducer or current-version confirmation
priority:high\tb60205\tHigh-impact or release-blocking work"""

LABEL_RECORDS = [
    {"name": name, "color": color, "description": description}
    for name, color, description in (
        line.split("\t", 2) for line in EXPECTED_LABELS.splitlines()
    )
]
EXPECTED_LABELS_JSON = json.dumps(LABEL_RECORDS)
DRIFT_LABELS_JSON = json.dumps(LABEL_RECORDS[:-1])
MALICIOUS_LABELS_JSON = json.dumps(
    [
        *LABEL_RECORDS,
        {
            "name": '$(touch "$GH_INJECTION_PROBE")',
            "color": "ffffff",
            "description": "unmanaged remote label",
        },
    ]
)


def _fake_gh(tmp_path: Path) -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "gh.log"
    gh = bin_dir / "gh"
    gh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "$GH_LOG"

if [[ "$1" == "api" && "$*" == *"--jq .description"* ]]; then
  if [[ "${GH_FAKE_SCENARIO:-ok}" == "metadata-drift" ]]; then
    printf '%s\\n' 'stale description'
  else
    printf '%s\\n' 'Turn PDF, DOCX, tables, and figures into citation-ready reusable agent assets and Foam/LightRAG wikis — MCP SDK 2 server plus VS Code extension'
  fi
elif [[ "$1" == "api" && "$*" == *"--jq .homepage"* ]]; then
  printf '%s\\n' 'https://u9401066.github.io/asset-aware-mcp/'
elif [[ "$1" == "api" && "$*" == *"topics --jq"* ]]; then
  printf '%s\\n' "$GH_FAKE_TOPICS"
elif [[ "$1" == "label" && "$2" == "list" ]]; then
  if [[ "${GH_FAKE_SCENARIO:-ok}" == "label-drift" ]]; then
    printf '%s\\n' "$GH_FAKE_LABELS_DRIFT_JSON"
  elif [[ "${GH_FAKE_SCENARIO:-ok}" == "malicious-label" ]]; then
    printf '%s\\n' "$GH_FAKE_LABELS_MALICIOUS_JSON"
  else
    printf '%s\\n' "$GH_FAKE_LABELS_JSON"
  fi
fi
""",
        encoding="utf-8",
    )
    gh.chmod(0o755)
    return bin_dir, log


def _run_script(
    script: str,
    mode: str | None,
    tmp_path: Path,
    *,
    scenario: str = "ok",
    repo: str = "u9401066/asset-aware-mcp",
) -> tuple[subprocess.CompletedProcess[str], str]:
    bin_dir, log = _fake_gh(tmp_path)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "GH_LOG": str(log),
        "GH_REPO": repo,
        "GH_FAKE_SCENARIO": scenario,
        "GH_FAKE_TOPICS": EXPECTED_TOPICS,
        "GH_FAKE_LABELS_JSON": EXPECTED_LABELS_JSON,
        "GH_FAKE_LABELS_DRIFT_JSON": DRIFT_LABELS_JSON,
        "GH_FAKE_LABELS_MALICIOUS_JSON": MALICIOUS_LABELS_JSON,
        "GH_INJECTION_PROBE": str(tmp_path / "injection-probe"),
    }
    command = ["bash", str(ROOT / "scripts" / script)]
    if mode is not None:
        command.append(mode)
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return result, log.read_text(encoding="utf-8") if log.exists() else ""


def test_repository_metadata_check_is_read_only_and_fails_on_drift(
    tmp_path: Path,
) -> None:
    result, calls = _run_script("gh_update_repo_metadata.sh", "--check", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "--method PATCH" not in calls
    assert "--method PUT" not in calls

    drift_root = tmp_path / "drift"
    drift_root.mkdir()
    drift, drift_calls = _run_script(
        "gh_update_repo_metadata.sh",
        "--check",
        drift_root,
        scenario="metadata-drift",
    )
    assert drift.returncode == 1
    assert "description drift" in drift.stderr
    assert "--method PATCH" not in drift_calls


def test_hygiene_scripts_default_to_read_only_checks(tmp_path: Path) -> None:
    for script in ["gh_update_repo_metadata.sh", "gh_sync_labels.sh"]:
        run_root = tmp_path / script
        run_root.mkdir()
        result, calls = _run_script(script, None, run_root)
        assert result.returncode == 0, result.stderr
        assert "--method PATCH" not in calls
        assert "--method PUT" not in calls
        assert "label create" not in calls


def test_repository_metadata_apply_uses_explicit_canonical_api_updates(
    tmp_path: Path,
) -> None:
    result, calls = _run_script("gh_update_repo_metadata.sh", "--apply", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "--method PATCH repos/u9401066/asset-aware-mcp" in calls
    assert "--method PUT repos/u9401066/asset-aware-mcp/topics" in calls
    assert calls.count("--jq") == 3


def test_label_apply_preserves_unmanaged_labels_and_verifies_managed_values(
    tmp_path: Path,
) -> None:
    result, calls = _run_script("gh_sync_labels.sh", "--apply", tmp_path)
    assert result.returncode == 0, result.stderr
    assert calls.count("label create") == 14
    assert "label delete" not in calls
    assert "label list" in calls

    drift_root = tmp_path / "drift"
    drift_root.mkdir()
    drift, _ = _run_script(
        "gh_sync_labels.sh",
        "--check",
        drift_root,
        scenario="label-drift",
    )
    assert drift.returncode == 1
    assert "missing managed label" in drift.stderr


def test_remote_label_names_are_data_not_bash_expressions(tmp_path: Path) -> None:
    result, _ = _run_script(
        "gh_sync_labels.sh",
        "--check",
        tmp_path,
        scenario="malicious-label",
    )
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "injection-probe").exists()


def test_github_hygiene_scripts_reject_invalid_repository_identifiers(
    tmp_path: Path,
) -> None:
    for script in ["gh_update_repo_metadata.sh", "gh_sync_labels.sh"]:
        run_root = tmp_path / script
        run_root.mkdir()
        result, calls = _run_script(
            script, "--check", run_root, repo="owner/repo/extra"
        )
        assert result.returncode == 2
        assert "owner/repository pair" in result.stderr
        assert calls == ""


def test_scheduled_hygiene_workflow_is_pinned_least_privilege_and_auditable() -> None:
    workflow = (ROOT / ".github" / "workflows" / "project-hygiene.yml").read_text(
        encoding="utf-8"
    )

    for required in [
        'cron: "43 6 * * 3"',
        "python3 scripts/build_docs_site.py --check",
        "python3 scripts/audit_release_artifacts.py --require metadata",
        "npm --prefix vscode-extension run sync-assets:check",
        "astral-sh/setup-uv@ae62891fec2bb8e7d6c99fc78c9fec3a63790f8d",
        'version: "0.12.3"',
        "enable-cache: false",
        'uv sync --frozen --python "$PYTHON_VERSION"',
        "tests/unit/test_docs_site_reference_sync.py",
        "tests/unit/test_public_docs_hygiene.py",
        "./scripts/gh_sync_labels.sh --apply",
        "./scripts/gh_sync_labels.sh --check",
        "./scripts/gh_update_repo_metadata.sh --apply",
        "./scripts/gh_update_repo_metadata.sh --check",
        "PROJECT_HYGIENE_TOKEN",
        "issues: write",
        "if: github.repository == 'u9401066/asset-aware-mcp'",
        "persist-credentials: false",
        "package-manager-cache: false",
    ]:
        assert required in workflow

    assert "contents: write" not in workflow
    assert "pull-requests: write" not in workflow
    assert "git push" not in workflow
    assert workflow.count("if: github.repository == 'u9401066/asset-aware-mcp'") == 2
    uses = re.findall(r"(?m)^\s*-?\s*uses:\s*([^\s#]+)", workflow)
    assert uses
    assert all(re.search(r"@[0-9a-f]{40}$", action) for action in uses)
