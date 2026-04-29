# Cline Harness (Project Setup)

This repo includes a Cline-oriented harness so agents can work consistently across coding, review, and releases.

## Rules
- Workspace rules live under `.clinerules/`.
- Files may include YAML frontmatter with `paths:` so rules only activate when relevant.

## Skills
- Project skills can live in:
  - `.cline/skills/` (recommended by Cline)
  - `.claude/skills/` (already used in this repo; Cline supports it too)
  - `.codex/skills/` (validated for Codex harness parity)
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

The VSIX now auto-configures MCP access when the extension activates:

- Copilot: merges `asset-aware-mcp` into workspace `.vscode/mcp.json`
- Cline: merges `asset-aware-mcp` into Cline `cline_mcp_settings.json`
- Codex: merges `[mcp_servers.asset-aware-mcp]` into `~/.codex/config.toml`
- Harness assets: installs/updates `AGENTS.md`, `.github/copilot-instructions.md`, `.github/agents/asset-aware-document.agent.md`, `.cline/skills/asset-aware-mcp-harness`, `.codex/skills/asset-aware-mcp-harness`, and `.clinerules`

All merges are conservative: unrelated servers, custom same-key servers, Cline `alwaysAllow`, and Codex comments are preserved.

The repo also includes a CLI helper to register `asset-aware-mcp` as a Cline MCP server using the standard `cline_mcp_settings.json` file.

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
