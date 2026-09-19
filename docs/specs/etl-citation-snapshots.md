# ETL evidence snapshots for CSL (Unreleased / 1.4.x)

## Problem and boundary

Native citations already bind immutable revisions. Legacy PDF ETL span/table/figure
AssetRefs point into a mutable extraction directory. A formatted citation must not
silently resolve a changed extraction or lose its original evidence after deletion.
Capture an explicitly requested, verified ETL reference as an immutable managed
snapshot, then use that snapshot alongside native sources in one CSL document.
DOCX DFM ingestion is a separate representation; existing native DOCX block refs
remain its CSL route. Public version stays 1.4.0, with no per-feature tag.

The snapshot proves exact original bytes, captured extraction content and locator
consistency. It cannot prove extraction accuracy, semantic support, bibliographic
truth or correspondence between printed citation pages and source page indices.
Agent review owns those checks and correction decisions.

## Operations through evidence

- `inspect_etl_source(ref={doc_id,source_type,source_id})`: read a selected current
  span/table/figure, returning its full canonical AssetRef and complete record via
  hash paging. This writes no snapshot and allows long refs to be obtained without
  accepting a truncated preview or writing a temporary Wiki just to read evidence.
- `capture_etl_source(ref=<complete current AssetRef>)`: accept canonical span,
  table or figure references. Verify the reference against captured canonical
  artifacts, not an untrusted/stale citation-index cache. Preserve full quotes,
  typed locators and complete table/figure metadata. Reject previews, missing
  fields, wrong hashes and stale references. Capture creates managed evidence;
  source files are never changed and no citation is automatically promoted.
- `read_etl_source(ref=<etl-citation-ref-v1>)`: validate the complete immutable
  inventory and return the full record/reference through existing hash paging.
  Reads survive changes/deletion of the original ETL directory.
- `view_etl_source(ref=<etl-citation-ref-v1>, render_size=...)`: return a real MCP
  PNG of the captured original PDF page at its recorded one-based source page.
  Reuse the bounded native PDF renderer. Missing page or non-PDF source fails
  explicitly. Rendering is inspectable evidence, not a visual correctness verdict.
- `csl_contract` advertises these operations and complete snapshot-reference
  schema. `render_citations` accepts captured refs in the existing `sources` map.
  Raw mutable ETL refs must first be captured. Mixed native/ETL citations preserve
  both reference kinds without rewriting their identities.

Capture/read use text_offset/text_limit/expected_text_sha256. A mismatching expected
hash must be rejected before capture publication. Follow every next_text_offset;
snapshot references exclude local paths and mutable current-state labels. Captured
raw manifests can contain descriptive historical paths; they never select files
during immutable readback or portable Wiki verification.

## Snapshot and publication invariants

Each snapshot contains exact original source bytes checked against the manifest,
raw canonical markdown, raw blocks and source manifest, selected complete evidence,
and figure/optional raw-image bytes when relevant. Paths must resolve within the
ETL document directory, with no symlinks or special files. Bounded reads record file
identities and compare the entire captured set again before publication. Canonical
span content is rebuilt from the captured markdown/blocks and checked byte-for-byte.
No empty or stale citation index is accepted as proof of current content.

The snapshot ID is SHA-256 of its canonical manifest; every artifact has a size
and hash, and the reference binds the complete record hash and source identity.
Managed snapshots use exclusive writes and manifest-last publication. Reuse checks
exact files/inventory; modified or interrupted snapshots fail without overwriting.
128 MiB total snapshot budget and bounded metadata/input/output apply. No caller
paths are stored in references or used to locate snapshots.

CSL Wiki exports include the exact snapshot evidence and all original attachments,
with content-addressed names, complete source mappings and links from cite notes.
An ETL directory changing later cannot change the saved snapshot or CSL output.
Modified snapshots fail verification; human-edited Wiki notes remain protected.

## Architecture and verification

Move existing pure AssetRef construction/verification into application helpers
with presentation compatibility exports. Domain defines the immutable reference
and snapshot/source IO ports. Infrastructure handles bounded source capture and
manifest storage. Application coordinates checks, snapshot creation/readback and
CSL integration. Reuse the native immutable publisher and PDF worker where suitable.

Regressions cover span/table/figure captures, forged quote/locator/cache, original
source mismatch, changed extraction with retained original bytes, file races,
traversal/symlinks, oversized inputs, missing/extra/tampered snapshot files, complete
Unicode hash paging and no-write hash rejection. SDK2 uses actual PDF ingestion,
mixed source citations, actual page images, historical snapshots and protected Wiki.
An actual default-model Codex workflow independently discovers, captures, reads,
views and cites extracted assets; no preselected replacement model or subagents.

## References reviewed

Docling's structured document model keeps text, tables, pictures, hierarchy and
available geometry/provenance separate; its graph provenance records chunk text,
item references, geometry and content hashes. These are useful design references,
not evidence that our extraction is correct or that arbitrary source round trips
are lossless. This change adds no new extraction backend or dependency.

- [DoclingDocument model](https://github.com/docling-project/docling/blob/main/docs/concepts/docling_document.md)
- [Docling graph provenance](https://github.com/docling-project/docling-graph/blob/main/docs/fundamentals/graph-management/provenance.md)
