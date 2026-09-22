# Native PDF region evidence

Release scope: **1.4.1**. Use the installed runtime contract and the limits below.

Goal: an Agent viewing a scanned PDF can identify a visual table cell/figure/label,
read a detailed crop, and link that exact source region to a typed target cell or
shape through the existing derivation ledger and portable Wiki. MCP checks source
identity and geometry; Agent supplies transcription and semantic/visual review.

`read_pdf_region` takes a complete native PDF page reference plus explicit
`pdf_region` selector, or an existing region reference without a new selector.
The selector is a nonempty rectangle of fractions [x0,y0,x1,y1] in [0,1], with
origin at the top-left of the displayed CropBox after page rotation. It does not
use native bottom-left PDF units or unrotated text-block coordinates. This makes
Agent-selected image regions independent of preview pixel dimensions. A bounded
render_size controls preview detail and is not part of region identity.

Return a complete small `native-pdf-region-v1` record, typed full region reference,
actual MCP PNG, image hash and renderer/version/geometry metadata. The immutable
reference binds page identity, full parent representation hash, selector and source
geometry. Verification proves this source-bound region, not OCR accuracy or a
renderer-independent pixel identity. Different render sizes preserve the reference.
No PDF content, crop box, page rotation, source bytes or managed history is changed.
No silent rectangle clipping, inferred table cells or automatic semantic mapping.

Use the existing bounded PDF subprocess for direct region rendering. Validate
finite geometry, pixel dimensions/origins, byte limits and source locator. Test
rotations, offset CropBox/MediaBox, UserUnit and annotations against independent
full-page pixel crops. Vector geometry fixtures compare exact pixels; embedded scans
allow measured partial-resampling differences. Independently replay direct rendering
exactly, compare full-page raster crop geometry/mean error, and reject shifted images
even if an attacker updates the PNG hash.
Parent/region hash tampering and stale revisions must fail or verify false.

Native verify, derivation endpoints and parsed record selections accept region
references. Wiki exports retain exact region JSON and actual region preview with
renderer metadata, plus the source PDF through existing provenance attachments.
A region note uses the selected citation display contract and stable wikilinks.
For an external source, only its registered title and canonical locator are known;
never inherit the target's authors/year/reference number. If the chosen template
requires unavailable bibliographic fields, record that display is unavailable with
the reason, retaining the selected contract and complete canonical reference.
Metadata supplied for the exported asset applies only to that same asset;
curated notes and prior snapshots remain protected. Historical assertions never
advance automatically when the PDF or destination workbook changes.

Validation: domain/schema/budget regressions; independent geometry and actual
SDK2 PNGs; an actual default-model Codex flow transcribes cropped scanned cells,
creates/updates structured target data, records per-cell provenance, rereads full
records, verifies history and exports exact Wiki artifacts. Include real-file
coverage where a suitable primary/public-domain fixture can be pinned and audited.

Primary references:
- https://pymupdf.readthedocs.io/en/latest/page.html
- https://pymupdf.readthedocs.io/en/latest/recipes-images.html
- https://github.com/pymupdf/PyMuPDF
- https://github.com/pikepdf/pikepdf
