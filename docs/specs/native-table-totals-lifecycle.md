<a id="native-table-totals-row-lifecycle-unreleased-14x"></a>

# Native Table totals-row lifecycle (1.4.1)

Extend `update_workbook_table` with `table_update.totals_row`. Existing column edits
remain compatible; `columns` may be empty only when a totals transition is given.
The exact file revision, worksheet key, active Table part and expected_ref still
identify the source. Capability: `table_totals_lifecycle_enabled`.

## Explicit row intent

- `{action:"add", reuse_definitions:true, cell_styles:"preserve"}` appends one
  totals row immediately below the existing Table. Every target cell must be blank;
  no worksheet row is inserted and existing data membership does not change.
  Hidden totals metadata is reused by default. `reuse_definitions:false` creates
  blank totals definitions; per-column `totals` edits override either default.
- Optional `cell_styles:"last_data_row"` copies direct cell style indices from the
  final data row. Row/column defaults and physical row height are unchanged; this
  is an explicit format choice, not proof of equivalent rendered appearance.
- `{action:"remove", cells:"clear"|"keep_cells", retain_definitions:true}` removes
  the totals role and shrinks only the Table extent. Clear removes contents (also
  rich text) with cell styles retained. Keep preserves values/runs and converts
  retained cells' references to this Table into absolute worksheet ranges from
  before removal. This freezes their Table membership; subsequent Agent review
  must choose whether formulas should track future Table growth.
- Retaining hidden totals definitions allows later add/reuse. Set
  `retain_definitions:false` to discard labels/functions/custom totals metadata.
  Totals edits cannot accompany removal; header/calculated edits can.
- Whole worksheet insertion/deletion remains `update_worksheet_grid`, with its
  explicit format/movement policy and a new revision. Agent can prepare space
  before adding totals or delete the cleared row afterward. No implied movement
  of neighboring tables, drawings, comments or other worksheet data.

## Mechanical checks and preservation

Validate actual current totals state, lower worksheet boundary, adjacent Table/
merge/AutoFilter/special-formula overlap and blank target cells. Preserve data,
headers, column identities, Table styles and filter/sort ranges over unchanged
data. Unsupported mapped/query/extended structures retain existing guards.

Convert retained formulas using parsed operands, not string replacement: preserve
quoted strings and external-workbook references; validate current-row context and
resolve item/column selectors against the old Table. Current-row selectors in totals cells have
no data-row intersection (Excel returns #VALUE!) and require an explicit formula
edit before keeping cells; never silently convert them into valid cell references. Combined
same-Table range endpoints resolve to one rectangle. Ambiguous mixed-range or
disjoint selectors require an explicit formula edit instead of guessed semantics.
Unchanged formulas elsewhere keep their structured references, including #Totals;
removal intentionally changes that selector's available rows.

Invalidate affected pivot caches using the full old/new edited footprint, including
the detached totals row. A surviving named pivot/consolidation source that would
lose its range must block removal. Request formula recalculation, clear stale
formula/chart caches and retain original sources/history. Exact cell/complete XML/
untouched-part readback plus combined 16 MiB public review runs before one CAS.
The receipt records old/new ranges, row intent and exact original before values.
Agent verifies meaning, formula results, filter behavior and rendered formatting.

## Verification

Regressions cover add/remove/reuse, clear/keep rich content, direct cell styles,
calculated data unchanged, formula scope/escaped names/literals/external references,
same-Table ranges/current-row selectors, headerless and last-row boundaries,
neighbor/merge/formula/protection guards, indirect pivots, source revision conflicts
and review-budget rollback. SDK2 and actual Codex scan-to-Table lifecycle must read
complete revisions and preserve historical cell references and exact Wiki files.

Primary sources:

- [Excel structured references and #Totals](https://support.microsoft.com/en-us/excel/using-structured-references-with-excel-tables)
- [Excel ShowTotals](https://learn.microsoft.com/en-us/office/vba/api/excel.listobject.showtotals)

 This is part of
the active cross-format CRUD, fidelity and evidence goal, not its completion.
