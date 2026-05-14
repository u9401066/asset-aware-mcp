---
name: llm-wiki-builder
description: "Build or refresh Foam-compatible LLM wikis from Asset-Aware document evidence, knowledge graph output, and local Markdown notes."
---

# LLM Wiki Builder

Use this skill when the user asks to create, refresh, repair, or extend a Foam
wiki or LLM-readable evidence wiki.

## Read First

- `.clinerules/35-foam-llm-wiki.md`
- `.clinerules/workflows/llm-wiki-build.md`
- `.cline/skills/asset-aware-mcp-harness/SKILL.md`

## Multi-Tool Choreography

1. Inspect the filesystem for the wiki root, Foam markers, existing note style,
   and link conventions.
2. Use Asset-Aware document tools when PDFs, DOCX, DFM, tables, figures, or
   span-level citations are part of the request.
3. Use evidence tools to create verified Foam bundles, promote table/figure
   notes, and validate AssetRefs.
4. Use knowledge graph tools only when KG is enabled and the user needs
   cross-document discovery.
5. Write or update Markdown notes with Foam-compatible wikilinks and preserved
   source identifiers.
6. Validate generated links and report unresolved wiki TODOs separately from
   completed notes.

## Output Contract

- Keep the note graph readable in Foam and useful for LLM retrieval.
- Preserve source provenance close to claims.
- Ask before bulk rewrites, destructive cleanup, or workspace-wide renames.
- Do not leave broken wikilinks hidden in generated files.
