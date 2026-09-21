# Native PDF annotations (Unreleased / 1.4.x)

Public version remains **1.4.0**; the next consolidated patch is **1.4.1**.

Annotations are independently addressable assets within a PDF revision. A comment,
its visible appearance and the text underneath a highlight are different objects.
The MCP provides native operations, evidence and mechanical checks. The Agent
decides whether a comment is accurate, covers the right text and renders correctly.

## Contract and identity

Discover `pdf_annotations_enabled` and assemble complete `contract_request` and
per-operation `schema_request` pages. `read_pdf_annotations` requires `asset_id`
and `revision`; its paged `annotation` value contains a complete catalog, a catalog
hash and the latest matching revision's operation receipt. `read_pdf_annotation`
also requires `pdf_annotation_locator`. Assemble every `text_excerpt` at one
`text_sha256` before using the record.

`native-pdf-annotation-ref-v1` binds the asset and revision to a page locator,
zero-based annotation-array index, native object/generation and representation
hash. Direct dictionaries use object ID zero. Names such as `/NM` are retained
data, not trusted unique identities. Native graphs, metadata, appearance streams,
raw/display geometry and unresolved popup/reply links remain inspectable. Unknown
annotation types and form widgets can be read without claiming edit support.

## Supported edits

`update_pdf_annotations` takes `expected_revision` and `pdf_annotations_update`
with 1–32 edits. Every existing target is used at most once per batch; all references
address the original input revision and are checked before any mutation.

| Edit | Required intent |
| --- | --- |
| `create` | Complete `page_reference`, typed `appearance`, optional `metadata`. |
| `update` | Complete annotation `reference`; `metadata` and/or `replace_appearance`. |
| `delete` | Complete annotation `reference`; `scope: annotation_and_owned_popup`. |

Appearance kinds: `Text` uses `point`; `FreeText`, `Square`, `Circle` use `rect`;
`Line`, `PolyLine`, `Polygon` use `vertices`; `Ink` uses `strokes`; `Highlight`,
`Underline`, `StrikeOut`, `Squiggly` use `quads` in UL/UR/LL/LR order. Positions are
displayed rotated CropBox fractions, top-left origin, 0–1. Read geometry retains
out-of-crop coordinates. Font size and border width are points. The schema lists
which style fields each kind accepts; unused fields are rejected, including nulls.

Omitted metadata stays; explicit null removes the native key. Metadata-only edits
retain foreign appearance bytes. Changing visible FreeText requires explicit
same-kind appearance replacement. Its authored text can also appear in ordinary
page text extraction, so inspect annotation records before attributing text to the
original body. Rich comment formatting and unmodeled appearance dependencies have
explicit limits. Existing annotation kinds are never silently converted.

## Preservation and review

New appearances are created in disposable PDFs matching native geometry, then
imported as annotation objects. Exact native inverse checks, serialized readback,
source/version checks and bounded independent pixels precede commit. The body
pixel comparison uses annotation-free reader copies: `annots=False` alone was
observed to change compositing by one color level after adding a Highlight. These
copies are verification inputs only. The requested PDF retains all annotations;
body hashes and untouched-page pixels are compared exactly, without tolerances.
Reader copies also use the existing strict parser proof for equal duplicate stream
length declarations. Conflicting lengths or unrelated warnings remain rejected;
the original NASA corpus exposed a missing application of this check in the copy.

Shared arrays/objects, locks, signatures, widget structures, standalone popups and
surviving incoming dependencies block unsupported changes. Delete a reply thread
only by explicitly including its dependent annotations. Native array indirection,
source bytes and historical revisions remain intact. Deletion is not secure erasure.

Read the complete `review_request`, new records and actual affected page PNGs.
The Agent checks positioning, clipping, glyphs, comment meaning and viewer behavior.
Native checks do not establish semantic support or universal PDF viewer fidelity.

## Evidence and Wiki

Full annotation references support verification, parsed-value/Unicode selections,
derivation endpoints and CSL citations. Old references never migrate after edits
or deletion. Custom citation displays include page, annotation index and native
object identity; the canonical reference remains separate from presentation.

Annotated PDFs use `pdf-annotations-v1`, retaining exact PDFs, complete page
previews/records, `annotation-catalog.json`, `annotations.jsonl` and linked comment
notes. Unannotated PDFs retain byte-identical legacy `pdf-pages-v1` output. Old
projections and user-curated notes are preserved.

## References

- [PyMuPDF annotation APIs](https://pymupdf.readthedocs.io/en/latest/annot.html):
  creation and appearances; existing project dependency.
- [PyMuPDF guidance on modifying foreign annotations](https://pymupdf.readthedocs.io/en/latest/recipes-common-issues-and-their-solutions.html#changing-annotations-unexpected-behaviour):
  informs explicit appearance replacement and preserving foreign AP streams.
- [pikepdf annotation objects](https://pikepdf.readthedocs.io/en/stable/api/models.html#pikepdf.Annotation):
  native PDF objects, relationships and exact source preservation.
- [pypdf annotation creation](https://pypdf.readthedocs.io/en/stable/user/adding-pdf-annotations.html):
  API design reference; no new runtime dependency or copied implementation.

These libraries supply document primitives. Versioned assets, guarded intent,
complete review receipts and durable evidence links are this project's integration.
