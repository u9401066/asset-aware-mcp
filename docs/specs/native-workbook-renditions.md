# Immutable workbook renditions

Release scope: **1.4.1**. Use the installed runtime contract and the limits below.

`create_workbook_rendition` takes `asset_id`, explicit `revision`, and
`workbook_rendition` with a PDF filename, required `mode` (`print` or
`whole_sheet`) and required `calculation` (`recalculate` or `prefer_cache`).
An optional LibreOffice Calc adapter converts an exact private XLSX copy to PDF.
It never saves a new workbook or advances the source history. Historical inputs
are allowed. The output is a new native PDF asset with immutable byte identity.

The creation receipt retains the exact source file reference, requested settings,
renderer/version, page geometry, source sheet inventory and limitations. Read it
completely with `read_rendition`, pinning the PDF creation revision and assembled
UTF-8 JSON hash. Page operations, actual PNG rendering, evidence verification and
Wiki snapshots then use the existing native PDF API without another conversion.
Wiki exports include the complete receipt and exact input XLSX attachment.
Modified PDF revisions do not inherit this creation manifest. No review verdict
or derivation assertion is fabricated; Agents record reviews actually performed.

`print` honors source print ranges and page geometry. Hidden/blank sheets and
out-of-range cells may be omitted. Page-to-sheet mapping is deliberately absent:
page numbers are rendition-local and cannot be guessed from worksheet order.
`whole_sheet` requests SinglePageSheets: it ignores print ranges, paper geometry
and hidden status. One page per source worksheet is required before recording
the ordered sheet mapping. Blank sheets can have tiny pages. Overflowing text,
objects, fonts and very large sheets still need visual review; a complete page
inventory does not certify complete or Excel-equivalent rendering.

Calculation records requested Calc import behavior, not an Excel-result verdict.
Recalculation uses OOXMLRecalcMode=0; prefer_cache uses 1. Volatile, unsupported or
missing-cache formulas may differ. Compare source formulas, rendered values and
the intended calculation in Agent review. Source cached values remain untouched.

Known resource-loading inputs (external linked content other than hyperlinks,
embedded OLE/packages, macro/ActiveX content, connections/query parts, SVG and
resource-loading formula operands) require a separate resource-aware workflow.
Formula guards use parsed tokens, preserving harmless quoted strings, ordinary
hyperlinks and local sheet/table references. Only transitional XLSX worksheets
are initially supported, with 1..100 sheets. Package/PDF byte bounds, PDF page
count, private profiles, macro suppression, process timeout and bounded logs
apply. The converter process is not an OS filesystem/network sandbox.

Validation includes explicit-policy schema rejection, historical source and
history immutability, complete receipt paging, no manifest migration after PDF
edits, formula/resource regressions and injected converter failures. Optional
real Calc/SDK2 tests compare print/whole-sheet pages, blank/hidden sheets, ignored
print areas, cached999 versus recalculated3 and actual colored MCP image pixels.
Actual Codex exercises the same public operations before publication.

References:
- [LibreOffice PDF parameters](https://help.libreoffice.org/latest/en-US/text/shared/guide/pdf_params.html)
- [Calc recalculation options](https://github.com/LibreOffice/core/blob/libreoffice-7-3/sc/inc/calcconfig.hxx)
- [OOXML import calculation policy](https://github.com/LibreOffice/core/blob/libreoffice-7-3/sc/source/filter/oox/workbookfragment.cxx)
