---
name: llm-wiki-builder
description: "Codex workflow skill for building Foam-compatible LLM wikis from Asset-Aware document evidence, knowledge graph output, and local Markdown notes."
---

# LLM Wiki Builder

Use this skill when working on Foam, LLM wiki, citation-ready notes, document
evidence, or Markdown knowledge graph tasks in this repository or an installed
workspace.

## Read First

- `.clinerules/35-foam-llm-wiki.md`
- `.clinerules/workflows/llm-wiki-build.md`
- `.codex/skills/asset-aware-mcp-harness/SKILL.md`

## Workflow

1. Find the wiki root and existing Foam conventions.
2. Build a note map before editing files.
3. Gather evidence through Asset-Aware MCP tools:
   - `citation_bundle(output_format="foam")` for verified evidence packs.
   - `document_asset(op="foam_notes")` for table and figure evidence notes.
   - `evidence(op="health")` for wikilink, anchor, and AssetRef validation.
   - Knowledge graph queries only when LightRAG/KG is enabled and useful.
4. Write Markdown notes with stable filenames, one H1, clean sections, and
   Foam-compatible wikilinks.
5. Validate links, attachments, source markers, and verification payloads before
   reporting completion.

## Guardrails

- Ask before bulk rewrites, destructive cleanup, or workspace-wide renames.
- Keep source identifiers and AssetRefs near claims.
- Do not leave unresolved wikilinks unless they are marked as intentional TODOs.
- Keep generated notes human-readable and chunkable for LLM retrieval.
