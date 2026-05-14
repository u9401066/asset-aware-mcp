---
paths:
  - ".clinerules/workflows/llm-wiki-build.md"
  - ".cline/skills/llm-wiki-builder/SKILL.md"
  - ".codex/skills/llm-wiki-builder/SKILL.md"
---

# Foam LLM Wiki Rules

Use these rules when turning Asset-Aware PDF, DOCX, DFM, table, figure,
knowledge graph, or project evidence into a Foam-compatible Markdown wiki for
LLM-assisted reading and synthesis.

## Asset Boundaries

- Treat Foam wiki files as user-authored knowledge assets, not generated trash.
- Detect the wiki root before writing. Prefer an existing Foam workspace layout
  such as `.foam/`, `.vscode/settings.json`, or an existing note graph.
- Ask before bulk rewrites, renames, deletions, or moving an existing wiki root.
- Keep raw exports, JSON payloads, and tool responses out of final notes unless
  the user explicitly asks for an appendix.

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

- Preserve document IDs, AssetRefs, DOI, URL, title, source filename, page,
  line, char, byte, quote hash, and access status whenever available.
- Distinguish verified evidence bundles, KG discovery candidates, and unverified
  local notes.
- Cite claims at paragraph or bullet level using compact source markers such as
  `doc_abc#spn_123`, `DOI:...`, or `URL:...`.
- Prefer exact text spans, section names, page numbers, line offsets, or quote
  hashes when an Asset-Aware tool provides them.
- Do not claim that a note is citation-ready unless its source markers can be
  traced back to a concrete document span, table, figure, or verified AssetRef.

## Workflow And Skill Split

- Rules define durable wiki constraints and rendering invariants.
- Workflows define the complete user-facing sequence for making or refreshing
  an LLM wiki.
- Skills orchestrate filesystem search, Asset-Aware evidence extraction,
  optional KG discovery, Markdown writes, and link validation.
