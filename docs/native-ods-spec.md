# Native OpenDocument spreadsheets

Status: implementation in progress on main, public 1.4.0; next consolidated
release 1.4.1. Discover `ods_enabled` in the installed runtime before using ODS operations.

ODS must remain ODS throughout native CRUD. An XLSX/CSV conversion is a separate
derivative, with its own source relationship. The bounded package/worksheet adapter connects to revision-bound MCP operations,
evidence, citations and Wiki. Actual Agent evaluation is scoped to the exercised
operations; format lifecycle and reader-specific fidelity gaps remain explicit.

## MCP, evidence and portable snapshots

The integration adds `create_ods`, `read_ods`, `read_ods_cell` and `update_ods`.
Reads require an immutable revision. `read_ods` pages physical ranges with
`offset`/`limit`; each selected page includes the complete operation receipt and
is independently serialized with hash-paged Unicode text. Continue text pages
with the first page's `ods_text_sha256`; a changed receipt must fail continuation.
Follow both text and physical-record continuations. Cell reads bind one logical
coordinate, including explicit absence when no native cell exists.

`native-ods-cell-ref-v1` binds asset, revision, content.xml, exact table index/name,
logical row/column and a SHA-256 of the complete native record. A repeated-range
anchor reference identifies that anchor only; it is not verification of all cells
represented by the range. Selection, derivation and CSL inputs accept these full
references. Custom citation locators display the ODF part, table index/name and
one-based row/column, independently of caller bibliographic metadata.

Updates require `expected_revision` and 1–100 full cell references, explicit typed
values and rich-display replacement policy. All references address the original
revision, each logical target occurs once, and every full record is checked before
any edit. Clear uses a blank value; row/column deletion is not implied. Reopen the
actual output and ensure the full report remains readable before one repository
commit. Register/publish/writeback/refresh/archive retain existing source and CAS
checks; creation is source-independent. ODS-specific source writeback is never an
implicit side effect of a cell update.

`ods-physical-ranges-v1` Wiki snapshots retain the exact .ods, complete physical
range records, anchor references, operation receipt, citation presentations and
explicit review limits. They never expand repeated ranges into invented records.
Derivation endpoints additionally retain exact referenced logical cell records,
including non-anchor and implicit coordinates. Receipt identity participates in
snapshot identity, so distinct reports for identical file bytes cannot overwrite
old snapshots. Formula caches/display, semantic support and actual Calc rendering
remain Agent review work; native hashes do not certify them.

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
hash-paged evidence use the same adapter, with dedicated ODS locator types.

Remaining beyond the first adapter: sheet/row/column lifecycle and dependency
remapping and rich-run edits. Recalculated renditions are described below. SDK2 integration covers
restart, full receipts,
source preservation and unchanged portable snapshots. ODT/ODP and the other
format gaps remain part of the broader goal.

## Native ODS renditions (Unreleased)

Discover `workbook_rendering.source_formats`; `ods` enables the existing
`create_workbook_rendition` request with an exact asset/revision, explicit
`print`/`whole_sheet` mode and `recalculate`/`prefer_cache` import policy. The
optional LibreOffice Calc process reads an unchanged private `.ods` copy and
creates a separate PDF. No intermediate XLSX conversion or source writeback occurs.
Read the complete `read_rendition` receipt at its creation revision and hash,
then every PDF page record and actual PNG. The receipt records ODFRecalcMode,
renderer version, exact source reference, sheets, page count and PDF hash.
Whole-sheet mappings retain content.xml/table index/name and verified page order;
print pages have no inferred cell/sheet mapping. Wiki retains the exact `.ods`.

ODS resource checks resolve package-relative paths and OpenFormula namespaces,
distinguishing quoted literals/local references from external resources. Local
rasters and embedded ODF charts are supported, including chart parent-data links
and bounded native GDIMetaFile fallbacks. Foreign/nested metafile payloads and
unsupported comments retain explicit limits. Scripts, linked data, external
formula resources and unknown embedded objects need a dedicated workflow.
These are mechanical checks, not an operating-system sandbox or a visual verdict.

Calc 7.3 and 24.2 tests independently author/import ODS, then compare complete
rendered pages with direct same-version Calc conversion. They cover chart/raster
content, native style retention, cached999 versus recalculated3, all four
mode/policy combinations, blank/hidden sheets, source bytes/mtime, SDK2 restart,
unchanged preview PNGs and byte-identical Wiki snapshots. Whole-sheet rendering
can clip text that overflows the last populated column; the Agent must report it.

`prefer_cache` is not a promise to freeze formula values. An unstyled formula can
recalculate to determine its number format even with ODFRecalcMode=never. A
separate regression compares that case with independent Calc output; explicitly
styled fixtures verify cached999 versus recalculated3 without accepting arbitrary
values. Source formula caches remain unchanged in both cases. This follows the
[Calc import implementation](https://github.com/LibreOffice/core/blob/master/sc/source/filter/xml/xmlcelli.cxx)
and the separate [ODF recalculation setting](https://github.com/LibreOffice/core/blob/master/officecfg/registry/schema/org/openoffice/Office/Calc.xcs).
Native vector record framing is informed by the upstream
[SVM reader](https://github.com/LibreOffice/core/blob/master/vcl/source/filter/svm/SvmReader.cxx);
no new parsing dependency or copied upstream implementation is introduced.

The default-model evaluation is available through
`python -m tests.codex_workbook_rendition.run --format ods --output <new-directory>`.
It uses only the isolated document MCP, reads complete source/receipt/page records,
edits the managed formula and requires actual PNGs for all three frozen PDFs.
Its independent auditor retains the existing XLSX evaluation and checks ODS XML,
formula/style preservation, historical refs, pixels and the native Wiki attachment.

Codex, Cline and Copilot guidance now follows this rendition workflow and ships
with the extension. It requires advertised source formats, complete receipts and
every actual PDF page, distinguishes requested calculation policy from observed
results, and leaves semantic/visual correction with the Agent. A stored preview
does not recalculate when read; new PDF edits do not inherit old sheet mappings.

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
in clean wheel and Docker installations. These kernel checks complement the
MCP/Agent/evidence/Wiki verification described below.

## Formula-cache traversal performance (Unreleased)

Before this optimization, the 5,000-formula storage replay took about19.5s locally. Repeated
`read_cell` scans inside cache invalidation and serialized cache readback make
work quadratic in physical rows. Operation-result archives solve index capacity,
but do not address this traversal cost.

Require work proportional to physical row/cell records for cache collection and
readback. Construct records from visited XML elements and exact compressed range
coordinates, then verify every planned cache against one traversal of reopened
output. Keep the existing edit guards, physical/logical budgets, namespaced XML,
formula expressions, style metadata, repeated ranges and complete before/after
receipts. Do not expand logical repetitions or omit cache evidence to save time.

Verification must compare exact output bytes and complete receipts with the
published implementation, prove bounded physical traversal without flaky timing
thresholds, cover grouped/repeated rows and columns, and replay the 5,000-formula
case in actual package artifacts. Wall-clock benchmarks supplement those checks.
The MCP/evidence/Wiki integration above now uses this traversal. Public1.4.0,next1.4.1.

Implementation now shares exact cell-record construction between point reads and
physical traversal. Cache collection retains each visited record; reopened output
is traversed once and matched to every planned locator/range. Missing, duplicate
or changed targets fail. No mutable coordinate index or logical range expansion
is introduced. Other point-read/edit costs are unchanged.

The deterministic regression initially observed41,813physical row visits for200
formulas and163,613for400. Both now satisfy a bound proportional to physical rows
and match complete output/receipt hashes captured from published5093031. Grouped
rows, repeated300columns*1000rows, rich cached display and Unicode formula aliases
retain exact evidence. A5,000-formula replay measured0.335961s versus19.535553s,
about58.15x in this run; timing varies by environment. Output SHA-256 remains
`768d0e4360cd50b2e1d55cea290d672b998061a5ad6255e89b407ab31fc55695`; the complete
12,387,293-byte canonical result hash remains
`990a3f5790fe0e7b99aad61ba6a5f4ea82c141bb85694c9a756c9a6465f79b05`.

Focused60kernel tests and actual Calc7.3/odfdo checks pass. Package replay can use
`tests/native_operation_results_artifact_smoke.py --baseline <baseline.json>` to
verify the same large output and complete result in an installed wheel/container.
Full local validation passed: 3,789 tests / 33 environment skips (749.77s),
including the optional existing Writer/CJK/Calc/odfdo/public-PDF fixtures.
Python3.13 wheel and Python3.12 Docker match all335source files, the exact large
result/output goldens and the Calc fixture; doctor,30tools and SDK2stdio pass.
VSIX199tests,64packagedentries and install/update pass. Each publication also
requires exact-head remote CI and deployed-byte verification.

## Default-model ODS evaluation

Run `uv run python -m tests.codex_native_ods --output /tmp/ods-evaluation-new`
with explicit model-use authorization. The runner selects no model override,
allows only this checkout's document MCP, and retains all events and artifacts.
Replay with the same command plus `--audit-only` and the existing output directory.
The XML/ZIP auditor is independent of the production ODS reader and verifies
complete canonical reads, native values/styles, unchanged members, source mtime,
history, derivation endpoints and snapshot file hashes.

The 2026-09-21 successful final-source run completed 223 MCP calls with zero tool errors in
197.33 seconds: 27 complete ODS reads, nine cell records, three source revisions,
two independent-workbook revisions and three Wiki snapshots. Visual review and
formula recalculation remain `not_checked`; this is a synthetic representation
evaluation, not a general fidelity claim. The preceding run is retained as failed:
its repeated rows contained formulas, so two edits correctly hit the mapping-aware
guard and did not change the source. The success fixture uses repeated literal
rows and a separate formula row; the guard was not relaxed. A still earlier wrapper
import failure (optional defusedxml absent) is also retained; the standalone auditor
now uses the installed XML parser with entities disabled and independent traversal.

Installed wheel/Docker checks use `tests/native_ods_mcp_artifact_smoke.py` against
a source manifest and the independently rendered Calc fixture. They require exact
output bytes, full receipts, historical references and identical restart/Wiki
artifacts. No-op transactions return their complete empty-change receipt inline;
the repository does not append a new history event for unchanged bytes.
