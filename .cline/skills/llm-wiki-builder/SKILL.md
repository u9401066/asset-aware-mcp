---
name: llm-wiki-builder
description: "Build or refresh Foam-compatible LLM wikis from Asset-Aware documents, citation bundles, tables, figures, and local Markdown notes using a multi-tool workflow."
---

# LLM Wiki Builder

Use this skill when the user asks to create, refresh, repair, or extend a Foam
wiki or LLM-readable document evidence wiki.

## Read First

- `.clinerules/35-foam-llm-wiki.md`
- `.clinerules/workflows/llm-wiki-build.md`

## Multi-Tool Choreography

1. Inspect the filesystem for the wiki root, Foam markers, existing note style,
   and link conventions.
2. Use Asset-Aware document tools to inspect ingested PDFs, DOCX/DFM sessions,
   tables, figures, sections, and citation-ready spans.
3. Use citation bundles, evidence health checks, and optional knowledge exports
   when claims need source-backed summaries.
4. Write or update Markdown notes with Foam-compatible wikilinks and preserved
   AssetRef, document, table, figure, section, DOI, URL, or local-file source
   identifiers when available.
5. Validate generated links and report unresolved wiki TODOs separately from
   completed notes.

## Output Contract

- Keep the note graph readable in Foam and useful for LLM retrieval.
- Preserve source provenance close to claims.
- Ask before bulk rewrites, destructive cleanup, or overwriting curated notes.
- Do not leave broken wikilinks hidden in generated files.
