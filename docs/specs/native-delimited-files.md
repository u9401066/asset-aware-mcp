# Native CSV / TSV assets

Status: implemented and locally verified, Unreleased within 1.4.x; public remains 1.4.0.

Purpose: human CSV/TSV files become editable native table assets with retained source
bytes, exact field evidence, complete review receipts and portable Wiki snapshots.
MCP checks encoding/dialect/structure/source integrity. Agent interprets headers,
types, units, semantics and downstream spreadsheet rendering; no inferred headers,
number conversion, automatic dialect guessing or formula evaluation.

## Contract

- `create_delimited`: independent CSV/TSV from ordered rows of exact string values,
  explicit/default dialect, encoding/BOM and new-record separator.
- `read_delimited`: complete hash-pinned paged structure, dialect, encoding/BOM,
  logical row lengths, physical separators and latest matching operation result.
  Identical file bytes can recur with a newer receipt; assemble at one text_sha256
  and restart if it changes, as with workbook reads.
- `read_delimited_cell`: exact revision, zero-based logical row/column and dialect;
  complete paged field JSON includes decoded value, raw spelling, source byte/char/
  physical-line spans, context and a full `native-delimited-cell-ref-v1`.
- `update_delimited`: one checked operation at an expected file revision. Set a batch
  of fully referenced fields, insert/delete logical rows, or insert/delete columns.
  Column edits require the requested position to exist in every affected row; ragged
  inputs remain readable and individual fields editable without implicit padding.
- Existing register/inspect/history/refresh/publish/writeback/archive apply. Native
  verify, parsed selections, derivation endpoints and Wiki accept field references.

Dialect defines one-character delimiter/quote/escape, doublequote, and optional
explicit encoding. CSV defaults comma and TSV defaults tab; quote defaults double
quote; no skipinitialspace. Encoding auto-detects UTF BOMs, otherwise UTF-8; explicit
UTF-16 LE/BE, CP950, CP1252 and Latin-1 are supported. Strict decoding and exact byte
locators never replace invalid characters. BOM conflicts are explicit errors.

Values stay strings, including empty values, leading zeros, exponent notation,
commas/newlines within quotes, Unicode variants and formula-looking text. Blank
logical records have zero fields, distinct from a quoted empty single field. Keep
mixed CRLF/LF/CR separators and the presence/absence of a final separator.

Mutations splice native bytes. Unchanged fields retain their quoting/escape spelling,
encoding, BOM and separators exactly. Replaced fields retain quoted spelling where
possible; new values receive required quoting/escaping. New rows use the explicit
record_separator and terminate each inserted row. Appending after an unterminated
row inserts one separator and records the repair. Deleting all columns preserves
zero-field rows, inserting a required final separator if needed rather than silently
losing the last empty record. If column deletion leaves one unquoted empty field,
quote that surviving empty string and record the grammar repair; it is not a blank row. Operations reparse with the same dialect and compare
all expected values/row correspondence before one repository CAS. Impossible
encoding/quoting, malformed CSV, stale/tampered references or budget excess fail
before commit. A byte-identical update returns its complete no-change receipt and
creates no history entry; read_delimited retains the last committed receipt. Sources are changed only by explicit checked writeback.

Parsing uses Python's maintained csv implementation for values plus an independent
source-boundary scanner. A bounded child process owns csv.field_size_limit so server
and other tools' global CSV state does not change. Byte spans are absolute original
file offsets (including BOM); character spans address decoded text without BOM;
logical rows differ from physical lines for quoted/escaped multiline values.
Bounds: 16 MiB file, 20,000 fields/rows, 1,024 inserted/deleted rows or deleted columns, one inserted column per call,
1,000 replacements and fixed process/result/time budgets. No silent truncation. All-enabled contract discovery must fit the existing 10,000-
character response budget; retain operation/schema inventory and compact repeated
overview prose. Detailed constraints stay in typed schemas, format guides and harness.

Wiki uses a distinct dialect-bound projection and exact source attachment, field
records/notes with canonical locators, and existing custom citation display. Retain
old snapshots and curated notes. Historical field references never move after
structural edits; Agent creates replacement derivations explicitly.

## Verification

Differential fixtures against Python csv; UTF-8/BOM/UTF-16/CP950/CP1252; mixed EOL,
multiline/escaped/unquoted fields, blank/ragged records and missing final newline.
Native byte preservation outside edits, strict round-trip values, stale CAS,
malformed dialect/input, zero-field row retention and exact evidence spans.
Actual SDK2 CRUD/derivation/Wiki/source refresh and default Codex PDF-region→CSV
transcription/row-column CRUD→historical evidence/Wiki/publish with independent
raw-byte, csv reader and trace audit. Full release checks before direct-main push.

References considered:
- Python csv: https://docs.python.org/3/library/csv.html
- CleverCSV: https://github.com/alan-turing-institute/CleverCSV (dialect discovery;
  an inferred dialect is not an authoritative write contract).
- Microsoft jsonc-parser: https://github.com/microsoft/node-jsonc-parser (localized
  edits to preserve source formatting; JSON support remains subsequent work).
- Tree-sitter: https://github.com/tree-sitter/py-tree-sitter (syntax byte spans;
  additional structured formats remain within the active goal).
