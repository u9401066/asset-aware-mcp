---
name: llm-wiki-builder
description: "Codex workflow skill for building Foam-compatible LLM wikis from Asset-Aware documents, citation bundles, tables, figures, and local Markdown notes."
---

# LLM Wiki Builder

Use this skill when working on Foam, LLM wiki, citation-ready notes, or Markdown
knowledge graph tasks in this repository or an installed workspace.

## Read First

- `.clinerules/35-foam-llm-wiki.md`
- `.clinerules/workflows/llm-wiki-build.md`

## Workflow

1. Find the wiki root and existing Foam conventions.
2. Build a note map before editing files.
3. Gather evidence through Asset-Aware MCP tools:
   - Documents, sections, tables, figures, and DOCX/DFM content.
   - Citation bundles, evidence spans, and verification payloads.
   - Optional knowledge exports for synthesis, not as the sole citation source.
4. Write Markdown notes with stable filenames, one H1, clean sections, and
   Foam-compatible wikilinks.
5. Validate links, attachments, and source markers before reporting completion.

## Guardrails

- Ask before bulk rewrites, destructive cleanup, or overwriting curated notes.
- Keep source identifiers near claims.
- Do not leave unresolved wikilinks unless they are marked as intentional TODOs.
- Keep generated notes human-readable and chunkable for LLM retrieval.
