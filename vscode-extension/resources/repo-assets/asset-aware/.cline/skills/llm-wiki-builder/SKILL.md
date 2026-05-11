---
name: llm-wiki-builder
description: "Codex workflow skill for building Foam-compatible LLM wikis from Asset-Aware document evidence and local Markdown notes."
---

# LLM Wiki Builder

Use this skill when working on Foam, LLM wiki, literature wiki, citation-ready
notes, or Markdown knowledge graph tasks in this repository or an installed
workspace.

## Read First

- `.clinerules/35-foam-llm-wiki.md`
- `.clinerules/workflows/llm-wiki-build.md`
- Asset-Aware document outputs: `content.md`, `blocks.json`, `manifest.json`,
  `segmentation.json`, and citation span AssetRefs when available

## Workflow

1. Find the wiki root and existing Foam conventions.
2. Build a note map before editing files.
3. Gather evidence through Asset-Aware/document tools for PDFs, DOCX, DFM,
   tables, figures, sections, segmentation, and span-level evidence.
   If a separate workspace explicitly provides Zotero Keeper or PubMed Search,
   treat those as external sources and follow their own harness rules; do not
   install or maintain those harnesses from this repository.
4. Write Markdown notes with stable filenames, one H1, clean sections, and
   Foam-compatible wikilinks.
5. Validate links, attachments, and source markers before reporting completion.

## Guardrails

- Ask before bulk rewrites, destructive cleanup, or external-library imports.
- Keep source identifiers near claims.
- Do not leave unresolved wikilinks unless they are marked as intentional TODOs.
- Keep generated notes human-readable and chunkable for LLM retrieval.
