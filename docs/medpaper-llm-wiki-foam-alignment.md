# MedPaper LLM Wiki / Foam Alignment

This document records how Asset-Aware MCP should interoperate with
`u9401066/med-paper-assistant` without duplicating MedPaper's wiki-writing
responsibilities.

## Boundary

Asset-Aware MCP is the source-material decomposition and locator authority.
It should emit document assets, evidence spans, and citation-ready references
that can be re-verified against the original file.

MedPaper is the durable LLM wiki writer. It owns Foam-facing reference notes,
knowledge maps, synthesis pages, wikilinks, frontmatter, dashboards, and graph
views.

Foam is the Markdown navigation layer. It owns wikilinks, backlinks, graph
views, hover previews, block embeds, and query rendering.

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

Asset-Aware does not need to write Foam files directly. It should give
MedPaper enough data to materialize notes like:

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

## Current Asset-Aware Coverage

Already aligned:

- `EvidenceSpan` stores stable `span_id`, `source_revision_id`,
  `locator_version`, line/char/byte ranges, text hashes, context, bbox,
  section hierarchy, source type, and CRAAP scaffold.
- `AssetRef` carries span-level and asset-level references with quote hashes,
  locator ranges, bbox, and CRAAP data.
- `TableAsset` and `FigureAsset` preserve `source_block_id`, `source_order`,
  line spans, section id/title, and extraction source for MedPaper graph notes.
- `find_evidence_spans` and `verify_citation_ref` expose re-verifiable
  span-level AssetRef payloads.
- DFM -> DOCX Track Changes can emit reviewable `w:del` / `w:ins`, giving
  human-visible edit provenance before a changed DOCX is treated as a new
  source revision.
- `save_docx(track_changes=True)` writes `revisions.jsonl` with
  `schema=asset-aware.docx-revisions.v1`, block ids, old/new text hashes,
  char/byte ranges, context, and a locator object for each delete/insert
  chunk.

Still intentionally delegated to MedPaper:

- Foam note path layout under `projects/{slug}/notes/**`.
- Citation-key selection and `[[citation_key]]` wikilink normalization.
- Foam frontmatter, `type` / `tags`, graph views, dashboards, and
  publish-safe reference packs.
- Deciding which evidence spans deserve promoted wiki pages.

## Verification Checklist

Use this checklist to confirm alignment before claiming a source is
Foam/wiki-ready:

- Ingest or parse a source and build `manifest.json`, `blocks.json`, optional
  `segmentation.json`, and citation index.
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
