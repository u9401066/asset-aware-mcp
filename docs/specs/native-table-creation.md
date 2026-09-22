<a id="native-excel-table-creation-unreleased-14x"></a>

# Native Excel Table creation (1.4.1)

## User outcome

An Agent can create an independent XLSX using `create`, fill exact typed cells,
and turn an explicit worksheet range into a native editable Excel Table using
`add_workbook_table`. Existing workbooks use the same operation. No PDF import or
A2T projection is required. Original file bytes and historical evidence survive.

## Contract

Discover `workbook_table_creation_enabled` and the operation schema. Supply
`asset_id`, `expected_revision`, and `table_create` with:

- Exact `worksheet: {sheet_id, part}`, canonical A1 `ref`, and workbook-unique
  `name` (case insensitive, also checked against defined names).
- Ordered `columns`, each with a nonempty unique `name`, optional `calculated`
  formula/policy and optional `totals` intent, using existing Table edit types.
- `header_row` (default true), `autofilter` (default true; requires headers),
  `totals_row` (default false). The explicit range includes these rows and at
  least one data row; creating a Table never inserts worksheet rows.
- `header_policy`: `require_matching` preserves exact existing string headers,
  including rich/shared strings; `fill_blank` additionally fills blank headers.
  Neither mode silently renames or coerces an existing value.
- `style`: built-in or existing workbook Table style name (or null), and explicit
  first/last column and row/column stripe flags. Default is TableStyleMedium2
  with row stripes. This adds Table styling; existing cell styles stay intact.

Totals rows must be blank before creation, including columns without totals
intent. This prevents reclassifying the last data row as a total. New calculated
columns use `require_matching` for blank cells, or explicit `replace_all` for
ordinary existing values/formulas. Null/keep_cells is meaningless during creation
and rejected. New formulas use final Table/column names. No formula evaluation
is performed. Data cells outside explicit calculated/totals/header writes retain
their native payloads; leading zeros, rich text, and number formats are preserved.

## Package and evidence invariants

- One private patch and one repository CAS. Validate source/revision, exact sheet,
  unique names/IDs/parts/relationships, Table width/range, and sheet protection.
- Reject overlap with existing Tables, merged cells, worksheet AutoFilter, and
  shared/array/data-table formula ranges. Keep independent unrelated structures.
- Allocate unused Table part/ID and relationship ID, including retained detached
  Table parts. Insert schema-ordered `tableParts`, content type and relationship.
- Preserve all old package parts except explicit worksheet/reference/cache edits.
  New Table XML, package relationships, cell writes and complete planned XML are
  read back. Complete public references plus operation receipt must fit the
  existing 16 MiB limit **before** commit.
- Pivot source header changes retain existing coordinated-identity checks. Mark
  affected pivot caches stale, clear formula/chart caches, request recalculation.
- Read the complete `review_request` result, including generated Table identity,
  request, cell before/after values, and mechanical checks. Use current native
  cell/selection references for derivations and immutable Wiki export. Existing
  references and A2T bindings remain historical; no implicit citation migration.
- MCP checks integrity and supported deterministic repairs. Agent checks actual
  meaning, layout, filter behavior and recalculated results. No Excel fidelity
  verdict follows merely from ZIP/XML/openpyxl readback.

## Verification

Regression coverage: independent creation, existing data/rich headers/styles,
calculated/totals cells, blank-header policy, headerless Tables, Unicode/escaped
names, custom styles, allocation with detached parts, graph/cell/XML readback,
overlap/protection/duplicate-name failures, stale revision, oversized receipt
rollback, subsequent specialized edits, historical references and source bytes.
SDK2 must discover and operate the typed contract. An actual Codex run must read
an image-only PDF, create a workbook and native Table, then independently audit
typed strings, formulas, source identity, historical evidence and Wiki output.

## Primary references

- [XlsxWriter Table options](https://xlsxwriter.readthedocs.io/working_with_tables.html)
- [Excel Table names](https://support.microsoft.com/en-US/Excel/rename-an-excel-table)
- [Open XML Table structure](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/working-with-tables)

This operation adds no dependency. Totals-row lifecycle is supported by its
separate contract; arbitrary row/column identity moves remain outside this operation.
