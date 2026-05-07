# LLM Wiki Build Workflow

Build or refresh a Foam-compatible LLM wiki from Asset-Aware document evidence
and local Markdown notes. Use with `.clinerules/35-foam-llm-wiki.md`.

## 1. Locate The Wiki

- Identify the wiki root and avoid creating a parallel wiki unless requested.
- Inspect existing filename style, frontmatter conventions, attachment folders,
  and wikilink patterns.
- Build a note map before editing so new links target known files.

## 2. Plan Changes

- Separate source ingestion, note updates, link repairs, and cleanup.
- Ask before bulk rewrites, renames, deleting notes, or moving attachments.
- Preserve user-written sections unless the user explicitly asks for rewrite.

## 3. Gather Evidence With Tools

- Use Asset-Aware/document tools when the user provides PDFs, DOCX, DFM,
  tables, figures, segmentation needs, or span-level citation requirements.
- Prefer existing document artifacts before regenerating: `manifest.json`,
  `content.md`, `blocks.json`, `segmentation.json`, figures, tables, and
  citation span AssetRefs.
- If the workspace explicitly provides external Zotero Keeper or PubMed Search
  tools, treat their results as user-supplied external evidence and follow that
  project's own harness rules. Asset-Aware must not install or maintain those
  harnesses.
- Record provenance as you gather it; do not reconstruct citations from memory.

## 4. Write Foam-Compatible Notes

- Use stable lowercase kebab-case filenames for generated notes.
- Use one `# H1` per note.
- Keep generated notes readable, not just chunkable.
- Put source identifiers near claims, especially for synthesized paragraphs.
- Use `[[wikilinks]]` only for notes that exist or are being created.
- Use relative Markdown links for PDFs, figures, tables, and exported files.

## 5. Validate

- Check that generated wikilinks resolve or are explicitly marked TODO.
- Check that source markers can be traced to a concrete source.
- Check that no raw tool dump was accidentally pasted into final notes.
- Report skipped or unresolved evidence separately from completed notes.

## 6. Report

- Summarize created, updated, preserved, and skipped notes.
- List unresolved TODOs separately from completed links.
- Mention any evidence gaps, missing PDFs/assets, unresolved external source
  status, or uncertain preprint/peer-review status.
