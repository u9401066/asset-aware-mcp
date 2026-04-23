# Cline Harness (Project Setup)

This repo includes a Cline-oriented harness so agents can work consistently across coding, review, and releases.

## Rules
- Workspace rules live under `.clinerules/`.
- Files may include YAML frontmatter with `paths:` so rules only activate when relevant.

## Skills
- Project skills can live in:
  - `.cline/skills/` (recommended by Cline)
  - `.claude/skills/` (already used in this repo; Cline supports it too)
- Enable Skills in Cline: Settings → Features → Enable Skills.
- Tip: Skill YAML frontmatter is parsed strictly. If `description:` includes text like `Triggers: ...`, wrap the whole description in quotes.

## Workflows
- Workspace workflows live under `.clinerules/workflows/`.
- Invoke a workflow by typing its filename as a slash command:
  - `/full-check.md`
  - `/mcp-setup.md`
  - `/release-publish.md`
  - `/skills-audit.md`

## .clineignore
- `.clineignore` keeps Cline from indexing large/binary artifacts (envs, build outputs, PDFs/DOCX fixtures).
- If you need an ignored fixture for debugging, explicitly mention its path in your request.

## MCP Server Setup (Asset-Aware MCP)

This repo includes a helper to register `asset-aware-mcp` as a Cline MCP server using the standard `cline_mcp_settings.json` file.

- Guided workflow: `/mcp-setup.md`
- Script (idempotent): `python3 scripts/install_cline_mcp.py --write`

Notes:
- The script prefers updating an existing Cline settings file. If none exist, it creates the Cline CLI default at `~/.cline/data/settings/cline_mcp_settings.json`.
- After running it, restart Cline (or reload the VS Code window) so it re-reads MCP settings.

## Recommended Starting Point
- After a non-trivial change: run `/full-check.md`.
- Before tagging a release: run `/release-publish.md`.

## Troubleshooting
- Skills not showing up: run `/skills-audit.md` and fix any YAML/frontmatter errors, then restart Cline.
