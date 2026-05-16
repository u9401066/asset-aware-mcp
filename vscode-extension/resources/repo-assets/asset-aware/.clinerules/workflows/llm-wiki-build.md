# LLM Wiki Build Workflow

Build or refresh a Foam-compatible LLM wiki from Asset-Aware document evidence.
Use with `.clinerules/35-foam-llm-wiki.md`.

## 1. Locate The Wiki

- Find the workspace root and any existing Foam markers such as `.foam/`,
  `.vscode/settings.json`, existing `[[wikilinks]]`, or a user-provided note
  directory.
- If no wiki root is obvious, propose a small root such as `wiki/` and wait for
  user confirmation before creating many files.
- Read nearby README or index notes to preserve existing naming and link style.

## 2. Define The Note Map

- Create a short map before writing files:
  - hub note
  - topic notes
  - literature/source notes
  - method or protocol notes
  - unresolved TODO notes
- Prefer a few well-linked notes over one large dump.
- Decide which notes are generated, refreshed, or preserved.

## 3. Gather Evidence With Tools

- Use document or asset-aware tools when the user provides PDFs, DOCX, DFM,
  tables, figures, or span-level citation requirements.
- Use citation bundle, evidence health, manifest, and asset-resource tools to
  gather traceable source spans and reviewable claim payloads.
- Record provenance as you gather it; do not reconstruct citations from memory.

## 4. Write Foam-Compatible Notes

- Add YAML frontmatter only when it carries useful metadata.
- Use a single `# H1`, concise sections, and stable anchors.
- Use `[[note-slug]]` only when the target exists or is created in this run.
- Add source markers near claims, not only in a bibliography note.
- Keep note bodies readable for humans and chunkable for LLM retrieval.

## 5. Validate The Wiki

- Check that generated note filenames match the wikilinks you emitted.
- Search for unresolved `[[...]]` links and either create the missing target,
  convert the link to plain text, or mark it as an intentional TODO.
- Confirm relative attachment links point to existing files.
- Re-open a sample hub note and source note to verify the rendered structure is
  clean: frontmatter, H1, sections, links, and citations.

## 6. Report The Result

- Summarize created, updated, preserved, and skipped notes.
- List unresolved TODOs separately from completed links.
- Mention any evidence gaps, missing source documents, unresolved assets, or
  uncertain preprint/peer-review status.
