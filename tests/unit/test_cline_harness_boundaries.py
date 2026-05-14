import runpy
import subprocess
from pathlib import Path

LLM_WIKI_HARNESS_FILES = [
    Path(".cline/skills/llm-wiki-builder/SKILL.md"),
    Path(".codex/skills/llm-wiki-builder/SKILL.md"),
    Path(".clinerules/35-foam-llm-wiki.md"),
    Path(".clinerules/workflows/llm-wiki-build.md"),
]

CLINE_WORKFLOW_FILES = [
    Path(".clinerules/workflows/full-check.md"),
    Path(".clinerules/workflows/release-publish.md"),
]

RETIRED_HARNESS_PATHS = [
    Path(".claude/skills/pipeline-persistence"),
    Path(".claude/skills/zotero-keeper-harness"),
    Path(".claude/skills/pubmed-export-citations"),
    Path(".claude/skills/pubmed-fulltext-access"),
    Path(".claude/skills/pubmed-gene-drug-research"),
    Path(".claude/skills/pubmed-mcp-tools-reference"),
    Path(".claude/skills/pubmed-multi-source-search"),
    Path(".claude/skills/pubmed-paper-exploration"),
    Path(".claude/skills/pubmed-pico-search"),
    Path(".claude/skills/pubmed-quick-search"),
    Path(".claude/skills/pubmed-systematic-search"),
    Path(".cline/skills/pubmed-search-mcp-harness"),
    Path(".cline/skills/zotero-keeper-harness"),
    Path(".codex/skills/pubmed-search-mcp-harness"),
    Path(".codex/skills/zotero-keeper-harness"),
    Path(".github/hooks"),
    Path(".github/agents/research.agent.md"),
    Path(".github/zotero-research-workflow.md"),
    Path(".clinerules/00-zotero-project.md"),
    Path(".clinerules/10-zotero-python.md"),
    Path(".clinerules/20-zotero-vscode-extension.md"),
    Path(".clinerules/30-zotero-research-workflow.md"),
    Path(".clinerules/40-zotero-release.md"),
    Path(".clinerules/50-pubmed-project.md"),
    Path(".clinerules/60-pubmed-python.md"),
    Path(".clinerules/70-pubmed-mcp-tools.md"),
    Path(".clinerules/80-pubmed-release.md"),
    Path(".clinerules/workflows/pubmed-full-check.md"),
    Path(".clinerules/workflows/pubmed-mcp-setup.md"),
    Path(".clinerules/workflows/pubmed-release-publish.md"),
    Path(".clinerules/workflows/pubmed-skills-audit.md"),
    Path(".clinerules/workflows/zotero-full-check.md"),
    Path(".clinerules/workflows/zotero-mcp-setup.md"),
    Path(".clinerules/workflows/zotero-release-publish.md"),
    Path(".clinerules/workflows/zotero-skills-audit.md"),
    Path("scripts/hooks/copilot"),
]


def test_llm_wiki_harness_stays_asset_aware_scoped() -> None:
    forbidden_fragments = [
        ".github/zotero-research-workflow.md",
        "Use Zotero tools",
        "Use PubMed tools",
        "Use PubMed Search MCP tools",
        "Build or refresh a Foam-compatible LLM wiki from Zotero",
        "Zotero imports",
        "Zotero key",
        "Zotero:ABC123",
        "PMID:12345678",
        "PubMed discovery",
    ]
    for path in LLM_WIKI_HARNESS_FILES:
        text = path.read_text(encoding="utf-8")

        for fragment in forbidden_fragments:
            assert fragment not in text, (path, fragment)


def test_release_audit_flags_retired_harness_text(tmp_path: Path) -> None:
    namespace = runpy.run_path("scripts/audit_release_harness.py")
    require_absent_text = namespace["require_absent_text"]
    sample = tmp_path / "harness.md"

    sample.write_text("Use Zotero tools before Asset-Aware tools", encoding="utf-8")

    assert require_absent_text(str(sample), ["Use Zotero tools"]) == [
        f"{sample}: forbidden retired harness text 'Use Zotero tools'"
    ]


def test_retired_harness_files_are_absent_from_workspace() -> None:
    for path in RETIRED_HARNESS_PATHS:
        if not path.exists():
            continue
        result = subprocess.run(
            ["git", "check-ignore", "-q", "--", str(path)],
            check=False,
        )
        assert result.returncode == 0, path


def test_cline_workflow_execute_commands_are_powershell_safe() -> None:
    forbidden_fragments = [
        "&&",
        'VERSION="$(',
        "$VERSION",
        "Push-Location",
    ]
    for path in CLINE_WORKFLOW_FILES:
        text = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in text, (path, fragment)
