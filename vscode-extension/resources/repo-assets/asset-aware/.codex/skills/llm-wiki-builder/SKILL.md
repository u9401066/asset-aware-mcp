---
name: llm-wiki-builder
description: "Codex workflow skill for building Foam-compatible LLM wikis from Asset-Aware documents, citation bundles, and local Markdown notes."
---

# LLM Wiki Builder

Use this skill when working on Foam, LLM wiki, literature wiki, citation-ready
notes, or Markdown knowledge graph tasks in this repository or an installed
workspace.

## Read First

- `.clinerules/35-foam-llm-wiki.md`
- `.clinerules/workflows/llm-wiki-build.md`

## Workflow

1. Find the wiki root and existing Foam conventions.
2. Build a note map before editing files.
3. Gather evidence through the appropriate MCP tools:
   - Asset-aware/document tools for PDFs, DOCX, DFM, tables, figures, and
     span-level evidence when available.
   - Citation bundle, evidence health, manifest, and asset-resource tools for
     traceable source spans and reviewable claims.
4. Write Markdown notes with stable filenames, one H1, clean sections, and
   Foam-compatible wikilinks.
5. Validate links, attachments, and source markers before reporting completion.

## Guardrails

- Ask before bulk rewrites, destructive cleanup, or large note regeneration.
- Keep source identifiers near claims.
- Do not leave unresolved wikilinks unless they are marked as intentional TODOs.
- Keep generated notes human-readable and chunkable for LLM retrieval.
