# Progress (Updated: 2026-09-19)

## Native Word notes — validated runtime/spec/tests

Final production e52943694c29f791f85dc267f24901c7df8915e2b314a2e9e9eb8bbdc5d04a62
passes full3384/33optional skips/396.74s with Writer/CJK and fixed NIST/NASA PDFs.
Actual default Codex153successful MCP calls +1recovered contract input error/204.28s
verifies16complete notes,3catalogs,12contracts,3managed revisions,2historical Wikis,
all6actual PNGs with independent pixel replay. No model override. Earlier run
149success+1recovered error/223.72s is retained; final rerun follows a production
fix giving note-only Wiki adapters a distinct projection identity. Full projections
stay byte-compatible. Native IDs differ from displayed numbers; complete source,
formatting, history, receipts, selections and deleted-note evidence remain intact.
SDK2 first render exposed real Writer content/order mismatch; exact failed files
remain in /tmp/pytest-of-eric/pytest-269/test_note_lifecycle_over_sdk2_0. Controlled
probes support inserting a new definition before the following body reference's
existing definition, preserving original IDs/order. No Microsoft Word parity claim.
Python3.10:60pass/1optional skip/23.43s. Clean installed wheel and Docker both replay
16notes/3catalogs/2byte-identical Wikis at the exact final production fingerprint.
Standard pip wheel/import/doctor/30tools/SDK2 smoke pass. Ruff705/mypy297, security,
Python214package audit, both npm audits, artifact/harness/sync and docs25 pass.
VSIX199tests/64files/install-update pass; local GUI activation remains a CI gate.
Browser8desktop/mobile zh/en states pass, actual desktopzh/mobileen inspected;
cached CDN scripts do not establish live CDN availability. Owned server8885 stopped.
Docker f012ea75fb54 and builder dda78ebdf9ba removed; all11 temporarily staged owned
runs restored with exact hashes/mtimes. Privatepy310 retained until CI finishes.
Logs/proof: /run/user/1000/asset-aware-docx-notes-validation.json and matching prefix.
This runtime/spec/tests segment has27counted files plus2MEM; separate6-file actual
Codex harness and20-file docs/harness segments follow before one main push.
Exact-head CI/Pages/public-byte verification pending. Original dirty detached
checkout untouched. Public1.4.0; next consolidated1.4.1, no tag/version bump.
MCP necessary checks; Agent complete semantic/visual review and correction.
Broader all-format goal remains active; no subagents or PRs.

## Native Word footnotes/endnotes — active

Previous goal turn classified as substantive progress, independently revalidated:
main/origin0a97f8b186cd384c4cf950cba868c5f6c93b3325 clean. Publication proof
/tmp/asset-aware-story-lifecycle-publication-proof.json passed/fully_published;
CI35452874985 all10success, Pages35452874881 all3success, six live files exact.
Integration201pass432.51s includes both new lifecycle SDK2 render configurations.
All11staged runs restored, privatepy310 removed, Docker image/builder removed,
owned server stopped. Source70aef unchanged. Public1.4.0, next consolidated1.4.1.

Current verified gap: footnote/endnote definitions and their body references lack
complete native read/content/definition CRUD, precise evidence and Wiki projection.
Implement typed note locators (part/kind/nativeID), separate displayed numbering,
full native body/reference inspection, revision/catalog guards, content edits,
anchor-bound note creation/deletion, unchanged XML/part checks, historical refs,
selections/derivations/citations and portable Wiki. MCP supplies mechanical checks;
Agent must inspect actual pages, note numbering/placement and meaning.
Reference upstream Open XML Footnote/FootnoteReference/FootnoteEndnoteType and
GitHub eigenpal/docx-editor note-nodes.ts identity/role separation; do not import
third-party code or infer note roles from conventional IDs alone.
Use tests-first, SDK2 and actual default Codex before full release gates. Full
pytest must use -o tmp_path_retention_policy=failed to avoid RAM accumulation.
Only Writer exists locally; enable actual Writer/CJK and pinned real PDF corpus,
leave unavailable Impress/Calc gates disabled. Preserve all original failures.
Work only agent-assets main; original dirty detached checkout untouched. Direct
u9401066 commits/push, <=30counted files per segment plus2MEM; no PR/subagents,
model override, version bump or tag. Broader all-format objective stays active.
Temporary prefix for this milestone: asset-aware-docx-notes.


## Native Word story lifecycle documentation — ready for publication

Runtime412ee00 (27counted+2MEM) and audit compatibility251126e (10counted+2MEM)
are committed under authoru9401066. This20-file documentation/harness segment
publishes bilingual lifecycle/contract paging instructions and exact evaluation
metrics, README/CHANGELOG/ROADMAP, generated website and five source/bundled
harness pairs. Final docs28pass and eight browser feature/evaluation desktop/mobile
zh/en states pass; actual desktopzh/mobileen and Word page3/4 screenshots reviewed.
Owned localhost8884 stopped. All11temporary staging directories restored exactly;
Docker smoke image/builder removed after successful complete read/Wiki replay.
Final full3315/33optional skips/357.08s; actual defaultCodex98success/0errors/222.28s;
source70aef matches installed wheel/Docker; no production change after actual run.
Private Python3.10 environment retained until CI completion, then remove only that
owned environment. All original error logs stay retained. Original dirty detached
checkout untouched. Public1.4.0; next consolidated1.4.1, no version/tag bump.
Pushmain next. Exact-head all CI jobs, Pages jobs and six public-file comparisons
pending; proof will be /tmp/asset-aware-story-lifecycle-publication-proof.json.
Broader all-format goal remains active; this milestone does not finish every format.


## Native contract discovery — legacy evaluation compatibility

Runtime/spec/tests committed as412ee00,27counted files plus2MEM. This separate
10-file segment permits optional read-only contract_details in nine retained
Codex auditors; original required actions and forbidden-writeback checks stay.
Four new regressions pass, included in final full3315/33/357.08s. Production
fingerprint70aef and actual98-call trace remain unchanged; no new model run.
Bilingual documentation/harness segment follows before one pushmain. Public1.4.0,
next consolidated1.4.1; no tag/bump, broad goal active. Local proof retained.


## Native Word story lifecycle — validated runtime/spec/tests

Final production70aef46664a3127832c0e2e26333b01a9d582483ae33fa76b1e833fab6f42ad9
passes full3315/33optional skips/357.08s with Writer/CJK and real NIST/NASA PDFs.
Actual default Codex98success/0tool errors/222.28s verifies10story/3structure/2contract
records,3managed revisions,2historical Wikis and8actual PNGs. Source bytes/mtime,
complete receipts, native preservation and deleted-story evidence remain intact.
Pages1/2/4 unchanged; longer page3 header intentionally wraps. No Word parity claim.
Auditor9-versus9.0 mismatch fixed with regression; same model trace replayed.
Private Python3.10 36pass/1optional skip11.76s; installed wheel and Docker both
reproduce10story/3structure records plus2byte-identical Wikis at the exact source.
Standard pip wheel smoke, import/doctor/tools/SDK2 and all local gates pass.
Final docs28pass; Ruff686/mypy290, security, dependency audits, artifact/harness/sync
and GitHub metadata/labels pass. VSIX199tests/64files/install-update pass; GUI
activation delegated to CI. Final browser8desktop/mobile zh/en states pass.
Owned Docker b631a01e2473 and builderf90bfe1b86cc removed after successful replay;
all11staged temporary runs restored with exact hashes/mtimes. Browser8884 remains
until final publication. Failed attempts retained in logs and local proof, including
root/RAM ENOSPC and absent Impress/Calc gates; transient full03 scan inputs were
not archived. Full04 cleans passing tmp_path fixtures immediately, keeps failures.
Authoritative local proof: /tmp/asset-aware-story-lifecycle-local-proof.json.
Stage27runtime/spec/test files plus2MEM, then10legacy-audit compatibility files
plus2MEM, then20documentation/harness files plus2MEM. Directmain, authoru9401066;
no PR/branch/tag/version bump. Public1.4.0, next consolidated1.4.1. Exact-head
CI/Pages/public-file verification follows push. Broad all-format goal stays active.


## Native Word story lifecycle — validation checkpoint

Implemented whole-definition create/clone/bind/delete and first/even options with
catalog/revision/hash checks, dependency protection, complete paged receipts and
historical story/Wiki preservation. Contract metadata now has its own hash-pinned
pagination; all capability flags/schema continuations survive the compact index.
Production source remains 70aef46664a3127832c0e2e26333b01a9d582483ae33fa76b1e833fab6f42ad9.
Actual default Codex run01: 98 calls, zero tool errors, 222.28s; independent audit
passes 10 story records, 3 structure records, 2 contracts, 3 revisions, 2 Wikis and
8 actual PNGs. Pages 1/2/4 unchanged; page3 intentionally wraps a longer header.
Original audit 9-versus-9.0 intent comparison failed; corrected with regression,
same trace replayed, no model rerun. /tmp/asset-aware-story-lifecycle-local-proof.json.
Private Python3.10 36pass/1optional skip11.76s; installed wheel outside checkout
replays all 10+3 records and exact two Wikis at the same production fingerprint.
Standard pip wheel smoke passed with RAM TMPDIR after retained root ENOSPC failure.
VSIX199tests/64files/install-update passed, local GUI activation unavailable;
security/dependency, lint686/mypy290, harness/sync and GitHub metadata/labels pass.
Browser eight feature/evaluation desktop/mobile zh/en states pass; actual screenshots
inspected. Browser plugin unavailable, existing Playwright fallback; localhost8884
still active. Full04 currently running with Writer/CJK and real NIST/NASA corpus.
Full03 reached RAM ENOSPC at93%, exit120; two scan failures occurred. Original
partial log retained, but those transient scan inputs were removed during cleanup.
Full04 uses pytest tmp_path_retention_policy=failed to remove each passing fixture
immediately while preserving failures, preventing accumulated RAM exhaustion.
Full01: legacy contract test plus expired corpus path; full02: one PDF false result
during pip ENOSPC plus three unavailable Impress/Calc cases. Failure logs/fixtures
retained, successful terminal full fixtures removed only. PDF isolated recheck1pass.
Nine legacy evaluation auditors accept optional read-only contract_details; four
new regressions preserve missing-step and unauthorized-writeback rejection.
Pending full04, Docker, final docs metrics/build checks and segmented commits/push.
No version/tag/model override, no subagents, no original-checkout edits. Public1.4.0,
next consolidated1.4.1; broad all-format goal remains active.


## Native Word story definition lifecycle — active

Previous goal turn made substantive progress: existing story content CRUD and
complete evidence fully published at b5c7483a4b93120c53258a0bea3c62246b283381.
CI35448665822 all10success, Pages35448665507 all3success; six deployed files exact.
Integration199pass387.11s including both new story SDK2 cases. Authoritative proof:
/tmp/asset-aware-docx-stories-publication-proof.json (fully_published true).
All staging restored, owned browser stopped, private Python3.10 env removed after
CI; source92fe28 unchanged. Public1.4.0; next consolidated1.4.1; no tag/bump.

Current verified gap: contents can be edited but entire definitions cannot yet be
created/cloned/bound/unlinked/deleted. Build explicit sequential story lifecycle
operations with source/revision/catalog preconditions, full native preservation,
section inheritance receipts and Agent actual-page review. Preserve source/history
and existing evidence/Wiki semantics. First/even flags affect both headers/footers;
unlink means inherit, not blank. Detached media retained, not secure erasure.
Continue tests-first implementation, SDK2, actual default Codex and release harness,
then bilingual docs/MEM and separate runtime/docs author-u9401066 commits/pushmain.
No model override, subagents, extra branch/PR, version bump or original-checkout edit.
Broader all-format goal remains active. Temporary prefix: asset-aware-story-lifecycle.

## Native Word header/footer documentation — ready for publication

Runtime/spec/tests committed as f3ccf0d (27 counted files plus2MEM), author u9401066.
This separate segment publishes bilingual story content CRUD and exact evaluation
metrics, README/CHANGELOG/ROADMAP, generated site and five synchronized source /
bundled harness pairs. Feature and evaluation pages passed eight total desktop /
mobile zh/en states; desktopzh/mobileen screenshots from both visually inspected.
Browser plugin unavailable, installed Playwright used. Owned localhost8880 stopped.
Final docs28pass, full3268/33/325.91s, actual75success/0errors/165.22s, source92fe28
and installed wheel/Docker parity unchanged. All staged temporary runs restored;
original dirty checkout untouched. Public1.4.0, next consolidated1.4.1, no tag/bump.
Pushmain next; exact-head CI/Pages and six deployed file comparisons pending.
Remaining broad all-format/Word story lifecycle work keeps the goal active.

## Native Word header/footer stories — validated runtime/spec/tests

Final source 92fe28b29f3988b4c9a2cdff41745eb7fdbf38e3fe03a6b80f05786553e030a4
passed full3268/33optional skips/325.91s, with actual Writer/CJK and NIST/NASA PDFs.
New unit42pass; SDK2 both2pass16.10s; private Python3.10 group43pass/1optional skip
7.50s. Final docs28pass; Ruff671/mypy285; harness/artifact/sync/diff clean. Bandit,
uv214/npm/zizmor pass. VSIX199tests/64files/install-update pass; activation in CI.
Metadata/topics/managed labels synchronized. No version change: public1.4.0,
Unreleased1.4.x, next consolidated patch1.4.1.

Actual default Codex completed75success/0toolerrors/165.22s, eight complete story
records, three managed revisions, two historical Wikis and six actual PNGs. Source
bytes/mtime, all unrelated parts, complete receipts and historical references pass
independent audit. Synthetic3page/2section source uses a nonstandard shared header
part and preserved first-page exception. Native PAGE cache stays1; rendered pages
2/3 calculate dynamic values. No MicrosoftWord parity claim. Full-definition
lifecycle/relinking and note stories remain further work; broad goal stays active.

Clean Python3.10 wheel and Docker ae03a5a48b94 reproduce all8complete records,
2catalogs and both exact historical Wikis outside checkout. Source SHA equals
actualCodex. Import/doctor/SDK2stdio30tools pass. Only successful owned Docker
smoke and terminal builder ae62692458eb removed; all11 staged historical runs
restored with exact hashes/mtimes. Actual traces and failure logs retained.
Initial render oracle was corrected for titlePg's blank first-page footer; no
production change/model rerun. Initial system zizmor command was absent; locked
uv invocation passed. One docs test command used a nonexistent path; actual
reference-sync/hygiene tests28pass. No errors erased or unrelated cleanup.

Feature browser4desktop/mobile zh/en states passed; actual final Word pages and
desktopzh/mobileen documentation visually inspected. Browser plugin absent;
existing Playwright fallback used. Evaluation browser separately checked after
metrics update. Original dirty checkout untouched; working main in agent-assets.
Commit runtime/spec/tests/CI/smoke separately from docs/harness, each withMEM.
Pushmain next; require exact-head CI/Pages and six live byte comparisons. Final
proof planned /tmp/asset-aware-docx-stories-publication-proof.json. Goal active.

## Native Word header/footer stories — active

Previous goal turn made substantive progress: pagination correction fully published
at cb9a4a8e2619114483f7f43516acdf623df6028a, CI35445459440 all10success and
Pages35445458766 all3success, six deployed files exact. CI integration197pass364.64s,
including both new layout SDK2 cases. Authoritative proof:
/tmp/asset-aware-docx-layout-publication-proof.json. No pending staging or processes;
private Python3.10 env removed after success. Public1.4.0; next consolidated1.4.1.

Next verified gap: legacy DFM header/footer previews stop at100 characters and guess
variants from filenames; nonstandard story filenames can be missed. Native story
operations now discover actual content types/relationships, section inheritance,
full XML/text paths, and edit existing shared definitions (text/insert/delete blocks)
while preserving all other parts. Independent representation keeps legacy refs stable.
MCP mechanical checks; Agent reviews all shared/dormant definitions and actual pages.
New story references connect selection/derivation/citation/Wiki; distinct story Wiki
projection leaves old snapshots intact. Full definition creation/unlink/deletion and
footnote/endnote stories remain outstanding toward the broader all-format objective.

Test-first missing-module failure retained; core5pass and service tests underway.
Continue meaningful guard/SDK2/actual default Codex multi-section visual evaluation,
then full release harness, docs/MEM and segmented author u9401066 commits/pushmain.
No source checkout changes, no branch/PR/version/tag, no subagents. Temporary outputs
use /run/user/1000/asset-aware-docx-stories-*; root92MiB free, stage only verified
owned terminal runs if Docker requires space. Broad goal remains active.

## Native Word pagination docs — ready for publication

Runtime/spec/tests committed as12e2230 (16 counted files plus2MEM), authored by
u9401066. This separate segment publishes bilingual pagination behavior/evaluation,
README/CHANGELOG/ROADMAP and five synchronized source/bundled assistant harness
pairs. Actual74success/1recoverederror/200.83s, all5PNGs and 1-to-4-page synthetic
correction are stated with limits. Final full3218/33/305.27, Python3.10, installed
wheel/Docker source parity and browser evidence are unchanged. Docs25pass after
metrics update; build_docs_site/harness/artifacts/diff/sync clean. All temporary
staging restored and owned browser server stopped. Original checkout untouched.
Pushmain next; exact-head CI/Pages and six deployed byte comparisons pending.
Public1.4.0, next consolidated1.4.1; no version bump/tag. Broad goal remains active.

## Native Word table pagination — validated runtime/spec/test segment

Final source f5abe76ba927967af4b568eb688804eae31f57a0ae0549307a4216df928a50ad
passed 3218 tests /33 optional skips /305.27s, including actual Writer/CJK and
NIST/NASA PDFs. New layout/audit/SDK2 group34pass14.82s; Python3.10 group33pass /
1optional rendering skip7.61s. Docs25pass, Ruff657/mypy280, harness/artifact audit,
Bandit/uv214/npm/zizmor checks pass. VSIX199tests/64files/install-update pass;
activation skipped locally and required in CI. Metadata/topics/labels synchronized.

Actual default Codex01 passed74 successful MCP calls with1 recovered schema-limit
input error in200.83s, no model override or rerun to erase errors. Two complete
DFM/grid/receipt reads, two historical Wikis and all5 actual page PNGs reviewed.
The clipped1-page source becomes4 pages, both header rows repeat, all14 body rows
retain every END/CONFIRMED line and numeric spelling. Independent pixels, native
cell/style XML and all other package parts, source bytes/mtime and Wiki pass.
Synthetic14-row scope only; inherited styles/oversized rows/MicrosoftWord remain
open. MCP checks mechanical properties; Agent owns full meaning/visual correction.

Clean installed Python3.10 wheel and Docker b7663e5ec8b0 replay both complete table
revisions and exact current Wiki outside checkout; source SHA matches actualCodex.
Import/doctor/SDK2stdio30tools pass. Docker builder717fe344272c and smokeimage were
removed only after successful replay to reclaim disk. All11 owned historical runs
restored with exact hashes/mtimes; /tmp/asset-aware-docx-layout-staging.json alltrue.
Logs/actual runs/failures preserved. No source or original dirty checkout touched.
Browser4desktop/mobile zh/en states pass; desktopzh/mobileen visually inspected;
no overflow/console errors. Browser plugin absent; existing Playwright used.

Commit runtime/spec/tests/CI/smoke separately from docs/harness, each withMEM.
Public1.4.0; next consolidated patch1.4.1, no per-feature bump/tag. Broader goal
remains active. Next pushmain, require exact-head CI/Pages and six live byte checks;
final proof /tmp/asset-aware-docx-layout-publication-proof.json pending.

## Native Word table pagination — active

Previous goal turn made substantive progress: native DOCX grid CRUD fully published
at67407f2, CI35443245856 all10success, Pages35443245547 all3success, six deployed
files exact. Authoritative proof:/tmp/asset-aware-docx-grid-publication-proof.json.
Main/origin clean and equal; all previous staging restored. Public1.4.0, next
consolidated patch1.4.1; no per-feature bump/tag. Original checkout untouched.

Next gap verified from code: table row resizing only sets minimum heights, existing
repeated headers cannot be configured, and row pagination cannot be corrected.
Implement explicit contiguous header count and row height/split policies through
existing version-bound table-grid operations. Preserve native cell/paragraph XML,
styles, merged/omitted topology and other package parts. Agent checks actual pages;
MCP does not claim visual fidelity. Add multi-page clipped-text/header correction
fixtures, real SDK2 images and actual default Codex before/after review. Keep source
history/Wiki evidence and atomic review receipts. Research uses official OpenXML
TableHeader/CantSplit/TableRowHeight plus python-docx implementation, no new deps.
Root104MiB free; new transient outputs under /run/user/1000/asset-aware-docx-layout-*.
No staging currently. Broad all-format/citation/wiki goal remains active.

## Native DOCX grid docs — ready for publication

Runtime/spec/tests committed as d22bac4 (22 counted files plus2MEM), authored by
u9401066. This separate segment updates README/CHANGELOG/ROADMAP, bilingual site,
native table guide, evaluation evidence and five source/bundled assistant harness
pairs. Full receipts/latest matching history/no-op behavior and Agent review are
explicit. Final test3184/33, default Codex70/0/162.73, sourcef55fcb83 and installed
wheel/Docker replay remain unchanged; no new model run or version bump.
All temporary staging restored; final task-only Docker image/builder removed after
verification. Public1.4.0 / Unreleased1.4.x. Next pushmain, verify exact-head CI and
Pages plus six live files, store /tmp/asset-aware-docx-grid-publication-proof.json.
Broad all-format goal remains active; cross-page/Microsoft Word fidelity and
unextracted Word stories remain open. No PR or extra branch created.

## Native DOCX grid — validated runtime/spec/test segment

Final source f55fcb83b05302698080b1a081e482ed15d9d199ef2248df3f8c7a51e3ae9ff7
passed3184 tests /33 optional skips /290.27s, including actual Writer/CJK and
NIST/NASA PDFs. Python3.10 focused59pass12.61s; docs25pass0.18s; Ruff649/mypy279,
release harness/artifacts/security clean. Final default Codex02 passed70 MCP calls,
zero errors,162.73s;3 complete revisions and receipts,1original scan +2actual Word
PNGs. Independent pixels/CJK/native XML/source bytes/mtime/historical refs/fullWiki
pass; Agent inspected both Writer pages. Initial61call run and reproduced long
receipt regression remain preserved. One-page synthetic scope; no MicrosoftWord
or cross-page repeated-header fidelity claim.

Final wheel (clean locked Python3.10 runtime) and Docker95559c66c9fd replay all3
complete table records and exact Wiki, matching final source SHA. Doctor/import/
SDK2stdio30tools pass. VSIX199tests/64files/install-update pass; activation skipped
locally and required in CI. Browser4desktop/mobile zh/en states pass, no overflow
or console warnings; existing Playwright used because Browser plugin absent.
GitHub description/topics/managed labels remain synchronized.

All11 owned terminal run directories restored exactly after final Docker replay;
/tmp/asset-aware-docx-grid-final-staging.json allrestoredtrue. Final smoke image
95559c66c9fd and terminal builder7d4e91c186ad removed only after successful replay
to reclaim constrained disk space; evidence/logs retained. No outstanding staging.
Original dirty checkout untouched. Public1.4.0 / Unreleased1.4.x, no version/tag.
This commit is runtime/spec/tests/CI, with separate docs/harness commit next; then
pushmain and verify exacthead CI/Pages/publicbytes. Goal stays active.

## Native DOCX grid — final validation in progress

Public version remains 1.4.0; accumulate Unreleased work within 1.4.x, next
consolidated patch 1.4.1. User reaffirmed no rapid minor/major bumps. MCP provides
mechanical checks; Agent owns complete semantic/visual review and correction.
Initial implementation passed 3158 tests / 35 optional skips, and actual default
Codex run01 passed 61 calls / 0 errors / 174.05s. Final audit found long mutation
receipts could be truncated: retained failing regression, added complete paged
operation_result and before-commit combined 16MiB review limit. Recurring file
hashes use the latest matching receipt; full text_sha256 must stay consistent.

Final source f55fcb83b05302698080b1a081e482ed15d9d199ef2248df3f8c7a51e3ae9ff7.
Focused SDK2/grid group55 passed8.93s; Python3.10 group including four new receipt
assertion tests59 passed12.61s. Ruff649/mypy279 and security checks pass (uv214
packages/npm0 vulnerabilities, Bandit medium+ clean, zizmor no high findings).
Full02 and actual default Codex02 are running against this final source. Initial
run01 retained; rerun is justified by production receipt delivery change, not to
hide an evaluation failure. VSIX199 unit tests/64 package files/install-update and
four desktop/mobile zh/en browser states pass. Local VS Code activation is not
available; CI remains required. Wheel rebuilt/reinstalled; final replay pending.

Disk-full interrupted restoration of owned terminal test evidence and left the
untracked grid spec empty. Verified complete staged copies, removed only partial
restore duplicate and superseded task Docker6348, restored all11 exact hashes and
mtimes, and reconstructed/reviewed the spec. Original checkout untouched. Staging
manifest /tmp/asset-aware-docx-grid-staging.json now all restored. Final Docker,
runtime replay, final docs/MEM commits, main push and exact-head CI/Pages remain.
Broad document/asset goal stays active; this milestone is substantive progress.

## Native DOCX table grids — implementation and focused validation

Previous ETL snapshot milestone is fully published at 1ae66a5: exact-head CI
35439649309 (10 successful jobs), Pages35439649128 (3 successful jobs), six live
files byte-identical. Authoritative proof: /tmp/asset-aware-etl-csl-publication-proof.json.
Previous version-only turn made no new feature progress; revalidated main clean and
all version sources1.4.0. This turn implements native Word table grid CRUD, preserving
full table references, native rich/nested content, omissions and historical evidence.
New spec: docs/specs/native-docx-table-grid.md. MCP mechanical integrity; Agent full
semantic/visual review. Public1.4.0 / Unreleased1.4.x, no per-feature bump or tag.

Implemented read_docx_table and update_docx_table_grid (sequential insert/delete/
resize/merge/split), source CAS, complete paged native XML/grid, package invariants,
merge-anchor promotion and explicit append_blocks/require_empty. Tests include
nested/omitted/merged tables, rich text, rollback, no-op history, stale/tampered refs,
source bytes/mtime, old proofs and Wiki. Focused Python3.13 + actual SDK2 stdio:
60passed7.27s. Ruff passes; mypy279 passed before last minor read-record extension.
Initial type-check errors were loop-variable reuse and missing list annotation;
fixed, no production bypass. First 27 infrastructure tests passed; service group34
also passed before broad focus60. Actual default Codex, additional dependency cases,
full harness, docs/site/MEM segments and publication remain. No source commit yet.
Root filesystem tight (~12MiB); all new test workspaces/mypy cache under private
/run/user/1000/asset-aware-docx-grid-*. No staging currently. Original dirty checkout
untouched. Only work in /home/eric/workspace251226/asset-aware-mcp-agent-assets.

## CI correction docs — ready for retry

Test-only fix 1b7ded8 is paired with updated bilingual evaluation docs;
initial failed CI and local Python3.10 reproduction remain visible. Corrected groups
44pass49.37s (3.10) and10pass40.13s (3.13); production fingerprint unchanged. This
commit records recovery, regenerates Pages and keeps public1.4.0/Unreleased1.4.x.
Push correction, await exacthead CI and Pages, then refresh external publication
proof. Whole goal remains active, no version/tag or original-checkout change.

## CI Python3.10 image decoder correction

Initial exact-head CI35439173449 at e1bd887 failed only the new ETL stdio test in
Python3.10: structured_content held a list of content blocks, not metadata. Its
trace fails at metadata[image_sha256]; macOS/Windows/unit/static/VSIX passed before
final integration. Local frozen Python3.10 reproduced1failure5.89s. Test now parses
actual TextContent with the existing native decoder, verifies one actual PNG/hash
and full returned reference on both initial/historical views. Two regressions cover
list wrapping/no wrapping and changed image rejection. No production source changes.

Frozen Python3.10 snapshot/audit/SDK2 group44pass49.37s; Python3.13 audit/SDK2 group
10pass40.13s. Ruff636 and diff hygiene pass. Source296dc68a…72da86 remains identical
to actual52success/2recovered-error audit and wheel/Docker replay. Initial CI logs
/tmp/asset-aware-etl-csl-ci-job-105886897809.log and localbefore failure are retained.
Private env/cache:/run/user/1000/asset-aware-etl-csl-py310{,-cache}; remove after final
CI proof. All staging restored; no new staging. Public1.4.0/Unreleased1.4.x,no tag.
Next separate correction/docs commits, pushmain and verify new exacthead CI/Pages.
Whole goal remains active; this is a test-adapter correction with forward progress.

## ETL snapshot docs — pre-push checkpoint

Runtime/spec/tests committed as ddfafde (18 counted files plus5MEM), authored by
u9401066. This separate docs/harness segment explains full inspection/capture/read/
view, mixed CSL sources, complete attachments, historical behavior and Agent review.
README/CHANGELOG/ROADMAP and bilingual generated Pages match; five assistant sources
match five VSIX bundled copies. Actual proof remains52successful/2recovered errors,
6images/3captures/1Wiki; source296dc68a…72da86 is unchanged after wheel/Docker replay.
Final browser desktop/mobile zh/en+APA checks pass; privatewheel env removed and all
11 staged directories restored exactly. GitHub metadata/managed labels already match.
No version bump/tag: public1.4.0, Unreleased1.4.x. Next pushmain, await exact-head CI/
Pages and compare publicbytes. No selfPR/extra branch; broadgoal remains active.

## ETL evidence snapshots — validated, publication pending

Immutable legacy PDF ETL capture/read/view plus complete no-write inspection now
connect spans/tables/figures with native sources in CSL. Fresh spans rebuild from
captured canonical artifacts, not cached citation_index. Raw BOM/encoding/line-ending
bytes remain separate from normalized text hashes. Source/locator checks are MCP
mechanics; Agent reviews extraction, pixels, semantics and bibliographic truth.
Public1.4.0 / Unreleased1.4.x, no tag. Original dirty checkout remains untouched.

Full01:3110passed35optional-skips289.41s with NIST/NASA. New snapshot unit34pass;
SDK2 actual ingestion/historical PNG onepass38.65s; seven later auditor regressions
pass0.13s separately. Actual default Codex01:52successful/2recovered input errors,
223.68s,6PNGs,3ETLsnapshots,1mixed-source Wiki. Both errors passed text_limit to native
contract; schema paging recovered. Initial audit mistook mime_type for wire mimeType
and omitted readonly schema discovery; same retained trace passes corrected audit.
Original failure retained in audit.before-wire-fix.json; no model rerun/model override.
Evidence:/run/user/1000/asset-aware-codex-etl-csl-01. No subagents.

Source SHA296dc68aca5227328ac6eef71f74af6502449561e8edcfeaebbc99d96e72da86
matches actual/wheel/checkout/Docker727caccabe93. Clean Python3.10 wheel runtime and
outside-checkout replay pass all3historical PNGs and byte-identical Wiki. BaseDocker
import/doctor/tools/SDK2 pass; CSL explicitly lacks optionalNode; readonly Node mount
renders, and readonly actual-evidence replay with matching UID1000 passes. First
replay default container UID could not read host0600 native asset metadata; retained
failure, no chmod or source mutation. VSIX199tests/64files/install-update pass; local
activation unavailable and delegated to CI. Browserzh/en desktop/mobile guide +APA
preview pass6screens with existing private Chromium libs; first missingLD_LIBRARY_PATH
launch retained. Ruff636/mypy274/Bandit/harness/security/artifacts and final docs/auditor46pass
0.37s all pass. uv214/npm0vulnerabilities, existing zizmorinfo baseline.

All11 temporarily staged owned terminal directories restored with exact hashes/mtimes;
/tmp/asset-aware-etl-csl-staging.json allrestoredtrue. Only owned replaced Docker image
1a0f5426b862 and current terminalbuilder42b30863b83c removed. Root~16MiBfree; private
wheel env removed after terminal replay proof. No outstanding staging obligation. Final docs,
MEM, scoped commits (<=30 counted files), mainpush/CI/Pages/live-byte proof remain.
Whole multi-format goal remains active; this is substantive progress, not blocked.

## ETL citation snapshots — active

Previous goal turn made substantive progress:5f4450b168fbcf67aa22fdc53bf8eb82405f8a2e
fully published; CI35436567752 all10success, Pages35436567715 all3success, six public
files exact, latestreleasev1.4.0, mainclean. Authoritative external proof:
/tmp/asset-aware-csl-publication-proof.json. No proof-only commit needed.

Current gap: legacy PDF ETL AssetRefs bind mutable manifest/markdown/blocks, unlike
native immutable revisions. Implement explicit capture/read/view of immutable ETL
citation snapshots, then mixed native/ETL CSL sources and portable full evidence.
Read docs/specs/etl-citation-snapshots.md before source changes. Existing pure ref
checks move into application without changing public compatibility. Canonical spans
must rebuild from captured bytes; cached spans alone are insufficient. DOCX DFM is
separate; native DOCX block refs already provide its CSL route. Consulted official
DoclingDocument/graph provenance docs for structured content+geometry+hash boundaries.
MCP checks bytes/locators/versions; Agent reviews meaning, actual images and citations.
Public1.4.0/Unreleased1.4.x; actual Codex uses unchanged default model; no subagents.
RootFS28MiB free; use /run/user/1000 for task scratch, keep all previous evidence.
No current staged/restoration obligation; prior11directories fully restored.

## CSL docs and publication checkpoint

Source/tests91e2131 follows pinned resources/spec6ad8ab5; both authored by authorized
u9401066. This docs/harness segment updates README/CHANGELOG/ROADMAP, bilingual Pages,
CSL operation examples, native-template boundary and final evaluation metrics. Five
assistant sources match five bundled VSIX copies. GitHub description includes CSL;
managed labels already match. Docs35pass, sync/harness/lint/format gates pass; runtime
is unchanged from actual02/wheel/Docker SHA5b4d74bc…10c0ef. Original checkout untouched.

Publication pending: pushmain, await exact-head CI and Pages, compare live files with
local generated bytes, record external publication proof. No tag/version bump:
public1.4.0 / Unreleased1.4.x. Whole multi-format goal remains active after this
milestone; legacy ETL CSL bindings and broader native CRUD/fidelity/corpus remain.

## CSL runtime — pre-publication checkpoint

Resources/spec committed as6ad8ab5 with21countedfiles plus3MEM. This commit adds
domain citation-document validation, optional offline Node processor, full-document
retroactive cluster updates, safe typography, verified native source bindings and
immutable citation Wiki via existing publisher. Existing template contract/tool count
unchanged. SDK2 typed paging rejects invalid limits/hash formats before side effects.
Direct jsonschema>=4.26,<5 dependency is already in the lock; no runtime npm install.
CI adds Node before CSL tests and audits bundled npm lock. Source remains5b4d74bc…10c0ef;
all final local/actual/wheel/Docker proofs in preceding checkpoint still apply.
Latest docs/hygiene35passed0.35s, final lint/format/harness/assets pass; metadata and
managed GitHub labels synchronized, actual02 audit replay passes38successful/1error.
Next commit human-facing docs/harness separately, then pushmain and verify exact-head
CI/Pages/public bytes. Public1.4.0/Unreleased1.4.x; no tag; broad goal remains active.

## CSL resources — final local validation checkpoint

Pinned upstream citeproc-js2.4.63 (internal1.4.61), official CSL styles/locales and
input schema retain exact URLs, hashes and original licenses. Resources/spec are
committed separately from runtime/tests and docs/harness; each group <=30 counted
files excluding MEM. Public1.4.0 / Unreleased1.4.x; no new tag or model override.

Final full03:3075passed35optional-skips221.04s with real NIST/NASA corpus. Earlier
full02 had three stale GitHub-description fixtures; fixed expectation and reran all.
Clean private Python3.10 CSL unit/audit/SDK2:31passed23.30s. Actual default Codex02:
38successful calls,1recovered invalid schema-hash error,192.75s,4PDFimages,2Wikis.
Actual01 retained167/1/221.2s with redundant reads and an oversized CSL page request.
Both use fictional books; neither proves arbitrary bibliographic/semantic fidelity.
Proofs:/run/user/1000/asset-aware-codex-csl-{01,02}; all original bytes/mtime retained.

Source/wheel/actual02/Docker share SHA5b4d74bc3dc8e1aed0f05f89aa210f6c6e33ad95b20f52737fc90fa64410c0ef.
CSL manifest97beaf131e1784d8dc694fc9de9afd7270b9cc773f46cab52ea4cf4885b4a953;
worker d897399d29e9f521764f2366e15fbc4970beba227ad4e0a898d51386725beb42.
Docker1a0f5426b862 passes import/doctor/tools/SDK2; base has noNode and reports it;
read-only optional Node mount passes actual APA. Installed wheel outside checkout
passes real rendering. VSIX199 tests, package64files and install/update pass; local
activation unavailable. Browser1440x1000/390x844 zh/en and APA/NLM previews pass,
8screens saved. Docs35pass0.35s; Ruff626, mypy270, Bandit, artifact/harness/sync audits
pass. uv214audit/npm audits0vulnerabilities; zizmor has existing informational baseline.

After terminal Docker proof, only owned old e4de8f8e runtime and0ebdb50a builder were
removed. First restore hit root disk capacity on final directory; staged originals
remained intact. Removed reproducible local Python/mypy caches, copied missing files,
and verified all11 original inventories/hashes/mtimes restored; staging manifest
/tmp/asset-aware-csl-staging.json allrestoredtrue. Terminal private wheel env removed;
logs/current actual runs retained. Root disk remains tight; avoid unnecessary rebuilds.

Pinned upstream whitespace remains unmodified. Narrow .gitattributes exceptions
cover only citeproc.js/CPAL; -text preserves resource/worker bytes across Git newline
conversion. A temporary staged checkout with core.autocrlf=true verifies every
manifest resource hash/size. This changes no production runtime bytes.

Next commit runtime/tests, then docs/harness with updated MEM; push main and require
exact-head CI/Pages/public bytes. Original dirty worktree untouched; broad goal active.

## CSL citation document work — active

Prior real-PDF milestone 00470f94 is fully published: CI35433497376 all10success,
Pages35433497144 all3success, five public files match exact local bytes; proof
/tmp/asset-aware-real-pdf-publication-proof.json. Current main is clean at start.
Next implement real document-context CSL processing with complete source evidence
and portable citation Wiki, preserving existing custom display contracts. Read
docs/specs/csl-citation-documents.md before code. citeproc-js selected for proper
retroactive disambiguation; citeproc-py currently documents that feature as missing.
No Agent delegation; actual Codex must keep default model. Public1.4.0/1.4.x.
11 owned terminal evidence directories are temporarily staged with verified hashes
and original symlinks under /run/user/1000/asset-aware-csl-build-staging; manifest
/tmp/asset-aware-csl-staging.json. Restore exact files/mtimes after terminal gates.
Broad goal stays active.

## Real PDF final pre-push checkpoint

Portable corpus correction96b480ea442ac70edc7a6c2531d72423612a8800 changes only test
IO: explicitUTF-8 and non-UTF-8subprocess regression. Final full04 passes3044/35
198.26s with real corpus enabled;15focused oracle tests pass0.43s. Replayed both
retained actual Agent audits with updated UTF-8 reader and obtained identical
reports. Runtime source remains fae31e15…509c4300, matching installed wheel/Docker/
actualNIST02+NASA01. Docs links fixed, docs35pass, source lint/format still pass.
GitHub DNS recovered and ls-remote confirms origin/main c8874795; first failedpush
changed no remote state. Push all scoped commits, await exact-head CI/Pages and
public file bytes. Public1.4.0/Unreleased1.4.x,no tag; broad goal active.


## Portable corpus text — pre-push correction

First push of9031f4a+6999d2d failed terminally before connection: GitHub DNS resolution.
Resolver later returned GitHub/API addresses; retry after final validation. No remote
CI was started by that failed push. Cross-platform review reproduced corpus loader
UnicodeDecodeError under PYTHONUTF8=0/PYTHONCOERCECLOCALE=0/LC_ALL=C.
Manifest/trace/report reads and writes now explicitly use UTF-8;15focused oracle
tests pass including a real non-UTF-8 child process. No src/runtime changes, so
actual/wheel/container source SHAfae31e15…509c4300 remains applicable. Full04 recheck
is running; prior full03 3043/35/197.35s is retained. Public1.4.0/Unreleased1.4.x.


## Real PDF publication checkpoint

Source/spec/tests commit 9031f4aec2115d907e632ea06ba16218f5ff1f49 preserves original NASA/NIST source bytes and
adds verified duplicate-Length interpretation plus real corpus/actual Agent audits.
All local gates pass, including3043/35full,31Python3.10,466successful current Codex
calls/0toolerrors/143exactdata-cells, wheel/container source SHAfae31e15…509c4300,
VSIX199 and browser zh/en desktop/mobile. NIST's earlier wrong-column workflow
remains reported separately. This docs/harness commit publishes clear scope, test
commands and mechanical-vs-Agent boundary; runtime source remains unchanged.
Push both commits to main, then require exact-head CI/Pages/public-byte evidence.
Public1.4.0/Unreleased1.4.x,no tag; broad goal remains active.


## Real PDF corpus — all local publication gates passed

Full03:3043passed35optional-skips197.35s, with actual government corpus enabled.
Passed-fixture cleanup and TMPDIR avoid constrained-disk failures; assertions/test
coverage unchanged. Clean private Python3.10:31passed74.86s; canonical built-wheel
CLI/doctor/tools/SDK2 smoke passes. Installed-wheel import was independently checked
outside checkout. Source/wheel/actualNIST02+NASA01/Docker all share SHA
fae31e15c827e60055c8a00286e56d4df0b54ed197b61f39821a63c1509c4300.
Docker e4de8f8e8de61e8de06a743860f3e3886083c016479ba39d8e998bd922c5939e
passes import/doctor/tools/actualSDK2; old owned a83runtime and67886aa builder removed
only after proof.11ownedterminal evidence directories were staged to private
/run/user/1000 then restored with exact hashes/mtimes; manifestallrestoredtrue:
/tmp/asset-aware-real-pdf-staging.json. Private wheel environment removed after proof;
Python3.10 SDKfixtures retained /run/user/1000/asset-aware-real-pdf-py310-tests-01.
VSIX199tests106ms,64file packageaudit,66file233.83KiBpackage,install/update pass;
local activation unavailable as before. Browser zh/en desktop/mobile pass.
Docs35pass; source Ruff614/mypy265/Bandit, zizmorbaseline,uv215lock/214audit/npm0
passed. Public1.4.0/Unreleased1.4.x,no tag.

Next: staged source/spec/tests and docs/harness commits under authorized user,
pushmain, then require exact-head CI, Pages and public-byte proofs. Broad goal active.


## Real public PDF corpus — actual Agent proofs and parser correction

Current source SHA fae31e15c827e60055c8a00286e56d4df0b54ed197b61f39821a63c1509c4300
matches both actual default-model Codex runs: NIST02 234successful/0errors283.58s,
25rows75data-cells; NASA01 232/0/251.22s,34rows68data-cells across2pages. All143
first-transcribed values match independently image-reviewed truth. Each run audits
7CSV history events, allinitial/finalfields, bytes/BOM/CRLF, complete receipts,
source bytes/mtime, sampled region claims and Wiki. NIST01 remains a failed workflow:
75/75transcription but model edited column0 instead of specifiedcolumn1 (237calls,
256.27s). Explicit zero-based wording fixed retry; do not erase first outcome.
Artifacts:/dev/shm/asset-aware-codex-real-{nist-01,nist-02,nasa-01}.

NASA original source has359 duplicate Length warnings. New source-byte/xref/dictionary
checks prove718 equal direct integer declarations against all raw streams and bounds;
read bytes unchanged, parser_checks retained, requested edits/copies record repair.
Conflicts/indirect/unknown warnings still fail. Native page references for ordinary
PDFs stay unchanged.15focused parser regressions plus14corpus/auditor cases and2real
SDK2 cases pass31/72.10s; actual NASA page copy canonicalizes duplicates.

Independent exact direct-region pixels pass; full-page crop resampling differs on
old scans, so corpus audit reports diagnostic4.726/3.847mean differences instead of
reusing synthetic mean<1 assumption. Separate calibrated glyph bounds/string truth
remain; forged PNG+hash is rejected. Both rendering paths share MuPDF.

README/CHANGELOG/ROADMAP, zh/en Pages guides and5assistant sources+bundled copies
updated; docs35pass, browser4desktop/mobile/language flows pass. CI now explicitly
fetches/hash-checks original government PDFs;3platform inventories include offline
parser/oracle tests. Metadata/labels already synchronized. Ruff614/mypy265/Bandit,
zizmor baseline and dependency audits pass; VSIX199tests/package64pass.

Full01 exhausted shared-memory test scratch; full02 passed3040 with3failures:
worker root-temp ENOSPC(2), doc-link convention(1). Fixed docs links and directed
TMPDIR to SHM; focused failures2pass. Full03 now runs with passed-fixture cleanup,
no disabled assertions. Preserve final SDK05/actual evidence; terminal failed SDK
scratch/full01 and duplicate verified download were removed. Source corpus remains
/dev/shm/asset-aware-real-pdf-sources-01. RootFS tight; owned terminal evidence may
be temporarily staged via /tmp/asset-aware-real-pdf-stage.py to /run/user/1000 only
with snapshot/hash/mtime verification and exact restoration.

Remaining publication gates: full03, fresh wheel/isolated Python3.10/runtime proof,
VSIX install smoke, Docker, scoped source/docs commits+push, exact-head CI/Pages.
Public1.4.0/future1.4.x, no new tag. Original broader goal remains active.


## Real PDF corpus — active work

Previous CSV milestone is fully published at c88747951ed3599911451d083bc72600ac4f0767:
CI35430475848 all10 success, Pages35430475275 all3 success, public5 exact. External
proof:/tmp/asset-aware-delimited-publication-proof.json. Main clean, only main;
Python/VSIX/latest release remain1.4.0, future workUnreleased1.4.x/no new tag.

Next requirement: actual real-file PDF visual/structured CRUD. Spec now records
unchanged NIST1648a (17pages, SHAde60072d…) and Apollo11 NASA report (359pages,
SHA3314d996…), including scan+imperfectOCR, not synthetic scans. Entire selected
tables:25 NISTrows,34 NASArows across2pages. Independently image-reviewed string
oracles, source-hash pins and region coverage; actual default-model Codex plus
separate SDK2 tests. Sources:/dev/shm/asset-aware-real-pdf-sources-01. No completion
claim yet; broad native text/web/media and academiccitation work remains active.


## Native delimited compatibility publication checkpoint

NUL source correction e16a971cc70c5a295bc6eb0de9a20e5b50e9b1c3 preserves exact CSV strings/positions across Python3.10
and newer. Docs/changelog now record final3012/35 full tests, clean Python3.10 SDK2
37pass, default Codex103/0/4regionPNG210.09s, and both earlier CI findings/corrections.
Runtime source/wheel/actual/container share SHA0f9c93de…20a0a24; all local gates pass.
This doc commit keeps source code unchanged. Push both scoped commits and require
new exact-head CI/Pages/public byte proofs before closing the milestone. No version
bump or tag: public1.4.0/Unreleased1.4.x. Original broad goal remains active.

## Native delimited NUL fix — all local gates revalidated

Current source SHA0f9c93deb1f56031bce79b3aeeca373c4cf2e0b429e2173b2afa08fbf20a0a24
matches actual default Codex run02, built wheel, isolated Python3.10 installation,
and Docker a83ff0fe9f0b91cbaa2f1cec29bcf1e3ba82c029475baf12b6289696f2a21e4b.
Fullpytest3012passed35optional-skips126.86s; Python3.10 focusedunit+SDK2 37pass13.91s.
Actual Codex103successful/0errors210.09s,4regionPNGs,3claims,6historyevents and2Wikis
pass independent bytes/raster/trace audit; artifacts:/dev/shm/asset-aware-codex-delimited-02.
Clean wheel and rebuilt Docker import/doctor/tools/SDK2 pass. Source lint/type/Bandit,
artifact audits, docs/hygiene32tests and browser desktop/mobile zh/en pass. Previous
extension199tests/package/install checks still apply (no extension/harness changes).
Both prior CI failures are documented: stale metadata fixture at2dde288, then legacy
Python3.10 NUL rejection at7dae1a3; all other latter-run platform/unit/integration jobs
passed. The NUL correction preserves source/value/positions; no tests were disabled.
Temporary Docker staging was restored with exact hashes/mtimes; obsolete owned builder/
image and terminal private Python3.10 environment/full-test scratch were cleaned.
Push scoped code/docs correction, then require new exact-head CI/Pages/public proof.
Public1.4.0/future1.4.x, no tag; original broad goal remains active.

## Native delimited Python3.10 NUL compatibility

CI35429684191 at7dae1a3 passed every functional platform/unit/integration job except
Python3.10: its stdlib csv rejects NUL on read/write (upstream71767/97503). Newer
Python accepted the existing long-field fixture. Add reversible, syntax-disjoint
single-scalar masking only around csv calls; original bytes/text/positions and values
stay exact. Regression covers real marker collisions, custom quoting/escape dialects,
NUL and native offsets. An initial new assertion compared neighbor context across
an edit; corrected it to preserve the field/spans while expecting updated context.
Python3.13 focused36pass; clean isolated Python3.10 unit+actual SDK2 37pass13.91s.
Runtime source changed; rebuild/recheck wheel/container and rerun default Codex,
full suite and exact-head CI/Pages before publication. No version/tag change.

## Native delimited final-state recheck

Corrected metadata fixture plus explicit CSV cross-platform inventories pass the
full local suite:3,009 passed/35 optional skips126.46s. Focused hygiene7pass;
workflow/static/harness checks and live GitHub metadata/labels pass. Runtime source
is unchanged from the actual Codex/wheel/container proof. Release docs now disclose
the first CI fixture failure and final full run. Push the scoped correction, then
require fresh exact-head CI/Pages and public-byte proofs. Version remains1.4.0/1.4.x.

## Native delimited CI correction — canonical metadata fixture

Exact head2dde288 CI35429278596 exposed3 GitHub hygiene test failures: after the
local full suite, the docs commit added CSV/TSV to the canonical description but
its fake-gh fixture still returned the previous description. Runtime/CSV code is
unchanged. Synchronize the explicit fixture and retain real metadata drift/read-only
assertions; focused hygiene7tests pass. Add CSV unit/service cases to the explicit
Python3.10/macOS/Windows format inventories. The final combined full suite is running.
Preserve source/actual/wheel/container SHA361a1a78…0f92c9. No new model run needed.
Pages35429278048 and five public files matched2dde288; final-head CI/Pages/public
proof must be renewed after correction. Public1.4.0/1.4.x, no tag; goal stays active.

## Native delimited publication checkpoint

Source commit b8d4fb46fc27257c0abdc3850a30cea28f26087c contains26 counted source/spec/test files plus4 MEM.
This documentation commit updates CSV/TSV guides, both READMEs, bilingual Pages,
release evidence, roadmap/changelog, canonical GitHub description and five synchronized
assistant harness assets. Full gates and actual default Codex proof are recorded above.
Public remains1.4.0; changes accumulate within Unreleased1.4.x without a new tag.
Push both scoped commits directly to main, then verify exact-head CI/Pages/public bytes.
The broader goal remains active; no blanket all-format or arbitrary-document guarantee.

## Native delimited files — release gates passed

CSV/TSV implementation and docs are ready for two scoped direct-main commits.
Full pytest: 3,009 passed / 35 optional skips in 127.59s; actual default Codex:
101 successful calls / 0 errors / 4 region PNGs in 179.79s. Exact byte histories,
complete reads, three region-to-field assertions and both Wikis pass independent audit.
Ruff/format (603 files), mypy (264 source files), Bandit/zizmor, uv audit (214 packages)
and npm audit pass. Extension: 199 tests, 64 package-content files / 66 VSCE files,
fresh/update install pass; local activation remains unavailable without a display.
Clean Python 3.10 wheel install/doctor/tools/SDK2 and Docker runtime/doctor/tools/SDK2
pass. Source/actual/wheel/container SHA:
361a1a78d28ffd453af75d7051e50083de3c347b7ea280229719aee8520f92c9.
Docker: cb7d5ffe9e551a6f83f24dd456c761aaac35b27df833f0bb11378d6925a44bad.
Browser zh/en desktop/mobile, navigation/overflow/console, docs25tests, generated site
and bundled harness sync pass. GitHub description includes CSV/TSV; labels synchronized.
Owned temporary Docker staging is restored with exact hashes/mtimes. Terminal full-test
scratch and replaced owned image/builder were removed; unrelated project artifacts retained.
Public version1.4.0 and future1.4.x remain; no tag. Exact-head CI/Pages/public proof follows
push. Broad original goal is active; JSON/text/web/media and real corpus remain open.

## Native delimited files — runtime and actual Agent verified, publication pending

Native CSV/TSV now supports exact string creation/read/cell/row/column CRUD, source
byte/char/line evidence, explicit dialect/encoding, process isolation, selections,
derivations and dialect-bound Wiki. Required row separators/sole empty-field quotes
are deterministic recorded repairs. No-op reports are complete without history.
Identical bytes may recur with newer receipts; complete reads check text hashes.

Focused SDK2/unit33passed12.55s; fullpytest3009passed35optional-skips127.59s.
Actual default Codex101successful/0errors179.79s,4regionPNGs,3per-fieldclaims,
6historyevents and2Wiki snapshots passed independent CSV-byte/raster/readback audit.
Artifacts:/dev/shm/asset-aware-codex-delimited-01; audit.json retains proof.
SourceSHA361a1a78d28ffd453af75d7051e50083de3c347b7ea280229719aee8520f92c9.
The all-enabled contract initially exceeded its response cap; repeated overview
prose was compacted without dropping operations/schema fields,159discovery tests pass.
Public1.4.0 / Unreleased1.4.x; no feature bump/tag. Packaging/container/browser and
exact-head CI/Pages proofs are pending. Broad original goal remains active.

## Native delimited files — in development

Previous PDF-region milestone3ccc559e4191c681ed9d3201956e46d12a8c99de is fully
published:CI35426746738 all10,Pages35426746411 all3,public5exact; proof at
/tmp/asset-aware-regions-publication-proof.json. Prior pending entries are historical.

Authoritative audit: CSV/TSV assets currently retain whole-file bytes but have no
native cell/row/column CRUD or field evidence. Implement the complete delimited-file
workflow in docs/specs/native-delimited-files.md, preserving encoding/quotes/EOL and
splicing exact native bytes. Python csv supplies values in a bounded worker; explicit
dialect avoids unverifiable sniffing. References/derivations/Wiki extend across the
new format; Agent owns meaning and rendered review. JSON/text/web/media and real
corpus remain part of the original active goal. Public1.4.0 / Unreleased1.4.x; no tag.

## Native PDF region publication checkpoint

Source commit 1b62c4ed61e351821f0c3a4f1a29cb667f2d015c contains23 counted files plus5 MEM.
Final fullpytest2967/35skipped114.02s and actual default Codex82/0/5regionPNG218.02s
pass; source/actual/wheel/Docker SHA match. This documentation commit updates both
READMEs, Wiki/bilingual Pages, roadmap/current project brief and synchronized
assistant harness. The docs link checker now stops at the actual closing parenthesis
instead of consuming later external links; complete docs/full tests pass.
Public1.4.0 / Unreleased1.4.x, no new version/tag. Both scoped commits go directly
to main; exact-head CI/Pages/public-byte verification follows. Goal stays active.

## Native PDF regions — verified locally, publication pending

Implemented read_pdf_region with full source/page/geometry-bound references,
displayed CropBox fractions and actual bounded process-rendered PNGs. Preview
resolution is not identity. Native verify, parsed selections, derivation endpoints
and portable Wiki preserve exact region records, PNGs, renderer metadata and PDFs.
External-source citations never inherit target bibliographic metadata; missing
fields are explicit. MCP checks mechanics; Agent chooses regions/transcription.

Full pytest2967 passed/35 optional skips114.02s; SDK2 scan/region/Wiki/history passed
6.95s. Actual default Codex82 successful calls/0 tool errors218.02s,5 region PNGs,
three distinct cells and per-cell assertions; historical PDF/workbook evidence and
two Wiki snapshots passed independent audit. Initial scan pixel-equality assumption
was corrected in the auditor: exact fresh direct-render replay plus full-page crop
geometry/mean-error comparison. Shifted-PNG-with-rehashed-digest regression passes.
Vector geometry matrix remains pixel-exact. No broad real-file fidelity claim.

SourceSHA66238a84dc4ced0c30f64c2aedd64d2da86ed24f3b28aa0386a8a307a62f575d
matches actual Codex, built wheel and Docker e2170ffc6e86be08beb8df4ac7bf307832f1a4e0d6c03eabf5e3bff40370c434.
Ruff590/mypy257, Bandit/zizmor, Python214-package and npm audits pass. Extension199,
package66/install/update, clean wheel runtime/SDK2, Docker runtime/doctor/tools/SDK2,
zh/en desktop/mobile browser and docs/harness/metadata/labels pass. Local activation
not run without display. Wheel first hit temporary-space exhaustion; after cleaning
only owned terminal scratch and restoring staged evidence, retry passed. Eleven
older evidence directories restored with identical hashes/mtimes; other work untouched.

Proof:/tmp/asset-aware-regions-local-proof.json. Source/spec/tests and human docs/
website/harness are separate scoped main commits, followed by exact CI/Pages/public
byte checks. Refresh stale roadmap and original narrow project brief from current
scope. Public1.4.0 / Unreleased1.4.x, no bump/tag, no subagents; broad goal active.
Previous layout milestone c1f9bed4f92325fb70ef013f7f248cdc3be328d7 fully published:
CI35424758902 all10, Pages35424758353 all3, public5 exact. Older pending entries below
are historical. Original dirty detached user worktree remains untouched.

## Worksheet layout publication checkpoint

Source commit 94c0fbbd59fa36721c297cd18496ea909159f486 contains25 counted files plus5 MEM.
Final fullpytest2931/35skipped105.17s and actual Codex125/0/9PNG194.47s pass.
This documentation commit updates README/wiki/bilingual site and synchronized
assistant assets, retaining public1.4.0 / Unreleased1.4.x. Both scoped commits go
directly to main; exact CI/Pages/public-byte verification follows. Goal stays active.

## Worksheet layout correction — verified locally, publication pending

Implemented read_worksheet_layout/update_worksheet_layout with explicit dimensions,
reset/visibility, complete hash-pinned receipts and one CAS. Preserve native cell
identity/content/styles, Table/merge structures, interval metadata and authored
DrawingML/VML anchor modes. Default-hidden absent rows stay hidden; sparse row
creation uses ordered lookup. Formula/chart caches invalidate for Agent recalculation.
MCP checks mechanics; Agent selects sizes and reviews actual frozen PDF images.

Final fullpytest2931 passed/35 optional skips105.17s; real Calc/SDK2 passed6.75s.
Actual default-model Codex125 successful calls/0 tool errors/194.47s,9 deliveredPNGs,
four workbook versions, complete dimensions/receipts/pages, historical cell/PNG
proof and exact Wiki attachments. Source text/formulas/styles/visibility preserved;
First/Last row1=36points, Hidden columnA rawwidth24 correct observed top/right cuts.
Independent equal-scale title pixels: red1196→2956,blue1063→2729. These are one
synthetic workbook's corrections, not general Excel fidelity certification.
Evidence:/dev/shm/asset-aware-codex-workbook-layout-02. Earlier run01 completed136
calls/14 rejected oversized schema reads/170.34s; errors retained. Final rerun follows
sparse-row optimization; no schema limits were weakened. Full01:2924/35;full02:2930/35;
full03 is the final2931/35 run. Browser first attempt exposed a new unsupported
fragment link; corrected the document link and verified both languages/viewports.

SourceSHA c90cac3ea6ca64d70a923c84df22318123d9768adbd8823b555a82bb25c5f195
matches actual Codex, wheel and Docker393359eef35d08baeb2d7a00505c06f0c70176fdbc22efe8d4cf8f9ae2821f6d.
Ruff581/mypy253/Bandit/locked audit214zero/npmzero/zizmor passed. Extension199,
VSIX package/install-update, clean wheel and Docker import/doctor/list/SDK2 passed.
Local GUI activation unavailable. Browser plugin absent; Playwright desktop/mobile
zh/en navigation, console and overflow passed; mobile screenshot inspected.
README/wiki/bilingual site and bundled harness synchronized; metadata/labels checked.
Proof:/tmp/asset-aware-layout-local-proof.json. Public stays1.4.0 / Unreleased1.4.x,
no tag/bump. Direct-main source/docs commits and exact CI/Pages/public proof follow.
All11 temporarily staged owned terminal runs restored with exact hashes/mtimes;
only the completed builder and superseded owned runtime removed. Current image and
real-Codex evidence retained. Original dirty detached user worktree untouched.
Overall goal stays active.

## Worksheet layout correction — in development

Version policy reconfirmed: public1.4.0 / Unreleased for1.4.x, no per-task bump/tag.
Previous rendition milestone fully published at e09bd566552ce1a62306a255b0722494ad38a2e6:
CI35422734715 all10 and Pages35422733329 all3 passed; public5 files exact.
Proof: /tmp/asset-aware-rendition-publication-proof.json. Older pending entries
below are historical. Original dirty detached user worktree remains untouched.

Next: explicit native row height/column width/reset/visibility, complete dimension
read-back, authored object anchor behavior and Agent rerender correction. Preserve
source revisions and immutable PDF evidence. Spec:docs/specs/native-worksheet-layout.md.
No automatic semantic/visual verdict; full cross-format goal remains active.

## Workbook rendition publication checkpoint

Source commit 890f5f09898d95de0f492f4a35f6e725968747de contains22 counted files plus5 MEM.
Final local fullpytest2896/34skipped103.89s and actual Codex232/0/11PNG proof pass.
The documentation commit updates README, Wiki, bilingual site and synced assistant
assets, retaining public1.4.0 / Unreleased1.4.x. Both scoped commits go directly to
main; exact CI/Pages/public-byte validation follows. Overall goal stays active.

## Workbook renditions — final local verification

Pytest2896passed34skipped103.89s; optional real Calc/SDK2 passed10.83s. Actual
Codex232 calls/0 errors/11 PNGs184.70s; independent PDF/workbook/Wiki audit passes.
Source, wheel and Docker hashes match. Full release gates passed; proof retained
at /tmp/asset-aware-rendition-local-proof.json. Source/docs main commits and exact
CI/Pages/public validation follow. Public remains1.4.0 / Unreleased1.4.x. Whole
goal active; actual whole-sheet clipping identifies the next Agent correction task.

## Workbook PDF renditions — in development

Version policy reconfirmed: public1.4.0, Unreleased/future1.4.x; no task-based bump.
Previous Table totals milestone fully published at8d4949550f7ff1bb1c349c60825c8fadaf2c629a:
CI35420519911 all10 and Pages35420519468 all3 passed; five public files exact.
Proof:/tmp/asset-aware-table-totals-publication-proof.json. Earlier pending entries
below are historical; original dirty detached user worktree remains untouched.

Doing: revision-pinned immutable XLSX-to-PDF renditions using optional Calc, with
explicit print/whole_sheet and recalculate/prefer_cache choices, complete source
receipt and existing PDF page PNG/evidence/Wiki reuse. Spec:native-workbook-renditions.
Private Calc7.3.7 probe shows print2 versus whole4 pages (blank+hidden included),
print-area differences and real text overflow clipping. OOXMLRecalcMode0 renders3
for=1+2 while cached mode renders999. Source bytes remain exact. These probes are
not a cross-version Excel fidelity verdict. Add regressions, real SDK2 and actual
Codex review before publication; overall cross-format goal remains active.

## Native Table totals lifecycle — source committed; docs/publication pending

Explicit add/remove/reuse landed in the private Table edit path, retaining typed
row intent, data/filter membership, style choices, original receipts and source
footprint checks. Kept direct structured references become pre-removal ranges;
current-row selectors in header/totals contexts reject per Microsoft semantics.
No worksheet rows move implicitly; MCP checks mechanics, Agent reviews results/layout.

Final source SHA 5380c98cf192e251ef7ba1a96c48e952811adde1f8c801a52377f020bb2aa0e7 matches actual Codex, wheel and Docker
sha256:e21a09b7850065a873711832dc7b9b90cde2652f1a9e33c809146c1e0c0f0b8b. Pytest2834 passed/33 optional skips (103.42s), Ruff555,
mypy245, Bandit, locked audit214/no findings, npm audit0 and zizmor high passed.
SDK2 lifecycle, CAS/read-budget rollback and independent package regressions passed.
Actual Codex 201 successful calls/0 errors/181.76s, one scanned MCP PNG,
five complete history entries, historical007 proof and two exact Wiki snapshots:
/dev/shm/asset-aware-codex-table-totals-02. No Excel rendering/recalculation claim.
Extension199, VSIX contents/install-update, clean wheel and Docker MCP smoke passed;
local activation not run without display. Browser zh/en desktop/mobile and docs25
passed. GitHub metadata/labels synchronized. All11 owned temporary evidence moves
were restored with exact hashes/mtimes; original dirty user worktree unchanged.

Proofs: /tmp/asset-aware-table-totals-local-proof.json and source-proof.json.
Previous main2882ade CI35418513200 all10, Pages35418512785 all3/public5 files verified.
Source commit b28e35a2e6791ae00605eabdb03da90c1c9dbe4b (21 counted files +4MEM) complete.
Docs/site/harness changes cover22 counted files +2MEM, including explicit1.4.x policy.
Next: push both direct-main commits, then exact-head
CI/Pages/public-byte verification. Public1.4.0 / Unreleased1.4.x; no bump/tag.
Overall cross-format CRUD/evidence/real-Codex goal remains ACTIVE; not complete.

## Native Table creation — verified locally, publication pending

Implemented add_workbook_table over exact worksheet/range/revision: ordered columns,
matching rich/shared headers or explicit blank fill, calculated policies, blank
reserved totals rows, native styles, unique package identities including detached
Tables, protected/overlapping geometry/source checks and one CAS. Shared full Table
XML/cell/package readback plus combined16MiB public receipt checks run before commit.
A reproduced openpyxl empty workbookProtection failure is fixed; empty/false flags
are preserved while active/password/unknown guards stay enforced.

Final fullpytest:2764passed33skipped100.36s; creation45, SDK/schema143, docs25.
Actual Codex:73successful calls/zeroerrors109.47s from image-only PDF through new
XLSX and native Table; independent openpyxl/ZIP/trace/history/2Wiki audit passes.
No supplied native template; no Excel rendering or formula-evaluation claim.
Evidence:/dev/shm/asset-aware-codex-table-create-01;
/tmp/asset-aware-table-create-local-proof.json. Source SHA dafa47275927b0d647c8019b365db1eb6e0837b793a6edde6f1202281db41c6d
matches actual Codex, wheel and Docker b26cdeafc779. Ruff544/mypy242/Bandit,
lock/security214zero/npmzero/zizmorhigh, extension199/package/install-update,
artifact audit/wheel/Docker SDK2 and zh/en desktop/mobile browser passed. Local
VSIX activation unavailable without display; CI platforms must verify after push.
GitHub metadata/labels synchronized. Temporary disk staging restored all11 owned
completed synthetic runs with exact hashes/mtimes; unrelated artifacts untouched.

Next: segmented main commits/push, exact CI/Pages/public-byte checks. Public1.4.0 /
Unreleased1.4.x; no newtag. Broader goal stays active: existing Table totals lifecycle,
identity moves, cross-format real-corpus fidelity and evidence workflows.

## Native Table creation — in progress

Previous goal turn made progress: exact main6068125 CI35416560142 attempt2 all10
jobs passed after the pinned CJK download timeout; Pages35416559607 all3 passed;
all5 public site files matched. Proof: /tmp/asset-aware-table-edit-publication-proof.json.

Current work adds add_workbook_table over explicit current worksheet ranges,
with native header/data/formula/totals/style preservation and one revision commit.
Specification: docs/specs/native-table-creation.md. SDK2, actual Codex scan-to-table,
independent package/evidence audit and full release gates remain required.
Public1.4.0 / Unreleased1.4.x; original user worktree stays untouched. Broad goal active.

Core native Table editing committed as642e3b2. Documentation/assistant parity is
the second scoped commit before main push. Final local proof is retained at
/tmp/asset-aware-table-edit-local-proof.json; final2716tests and Codex03/66calls
pass. Exact CI/Pages/public-file verification remains the immediate publication
step. Public1.4.0 unchanged; Unreleased1.4.x. Whole goal is still active.

## Native Table column editing — verified locally, publication pending

Done: exact native Table column/header/calculated/totals edits, preserved rich runs
and original parts, stable IDs/structured references, source-schema guards, combined
readback budget before CAS and original-revision before receipts. Generic guards
remain. Final pytest05:2716passed33skipped99.21sec; actual Codex03:66success/0errors,
132.75sec, independent scan/native/history/Wiki audit passed. Source SHA07e8fcbe8627f93cded1a89af22dbd2423b203f210ba792bd3f3dd13e360edcc
matches wheel and Docker. Local quality/security/extension/artifact/runtime and
browser checks passed. No local VSIX activation or Excel render/recalculation claim.
Earlier capacity/Wiki/audit/receipt defects were reproduced and corrected; prior
successful audits without the new receipt check do not certify the final behavior.
Doing: scoped main commits/push and exact CI/Pages/public verification.
Public1.4.0 / Unreleased1.4.x. Independent native Table creation, totals-row lifecycle,
axis moves and wider cross-format real-corpus/fidelity goal remain active.

## Native Table column editing — in progress

Revalidated main0d0e65b clean; previous version-policy-only turn was no progress.
Table expansion is already published/verified (CI35413821293, Pages35413820003,
five public byte checks), superseding historical pending entries below.
Implement exact Table header/column rename, calculated-column policy and totals
edits; preserve native styles/references and evidence. Tests and actual Codex
verification precede publication. Public1.4.0 / Unreleased1.4.x; whole goal active.

Core native Table expansion committed as b4e797e; the accompanying documentation,
bilingual site and synchronized assistant assets form the next scoped commit. All
local checks and actual Codex proof passed; push and exact CI/Pages checks follow.
Public remains 1.4.0 / Unreleased for 1.4.x; overall goal is active.

Final verification: pytest04 passed **2678 tests,33 skipped in96.90sec**;
Docker import/doctor/list/stdio and clean wheel02 installation/runtime/stdio passed.
GitHub metadata/managed labels and all artifact gates passed. Local proof:
/tmp/asset-aware-table-expansion-local-proof.json. Exact CI/Pages/public proof still
awaits the scoped commits/push; overall goal remains active.

## 2026-09-19 — explicit native Table expansion and generated A2T intent

Done locally: Table boundary selection at exact intermediate part/ref, stable native
columns, generated headers/calculated cells, synchronized Table/filter/sort extents,
complete read_workbook Table inventory and A2T native_generated resolution in one
native CAS. Original and frozen evidence retain their source revisions.
Actual Codex82calls/zeroerrors/150.48sec audit passes, including real scan PNG,
20 final literal cells, native formulas/IDs/membership, complete reads, frozen/live
workspaces, historical007, untouched PDF/XLSX and two revision-specific Wikis.
No native Excel rendering/formula evaluation claim; template was supplied.
Source hash dda6223ec8f8f23d82cf1fd7deccfabb44e73252a1f2f103c1bb1690180cb3c6.
Full suite02 passed2667+33skips;11 audit regressions added and pass. Final04 pending
following resource-only exit120 in03. Docker and wheel retries pass after removing
only own completed builder/smoke/pytest temporary artifacts; original worktree and
actual evidence preserved. Docs/browser/harness, extension/package/install-update,
source/security checks passed. No local VSIX activation; CI must cover it.
Doing: finish publication gates, segmented main commits/push and exact CI/Pages.
Public1.4.0; Unreleased/future1.4.x. Native special Table edits/moves and broad goal
remain unfinished.

## 2026-09-19 — explicit native Table expansion in development

Previous turn was progress: main 3e9d6ee equals origin, CI35411992629 all10 jobs and
Pages35411992117 all3 passed; five public files match. Evidence is retained at
/tmp/asset-aware-a2t-grid-publication-proof.json. Original user worktree is untouched.
Public stays 1.4.0; development is Unreleased within 1.4.x, no automatic tag/bump.

Doing: explicit per-grid-insertion Table membership, matched by exact part and
intermediate expected_ref. Extend table/filter/sort extents, retain column identities
and generate header/calculated cells. A2T needs explicit native_generated intent;
missing and blank retain their current meaning. Test full packages, stale requests,
SDK2 and actual Codex. Specialized table header/formula/totals edits, source-axis
moves, richer cross-format fidelity and real-corpus evidence remain open.

## 2026-09-19 — A2T structural bridge verified locally and by actual Codex

Native-grid publication is complete at df1f26a; CI35409819540 all10 and
Pages35409818898 all3 passed, public bytes matched. Core commit156885b provides
stable column identity, fresh recreated row/column IDs, legacy snapshot compatibility,
typed native column defaults and explicit structural_plan application in one native
CAS commit. Original rich payloads/formulas/styles, complete destination readback,
historical snapshots/source evidence and late conflict handling have regressions.

Final full suite2642passed33skipped (94.77sec), including6 new audit tests. Actual Codex audit
passed86calls (84successful,2recovered native-contract query errors),178.67sec;
evidence /tmp/asset-aware-codex-a2t-grid-01. Source runtime hash matches the run.
All local publication gates passed: source checks, extension199, artifact/wheel/
Docker/VSIX install-update, docs/browser and metadata/labels. No local activation
because no display/Xvfb; CI will verify it. Proof /tmp/asset-aware-a2t-grid-local-proof.json.
The final documentation commit, push and exact CI/Pages/public checks remain. Native Table boundary expansion/specialized edits,
reordering and the broad goal remain open. Public1.4.0; future1.4.x, no auto tag/bump.

## 2026-09-19 — native grid application and Codex workflow verified

Configured update_worksheet_grid is available through MCP SDK2 with complete
contract/schema discovery, exact revision/CAS checks and operation receipts.
Static named pivot/consolidation sources resolve scoped name chains, A1 ranges
and structured table selectors; unresolvable dynamic dependencies fail explicitly.
Contract paging considers the complete response size, not just its schema.

2623 pytest passes, 33 optional skips (93.13 seconds); extension 199 passes and
64-file package check; Ruff, format, mypy, Bandit, lock and dependency/workflow
audits pass. Actual Codex made 126 successful MCP calls with no tool errors;
independent audit passes for scan-to-XLSX values, grid insert/delete, historical
selection/derivation integrity, source preservation and revision-specific Wikis.
It does not certify Excel rendering or formula evaluation. Auditor regressions
cover repeated content revisions and required complete pre/post-operation reads.

Evidence: /tmp/asset-aware-grid-pytest-04.log,
/tmp/asset-aware-grid-extension-01.log and /tmp/asset-aware-codex-native-grid-01.
Artifact, wheel/runtime/stdio, Docker, VSIX install/update, browser and metadata
gates pass; /tmp/asset-aware-grid-local-proof.json pins the source/site/lock hashes.
Local VSIX activation was not run because no display/Xvfb is available. Four
segmented commits from base 11ddd92 comprise core 397a024, 853460f, b86a5ae and the
pending documentation commit; exact CI/Pages verification remains after push.
Structural A2T writeback remains unfinished. Public stays 1.4.0 with
Unreleased/future 1.4.x; no tag or original user-worktree changes.

## 2026-09-19 — native table/drawing package integration, still private

Private NativeWorkbookGrid now applies sequential row/column changes to actual
XLSX packages with stable table columns, structured formulas, merges, drawing and
note geometry, cross-sheet references, pivot locations, watches and outline levels.
Independent openpyxl reads cover rich packages; exact XML/member readback rejects
serialized tampering. Pictures retain exact embedded bytes. Comments retain rich
payload/authors and delete only the corresponding note shape. Geometry records
explicit 96-DPI assumptions; rendering and actual recalculation remain Agent work.

217 focused tests plus five metadata dependency tests pass; Ruff 489 files,
mypy 226 sources, Bandit, docs-site and release-harness checks pass. Full pytest
passed 2525 tests, 33 optional skips in 87.71 seconds; log
/tmp/asset-aware-grid-pytest-02.log, using its own temporary /dev/shm directory.
Indirect named source dependencies, public application/contract/CAS wiring,
structural A2T and actual SDK2/Codex workflow remain open. No helper-only completion
or public operation is claimed. Working main unchanged at 11ddd92, no commit/push,
tag or version bump; public stays 1.4.0 and planned releases stay 1.4.x.

## 2026-09-19 — native grid internals in progress, not exposed or released

Public version remains 1.4.0, future work 1.4.x; main base 11ddd92 is unchanged and
current grid changes remain uncommitted. Typed grid transforms, original XML cell/
format relocation, merge anchor policies, relative rule rebasing, shared formula
expansion, array/data-table range handling, cross-part/scoped formula rewrites and
cache invalidation, views/freeze/selection and print breaks now have focused tests.
Escaped structured headers and second-endpoint table dependencies also fix defects
in the existing formula parser; external qualifier inheritance remains intact.

127 focused tests passed; Ruff 465 files, mypy 211 sources and Bandit passed. Full
pytest passed 2440 tests, 33 optional skips, in 87.48 seconds with a task-owned
/dev/shm basetemp; log /tmp/asset-aware-grid-pytest-01.log. This is
implementation progress only: no native grid contract/API, structural A2T workflow,
complete rich-package read-back, actual Codex grid run or release proof yet. Continue
table/filter/sort identities, structured refs, comments/drawings/VML, package/app
integration and full workflow verification before publishing. Original user tree
is untouched, no version bump/tag, and the broad goal remains active.

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

## 2026-09-18 active goal — not complete

- [x] Native PDF page collaboration implemented and locally verified: create/read/
  render/copy/insert/delete/reorder/geometry, source lineage, immutable evidence,
  wiki and explicit source writeback. 1,739 Python tests pass / 30 optional skips.
  SDK2 and Codex scanned run 02 pass all seven independent checks (49 MCP calls,
  zero errors; exact final transcription). No new version: public 1.4.0 / Unreleased.
- [x] Native PDF runtime e47ad9f and tests/docs 4af244d pushed; Pages 35349131496
  passed with exact public bytes. CI follow-up adds PDF to explicit platform/SDK2 lists.
- [x] Final 44568f7 CI 35349396027 (all ten jobs) and Pages 35349393804 passed.
- [x] Native PPTX picture add/replace/read/extract and native-file-ref-v1 implemented.
  Exact media, shared-image isolation, lineage, CAS and immutable evidence/wiki tested.
  1,790 Python tests / 199 extension tests; two real Codex picture runs each 38 calls,
  zero errors, three actual image deliveries and independent package/shape audits.
  Source hashes match the evaluated runtime. Public remains 1.4.0 / Unreleased.
- [x] d46fdce picture checkpoint: exact CI 35353663631 and Pages 35353662373 passed.
- [x] Native editable PPTX table creation, grid sizes/direct formatting/merges,
  existing run edits/deletion/evidence/wiki and guarded source writes implemented.
  Typed citation preset/template schema added after an actual Codex input failure.
  Scanned PDF -> native table run 02: 66 calls, zero errors, exact first transcription;
  run 01 recovery retained. 1,857 Python tests / 199 extension tests pass.
- [x] Table checkpoint 8c7548b: exact CI 35358045055 (ten jobs, including Linux
  activation) and Pages 35358043487 passed; public site bytes match. Version 1.4.0.
- [x] Cross-asset derivation ledger with verified native references, separate agent
  review assertions, append-only corrections/retractions and portable Wiki implemented.
  1,909 Python tests / 199 extension tests; real Codex runs 02/03 pass independent
  derivation/PPTX/source audits with 93/92 calls and zero MCP tool errors.
  Final runtime run 04: 96 calls, zero MCP tool errors; retained initial auditor
  restart false-positive and model-reported diagnostics; 3 restart regressions pass.
- [x] Derivation checkpoint cea4870 pushed; CI 35363142564 (ten jobs) and Pages
  35363141517 pass at exact HEAD; public bytes match. Public stays 1.4.0.
- [x] Native PPTX table row/column insertion, deletion, resizing and merged-cell
  rebasing implemented. 1,971 Python / 199 extension tests pass. Actual Codex grid
  run 01: 123 calls, zero tool errors, five independently verified intermediate
  revisions and unchanged source/package evidence. Full slide rendering not claimed.
- [x] Grid checkpoint 6cb054b pushed; exact CI 35366326974 (ten jobs) and Pages
  35366597637 pass, public bytes match. Public remains 1.4.0.
- [x] Native table merge/split with explicit content policy and paragraph XML
  preservation implemented. Full 2,015 tests / 30 skips plus additional regression
  pass; 199 extension tests pass. Codex --grid --merges: 180 calls, zero errors,
  exact first transcription, 13 full records and 11 independently audited stages.
- [x] Merge checkpoint local release gates pass (including Docker, VSIX, clean wheel
  and browser QA); initial disk-exhaustion failures retained and successfully rerun.
- [x] Merge checkpoint 68153e3: exact CI 35369646303 (ten jobs), Pages 35369645315
  and public bytes verified; clean main and public 1.4.0.
- [x] Native PPTX slide layout discovery, insertion, ordering and deletion implemented.
  Full 2,068 Python / 199 extension tests pass. Actual Codex --slides: 96 calls,
  zero errors, exact first transcription, eight full records, three independently
  audited intermediate revisions. Source/publication/wiki/historical evidence pass.
- [x] Slide checkpoint local release gates, Docker, clean-wheel, installs and browser QA pass.
- [ ] Slide checkpoint: commits, push, exact CI/Pages pending.

- [x] Unreleased checkpoint: native PPTX textbox addition / existing shape deletion
  with reference, dependency, version and XML preservation guards; truthful A2T
  row-ID results after earlier-row deletion. 1,647 Python tests / 199 extension
  tests pass. Real SDK2 CRUD/writeback and scanned Codex run (49 calls, nine checks)
  pass; first transcription errors were corrected and retained in evidence.
  Docs/README/harness/assets/Pages sources synchronized, public version stays 1.4.0.
  Exact commit ab49252 CI 35342913394 and Pages 35342912718 passed.
- [ ] Broader structural CRUD remains: slide manipulation, broader non-text creation,
  full format coverage, opaque dependency handling and real-document evaluation.

- [ ] Goal item 7: real Codex MCP PDF image-to-structured-data CRUD evaluation,
  independent fixture truth, actual image/tool-call evidence and repeatable SDK
  regressions. The synthetic baseline shipped in 1.4.0; broader coverage is ongoing.
  Baseline implemented: three SDK modes, live mixed/scanned Codex runs, eight
  independent final checks, first-pass accuracy and recoveries recorded separately.
  Messy real-document corpus expansion remains active.

- [ ] Maintain MCP SDK 2.0+ compatibility, evaluate current native-format/PDF
  libraries against official repositories and regression evidence; adopt suitable
  updates without removing format features or bypassing release checks.

- [ ] Native format capability contracts and asset registry: source/components,
  revisions, locators, representations and relationships, including unknown formats.
- [ ] Native read/decompose/create/update/delete/writeback across Word,
  spreadsheets, presentations, PDF, text/web/structured documents and media.
- [ ] Necessary MCP source/version, format and operation-result checks with
  atomic writes; agent-led complete semantic/visual verification and correction,
  with explicit check coverage and unsupported features.
- [ ] Independent table creation and native/A2T round trips preserving cell
  identities, types, formulas, styles and provenance.
- [ ] Cross-format wikilink evidence library with stable targets, attachments,
  provenance and protection of curated notes.
- [x] Versioned custom citation display contracts for existing PDF evidence,
  Foam notes and portable asset exports, independent of canonical provenance.
- [ ] Standards-aware academic citation rendering (APA/Chicago/CSL) and citation
  integration with the remaining native-format evidence adapters.
- [ ] Real-file regressions, README/Pages/metadata/labels/MEM synchronization,
  reviewed staged commits/pushes and fully verified releases throughout the work.

Baseline revalidated; isolated latest main while preserving original user edits.

- [x] 1.4.x development: bounded canonical A2T citation readback with cell/value/hash
  binding, compatible get summaries, and explicit source/meaning review boundary.
  Added 38 regressions plus actual paged readback in the three-mode SDK2 matrix.
  Three live Codex runs pass all nine final checks; the forced-paging run includes
  two continuations and corrected two initial count transcription errors. Preserve
  first-pass failures/recoveries separately. Evidence paths are in activeContext.md.
- [x] 1,584 Python tests / 30 optional skips, 199 VSIX tests/package audit, static
  checks, docs/harness/skills/metadata audits, sync parity and bilingual browser QA
  passed. README/Pages/CHANGELOG mark main development as unreleased; version1.4.0
  remains unchanged. Exact commit CI/Pages must be verified after push.
- [x] A2T row-ID result labels fixed in ab49252; structural CRUD and corpus work remain active.


## 2026-09-18 v1.4.0 published and verified

- User explicitly rejected the proposed 2.0.0 jump and requested 1.4.x. Use 1.4.0
  for this milestone and 1.4.x for subsequent small fixes. No 2.0.0 tag/package
  exists; retain the native discovery migration notice while correcting metadata.
- Version 1.4.0 metadata, lockfile, Docker, VSIX, guides, anchors and bundled
  instructions are synchronized; 35 focused metadata/docs tests pass. Preparation
  commit 929e878 has green CI 35335476121; correction da829fa has green CI
  35335805871 and Pages 35335805355.
- Annotated v1.4.0 points to da829fa6f360bd684fda9b8d31efee3651a9ed94.
  Release workflow 35336169071 passed all eight jobs. Public PyPI wheel/sdist
  match audited local bytes; GitHub/Marketplace VSIX bytes match after HTTP gzip
  decoding. Version/author/native modules/bundled harnesses and public Pages
  source bytes are verified. Hashes and proof paths are in activeContext.md.
- Repeated live mixed-04 is retained as a strict failure: Greek mu versus micro
  sign in one Unit cell, with matching Excel mismatch. Six other checks pass;
  raster appearance alone cannot establish original Unicode identity. Do not
  weaken source comparison or report universal/lossless vision accuracy.

- Codex PDF baseline exposed and fixed rotated figure cropping (10/16 failing
  pixel cases before, 16/16 after). Real mixed/scanned workflows preserve source,
  transcribe 35 cells, cite assets, update/delete/restore and export checked Excel
  plus Wiki bundles. A second scan run corrected two first-pass leading-zero
  mistakes; the initial error remains visible in its independent audit.
- Added an opt-in isolated Codex runner and negative audit guards, plus three
  production SDK2 digital/scanned/mixed CRUD regressions included in CI. Tests
  never silently invoke a model. New section guidance supports image-only PDFs.
- Validation: 1,546 Python passed / 30 optional skips, 199 VSIX tests and package
  checks, lint/format/types/Bandit, docs/harness/skills/metadata audits and asset
  synchronization. Desktop/mobile zh/en guide QA passed with cached pinned CDN
  assets. New corpus baseline adds 53 regressions. Exact release commit CI passed.

- Revalidated clean main@cf7f166 and successful checkpoint CI/Pages. Previous goal
  turn made concrete progress (native schema discovery and PPTX collaboration).
- Released 1.4.0 as requested; native-contract-v2 changes the discovery response
  shape, with an explicit migration notice. Full release harness, exact-tag CI and
  public PyPI/Marketplace/GitHub artifact verification passed. Registry/index
  visibility delays resolved; no tag movement or duplicate publication was needed.
- Next: expose bounded canonical table citation readback so agents can inspect
  precise persisted locators, and expand beyond the synthetic document corpus.
- Structural CRUD, further formats, standard academic citations and complete agent
  review workflows remain active after this publication milestone.

## 2026-09-18 native discovery and PPTX (released in 1.4.0)

- Revalidated clean main@269893f and its green exact-commit CI. Full goal stays active.
- Implemented bounded full-schema retrieval, per-operation discovery sharing
  runtime field guards and explicit native-contract-v2 migration from inline schemas.
  Hash pins reject mixed scope/server versions; encoded excerpts also stay bounded.
- Added 31 discovery regressions and updated real SDK2/DOCX tests. Full Python suite:
  1,454 passed / 30 optional skips. Lint/format/types, docs generation/check,
  harness/skills audit and bundled asset synchronization passed.
- README/zh/native guide/CHANGELOG/Pages and assistant instructions updated;
  changes are on main and included in 1.4.0.
- Discovery commit 1546bd3 has green CI 35329453898 and Pages 35329453179.
- PPTX now supports independent native creation, slide/notes shapes, complete JSON
  component pages, precise existing-run edits, revision-pinned references and exact
  package wiki attachments. Reuses source/CAS/writeback guards. New pptx-shapes-v1
  snapshots preserve older opaque outputs; v1.2 XLSX/v1.3 DOCX goldens remain stable.
- 35 additional presentation/compatibility regressions plus four new operation-schema
  cases pass: full Python 1,493 passed / 30 optional skips. VSIX 199 tests/package
  checks, lint/format/types/Bandit, docs/harness audits and synchronization passed.
- Desktop/mobile zh/en browser QA passed with cached pinned CDNs; English native
  overview reflects the PPTX/schema capabilities released in 1.4.0. Metadata/labels checked.
- Feature commit 2364fee passed all ten CI jobs in 35331710478 and Pages
  35331709690. Published in 1.4.0. Broad structural CRUD, legacy/macro
  formats, academic CSL and complete agent review remain ongoing.


## 2026-09-18 v1.3.0 published and verified

- Annotated v1.3.0 points to 2aba6595453a65aa6fd541b3d93df69c9b041fc6.
  Exact-tag CI 35325369333 and Pages 35325368633 passed. Release workflow
  35325631670 completed all eight jobs, including all three install platforms.
- Public PyPI wheel/sdist match local audited bytes; Marketplace and GitHub VSIX
  bytes match after HTTP gzip decoding. Version, author/publisher, new DOCX modules,
  two native harnesses and exclusion of compiled VSIX tests are checked. Digests and
  verification artifact paths are recorded in activeContext.md.
- Full local release.sh: 1,423 Python passed / 30 optional skips, 199 VSIX tests,
  all audits, package/runtime/Docker/stdio gates passed. CI supplies Xvfb activation.
  Docs/browser QA, repository metadata and managed labels are synchronized.
- Stale status observations required fresh exact-run API queries; the workflow
  itself succeeded. No tag was moved and no duplicate publication was requested.
- Broader native formats, structural CRUD, academic citation engines and agent
  review workflows remain active; this milestone does not complete the overall goal.


## 2026-09-18 v1.3.0 release preparation

- Feature b50ed3505161c486473773cefec8d9f9006ef32f passed all jobs in CI
  35324654138, including Windows/macOS/native tests and Linux extension activation;
  Pages 35324654419 passed. Existing branch protection remains unchanged.
- Synchronized seven version sources, changelog, bilingual README/Pages, extension
  README and harness. Public latest remains 1.2.0 until registry verification.
- Candidate metadata/docs regressions: 32 passed; dependency audits zero known
  issues; desktop/mobile bilingual reader QA and harness audit pass. Next: exact
  release-candidate CI, full release.sh, annotated tag and publication verification.


## 2026-09-18 DOCX component evidence / wiki (released in 1.3.0)

- Complete parsed block representations feed revision-pinned native references,
  bounded read_docx_block and verification. Integrity, head freshness, source
  freshness, extraction coverage and agent meaning/layout review stay distinct.
- DOCX block notes/JSONL, original DOCX and every exact package part export under a
  distinct docx-blocks-v1 projection. Existing opaque DOCX exports remain untouched;
  v1.2 spreadsheet artifact hashes are covered by a golden regression. Custom
  citation display uses native part/block location without changing evidence IDs.
- 1,423 Python passed / 30 optional skips; 199 VSIX tests, types/lint/Bandit,
  docs/harness synchronization and bilingual desktop/mobile reader checks passed.
  Nineteen added tests plus extended real SDK2 native DOCX flow. New cases are
  configured for Python 3.10, macOS and Windows CI; every job passed on b50ed35.


## 2026-09-18 native DOCX version / DFM bridge (released in 1.3.0)

- Native read_docx/update_docx reuse DocxService's existing session/checksum,
  table-shape, unedited-block and pre/post-save checks. DFM projection excludes
  volatile session timestamps, binds the full asset/revision, uses bounded chunks
  and preserves marker order. Writes first create a managed revision, then reuse
  explicit native publish/writeback. Old revisions remain readable after updates.
- Added private workspace and bounded OOXML guards. Preserve every unaffected
  ZIP member; only document.xml and opt-in tracked-change settings.xml may change.
  Signed/protected documents, including relocated signature/settings targets,
  reject updates. Source files remain unchanged on parsing/check/concurrency failure.
- 29 new regressions cover formatted paragraphs/tables/media/header/footer,
  chunk assembly, stale/cross-asset DFM, missing markers/styles, no-op bytes,
  pre/post integrity failures, cleanup, concurrent CAS, tracked author and real
  SDK2 stdio source writeback/backups. Full suite: 1,404 passed / 30 optional skips.
  199 VSIX tests, lint/format/types, configured Bandit gate and reader QA pass.
- Full regression exposed contract response truncation after schema growth.
  Compact annotation titles while preserving named title properties and every
  validation keyword; default-cap and old workbook stdio regressions now pass.
- README/Pages/spec/roadmap and bundled harness distinguish this development from
  published 1.2.0. Python 3.10/macOS/Windows CI now runs the DOCX regressions.
  Pushed bbdbf8a; CI 35321780547 passed all ten jobs and Pages 35321779592 passed.
  No claim of arbitrary DOCX structure/style CRUD, complete rendered fidelity,
  DOCX component citations/wiki, PPTX editing or standards-complete CSL support.

## 2026-09-18 v1.2.0 published and verified

- Annotated v1.2.0 targets dd0224f333bf466a388b1cbc291061a87f70b2d5. Exact-head CI
  35318628716 and Pages 35318627849 pass. Release workflow 35318888092 publishes
  PyPI, Marketplace and GitHub Release after full cross-platform/artifact gates.
- Complete local release.sh passed: 1,375 Python tests / 30 optional skips,
  199 VSIX tests, lint/types/security audits, docs/harness synchronization,
  wheel/sdist clean-runtime checks and Docker SDK2 smoke. CI supplied Xvfb activation.
- Public PyPI bytes match the checked local artifacts and metadata author:
  wheel SHA-256 69de5928349f4e275f591ad17e5fc847a3b872eb31949283c7674fa926780f43;
  sdist SHA-256 f633bb2627af1900ad23f729b95d43a8d2c973b638f9b136ab15f9aafb130eb6.
- Marketplace VSIX SHA-256 22b471546144cdbe1c127b84f8ac65b188f2eb9d7a1349d669fc93c4447a782f
  matches the GitHub Release digest. Version 1.2.0, publisher u9401066, two current
  bundled native harnesses and no compiled test payload are verified.
  Release: https://github.com/u9401066/asset-aware-mcp/releases/tag/v1.2.0
- Native reference/wiki export and PDF curated-note protection are released.
  DOCX/PPTX/general CRUD, spreadsheet structural operations, agent integration and
  standards-aware academic citations remain unfinished; the overall goal is active.

## 2026-09-18 existing PDF bundle protection (included in 1.2.0 preparation)

- Replaced marker-only directory replacement with an injected domain publication
  port and infrastructure inventory/publisher implementations. Verify manifest
  self-hash, bounded complete file/directory inventory, file sizes/hashes and no
  symlinks; preserve manually modified or unexpected content by refusing refresh.
- Recheck the observed manifest token under the OS lock; identical outputs reuse
  files and mtimes. Actual updates retain the former directory and report backup_path.
  Late writes through old POSIX editor handles remain in that backup. Failed or
  competing publication restores the old target when possible or preserves both
  the competing target and named backup. No external-editor serialization claim.
- 18 new data-preservation regressions; focused bundle/citation/SDK2 tests pass 61.
  Full Python suite passes 1,374 tests, 30 optional skips. Ruff/format/MyPy,
  configured Bandit gate and release harness audit pass. Cross-platform CI includes
  these new regressions. README/wiki/Pages explain the unpublished behavior.

## 2026-09-18 native wiki snapshot checkpoint (unreleased)

- Added native/export_wiki through the existing document facade: immutable source
  attachment, complete JSONL cell records/references, a Foam index and cell notes.
  Note identity uses asset/revision/native locator and ignores citation display.
  Other formats export explicitly opaque attachments without invented semantics.
- Native sheet/cell locators drive source/author-year/numeric/custom citation
  display. Agent semantic/rendered/formula review remains explicit. Export limits
  reject entire oversized requests rather than silently truncating evidence.
- New revisions add snapshots and retain old links. Exact repeated exports reuse
  unchanged files; edited/missing/unexpected/symlink entries reject reuse. Source
  and store overlap are rejected. Exclusive new writes plus a manifest-last marker
  report retained partial output; there is no claim of atomic directory visibility.
  Different citation displays for the same revision require separate wiki roots.
- 21 new unit regressions plus the expanded real SDK 2 stdio flow pass. Full
  regression: 1,356 passed, 30 optional skips. Ruff/format/MyPy and the configured
  medium-severity Bandit gate pass; the broader scan lists 17 existing low-severity
  subprocess advisories. No new native-code findings. Assistant asset sync and
  generated docs checks pass; desktop/mobile zh/en reader checks pass using cached
  exact CDN scripts (not a live CDN availability test).
- README/guide/spec/roadmap/Pages and bundled harness distinguish main from v1.1.0.
  Focused native wiki/reference tests now run on Python 3.10, macOS and Windows CI.
  Code is pushed at e3bb2cf; Pages succeeded. CI 35317000129 exposed three Windows
  test-reader failures: the new Unicode tests relied on the cp1252 locale instead
  of specifying UTF-8. Exported bytes are already explicitly UTF-8. Corrected the
  test reads; rerun cross-platform CI before treating this checkpoint as verified.
- Follow-up 6407d31 passed every job in CI 35317215411, including Windows native
  tests/VSIX install, macOS, Python 3.10 and Linux integration. Pages 35317214962 is
  green. Existing PDF bundle publication protection is the next bounded change.

## 2026-09-18 release and native reference checkpoint

- v1.1.0 is annotated at 0e71b4c. Complete local release.sh gates and main CI
  35314228355 pass; release workflow 35314426885 passed all eight jobs.
- PyPI 1.1.0 is published with the correct author. Wheel SHA-256 d5ae3e5c0f7a3e8304aaefc57d305a4fa847321251d54121cf212da78ba3c1d3
  and sdist SHA-256 6788bfafaf8286e447086e2096ef56fa319a692d55f934630fec154e73651c58
  match local checked artifacts exactly. Marketplace and GitHub Release are public:
  https://github.com/u9401066/asset-aware-mcp/releases/tag/v1.1.0
  Marketplace VSIX SHA-256 58b152d33b2b8b614b37febf5ec4199161207feaf54197fb6da3d0faa0700086
  matches the GitHub Release asset digest; package version/publisher/native harness
  and absence of compiled tests are verified.
- Only main remains in local/remote branch lists. Original dirty worktree is
  detached at its unchanged old commit; tracked diff and untracked inventory were
  verified unchanged. No further self-PR workflow; future changes go directly to main.
- Post-1.1.0 native reference verification is implemented: immutable revision
  integrity, exact native locator and complete cell hash; head freshness and
  semantic/rendered/formula review remain separate. Full suite 1,335 passed,
  30 optional skips. Code checkpoint e2fa020 has fully green CI 35315203866.
  README/guide/roadmap/spec distinguish this unreleased addition from 1.1.0.
- Native wiki export and preservation of manually edited generated notes are next.
  Existing PDF bundle replacement checks only its matching marker, so do not reuse
  that publication policy for a curated native evidence library without added checks.

## 2026-09-18 direct-main integration and 1.1.0 preparation (completed)

- User explicitly requested direct code changes without self-PRs. Green b882fa1
  was fast-forwarded to main using the owner's allowed bypass of the approving
  review requirement, without changing protection settings. This supersedes the
  earlier unanswered admin-merge question. PRs #9/#10 auto-completed; remote topic
  branches were deleted. Main is the only remote branch.
- CI 35313470325 passed every job, including native operations on Python 3.10,
  macOS and Windows plus Linux VSIX activation. Main CI 35313709615 also passed.
- Docker native-checkpoint build/doctor/SDK2 stdio pass; Pages deployment from
  b882fa1 succeeded. Preparing 1.1.0 metadata/docs/harness and release gates.
- Version 1.1.0 metadata, bilingual docs, repository metadata contract and bundled
  agent harness are synchronized. Final-version Python regression: 1,326 passed,
  30 optional skips. Complete release harness/tag/registry verification is next.
- v1.1.0 publication is complete; post-1.1.0 native evidence work and the larger
  overall goal remain active.

## 2026-09-18 native file assets — merged to main

- Source-independent registration, immutable revisions, typed native request
  contract, XLSX create and scoped XLSX/XLSM read/update/clear are implemented.
- Explicit publish/writeback/refresh/archive preserve versions, detect stale or
  divergent human edits, retain source backups and report post-write failures.
- Long cell reads retain canonical provenance while returning bounded excerpts;
  literal OOXML escape sequences, formula followers/calc chains, rich text,
  table regions and process-crash lock recovery have regression coverage.
- Parsing, edit guards, deterministic repairs and source publication were split
  into focused modules after regression coverage. The missing English reader mapping
  from the first full run is fixed; the complete rerun passes 1,326 tests with
  30 optional skips.
- Focused native tests: 45 passed including true MCP SDK 2 stdio. Ruff/MyPy,
  Bandit and universal dependency audit pass (213 packages, zero known issues).
- VSIX: 199 unit tests, assistant asset synchronization and 64-file package
  inventory pass. Generated docs/release harness audits and diff hygiene pass.
- Desktop/mobile native reader routes, Chinese/English switching, overflow and
  console checks pass; screenshots are outside the repository. Exact cached CDN
  scripts were reused, so live CDN availability is not covered.
- README bilingual, native operation guide, Pages reader, changelog, roadmap and
  architecture are updated. Commit aa41ddd is pushed in PR #10:
  https://github.com/u9401066/asset-aware-mcp/pull/10 (depends on #9).
- Built wheel/sdist artifact audit, clean-wheel runtime/stdio and fresh/update
  VSIX install smoke pass. Local activation has no display and remains a CI gate.
- Add explicit native fixture/stdio regressions to Python 3.10, macOS and Windows
  CI steps; extension-only smoke did not exercise OS file locks or source writes.
  These CI steps passed; the native milestone is released in 1.1.0.
- Broader native structural CRUD, native wiki/academic citation integration,
  visual verification and other formats remain in scope after this milestone.

## 2026-09-18 citation contract milestone — released in 1.1.0

- Added citation-format-v1 custom/source/author-year/numeric display contracts to
  evidence bundles, Foam notes and portable asset exports. Canonical evidence,
  source hashes, locators and note identities are unchanged by citation style.
- Missing metadata and expression templates fail before publication; failed
  bundle rebuilds preserve the previous managed export. Markdown output treats
  citation content as escaped text. Presets are not full CSL/APA implementations.
- Latest user clarification: MCP performs necessary operation checks; the agent
  owns complete semantic/visual verification and coordinates corrections.
- SDK lock now uses official MCP 2.2.0. Patched HTTPX2/model dependency floors,
  compatible universal lock and npm transitives remove the scheduled audit issues.
- Python: 1,281 passed / 30 optional skips with SDK 2.2.0, including real PDF
  stdio/custom citation export. Ruff, format, MyPy, Bandit, workflow severity gate,
  generated docs and release harness audits pass; both dependency audits are clean.
- VSIX: 199 unit tests, package inventory, assistant asset sync and fresh/update
  install smoke pass. Activation remains unverified (no Xvfb/display in this host).
- Wheel/sdist audit, clean Python 3.10 wheel runtime/stdio and Docker build/doctor/
  stdio pass. Desktop 1440×1000 and mobile 390×844 Playwright checks pass for
  identity, content, language switching, overflow and console health. Exact CDN
  scripts were locally replayed after browser CDN timeouts; live CDN reliability
  is outside this check. Screenshots remain in /tmp, outside source control.
- Commit 07d7c90 is pushed; PR https://github.com/u9401066/asset-aware-mcp/pull/9
  has all 12 GitHub checks green at 36b8cfe. Required approving review is pending;
  ordinary merge was rejected, and admin merge authorization remains unanswered.
  Managed labels are synchronized. Description/topics and Pages deployment await
  merge so scheduled hygiene stays aligned with the authoritative default branch.
- main requires one approving review and the Test Summary status; no tag/release
  has been published, and the branch policy has not been bypassed.
- Native XLSX/PPTX CRUD, generalized asset registration, cross-format wiki adapters
  and standards-aware scholarly formatting remain open; the overall goal is active.

## v1.0.1 validation in progress

- Implemented the bounded streaming MessagePack PDF worker result channel and
  comprehensive fork/spawn, large-binary, timeout, crash, malformed-envelope,
  permission and cleanup regressions. Focused PDF/document tests, Ruff, MyPy,
  Bandit, frozen lock and universal dependency audit are green.
- Implemented MCP stderr logging, empty/blank ingest rejection and the managed
  dotenv-disable switch. The integrated Python run reached 1,138 passed and 30
  intentional optional-backend skips; its sole generated-docs version drift was
  rebuilt and the 16-file docs contract then passed.
- Added a true-stdio PDF asset regression with source/citation/media/Foam/hash
  integrity and deterministic repeat export. The final 15-page Attention paper
  run completed in 3.286 seconds: 27 text, six table and six figure assets,
  435 verified spans, 39 deterministic bundle records and 39 Foam notes; source
  bytes/mtime and protocol cleanliness were preserved.
- Codex CLI 0.147.0 is installed for parser/runtime verification. The VSIX
  semantic TOML parser bundle passed packaged activation smoke; final version
  alignment, local Codex config migration and `v1.0.1` release remain pending.
- Independent VSIX review found and fixed destructive Codex policy merging:
  extension-owned launch/env fields are rebuilt, while primary approval/future
  keys and nested `tools.*` tables are byte-preserved through update, opt-out
  and re-enable. Opt-out uses a non-executable `enabled=false` transport shell
  only when policy remains. Focused tests, all 185 VSIX tests, real Codex CLI
  parsing in all three states, npm audit, package audit and release harness pass.
- Closed the remaining global-config trust boundary: untrusted/lookalike
  workspaces cannot write Codex, Cline or Copilot settings, and production
  external-consumer launches are pinned to the extension version with isolated
  globalStorage data/cache instead of local source or workspace `.env`.
- Rebuilt the website and docs reader around the Evidence Rail contract,
  exact 30-tool explorer, install and development/release guidance, and GitHub
  navigation. Desktop and 390px Playwright screenshots, route/search/language/
  copy/mobile-menu/sidebar interactions and console/overflow assertions pass.

## Done

- 將 stale local checkout 快進至已發布 `v0.9.0` 基線；原始 dirty
  worktree 完整保存在 `pre-v0.9-sync-2026-08-13` stash。
- 完成 GitHub 收斂：關閉 PR #3/#4/#5/#8、刪除所有 13 條非 default
  remote branches，並從 backup branch 人工移植資料目錄對齊、Ollama
  embedding dimension probe、line metadata/query excerpt 等仍有效語意。
- 完成官方 MCP Python SDK `2.0.0` breaking migration：`MCPServer`、runtime
  `Context`、snake_case models、v2 `Client` smoke/tests，30 tool schemas 無
  `ctx` leakage，不保留 SDK v1 fallback。
- 完成 `pdf-preflight-v1`：五類 PDF、per-page OCR reason、native/OCR/Docling
  route、SHA-256/source-change guard、1-based top-left locators、spawn timeout/
  file/page/layout/memory caps；未直接引入尚未發布最新 DoS hardening 的
  `pdf-inspector` dependency。
- 完成 `agent-asset-bundle-v1`：deterministic manifest/JSONL/text/table/
  figure/media、stable hashes/locators/citations、portable Foam index/notes，
  使用 document-scoped staging/atomic replace 並保護來源及非 bundle output。
- Python universal lock、LightRAG floor、VSIX npm lock、Actions majors、
  Dependabot 與 dependency-security workflow 已更新；Python core/dev 與 npm
  audit 均為零已知漏洞。MinerU/Marker extras 因上游 cap 保持安全暫停。
- GitHub description/homepage/topics 與 area/security/provenance/release labels
  已同步；README、wiki、架構、VSIX Marketplace 說明與 `1.0.0` changelog 已
  對齊 reusable agent assets + Foam/LightRAG 核心定位。
- 修正 release review 發現的 LightRAG 初始化競態、figure hash/copy TOCTOU、
  evidence join 平方複雜度與無界輸出；bundle 現有 50,000 spans、25,000 records、
  256 MiB output hard limits，Marker/MinerU 即使手動安裝也無法走 production factory。
- GitHub Pages payload 與 VSIX assistant assets 已重新產生並驗證同步。
- 完整 Python gate：`1096 passed / 30 skipped`；Python 3.10 MCP/preflight/bundle
  focused gate：`32 passed`。Ruff、format、MyPy、Bandit、uv/npm audits、workflow
  security、docs/harness、git diff gates 全部通過。
- 重建 wheel/sdist/VSIX 並完成 clean Python 3.10 wheel smoke、MCP 2.0 stdio、
  154 VSIX tests、artifact audit、VS Code 1.133.0 fresh/update activation smoke。
- Docker `1.0.0` image 重建成功；容器內 doctor/list-tools/SDK 2 schema/stdio
  全綠，30 tools 且 `ctx` leakage 為零。
- 已建立並推送三個分段提交（core、release、docs），將 GitHub default branch、
  Pages source 與本機 tracking 原子遷移為 `main`，刪除遠端 `master`；目前遠端
  僅保留單一 `main` branch，沒有 open PR。
- 第一輪 `main` Actions 除 Windows VSIX smoke 外全綠；其根因是 npm script
  內單引號 glob 被 Windows 視為字面檔名，現已改為跨平台雙引號並加入契約測試。
- Replacement `main@183bbeb` CI、Windows、fail-closed `📋 Test Summary` 與
  `main:/docs` Pages build/deployment 全綠；線上網站已實測回傳 1.0.0、MCP 2、
  `export_assets` 與 Foam 內容。
- `main` 現受 strict aggregate check、至少 1 個 approval、stale review dismissal、
  conversation resolution、linear history、禁止 force-push/deletion 等 branch
  protection 保護。
- Annotated `v1.0.0` 已由 tag-first harness 建立並推送；Release workflow 的 tests、
  三平台 VSIX smoke、artifact/Docker preflight、PyPI、Marketplace、GitHub Release
  共 8 jobs 全綠。PyPI wheel/sdist 與公開下載 hashes 符合本機 build，Marketplace
  CDN 與 GitHub Release VSIX bytes/hash 一致。
- GitHub Wiki 已從舊 0.6.28 同步至 v1（19 files changed、5 new、0 deleted），
  並先建立 `pre-v1.0.0-sync-790a337` recovery tag；Home、LLM Wiki 與圖片 URL
  均回 HTTP 200。歷史 `v0.2.0` draft 因仍有對應 tag 與唯一 VSIX 而保留。

## Doing

- [x] v1.0.0 refresh、convergence、publication 與 post-release verification 完成。


## Next

- Let the scheduled uv/npm/Actions dependency workflows and Dependabot maintain
  the refreshed security floors; fail closed if held MinerU/Marker chains regress.
- Extend the reusable asset bundle through explicit DOCX/general-document
  repository adapters while preserving the v1 hashes, locators and Foam contract.
