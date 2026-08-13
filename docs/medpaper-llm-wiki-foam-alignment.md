# MedPaper LLM Wiki / Foam Alignment

This document records how Asset-Aware MCP should interoperate with
`u9401066/med-paper-assistant` without duplicating MedPaper's wiki-writing
responsibilities.

## Boundary

Asset-Aware MCP is the source-material decomposition and locator authority.
It emits document assets, evidence spans, citation-ready references, and a
document-scoped portable agent/Foam bundle that can be re-verified against the
original file.

MedPaper is the durable LLM wiki writer. It owns Foam-facing reference notes,
knowledge maps, synthesis pages, wikilinks, frontmatter, dashboards, and graph
views.

Foam is the Markdown navigation layer. It owns wikilinks, backlinks, graph
views, hover previews, block embeds, and query rendering. Asset-Aware may emit
a self-contained per-document Foam subtree, while MedPaper remains responsible
for integrating that subtree into a durable, curated project wiki.

## Alignment Contract

Asset-Aware assets are aligned with MedPaper's LLM wiki / Foam workflow when
each citable unit can be promoted into a Foam note or block anchor without
losing provenance.

Required fields for alignment:

- Stable identity: `doc_id` plus `asset_id`, `block_id`, or `span_id`.
- Source revision: `source_revision_id` or equivalent hash of the canonical
  markdown/text used for locators.
- Exact quote verification: `quote` or `text`, `quote_sha256` or
  `text_sha256`, and normalized hash when available.
- Locator metadata: page, line range, char range, byte range, bbox, and
  locator algorithm version when available.
- Context: section hierarchy plus short surrounding context for review.
- Asset relationship: table/figure/section/full-text/span source type and the
  nearest containing section.
- Conservative quality scaffold: CRAAP values should remain `unassessed`,
  `partial`, `supported`, or `needs_review`; do not invent certainty.

## Foam-Compatible Promotion Shape

Asset-Aware can either provide promotion data for MedPaper or write a bounded,
portable per-document Foam subtree. It should give MedPaper enough data to
materialize or integrate notes like:

```markdown
---
title: "Source fragment label"
type: evidence
tags: [asset-aware, evidence]
source_doc_id: doc_...
source_revision_id: ...
span_id: spn_...
quote_sha256: ...
---

Quoted or summarized evidence text. ^spn-...
```

MedPaper can then link or embed that evidence with Foam syntax:

```markdown
[[citation_key#^spn-...]]
![[citation_key#^spn-...]]
```

The anchor name may be derived from `span_id`, but the canonical proof remains
the Asset-Aware `source_revision_id` + locator ranges + text hash.

For direct promotion, `citation_bundle(output_format="foam", citation_key="...")`
exports a Foam-compatible evidence pack with YAML frontmatter, `^spn-...` block
anchors, wikilink/embed strings, verification status, locator hashes, and the
machine-readable AssetRef JSON beside each quote. When `wiki_root` is supplied,
the bundle can be written into a Foam wiki and the managed evidence index block
can be updated in place.

## Portable Agent Asset Bundle

For an ingested PDF document, the complete reusable-asset workflow is:

```text
document(
  op="export_assets",
  doc_id="doc_...",
  output_dir="agent-assets"
)
```

The output stays under that document's repository data directory:

```text
agent-assets/
  manifest.json
  assets.jsonl
  index.md
  notes/<stable-note>.md
  media/<stable-media>
```

`assets.jsonl` contains deterministic text, table, and figure records. Each
record keeps the source `asset_id`, a stable `<asset_type>:<asset_id>` key,
format-neutral source identity (`source_sha256`, `source_kind`,
`source_media_type`), content and record hashes, locator metadata, citation
status, primary AssetRef when available, EvidenceSpan references, and Foam note
metadata. `manifest.json` adds counts, artifact hashes, and `bundle_sha256`.

`index.md` is the hub for the generated `notes/**`; every wikilink targets a
note and block anchor created in the same export. Figure notes use relative
links into `media/**`. No execution timestamp or output directory absolute path
is embedded in these artifacts, so identical repository inputs produce the
same bundle bytes and the subtree can be moved as a unit.

The safety boundary is deliberate: `output_dir` must resolve to a strict child
of the document directory. Traversal, the document root, source image folders,
arbitrary pre-existing directories, and bundles belonging to another `doc_id`
are rejected. Export uses a staging directory and rename-based replacement,
does not overwrite source files, and only copies supported figure files that
resolve inside the document directory.

This does not transfer project-wiki ownership to Asset-Aware. MedPaper still
chooses project paths and citation keys, merges or curates notes, builds topic
maps and dashboards, and controls publication. It can treat the exported
subtree and JSONL as a versionable, rebuildable source pack.

## Current Asset-Aware Coverage

Already aligned:

- `document(op="export_assets")` emits a deterministic agent bundle plus a
  portable `index.md + notes/**` Foam subtree with stable asset identities,
  artifact hashes, locators, citation provenance, and relative figure links.

- `EvidenceSpan` stores stable `span_id`, `source_revision_id`,
  `locator_version`, line/char/byte ranges, text hashes, context, bbox,
  section hierarchy, source type, and CRAAP scaffold.
- `AssetRef` carries span-level and asset-level references with quote hashes,
  locator ranges, bbox, and CRAAP data.
- `TableAsset` and `FigureAsset` preserve `source_block_id`, `source_order`,
  line spans, section id/title, and extraction source for MedPaper graph notes.
- `find_evidence_spans` and `verify_citation_ref` expose re-verifiable
  span-level AssetRef payloads.
- `citation_bundle(output_format="foam", citation_key="...")` emits a
  promotion-ready Foam evidence pack while keeping AssetRef verification data
  embedded beside each `^spn-...` block anchor.
- `evidence(op="health", wiki_root="...")` scans Foam Markdown notes for
  embedded span/table/figure AssetRefs and `[[note#^...]]` links, then reports
  stale source revisions, quote/hash mismatches, missing spans/assets, and
  missing target anchors.
- `document_asset(op="foam_notes", ...)` promotes manifest table/figure assets
  into `table_evidence` / `figure_evidence` Foam notes with source block/order,
  line span, section context, source PDF hash, and asset locator hash.
- `evidence(op="claim_promotion", ...)` produces exact-quote claim candidates
  with embedded AssetRefs and full verification payloads, and refuses Foam
  writes unless every candidate verifies against the current citation index
  first.
- DOCX/DFM blocks preserve Word-origin locators in `DfmBlock.metadata`:
  `source_part`, `source_story`, `source_element`, paragraph/table/source
  indexes, run ranges, table cell locators, text hash, and
  `locator_version=docx-dfm-locator-v1`.
- DFM -> DOCX Track Changes can emit reviewable `w:del` / `w:ins`, giving
  human-visible edit provenance before a changed DOCX is treated as a new
  source revision.
- `save_docx(track_changes=True)` writes `revisions.jsonl` with
  `schema=asset-aware.docx-revisions.v1`, block ids, old/new text hashes,
  char/byte ranges, context, the DOCX block locator, and a locator object for
  each delete/insert chunk.

Still intentionally delegated to MedPaper:

- Foam note path layout under `projects/{slug}/notes/**`.
- Citation-key selection and `[[citation_key]]` wikilink normalization.
- Foam frontmatter, `type` / `tags`, graph views, dashboards, and
  publish-safe reference packs.
- Deciding which evidence spans deserve promoted wiki pages.

## Current Adapter Boundary

The exporter currently consumes the PDF ingest side of `DocumentRepository`:
its document manifest, canonical Markdown segmentation, citation index, and
table/figure mappings. The v1 bundle uses generic source field names so future
adapters do not inherit a PDF-only public contract, but that naming choice is
not evidence that DOCX/DFM or arbitrary formats already flow through the
exporter.

A future DOCX/general adapter must explicitly normalize source identity,
segments, assets, revisions, locators, and citation references into the bundle
input contract. Until those adapter and conformance tests exist, use the
existing DOCX/DFM revision/locator workflows separately and describe
`document(op="export_assets")` as the PDF-backed vertical slice.

## Verification Checklist

Use this checklist to confirm alignment before claiming a source is
Foam/wiki-ready:

- Ingest or parse a source and build `manifest.json`, `blocks.json`, optional
  `segmentation.json`, and citation index.
- For a reusable per-document source pack, call
  `document(op="export_assets", doc_id="...", output_dir="agent-assets")` and
  keep `index.md`, `notes/**`, `media/**`, `assets.jsonl`, and `manifest.json`
  together.
- Verify the export target is inside the document data directory, every hub
  wikilink resolves to an emitted note/anchor, relative media links exist, and
  manifest artifact hashes match the copied files.
- Call `find_evidence_spans` for a representative claim and confirm the
  returned AssetRef includes `doc_id`, `span_id`, `source_revision_id`,
  `quote_sha256`, `line_range` or `char_range`, and page/bbox when available.
- Call `verify_citation_ref` with the returned AssetRef and require a success
  result before using the quote in a table or wiki note.
- Confirm table/figure assets have a stable source block or section mapping
  (`source_block_id`/`source_order` or section id/title).
- If the source is edited through DFM, use `save_docx(track_changes=True)` for
  reviewable Word revisions; require `revisions.jsonl` to map each generated
  edit chunk back to `block_id`, text hash, and char/byte ranges before
  promoting accepted edits.
- In MedPaper, materialize a reference/asset note and ensure the Foam-facing
  block anchor links back to the Asset-Aware `span_id` and text hash.
- Run MedPaper graph-health checks there for unresolved wikilinks/orphans;
  Asset-Aware should not attempt to replace that wiki-layer validation.

## External Reference Points

The contract above is based on MedPaper's documented LLM wiki/Foam boundary:

- `med-paper-assistant/docs/reference/llm-wiki.md`
- `med-paper-assistant/docs/reference/foam.md`
- `med-paper-assistant/docs/how-to/llm-wiki.md`
