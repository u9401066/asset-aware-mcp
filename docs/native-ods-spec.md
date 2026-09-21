# Native OpenDocument spreadsheets

Status: implementation in progress on main, public 1.4.0; next consolidated
release 1.4.1. This specification does not advertise an installed MCP operation.

ODS must remain ODS throughout native CRUD. An XLSX/CSV conversion is a separate
derivative, with its own source relationship. The first implementation segment
provides a bounded package/worksheet adapter; subsequent segments connect it to
revision-bound MCP operations, evidence, citations, Wiki and actual Agent review.
Those integrations are required before claiming the ODS workflow complete.

## Representation and preservation

- Validate ZIP inventory, MIME/manifest agreement, XML and decompression budgets.
  Preserve package members not explicitly changed, including styles, images,
  settings and metadata. Preserve source ODF version; new documents use ODF 1.3
  for existing Calc compatibility. Do not claim full ODF schema conformance.
- Row/cell repetition stays compressed. Reads identify zero-based table index,
  exact table name and logical row/column, plus physical repetition bounds.
  Read catalogs list physical cell ranges, never silently truncate logical cells.
  Operational limits are explicit and are not represented as ODF format limits.
- Keep raw typed lexical values, displayed paragraph content, formula expression
  and its namespace, native attributes/XML separate. Formula caches are never
  verified results. Covered cells are not ordinary empty cells. XML paths and
  coordinates belong to the exact source revision and never migrate implicitly.
- Cell updates split only the affected repetition ranges. Preserve cell/row
  attributes and all other package content. Preserve XML structure outside the
  declared edits; changed XML serialization is not promised byte-identical.
  Growing the used grid extends native column declarations in compressed form;
  record that deterministic repair so independent readers see the full width.
- Clear means clearing the cell value, not deleting the row, column, style or
  historical source. Literal string input is never interpreted as a formula.
  Formula authoring uses OpenFormula explicitly; no calculation is performed.
- Rich text replacement requires an explicit display policy. A plain display
  replacement may replace paragraph runs but retains cell formatting and attached
  annotations. Agent must review that formatting decision. Existing rich text is
  otherwise retained in native reads. No implicit flattening of unrelated cells.
- Signed/encrypted packages, protected/tracked content and ambiguous or dependent
  edits fail with an explicit explanation. Read support must not imply write
  support. Repetition containing identity-bearing or dependent objects cannot be
  duplicated without a mapping-aware operation.

## Verification and remaining work

Every edit is checked by reopening the actual output. Receipts identify changed
parts, complete before/after records, deterministic changes and Agent review needs.
No-op writes return original bytes. Actual Calc testing found that retaining numeric
formula caches after changing a precedent could display the old result. Transactions
therefore invalidate typed formula caches and record the affected physical ranges;
formula expressions, paragraph formatting and cell styles stay intact. Existing
display paragraphs are unverified cached display, never a fresh calculation. A
separate reader/render must recalculate and review results; sources are not resaved.
Tests must cover compressed ranges, namespace aliases, rich text, native value
types, merged/covered cells, malformed packages, output preservation and an
independent actual Calc read/render. MCP source/revision guards and complete
hash-paged evidence will use the same adapter, with dedicated ODS locator types.

Remaining beyond the first adapter: sheet/row/column lifecycle and dependency
remapping, rich-run edits, recalculated renditions, full evidence/Wiki integration,
SDK2 round trips and actual default-model Codex evaluation. ODT/ODP and the other
format gaps remain part of the broader goal.

## References and reuse choices

- [OASIS ODF packages](https://docs.oasis-open.org/office/OpenDocument/v1.4/os/part2-packages/OpenDocument-v1.4-os-part2-packages.html):
  MIME member placement, manifest binding and signature/encryption handling.
- [OASIS ODF schema](https://docs.oasis-open.org/office/OpenDocument/v1.4/os/part3-schema/OpenDocument-v1.4-os-part3-schema.html):
  native rows/cells, repetition, typed values, whitespace and formula namespaces.
- [odfdo](https://github.com/jdum/odfdo): Apache-2.0 Python ODF implementation;
  useful reference and independent reader. Its documented save path writes ODF 1.4,
  so a generic save must not silently replace our source-version preservation.
- [odfpy](https://github.com/eea/odfpy): older OpenDocument 1.2 API, useful historical
  reference. Neither library substitutes for source identity or Agent review.

The adapter uses the existing locked lxml dependency; no new runtime dependency
or project version change is needed for this segment.

## Developer verification

`tests/unit/test_native_odf_package.py` and `tests/unit/test_native_ods.py` cover
the bounded kernel, compressed coordinates, literal types, namespace aliases
(including non-ASCII XML names), cache invalidation and preservation guards.
`tests/integration/test_native_ods_calc.py` requires `NATIVE_ODS_RENDER_TEST=1`
and actual Calc; `NATIVE_ODS_CALC_BIN` can select a private test installation.
It checks numeric/Boolean/string formula read-back, styles, actual PDF content
and unchanged-region geometry/pixels without resaving the source. Comparison
formula caches can be exported as Boolean or numeric values by different Calc
versions: use a separately authored expected workbook converted by the same Calc
as the type/value and full-page rendering oracle. Do not accept arbitrary truthy
values or infer a native Boolean from a comparison formula; explicitly authored
Boolean cells still require Boolean read-back. Exported font metadata is checked
against that independent control and the actual red PDF glyphs; a specific RGB
storage field is not required. CI installs Calc and requires these tests;
Python 3.10 also runs the kernel tests.

`tests/integration/test_native_ods_odfdo.py` is an optional independent reader
check with `NATIVE_ODS_ODFDO_TEST=1`; odfdo 3.25.0 was isolated outside the runtime
environment. `tests/native_ods_artifact_smoke.py` compares all installed source
files and replays exact ODS bytes/full receipts against the actual Calc fixture
in clean wheel and Docker installations. Neither test substitutes for the
still-pending MCP/Agent/evidence/Wiki integration.
