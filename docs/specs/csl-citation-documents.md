<a id="csl-citation-documents-unreleased-14x"></a>

# CSL citation documents (1.4.1)

## Purpose and boundary

Render an ordered document of citations and its bibliography with the real
citeproc-js processor and pinned official CSL styles/locales. Existing
`citation-format-v1` presets/custom templates remain unchanged. An author-year
template is not an APA or Chicago implementation. MCP checks input structure,
source references, resource identities and deterministic output; the Agent checks
bibliographic truth, source support, the correspondence of printed locators and
actual rendering.

## Contract

`evidence(op="csl_contract")` describes the available processor, styles, locales
and the complete hash-paged citation-document input schema. The processor uses
an optional local Node.js executable; absence is explicit, never a fallback to a
template. No runtime network requests, automatic installs or model calls occur.

`evidence(op="render_citations", citation_document={...})` accepts:

- A bundled style (`apa`, `chicago-author-date`,
  `chicago-notes-bibliography`, `vancouver`) and locale (`en-US`, `zh-TW`).
- CSL-JSON items with unique string IDs, validated against the pinned official
  schema. Bibliographic names/dates stay structured, never inferred from strings.
- Ordered clusters with stable IDs, explicit note numbers, cite items, optional
  printed locators/labels, prefix/suffix and author suppression. The processor
  handles sorting, repeated citations and retroactive disambiguation updates.
- Optional explicit uncited item IDs to include in the bibliography.
- Named complete native source references, and per-cite source keys. Source keys
  must exist and every supplied reference is verified at its exact revision.
  A printed CSL locator is caller-authored display data, not a source locator
  override or a verified mapping from PDF page indices to printed page numbers.

The complete result is canonical JSON with UTF-8 SHA-256 and bounded character
pages (`text_offset`, `text_limit`, optional `expected_text_sha256`). It includes
the original document, final citations/bibliography, item-to-entry mapping,
processor/style/locale/schema hashes and explicit review scope. Rendering the
same input is deterministic. A source becoming historical must not rewrite the
saved reference or citation meaning. Missing data is not fabricated; missing
author/date/title fields are reported, and CSL style fallbacks remain visible.

## Portable wiki

An explicit `wiki_root` publishes a new immutable snapshot with a citation index,
per-cluster wikilinks, complete input/result JSON, exact native source attachments,
and an inventory manifest written last. Cite items keep their canonical source
references next to formatted citations. Typography is preserved with a bounded
safe HTML representation; plain text is also available. User markup cannot add
scripts, arbitrary attributes, external embeds or unrelated wiki links.
The snapshot identity includes citation input, rendering resource identities and
immutable source evidence. Changing styles creates a separate snapshot without
moving source IDs. Existing matching snapshots may be reused only after exact
inventory/byte verification; edits to curated/generated notes are preserved and
reported. No source writeback or automatic evidence promotion occurs.

## Implementation and verification

Domain models have no I/O. Application orchestration depends on processor,
native evidence/repository and wiki publisher boundaries. The infrastructure
processor runs the pinned unmodified citeproc-js distribution with bounded input,
output, memory and timeout. Resource downloads happen only during development;
committed resources have exact source URLs, hashes and upstream licenses.

Regression evidence must cover same-author/year disambiguation (including changes
to previous clusters), citation and bibliography sorting, numeric repeated cites,
Chicago first/subsequent notes, corporate/Unicode authors, date/locator precision,
missing fields, unsafe markup/URLs, bad source hashes, duplicate/missing IDs,
resource drift, process timeout and complete hash paging. SDK2 tests must create
real native evidence, render and export, verify attachments and preserve old
citations after source edits. An actual default-model Codex workflow must discover
the contract and produce/review a complete evidence-backed citation snapshot.

## Primary references

- [CSL 1.0.2 specification](https://docs.citationstyles.org/en/stable/specification.html)
- [citeproc-js processor](https://github.com/Juris-M/citeproc-js)
- [Document-context processing API](https://citeproc-js.readthedocs.io/en/latest/running.html)
- [Official CSL styles](https://github.com/citation-style-language/styles)
- [Official CSL locales](https://github.com/citation-style-language/locales)
- [Official CSL input schema](https://github.com/citation-style-language/schema)

The current citeproc-py documentation lists missing year-suffix disambiguation,
so it does not meet this document-context requirement without further work:
[citeproc-py compatibility](https://pypi.org/project/citeproc-py/).
