# Real PDF corpus and actual Agent evaluation

Status: implemented, real SDK2 and actual Agent verification completed; public version stays 1.4.0, Unreleased 1.4.x.

## Purpose and evidence boundary

Extend synthetic PDF tests with unchanged public documents: the NIST SRM 1648a
certificate (digital text, Table 1 on PDF page index 4) and the NASA Apollo 11
mission report (historic scans with an imperfect OCR layer, Table 3-I on PDF
indices 17 and 18). PDF indices are zero-based; printed page labels differ.
Neither successful cases nor SDK checks certify arbitrary-document fidelity.

The manifest pins original HTTPS URLs, byte lengths, SHA-256, page counts, table
page indices, visually calibrated content bounds, string columns and independently
reviewed expected rows. Keep complete original PDFs outside Git. Explicit download
or an operator-supplied corpus directory is required; normal pytest has no network
dependency. Reject size/hash drift before any evaluation. Never silently refresh
the expected answer when an upstream PDF changes. Preserve original scan/OCR data.

Sources:

- https://tsapps.nist.gov/srmext/certificates/1648a.pdf
- https://ntrs.nasa.gov/citations/19700008096
- https://ntrs.nasa.gov/api/citations/19700008096/downloads/19700008096.pdf

Both are US government publications. Store only source metadata and factual table
transcriptions in Git; no government logo, endorsement or certificate validity claim.
The NASA record identifies the report as work of the US government. This corpus is
for document behavior, not scientific/mission analysis or use of the certificate.

## Transcription contract

Transcribe the entire selected tables, in source row order. NIST has 25 rows and
columns `Element`, `Mass Fraction`, `Units`. Flatten superscript method letters
into immediately following parentheses, for example `(a,b)`. Retain one space
between element name and symbol and around ±. NASA has 34 event rows across two
pages and columns `Event`, `Time (hr:min:sec)`; preserve colons, decimal digits,
leading zeros and the engine-ignition `*`. The Range zero explanatory line is
context, not an event row. Table titles, repeated headers and explanatory footnotes
are not data rows. Join layout-only whitespace with single ASCII spaces. Do not
normalize Unicode, convert numbers, infer dates, drop footnotes or round values.

Oracle provenance: read the original page images before writing expected rows;
compare the digital NIST text as an additional check. NASA OCR is explicitly not
the authority. Fixture answers live outside the model workspace and are not put
in its prompt or passed through MCP. The prompt specifies task/schema and layout
normalization, not expected values or source region coordinates.

## Required evaluation

1. Verify source identity, register the complete PDF, read the selected complete
   page records with pinned revision/hash and view actual full-page MCP images.
2. Agent chooses a full-table region for each page. Read complete region records
   and actual MCP PNGs; check the displayed glyphs. The independent audit checks
  chosen rectangles contain calibrated content bounds, source identity, actual
  raster pixels and image hashes. Pixel agreement does not establish semantics.
   Original scan resampling differs between a clipped render and a full-page
   render followed by a pixel crop (NASA page17 mean channel difference5.058 at768).
   Require exact pixels against an independently constructed direct source render;
   retain the full-page crop comparison as a diagnostic metric, not a universal
   less-than-one threshold inherited from synthetic scans. Keep independent glyph
   bounds and complete string-oracle checks. Both render paths share MuPDF.
3. Create an independent UTF-8 BOM/CRLF CSV string table. Read complete structure,
   all data fields and headers. Compare every value to the independent oracle.
4. Record one explicit source-region derivation per table-page first-row value,
   with complete source/target references and hash-pinned ledger reads. This is
   sampled provenance coverage, not a claim of per-field provenance for all rows.
5. Exercise update/restore, row insertion/deletion, column insertion/deletion.
   Read complete operation receipts after each change. Independently compare each
   native revision, including same-byte revisions with distinct history entries.
   Check historical references remain valid and assertions do not auto-migrate.
6. Export an original-revision Wiki with source attachments and custom citation
   display; publish the final CSV. Verify exact original PDF bytes/mtime, immutable
   histories, CSV bytes/values, source attachments and exported evidence artifacts.

Actual Codex runs are explicit opt-in, use the user's default model without a
model override, and enable only this checkout's document MCP tool. No shell, web,
other servers, subagents or expected-answer access. Audit every action. Preserve
raw event traces, first transcription, later corrections, errors and run outcome.
Never replace a failed run with a passing retry or describe model prose as proof.
SDK2 regression exercises source/region/CSV/provenance operations deterministically;
it is reported separately and cannot stand in for actual Agent visual review.

Reference design: [pdfplumber](https://github.com/jsvine/pdfplumber) exposes source
characters/geometry and visual debugging, and notes that extraction works best on
machine-generated PDFs. Reuse that inspectable-evidence principle; retain the
existing PyMuPDF/pikepdf adapters and test real images instead of introducing a
new parser merely to make a fixture pass.
