---
name: llm-wiki-builder
description: "Build or refresh Foam-compatible LLM wikis from Asset-Aware document evidence and local Markdown notes."
---

# LLM Wiki Builder

Use this skill when the user asks to create, refresh, repair, or extend a Foam
wiki or LLM-readable literature wiki.

## Read First

- `.clinerules/35-foam-llm-wiki.md`
- `.clinerules/workflows/llm-wiki-build.md`
- Asset-Aware document outputs: `content.md`, `blocks.json`, `manifest.json`,
  `segmentation.json`, and citation span AssetRefs when available

## Multi-Tool Choreography

1. Inspect the filesystem for the wiki root, Foam markers, existing note style,
   and link conventions.
2. Use Asset-Aware/document tools when PDFs, DOCX, DFM, tables, figures,
   segmentation, or span-level citations are part of the request.
3. If a separate workspace explicitly provides Zotero Keeper or PubMed Search,
   treat those as external sources and follow their own harness rules; do not
   install or maintain those harnesses from this repository.
4. Write or update Markdown notes with Foam-compatible wikilinks and preserved
   source identifiers.
5. Validate generated links and report unresolved wiki TODOs separately from
   completed notes.

## Output Contract

- Keep the note graph readable in Foam and useful for LLM retrieval.
- Preserve source provenance close to claims.
- Ask before bulk rewrites, destructive cleanup, or external-library imports.
- Do not leave broken wikilinks hidden in generated files.
