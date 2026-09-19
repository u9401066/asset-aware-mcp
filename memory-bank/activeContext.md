# Active Context

## 2026-09-19 — structural A2T application and actual Codex audit in development

Previous goal turn was progress: four native-grid commits reached clean main/origin
df1f26ad111b66d6cb7a601c9b82ead3acc436b7. Exact CI35409819540 (10 jobs) and
Pages35409818898 (3 jobs) passed; four public website files matched. Proof:
/tmp/asset-aware-grid-publication-proof.json. Original user worktree is unchanged.
Public remains 1.4.0; all current development stays Unreleased/future 1.4.x.

Core commit156885b adds stable A2T column IDs, fresh IDs for new
rows/columns, rename identity preservation and legacy snapshot representation
compatibility. Missing legacy dates stay unknown and hash-stable. Complete workspace
reads expose a deterministic structural_plan. apply_table_workspace optionally takes
its explicit worksheet_grid, validates the surviving/new identity correspondence,
applies grid and typed value edits in memory, checks complete destination values and
unedited representations/styles, freezes input and commits once with native CAS.
Old bindings, source bytes and evidence do not advance. table_manage accepts typed
JSON defaults for native columns; invalid defaults fail before schema mutation.

SDK2 plus rich-package tests cover formula relocation, rich text/styles, deletion/
recreation, whole-axis deletion, late CAS conflict and tampering. Final full pytest
2642passed33skipped in94.77sec includes the six audit regressions; log
/tmp/asset-aware-a2t-grid-pytest-02.log. Actual
Codex /tmp/asset-aware-codex-a2t-grid-01 passed independent audit:86 calls (84
successful,2 recovered contract input errors),178.67sec,one actual scan PNG. Original
15 and final20 literal cells, identities, complete before/after reads, native receipt,
frozen input, old007 selection/derivation, source PDF bytes/mtime and two Wikis checked.
Runtime SHA1630f0e3781d73f7f4e77a32875ffcb6c2bc33ad17718f15622cce54da243f71 matches.
Errors were attempts to pass table_data/table_manage as native contract.for_op;
documentation now distinguishes exposed MCP tool schemas. Source code has not changed
since this actual run; later edits are tests/docs/harness only.

Local publication gates passed: Ruff507files, mypy230sources, Bandit, lock/dependency/
workflow audits, extension199tests, synchronized harness, VSIX install/update, artifact
audit, fresh wheel/runtime/stdio, Docker import/stdio, zh/en desktop/mobile browser
and metadata/labels. No local VSIX activation (no display/Xvfb). Browser found one
unsupported cross-page anchor link; switched it to the established page link and
verified navigation. Temporary disk pressure was resolved by removing only the
completed task's builder image110026c3fbb5 and old smoke64d7b0f7; current smoke288e73dc
remains available. Completed pytest and wheel temp directories were removed.
Local evidence: /tmp/asset-aware-a2t-grid-local-proof.json.

Remaining this phase: final documentation commit, push and exact CI/Pages/public validation.
Broader native Table membership expansion,
headers/calculated-column edits, surviving-axis reordering and cross-format/real-corpus
goal remain incomplete. Do not equate this bridge milestone with whole-goal completion.

## 2026-09-19 — native grid MCP workflow and actual Codex audit passed

Public versions remain 1.4.0; this work accumulates Unreleased within 1.4.x.
The original detached user worktree is unchanged. Native grid core is committed
as 397a024 (transforms/references), 853460f (native package integration), and
b86a5ae (MCP/application and actual-Codex evaluation). The final documentation group
is being committed before pushing working main; no tag or version bump.

update_worksheet_grid now has typed contract/schema discovery, configured native
adapter, exact revision checks, repository CAS and complete operation readback.
Named pivot/consolidation sources resolve static A1 ranges, table selectors and
scoped defined-name chains before and after changes. Dynamic, cyclic or ambiguous
internal dependencies fail explicitly. Source checks and cache repair do not
certify visual fidelity, semantics or recalculated results; those remain Agent work.
SDK2 discovery now pages schemas when the complete contract would exceed its
transport budget, including capability and policy overhead.

Full pytest: 2623 passed, 33 optional skips in 93.13 seconds; log
/tmp/asset-aware-grid-pytest-04.log. Ruff 498 files, mypy 228 sources and Bandit
passed; extension test:ci passed 199 tests plus 64-file package contents. Lock,
Python/npm vulnerability audits and high-severity workflow audit passed.

Actual Codex /tmp/asset-aware-codex-native-grid-01 completed 126 successful MCP
calls, zero tool errors and one scanned-page PNG. It checked 15 literal cells,
007-to-008 editing, row/column insertion then deletion, old selection/derivation
preservation, source bytes and two revision-specific Wikis. Independent audit
passed after correcting the auditor: exploratory unpinned reads do not count as
proof, while every mutation still requires a complete pinned read. Operation
history must distinguish revisited identical file hashes; regression tests reject
missing current receipts or pre-edit reads even when the bytes repeat. Original
runner log records the earlier auditor failure; audit.json records the corrected
successful audit. Excel rendering/formula evaluation were not exercised here.

Artifact audit, wheel fresh-install/runtime/stdio, Docker import/stdio, VSIX fresh
install/update, zh/en desktop/mobile browser checks and GitHub metadata/labels all
pass. No local activation test: this environment lacks a display/Xvfb; CI owns
that gate. Browser uses cached pinned CDN scripts and private shared libraries.
Wheel source bytes and actual-Codex runtime hash match the current source.
Full local proof: /tmp/asset-aware-grid-local-proof.json. Removed only task-owned
temporary pytest/wheel directories and obsolete local smoke Docker images.

Remaining: publish segmented main commits with exact CI/Pages verification. Structural A2T
correspondence back to the original file, richer object fidelity and the broader
cross-format/real-corpus objective remain open; this grid milestone is not goal
completion. No automatic version bump or tag.

## 2026-09-19 — private native grid package adapter and object geometry verified

Public Python/MCP/VSIX versions remain 1.4.0; future work is Unreleased/1.4.x as
requested. Working main stays 11ddd92; original detached user worktree is unchanged.
No new public native operation, tag, version bump, commit or push in this phase.

Added native table identity/selector/filter/calculated-row integration, sparse
96-DPI row/column metrics, DrawingML move/resize/fixed anchors and top transforms,
VML note locator/anchor/style relocation and exact note/shape deletion. Private
NativeWorkbookGrid now combines sequential transforms, table/reference edits,
merges, views, comments/drawings, watches/outline summaries, pivot result location
movement and derived-cache invalidation. It checks cell payload/style relocation
and reparses complete planned XML plus table identities and untouched member bytes.
Real packages are independently read with openpyxl without resaving their sources.

217 focused grid/workbook tests passed before five new metadata dependency tests;
all five added tests pass too. Ruff 489 files, mypy 226 sources and Bandit pass.
Full pytest passed 2525 tests with 33 optional skips in 87.71 seconds, using
task-owned /dev/shm/asset-aware-grid-pytest-02; log is
/tmp/asset-aware-grid-pytest-02.log. Docs-site check, release-harness audit and
git diff hygiene pass. This is current private adapter evidence, not release or
actual-Codex grid workflow proof. The earlier 2440 passes described the foundations.

Integration fixes: worksheets without resources legitimately lack .rels; cell
canonical comparison must ignore unused inherited namespace declarations while
preserving actual namespaced payload. Fixed-position boxes may require different
marker offsets after row metrics move. In a sequential insertion then deletion,
structured intervals include columns inserted within their earlier endpoints.
Named-table pivot caches and unchanged-text chart references still become stale;
direct source dependencies are handled, external same-name sources stay untouched.

Remaining before public grid exposure: indirect named pivot/consolidation sources
(defined-name chains, named A1 ranges and dynamic formulas) need explicit dependency
handling; review geometry for rotated/grouped objects and richer controls. Reduce
repeated table-bound parsing for large formula inventories. Finish application/
contract/revision-CAS wiring, structural A2T mapping, SDK2 and actual Codex scanned
PDF→native→A2T workflow, then complete release/docs/segmented Git publication gates.
Do not equate passing private adapter tests with the complete user goal.

## 2026-09-19 — native table/grid integration advancing; drawing work next

The preceding turn was progress: 2440 full-suite passes and the uncommitted grid
foundations were revalidated at main base 11ddd92. This continuation adds stable
table column identity changes, escaped/bracketed/bare structured selectors, shrinking
column intervals and explicit deleted-column/table errors; same-name new columns
cannot capture old references. Native table XML, header creation, filter/sort IDs,
calculated-column templates/new row formulas, hidden deleted headers, disabled
deleted totals and whole-table detachment now work in private package integration.
Tests also read the result with openpyxl, without resaving the original package.

Real fixtures revealed XlsxWriter's [[#This Row],Column] stored shorthand and its
literal copying of A1 formulas to every table row. The parser handles the shorthand;
tests separately cover explicit per-row source formulas and literal repeated A1
dependencies. Do not infer a source formula was relative when its stored text is not.
Workbook cache repair now retains valid title properties when sheet names/order do
not change. Shared GridCellWriter prevents repeated whole-sheet scans for fills.

175 focused grid/table/workbook tests and mypy 218 sources pass. The prior 2440 full
suite is evidence for the preceding state only; newer full gates remain pending.
Drawing/notes geometry, package adapter/read-back invariants, native application/API,
A2T structural mapping and actual SDK2/Codex workflow are still incomplete. Continue
the complete feature rather than exposing these helpers alone. No version bump,
tag, commit/push or original-user-worktree changes; public remains 1.4.0/1.4.x.

## 2026-09-19 — native grid internals under development; no public operation yet

Working main remains 11ddd92; the grid phase is uncommitted. Python and extension
versions were rechecked as 1.4.0 in response to the user's 1.4.x constraint. No bump,
tag, source publication or original-user-worktree mutation occurred.

Implemented typed sequential grid edits, strict coordinate/range transforms,
lossless A1 formula edits, original row/cell/column XML relocation and format-only
inheritance, merge anchor preservation, rule-origin rebasing, sparse shared formula
materialization, whole array/data-table block handling, scoped/cross-part formula
ownership, cache invalidation, selection/freeze and zero-based page-break repair.
Shared group followers ignore their own text; nonshared overrides remain intact.
Array result cells without formula nodes have their cached values invalidated too.

The existing workbook formula tokenizer now shadows escaped structured-header
brackets, so header text resembling B2 or Data!A2 cannot be rewritten. Existing
worksheet-deletion dependencies now inspect both structured range endpoints and
retain external qualifier scope. A targeted real-package regression confirms
the second endpoint blocks deletion. The first attempt at an explicitly qualified
integration fixture correctly hit the earlier sheet-reference guard; that redundant
case was removed, retaining the unqualified second-endpoint regression.

127 focused grid/workbook formula/dependency cases pass; mypy 211 sources, Ruff
465 files and Bandit pass. Full pytest passed 2440 tests with 33 optional skips in
87.48 seconds, using its own /dev/shm basetemp; log /tmp/asset-aware-grid-pytest-01.log.
No new full workflow or actual-Codex grid proof is claimed yet. Tables/filter/sort metadata,
structured column deletion/rename, comments/VML/drawing geometry, full package
orchestration and preservation read-back, native contracts/application wiring,
structural A2T mapping, SDK2/actual Codex and all publication gates remain ahead.

Intended orchestration order: expand shared formulas; shift array/data-table blocks;
rebase rule origins and shift rule ranges; plan merges; relocate cells/columns and
restore surviving merge anchors; transform table/view/drawing metadata; rewrite
formulas on surviving nodes; invalidate caches and serialize/read back. Rewriting
after cell deletion avoids blocking or reporting references in removed cells. Do not
substitute these internal helpers or unsupported-case rejection for the complete
requested native workflow. The broader goal remains active.

## 2026-09-19 — native worksheet grid work in progress

Previous goal turn made progress: native/A2T corea1f84cb and docs11ddd92b7debb4c2aa47205f372131dd92d12c90
are clean onmain/origin. Exact CI35400517335(all10jobs) and Pages35400516632(all3jobs)
passed; public JS bytes matched. Revalidated current clean head and both remote runs.
The90-call Codex audit,2356pytest passes and package/SDK2/browser gates remain evidence
for that phase only. Public1.4.0/future1.4.x; original user worktree untouched.

Next real gap is native row/column structure with formula, merge, table, comments,
drawing and format relocation, then structural A2T correspondence. Specification
records intended complete workflow before code. Official openpyxl docs explicitly
exclude formula/table/chart dependency management for insert/delete; retain original
OOXML patches and use tokens only. Microsoft column metric rules and XlsxWriter
object placement explain why drawings must honor move/resize behavior and digit
metrics. No new dependency is justified yet. Implement typed sequential edits,
coordinate/reference transforms, native package orchestration/readback, contracts,
regressions/SDK2/actual Codex and all publication gates. Do not claim completion from
coordinate scaffolding or unsupported-case rejection alone. Full broad goal active.

## 2026-09-19 — native/A2T core committed; documentation ready

Core a1f84cbceace18a0292aa336f9ac4a95da1fb122 contains the guarded native/A2T bridge,
SDK2 and actual-Codex evaluators, regressions, specification and Unreleased notes.
All local gates and the90-call actual audit passed with the one recovered schema
input error documented. Final browser zh/en desktop/mobile checks passed; wheel,
sdist andVSIX audits are complete, runtime bytes match the actual tested source.
Documentation/harness/bundled assets are ready for the second scoped commit. Push
both to main, verify exact CI/Pages and public JS bytes. Public stays1.4.0/future1.4.x;
no tag. The cross-format/structural-grid/CSL/real-corpus goal remains active.

## 2026-09-19 — native/A2T workspaces verified; commit/push pending

Implemented exact native range projection, tagged A2T cells, complete hash-pinned
workspace/source-cell readback, guarded same-grid application and independent XLSX
creation. Stable row IDs and source binding survive persistence. Applied/exported
inputs remain immutable `workspace_reference` assets, re-readable after mutable
table changes/deletion. No-op apply creates no revision/snapshot; native/source
revision guards and rich-text/merge/table-header protections remain active. Native
updates patch original parts; independent creation retains scalar/formula values
without copying layout or relocating formulas. Binding never auto-advances.

Shared table codec stays domain-only; FileTableWorkspaceReader reads fresh bounded
atomic JSON snapshots, avoiding mutable TableService caches. Composition root wires
range/workspace ports; table_data.update_cell now accepts typed JSON (old string-only
MCP signature would reject native objects). Optional services report truthful
capabilities. Original user worktree is untouched; public remains1.4.0, all work
Unreleased/future1.4.x, no version bump or tag.

Actual Codex /tmp/asset-aware-codex-a2t-01:90calls (89successful,1recovered invalid
schema text_limit=20000),145.14sec,1actualscanPNG. Independent audit checks all15literal
cells, exact007→008 typed A2T edit, source refs, complete reads before writes, pinned
snapshots, native histories/parts, independent workbook, sourcePDF bytes/mtime and
two revision-specific Wikis. Original007 assertion never migrates. Audit regressions
reject missing prior reads/snapshot proofs and forged hashes. CLI0.154.0-alpha.6.1
uses its default model; no OCR/general Excel rendering/formula evaluation claim.
Runtime SHA7f345b8116e4e86089e43b726d59f56b7374eade11b372ea43bf2394d4f01674;
lock27749305b83ccda9c265d5ae7f2b02d004ed5500fbc0fbed143d039c7dfc0739.
Wheel source bytes exactly match actual-Codex runtime.

Full pytest2356passed33optional-skips87.82sec; Ruff452files/mypy202sources passed.
Bandit/highzizmor, lock/audit214Python/npmzero, harness/skills/docs, extension199tests,
VSIXcontents/fresh+updateinstall/package, Dockerdoctor/listtools/SDK2 passed. Wheel
console/doctor/listtools/SDK2 passed in executable /dev/shm temporary env after root
space exhausted an earlier attempt. All artifact audit passed (wheel/sdist/VSIX).
An initial fullsuite docs-link failure was corrected; browser then caught an anchor
route not rewritten by the site, now linked via the supported page route. A second
fullsuite was interrupted by disk exhaustion; the final fullsuite above passed.
Only this phase's completed Docker builder4229c39101a5/runtime0c37c1dbd2c3 and own
pytest temp were removed. No global prune or user-source cleanup.

Browser zh/en desktop/mobile content, navigation, overflow and screenshots passed;
private Noto Fontconfig and cachedCDN fixtures used, not a liveCDNavailability test.
GUIactivation unavailable locally; remote CI must cover platforms. README/spec/
CHANGELOG/ROADMAP/wiki/zh+en site/harness and bundled assets updated. GHmetadata/
managedlabels checked synchronized. Next: final review, segmented main commits,
push, exact CI/Pages completion and public JS byte verification.

Broader goal remains active: native grid structural relocation, cross-format CRUD
and fidelity, full CSL semantics and real-corpus coverage still require work. This
phase completes a cell-value correspondence workflow, not universal native/A2T
round trips or the overall user goal.

## 2026-09-19 — native/A2T workbook correspondence in progress

Previous turn is progress: worksheet corec74758a/docs287f9cb4cd91a6360de832016d493b0156510280
are clean onmain; exactCI35396286563(all10jobs)andPages35396285366 passed. ActualCodex
115calls/zeroerrors and publicJS byte verification passed. Public1.4.0, future1.4.x,
no tag; original userworktree unchanged. These remote states were revalidated.

Current gap: A2T has stable rows and PDF/DFM evidence, but no native workbook binding;
ordinary Excel render builds a different layout. Implement explicit native-range
projection into A2T, complete hash-pinned workspace/source-cell readback, independent
native workbook creation from table data, and guarded application to the bound
workbook using original package edits. Preserve scalar types/formula-vs-string,
blank cells/raw baseline/style and full native source references. Do not infer headers
or column types. Applying changed cell data requires exact source revision, unchanged
row/column correspondence and a pinned table snapshot. Structural A2T edits can create
an independent workbook; applying row/column structural edits with formula/merge/style
relocation remains explicit future work, not claimed complete native/A2T round trips.

Need domain/format adapters/application ports, durable bindings through existing
TableService saves/reloads, native contract/discovery, end-to-end SDK2 and actual
Codex scan→XLSX→A2T→managed XLSX checks, docs/harness/site/MEM and all release gates.
Keep goal's full structural editing, CSL and real-corpus requirements open.


## 2026-09-19 — workbook core committed, documentation prepared

Core c74758a contains worksheet operations, contracts, source-preserving repairs,
SDK2/actual-Codex evaluators, regression tests and the Unreleased spec/changelog.
All local gates and actual115-call audit passed as recorded below. Documentation,
English/TraditionalChinese website and bundled assistant instructions now describe
the same capabilities/limits. Commit this reviewed documentation batch and push
both commits to main, then await exact CI/Pages and verify public JS bytes.
Public version1.4.0/future1.4.x; no tag. Broad user goal remains active.


## 2026-09-19 — workbook structure verified locally; main push pending

Implemented native read_workbook/add_worksheets/rename_worksheet/reorder_worksheets/
delete_worksheets with exact revision and sheetId/part keys. Complete structure and
explicit reference JSON is hash-paged; full operation results remain in history.
Original OOXML is patched without openpyxl resaving. Local formulas/names/charts/
validation/conditional formatting/hyperlinks/pivot/consolidation sources are repaired;
external references and string literals stay intact. Scope/view indices are remapped,
3D membership changes require explicit policy, and surviving deletion dependencies
fail. Untouched parts remain byte-identical; deleted sheet/chain parts are detached,
not securely erased. Signed/protected/VBA/ActiveX/revision/unknown workbook structures
fail explicitly. Agent owns dynamic-reference, formula-result and rendering review.

Actual Codex /tmp/asset-aware-codex-workbook-01: 115 MCP calls, zero errors,160.49sec,
one actual scanned PNG. Seven revisions cover all15 literal values, original007
selection/current008, added Review/Temporary, native cross-sheet formula, Chinese/
apostrophe rename, reorder and deletion, historical evidence and two Wiki snapshots.
Independent audit verifies native files, stable keys, explicit formula, unchangedparts,
sourcebytes/mtime, complete before/after reads and no migrated assertion. CLI0.154.0-
alpha.6.1 defaultmodel not pinned. Evaluator regressions reject read-after-edit,
forged revision transitions and hashes. Saved actual trace replay passed after these
additional audit checks. No OCR, formula evaluation or Excel rendering guarantee.

Full pytest2322passed33optional-skips85.53sec; subsequent15focused tests passed,
including three additions (two audit cases and consolidated-range reference).
Ruff438files/mypy196sources, bandit/highzizmor, lock/audit214Python/npmzero, skills/
harness/docs checks passed. Extension199tests, package-content guard, fresh/update
VSIX installs/package, Dockerdoctor/listtools/SDK2, cleanwheelconsole/SDK2 and all
artifactaudit passed. GUIactivation unavailable locally, CI must cover platforms.
Builtwheel source bytes and runtime/lock hashes match the actual Codex environment.

Runtime b46fad8ec0a37b1eed3bd29e52094ab80a225b6f98e82c191286fd5e49073f49;
lock27749305b83ccda9c265d5ae7f2b02d004ed5500fbc0fbed143d039c7dfc0739.
Docker temporarily consumed free disk; removed only own completed builder4d3f3df57dbe
and runtimeceb21b907aa9. Completed pytest and pip caches in exact task-owned /dev/shm
paths were removed; retained Codex trace/evidence and original sources.

READMEs/CHANGELOG/ROADMAP/spec/wiki/zh+en site and bundled harness updated. Browser
zh/en desktop/mobile passed with viewed screenshots and no console errors/overflow.
Default local monospace lacked Chinese glyphs; rerun using existing private Noto
Fontconfig fixture rendered the unchanged Chinese code example correctly. No global
font changes. CachedCDN scripts do not establish liveCDNavailability. GHmetadata/
managedlabels synchronized. Sourceworktree untouched; main was up to date at9aa31c1.
Public1.4.0, allnewworkUnreleased/future1.4.x; noautobump/tag. Nextsegmentedcommits,
mainpush/exactCI/Pages/publicbyteverification. Broadergoal remains active: crossformat
CRUD/fidelity, native/A2T correspondence, fullCSL and real-corpus cases remain open.


## 2026-09-19 — native workbook sheet CRUD in progress

Previous goal turn is progress: native selections committed as38c4b65/docs11cd537,
final audit correction9aa31c1058127f9bd840b4607db6522932e6f219. Revalidated clean main
and exact CI35391575079 success; all10jobs and Pages35391573842 passed. Public1.4.0,
no new tag, next1.4.x. Actual Codex58calls/zeroerrors and independent selection/wiki
proof passed. Original user worktree remains untouched. The superseded CI35391254625
was explicitly cancelled after the audit correction queued, not an unresolved failure.

Next scope is real native workbook sheet structure, currently absent: read/add/
rename/reorder/delete with stable sheetId/part keys and managed revisions. Preserve
original packages; update explicit formula/name/chart references and index metadata,
check deletion dependencies and 3D membership, retain untouched parts and historical
cell/selection evidence. Use openpyxl tokenizer for lossless spans only, never resave
the original workbook with it. Official docs confirm limited parsing, whitespace
normalization and no full formula evaluation; experiments show spill '#' needs a
length-preserving lexical adaptation. Dynamic strings/external references stay intact
and Agent reviews results. Exact spec recorded before implementation.

Sources: Microsoft SpreadsheetML structure/worksheet relationships and openpyxl
formula-tokenizer documentation; installed/upstream openpyxl3.1.5 is currently a dev
only dependency. Promote tokenizer use deliberately with fresh lock/audit/package
checks. Need domain/contracts, infrastructure reference/structure checks, API wiring,
meaningful regression/SDK2/actual Codex tests, docs/harness/site/MEM, segmented main
commits/push and exact CI. Broad goal remains active; all workUnreleased/future1.4.x.

## 2026-09-19 — selection audit enforces source-read ordering

Core38c4b65/docs11cd537 pushed; Pages35391253676 passed and public JS bytes match.
CI35391254625 has successful docs/static/npm/Linux/macOS/Python3.10 jobs while
Windows/Python tests are still running. Final review found the independent Codex
selection auditor initially pre-populated source availability from all complete
reads, which could accept a source read occurring after an assertion. Track source
availability in actual call order and require the exact original PDF revision/page0.
Add a regression rejecting read-after-assertion and accepting read-before-assertion.
Six evaluator tests and the saved58-call Codex audit pass. Runtime/lock/public-site
hashes and all prior packaging/SDK2 gates remain unchanged. Push this test-only
correction, then verify the superseding exact CI/Pages head. Public1.4.0/future1.4.x.

## 2026-09-19 — native selections verified locally; push pending

Implemented immutable native-selection-ref-v1 for exact RFC6901 JSON values or
Unicode spans within verified native XLSX cells, DOCX blocks, PPTX shapes and PDF
pages. Empty selector reads the complete parsed parent without added evidence.
Full parent identity/selector/value/context are hashed; UTF-8 spans refer to parsed
strings, not original file offsets. Readback is bounded complete canonical JSON.
Existing verify/derivation history and Wiki exports accept selections, retain full
sidecar records and exact sources, and never migrate assertions to new revisions.
Opaque/nested parents, wrong pointers/types/ranges and forged bindings fail.

Actual Codex `/tmp/asset-aware-codex-selection-01`: 58 MCP calls, zero errors,
130.45 seconds, one actual scanned PNG. Independent audit verifies all 15 literal
XLSX cells, full parent/selection/ledger reads, hashes, PNG pixels, source bytes/mtime,
historical 007 after B2 becomes 008, published workbook and two revision-specific
wikis. Old Wiki retains selected-record JSON and the exact PDF; new Wiki has no
inherited assertion. CLI0.154.0-alpha.6.1 default model not pinned. Rehashed fake
values/context/locators fail evaluator regressions. SDK2 also checks precise text
inside a merged-title PPTX table across an edit. No general OCR/Excel fidelity,
pixel-region evidence or native DOCX cell geometry claim.

Full suite: 2,262 passed,33 optional skips in82.29seconds after updating the DOCX
contract's expected operation list. Subsequent focused41passed4.82sec includes an
additional real DOCX Unicode/combining-character span/source-preservation case;
actual saved Codex audit replay passed after auditor module split. Ruff421files,
mypy188sources, bandit/highzizmor, lock,214Python/npmzero audits, harness/skills/docs
passed. Extension199tests/64contentguard, fresh/updateVSIXinstall, cleanwheel console
and SDK2, Dockerdoctor/listtools/SDK2, allartifactaudit passed. Local GUI activation
unavailable; CI must cover it. Browserzh/en desktop/mobile passed and screenshots
viewed; cached CDN fixtures do not establish live CDN availability. GitHub metadata
and managed labels already synchronized. README/wiki/site/harness copies updated.

Evaluated runtime394f33ef4dee30f16df5b7760a8d440d500f53ca413e4c992a6a4eff3a5922e3;
lockabfaddf3d7d964ace1e210b1fd584e1717775a70f8ccdc98ad9b669b61f1bcd3.
Docker build briefly exhausted local disk; removed only this run's builder1880636e5922
and runtimeb5b101b6e090 after checks. Kept source/evaluation evidence and all unrelated
images. Removed only exact completed test-owned /dev/shm/asset-aware-selection-pytest.
Public version remains1.4.0, all new workUnreleased/future1.4.x, no tag. Original
user worktree untouched. Next: segmented main commits/push and exact CI/Pages/public
byte verification. Broader nativeCRUD/fidelity, A2T/native correspondence, fullCSL,
real-corpus validation and general document structures remain active goal work.

## 2026-09-19 — revision-bound selection evidence in progress

Previous goal turn is **progress**: CJK correction committed/pushed as70645dc
(core53024f5/docs2b3fba9), exact CI35387856340 all10jobs and Pages35387855694 passed.
Revalidated clean main and exact successful CI this turn. Codex49calls/zeroerrors,
CJK pixels/native evidence passed; public1.4.0, future1.4.x, no new tag.

Next: native selection references identify exact JSON subtrees or Unicode character
ranges inside verified immutable XLSX cells, DOCX blocks, PPTX shapes or PDF pages.
RFC6901 pointer + optional half-open character range; parent/reference/selector/value
are bound by the selection hash, so equal values at different locators cannot swap.
read_selection also exposes complete paged parent records (empty pointer), closing
DOCX full-representation discovery through MCP. Reject opaque/no-parser and nested
selection parents. Preserve UTF-8 spans/context for text; ranges address parsed
text, never raw DOCX/PDF bytes. No guessed OCR, scan region or semantic alignment.

Extend existing verify/derivation endpoints and wiki snapshots, attaching complete
selection records alongside native originals. Old refs/ledgers retain identities;
new revisions never remap assertions. Agent can record a source-to-specific-value
claim and review; machine integrity remains separate from semantic support.
References: RFC6901 and W3C Web Annotation selectors (conceptual guidance; do not
claim JSON-LD annotation compliance). Need cross-format, Unicode/locator/tamper/
history/ledger/wiki regression coverage, actual SDK2 and real Codex evidence use,
then docs/harness/assets, release checks, segmented main commits/push and exact CI.


## 2026-09-19 — portable font manifest paths

CJK changes pushed as2b3fba9 (core53024f5); initial exact CI35387712309 and
Pages35387711381 started. Final portability review found font manifest inventories
used str(relative_path), which yields backslashes on Windows while the protocol
uses slash-delimited names. Use as_posix for both fixture generation/inventory and
synthetic test fixtures. Existing cross-platform font tests cover the correction;
production runtime and saved Linux Codex/font hashes remain unchanged. Push this
test-harness correction and verify the superseding exact HEAD CI/Pages.


## 2026-09-19 — CJK font correction verified locally; push pending

Controlled Linux Fontconfig fixture now retains pinned Noto Sans TC Regular/Bold
and license at upstream523d033d6cb47f4a80c58a35753646f5c3608a78, copies/hashes local
Liberation Sans and license, and leaves global fonts/DOCX bytes unchanged. Explicit
--font-fixture forwards FONTCONFIG_FILE to actual Codex MCP; independent audit
restores that same recorded environment and rejects changed files/configuration.
Fontconfig2.13 .uuid cache files are validated/permitted; no font-content exception.
A first audit check assumed PDF paint order matched text order; Writer paints a
Latin space before the CJK run. Scoped CJK checks now require the two actual Chinese
codepoints in their run plus distinct Noto glyphs, with whole-image pixel equality;
complete native readback still checks the full heading. Added negative regressions.

`/tmp/asset-aware-codex-docx-cjk-01`: **49 calls, zero errors**,139.22 seconds,
actual one scan PNG and two Writer PNGs, five complete DFM revisions. Codex found
readable Chinese heading in both final/historical previews; table values, merged
grid and 007/008 changes remained correct. Independent complete RGB pixels, CJK
font/codepoints, source/history/publication/wiki checks passed. Agent did not claim
font-family identification or Microsoft Word fidelity; native run still says Arial.
SDK2 same-source regression renders identical bytes with Latin-only/with-CJK fixture,
rejects missing CJK evidence and checks unchanged source bytes/mtime after both.
Saved same-source before/after files: `/tmp/asset-aware-docx-font-review` and
`/tmp/asset-aware-docx-font-review-fixed`; private fonts `/tmp/asset-aware-docx-cjk-fonts`.

Full suite **2,221 passed,33skipped in78.27seconds**; focused37passed7.57seconds
including actual SDK2. Ruff411files/mypy186sources, high zizmor, lock/dependency
(214Python/npmzero), harness/skills/docs and GitHub metadata/labels checks passed.
Extension199tests/64filecontentsguard passed. zh/en desktop/mobile browser screenshots
passed; changed new prose Chinese literals out of code styling so readers see glyphs.
Source/dependency runtime hash remains7a4ba4128eb6e237f9dde0f47630af3f8370d0abc6ce816f40f5a85533f44df5,
matching both actual Codex runs and prior Docker/clean-wheel/VSIX-install gates.
No runtime/package/version changes. CI now prepares pinned fonts explicitly and runs
real before/after test; ordinary pytest never downloads/fonts or starts Codex.
Next: segmented commits/main push, exact CI/Pages/public-byte verification. Public
1.4.0 and future1.4.x; no new tag. Broader cross-format/evidence goal remains active.


## 2026-09-19 — CJK rendering correction in progress

Previous goal turn is **progress**: DOCX whole-page renderer committed/pushed as
main d12d6670a1a00ee32131dc275472b11104c2c214 (coree2e3847), exact CI35385711787
all10 jobs and Pages35385711608 passed. Revalidated clean main and CI this turn.
Public remains1.4.0, no new tag; future1.4.x. Original worktree remains untouched.

Actual Codex detected missing Chinese glyphs in the prior Writer preview. fc-list
:lang=zh returns empty; Arial resolves to LiberationSans. Independent conversion
of the exact saved DOCX reproduces boxes. PyMuPDF texttrace misleadingly maps both
boxes to U+7814 with nonzero glyph1, so nonzero glyph IDs/readback alone cannot
prove glyph fidelity. Keep semantic/visual judgment with the Agent.

Next: optional private Linux Fontconfig fixture with hash-pinned Noto Sans TC
Regular/Bold from notofonts/noto-cjk Sans2.004 commit523d033d6cb47f4a80c58a35753646f5c3608a78,
copy and hash local Liberation Sans, preserve licenses, and avoid global font/source
changes. Forward explicit fixture only to evaluated MCP process and independent
replay, retain exact environment hashes. Test same-source before/after images,
repeat actual Codex visual review, and document remaining Word/real-corpus limits.
Primary references: official Noto Sans README, Fontconfig user manual, PyMuPDF
get_texttrace/Font.has_glyph docs. No runtime font guessing or automatic font installs.


## 2026-09-19 — DOCX page preview local gates complete; push pending

Core committed as **e2e3847b46f247d28176be6b72b07c86e770fa35** by
u9401066 <u9401066@gap.kmu.edu.tw>. Final full suite **2,210 passed, 32 skipped
in 78.04 seconds** (`/tmp/asset-aware-docx-render-final-full.log`). Real Writer and
Impress SDK2 tests passed separately. Docker runtime **3aef184d8a99** passed doctor,
list-tools and SDK2 stdio; removed only that smoke image and its builder
**57cdb0fe291b** after terminal success, recovering ~350 MiB. Clean-wheel and VSIX
checks passed; package audit identifies1.4.0 consistently. Extension199 tests,
64-file contents guard and66-file VSIX. All other gates and actual47-call Codex
pixel audit recorded below. No runtime changes after model run.

README/zh, Unreleased changelog/roadmap, Wiki/spec, bilingual website and assistant
harness bundles now describe actual DOCX page preview scope and local Chinese-font
limitation. Original worktree remains at6ad9a5c with its preexisting edits unchanged.
Latest public release remainsv1.4.0. Next: commit docs/assets, push main, await exact
HEAD CI/Pages and check public bytes. Broader goal remains active; no new tag.


## 2026-09-19 — DOCX page previews implemented; final gates in progress

Public stays **1.4.0**; user reaffirmed the **1.4.x** line. No tag or package-version
change. New render_docx_page converts exact immutable DOCX bytes through optional
Writer, returns actual MCP PNG plus rendition-local pagination/geometry/hashes,
and retains source bytes. Shared Office process/profile guards now cover Writer.
Known resource-loading fields/relationships, OLE/chunks, SVG and VML links reject.
MCP mechanical checks remain separate from Agent semantic/visual judgments.

Actual Codex `/tmp/asset-aware-codex-docx-render-01`: CLI 0, 157.96 seconds,
**47 MCP calls, zero errors**, one scan PNG, two Writer PNGs at final/historical
revisions, five complete DFM revision reads. Independent exact RGB replay, 007/008,
rich table/native structures, source/published/wiki checks passed. Renderer 7.3.7.2;
Codex detected missing Chinese heading glyphs (boxes) on this machine. Native text
is correct; font availability and Microsoft Word fidelity remain unverified.
Runtime SHA256 `7a4ba4128eb6e237f9dde0f47630af3f8370d0abc6ce816f40f5a85533f44df5`;
lock `abfaddf3d7d964ace1e210b1fd584e1717775a70f8ccdc98ad9b669b61f1bcd3`.
CLI 0.154.0-alpha.6.1; model uses CLI default. Production fingerprint still matches.

49 focused renderer/auditor tests passed; actual Writer multi-page SDK2 test passed
(8.17 seconds with earlier 28 unit tests), plus real Impress SDK2 regression passed.
First full suite: 2,209 passed, 32 skipped, one docs-link convention failure. Fixed
that Wiki link and all 25 docs tests passed; final full suite is running. Ruff (408
files), mypy (186 sources), medium/high Bandit, high zizmor, lock/dependency audits
(214 Python packages; npm zero vulnerabilities), harness/skills/assets/artifact
audits passed. Extension 199 tests passed, 64-file contents guard; fresh/update
VSIX and clean-wheel CLI/SDK2 passed. Local GUI activation unavailable; remote CI
checks it. Desktop/mobile zh/en browser checks and screenshots passed with cached
CDN JS, not a live CDN reachability claim. GH metadata and managed labels match.

Docker 3aef184d8a99 built; CLI/SDK2 smoke pending, then remove only this turn's
smoke images to recover disk. Older native PDF scanned run 01 is now preserved at
`/tmp/asset-aware-codex-native-pdf-scanned-01.tar.gz`: all member file hashes verified
before removing its unpacked directory. Current audit evidence remains unpacked.
Original user worktree untouched. Next: complete gates, segmented main commits,
push and wait for exact HEAD CI/Pages; broader goal stays active.


## 2026-09-19 — native DOCX page rendering in progress

Previous goal turn is **progress**: native DOCX creation/body CRUD committed and
pushed; authoritative HEAD50fdc05544d9cca97503845235742aab5928c430 is clean/main,
CI35381844909 all10 jobs passed and Pages35381844084 succeeded. Revalidated CI
at this turn start. Includes Windows UTF-8 evaluator/child-stdin fixes and47focused
regressions; native runtime fingerprint unchanged after the actual45-call Codex run.
Public remains1.4.0, new work Unreleased for1.4.x; originalworktree untouched.

Next: render_docx_page at explicit revision/index using original DOCX bytes and
optional LibreOffice Writer, full-document pagination and actual MCP PNGs. Separate
renderer port; use existing private process/timeout/output infrastructure and PDF
workers. Report renderer/page count/dimensions/hashes and no Word-fidelity verdict.
Spec added before implementation. Primary references reviewed:
https://help.libreoffice.org/latest/en-US/text/shared/guide/pdf_params.html
https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html

Need focused/resource/SDK2 tests and actual Codex visual review; then README/site/
harness/MEM and complete release gates before main push. Broader cross-format CRUD,
source-to-cell mapping, general Word objects/styles and full academic CSL remain
in the active goal. Disk only286MiB free at start; use dedicated shm for full tests,
and inspect task-owned build artifacts before Docker gates, never broad prune.


## 2026-09-19 — Windows audit locale fix; remote checks rerun required

`5e3f89b` (core235b89b) was pushed; CI35380567397 passed all substantive jobs except
Windows. Windows699-case native suite: one audit test failed,698passed3skipped;
`records.jsonl` was decoded with the locale default, changing Chinese representation
text and producing a false hash mismatch. DOCX runtime/artifact bytes were correct.
The new Codex DOCX runner/auditor now explicitly reads/writes UTF-8. Regression
parameterization simulates cp1252 defaults on Linux; **12 focused audit tests pass**,
including extra PDF snapshot and corruption rejection. Saved actual Codex trace
re-audited successfully (45calls,0errors,5revisions). Runtime fingerprint unchanged.
No repeat model run or runtime install is needed for this tests-only correction.

Pages35380566066 already succeeded for5e3f89b; served site.js SHA256
`d14ecc7a330d9e364015e4878b0f1bdc62873c17171637a608e1e3376fb0f6b7` and
site-content.js `fd91583ad3e97713a9dbb3e03c60620290c2865ca7b1f6bfa7ede96857d80576`
matched localbytes. Public remainsv1.4.0, onlymain, originalworktreeuntouched.
Next: push the test-only locale fix, await exact newHEAD CI/Pages, preserve active goal.



The locale regression uses a public Popen wrapper instead of the newer private
_text_encoding helper, which is absent on Python3.10. A system Python3.10 child
process independently reproduced the omitted-encoding failure and verified UTF-8
roundtrip; all47 focused tests still pass on Python3.13.

The same locale review found the shared Codex runner passed Unicode prompt stdin
through the platform-default subprocess encoding. It now explicitly uses UTF-8;
a real child-process echo regression forces cp1252 defaults and checks exact UTF-8
bytes. **47 focused DOCX-auditor/PDF-evaluation tests passed**, including13 DOCX
audit cases. This changes evaluation tooling only, not the native runtime or actual
saved evaluation results. Exact remote CI will run on the final correction commit.

## 2026-09-19 — native DOCX structure local gates passed; exact remote proof next

Core committed as `235b89b` (26 counted files +2 MEM) with author u9401066.
Final full suite **2156 passed,31 optional skipped**,76.97s, retained log
`/tmp/asset-aware-docx-structure-final-full.log`. Extension199 passed;64-file
package guard; fresh/update VSIX install passed (baseline0.2.10 absent, local
GUI activation unavailable). VSIX rebuilt66files; wheel/sdist/VSIX auditallpass.
Clean-wheel install/help/doctor/list-tools/SDK2stdio passed. Docker image
`b8303c0aa802` and builder `3f5e1eb577b1` passed CLI/stdio; only these task-owned
images removed after proof to recover350MiB. Dedicated full-pytest shm cleaned
after terminal success. Runtime fingerprint still matches actual Codex run.
Public remains1.4.0. Next: documentation/assets checkpoint, push main, exactHEAD
CI/Pages and publicsitehash proof. Goal stays active for outstanding scope.

### Implementation and evaluation detail

Public stays **1.4.0**, all work Unreleased for **1.4.x**, no new tag/bump.
Authoritative worktree: `/home/eric/workspace251226/asset-aware-mcp-agent-assets`;
original detached user worktree remains untouched. MCP mechanical checks versus
Agent semantic/visual/formula review division remains explicit.

- Added typed independent create_docx and current-reference add/delete body blocks;
  rich runs, half-point/complex-script formatting, explicit twip grids, merges,
  shading, headers, paragraph flow and page settings. Existing DOCX mutations patch
  only word/document.xml; independent readback, unchanged XML/other bytes, source/CAS,
  field/range/section/embedded dependencies guard publication.
- New domain port/model and infrastructure builder/check modules; wired native
  operations/contract/dependencies. Added unit guards/operations, SDK2 stdio test,
  actual Codex runner/auditor plus negative auditor tests and CI matrix registration.
- Full Python runtime suite: **2147 passed, 31 optional skipped**, 76.03s,
  `/tmp/asset-aware-docx-structure-full.log`; nine subsequently added auditor tests
  separately passed. Ruff and mypy 184 files pass. Bandit medium/high and zizmor gates
  pass; default all-severity Bandit reports 84 existing/low findings (no medium/high).
  Python audit214 packages and npm0 vulnerabilities; GitHub metadata/labels in sync.
- Actual Codex `/tmp/asset-aware-codex-docx-structure-01`: CLI0,139.99s,45nativecalls,
  zero errors, one actual scan PNG independently pixel-checked, five full DFM
  revisions, exact table strings/leading zeros/fonts/grid/merge and old proofs.
  Published DOCX and all17 wiki parts match. Audit initially rejected supplementary
  file proof/source-PDF wiki; corrected auditor and re-audited saved trace, passed.
  No rerun model needed; no native runtime changed after this run.
  Runtime SHA256 `7f77a7a215f6f34241ea1db67d458e4963782da1c86fa74cdacb221cd4870308`;
  lock `abfaddf3d7d964ace1e210b1fd584e1717775a70f8ccdc98ad9b669b61f1bcd3`.
  Codex0.154.0-alpha.6.1, default model not pinned. Synthetic first page only;
  no DOCX rendered page/flow review or general real-corpus claim.
- README/zh, CHANGELOG, ROADMAP, spec, wiki/site and bundled assistant assets updated.
  Browser zh/en desktop/mobile checks/screenshots pass with Playwright fallback;
  CDN scripts locally replayed, not a live CDN reachability check.
- Remaining this checkpoint: Docker/VSIX/wheel install gates, final docs/assets
  freshness, segmented main commits/push, exact CI/Pages/public-byte verification.
  Larger goal remains active: native DOCX rendering/general objects/styles, other
  format CRUD, cross-deck/notes, cell derivation maps, academic CSL and real corpus.


## 2026-09-19 — native DOCX creation and body structure in progress

Previous goal turn classified progress: bc23768/260def7 pushed; exact CI35376045368
(all ten jobs, including actual Impress/SDK2 render) and Pages35376043498 revalidated
successful at260def7. Public bytes matched, main clean/onlymain, publicversion1.4.0.
Original user worktree remains untouched. New scope: independent native DOCX
creation with typed rich paragraphs/tables, and revision/reference-bound body block
insertion/deletion preserving untouched package bytes. Existing DFM edits, references,
wiki and explicit source writeback remain in use. Primary python-docx document/text/
table/merge documentation reviewed. Full cross-format goal remains active.

## 2026-09-19 — native whole-slide preview in progress

Previous goal turn classified progress: 3fb6b88/208022a committed and pushed;
CI 35372694026 (ten jobs) and Pages 35372691520 passed at exact 208022a.
Public version remains 1.4.0; all new work is Unreleased for the 1.4.x line.
Original user worktree and its preexisting changes remain untouched.

This turn adds an optional rendering port and revision-pinned render_pptx_slide.
Actual environment probe found LibreOffice 7.3.7 Writer without Impress: conversion
returned exit zero without output. Downloaded matching Ubuntu Impress/Draw .debs
into /tmp/asset-aware-render-lo and built a private overlay for testing; no system
installation or user profile modified. Three-slide hidden-middle probe then passed.
Production adapter checks actual output, PDF count, raw source slide keys, timeout
cleanup, bounded images and explicit renderer identity; no PowerPoint fidelity verdict.
76 focused unit/schema tests and real SDK2 image delivery passed. Initial SDK2 test
attempts exposed test harness constructor/image-unwrapping mistakes; corrected final
run passed in 7.96s, /tmp/asset-aware-render-stdio-final.log; failed logs retained.
Source/MEM/docs/actual Codex and remaining release gates are in progress.
Broader goal remains active: other formats, cross-deck import, notes, A2T bridges,
real corpus, cell derivation mappings and standards-aware academic citations.

Actual Codex --render run 01 passed: 78 calls, zero MCP errors, exact first
transcription, five complete native records, one scanned-page PNG and two static
slide PNGs at two revisions. Independent LibreOffice/PyMuPDF replay matched all
RGB pixels. Codex correctly observed the historical 008 edit hidden behind the
second table (visible 007), plus style differences from the scan. Screenshots viewed.
Logs/artifacts: /tmp/asset-aware-codex-pptx-render-01, /tmp/asset-aware-render-codex-01.log.
Runtime source SHA256 74a47ca86ac08bef237847c41c2d8b53a78a9196a4440105172f60330433371a;
lock abfaddf3d7d964ace1e210b1fd584e1717775a70f8ccdc98ad9b669b61f1bcd3.
Full suite 2,095 passed/30 optional skipped (79.31s); task-owned RAM fixtures removed
only after terminal success, log /tmp/asset-aware-render-full.log retained.
Ruff/386-file format/mypy180/Bandit/docs/harness/skills/CI workflow audits passed.
199 VSIX tests/64-file guard and fresh/update installation passed; GUI activation
unavailable locally and remains CI-enforced. Initial follow-on packaging exited228
with an empty log; retry in progress after removing completed task Docker images.
Docker f0f98eb1d6e3 import/native wiring passed; initial --doctor CLI spelling failed,
correct doctor/list-tools and SDK2 stdio retry passed. Removed only that runtime and
its builder ffd85ac7e75a after terminal success to reclaim 350MiB before wheel smoke.
Python214/npm locks report no known vulnerabilities; GitHub metadata/labels match.
Browser plugin unavailable: Playwright1.63.0 fallback verifies zh/en desktop/mobile,
no overflow or console errors; screenshots /tmp/native-render-* viewed. Cached CDN
scripts mean CDN reachability is not covered. Clean-wheel/package/CI/Pages pending.

Final local package retry passed: 66 VSIX entries, all-artifact audit passed.
Clean-venv built-wheel help/doctor/list-tools/SDK2 stdio passed; task-owned RAM pip
cache removed after terminal proof. Local gate logs retained. No source change after
actual Codex/full suite; source fingerprint rechecked. Pending scoped main commits,
push and exact CI/Pages/public-byte verification. No version bump or release tag.

Core committed as bc23768. Companion commit contains actual Codex rendering audits,
corruption regressions, required Impress integration CI, bilingual website/docs and
synchronized assistant assets. Final push/CI/Pages verification follows.

## 2026-09-19 — native slide structure in progress

Previous goal turn classified progress: 796656c/68153e3 pushed; exact CI 35369646303
(ten jobs) and Pages 35369645315 revalidated successful at 68153e3. Public bytes
matched, main clean, only main branch. Public stays 1.4.0 / Unreleased for 1.4.x.
Original user worktree remains untouched. Next scope: revision-pinned native slide
layout discovery, insertion with inherited layouts/placeholders, ordering and deletion
with dependency guards, exact untouched package bytes and independent readback.
Primary python-pptx slide and Microsoft slide deletion docs reviewed. Broader goal
remains active: copying/import, notes structure, other formats, A2T, real corpus,
cell derivations and standard academic citations still require work.

Implemented four native slide operations, destination-master layout discovery,
empty placeholder generation, ID/part-preserving insertion/order/deletion,
dependency checks and count-property repairs. 38 focused structure/guard tests,
89 SDK2/discovery/guard tests passed. Independent auditor's first reorder test
failed because python-pptx renames parts in memory; changed auditor to original ZIP
relationships, then all nine corruption/order regressions pass. No production issue.
Full suite: 2,068 passed / 30 optional skipped (68.34s), log
/tmp/asset-aware-slides-full.log. Removed only completed task-owned RAM fixtures
/dev/shm/asset-aware-slides-pytest after terminal proof. Source fingerprint
1ef64237a6b976ebb60f20fed506e61c7d8f2fb39226d96d75c071d98c067f44;
actual Codex --slides run 01 in progress at /tmp/asset-aware-codex-pptx-slides-01.
Ruff/format/mypy 177 source files and Bandit passed. Public 1.4.0/Unreleased unchanged.

Actual Codex slides run 01 passed: 96 calls, zero MCP errors, exact first transcription,
1 PNG/8 complete records, three intermediate presentation revisions independently
audited; historical deleted-shape evidence and published-file/wiki checks pass. No
full presentation rendering claim. 199 VSIX tests/64-file guard, fresh/update installs
pass; local activation unavailable, CI requires it. Final VSIX 66 entries and all
artifact audit pass. Docker ec829d25a895 passed native slide wiring, doctor/list-tools
and SDK2 stdio. Removed only completed task runtime/builder images ec829d25a895 /
198218c65132 before clean-wheel smoke to avoid disk exhaustion; build log retained.
Browser Playwright 1.63.0 fallback (no Browser tool available), zh/en desktop/mobile
passes with no console errors/overflow. Screenshots /tmp/native-slides-{desktop,mobile}
-{zh,en}.png viewed. GitHub metadata/labels synchronized; Python 214 packages/npm
lock zero known vulnerabilities. Clean-wheel smoke passed (help/doctor/list-tools/SDK2 stdio); dedicated RAM pip cache
removed after terminal proof. Runtime source/lock hashes still match the actual Codex
run. Local gates complete, pending scoped commits/push and exact CI/Pages. Public 1.4.0.

Core committed as 3fb6b88. Companion commit contains independent Codex slide audits,
corruption regressions, platform/SDK2 CI registration, bilingual website/docs and
synchronized assistant assets. No source change after full suite/actual Codex run.
Remaining checkpoint work: push both commits and verify exact CI/Pages/public bytes.

## 2026-09-19 — native table merge/split in progress

Previous goal turn made verified progress: a9739eb/6cb054b pushed. Exact CI
35366326974 (ten jobs) and Pages 35366597637 revalidated successful at 6cb054b;
public bytes matched. Automatic Pages initially redeployed cea4870; explicit
rebuild corrected that and was independently verified. Main clean at start,
public still 1.4.0/Unreleased for 1.4.x; original worktree remains untouched.
Next scope: explicit-content-policy merge and split in existing native grid edits.
Preserve paragraph XML/format/relationships, reject partial merge intersections,
and avoid automatic content redistribution. Specification written first; primary
python-pptx merge/split docs checked. Full cross-format goal remains active.

Implemented explicit merge/split policies, rich paragraph migration and partial-overlap
rejection with atomic managed revisions. Full pytest passed 2,015 / 30 optional skips
(65.42s), /tmp/asset-aware-merge-full.log. One additional absent-anchor-body regression
plus positive/auditor tests passed afterward (18 focused); production source unchanged.
Completed task-owned /dev/shm/asset-aware-merge-pytest removed after terminal proof,
all logs retained. Actual Codex --grid --merges run 01 started at
/tmp/asset-aware-codex-pptx-merge-01; result pending. Public remains 1.4.0/Unreleased.


Actual merge run 01 passed: 180 calls, zero MCP errors, exact first transcription,
1 PNG/13 complete records, five grid and six merge revisions independently audited.
Source SHA256 cc9a0391f7c275b6627481c0e7ea3792de87b6e4a7fc5f86c443a8e0df51f358;
lock unchanged. No full slide render claim. 199 VSIX tests/64-file contents guard,
fresh/update installation pass; activation unavailable locally, enforced in CI.
Ruff/format/mypy 172 source files/Bandit/docs/harness pass. Python 214 packages/npm
lock zero known vulnerabilities; GitHub metadata/labels match. Browser fallback
Playwright 1.63.0 (no Browser tool available) zh/en desktop/mobile passed, no console
errors or page overflow; /tmp/native-merge-{desktop,mobile}-{zh,en}.png viewed.
Disk exhaustion caused Docker import / final VSIX repack / initial browser script
creation to fail; original logs retained, Codex run unaffected and audited passed.
Removed only this task's failed image a99323074f85 and prior completed task builder
images 85a406633cb0 / 45a3ff1f8a79 identified by retained grid/derivation build logs.
No broad prune, no source/evidence deletion. Docker/packaging reruns pending.

Docker retry ba071331d2e3 passed import/native merge wiring, doctor/list-tools and
actual SDK2 stdio. VSIX retry packaged 66 entries and all-artifact audit passed.
Initial clean-wheel install also exhausted disk; retained failure log. Removed only
completed task Docker runtime/builder (ba071331d2e3 / c216733ce610), then clean-venv
built-wheel retry passed help/doctor/list-tools/SDK2 stdio. Dedicated RAM pip cache
removed after terminal proof. Logs: /tmp/asset-aware-merge-{docker-retry,package-retry,
wheel-smoke-retry}.log. Runtime fingerprint still matches actual Codex run. Ready for
scoped main commits, then exact CI/Pages verification; no version bump/tag.

Core committed as 796656c. Companion commit contains the actual Codex merge auditor,
cross-platform/SDK2 CI registration, Chinese/English docs and synchronized assistant
harness. Local gates complete; push and exact remote CI/Pages remain pending.

## 2026-09-19 — native PPTX table grid CRUD in progress

Previous goal turn made verified progress: cea4870 / 29369ec pushed; exact CI
35363142564 (ten jobs) and Pages 35363141517 revalidated successful. Public bytes
matched, main clean and only main branch. Public version stays 1.4.0 / Unreleased
for 1.4.x. Original user worktree remains untouched. Next scope is table row/column
insertion, deletion and resizing, preserving existing XML/styles and rebasing
merged rectangles with explicit anchor promotion. Specification written before
implementation; reviewed primary python-pptx and Microsoft DrawingML references.
Full goal remains active; slide CRUD, other formats, real corpus and citations remain.

Implemented update_pptx_table_grid with typed insert/delete/resize, merge rebasing,
anchor promotion guards, frame-scale retention and package readback verification.
Full suite passed 1,971 / 30 optional skips in 62.28s; log
/tmp/asset-aware-grid-full.log. Ruff/format/mypy 171 source files/Bandit pass.
Full suite fixtures used dedicated /dev/shm/asset-aware-grid-pytest due low disk.
Live Codex run /tmp/asset-aware-codex-pptx-grid-01 started with --grid; evidence retained.
Actual Codex grid run 01 passed: 123 MCP calls, zero errors, exact first
transcription, one PNG and nine full records. Five intermediate revisions audited,
including surviving cell XML/format and unrelated package parts. Runtime SHA256
fc259ab32c056c1a82666a7d81e3ccea59dd6856bf936cc1b7304f0ad12ff2c5; lock unchanged.
199 VSIX tests/64-file contents guard, fresh/update install (activation unavailable
locally), Docker grid-check 6fa05ebe762c and Python build passed. Initial artifact
audit ran while install smoke removed the VSIX; explicit sequential package and
--require all audit then passed (66 packaged entries). Browser fallback Playwright
1.63.0 passed zh/en desktop/mobile with no console errors/overflow; screenshots
/tmp/native-grid-{desktop,mobile}-{zh,en}.png viewed. No Browser plugin available;
used existing local libraries/cached CDN. GitHub metadata and labels synchronized;
Python 214 packages/npm lock zero known vulnerabilities. Removed only completed
task-owned /dev/shm/asset-aware-grid-pytest after terminal full-suite result; rm-style
command was rejected before execution, scoped Python cleanup succeeded. Prior
Docker task-only derivations-check image removed after recorded success, no broad
prune. All actual Codex evidence and logs retained. Public remains 1.4.0/Unreleased.
Clean-venv built-wheel smoke passed (help/doctor/list-tools/real SDK2 stdio); log
/tmp/asset-aware-grid-wheel-smoke.log. Removed only task-owned grid-check image
after its completed smoke to recover disk, retained Docker log/image ID; dedicated
pip cache was /dev/shm/asset-aware-grid-pip-cache. Core committed as a9739eb.
Remaining: commit actual Codex/CI/docs/harness, push both and verify exact CI/Pages
and public bytes. No source changes since full tests or the successful Codex run.

## 2026-09-18 — cross-asset derivation ledger in progress

Previous turn made verified progress: 19dfb3f/8c7548b pushed; CI 35358045055 (ten
jobs, Linux activation) and Pages 35358043487 revalidated successful at exact HEAD.
Public site bytes match. Main is clean at start; source worktree remains untouched.
Public version stays 1.4.0; new work accumulates Unreleased for 1.4.x.
Specification first: record/read/retract/verify native derivations using existing
full immutable references, separate agent review claims and append-only CAS ledger.
Wiki includes source attachments and distinct ledger-pinned snapshots. References
checked: W3C PROV-O and Docling Graph provenance docs, 2026-09-18. Full goal remains
active: broader native structural CRUD, formats, real corpus and citations remain.

Implemented native derivation record/read/retract/verify, atomic supersession,
full reference verification across five families, bounded CAS/event replay and wiki
source attachments. Existing native models modularized with public import compatibility.
Initial full suite: 1,896 passed / 30 optional skipped in 61.25s. Thirteen independent
Codex-auditor regressions added afterward and pass. SDK2 scanned PDF->PPTX linkage,
stale-write rejection, correction/retraction and exact source wiki attachments pass.
Actual run 01 never started Codex: mistyped executable extension path, FileNotFoundError;
startup log retained. Corrected path run 02: 93 MCP calls, zero MCP errors, exact first
transcription, one PNG, five complete records, four ledger events/one active assertion,
all independent audits passed. Model self-reported a local orchestration syntax recovery
without a separate error event; preserved in agent_reported_limitations. This is not
counted as an observed MCP tool error or silently discarded. Run 03 passed: 92 calls,
zero MCP errors, exact first transcription, same five-record/four-event/source audit.
Evidence: /tmp/asset-aware-codex-derivations-{01,02,03}; source SHA256
bf399b5246cb6fd4c48b039ea102e3257eac69f433f1e9ceb3275cc73eca685c;
lock SHA256 abfaddf3d7d964ace1e210b1fd584e1717775a70f8ccdc98ad9b669b61f1bcd3.
Removed only completed pytest-187 after terminal full-suite proof and no live pytest;
retained logs/Codex/user files, recovering its 477 MiB fixture space. Final full suite
passed 1,909 / 30 skips (62.02s), then its completed fixtures were also removed before
Docker build to recover space. Final logs retained. Ruff/format/mypy 167 source files,
Bandit, 199 extension tests/64-file VSIX, Python build/artifact audits and dependency
audits passed (214 Python packages and npm lock: zero known vulnerabilities).
Browser zh/en desktop/mobile passes without overflow or console errors; Playwright
1.63.0 fallback, no Browser plugin, cached CDN assets and task-local libraries from
/tmp/asset-aware-contracts-browser-libs/usr/lib/x86_64-linux-gnu via LD_LIBRARY_PATH.
Initial browser launch lacked libasound/libgbm; corrected without system installation.
Screenshots /tmp/native-derivations-{desktop,mobile}-{zh,en}.png. Local VSIX fresh/update
installation and Docker build/native derivation wiring passed; activation skipped locally
(no xvfb), absent 0.2.10 baseline and optional runtime diagnostic skipped. CI enforces
activation. Final review added supported source attachment suffixes so exported PDF can
be directly re-registered; the real SDK2 regression confirms format and exact revision.
Focused 18 tests pass. Runs 02/03 describe the preceding runtime; run 04 and full gates
are repeated for this final production change. Previous task-only Docker image removed
after successful smoke to recover space. Exact post-push CI/Pages remain pending.
GitHub metadata and 17 managed labels match canonical configuration.

Final source after the portable-extension fix passed the full suite again: 1,909
passed / 30 skipped in 61.69s, /tmp/asset-aware-derivations-release-final.log.
Python wheel/sdist artifact audit and final Docker build/native wiring passed.
Removed only completed pytest-185/188 fixtures with live root excluded; original
files, actual Codex evidence and test logs retained. Desktop-en/mobile-zh screenshots
of the new derivation guide were viewed and legible. Public remains 1.4.0.
Final-source Codex run 04 completed 96 MCP calls, zero MCP tool errors, exact first
transcription, one PNG/five complete records/four ledger events/one active assertion.
Initial auditor rejected a preview followed by restart at offset zero. Actual trace
contains the complete 25,578-character shape before any edit; corrected the auditor
to discard incomplete prefixes on explicit restart, still requiring full hash-checked
readback. Three regressions prove valid restarts and corrupt restart rejection;
25 focused table/derivation auditor cases pass (16 derivation cases). Initial failure
retained as audit-initial.json and original runner log; final audit.json passes.
Model self-reported an over-escaped font diagnostic recovery; retain that limitation
without treating it as an observed MCP error or independent proof. Runtime SHA256:
dba99f0ee01452813611fd2eb18ecdf84a32e0fd240d499a873adcc7ebde3604.
Core and SDK2 changes committed as 29369ec under u9401066 <u9401066@gap.kmu.edu.tw>.
Remaining commit: actual Codex auditor, docs/harness/platform CI; push both commits
then verify exact CI/Pages. Full local source suite 1,909 passed / 30 skips; final
three added auditor regressions are covered by the focused 25-test rerun. Broader
format CRUD, cell-level mappings and real-document corpus remain active goal work.


## 2026-09-18 — native editable PPTX tables verified locally; push pending

Previous turn is verified progress: d46fdce/e220434 implements picture assets;
exact CI 35353663631 (ten jobs) and Pages 35353662373 both revalidated successful.
Main is clean at start; public still 1.4.0 and all new work is Unreleased / 1.4.x.
Original user worktree remains untouched. Next scope is add_pptx_tables, closing
native table creation while using existing shape reads, cell-run edits, deletion,
immutable verification/wiki and guarded source writes. Explicit grid sizes, rich
text, direct cell colors/alignment/margins, merge rectangles and destination style
inheritance. Reject content in covered cells, overlapping/out-of-range merges and
resource budget violations. Scratch python-pptx only creates new table nodes;
package edits remain scoped and read back against the typed request. Specification
written first; source table concepts/API checked 2026-09-18. Native row/column edits,
slide operations, broader formats and real-document corpus remain active goal work.

Implemented table creation, public schema/dispatch/capabilities, destination style
GUID resolution and generic named shape insertion. New src/domain/native_pptx_table.py
and infrastructure native_pptx_table_builder/checks/tables.py. Tables preserve exact
unrelated parts and reverse new shapes before XML comparison; raw readback verifies
request geometry/text/styles/merge map. Forty backend/guard tests (14+26) cover notes,
groups, numeric-looking strings, rich runs, merge rectangles, source signature/style
relationships, data loss/resource limits and builder corruption. Six managed tests
and real SDK2 table CRUD/wiki/backup-writeback passed. Existing shape-v1 unchanged.

Actual Codex scanned-table run 01 passed final checks with exact initial transcription,
but one recovered misuse of untyped citation_contract. Evidence retained at
/tmp/asset-aware-codex-pptx-tables-01: 67 attempts, 66 successful calls, one tool error.
Fixed the discovery gap: CitationFormatPreset/custom CitationFormatContract typed
union in native requests; JSON selectors/templates retain compatibility; source
proofs are not display settings. Ten schema regression cases plus native schema/wiki/
SDK2 focused matrix: 72 passed. Separate existing provenance claims remain untouched.
Run 02 /tmp/asset-aware-codex-pptx-tables-02: 66 calls, zero errors, first transcription
exact, one actual MCP PNG, four distinct complete records; same native source/lock
hash as current runtime. Codex 0.154.0-alpha.6.1 default model, not pinned.
Runtime source SHA256 3096077f38a15d48c9c646ea509532d2cab6554193a5c7ab027e2c6af3dde995
Lock SHA256 abfaddf3d7d964ace1e210b1fd584e1717775a70f8ccdc98ad9b669b61f1bcd3
Auditor checks actual page pixels, complete records before edits/deletes, exact grid/
merge/text and temporary change/restoration in all managed revisions, historical
proofs, source bytes/mtime and PPTX/wiki attachments. Initial mistakes/recoveries are
retained, never relabeled as first-pass success. Nine auditor regressions passed.

Final full tests: 1,857 passed / 30 optional skips; the final SDK2 test refactor
also passed its focused rerun (one integration test).
Ruff/format/mypy (162 source files), Bandit, docs/harness/18-skill audits and VSIX
199 tests/64-file package passed. Final gates and browser/build audits are recorded
below; commit/push and exact
final CI/Pages verification remain pending. Docs/README/ROADMAP/harness/CI
are synchronized; no new dependency/version/tag. Original user worktree untouched.
Next goal gap after this checkpoint: explicit cross-asset semantic derivation links
(PDF page -> new table) separate from citation display. Those links are NOT supplied
by merely matching table text or exporting native source evidence. Broader grid/slide
CRUD, real-document corpus and remaining formats also stay in the original scope.

Runtime/table/schema and SDK2 changes committed as 19dfb3f under
u9401066 <u9401066@gap.kmu.edu.tw>. The remaining commit contains the opt-in Codex
evaluator, auditor regressions, platform CI, bilingual site and synced harness.
Current source/lock hashes still match actual Codex run 02. Push both commits to
main, then verify exact final CI/Pages and public site bytes; no version bump/tag.

## 2026-09-18 — native PPTX image assets, local verification in progress

Public version remains 1.4.0; all current work is Unreleased for the 1.4.x line.
User explicitly rejects rapid version jumps. MCP performs necessary deterministic
checks; Agent coordinates full semantic/visual/formula verification and correction.
Use asset-aware-mcp-agent-assets on main; original user worktree is untouched.
Previous checkpoint 44568f7: exact CI 35349396027 (all ten jobs) and Pages 35349393804
success. Active long goal remains incomplete; broader structural CRUD remains.

Implemented native-file-ref-v1 and four native PPTX picture operations: add,
replace, read actual MCP PNG, extract independent asset with source lineage.
Exact PNG/JPEG media; shared media preserved; replacement changes only r:embed.
Creation supports slide/notes/nonzero groups with contain/cover/stretch. Existing
shape-v1 evidence/wiki and explicit source/backup/writeback guards are retained.
MCP verifies source/revision/CAS, resource budgets, exact additions, untouched parts,
relationships/content types and reverse XML. Embedded-image previews do not apply
slide crop, transforms, effects or color management. Agent must review actual slides.
Limits: 16 MiB/16M pixels per raster; 32 MiB/64M per batch including repeated uses.
Reject animated/multiframe, EXIF orientation, linked/alternate rasters and bad media.
No new dependency. python-pptx builds scratch nodes only; original packages use
scoped XML and additions. Pillow verifies containers, then reopens before metadata
and decoding. Source API docs: python-pptx Shapes, Pillow Image (2026-09-18).

Initial full suite 1,753 passed / 30 skipped before final guards/auditor tests.
Backend ten tests, guards nineteen, managed seven and actual SDK2 picture workflow
pass. Auditor regression matrix with existing PDF auditor: 44 passed.
Actual Codex CLI 0.154.0-alpha.6.1 picture runs 01 and 02 passed independently:
/tmp/asset-aware-codex-pptx-pictures-{01,02}. Run 01: 38 calls, no errors, three images,
two complete shape records, exact A101/007 and C301/001 visual transcription.
Run 02: also 38 calls, zero errors, three actual images and two full shape records.
Both runs pass the strengthened audit. CLI default model, not pinned.
Auditor verifies pixels independently, exact media, prior complete mutation refs,
source bytes/mtime, old shape proofs, lineage, baseline shape XML, notes/untouched
parts and wiki attachments. Tests do not launch a model. Logs/fixtures stay in /tmp.

README/CHANGELOG/spec/native-file and release-testing guides updated; English site
copy and harness/CI updated, bundled assets/build/gates/commit/push still pending.
Need final Ruff/format/mypy/Bandit/full pytest, VSIX sync then 199 tests/package,
docs desktop/mobile zh/en checks, audits/build, direct main commits under user
identity and exact CI/Pages verification. No tag, no minor bump, no self PR.

## 2026-09-18 — native PDF collaboration verified locally; commit/push pending

Public release remains 1.4.0; this is Unreleased main work for 1.4.x. User explicitly
rejects rapid version jumps. MCP provides necessary mechanical checks and supported
deterministic repairs; Agent coordinates complete semantic/visual/formula review.
Previous checkpoint ab49252 has green CI 35342913394 (ten jobs) and Pages 35342912718.
Original user worktree remains untouched; use asset-aware-mcp-agent-assets on main.

Current implementation: native PDF create/read/render/insert/copy/delete/reorder/
rotation/crop, revision-bound full page JSON/evidence, persisted copy lineage,
historical verification, pdf-pages-v1 wiki and explicit publish/writeback through
existing source/hash/mtime/backup guards. pikepdf>=10.13.0.post1,<11 uses public
form-aware copy; PyMuPDF independently reads text and pixels. No universal layout
or OCR correctness claim, arbitrary PDF text replacement or secure redaction.

PDF graph checks normalize object numbering while preserving encoded stream hashes,
cycles and page identities. Verify remaining page dependencies, untouched document
properties, form registration, serialized graphs and unchanged-page 512-pixel renders.
Repair discovered copied annotation Popup/Parent/IRT backreference duplication from
exact source mapping, then require graph equality. Preserve effective page labels.
Reject encryption/signatures/XFA/parser repair, dangling references, partial/renamed
forms and cross-document tagged/layer/named-destination integration. Copying pages
does not import document-level metadata/attachments. Source revisions remain exact.

Production worker: spawn, supported-platform 1.5 GiB address-space cap, 60-second
deadline, private atomic MessagePack handoff (128 MiB), validated edit reports and
child cleanup. Reuses tested PDF extractor transport; no blocking full pipe receive.
8 new worker tests cover large/partial/corrupt/oversized output, cleanup and invalid
timeouts. Full suite now 1,739 passed / 30 optional skips; Ruff/format/mypy (150 files)
and Bandit passed. SDK2 integration verifies actual PNG content, full-page chunks,
CRUD, copied forms, source writeback and wiki. Domain schema expresses exclusive page
inputs and nonempty geometry; bool/string/float rotations rejected without coercion.

Live Codex run 01: 171 actual MCP calls, zero tool errors, 13 complete page records,
all seven independent checks passed. Run 02 after worker/type/helper changes:
49 calls, zero errors, ten complete page records, six actual source/final images,
all seven checks passed including exact final 7-row/35-cell transcription, original
source hash/mtime, final page order/rotation/pixels, persisted lineage and wiki files.
Both runs are synthetic scanned three-page PDFs with no hidden OCR. Original and
final images are independently compared to the pinned revision render, beyond PNG
hash self-consistency. Do not reinterpret this as general real-document coverage.
Evidence: /tmp/asset-aware-codex-native-pdf-scanned-01 and -02.
Run 02 server source SHA-256: fff357bad15d8f678afc938ae3c64c88a7af79837df8e52ec22207152e4503dd
Run 02 lock SHA-256: abfaddf3d7d964ace1e210b1fd584e1717775a70f8ccdc98ad9b669b61f1bcd3

README en/zh, CHANGELOG Unreleased, wiki/site en/zh, harness and bundled assets
updated. Browser plugin unavailable; cached Playwright/Chromium validates language
switching, content, desktop/mobile overflow and console health on localhost:8876.
CDN scripts were routed from cached copies; this does not test CDN availability.
Screenshots: /tmp/native-pdf-crud-{desktop,mobile}-{zh,en}.png. Website/docs/harness
metadata checks pass. VSIX: 199 tests and 64-file package contents pass. All 17
managed labels and repository description/homepage/topics are synchronized. Universal lock Python3.10 audit previously passed
214 audited packages, no known vulnerabilities/adverse statuses; npm audit passes.

Runtime committed e47ad9f; tests/docs/harness committed 4af244d and pushed directly
to main. Pages 35349131496 passed; public site.js, site-content.js and both changed
Markdown guides exactly match committed bytes. CI 35349131756 was in progress.
Final audit found the CI integration job uses an explicit file list, so add native
PDF SDK2 plus focused backend/worker tests to Python3.10/macOS/Windows and Linux
integration jobs. A small CI follow-up will supersede the earlier CI run. No tag
or release; exact final CI still needs verification.
Broader active goal remains unfinished (slide/non-text CRUD, additional formats,
real-document evaluation, arbitrary PDF text editing). Do not mark goal complete.


## 2026-09-18 — cross-format CRUD and evidence library

Current work after 53714f2: fix truthful A2T row-ID result labels, then add native
PPTX shape creation/deletion. Previous turn was progress: citation readback commit
53714f22a8d92c18fc25e8867fc4f6d9099febd0 has green CI 35339895059 (all ten jobs),
Pages 35339894396 and matching public JS bytes. main and origin/main were clean
and equal before this turn. Public version remains 1.4.0; do not jump versions.

Current checkpoint: A2T result labels return resolved row_id/index;
18 new tests cover earlier-row deletion and conflicting/default indices. Corrected
baseline against git archive 53714f2: 16 failed / 2 passed, then all 18 pass. The
initial invalid fixture-intent setup failure is not regression evidence.

Native add_pptx_shapes/delete_pptx_shapes are now implemented. Domain contracts
bound atomic batches (1..100, 20,000 runs / 4 MiB UTF-8); application stages revisions
with CAS. New textboxes are built in an independent python-pptx scratch package,
converted to plain lxml and inserted in existing slide/notes/group XML only. Group
transforms remain untouched; zero extents fail closed. IDs avoid known reference
IDs and extLst remains last. Delete checks complete shape-v1 representation hashes,
asset/revision, duplicates, ancestor overlap and surviving numeric spid/shapeid or
connector IDs. Package inventory/untouched bytes and reverse-applied XML comparison
are checked. All related media/relationships remain; this is not secure erasure.
Unmodeled vendor/GUID dependencies and rendering require agent review.

Current full Python gate: 1,647 passed / 30 optional skips. New raw-shape suite:
27 passed; managed operations + real SDK2 CRUD: 16 passed. Tests cover connectors,
zero extents, protected/signed files, package/XML corruption, aggregate bounds,
source backup/conflicts, CAS, old references and immutable wiki snapshots. Public
version remains 1.4.0; this accumulates Unreleased for 1.4.x. Live Codex scanned
PDF recheck /tmp/asset-aware-codex-row-identity-scanned-01 passed all nine independent
checks: 49 MCP calls, zero tool errors, 9 canonical citation reads with continuations.
First transcription was NOT exact: B201 Count 03 -> 003 and B202 8 -> 18 were
corrected by the agent before final verification. Real tool responses now show
resolved row indices/IDs when the input row_index is omitted. Independent auditor
reopened Excel and checked source/image/citation/bundle integrity; agent prose is
not used as proof. Runtime source SHA256:
54463c8594dd9734a52ec680ab7ae77e7b3c37c93dfee1066b141cd702fc390c.
Ruff/format/mypy (138 files)/Bandit pass; 199 extension tests and 64-file VSIX
package guard pass. Docs generator/harness/artifact (1.4.0)/18 skills/assets sync,
GitHub metadata and 17 labels pass. Playwright desktop/mobile zh/en checks pass
for the new Unreleased shape operations, language switching, overflow and console
errors (/tmp/pptx-shape-crud-browser.cjs). Cached pinned CDN scripts were routed;
this does not test live CDN availability. Remaining: commit/push and exact CI/Pages.
Do not edit the original user worktree or mark the broad goal complete.

Primary research checked this turn:
https://python-pptx.readthedocs.io/en/latest/api/shapes.html (public textbox/element,
shape ID collision warning, z-order and automatic group extent recalculation),
https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.drawing.startconnection?view=openxml-3.0.1
and presentation.shapetarget.shapeid / presentation.shapetree (shape references/tree).
Implement with current pinned python-pptx; no new dependency is selected.

Current public release is **v1.4.0**, annotated at main@da829fa6f360bd684fda9b8d31efee3651a9ed94.
Tag object: 2eae299581211126d7bbc3e5586b6f4b3a028b54.
Worktree: /home/eric/workspace251226/asset-aware-mcp-agent-assets, branch main.
The user requests direct commits/pushes without self-PRs; use the owner's existing
bypass, preserve branch protection and monitor exact-commit CI. Author:
u9401066 <u9401066@gap.kmu.edu.tw>. Only main remains locally and remotely.
The original worktree /home/eric/workspace251226/asset-aware-mcp stays detached at
6ad9a5c with pre-existing user changes preserved. Do not edit/reset that tree.

Version 1.4.0 is published on PyPI, VS Code Marketplace and GitHub Release:
https://github.com/u9401066/asset-aware-mcp/releases/tag/v1.4.0
Exact-tag CI 35335805871 (all ten jobs), Pages 35335805355 and Release 35336169071
(all eight jobs) passed. Full local release.sh passed with 1,546 Python tests /
30 optional skips, 199 VSIX tests and all audit/package/runtime/Docker/SDK2 gates.
CI supplied extension activation because local Xvfb is unavailable.

Public Python artifacts match the locally audited builds byte-for-byte:

- wheel: 5d3ed4a4e760f50db223d8bc2b0ff47241d10a91aa04ddd34bcd52aacb563a83
- sdist: c18b12aa78d8d854492bfbac221c182f4bfd6fe0a8218719e942b5fe10e5ba38

GitHub and Marketplace VSIX bytes match after declared HTTP gzip decoding:
4c4bc06c6e47de5edfba1de27d8a0ce2c3b918e160e9c2283882b3a39cbaaa15.
Version, author/publisher, native source modules, bundled harnesses and exclusion
of compiled VSIX tests are verified. Public site.js/site-content.js match the
release commit. Proof: /tmp/asset-aware-release14-verified.json,
/tmp/asset-aware-release14-python-verified.json and
/tmp/asset-aware-release14-pretag.log. Initial registry/index visibility delays
resolved without duplicate publication. Do not move the tag or republish bytes.
The user explicitly requests 1.4.x for subsequent small updates. No v2.0.0 tag
or package was published; contract-v2 and MCP SDK 2.x are separate version axes.

Previous milestone v1.3.0 remains published at 2aba6595453a65aa6fd541b3d93df69c9b041fc6
(tag object b9217ed4a74d9f348129bb472f6ae340325a9aab):
https://github.com/u9401066/asset-aware-mcp/releases/tag/v1.3.0
Exact-tag CI 35325369333 and Pages 35325368633 passed. Release 35325631670 passed
all eight jobs: tests/activation, three-platform install smoke, artifact preflight,
PyPI, Marketplace and GitHub Release. Full local release.sh also passed: 1,423
Python tests / 30 optional skips, 199 VSIX tests, lint/types/Bandit, zero-issue
Python/npm audits, docs/harness, wheel/sdist/runtime and Docker/SDK2 stdio checks.
Local Xvfb is unavailable; Linux CI supplied required extension activation checks.
Bilingual reader QA passed at desktop 1440x1000 and mobile 390x844 using the pinned
cached CDN assets (not a live-CDN availability test). Metadata/labels are synchronized.

Public Python artifact digests match the local audited builds:
- wheel: 8d248e60960f1bd02a71b4f598ac014704c461d1be4a78859af9603da2bdff61
- sdist: 06c2b2d4730e2a3eded6a84a972e4c81873b3490c8d0eab667c0bd457d5a6223
Marketplace VSIX matches GitHub's release asset digest after decoding the declared
HTTP Content-Encoding: gzip transport: 2229c295d710e6a677dec36d883c0ff0bac7ecddf333fbba0a518bbe664b2d3d.
Version, author/publisher, required new DOCX source files, both bundled native
harnesses and absence of compiled VSIX tests are verified. Verification artifacts
are under /tmp/asset-aware-release13-verified.json, /tmp/asset-aware-release13-github.json,
/tmp/asset-aware-pypi-1.3.0.json and /tmp/asset-aware-mcp-1.3.0-marketplace.vsix.
Do not recreate/move v1.3.0 or republish different Python bytes under that version.

Observation pitfall: repeated gh run view/watch and Marketplace queries returned
stale in-progress/version data. Completed job logs and a fresh gh api GET with a
unique verification query parameter plus Cache-Control: no-cache confirmed success.
Prefer fresh exact-run/job API queries when status contradicts completed logs;
do not rerun publication merely because an observation is stale. Decode HTTP
content encoding before comparing artifact bytes (the raw gzip envelope differs).

Released native coverage includes stable file IDs, immutable SHA-256 revisions,
independent XLSX creation, scoped XLSX/XLSM cell edits and explicit
publish/writeback/refresh/archive. Native cell evidence and v1.2 wiki projections
retain exact legacy artifact hashes. PDF bundle refresh validates inventory/hashes,
rejects human edits and retains backups on actual generated-content replacement.

The 1.3.0 DOCX bridge reuses the existing DFM session/checksum, pre/post-save,
table-shape and unedited-block guards in private workspaces. read_docx returns
revision-bound deterministic DFM chunks; update_docx requires the complete native
binding and block markers. Updates commit managed revisions with CAS before any
explicit source writeback. Untouched package parts retain exact bytes. Signed or
protected packages are readable but updates are rejected, including relocated
signature/settings targets. Structural/style design edits remain unsupported.

DOCX evidence uses full DocxIR block serialization, never truncated previews.
read_docx summaries, read_docx_block and export_wiki share native-docx-block-ref-v1;
verify checks immutable bytes, exact part/block locator and representation hash.
Old references survive edits/archive, with freshness reported separately. Block IDs
are revision-scoped, not stable cross-revision component IDs.
DOCX wiki uses a distinct docx-blocks-v1 projection: complete JSONL, block/index
notes, original DOCX and exact package-part attachments with path/hash/size mapping.
Old opaque DOCX snapshots remain untouched; DFM temporary media paths never become
fabricated persistent associations. Limits: 20,000 blocks, 10,000 package parts,
30,004 artifacts and 128 MiB. Integrity does not prove extraction completeness.

Feature commits: bbdbf8a (DFM bridge, CI 35321780547) and b50ed35 (block/wiki evidence,
CI 35324654138; Pages 35324654419), all green. Forty-eight tests were added since
1.2.0, including real SDK2 read/edit/writeback/block verification/wiki flows.
Key modules: src/application/native_docx_{bridge,records,operations,wiki}.py,
native_document_contract.py, native_evidence_service.py, native_wiki_{format,service}.py;
src/domain/native_assets.py and native_docx.py; infrastructure workspace/publisher.

The latest explicit user clarification governs the broad goal:
「MCP 提供必要檢查，Agent 負責完整核對與修正」.
MCP owns mechanical source/version/locator/package/write checks and explicit,
deterministic repairs. Agents own semantics, rendering, fields/formulas, extraction
review and subsequent correction. No structural pass is a full-fidelity guarantee.

Native PPTX collaboration is implemented, verified and released in v1.4.0.
Feature commit 2364feefe50204f094eacc34f8d20464a7914578 has successful CI
35331710478 (all ten jobs, including Windows/macOS/Linux) and Pages 35331709690. Discovery checkpoint 1546bd351d633c169955ffd9a1540d31b6ef148b
has green CI 35329453898 and Pages 35329453179. Native-contract-v2 provides for_op
and complete hash-pinned schema pages; existing operation inputs remain unchanged.

PPTX exposes create_pptx/read_pptx/read_pptx_shape/update_pptx, native verify and
export_wiki. Creation uses python-pptx with explicit text boxes, paragraphs, styled
runs, dimensions in EMU and notes. Native edits resolve relationship-backed slide/
notes/shape IDs, preserve group/local transforms, require run hashes and managed
revision CAS, and change only existing a:t nodes. Package inventory/untouched bytes,
read-back and canonical XML outside the requested text nodes are checked. Fields,
new tabs/line breaks, merged-cell continuations and structural edits are rejected;
signed/protected or strict/macro/legacy presentations require separate support.

Shape evidence binds full JSON/XML to revision-scoped locators. PPTX wiki uses
pptx-shapes-v1, retaining every exact package member and previous opaque snapshots.
Golden v1.2 XLSX/v1.3 DOCX artifacts remain unchanged. Bounded reads materialize only
requested shape representations; agents review semantics, inheritance, overflow and
rendered layout. Integrity does not prove extraction completeness or visual fidelity.

Validation: 1,493 Python passed / 30 optional skips; 199 VSIX tests and package-content
checks passed. Lint/format/types/Bandit, docs generation/check, harness/skills audits,
asset synchronization and diff hygiene passed. Real SDK2 tests cover creation,
read/edit/evidence/wiki/publication/writeback/stale rejection. Logs:
/tmp/asset-aware-native-pptx-tests.log and /tmp/asset-aware-pptx-extension-tests.log.
Desktop/mobile zh/en browser QA passed after updating the English native overview;
pinned cached CDN replay was used, so it does not prove live CDN availability.
Screenshots: /tmp/native-pptx-{desktop,mobile}-{zh,en}.png. GitHub metadata/17 managed
labels remain synchronized. Original detached worktree and user edits are untouched.
README/Pages/spec/CHANGELOG/MEM and all bundled native harness guidance are updated.
Next: continue broader native CRUD, citation standards and agent review workflows.
Native discovery has an explicit response migration, documented in v1.4.0 despite
the owner's requested minor-version sequence. Never republish new bytes under an
existing tag/version.
Goal stays active. The current goal turn made concrete progress (schema discovery
and native presentation creation/edit/evidence/wiki), and is not blocked.

Published release: **1.4.0**, following the user's explicit correction to keep
incremental releases in 1.4.x. The proposed 2.0.0 was committed only as preparation
at 929e878; no 2.0.0 tag or package was published. Native discovery still documents
its client migration from always-inline schema to inline/paged delivery. Version metadata,
README/Pages/extension copy and bundled harness instructions are synchronized.
Checkpoint cf7f166 and its CI 35332075734/Pages 35332074774 were revalidated green.
Pre-tag full release harness, tagged CI and public artifact verification all passed
for 1.4.0; proof is recorded above. No new PDF backend dependency was added.

The user added goal item 7: directly use Codex to exercise MCP, especially
image/scanned PDF to structured-data CRUD with adequate tests. Its synthetic
baseline was completed before tagging 1.4.0. Existing real SDK2 tests alone are
not agent-driven validation. Continue preserving independent fixture truth and
checking actual Codex MCP events and persisted artifacts. Never alter the
user's persistent config or original sources; do not expose credentials.

Goal item 7 now has a reusable baseline under tests/codex_pdf: synthetic digital,
scanned and mixed 3-page fixtures (7 rows / 35 cells), a real opt-in Codex CLI
runner, an independent event/artifact auditor and an SDK2 CRUD matrix. Source
truth stays outside the agent workspace; shell/apps/subagents are disabled and
only one required checkout-local MCP server is configured. No persistent user
configuration or credentials are read/changed. CLI 0.154.0-alpha.6.1 uses existing
ChatGPT login and its default model; runs are not a pinned-model benchmark.

Live testing exposed a rotated crop bug: image locators were intersected with
rotated page.rect and passed directly to rendering. Pad/intersect in unrotated
cropbox space, then apply rotation_matrix for rendering. Sixteen full/partial
pixel regressions across 0/90/180/270 and crop offsets had 10 failures before and
16 passes after. Image-only section errors now point to inspect/figure fetch.

Live evidence: /tmp/asset-aware-codex-pdf-mixed-03 (56 successful MCP calls, two
recovered tool errors), /tmp/asset-aware-codex-pdf-scanned-01 (46 / one recovery),
and /tmp/asset-aware-codex-pdf-scanned-02 (48 / three recoveries). Independent
audits pass all eight final artifact/workflow checks. The second scanned run
initially dropped two leading zeros, then visually rechecked and corrected them;
first_transcription_exact remains false. Its first audit was overly strict about
unrelated correction edits; the auditor now targets the requested B202 Reading
edit/restore history while retaining final-data equality, with regression tests.
The earlier mixed-02 correctly fails scan pixel integrity despite correct rows.
The first configuration attempt mixed-01 was blocked by MCP approval policy;
explicit approval is now scoped only to this authorized synthetic test server.

Latest repeated live run /tmp/asset-aware-codex-pdf-mixed-04 completed 47 successful
MCP calls but fails strict transcription/Excel equality: B201 Unit was Greek
mu U+03BC instead of micro sign U+00B5. The raster glyph cannot recover the original
Unicode codepoint. Keep this failed result and limitation explicit; do not silently
normalize the evidence or describe all live runs as lossless. Other six checks pass.
This is a perception/encoding boundary, not a regression in mechanical crop repair.

Final full tests: 1,546 passed / 30 optional skips (53 added since the PPTX
checkpoint). VSIX: 199 passed, 64-file package inventory. Lint/format/types/Bandit,
docs/harness/skills/metadata audits, sync parity and diff hygiene pass. Logs:
/tmp/asset-aware-pdf-codex-full-tests-final.log and
/tmp/asset-aware-pdf-codex-extension-tests.log. Commit 929e878 has green CI
35335476121; version correction da829fa has green exact-commit CI 35335805871.
Thirty-five metadata/public-doc/release-audit tests pass for 1.4.0; lock changes
only the project's version. Remote v1.4.0 is verified; no v2.0.0 tag was created.
Desktop/mobile zh/en browser QA includes the new Codex guide; screenshots
/tmp/pdf-codex-{desktop,mobile}.png use cached pinned CDN assets and therefore
do not test live CDN availability. Rebuilt docs include commands and limits;
English Pages has corresponding evaluation guidance. No general OCR accuracy,
handwriting/complex-table coverage or PDF source-layout writeback is claimed.

The citation readback gap found in live Codex testing is now implemented on main's
development line, pending commit/CI below: table_cite read exposes full stored
doc_id/asset_id/page and precise locators. get summaries remain compatible. Expand
the real-document evaluation corpus and address the remaining workflow gaps.

Further implementation work remains active: native structural CRUD (slide/shape
addition/removal and equivalent operations for other formats), independent table/
native bridges, asset relationships and complete agent review workflows. Scalable
schema discovery and scoped native PPTX operations are already implemented; do not
repeat the old discovery-size investigation. The full goal remains incomplete.
CSL evaluation is recorded in decisionLog.md: citeproc-py has documented conformance
gaps, citeproc-js needs ordered citation context and CPAL/AGPL evaluation, while
jgm/citeproc offers a BSD Haskell/JSON executable. No citation engine is selected.
MCP SDK stays >=2,<3, locked to 2.2.0. Docling/pdfplumber/pikepdf/pypdf roles were
rechecked against official repositories; no new dependency was added in 1.3.0.
MinerU/Marker security holds remain. A release is a milestone, not completion of
the broad goal in docs/spec.md and ROADMAP.md.

Completed 1.4.x development milestone: canonical A2T citation readback, specified
before code in docs/spec.md. table_cite read returns complete stable cell/value/
citation JSON with pinned SHA-256, 1..4000-character pages, encoded-response budget,
16 MiB full-representation cap, and explicit non-verification of source/meaning.
Invalid addresses, stale/cross-cell pins, missing continuation pins, non-finite or
non-UTF-8 JSON fail closed. Source/table artifacts are untouched. Stable row IDs
survive unrelated row reindexing; old get remains a summary with read guidance.

Modules: src/application/table_citation_read.py, TableService.read_citation and
the existing table_cite facade. Added 38 regressions in
tests/unit/test_table_citation_readback.py and test_codex_citation_readback.py;
the real SDK2 three-mode PDF matrix reconstructs every final Reading citation.
tests/codex_pdf/citation_readback.py independently verifies delivered pages and
final persisted values/refs, without trusting agent success prose. New runs opt
into citation_readback_required and citation_paging_required; historical eight-check
runs retain their original coverage and previous strict Unicode failure evidence.

Live Codex evidence (CLI/default-model policy unchanged):
- /tmp/asset-aware-codex-citation-scanned-01: 47 successful MCP calls, two recovered
  tool errors, first transcription exact, all nine final checks passed.
- /tmp/asset-aware-codex-citation-mixed-01: 46 successful calls, two recoveries,
  first transcription exact, all nine final checks passed.
- /tmp/asset-aware-codex-citation-paged-01: 48 successful calls, one recovery;
  nine canonical read calls include two hash-pinned continuations for a three-page
  record. Two count transcription errors were corrected; first_transcription_exact
  remains false. All nine final checks passed, including the explicit paging gate.
Every run retains source hash/mtime, actual images, exact final 35 cells, citations,
CRUD/readbacks, independently reopened Excel and exact bundle artifacts. No general
OCR accuracy or source-PDF layout editing is claimed. Agent reports cannot prove
hash verification; the independent auditor computes it from actual MCP responses.

Validation: 1,584 Python passed / 30 optional skips, 199 VSIX tests and 64-file
package check; lint/format, mypy (136 files), Bandit, docs generation/check,
harness/18-skills/metadata audits, sync parity and diff hygiene passed. Repository
metadata and all 17 managed labels match. Logs:
/tmp/asset-aware-citation-readback-final-tests.log and
/tmp/asset-aware-citation-readback-extension-tests.log. Desktop/mobile zh/en reader
QA passed; screenshots /tmp/citation-readback-{desktop,mobile}-{zh,en}.png use pinned
cached CDN assets and do not establish live CDN availability.
README/CHANGELOG/Pages and source/bundled skills explicitly mark this as unreleased.
No immediate version bump/tag: public release stays v1.4.0. Exact new-commit CI/Pages
must be checked after push. Further native CRUD/citation standards remain active.
Live Codex also observed old A2T row-ID response messages displaying input index -1;
data operations were correct, but resolved target display needs a regression fix.

Previous turn made progress: public v1.4.0 verification and checkpoint 6e61163;
its CI 35337926020 (all ten jobs) and Pages 35337924993 passed.


## 2026-08-13 - v1.0.1 large-PDF and Codex hardening

- Release scope is a non-breaking `1.0.1` reliability/security patch on top of
  the public `1.0.0` MCP SDK 2 release. It is driven by production Codex install
  and real-PDF asset-decomposition testing rather than a new public tool surface.
- Process-isolated PyMuPDF workers no longer send multi-megabyte results through
  a multiprocessing pipe or deserialize pickle. A private 0700 directory and
  0600 atomic file carry a bounded streaming MessagePack envelope; malformed,
  partial, oversized, crashed-worker and source-change cases fail closed.
  Text extraction uses one absolute deadline: a rich-worker timeout fails
  closed, while an early worker error may run the fast fallback only in a
  second isolated process with the remaining budget.
- MCP SDK 2 request progress still uses injected `Context`, while operational
  logs use Python logging on stderr. Empty/blank ingest inputs are rejected
  before any job is persisted, and managed launches can disable implicit cwd
  `.env` loading with `ASSET_AWARE_DISABLE_DOTENV=true`.
- Codex config work is hardened around semantic TOML validation, marker-only
  field-level ownership, custom/unrelated table preservation, user primary
  policy and nested `tools.*` byte preservation, 180/900-second timeouts,
  isolated `cwd`, least-privilege environment forwarding, parser-valid opt-out
  independent of uv readiness, and fail-closed symlink handling.
- A true MCP SDK 2 stdio regression creates a real PDF with text, table and a
  raster larger than 512 KiB, then validates preflight, async ingest,
  citation-ready records, media/artifact hashes, Foam notes, deterministic
  re-export, clean protocol output, and unchanged source bytes/mtime.
- A real 15-page paper exposed long evidence previews whose hash/ranges still
  described the full span. Persisted AssetRefs now retain exact quote/hash/range,
  while public MCP surfaces return bounded non-canonical previews. The fresh
  SDK 2 stdio rerun completed in 3.286 seconds with 39 asset records, 47
  artifacts, 39 Foam notes, six media files and all 435 evidence refs verified;
  the source hash, size and mtime stayed unchanged.
- Global Codex/Cline/Copilot configuration is now workspace-trust gated.
  Production entries use the exact extension package version and globalStorage
  only; a lookalike workspace and its `.env` cannot inject local Python or
  launch metadata into global agent settings.
- GitHub Pages is being replaced with a bilingual responsive product landing,
  an exact 30-tool explorer and a generated docs reader. Retired JPGs containing
  v0.6-era metrics, Marker claims, private IPs or local paths were removed;
  Playwright desktop/mobile visual and interaction QA is green before release.

## 2026-08-13 - MCP v2 / agent asset / Foam wiki major refresh

- Goal: converge all safe branches and PRs into the default branch, migrate to
  MCP Python SDK 2.x with no SDK-v1 runtime path, refresh document-to-agent
  assets and Foam wiki workflows, and publish a fully gated Python/VSIX release.
- Repository baseline is now fast-forwarded from local `0.6.3` to remote
  `0.9.0` (`6ad9a5c`). The previous dirty workspace is recoverable from stash
  `pre-v0.9-sync-2026-08-13`; installer-generated invalid MCP config backups
  remain there and will not enter release artifacts.
- MCP upstream baseline: official Python SDK `2.0.0` (released 2026-07-28).
  The new project floor will be `mcp>=2,<3`, with `MCPServer`, v2 protocol
  field names, and v2 in-memory client tests. No `mcp.server.fastmcp` fallback.
- Pre-sync local baseline found Ruff/format/MyPy green and pytest at
  `533 passed / 3 skipped / 1 failed / 16 errors`; all failures were the old
  checkout's optional Marker integration suite running without Marker.
- Repository convergence is complete: PRs #3/#4/#5/#8 were closed as empty,
  superseded, conflicted/obsolete, or stale; all 13 non-default remote branches
  were either already absorbed or safely retired after the remaining useful
  backup semantics were ported with regression tests. No unique work was
  discarded and no open PR remains.
- MCP SDK 2 migration is implemented with `MCPServer`, runtime `Context`, v2
  clients and snake_case protocol fields. The 30-tool schema regression proves
  that `ctx` leakage fell from 11 tools to zero; SDK v1 is unsupported.
- `document(op="preflight")` now provides a process-isolated,
  `pdf-inspector`-informed router with stable `pdf-preflight-v1` provenance and
  resource caps. Published `pdf-inspector` 1.14.1 was not added because it
  predates the pinned upstream main commit's DoS hardening.
- `document(op="export_assets")` now emits deterministic, atomic,
  traversal-safe `agent-asset-bundle-v1` records plus portable Foam notes,
  keeping exact hashes/locators/citations. The first implementation is backed
  by the existing PDF `DocumentRepository`; DOCX/general adapters remain a
  documented extension boundary.
- Dependency locks, Actions, Dependabot, audit workflows, docs, GitHub metadata
  and labels are refreshed for `1.0.0`. Base Python and VSIX npm audit results
  are zero; MinerU and Marker packaged extras remain empty security holds.
- Final local gates are green: 1,096 Python tests passed (30 intentional optional
  skips), Python 3.10 MCP/preflight/bundle tests passed, Ruff/format/MyPy/Bandit,
  uv/npm audits, docs/harness checks, wheel clean-venv smoke, 154 VSIX tests,
  package audit, and VS Code 1.133 fresh/update activation smoke all passed.
- Independent review additionally fixed LightRAG first-use initialization,
  figure copy/hash TOCTOU, quadratic evidence joins, bounded bundle resources,
  and production factory/worker enforcement of Marker/MinerU security holds.
- The refresh is pushed as three segmented commits. GitHub's default branch,
  Pages source and local tracking now use `main`; remote `master` and every
  obsolete topic branch are removed, and no PR remains open.
- The first `main` CI isolated a Windows-only single-quoted Mocha glob; the
  portable command and regression then passed replacement CI, all three OS
  smoke jobs, the fail-closed aggregate gate, and the first `main:/docs` Pages
  deployment.
- `main` now requires the strict `📋 Test Summary`, one approval, resolved review
  conversations and linear history, and rejects force-push/deletion. The
  annotated `v1.0.0` tag resolves exactly to green `main@183bbeb`.
- The tag-triggered Release workflow passed all eight jobs. PyPI 1.0.0,
  Marketplace 1.0.0, GitHub Release/VSIX and Pages are public and were verified
  from their actual bytes/endpoints; final wheel/sdist/VSIX hashes match their
  independently built or cross-registry counterparts.
- The standalone GitHub Wiki now mirrors v1 `docs/wiki` (5 new pages, 14 updated,
  no deletions), with a recovery tag on its prior SHA. The old v0.2.0 draft was
  deliberately retained after exact inspection found a valid historical tag and
  unique VSIX asset; provenance took priority over cosmetic cleanup.
- The v1 goal is complete. Future work is maintenance and adding explicit
  DOCX/general repository adapters to the reusable-asset contract, not reopening
  MCP SDK v1 or the held MinerU/Marker dependency chains.

## 2026-05-17 - v0.7.0 structural readiness and A2T production hardening

- Release scope: publish `0.7.0` as the larger production-hardening release
  after multi-subagent review of A2T, document readiness, structural retrieval,
  install/runtime portability, and release packaging.
- Document facade scope: `document(op="safety_audit")`,
  `document(op="native_structure")`, `document(op="coverage")`, and
  `document(op="accessibility")` now stay inside the existing facade surface;
  `document(op="pointer_index")`, `document(op="structural_retrieve")`, and
  `document(op="compare")` add Proxy-Pointer-inspired retrieval/comparison
  without increasing public tool count.
- Readiness scope: `DocumentReadinessService` is the single read-only contract
  for `prepare_ai`, including status/blockers/warnings/capabilities/artifacts,
  `missing_audits`, `invalid_audits`, `audit_artifacts`, and next actions.
  Cached audit artifacts with `skipped`/`unavailable` status or stale source
  revision/locator hashes are blockers and are rebuilt by `document(op="audit")`
  unless explicitly refreshed globally.
- A2T scope: stable row IDs, row provenance, row-id citation targeting, large
  table startup skip metadata, `query_rows` paging/search/filter/coverage,
  `table_cite(op="coverage")`, and artifact-only render hashes/previews are in
  the 0.7.0 surface.
- Verification so far: focused 0.7.0 document/pointer/A2T regression suite
  passed (`171 passed`), focused Ruff passed, and mypy passed on the touched
  document readiness/pointer/tool files. Full release gates, Docker/OOM smoke,
  VSIX package, push, and annotated tag remain pending.

## 2026-05-17 - v0.6.36 balanced tool surface and runtime portability release prep

- Release scope: publish the balanced MCP tool surface as the default runtime
  contract: 30 public tools for Cline/Codex/Copilot, compact 17-facade mode for
  strict allow-lists, and legacy 63-tool compatibility for older direct-tool
  clients.
- Runtime/install scope: VSIX prepare/launch paths now use version-pinned
  `uv tool run`, quote paths safely for terminals, preserve workspace-scoped
  `DATA_DIR`/`UV_CACHE_DIR`, and try Python 3.11 before Python 3.10 so older
  Windows/macOS machines have a fallback.
- A2T scope: table service behavior is tightened around cell validation,
  duplicate column renames, citation cleanup, persisted draft timestamps, and
  `table_history` shortcut ergonomics. Follow-up product design remains stable
  row IDs, large-table paging/chunking, artifact-only mode, richer provenance,
  and row search/filter/coverage tools.
- Document readiness hardening scope: `DocumentReadinessService` now owns the
  AI-readiness artifact registry and v2 payload contract. `document(op="prepare_ai",
  output_format="json")` returns `status` / `blockers` / `warnings` /
  `capabilities` / `artifacts` / `next_actions`; `document(op="audit")` skips
  current safety/native/coverage artifacts unless `refresh=true`; job-status
  artifact discovery is read-only and does not create document directories.
- Documentation/release scope: README, README.zh-TW, VSIX README, wiki source,
  generated docs site payload, count scripts, assistant harness assets,
  CHANGELOG, and Memory Bank are being aligned to `0.6.36` and the balanced
  30-tool / 13-resource / 43-public-endpoint story before segmented git
  commits, push, and tag.
- Verification target before tag: Python lint/format/mypy/full pytest, docs-site
  check, runtime surface counts, VSIX `npm run test:ci`, asset sync check,
  package/build smoke, artifact audit, and git diff hygiene.

## 2026-05-16 - v0.6.35 emergency OOM hotfix release prep

- Emergency scope: Cline/stdio OOM prevention for simple document extraction,
  DOCX/DFM reads, section/table/KG/job/citation payloads, plus VSIX-managed MCP
  launch safety. The hotfix adds bounded MCP text/JSON/image responses, artifact
  references for oversized payloads, table startup load caps, lazy optional-heavy
  imports, subprocess worker startup minimization, and streaming/manifest-safe
  document flows.
- VSIX/Cline/Copilot/Codex launch configs now inject conservative safety env:
  `ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS=12000`,
  `ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS=750000`, and
  `ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES=20971520`. Existing managed custom
  env such as `HTTP_PROXY` and `SSL_CERT_FILE` is preserved while stale unsafe
  OOM guard values are overwritten.
- Release hardening: install smoke runtime diagnostics now isolate uv
  `DATA_DIR`/`UV_CACHE_DIR` and use `--isolated`; retired LLM wiki harness text
  was removed; docs/site version drift was fixed; VSIX repo-assets were synced.
- User-requested OpenRouter preset is now in scope for the same release: VSIX
  settings expose `openrouter` as an LLM backend, local `OPENROUTER_API_KEY`,
  OpenRouter base URL/model fields, a fast/free preset button for
  `liquid/lfm-2.5-1.2b-instruct:free`, and Ollama CPU/GPU model preset
  selection. Runtime uses OpenRouter for chat/summary/RAG answer generation
  while keeping LightRAG retrieval embeddings on the configured embedding path.
- Version target is **0.6.35** because `v0.6.34` already exists locally and on
  origin. `pyproject.toml`, `src/__init__.py`, `Dockerfile`,
  `vscode-extension/package.json`, `package-lock.json`, docs source, generated
  docs site payload, CHANGELOG, and Memory Bank are aligned for the tag.
- Verification before tagging: focused OpenRouter/Python tests passed (`7
  passed`), full Python suite passed earlier in the hotfix cycle (`919 passed,
  23 skipped`), VSIX `npm run test:ci` passed (`138 passing`), default VSIX
  install/update smoke passed, `uv build` produced 0.6.35 wheel/sdist, VSIX
  package produced `asset-aware-mcp-0.6.35.vsix`, release harness/docs/sync
  checks passed, and `git diff --check` had only LF/CRLF warnings. Per the
  user's fast-release instruction on 2026-05-16, no additional full-suite rerun
  and no Docker smoke are required for the final publish step. The isolated
  `uvx --from .` stdio smoke attempted a network dependency resolve and was
  stopped when the user switched to fast publish; CI/release should cover the
  remote resolver path after publication.
- Post-push release correction: the first `v0.6.35` tag run failed before
  artifact publication because root LLM wiki harness files still carried retired
  Zotero/PubMed wording while VSIX repo-assets had the corrected Asset-Aware
  copies. Root source harness files were corrected, with targeted verification:
  `test_llm_wiki_harness_stays_asset_aware_scoped` passed and VSIX
  `sync-assets:check` passed. The failed tag is being retargeted to this source
  fix before publication proceeds.

## 2026-05-15 — v0.6.34 release: GPT subagent review + source-mode install fix

- Ran a 3-agent parallel `reviewer-openai` code review of the dependency slim-down. 3 findings:
  1. **REAL BUG (FIXED)** — `installOptionalExtra` in `vscode-extension/src/extension.ts` always emitted `uv tool install --upgrade --python 3.11 'asset-aware-mcp[lightrag]==<version>'`, but when the extension launches from a local source checkout (`uv run --directory <repo> python -m src.server`), the active venv is the workspace `.venv`, **not** the `uv tool` env. Install would succeed and have zero effect on the running server. Fixed by detecting `findLocalAssetAwareSource(workspaceRoot, workspaceRoot)` and branching to `uv sync --extra <extra>` (with terminal cwd = source root) when local source is detected. Modal now shows the chosen mode + exact command. `uv tool install` path retained for published/uvx installs.
  2. **STALE ERROR TEXT (FIXED)** — `src/infrastructure/lightrag_adapter.py` `_validate_lightrag_hku_distribution()` and the lazy `_get_or_create_rag` ImportError catch both emitted pre-extra `uv sync` instructions. Updated to `uv tool install --upgrade 'asset-aware-mcp[lightrag]'` (primary) with `uv sync --extra lightrag` as the source-checkout fallback.
  3. **NON-BUG (DOCUMENTED)** — `clineMcpConfig.ts::isCrossWorkspaceDataDirChange` final `return` is logically unreachable, but inline comment + `clineMcpConfig.test.ts` ("auto-tracks the current workspace DATA_DIR even if a previous workspace was installed") confirm the intent: tracking the active workspace is the only sane default. Behavior matches intent; left as-is.
- Documented optional `[lightrag]` extra + `Install LightRAG Backend` command in `README.md`, `docs/wiki/Knowledge-Graph.md`, and `vscode-extension/README.md` so users know they must opt in before flipping `ENABLE_LIGHTRAG=true`.
- Version bumped 0.6.33 → **0.6.34** across `pyproject.toml`, `src/__init__.py`, `Dockerfile`, `vscode-extension/package.json` + `package-lock.json`, `scripts/build_docs_site.py`, `docs/wiki/*`, `docs/site.js`, regenerated `docs/site-content.js` + `docs/site-content/*.md` + `docs/index.html` via `python scripts/build_docs_site.py`. `uv lock` updated (`0.6.33 -> 0.6.34`, 116 packages resolved). VSIX `npm run sync-assets` propagated harness changes into `vscode-extension/resources/repo-assets/**`.
- Verification: VSIX `npm run lint` clean, `npm run test:unit` 131 passing, Python `pytest tests/unit/test_lightrag_adapter.py test_config_defaults.py test_cli.py` 11 passed + 1 skipped (numpy unavailable in slim venv, expected).

## 2026-05-15 - Dependency slim-down + optional-extra install commands

- Slimmed default install footprint from **~1190 MB** to **~227 MB** (~963 MB saved). Achieved by moving `lightrag-hku` to a new `[lightrag]` optional extra and removing the unused `mistralai` dependency entirely (zero usages in src/tests/scripts confirmed). Old marker-pdf + torch + transformers + surya-ocr + scipy + sklearn + sympy + cv2 + pandas remnants from previous installs were dropped by `uv sync` after `uv lock` regeneration.
- Restructured `pyproject.toml` `dependencies` into a documented **core runtime** tier and a **security-floor pins** tier so transitive CVE mins (aiohttp, cryptography, protobuf, pyasn1, PyJWT, python-multipart, urllib3) stay traceable.
- Added two VS Code commands for menu-driven optional install: `Asset-Aware MCP: Install LightRAG Backend (optional)` and `Asset-Aware MCP: Install Marker Backend (optional)`. LightRAG opens a terminal and runs `uv tool install --upgrade --python 3.11 'asset-aware-mcp[lightrag]==<version>'`. Marker shows a modal with the security-hold notice + links to upstream tracker and Pillow CVE notes.
- Verified safety: `src/infrastructure/__init__.py` already guards `LightRAGAdapter` import with try/except, `_HAS_LIGHTRAG` flag is False when missing; `dependencies.py` lazy-builds adapter only when `enable_lightrag=true` and now points users at the new install paths in its error message.
- Verification: VSIX `npm run lint` clean, `npm run test:unit` 131 passing, Python `pytest tests/unit` 708 passed + 2 skipped (1 pre-existing failure in `test_cline_harness_boundaries.py` is unrelated to this work — caused by in-flight unstaged edits to `.cline/skills/llm-wiki-builder/SKILL.md` etc.). Core runtime imports (`src.presentation.server`, `FileStorage`) clean. `test_lightrag_adapter.py` updated to `pytest.importorskip('numpy')` + `pytest.importorskip('lightrag')` so it auto-skips on slim installs.

## 2026-05-15 - v0.6.33 Cline/MCP release readiness

- Release scope is `v0.6.33` on `master`. The release is centered on Cline install correctness, safe default local RAG settings, docs-site productization, and a full production smoke pass before push/tag.
- Multi-subagent cross-check focused on Cline config merge/install behavior, MCP runtime startup, VSIX assistant asset packaging, release gate coverage, and stale harness drift. The main blocker found was LLM wiki harness text drifting back to retired Zotero/PubMed workflow ownership; it was restored to Asset-Aware document evidence, citation bundles, and optional KG/Foam flows, then synced into VSIX repo-assets.
- Local RAG defaults are pinned and CPU-safe: `OLLAMA_MODEL=granite4.1:3b` by default, GPU-hinted installs use `granite4.1:8b`, and `ENABLE_LIGHTRAG=false` keeps KG/embedding work opt-in. VSIX and Python tests cover explicit overrides, GPU hints, and the "embedding model only when KG is enabled" behavior.
- Cline readiness checks now cover readable Traditional Chinese `mcpRules` triggers, non-destructive Cline MCP settings merge, preservation of `alwaysAllow`, `disabled`, custom env and unrelated servers, cross-workspace `DATA_DIR` guards, and direct stdio smoke from the generated launch command.
- Fresh release gates passed for this candidate: Ruff, format, MyPy, `uv lock --check`, docs-site build check, JS syntax, release harness audit, Cline harness boundary tests, VSIX `sync-assets:check`, full `uv run pytest -q` (`903 passed, 22 skipped`), VSIX `test:ci` (`130 passing` plus package contents), VSIX install/update/activation smoke, `uv build`, release artifact audit, built-wheel runtime and MCP stdio smoke, local stdio MCP smoke, VSIX package, Docker build, Docker `doctor`, Docker `list-tools`, and Docker stdio MCP smoke. Docker passed on this host; no release waiver is needed.
- `uv build` initially hit the host/network/cache path during the release run, then succeeded using the workspace `data/uv-cache`. The generated artifacts are ignored build outputs and must not be committed: `dist/asset_aware_mcp-0.6.33.*`, `vscode-extension/asset-aware-mcp-0.6.33.vsix`, `vscode-extension/out/`, and `data/`.

## 2026-05-14 - v0.6.32 repo health and release prep

- Release scope is `v0.6.32` on `master`, following the `v0.6.31` tag. The work focuses on production-readiness before push/tag: oversized source/test modules were split, stale VSIX-installed harness leftovers and orphan/generated files were cleaned, and the release smoke gates were expanded around built wheels, stdio MCP startup, Docker, VSIX install/update, and release artifact audits.
- All tracked source/test files over 2000 lines were refactored into smaller modules while preserving public MCP tools and monkeypatch/import compatibility: document tools gained `document_evidence_support.py`, `DocumentService` gained markdown/page-scope helpers, `DocxAdapter` gained OpenXML/writeback helpers, and the old MCP tool-layer test monolith was split into focused test modules.
- KG/Foam behavior remains a first-class release surface: `citation_bundle(output_format="foam")`, `document_asset(op="foam_notes")`, `evidence(op="health")`, and claim-promotion workflows are covered by focused tests and practical smoke coverage so wiki links, anchors, embedded AssetRefs, and verification payloads stay auditable.
- Local RAG defaults changed for the release candidate: Ollama LLM now defaults to pinned `granite4.1:3b` on CPU and `granite4.1:8b` when GPU hints are enabled, while LightRAG/KG is opt-in (`ENABLE_LIGHTRAG=false`) so CPU-only or document-only installs do not require KG dependencies or embedding models.
- Assistant harness assets are Asset-Aware-scoped again after removing retired Zotero/PubMed/academic-figure leftovers from the bundled source and VSIX repo-assets. `npm run sync-assets` must stay clean before packaging the VSIX.
- Fresh non-Docker release verification passed after the Granite/KG default change: Ruff, format, MyPy, `uv lock --check`, docs-site check, release harness audit, VSIX asset sync check, full pytest (`887 passed, 22 skipped`), VSIX `test:ci` (`125 passing` plus package contents), Python/VSIX packaging, release artifact audit, built-wheel runtime/stdout MCP smoke, and VSIX install/update smoke. Docker build was explicitly stopped by the user because it hangs in this environment and is waived for this local release run.

## 2026-05-11 - v0.6.29 DFM/citation-ready release prep

- Multi-subagent review confirmed DFM is correct for the supported mainline: DOCX/DOC ingest, DocxIR/DFM/split Markdown+YAML, no-op/text/existing-table-cell edits, `save_docx`, strict validation, and layout smoke. The boundary remains explicit: arbitrary Word structural edits and legacy `.doc` source-conversion layout drift are not claimed as fully solved.
- Multi-subagent review confirmed citation-ready is usable as a core loop: PDF span -> AssetRef -> verification -> bundle/Foam -> health check -> claim promotion. The strongest remaining product direction is making Foam/wiki promotion more durable and reviewable.
- Release scope moved to `0.6.29` because `v0.6.28` is already tagged. Version files, README/VSIX README, changelog, wiki source, GitHub Pages payload, and Memory Bank are aligned to `0.6.29`.
- Citation-ready was strengthened once more before release: Foam claim promotion notes now keep the original AssetRef JSON and an explicit Verification Payload JSON fence, so wiki-layer promotion can preserve full verification evidence while still failing closed before writes.
- Release harness audit is now clean after restoring local skip-worktree LLM wiki harness files to the tracked Asset-Aware-scoped wording and moving untracked retired Zotero/PubMed harness leftovers to `/tmp/asset-aware-retired-harness-backup-20260511T164609Z`.
- Release gates passed for the `0.6.29` candidate: Ruff, format, MyPy, `uv lock --check`, full pytest (`840 passed, 21 skipped`), docs site check, JS syntax, release harness audit, tool count, VSIX sync-assets, VSIX `test:ci` (`119 passing` plus package contents), VSIX install/update smoke, `uv build`, VSIX package, artifact audit, Docker build/import smoke, and `git diff --check`.
- Docker smoke required one compatibility fix: the production Dockerfile no longer depends on BuildKit cache mounts, so hosts without `docker buildx` can complete the release build.

## 2026-05-11 - Real IRB folder DOCX/PDF round-trip smoke

- Ran a real Asset-Aware smoke over `/home/eric/workspace251226/asset-aware-mcp/一般案-新案2025.00 (20250520)_20260128R` with 26 files: 18 DOCX, 5 legacy DOC, and 3 PDF. Original source hashes/mtimes were preserved; all generated artifacts live under `tmp/asset_aware_real_roundtrip_20260511T144132Z`.
- Initial result: 16/23 Word-like files passed strict validator + LibreOffice PDF raster layout checks; 2 failed save guards, 2 failed strict validator, 3 had validator-pass layout diffs, and 1 PDF content DOCX conversion failed despite complete ETL artifacts.
- Fixed the reproduced root causes: Markdown table blank rows are no longer mistaken for separator rows, split-format break blocks are protected/non-editable, terminal line-break normalization no longer creates false expected edits, break-only runs no longer receive duplicate `\n` text, and PDF->DOCX image embedding re-encodes python-docx-unrecognized JPEG headers through PNG.
- Targeted fix verification over the previously failing real files passed: `02`, `06-3`, `12`, `17`, and `18` all reached strict 100.0 with layout max mean diff `0.0`; `※審查費繳費單下載相關公告...pdf` now converts to content DOCX with one embedded figure. Fix-check artifacts live under `tmp/asset_aware_real_roundtrip_fixcheck_20260511T150045Z`.
- Full after-fix real-folder run over all 26 files passed source-integrity checks (`changed_count=0`): 18 DOCX reached strict 100.0 and layout diff `0.0`, all 5 legacy DOC files reached strict 100.0, and the two remaining layout warnings are isolated to `.doc` source-to-LibreOffice conversion baseline drift while converted-DOCX-to-IR rebuild diff is `0.0`. All 3 PDFs passed artifact/citation checks with citation lines carrying locator/hash/context/offset fields.
- Citation-ready provenance was strengthened so PDF manifests now persist root-level `source_pdf_sha256` plus `selected_page_map`, separating the original PDF byte identity from markdown/citation locator hashes.
- Foam/LLM wiki promotion support now lives on the existing evidence bundle path: `citation_bundle(output_format="foam", citation_key="...")` emits a Foam-compatible evidence pack with YAML frontmatter, `^spn-...` anchors, wikilink/embed strings, verification status, locator hashes, and embedded AssetRef JSON. `evidence(op="bundle", output_format="foam", citation_key="...")` routes to the same exporter.
- Foam promotion moved from export-only to wiki-maintenance capable: `citation_bundle(..., wiki_root=..., output_path=..., index_path=...)` writes the evidence pack under the Foam root and updates a managed evidence index block; `evidence(op="health", wiki_root=...)` scans Markdown notes for embedded span AssetRefs and `[[note#^spn-...]]` links, then reports stale/mismatched refs and missing target notes/anchors.
- Table/Figure Foam notes now hang off `document_asset(op="foam_notes", ...)`: manifest table/figure assets become `table_evidence` / `figure_evidence` notes with source block/order, line span, section context, source PDF hash, asset locator hash, and embedded table/figure AssetRef JSON. Foam health now validates span/table/figure refs and generic `[[note#^...]]` anchors.
- DOCX DFM blocks now carry Word-origin locator metadata in `DfmBlock.metadata`: `locator_version=docx-dfm-locator-v1`, `source_part`, `source_story`, `source_element`, paragraph/table/source indexes, run ranges, text char/byte/hash locator, and table cell locators; `get_docx_content(block_id=...)`, `list_docx_blocks`, split `format.yaml`, and Track Changes `revisions.jsonl` expose the locator so Word forms can be promoted/audited closer to PDF spans.
- Claim promotion workflow is now available through `evidence(op="claim_promotion" | "claims" | "promote_claims", ...)`: it proposes exact-quote claim candidates with embedded AssetRefs and Foam anchors, and Foam writes are blocked unless every candidate verifies against the current citation index.
- Regression validation is tracked through the split MCP tool-layer modules (`tests/unit/test_mcp_docx_tools.py`, `tests/unit/test_mcp_job_tools.py`, `tests/unit/test_mcp_document_tools.py`, `tests/unit/test_mcp_table_tools.py`, `tests/unit/test_mcp_profile_tools.py`, `tests/unit/test_mcp_knowledge_tools.py`, `tests/unit/test_mcp_server_startup.py`, `tests/unit/test_job_service_concurrency.py`, and `tests/unit/test_pdf_validation.py`) plus focused DOCX/citation/docs gates.

## 2026-05-11 - v0.6.28 feature release prep

- Preparing `v0.6.28` from `master` after adding six requested capability refinements: conversion background jobs, verified citation bundle export, KG answers with verified evidence, DOCX table structural edit plans, ETL profile auto-detect, and a VSIX artifact/citation viewer.
- Current endpoint inventory is 62 tools in 7 modules and 13 resources in 2 modules, 75 MCP endpoints total.
- Focused validation has passed for the new Python tools and services, MCP tool registration/counts, VSIX EnvManager and DocumentTreeProvider behavior, TypeScript compile/lint/unit slices, Ruff checks, and formatting on changed Python files.
- Docs/site/MEM are aligned to `0.6.28`, refreshed wiki assets are regenerated, and local release gates pass for Python, docs, VSIX unit/package, build artifacts, and release audits.
- Remaining environment caveats before publication are host-level only: VSIX install smoke is blocked by missing `libgbm.so.1` when using downloaded VS Code and by a hanging remote `code-insiders` CLI, while Docker smoke is blocked by missing Docker buildx/BuildKit support.

## 2026-05-11 - Git harness hygiene and wiki documentation setup

- Follow-up multi-subagent documentation alignment completed after the human-facing docs site was reviewed against the actual code. Corrections were made for MCP tool/resource contracts, `knowledge-graph://summary`, PDF artifact names (`{doc_id}_full.md`, `{doc_id}_manifest.json`, `citation_index.jsonl`), background-job/conversion boundaries, DOCX/DFM supported formats and safe-write limits, A2T `resume`, ETL profile activation semantics, Knowledge Graph response modes/timeouts, VSIX runtime cache behavior, assistant asset sync scope, and Code Map coverage.
- Added `tests/unit/test_docs_site_reference_sync.py` so `docs/wiki/MCP-Tools.md` and `docs/wiki/MCP-Resources.md` are checked against the actual `@mcp.tool()` / `@mcp.resource()` decorators, including resource URI strings and Start Here navigation order.
- Regenerated `docs/site-content.js` and `docs/site-content/*.md` from `docs/wiki/**`; validation passed for docs builder `--check`, JS syntax, linked wiki images, stale-string scan, ruff on changed Python files, `git diff --check`, `./scripts/count_tools.sh`, and focused docs/count tests.
- Main worktree was fast-forwarded from the stale local checkout to `origin/master` / `v0.6.27`; four older VSIX-installed LLM wiki harness files were moved to `/tmp/asset-aware-harness-backup-20260511091421` before the fast-forward because the same paths are now tracked upstream.
- VSIX-managed assistant harness source paths were marked local-only with `git update-index --skip-worktree` to keep automatic extension sync from dirtying normal feature work: `AGENTS.md`, `.github/copilot-instructions.md`, `.github/agents`, `.github/bylaws`, `.claude/skills`, `.cline/skills`, `.codex/skills`, and `.clinerules`.
- `scripts/count_tools.sh` and `scripts/count_tools.ps1` were fixed to skip helper modules with zero MCP endpoints; focused regression coverage now lives in `tests/unit/test_count_tools_script.py`.
- Endpoint inventory from the repaired script was 59 tools in 7 modules and 13 resources in 2 modules, 72 MCP endpoints total before the later `0.6.28` feature additions.
- A full GitHub Wiki page set was authored in `/tmp/asset-aware-mcp.wiki` and mirrored into `docs/wiki/` for versioned source control. The page set includes Home, sidebar, architecture, all MCP tools/resources, PDF/DOCX/A2T/KG/jobs/profiles workflows, VSIX setup, Git harness hygiene, developer/release guide, and code map.
- Existing docs diagrams were reviewed as source material, but several embedded stale counts/versions such as `48 tools` made them unsafe for the current wiki. A new web-sized diagram batch was generated with Pillow under `docs/wiki/assets/`, covering architecture, endpoint map, PDF, DOCX/DFM, citation provenance, A2T, knowledge graph, jobs, ETL profiles, VSIX setup, and Git harness hygiene.
- After the GitHub Wiki was initialized, `/tmp/asset-aware-mcp.wiki` was merged with the remote initial page using `--allow-unrelated-histories` and pushed to `asset-aware-mcp.wiki.git`; remote `master` now points at `d6b3a17`.
- GitHub Wiki verification passed: the root wiki URL returns HTTP 200, `_pages` lists the generated pages, representative pages such as `MCP-Tools`, `PDF-Document-Workflow`, `DOCX-DFM-Workflow`, `VS-Code-Extension-And-MCP-Setup`, `Git-Harness-Hygiene`, and `Code-Map` return HTTP 200, and the raw `overview-architecture.jpg` asset returns HTTP 200 as `image/jpeg`.
- A PubMed-style GitHub Pages documentation site now lives under `docs/` and is published from `master` `/docs` at `https://u9401066.github.io/asset-aware-mcp/#/overview-zh`. The site uses `docs/index.html`, `docs/site.css`, `docs/site.js`, generated `docs/site-content.js`, and generated `docs/site-content/*.md`; `scripts/build_docs_site.py --check` is wired into CI docs-check to keep the site payload aligned with `docs/wiki/**`.
- The docs site was refined for human readers: Home now starts with task-oriented path cards, `Design-And-UX.md` documents audience, information architecture, page rhythm, UI choices, visual direction, and completeness criteria, and the CSS palette was adjusted away from the earlier single warm/green note. Main repo `master` contains `27aca29`; GitHub Wiki `master` contains `404b640`.

## 2026-05-08 - v0.6.27 security and release hygiene patch

- Preparing `v0.6.27` from a clean worktree on top of `v0.6.26` after prerelease audit found runtime dependency CVEs, Marker/Pillow resolver conflict, table citation provenance drift, and VSIX package guard gaps.
- Default runtime dependency floors now require patched image/XML/network/auth packages, including `Pillow>=12.2.0` and `lxml>=6.1.0`.
- Marker extras are intentionally empty in this release because upstream `marker-pdf` 1.10.2 pins `Pillow<11`; the VSIX/local launcher now logs a Marker security hold and does not install `marker-pdf` even if `assetAwareMcp.enableMarkerBackend` is set.
- Table citation AssetRefs now preserve `locator_source_sha256` through serialization/reload, with regression coverage for evidence-span conversion and table persistence.
- VSIX release hygiene now blocks root `dist/`/`tmp/`, generated nested repo-assets, and generated assistant asset directories during sync. Install smoke can be forced to VS Code Insiders with `ASSET_AWARE_MCP_VSCODE_QUALITY=insiders`.
- Main worktree remains intentionally dirty with unrelated LLM-wiki/harness/agent/test artifacts; release staging must happen only from the isolated `asset-aware-mcp-v0.6.27-fix` worktree with exact pathspecs.

## 2026-05-08 - v0.6.26 MCP stdio ingest hotfix

- Preparing `v0.6.26` as a patch on top of the already-pushed `v0.6.25` tag after a Codex-style stdio MCP smoke found that `ingest_documents(async_mode=False, use_marker=False)` could still block on Windows PyMuPDF document-level extractor timeouts.
- The MCP presentation layer now treats `async_mode=False` for PDF ingest as backwards-compatible input only; all PDF ingest requests return a background job so Cline/Codex/VS Code stdio clients stay responsive.
- Regression coverage now asserts that sync MCP PDF ingest creates a job, preserves job parameters, skips page-count probes, and never calls inline `document_service.ingest()`.
- Validation includes focused MCP tool tests, ruff, format, mypy, and a Codex-style stdio MCP client smoke covering initialize, tools/list, `ingest_documents`, `parse_pdf_structure`, `ocr_pdf_document`, disabled knowledge graph responses, and job cancellation.
- Main worktree full pytest is intentionally polluted by unrelated LLM-wiki/retired harness files; release verification must run from a clean worktree or exact staged scope so those harness drafts are not mixed into the hotfix.

## 2026-05-08 - v0.6.25 stability release prep

- Preparing `v0.6.25` as a scoped stability release after the Cline timeout and VSIX activation fixes were validated locally.
- MCP request responsiveness is the release focus: `parse_pdf_structure` and `ocr_pdf_document` now always return background jobs, synchronous ingest fails closed to a background job when LightRAG indexing would block, and knowledge graph query/export tools have request-level timeout guards.
- Isolated ingest worker behavior is hardened with presentation-owned worker entrypoint composition, application-layer worker helpers only, per-file logs, traceback capture, heartbeat/progress updates, and visible failed-job warnings.
- Citation-ready Marker fallback is improved with markdown block synthesis, citation status files, and helper modules split out of `document_service.py` and `document_tools.py`.
- The DDD boundary is improved by introducing an `IngestWorkerRunner` application port and a subprocess infrastructure adapter, keeping subprocess/env/log runner details out of `JobService`.
- DOCX/table safety is included in this release: strict validation now covers header/footer/footnote story parts and table-cell direct formatting, while table persistence is atomic.
- VSIX smoke coverage now verifies installed-extension activation and MCP provider definition, with runtime preparation using extension-storage `UV_CACHE_DIR` and avoiding `ELECTRON_RUN_AS_NODE=1` leakage into Code.exe.
- Git hygiene goal for this release: use segmented commits and exact pathspecs, leave ad-hoc `.github/agents`, `.pytest-tmp`, `.vscode-test`, PDFs, and unrelated LLM wiki harness sync files out of the release unless explicitly staged later.

## 2026-05-07 - v0.6.24 Cline worker isolation release prep

- Preparing `v0.6.24` after 4 subagents completed 3 review rounds over the Cline failure path, job lifecycle, document ingestion, and release pipeline.
- Marker-backed background jobs now use `src.application.ingest_worker` in an isolated subprocess with stdin/stdout/stderr closed, so Cline can keep calling `get_job_status` and `cancel_job` while Marker parses.
- `parse_pdf_structure(async_mode=True)` now carries `require_marker=True` and fails closed without writing PyMuPDF fallback artifacts when Marker structure is required.
- Job results now include per-document backend, warnings, artifacts, degraded state, and next-step commands; Cline no longer has to infer whether a Marker job actually degraded to PyMuPDF.
- Job cancellation, stale active job reconciliation, and ETL profile isolation were hardened with regression tests.
- Local Cline install now preserves cross-workspace `DATA_DIR` unless `--force-workspace` is explicit.
- Release workflow now guards PyPI reruns, VS Code Marketplace retry/visibility, wheel/sdist required runtime files, VSIX bundled `count_tools.ps1`, and precise release staging without `git add -A`.
- Verification so far: `ruff`, full `uv run pytest -q` (`781 passed, 19 skipped`), VSIX `npm run test:ci`, sync-assets check, release harness audit, `uv build`, artifact audit, `count_tools.ps1`, and `git diff --check` all passed.

## 2026-05-07 - v0.6.23 Cline / Marker corrective release

- Preparing `v0.6.23` as the second Cline corrective patch after multi-agent review found that Marker model loading and synchronous PDF parsing could still exceed Cline request budgets.
- Marker-backed `parse_pdf_structure` and `ingest_documents` now default to background jobs, with explicit synchronous diagnostics guarded by page/file-size checks.
- Generated Cline and VS Code MCP launch environments suppress noisy Marker stdout/stderr and preserve diagnostics in a workspace `logs/marker.log` file.
- Background job creation/cancellation/store writes are hardened against quota races, orphan tasks, unsafe IDs, and partial JSON writes.
- LightRAG/Ollama integration now validates the expected `lightrag-hku` distribution, uses batch Ollama embeddings with legacy fallback, and exposes timeout knobs.
- `save_docx` now surfaces skipped pending TableContext merge warnings; segmentation fallback warnings are visible in MCP output.
- Release gates for this patch must cover full Python checks, Cline skill audit, release harness audit, sync-assets, VSIX `test:ci`, install smoke, Docker smoke, artifact audit, git push, and `v0.6.23` tag publication.

> 📌 當前工作焦點和進行中的變更

## Current Goals

- 多引擎 PDF→資產 ETL 導入完成（PyMuPDF4LLM / Docling / MinerU），取代因 marker-pdf pin Pillow<11 與安全基線（Pillow>=12.2.0）衝突而停用的 Marker。透過 ETL_ENGINE 環境變數選擇引擎（預設 pymupdf）；結構化引擎懶加載、未安裝自動降級為 PyMuPDF。設計亮點：Docling/MinerU 輸出 Marker-compatible MarkerParseResult，零侵入復用現有 _ingest_single_with_marker 資產管線；document_service 的 marker_extractor slot 僅泛化型別為 StructuredPDFExtractor Protocol、保留名稱以維持 API/測試相容。全部驗證通過（1018 測試 / 0 失敗、ruff + mypy 乾淨、引擎選擇與降級冒煙測試 OK）。變更尚未 commit。

## 🎯 當前焦點

- **版本真相為 0.7.0**：本次 release 是 0.6.x 之後的大型 production-hardening refactor，不重用既有 tag。
- **DFM 主線結論**：支援範圍內可正確進行 DFM 拆解與重組；文件與 release notes 必須保留 `.doc` conversion drift、結構性表格變更、header/footer/footnote locator 測試深度等邊界。
- **Citation-ready 主線結論**：EvidenceSpan / AssetRef / verify / bundle / Foam / health / claim promotion 已可用；CRAAP 仍是保守 scaffold，不可宣稱已完成 source quality 評分。
- **Git policy**：只 stage tracked source/docs/test/version changes；`tmp/`、真實 IRB source folder、`dist/`、VSIX artifact、runtime cache、ignored data 皆不可提交。
- **Release blockers**：若 VSIX install smoke 或 Docker smoke 因 host-level dependency 失敗，必須記錄為環境阻塞；不把 generated artifacts 或 real corpus outputs 混入 release。

## 🆕 ETL / Layout / OCR 可視化 (2026-03-18)

- `src/domain/segmentation.py`：新增 `DocumentSegment` / `DocumentSegmentation`
- `src/application/segmentation_service.py`：整合 manifest + blocks + assets + reading order，輸出 `segmentation.json`
- `segmentation.json` 現在同時保留 `reading_order` 與 `line_start` / `line_end`，可用於內容流理解與精準行號引用
- `src/domain/line_spans.py`：新增 page-aware / section-aware line span index，對重複句子會先在 page 與 section 範圍內定位
- `blocks.json` 現在會持久化 `line_start` / `line_end` / `line_match_strategy` 等 metadata；舊資料在 export segmentation 時會自動 backfill
- `fetch_document_asset` 現在直接回傳 asset 的 line range、section、source block，減少 agent 端額外查詢成本
- `FigureAsset` / `TableAsset` 追加 `source_block_id` / `source_order`，segmentation 會優先按來源 block 身分配對，避免同頁多資產錯配
- `src/infrastructure/layout_visualizer.py`：以 `original.pdf` 或白底畫布渲染 bbox overlay
- `src/infrastructure/ocr_processor.py`：封裝 `ocrmypdf`，支援 `language` / `rotate_pages` / `deskew`
- `DocumentService`：每次 ingest 會覆蓋保存最新 `original.pdf`，可選 OCR 後再進 ETL；`JobService` step 數跟隨 OCR 階段
- `document_tools.py`：新增 `export_document_segmentation`、`visualize_document_layout`、`ocr_pdf_document`
- `document_resources.py`：新增 `document://{doc_id}/segmentation`
- `vscode-extension`：Documents tree 相容新 manifest 結構，並顯示 segmentation 與 ETL jobs 概況
- 驗證結果：`uv run pytest tests/unit -q` → 384 passed；`npm run compile` 通過

## 🆕 Reading Order 與行號並存 (2026-03-18)

- `src/domain/reading_order.py`：新增顯式 `ReadingOrderPolicy`
- policy 不取代 line-level citation；`DocumentSegment` 另存 `line_start` / `line_end`
- 排序依據分離為兩軸：
    - `reading_order`：回答「內容應該怎麼讀」
    - `line_start/end`：回答「這段資訊在 markdown 第幾行」
- Marker block metadata 會保存 `source_order`，segmentation 匯出時再套用 type/caption/non-text policy
- 驗證結果：`uv run pytest tests/unit -q` → 379 passed

## 🆕 MCP Progress / Logging (2026-03-18)

- `src/presentation/mcp_context.py`：封裝安全 progress/log helper
- `DocumentService.ingest()`：新增可選 progress callback，提供每個檔案內部 phase 訊號
- `JobService`：改接真實 ingest phase，不再手動模擬 job 階段
- 已接入 progress 的工具：
    - PDF：`ingest_documents`、`parse_pdf_structure`、`convert_pdf_to_docx`
    - DOCX：`ingest_docx`、`save_docx`、`convert_docx_to_doc`、`convert_docx_to_pdf`、`docx_validate_roundtrip`、`export_markdown`
- 驗證結果：`uv run pytest tests/unit -q` → 368 passed

## 🆕 v0.4.0 新功能

### 文件級 CRUD 與互轉 (2026-03-09)
- `delete_document` / `delete_docx` / `list_docx_documents`
- `convert_docx_to_pdf` / `convert_docx_to_doc` / `convert_pdf_to_docx`
- `scripts/dfm_cli.py` 新增 `to-pdf`、`to-doc`、`validate --strict`

### 保真與安全強化 (2026-03-09)
- `DocxValidator.validate(..., strict=True)` fail-closed 驗證
- `DocxService.save_docx()` 新增 unedited block mutation guard
- Proposal 真實文件通過 DOCX→DFM→DOCX、DOCX→PDF、DOCX→DOC 實戰驗證

## 🛡️ v0.3.3 新功能

### 生產強化 (2026-02-22)
- Dockerfile multi-stage build
- PDF magic byte 驗證
- 並行 Job 上限 MAX_CONCURRENT_JOBS=5
- Structured logging
- 37 個新 MCP 工具層測試

### .doc 格式支援 (2026-02-23)
- `ingest_docx` 自動偵測 `.doc` 格式，透過 LibreOffice 轉換為 `.docx`
- `_convert_doc_to_docx()` — LibreOffice headless 模式轉換

### Markdown 跳脫修復 (2026-02-23)
- `_escape_md()` / `_unescape_md()` — 跳脫 `*`, `~`, `^` 防止文字被誤判為格式標記
- Run 合併優化 — 相鄰相同格式的 runs 先合併再產生 Markdown
- Caption 偵測修正 — 排除 `**...**` bold 模式的誤判
- CLI import path 修正 — `src.application.docx_validator` → `src.infrastructure.docx_validator`

## Docx DFM 系統概要 (v0.3.0)

### 12 個 Docx MCP 工具
| Tool | 類別 | 功能 |
|------|------|------|
| `ingest_docx` | Core | 匯入 .docx → DocxIR → DFM |
| `get_docx_content` | Core | 讀取指定區塊 DFM 內容 |
| `save_docx` | Core | DFM 編輯寫回 .docx |
| `list_docx_blocks` | Core | 列出文件區塊結構 |
| `list_docx_documents` | Core | 列出所有已攝入 DOCX/DFM 文件 |
| `delete_docx` | Core | 刪除已攝入 DOCX/DFM 與本地 artifacts |
| `convert_docx_to_pdf` | Core | 以保真模式輸出 PDF |
| `convert_docx_to_doc` | Core | 以保真模式輸出 DOC |
| `docx_validate_roundtrip` | Validator | 6 維度往返保真驗證 + strict fail-closed |
| `docx_table_to_context` | Bridge | Docx 表格 → A2T 上下文 |
| `docx_table_from_context` | Bridge | A2T 表格 → Docx 表格 |
| `docx_chart_data` | Bridge | 提取 Docx 圖表數據 |

### DocxValidator 6 維度
- 結構 (Structure) / 文字 (Text) / 格式 (Formatting) / 表格 (Table) / 媒體 (Media) / 樣式 (Style)
- 加權評分：text=0.35, structure/format/table=0.15, media/style=0.10
- Emoji 等級：🟢 ≥95% / 🟡 ≥80% / 🟠 ≥60% / 🔴 <60%

## 📁 專案結構

```
src/
├── domain/          # 🔵 核心業務邏輯 (+docx_entities, docx_value_objects)
├── application/     # 🟢 使用案例 (+docx_service, dfm_table_bridge)
├── infrastructure/  # 🟠 外部依賴實作 (+docx_adapter, dfm_parser, dfm_renderer, docx_validator)
└── presentation/    # 🔴 MCP Server (30 balanced public tools, 13 resources; 63 legacy tools)
    ├── tools/
    │   ├── document_tools.py   # ETL + document management (11)
    │   ├── docx_tools.py       # Docx DFM + conversion (16) — core + validator + bridge
    │   ├── section_tools.py    # Navigation (5)
    │   ├── job_tools.py        # Job (4)
    │   ├── knowledge_tools.py  # KG (3)
    │   ├── profile_tools.py    # Profile (6)
    │   └── table_tools.py      # A2T (7) — operation-based
    └── resources/              # 13 resources
```

## 📝 新功能 (v0.3.1)

### 分離格式 (Split Format)
- `content.md` — 乾淨 Markdown，`<!-- @ID -->` 標記（預覽不可見），減少 78% 雜訊
- `format.yaml` — 所有格式元資料（runs, cell_formats, merged_cells…）
- `content.dfm` — 原格式保留（MCP 工具用）

### DFM CLI 工具
- `scripts/dfm_cli.py` — 互動式選單（匯入/開啟/存檔/驗證/列表/一鍵流程）
- `.vscode/tasks.json` — 6 個 VS Code Tasks

### Bug 修復
- `docx_adapter._update_table_text()` — 在更新第一個 run 後清除後續 runs，修復表格文字重複

## ⚗️ 待解決

1. **測試覆蓋率**: 目標 60%+
2. **文件缺乏**: API Reference, Examples, FAQ

---
*Last updated: 2026-04-24*

Final local gates: 1,790 passed / 30 optional skipped; Ruff/format/mypy (158 files),
Bandit, 199 extension tests, 64-file VSIX package, Python build/artifact audits,
docs/harness/18-skill/sync audits all passed. Dependency audits: universal 214
packages and npm lock report zero known vulnerabilities. GH metadata/17 labels
match canonical settings. Playwright 1.63.0 (Browser plugin not available) verifies
http://127.0.0.1:8876/#/native-file-assets and release-testing, desktop 1440x1000 and
mobile 390x844, zh/en, language interactions, no overflow or console warnings.
Screenshots /tmp/native-pptx-pictures-{desktop,mobile}-{zh,en}.png; desktop-en and
mobile-zh visually inspected. Local cached CDN assets used, so CDN reachability is
not covered.
Codex runtime source SHA256 e1f39a4829b26d243f6737a9f91c8e136a3f8c091d7db44a8d84ca7c7a8e50bd
Lock SHA256 abfaddf3d7d964ace1e210b1fd584e1717775a70f8ccdc98ad9b669b61f1bcd3
Local VSIX fresh/update installation passed. Activation was skipped locally (no
xvfb-run), as were absent 0.2.10 baseline and optional runtime diagnostics checks;
CI will require activation. Local Docker image build/import smoke passed, as did
all artifact audits (metadata, wheel/sdist and VSIX). Exact post-push CI/Pages pending.

Runtime/backend/managed/SDK changes committed as e220434 under
u9401066 <u9401066@gap.kmu.edu.tw>. Final documentation, harness, Codex auditor and
platform CI commit is being prepared before a single main push; no release tag.

Final release-check attempt hit an actual full filesystem (43 MiB free) and exited
120 while creating DOCX wiki/test artifacts; it is not counted as a pass. Earlier
full run passed 1,854 tests. Removed only this work's verified Docker check images
(pptx-pictures-check, pptx-tables-check) and completed pytest-176/178 fixture roots
after checking their unique scanned-table tests and excluding live pytest-current.
Source worktrees, Codex run evidence, user files and unrelated images/caches retained.
Recovered ~0.8 GiB; retry /tmp/asset-aware-pptx-tables-release-retry.log completed
successfully: 1,857 passed / 30 optional skips in 56.18s. Failed log retained.
Browser QA passed zh/en desktop/mobile with no errors/overflow; screenshots at
/tmp/native-pptx-tables-{desktop,mobile}-{zh,en}.png, desktop-en/mobile-zh inspected.
Browser plugin unavailable; Playwright 1.63.0 and cached CDN scripts used.
Docker build/import, Python wheel/sdist+VSIX artifact audits, VSIX install/update,
metadata/17 labels and dependency audits passed. Local GUI activation was skipped
(no xvfb-run); CI will enforce it. Public version remains 1.4.0.
