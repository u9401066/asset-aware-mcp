---
paths:
  - ".clinerules/workflows/llm-wiki-build.md"
  - ".cline/skills/llm-wiki-builder/SKILL.md"
  - ".codex/skills/llm-wiki-builder/SKILL.md"
---

# Foam LLM Wiki Rules

Use these rules when turning Asset-Aware documents, citation bundles, tables,
figures, sections, DOCX/DFM edits, knowledge exports, or project evidence into
a Foam-compatible Markdown wiki for LLM-assisted reading and synthesis.

## Asset Boundaries

- Treat Foam wiki files as user-authored knowledge assets, not generated trash.
- Detect the wiki root before writing. Prefer an existing Foam workspace layout
  such as `.foam/`, `.vscode/settings.json`, or an existing note graph.
- Ask before bulk rewrites, renames, deletions, or moving an existing wiki root.
- Keep raw exports, JSON, and tool responses out of final notes unless the user
  explicitly asks for an appendix.

## Foam Rendering Invariants

- Create ordinary Markdown files that render without custom HTML.
- Use one `# H1` title per note, matching the human-readable note title.
- Use stable lowercase kebab-case filenames for new generated notes.
- Put display titles and source identifiers in YAML frontmatter when useful.
- Use Foam wikilinks only for real note targets:
  - `[[note-slug]]` when the target note exists or is created in the same workflow.
  - `[[note-slug|Readable label]]` when the filename is less readable than the title.
- Use relative Markdown links for attachments, figures, PDFs, or exported files.
- Do not leave unresolved wikilinks unless they are intentionally marked as TODO.

## Evidence And Citation Hygiene

- Preserve AssetRef JSON, document IDs, citation span IDs, table IDs, figure IDs,
  section paths, DOI, URL, title, source file, year, and access status whenever
  available.
- Distinguish verified Asset-Aware evidence, candidate local notes, optional KG
  summaries, and unsupported claims.
- Cite claims at paragraph or bullet level using compact source markers such as
  `AssetRef:...`, `doc_id:...`, `table_id:...`, `DOI:...`, or `URL:...`.
- Prefer exact text spans, section names, page numbers, line/char/byte offsets,
  context snippets, or quote hashes when Asset-Aware tools provide them.
- Do not claim that a note is citation-ready unless its source markers can be
  traced back to a concrete document span, table cell, figure asset, or verified
  citation bundle entry.

## Workflow And Skill Split

- Rules define durable wiki constraints and rendering invariants.
- Workflows define the complete user-facing sequence for making or refreshing
  an LLM wiki.
- Skills orchestrate multiple tools: filesystem search, Asset-Aware document
  inspection, citation bundle export, optional KG/Foam synthesis, Markdown
  writes, and link validation.
