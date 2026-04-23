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

## Workflows
- Workspace workflows live under `.clinerules/workflows/`.
- Invoke a workflow by typing its filename as a slash command:
  - `/full-check.md`
  - `/release-publish.md`
  - `/skills-audit.md`

## .clineignore
- `.clineignore` keeps Cline from indexing large/binary artifacts (envs, build outputs, PDFs/DOCX fixtures).
- If you need an ignored fixture for debugging, explicitly mention its path in your request.

## Recommended Starting Point
- After a non-trivial change: run `/full-check.md`.
- Before tagging a release: run `/release-publish.md`.
