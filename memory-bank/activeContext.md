# Active Context

## 1.4.1 publication gate repair — Python3.10 overall CI budget

Goal PROGRESS. Current main/origin71a827c2844c3ffaf1a500e91b97b2b4e1ee76da contains
consolidated1.4.1 metadata/docs/guides. Publicrelease remainsv1.4.0; NO1.4.1TAG.
User wants1.4.x, no per-feature bump. All previous local release gates remain valid:
4143pass/49optional skip,205extension, freshwheel/SDK2, actualDocker/installedform
replays and fullartifact/metadata/security/browser checks. Source351 unchanged.

CI35669105694 completed CANCELLED, not all-pass. Eight jobs passed: static/docs/npm,
Linux/macOS/Windows, unit3892pass/1skip605.07s and integration212pass356.38s.
Linux/macOS actualactivation pass; Windows1069pass/7skip+204extension and install/
update pass; Windowsactivation skipped by workflow. Pages35669106601 all3pass,
37deployed docs exact, for71a827c ONLY. Preserve failed gate proof:
/run/user/1000/asset-aware-release-141-main-publication-proof-01.json.
Watcher40685 TERMINAL1; DO NOT poll/restart it. One transient API query recovered.

Python3.10 job106561340303 started23:47:00Z, cancelled00:07:15Z by its20minute
job budget. No failed pytest case before cancellation: both annotation and both
field SDK2 cases completed; CSL passed, later tests still running. Expanded batch
reached99%. Current annotation pair507s/fieldpair251s versus earlier successful
389s/192s; unchanged runtime on a slower runner exhausted overall headroom.
The final summary failed because its required job was cancelled. Keep exact log
asset-aware-release-141-ci-python310-cancelled-01.log; never call it a pass.

This repair changes ONLY1counted workflow file +both MEM: Python3.10 job budget
20->30minutes and an explanatory comment. Every test command and per-test/request
limit is byte-identical to71a827c. PDF annotations retain300s and fields420s test
limits; no source/locator assertions, coverage or SDK2 surfaces removed. Existing
36focused docs/artifact/harness tests, releaseharness, zizmor regular/high, all
artifact audit and diffcheck pass. Source351hashes exact; workflow is excluded
from sdist, so no runtime/artifact rebuild needed for this scheduling-only repair.

Supplementary install check PASSED: downloaded real publicv1.4.0 GitHubVSIX,
installed it in isolated profile then upgraded same profile to local1.4.1; actual
manifests/listing and fivecurrentbundledguides exact. This did NOT run activation.
Proof:/dev/shm/asset-aware-release-141-public-upgrade-01/proof.json, also linked in
localproof. Local first missing0.2.10baseline remains correctly recorded as skipped.

NEXT exactstage/commit/push this1file+MEM directmain as user author/committer, then
start NEW /run/user/1000/asset-aware-release-141-verify-main-02.py NEW_HEAD,
proof asset-aware-release-141-main-publication-proof-02.json (not started yet).
Require NEW_HEAD all10CI/all3Pages/37deployedbytes before tag. No other development
until this repair gate passes. Version remains1.4.1 throughout; no1.4.2 bump.
After gate, create annotateduser v1.4.1 tag, push and start prepared release watcher
/run/user/1000/asset-aware-release-141-verify-release-01.py HEAD; it validates all8
Releasejobs, GitHublatest, actualPyPIwheel351sourcefiles and Marketplaceversion+
5guides. It is NOT STARTED and requires a fresh releaseproof path. Final release
verification must finish before claiming publication. Broader format goal stays
ACTIVE: ODSsheet/gridlifecycle, PDFbody, otherformats incomplete.

Only alternateworktree edited; original dirtyworkspace untouched. Runtime/builder
Dockerimages removed after proven smoke. Ownnode_modules removed after fullchecks.
All7traces staged THISrelease restored exact;4earlier traces remain symlink-staged
(table-edit03/docx-render01/docx-structure01/workbook01) in old manifests. No global
cleanup. All failed traces/logs preserved. Checkdisk before any build/install.


## Consolidated 1.4.1 — all local release gates passed, one main push next

Goal PROGRESS. Latest user requires1.4.x, no feature-by-feature bumps. This release
consolidates accumulated native document/evidence work; no new runtime behavior.
Published base7b32301 gate complete(all10CI/all3Pages/10deployed bytes), public1.4.0.
Three local <=30-counted segments: e568ab9 metadata/guides26,7816f20 contracts21,
237fbf1 Wiki/site10. This final local segment adds4docs files +both MEM, then ONE
push. Author AND committer u9401066 <u9401066@gap.kmu.edu.tw>, directmain/noPR.
Original dirty workspace untouched. This goal is not complete.

All1.4.1 local gates passed. Fullpytest session23429 TERMINAL0:
4143passed/49optional-skipped/3warnings782.82s. One complete invocation, passing
tmp_path fixtures removed by pytest retention policy; no selected subset or model.
Ruff836formatted, mypy351, Banditmedium/high, docs, Cline18skills, harness,
metadata/allartifact audits, uvlock, locked214package vulnerability audit and npm
vulnerability audit passed. GitHub actual metadata/labels --check both pass.
43focused docs/artifact/harness/metadata tests pass; final docs32pass as well.

Extension205tests and64file contents check pass. VSIX1.4.1 isolated fresh/update
manifest/current-guide verification pass. Legacy0.2.10baseline absent/skipped;
local activation skipped(no display), exact-head Linux/macOS CI required.
Built wheel/sdist/VSIX1.4.1. Freshcleanvenv pip installation of wheel with current
supported dependency versions passes help/doctor/list-tools/realSDK2stdio; venv
removed by smoke script after success. Separate installedwheel service replay uses
locked host deps, matches351sourcefiles,4PDFrevisions/17historicalfieldrecords,
fullreceipts/customcite/Wiki/source. Rebuilt finalwheel's375payloadfiles exactly
match that tested installation (installer-owned RECORD excluded).

Actual unchangedDockerfile with1.4.1label built runtimec1aa42a34a92 and builder
76bc6c2cd96e; import/doctor/tools/realSDK2stdio/fullinstalledformreplay pass, all351
sourcefiles exact. Only tests mounted readonly; installedsrc used. ExactOWNruntime
andbuilder images now removed; no unrelated Docker cleanup. Image/fullIDs proof
/run/user/1000/asset-aware-release-141-docker-images-01.json.

Browser caught existing English site omission of PDF field workflow/evaluation.
Added English full-field/hash/receipt/Widget/Agent-review guide, actual evaluation
and ODS rename explanation. Fixed forms-vs-annotation Wiki projection description.
Desktop/mobile x zh/en DOM/overflow/old-anchor checks pass. Root viewed desktopZH
and mobileEN actual PNGs; readable/no overlap. Preserved first missinglib failure
and second missingEnglishheading failure, corrected thirdrun passed. Final tiny
Chinese status wording updated; docs builder regenerated. No new model run:
immutable previous Codex trace reused honestly, failures retained.

Authoritative localproof: /run/user/1000/asset-aware-release-141-local-proof-01.json
statuslocal_gates_passed. Logs/hashes/source manifest same release-141 prefix.
Fresh publication watcher PREPARED NOT STARTED:
/run/user/1000/asset-aware-release-141-verify-main-01.py HEAD
newproof:asset-aware-release-141-main-publication-proof-01.json.
It requires exact-head all10CI/all3Pages and every changed docs file deployed byte
exact, plus mainSHA/publicv1.4.0 before tagging. Commit/push finalcheckpoint first,
then start watcher and complete gate BEFORE any further development or v1.4.1 tag.
After gate: annotated user-authored v1.4.1 tag, push, verify Release workflow and
PyPI/Marketplace/GitHub visibility. No new version or tag is published yet.

Disk: initialnpmci ENOSPC retained; secondnpmci passed after own space staging.
Three old PASS synthetic SDK fixture trees were hash-inventoried/removed; all
model/failure evidence retained. Completed currentnode_modules now inventoried/
removed. Seven traces staged for THIS release have ALL been restored byte/hash/
mtime exact; release-141-build-space-01/02 manifests allrestoredtrue. Four earlier
traces remain staged via original /tmp symlinks in oldroot-space-01/build-space-02:
table-edit03,docx-render01,docx-structure01,workbook01. Do not rerestore others.
Root~194MB/shm864MB after ownDocker cleanup/restoration; check fresh. No global
cleanup. Broader ODS lifecycle/PDF body/other-format work remains incomplete.


## 1.4.1 release preparation — Wiki and bilingual website aligned

Goal PROGRESS; local main ahead2, no new push/tag. This10counted-file segment plus
both MEM synchronizes four canonical Wiki chapters, generated counterparts and
site payload/English reader. Current capability/release status references1.4.1;
old Unreleased heading links remain usable via explicit anchors. Historical test
scope/failures remain, and current native worksheet/A2T/rendition statements no
longer repeat superseded gaps. ODS full lifecycle/PDF-body/viewer gaps remain.
43docs/artifact/harness/GitHub hygiene tests pass; JS syntax/docs builder/diff pass.
Locked Python214packages audit found no known vulnerabilities/adverse status.

Npmci failed ENOSPC before completing node_modules; preserve log01 and npm cache.
No source behavior/dependency upgrade. Full1.4.1 tests/security/artifacts remain.
Current root180MB/shm533MB; inspect own completed test artifacts before safe cleanup
or using task-owned tmpfs dependency installation. Never global prune/other work.
Failed npm session69252 terminal228. Original workspace untouched, main direct,
user author/committer. Current public1.4.0 until gated consolidated1.4.1 release.
All prior publication proof and actual Codex evaluation evidence remain preserved.


## 1.4.1 release preparation — technical contracts and capability limits

Goal PROGRESS; no push/tag yet. Local e568ab9 prepared26counted release metadata/
README/Agent-guide files after current published7b32301 gate passed. This segment
updates21technical documents only, plus both MEM. Consolidated1.4.1 scope replaces
stale per-feature release statuses; old Unreleased heading anchors are retained
as explicit HTML IDs. ODS lifecycle/PDF body and viewer parity remain open.
Native Table creation doc now points to implemented separate totals lifecycle;
no arbitrary row/column identity-move claim. Changelog historical tail unchanged.
Docs builder --check and diff hygiene pass; source behavior/dependencies unchanged.
Next: canonical Wiki + English site status updates/generated payload, then complete
1.4.1 source/artifact/security/install/Docker gates, one direct-main push and exact
remote CI/Pages/deployed verification before tag. Author/committer user; original
workspace untouched. All earlier traces/logs and four staged old traces retained.


## Consolidated 1.4.1 release preparation — version/readme/Agent guides

Goal turn PROGRESS. Prior exact-head gate for 7b32301c9c983eb261ff7fb5bc832184e19561cd
is COMPLETE: CI35664730510 all10, Pages35664729609 all3, ten deployed files exact.
Proof: /run/user/1000/asset-aware-pdf-fields-integration-publication-proof-02.json,
status published_verified. Watcher13503 terminal0; never poll/restart old watchers.
Successful CI: unit3892pass/1skip, Python3.10 1750pass/4skip, integration212pass;
Linux/macOS actual extension activation passes; Windows workflow skips activation.

User requires 1.4.x without feature-by-feature bumps. Begin ONE consolidated1.4.1,
not a new feature. This local segment changes26counted files plus both MEM:
six version declarations, concise accumulated changelog, English/Traditional Chinese
READMEs, Home/GettingStarted/generated site data, extension README, five Agent guides
and five bundled copies. CHANGELOG1.4.0-and-earlier bytes retained exactly.
Publication status still governed by GitHub Releases; public remains1.4.0 until tag.
36focused docs/artifact/harness tests, lock check, metadata audit, release harness,
Cline18skill audit and bundle sync pass. Initial test path typo ran zero cases;
then Home exceeded90lines: shortened Home and all36passed; failure logs retained.
No PDF/runtime behavior changes; src version only. Documentation clearly retains
MCP mechanical vs Agent semantic/visual review, ODS lifecycle/PDF-body/viewer gaps.

Only alternate worktree main is edited; original dirty workspace untouched.
Author AND committer u9401066 <u9401066@gap.kmu.edu.tw>. No PR/subagents/model overrides.
Next local segments: technical docs/site status alignment <=30counted each;
then fresh1.4.1 full tests/security/packaging/install/Docker checks. ONE main push
only after coherent local preparation; verify exact-head all10CI +3Pages +deployed
bytes before annotatedv1.4.1 tag/release workflow. Do not claim release complete.
Broader goal remains active: ODS lifecycle, arbitrary PDF body and other format gaps.

Preserved traces: four old /tmp paths still symlink-staged in own shm, manifests
root-space-01 and build-space-02; build-space-03 ALL restored. No global cleanup.
Root~300MB/shm559MB free; check fresh before npm/build. node_modules absent.
Logs/scripts /run/user/1000/asset-aware-release-141-*; old artifacts remain1.4.0.


## PDF fields publication gate — repair stale GitHub metadata test fixture

Current goal turn: PROGRESS. Published main/origin3c2adcfa11dfe6cce0fdd479d59b50d299774cff
contains all field integration/guides and completed local artifact checks. Public
release stays1.4.0; next consolidated1.4.1. DO NOT advance version/release until
current publication gate passes. Author AND committer u9401066 <u9401066@gap.kmu.edu.tw>.
This repair changes ONLY1counted test file plus both MEM, no production or artifact
bytes. Original workspace untouched; direct main, no PR/subagents/model override.

Previous goal turn was PROGRESS: Docker Python3.12 installed replay/stdio passed,
metadata applied, main pushed, Pages all3jobs and10deployed files verified. Gate
watcher89554 is now TERMINAL1, NOT LIVE; do not poll or restart it. Its exact-head
CI35663541391 failed unit job106544224456:3889passed/3failed/1skip590.80s. All three
failures are hygiene-script tests: scripts/gh_update_repo_metadata.sh intentionally
added PDF forms, but fake gh's canonical description still had pages/annotations.
The earlier local full suite predates that metadata-script edit. Comparing only
351runtime source hashes did NOT cover the changed shell script; this was a missed
focused test, not a PDF runtime failure. Keep original CI log and failed proof.
Integration job skipped due dependency; do not call it an executed test failure.

Fix: tests/unit/test_github_hygiene_scripts.py independent mock description now
includes /forms. All existing read-only, drift, explicit apply, label preservation,
and shell-injection assertions remain unchanged. Complete hygiene7tests plus
32docs/harness and28Codex field-audit regressions =67passed5.28s, session92200
TERMINAL0. Ruff/format/diff and actual remote metadata --check pass. No new model
run, artifact rebuild or runtime check needed for this test-fixture-only change;
new exact-head full CI remains required. Proof:/run/user/1000/asset-aware-pdf-fields-
ci-fixture-repair-proof.json. Failure and correction logs retained separately.

On original3c2adcf, Linux205unit+2activation passed; macOS1072native/4skip,
205extension+2activation passed; Windows1069native/7skip,204extension and actual
isolated install/update passed. Windows activation was skipped by its workflow;
do not claim it ran. Python3.10 was still running when unit failure stopped watcher;
inspect authoritative job state if needed. Next push may supersede that old run.
Pages35663540353 all3success and10exact deployed files apply ONLY3c2adcf.
Original gate proof:/run/user/1000/asset-aware-pdf-fields-integration-publication-proof.json.

Resource correction: build-space-03 all8directories restored byte/size/mtime exact.
Of earlier6traces, table-edit01 and02 have ALSO now been restored; root-space-01
manifest records true for those2. Four remain staged through accessible original
/tmp symlinks: table-edit03,docx-render01,docx-structure01,workbook01. Do not replay
old11dir restoration. Root free space dropped while working; latest~70MB,shm451MB,
run154MB. Restoration stopped before consuming the64MBworking margin. Own Docker
runtime/builder removed; no global cleanup. Failed/PASSED model/replay output stays.
Node modules still removed, built VSIX/dist/out and installed wheel target retained.

NEXT: exact-stage1test+both MEM, commit/push directmain once. Start NEW watcher
/run/user/1000/asset-aware-pdf-fields-integration-verify-publication-02.py with
new full HEAD (not started yet). New proof path:asset-aware-pdf-fields-integration-
publication-proof-02.json. Verify all10CI +3Pages +10deployed bytes for NEW HEAD
before release/version/feature development. Preserve old failed results. Then
prepare ONE consolidated1.4.1 release for accumulated verified work; broader
ODS/PDF-body/other-format requirements remain active and incomplete.


## PDF field integration — all local artifact checks passed, main publication next

Current goal turn: PROGRESS. Previous turn was PROGRESS: a9b6d8e973ef5a69fbd6d7e1b53591547681b04f
committed26counted files +both MEM, completing default Codex field audit/guides.
Together with5bb28af5504ce87173f3dbdc743cf8bae3f65767 field MCP integration, local
main is ahead2 of published e953542ea7acf70ac42a22c8c15e2dfdab5211cd. This checkpoint
adds ONLY both MEM before ONE direct main push. User author AND committer:
u9401066 <u9401066@gap.kmu.edu.tw>. No PR, branch, model override or source-worktree
changes. All runtime351source hashes remain those of the4115pass/49skip full check;
new28audit regressions +32docs checks pass separately. Current/public remains1.4.0;
next consolidated1.4.1. Remote releases/latest rechecked: v1.4.0. No new tag/release.

Docker validation NOW COMPLETE (do not reuse old349source core proof):
Actual unchanged Dockerfile/frozen lock built Python3.12.13, image d9b5181e7136;
/run/user/1000/asset-aware-pdf-fields-docker-images-01.json retains full runtime/
builder IDs. Build session76977 TERMINAL0. Installed import/doctor/list-tools/
real SDK2 stdio and installed-service replay all0, session80151 TERMINAL0.
All351installed Python source hashes match the verified checkout. Reproduced exact
4PDF versions and all3complete operation receipts,17historical field records,
final4Wiki records, custom citations and original source bytes/mtime. Docker uses
installed site-packages src, only test harness bind-mounted readonly; source checkout
is not mounted as production code. Replay at /dev/shm/asset-aware-pdf-fields-docker-
smoke-01/replay/replay.json; commands/runs.json and complete logs retained.
Together with the already-passed installed Python3.13wheel, actual default Codex
trace audit,205extensiontests and isolated fresh/update VSIX checks, local artifact
checks are complete. Local VSIX activation not run (no display/xvfb); exact-head
remote platform activation remains required. All-artifact audit1.4.0 rechecked pass.

GitHub metadata applied AND verified: description now includes PDF forms,
homepage and all20canonical topics synchronized. Log:/run/user/1000/asset-aware-
pdf-fields-github-metadata-01.log. No messages sent to others. Source/Docs/Agent
changes remain exactly a9b6d8e. Consolidated authoritative local proof updated:
/run/user/1000/asset-aware-pdf-fields-agent-evaluation-proof.json.

Resource housekeeping completed with exact manifests. Eight more OWN completed
historical traces were staged, original paths retained via symlinks, then ALL8
restored with exact bytes/size/mtime after Docker checks: a2t01,a2t-grid01,native-
grid01,selection01,docx-cjk01,pptx-merge01,pptx-render01,pptx-slides01. Original
3PPTX run/audit return0/true verified before staging. Total354165115bytes;
/run/user/1000/asset-aware-pdf-fields-build-space-03.json all restored:true.
Staging35004 and restore/metadata/cleanup88682 TERMINAL0. Only owned Docker
runtime/builder IDs removed after verifying no containers used them; no global
prune, unrelated images or caches touched. Logs/trace/native outputs retained.
Earlier6traces are STILL staged in root-space-01 and build-space-02 with original
/tmp paths available, NOT restored. Never replay historical11dir restore manifest.
Last free root287MB/shm431MB/run~155MB; restoring all6needs~268MB+64MBmargin.
node_modules remains removed after successful VSIX checks; dist/VSIX/out retained.

NEXT: exact-stage both MEM, commit by user, push ALL local main checkpoints once.
Then run /run/user/1000/asset-aware-pdf-fields-integration-verify-publication.py
with the pushed full HEAD; proof path is asset-aware-pdf-fields-integration-
publication-proof.json (currently absent). Verify exact-head ALL10CI +3Pages
jobs,10deployed files including release-testing source/pages, main SHA and public
v1.4.0. No additional feature development before this gate. Poll the SAME live
watcher; observation timeout is not terminal. After gate, plan the consolidated
1.4.1 release for the accumulated verified capabilities; keep remaining ODS
worksheet/grid CRUD, PDF body CRUD and other formats in the full ACTIVE goal.
Current progress does NOT establish all-format completion or universal fidelity.


## Default Codex PDF field evaluation and Agent guides — local artifact checkpoint

Current goal turn: PROGRESS. Public/current version stays1.4.0, next consolidated
1.4.1; no per-feature bump/tag/release. All7version sources and built artifacts
agree. User explicitly reiterated the1.4.x policy. Work ONLY in agent-assets main;
original dirty asset-aware-mcp worktree untouched. Author AND committer must be
u9401066 <u9401066@gap.kmu.edu.tw>. This segment has26counted files +both MEM,
within30; exact hashes and tests in /run/user/1000/asset-aware-pdf-fields-agent-
evaluation-proof.json. Parent local main5bb28af5504ce87173f3dbdc743cf8bae3f65767
already contains field MCP/evidence/Wiki and is ahead1 of published origin e953542.
This segment is another local checkpoint; NO PUSH yet. Both checkpoints should
ship together after remaining Docker/publication checks. Use git log for its hash.
Do not infer goal completion; broader format CRUD and PDF body work remain.

Actual DEFAULT Codex evaluation COMPLETE; no model override/subagents:
/dev/shm/asset-aware-codex-pdf-fields-01. Model return0,342.15s,not timed out.
Runner session42506 TERMINAL1 because initial auditor rejected a legitimate saved
selection-reference reread. Original audit-before-selection-read-fix.json retained;
stronger complete parent/selector/value/context/Unicode-byte-range/hash checks plus
10regressions resolve it. Model trace unchanged, NOT rerun to erase failure.
Current audit.json PASSED:426successful/428total MCP calls,4managed PDF versions,
17complete field records,4actual MCP images, original/final Wiki. Two retained
errors: unused contract text_limit; ReviewCopy font5 did not fit, explicit4retry
succeeded. Full source hash/mtime, native values/button AS/AP, unchanged body bytes/
pixels/pushbutton, exact receipts, historical selections, derivation and Wiki checked.
Standalone audit CLI now exits1 for missing/invalid trace; new CLI regression passes.
Final reauditor session85773 TERMINAL0; audit-before-cli-exit-fix.json also retained.

Root Agent ACTUALLY VIEWED all4default-Codex PNGs individually this segment.
/run/user/1000/asset-aware-pdf-fields-root-visual-review.json records exact hashes
and observations: text legible/unclipped; checkbox checked/right radio selected;
ReviewCopy appears above gray PUSHBUTTON; only original Text1 disappears on delete.
Correction to historical MEM below: gray rectangle is Button2 pushbutton, NOT a
text area. Root confirmed all4images; earlier batch tool output was truncated and
did not count as review. Static MuPDF only, no interactive-viewer fidelity claim;
ReviewCopy contains authored text, not a fact from the original blank source.

Added5harness files: tests/codex_pdf_fields.py, codex_pdf_fields_audit.py,
codex_pdf_fields_checks.py, codex_pdf_fields_replay.py and unit/test_codex_pdf_fields_audit.py.
Synchronized5Agent guide sources +5bundled copies; expected_catalog_sha256 belongs
inside pdf_fields_update. Full ref/hash paging, borders/styles, historical refs,
Agent review and version policy explicit. README/CHANGELOG/spec/gap analysis,
Native-File-Assets Wiki/site and canonical Release-And-Testing Wiki/site plus
site-content.js reflect actual evaluation. edit canonical Wiki, not generated
site-content/release-testing.md alone: builder regenerates it. CI Python3.10 adds
new audit unit module. Metadata script adds PDF forms; remote apply still pending.

Checks COMPLETE; all related sessions terminal, do not restart:
- New28audit regressions +32docs/harness =60passed4.87s, session63302 TERMINAL0;
  final canonical docs32passed0.20s after restoring new section at canonical source.
- Ruff all pass;836files formatted. All351runtime source hashes EXACTLY match
  prior full-suite checkpoint:4115pass/49optional skip. New28audit tests separately
  passed; do not claim a new single full run. Prior failures stay in old proof.
- npm test:ci205tests passed, session30857 TERMINAL0. Latest guides also passed
  sync/package artifact audit and actual isolated fresh/update VSIX installs,
  session87289 TERMINAL0. Legacy0.2.10upgrade skipped (no baseline); no local
  activation because no display/xvfb. Exact installed manifest/current guide bytes
  verified. Safe PATH CLI /dev/shm/asset-aware-ods-guides-cli-02/code retained.
- uv build sdist+wheel1.4.0, session34753 TERMINAL0; metadata/all-artifact audit,
  docs check, release harness, sync, git diff check pass. Zizmor offline at CI's
  regular/high policy pass. Initial default-threshold command exit11 was ONE
  informational existing softprops release-action advisory; retained log, no high.
- Real installed wheel --no-deps target /dev/shm/asset-aware-pdf-fields-wheel-target-01/
  site-packages, uses locked existing Python3.13deps. src location asserted installed;
  every351file hash compared. Installed service replay02 session2860 TERMINAL0:
  same4PDF bytes, all3full receipts,17historical field records, final4Wiki fields,
  exact PDF/receipt/custom citations and unchanged source. Source-based tests cannot
  substitute for this installed import assertion. First replay01 session94996
  TERMINAL1: harness protected whole output root, Wiki guard rejected overlap.
  Corrected protected path to actual store; failed log/output kept, guards unchanged.
- Installed console help/doctor/list-tools +real SDK2 stdio all0, session5669 TERMINAL0.
  /dev/shm/asset-aware-pdf-fields-wheel-diagnostics-01/runs.json records exact commands.
  Runtime and replay outputs retained; no Docker smoke yet for this integration.

Resources: own completed node_modules/npm/build-cache and passing current test
fixtures were hash-inventoried then removed, session94079 TERMINAL0. All5roots
show removed:true in /run/user/1000/asset-aware-pdf-fields-completed-cleanup-01.json.
Observed free space after cleanup:root289MB,shm443MB,run155MB. NEVER delete global caches or others' data. Source dist/VSIX/out,
failed replay01, passing replay02, actual Codex trace and installed target remain.
Six OWN historical traces remain staged with original /tmp symlinks, all bytes/
mtime verified; NOT restored: table-edit01/02/03+docx-render01 via root-space-01
manifest; docx-structure01+workbook01 via pdf-fields-build-space-02.json. Old11dir
pdf-field-build-space.json is historical restored state; NEVER replay old restore.
Remaining5previously-restored own trace candidates total~245MB can be staged with
fresh hashes/manifests if Docker build needs capacity; inspect current disk first.
Restore only with remaining size +64MB working margin. No active unrelated work
may be cleaned. Node removal is for task-owned rebuildable dependencies only.

NEXT: finish fresh Dockerfile Python3.12 build and diagnostics/stdio +installed
service replay using tests.codex_pdf_fields_replay (--trace, --output, --manifest,
--installed-dir). Root disk scarce; inspect before build, preserve completed trace
paths via checked staging if needed. No repeated model run/full suite justified
unless code changes. Before ONE push of both local commits complete required
artifact checks; then exact-head10CI+3Pages+deployed bytes gate before new code.
Apply/verify GitHub metadata forms description with publication. Preserve1.4.0
until consolidated1.4.1 release; do not tag per feature or request approval again.


## PDF field MCP/evidence/Wiki checkpoint verified locally — publication pending

Current goal turn: PROGRESS. This checkpoint contains30counted files +both MEM,
for a direct local main commit by author AND committer u9401066
<u9401066@gap.kmu.edu.tw>. No push/tag/release in this segment. Public/current
version remains1.4.0 in ALL7version sources; next consolidated1.4.1, never a
per-feature bump. Published baseline main/origin remains e953542ea7acf70ac42a22c8c15e2dfdab5211cd;
its10CI+3Pages+8deployed bytes were already verified. Use git log for local checkpoint
hash; /run/user/1000/asset-aware-pdf-fields-integration-proof.json records exact
30file/351source hashes, tests, prior failures, image review and commit state.

Implemented complete MCP field reads/CRUD, full field refs/selections/derivations/
CSL/custom citations, source/revision guards, ProcessNativePdf field workers and
receipt-sensitive field Wiki. Every logical group/hidden/duplicate field and every
Widget page retains identity; complete receipts survive all-field deletion and
repeated file bytes. Object IDs can remap on serialization: new refs come from final
bytes, historical refs remain original. README/CHANGELOG/spec/capability analysis,
Native-File-Assets Wiki+site source and generated site-content.js now describe the
Unreleased scope; default Codex form evaluation and Agent-guide synchronization
are explicitly pending. No native PDF body-edit/general-format completion claim.

Verification COMPLETE, all sessions TERMINAL:
- Effective full Python suite4115passed/49optional-environment skipped/3intentional
  malformed-fixture warnings. No runtime source changed between phases.
- First unit/infrastructure/ALL5root-test phase:4052pass/1fail/1skip180.18s,
  session91387 TERMINAL1. Only failed old test expected pdf-annotations-v1 for a
  fixture that contains forms. Updated to fields projection, kept every old page/
  source/opaque-Wiki/human-note assertion and added full field-ref checks. Complete
  corrected module8passed0.57s, so effective unique unit/root4053pass/1skip.
  Original failure log and failed fixture directory retained. All other completed
  passing phase fixtures455541608bytes inventoried with hashes before cleanup;
  failed test_pdf_wiki_keeps_opaque_and0 and its current symlink remain.
- ALLintegration tests:62passed/48skipped600.88s, session13667 TERMINAL0. Includes
  both new field SDK2 surfaces and both prior annotation surfaces. Complete own
  integration fixtures363177702bytes hash-inventoried then removed after success.
- Focused338passed/3warnings60.63s; separately both field SDK2 configurations
  2passed143.97s. Original focused failures and logs remain preserved.
- New human-doc/site/harness tests32passed0.20s after doc changes; docs build/check,
  release harness, sync-assets:check pass. Ruff all,831formatted files, mypy351src,
  Bandit medium/high(session55551 TERMINAL0), zizmor offline all pass.
Logs/manifests: /run/user/1000/asset-aware-pdf-fields-full-check-01-{unit-and-root,
integration}.{log or related fixtures.json}; focused provenance-01/02, legacy-wiki-
01 and human-docs-01 paths are recorded in authoritative integration-proof.json.
The old full-check-01.json intentionally retains original failed first-phase state;
use integration-proof.json for the corrected full outcome. Never restart these
finished sessions or mistake the old first-phase proof for unresolved failure.

Root Agent additionally viewed FOUR actual compact SDK2 fixture Wiki PNGs:
original/created page indices0,2. New 中文009µgβ is legible/not clipped on both;
original headings, shapes and icons visually retained. Exact PNG hashes/findings
are in integration-proof.json; fixtures /dev/shm/asset-aware-pdf-fields-stdio-01.
This is NOT default Codex CLI evaluation. Original synthetic Widget appearances
are authored colored blocks, not a promise that their stored values are rendered.
One local apply_patch write failed and left the previously-clean Wiki file empty;
it was immediately restored byte-exact from HEAD, then all intended human docs
were atomically written and verified. Cause unknown; do not invent a disk diagnosis.
Observation/recovery hashes are in proof; final32docs tests passed, no data loss.

NEXT SEGMENT: implement/run actual DEFAULT Codex PDF-field MCP evaluation with
independent audit and actual page review/correction, then synchronize Agent guides
and bundled assets. Reuse tests/codex_pdf.run command/execute (no model override),
tests/codex_pdf_annotations/run.py +audit.py patterns, tests/codex_native_pdf.trace
and artifacts helpers. Pinned real pikepdf form.pdf is available at
/dev/shm/asset-aware-pdf-field-upstream-edits-03/source.pdf,
SHA2566e2b7541acc922d4c046621becd8cb91a63b358b72c875e58080d373946b4b93.
Old direct-adapter trials and14images are retained; they do not substitute for
Codex/MCP. Upstream original image has a gray text area, checkbox and two radio
buttons; prior adapter12pt request failed fit,8pt plus explicit border_width0
corrected unwanted border. Preserve failures; do not manufacture visual verdicts.
No new Codex field harness has been created or run yet.

After guides/model evaluation: refresh necessary artifact/wheel/Docker/VSIX checks,
update metadata as appropriate, then ONE direct main push with both local segments.
After EVERYpush verify exact-head10CI+3Pages+deployed-byte gate before further code.
Full release requirements remain before publication; current localPython checks
are not a replacement for pending default-Codex/artifact/remote verification.
Keep <=30counted files per segment, excluding ONLY both MEM. Current segment has
reached30; put additional files in the next commit. No PR/new branches/subagents.

Resources: four OWN historical Codex trace dirs remain staged via original /tmp
symlinks in /dev/shm/asset-aware-pdf-field-root-space-01:table-edit-01/02/03 and
 docx-render-01. Manifest /run/user/1000/asset-aware-pdf-field-root-space-01.json.
Bytes/mtime preserved, NOT restored. Restore only when root has~160MB+64MBmargin;
last root~97MB cannot satisfy that. Old11-directory build-space move was fully
restored; never replay that old restoration. Clean only completed OWN artifacts
with inventories; never live servers/original dirty workspace/global caches.
All work stays in asset-aware-mcp-agent-assets; original asset-aware-mcp untouched.

## PDF fields MCP/evidence/Wiki integration — full-suite verification running

Current goal turn: PROGRESS. Public/current version remains1.4.0; next consolidated
1.4.1. No version bump/tag/release or push in this integration segment. HEAD/main/
origin is still e953542ea7acf70ac42a22c8c15e2dfdab5211cd, whose exact-head10CI/3Pages/
8deployed-file gate is already complete. Work ONLY in this agent-assets worktree.
Author/committer u9401066 <u9401066@gap.kmu.edu.tw>; no PR/subagents or model override.

Current working changes:25counted files plus both MEM. New field operations expose
complete hash-pinned read_pdf_fields/read_pdf_field and checked update_pdf_fields,
with all create-parent/widget and update/delete references bound to asset/revision.
ProcessNativePdf supports four field operations. Full references support selection,
derivation source/target and CSL. Field Wiki retains exact PDF, every field/group/
hidden record and widget page, complete catalog/receipt, escaped native strings and
custom physical-path/object citations. Receipt hash participates in Wiki identity,
including repeated identical PDF bytes with different operation history. Empty
AcroForms retain final deletion receipts; no-form legacy projection remains intact.

Focused verification:338passed/3intentional malformed-fixture warnings60.63s;
/run/user/1000/asset-aware-pdf-field-provenance-02.log, session41572 TERMINAL0.
ALL16service +7provenance +80core cases plus schema/annotation regressions passed.
Earlier provenance-01 had34pass/1test-assumption failure: complete receipt has a
final field_catalog_readback entry, not another deleted_fields entry. Corrected
assertion checks that final catalog separately and all7removed records. Original
failure log/fixtures preserved; session91092 TERMINAL1. Previous service-01 object's
renumbering test failure is also preserved; final tests retain full historical ref
verification and compare native value plus the new locator, not old object IDs.
Ordinary test reads now use4000chars; dedicated79-char continuation guards remain.

Real SDK2 stdio: BOTHbalanced/compact configurations passed2tests143.97s;
/run/user/1000/asset-aware-pdf-fields-stdio-01.log, session12314 TERMINAL0. Actual
ProcessNativePdf: full contracts/schemas, hidden007->008 update, no-op/foreign/stale
checks, CJK field create with2widgets, complete receipts, all3page PNG comparisons
at original/update/create/delete stages, field Wiki/custom citations, deletion and
old refs/selections/Wikis/source bytes+mtime preservation. This is automated SDK2
verification, NOT the required actual default Codex field evaluation.

Ruff all pass;831files formatted; mypy351src pass; docs site payload up-to-date;
release harness audit and assistant sync-assets:check pass. Bandit session55551
was running at this checkpoint; poll once to capture terminal state. README,
CHANGELOG and docs/native-pdf-fields-spec.md reflect current Unreleased integration
and explicitly pending default Codex evaluation/Agent-site guidance/publication.
CI Python3.10 focused suite now includes all4field unit modules and field stdio.

Full pytest is running in TWO sequential phases to keep peak owned temp usage
within current disk limits; no tests intentionally omitted. Session91387 ACTIVE:
/run/user/1000/asset-aware-pdf-fields-full-check-01.py records status/hash/inventory
in matching.json. Phase1 includes tests/unit, tests/infrastructure and ALL5root
test modules; phase2 tests/integration. Each successful phase retains full logs
and a lstat-safe file/hash manifest, then deletes ONLY its completed own basetemp.
On failure it stops and preserves that phase's fixtures. No source change planned
while this snapshot runs. Do not start duplicate full suites or misreport a running
phase as passed. Logs prefix asset-aware-pdf-fields-full-check-01-{phase}.log.

Next: resolve full-suite failures if any; audit current code; make <=30-file local
core commit if needed before separate guides/default-Codex harness segment. Multiple
local commits may precede ONE publication push, but full checks/artifacts/default
Codex field review and synchronized human/Agent/site guidance remain before that
push. After EVERYpush, exact-head10CI+3Pages+deployed bytes before further code.
Do not claim broad all-format goal complete; PDF body CRUD and other gaps remain.

Resources: four historical OWN Codex trace directories are CURRENTLY staged in
/dev/shm/asset-aware-pdf-field-root-space-01 with original /tmp paths as symlinks:
table-edit-01/02/03 and docx-render-01. Manifest is /run/user/1000/asset-aware-pdf-
field-root-space-01.json; all bytes/mtime verified. NOT restored; restore only when
root has their~160MB plus64MBworking margin. Old build-space restoration is complete
and must not be reused. Never clean other worktrees, live servers, global caches or
unrelated output. Last free root132MB/shm620MB/run307MB before full suite. Failed
and actual Codex traces remain preserved; only completed owned test fixtures are
eligible for manifest-backed cleanup. Original workspace remains untouched.

## PDF field core publication verified — MCP integration is next

Current goal turn: PROGRESS. HEAD e953542ea7acf70ac42a22c8c15e2dfdab5211cd is fully
verified on main/origin. ALL10 CI jobs35652655180, ALL3 Pages jobs35652654911 and
ALL8 deployed files passed. Watcher58944 TERMINAL exit0; DO NOT restart or poll.
Remote logs: unit3835pass/1skip/3warnings506.15s (all80new field tests), Python3.10
1611pass/4skip916.07s, integration212pass568.72s. Linux/macOS205extension tests and
2actual installed activation tests each; Windows204pass/1skip and isolatedinstall/
update passed, activation explicitly skipped. Logs/hashes plus exact publication
state are in /run/user/1000/asset-aware-pdf-field-local-proof.json and publication-
proof.json. Local checks remain4084pass/49skip, installed wheel/Docker exact5PDF/
complete receipt replay, SDK2 and349source hashes. All capture sessions TERMINAL.
Public/latest release stays1.4.0; next consolidated1.4.1; no version bump/tag.

New development may now proceed: field MCP paged reads/CRUD, full managed refs,
source/revision checks for every create parent/widget page and every existing field,
complete no-op receipts, selections/derivations/citations/Wiki, and actual default
Codex image review/correction. Keep full all-format goal active. Multiple <=30-file
local commits may precede one push if needed to deliver code + synchronized guides;
still run full checks before publishing and exact-head CI/Pages after every push.

Read-only upstream body-edit research (no implementation/test claim) retained at
/run/user/1000/asset-aware-pdf-body-upstream-research-01.json. Primary sources:
https://pikepdf.readthedocs.io/en/latest/api/filters.html (parser/unparser loses
lexical details; token filters for mutation), PyMuPDF page redactions (possible
collateral links/images/characters and shrinking/omitted replacement text), Story
HTML/CSS DOM (new layout, not recovery of arbitrary source PDF structure). Verify
actual flag semantics before implementation. Body CRUD remains in broad scope;
form/annotation work does not complete it. Immediate task remains form integration.

Resource warning persists: FOUR own historical traces currently staged via original
/tmp symlinks under /dev/shm/asset-aware-pdf-field-root-space-01. Use its NEW manifest
/run/user/1000/asset-aware-pdf-field-root-space-01.json; do not reuse older buildspace
restoration. Root about152MB free, below full restore plus margin. All exactbytes/
size/mtime preserved, originals accessible. Restore when space permits. Do not
clean any other project/cache or touch original dirty checkout. Work exclusively
in agent-assets main. Only both MEM dirty at this checkpoint; no integration edits
yet. Author/committer u9401066 <u9401066@gap.kmu.edu.tw>, noPR/subagents, exactstaging.

## PDF field core pushed — exact-head CI gate still running

Current goal turn: PROGRESS. Main/origin HEAD is
`e953542ea7acf70ac42a22c8c15e2dfdab5211cd` (feat(pdf): add checked native form field
CRUD core), author AND committer u9401066 <u9401066@gap.kmu.edu.tw>.
14 counted files + both MEM committed and pushed directly under existing user
permission. GitHub reported the expected PR/status-check rule bypass. No tag or
release. All seven version declarations/public release remain 1.4.0; next
consolidated release is 1.4.1. User version constraint persists.

Local current verification is complete: 4084 passed / 49 optional-environment
skips / 3 intentional malformed-fixture warnings, 598.37s; all80 field regressions
included. Ruff/format826/mypy349/Bandit/zizmor, docs/site/harness/sync/artifact checks
pass. Installed Python3.13 wheel and actual Dockerfile Python3.12 both reproduce
five exact native CRUD PDFs AND complete receipts; doctor/30tools/SDK2 stdio pass.
This is INTERNAL core only. No field MCP capability/default Codex evaluation yet.

ACTIVE watcher session58944 runs
/run/user/1000/asset-aware-pdf-field-verify-publication.py for this exact HEAD.
DO NOT restart it or begin new development before the publication gate completes.
Latest observation: CI35652655180 still running,4completed jobs all successful
(static/docs/npm/LinuxVSIX); macOS,Windows,Python3.10 andunit running. Integration
and summary follow. Pages35652654911 ALL3jobs passed. ALL8 deployed files match
exact commit bytes, including native-pdf-fields-spec.md. Proof:
/run/user/1000/asset-aware-pdf-field-publication-proof.json. Poll the SAME58944;
then inspect any failure or verify all10CIjobs,3Pagesjobs and8deployed files plus
latest releasev1.4.0. Capture relevant CI test/activation logs, update local proof
and both MEM. Broader goal remains ACTIVE; do not call complete/blocked.

Resource state: current completed full-test fixture tree781586800bytes and three
passed PDF unit trees removed with manifests. All prior failure/visual/model logs
retained. Current owned Docker image/builder and wheel venv removed. Build-space
staging restored ALL11 trace trees byte/size/mtime exact. AFTER that restoration,
root available space reached0 again. A NEW preservation manifest at
/run/user/1000/asset-aware-pdf-field-root-space-01.json now retains FOUR owned
historical traces under /dev/shm/asset-aware-pdf-field-root-space-01, reachable at
the original /tmp paths via symlinks (three table-edit runs and docx-render01).
They are currently STAGED, not restored; old build-space manifest remains historical.
About162MB root became available. Restore these four using the NEW manifest only
when root has enough bytes for all files plus working margin. Never delete logs,
other projects/caches or original dirty worktree. All local process sessions are
terminal except publication watcher58944. Cleanup-only86725 stopped on intentional
FIFO (exit143); revised20329 passed; full pytest itself passed first try.

Read-only next integration reconnaissance: application/native_pdf_field_operations
will need new paged catalog/record/CRUD routing; domain/native_assets.py request/ref
union and native_operations.py schemas; native_pdf.py protocol/facade plus
infrastructure/native_pdf_process.py operation whitelist/MUTATIONS/methods.
Validate create parent AND every widget page ref against managed asset/revision;
update/delete refs likewise. Pin continuation content hashes and retain complete
no-op reports inline. Selection/derivation unions and native_evidence_service.py
must resolve full field records. Wiki projection must retain field catalog/records,
all field-to-page links, hidden fields, existing annotations, full receipts and
exact source attachment; preserve historical snapshots. Citation display needs
physical field path/object identity, with names as labels. Add explicit new field
cases to Python3.10 focused CI, actual SDK2 tests and default Codex image review/
correction. Keep <=30 counted files per segment; guides/model harness can follow
separately without version bumps. ODS lifecycle and remaining formats stay in scope.

## Native PDF field core — full local verification passed; publication next

Current goal turn: PROGRESS. Public/version declarations stay1.4.0; next consolidated
release1.4.1, no per-feature bump/tag. Internal core only: field MCP contract,
managed evidence/citations/Wiki and default Codex field evaluation remain pending.
Full current suite:4084passed/49optional-environment skips/3intentional malformed
fixture warnings/598.37s. Session40006 completed exit0. Final80 field tests are
included; all349runtime hashes match the focused core proof, wheel and Docker.
Ruff/format826/mypy349/Bandit/zizmor, release-harness audit, allartifact/metadata
checks, docs generation, asset synchronization and diff hygiene pass.
Installed Python3.13 wheel AND actual Dockerfile Python3.12 image reproduced all
five reviewed synthetic/upstream CRUD outputs and COMPLETE receipts exactly;
doctor/tool listing/SDK2 stdio also pass. These are internal adapter/package checks,
NOT a field MCP/default Codex evaluation. Extension and bundled harness bytes are
unchanged from82061f7: prior205local tests reused, new-head remote activation needed.
Local proof:/run/user/1000/asset-aware-pdf-field-local-proof.json; full/source/artifact
and replay logs/manifests use the same prefix. Completed passing fulltest temp
781586800bytes removed with manifest; previous3passing PDF temps likewise removed.
First cleanup inventory blocked on an intentional FIFO fixture; only its owned
cleanup shell/child stopped (86725 exit143), file-type-aware inventory completed.
The full TEST run passed first time; no assertion/timeout change. All failed prior
core/model/visual logs remain. Docker imagea51949f4341d/builder459f9b5febab and own
wheel venv removed. All11 historical trace trees temporarily staged for buildspace
were restored with exact bytes/size/mtime; no other project/cache cleanup.
Next: exactstage14counted+2MEM, commit/push directmain asu9401066, noPR/tag, then all
10CI jobs/3Pages jobs/8deployed bytechecks before furtherdevelopment. Prepared watcher
/run/user/1000/asset-aware-pdf-field-verify-publication.py takes the new full HEAD.
Parent82061f7 stays fullypublished; original dirty checkout remains untouched.

## Native PDF field CRUD core — verified; MCP integration/publication next

Current goal turn: PROGRESS. Internal native creation/update/deletion now exists;
this is no longer only a read catalog. The complete user objective stays ACTIVE.
Public version remains 1.4.0; next consolidated release 1.4.1, no feature bump/tag.
Designated agent-assets main HEAD remains 82061f7; no commit/push attempted here.
Original dirty worktree untouched. Current segment: 14 counted files + both MEM,
all under the 30-file cap. Exact source hashes and verification scope are at
/run/user/1000/asset-aware-pdf-field-core-proof.json. Prior foundation proof is
historical and does NOT describe the newly extended domain model/current sources.

New files/modules: native_pdf_field_appearance.py (disposable HTML/Unicode form
XObjects, glyph/fit checks, point/UserUnit/rotation conversion, font reuse),
native_pdf_field_journal.py (planned-key/array undo, incoming dependencies and
bounded edge scanning), native_pdf_field_values.py (typed V/AS/Opt/I updates),
native_pdf_field_edits.py (atomic CRUD, serialized/inverse graph and pixel checks),
and test_native_pdf_field_edits.py. Existing new domain model now has typed edits,
styles, definitions and explicit new_groups creation. README, CHANGELOG and the
human gap analysis link the expanded native-pdf-fields-spec and clearly mark the
core as INTERNAL, not an advertised MCP operation.

Core supports text/choice/checkbox/radio creation, multiple widgets, hidden values,
root/child/new nested group creation, exact-reference value/style updates and
subtree deletion with ALL removed field records. Visible text/choice edits need
explicit styles for every widget; existing rectangles and widget rotations stay.
Buttons preserve appearance stream bytes and update all AS with V. Choice indices
and duplicate export values survive. Multiline/comb and single-line fit are distinct;
no silent truncation, glyph replacement, wrapping or automatic font-size reduction.
Identical value/style yields original bytes; source fonts/resources are reused.
Existing scripts/actions are preserved, not executed or semantically verified.
Guards retain source encryption/signatures/XFA, ambiguous/direct/shared ownership,
locks/read-only/tags, NeedAppearances reconciliation, rich/password/file-select value
workflows, ambiguous radio state ownership and inherited-choice clearing limits.

Verification on final current core: 80 focused tests passed (33 record + 47 edit),
7.01s; the 3 warnings are intentional malformed fixtures. Earlier broad PDF suite:
314 passed, 22.39s, BEFORE the last edge-accounting regression/fix; final 80 include
that last change. Full Ruff passed, format826 files passed, mypy349 sources passed,
25 docs tests passed, site generation check current, diff check passed. No full
release harness or form MCP stdio/default Codex test yet. No task subprocess remains:
sessions 21713/24905/26650/49859/37729/54105/70106/35148/53976/78501/27950 all terminal.

Retained direct-adapter visual exercise: /dev/shm/asset-aware-pdf-field-visual-01,
original/created/changed/deleted PDFs and all 8 actual page images viewed. Both
visible fields changed from 中文007µgα to 更新008µgβ, with source content retained.
Final code reproduced all three prior output PDFs byte-exact; proof is
/run/user/1000/asset-aware-pdf-field-final-reproduction-01.json. Current complete
receipts are receipts-final.json; original receipts remain. This is NOT the user-
required default Codex/MCP evaluation.

Pinned real upstream form.pdf received Chinese text, /Yes checkbox and /Choice2
radio updates, then text deletion. Attempt01 rejected 12pt overflow (log retained).
Attempt02 used explicit 8pt and passed native checks, but actual visual comparison
revealed its default border1 added an unwanted black frame. Original field MK was
empty with no BS/Border/AP; Agent explicitly corrected border_width=0 in attempt03.
ALL 3 final images were viewed: no added border, fitting text, native checkbox/radio
appearance retained. Source bytes unchanged. Final /dev/shm/asset-aware-pdf-field-
upstream-edits-03/proof.json marks this scoped visual review; attempt02 PDFs/images
and attempt01 failure remain. In total14 images viewed (8 synthetic, 3 attempt02,
3 corrected attempt03). No general form/viewer fidelity claim.

Also retained failed edits-test-02: an empty no-border draw still emitted an S
stroke through PyMuPDF. Skipping that draw fixed it; original pixel equality test
now passes. Do not relax it. pikepdf items() includes null entries that keys() omits;
style/resource shallow copies filter those semantically absent values and have a
regression. Dependency accounting now counts repeated indirect EDGES, not just
container nodes; a regression proves the budget cannot be bypassed by an array of
references. Full logs: /run/user/1000/asset-aware-pdf-field-*.

Next work: finish the appropriate segment release checks and publish this coherent
core before expansion exceeds30 files, then integrate paged MCP field reads/CRUD,
worker/adapter methods, managed receipts/full refs, selections/derivations/citations/
Wiki and actual default Codex review/correction. No MCP enabled flag is present yet.
Read-only integration reconnaissance found NativePdfAnnotationOperations in
src/application/native_pdf_annotation_operations.py; op routing is in
native_document_service.py, native_document_contract.py and domain/native_operations.py.
Reference unions additionally touch domain/native_assets.py/native_pdf.py/
native_selection.py/native_derivation.py and application/native_evidence_service.py.
Preserve full objective including ODS lifecycle and other formats; do not declare
completion based on this backend or substitute a read-only-only endpoint.

Rules persist: direct main, author AND committer u9401066 <u9401066@gap.kmu.edu.tw>,
no PR/subagents, exact staging, atomic both MEM, <=30 counted files excluding ONLY
both MEM. After any push verify exact-head 10 CI jobs, 3 Pages jobs and deployed
bytes before further development. Prior82061f7 publication gate is complete. No
source writeback or original worktree mutation. Safe isolated VSIX CLI is retained
/dev/shm/asset-aware-ods-guides-cli-02/code; never use remote-cli launcher. Current
owned PDF test/visual fixtures remain retained; do not clean other projects/caches.


## Native PDF field identities — tested foundation; CRUD remains active

Current goal turn: PROGRESS. Public version is still 1.4.0; next consolidated
release is 1.4.1. All seven version values (Python project/module/uv root package,
Docker and extension manifest/lock/root lock entry) were re-read and agree.
Do not bump a version per feature. No new tag or release was created.

Six uncommitted counted files now implement and document the internal PDF field
read/identity foundation: src/domain/native_pdf_fields.py;
src/infrastructure/native_pdf_field_tree.py; src/infrastructure/native_pdf_fields.py;
tests/native_pdf_field_helpers.py; tests/unit/test_native_pdf_field_records.py;
docs/native-pdf-fields-spec.md. Both MEM are modified as required; HEAD/main and
origin/main remain 82061f7. Original dirty worktree remains untouched. No new MCP
operation/flag is advertised yet. This is NOT delivered form CRUD or overall goal
completion. Continue native creation/update/deletion, checked serialized readback,
MCP/evidence/Wiki, then actual default Codex visual review/correction. Keep ODS
lifecycle and the broader format objective in scope.

Implementation: physical Fields/Kids index paths + original object identities;
full refs pin revision/record hash, never names alone. Raw traversal retains radio
owners and every page Widget occurrence, duplicate names, hidden fields, ancestor
origins, multiselect Opt/V/I/TI, original appearance graphs/resources and unknown
properties. Parent links, detached/orphan/direct widgets and ambiguity remain
explicit. Cycles/shared tree ownership/invalid arrays and bounded count/depth/size
fail instead of implicit repair. Catalog includes form-properties and full record
hashes; group records do not recursively claim descendant values. Native encryption,
signature and XFA mutation guards are unchanged. Reader never calls form repair.

Validation completed: 33 new field-record regressions; 268 PDF-related unit/audit
tests passed in 16.39s, including those 33. Three PageCopyWarning observations are
from intentionally malformed orphan/direct/bad-Fields fixtures. Full repository
Ruff check passed; format check 821 files passed; mypy all 345 source files passed.
No full release harness, new form stdio workflow or actual Codex form run yet.
No commit/push has been attempted for this segment. Logs/proof:
/run/user/1000/asset-aware-pdf-field-foundation-proof.json
/run/user/1000/asset-aware-pdf-field-unit-01.log
/run/user/1000/asset-aware-pdf-fields-version-proof.json
Owned pytest fixture directory: /dev/shm/asset-aware-pdf-field-unit-01 (retain).
Session 89463 completed exit 0; no live task subprocess remains.

Pinned upstream checks on final current source: form.pdf gives 4 logical fields /
5 widgets, zero orphans; form_210966.pdf gives 64 nodes / 61 terminal fields /
69 widgets, zero orphans, XFA retained. Source bytes and complete native graphs
stay unchanged. IMPORTANT correction: form_dd0293.pdf is encrypted (empty user
password permits low-level pikepdf opening); our existing NativePdfPackage guard
rejects it. Prior raw upstream lookup was not proof of native package acceptance.
The first catalog experiment stopped on that guard after two successful inputs;
its observation is retained as asset-aware-pdf-field-upstream-catalog-01-failure.json
(explicitly reconstructed from original tool result, not an original stdout log).
The follow-up catalog-02.json and foundation proof distinguish the guarded input;
never strip encryption/XFA or claim this input passed our native workflow.

Latest published 82061f7 remains fully verified: 10 CI jobs, 3 Pages jobs and all
7 deployed files. Newly inspected exact-head integration log reports 212 passed /
556.06s. No publication gate remains for that prior commit. Current runtime changes
need their own appropriate checks before future publication; do not inherit the
prior unchanged-runtime release proof for these new Python modules.

Remain on designated agent-assets main; author and committer must both be
u9401066 <u9401066@gap.kmu.edu.tw>. At most 30 counted files per segment, excluding
only both MEM; exact staging and atomic MEM updates. No subagents, PR, source
writeback, or changes in the original dirty worktree. Full goal remains ACTIVE.


## 82061f7 publication verified — native PDF fields next

Watcher 84347 completed with exit 0. ALL 10 CI jobs, ALL 3 Pages jobs and all 7
deployed files match 82061f7b9412c7a122d74f76255538a2f512c0a1. The publication gate
is complete; next development is allowed. Exact-head remote evidence: Linux and
macOS 205 extension passes plus installed activation; Windows 204 passes / 1 existing
platform skip, all 6 new isolation regressions and actual isolated installation;
3,755 Python unit passes / 1 skip; Python 3.10 1,611 passes / 4 skips / 924.23s;
integration success in its retained log. Proofs/logs: /run/user/1000/asset-aware-ods-guides-*.
Completed owned npm dependencies/cache were removed after all platform checks;
workspace node_modules link was already absent. Safe CLI shim remains at
/dev/shm/asset-aware-ods-guides-cli-02/code, pointing to LOCAL code-server-insiders.
Never use the remote terminal launcher for future local install smoke.

Current focus is native PDF AcroForm CRUD, preserving exact field identity, all page
Widget occurrences and appearance/value consistency, followed by MCP/evidence/Wiki
and actual default Codex review/correction. Keep ODS remaining lifecycle and all other
formats in scope. No PDF runtime files have been edited yet. Do not replace this
objective with read-only catalog support or claim the whole goal complete.

Upstream pinned reference inputs are at /dev/shm/asset-aware-pdf-forms-upstream-01;
manifest /run/user/1000/asset-aware-pdf-forms-upstream-fixtures-01.json has tag,
git blob IDs and SHA-256. form.pdf: 1 page, 4 root fields, 5 Widgets, no XFA;
form_210966.pdf: 2 pages, 69 Widgets, XFA; form_dd0293.pdf: 4 pages, 102 Widgets,
XFA. Preserve dual representation; do not strip XFA to claim AcroForm compatibility.
Read-only native lookup left object graph hashes unchanged for all 3 PDFs.
New concrete upstream issue: low-level AcroForm.fields enumerates the two radio
Widgets as separate terminal fields; get_annotations_for_field on their logical
parent returns zero in form.pdf. High-level Form special-cases this via names, which
cannot bind duplicate names safely. Walk the raw Fields/Kids tree with original
physical paths/object IDs and actual page Annots; keep group and widget identities
separate. Hidden/nonvisual fields must remain represented. Existing exact-page and
annotation geometry/object-graph helpers can be reused. AcroForm.validate defaults
repair=True; readonly validation must explicitly disable it. Other limits and sources
are retained in asset-aware-pdf-forms-upstream-research-01.json.

Version 1.4.0; next consolidated 1.4.1. Direct main, author/committer u9401066
<u9401066@gap.kmu.edu.tw>, <=30 counted files per segment excluding only both MEM.
No subagents/PRs. Original dirty worktree remains untouched. Full goal ACTIVE.

## Pushed 82061f7 — publication verification pending

Committed and pushed directly to main as u9401066 <u9401066@gap.kmu.edu.tw>
(author and committer), 22 counted files + both MEM. HEAD, origin/main and remote
main all verified as 82061f7b9412c7a122d74f76255538a2f512c0a1. Public version remains
1.4.0; next consolidated release 1.4.1; no tag/release/version bump.

Live watcher session 84347 runs /run/user/1000/asset-aware-ods-guides-verify-publication.py.
It was re-polled directly and remains running. CI 35640530886 currently has 7
successful jobs. Pages 35640529346 passed all 3 jobs and all 7 deployed files
match this commit exactly, including the human gap analysis. Do not start further
development until all 10 CI jobs succeed. Keep polling this handle; do not restart
on an observation timeout. Proof: /run/user/1000/asset-aware-ods-guides-publication-proof.json.

Fresh Linux CI evidence at this exact head is now retained in
/run/user/1000/asset-aware-ods-guides-ci-linux-vsix.log: 205 unit passes, isolated
installation manifest/guide-file checks, and actual installed extension activation
all passed. This supplies new-head activation evidence; local activation remains
not run. Other jobs are still pending. Current continuation is a VERIFIED WAIT:
session 84347 was directly observed for 60 seconds and remains live. No new
runtime, tests or guide edits during this gate. Previous goal turn was PROGRESS.

Further exact-head evidence: macOS 205 unit passes and 2 actual activation tests;
Windows 204 unit passes / 1 pre-existing platform skip (Codex config symlink test),
with all 6 new isolation regressions passing and isolated installation verified.
Windows activation is skipped. Python unit suite: 3,755 passed / 1 skipped, 515.21s.
Fresh macos/windows/unit logs and hashes are retained under the ods-guides prefix.

Read-only PDF follow-up research changed the implementation approach: installed and
locked pikepdf 10.13.0.post1 already provides Form and Pdf.acroform. Its name-based
MultipleFieldProxy writes only the first duplicate field, high-level multiselect is
single-select, and built-in appearance generators have limited encodings (multiline
fallback can replace unsupported characters). Use exact field object identity and
all Widgets, including hidden/nonvisual fields; do not blindly wrap those defaults.
AcroForm.validate defaults repair=True: readonly analysis must explicitly pass False.
Evidence, source hash/paths and official URLs are stored in
/run/user/1000/asset-aware-pdf-forms-upstream-research-01.json. This is research only;
no PDF field implementation or new runtime/test/guidance edits during the gate.
Previous goal turn was VERIFIED WAIT; this continuation re-observed live session
84347 for 60 seconds and collected these new results. Full goal remains ACTIVE.

This turn made concrete progress: delivered guides/docs and fixed false-positive
VSIX smoke isolation. Final 205 tests, 29 docs/contract tests, 37 packaged AND
installed bundled assets, real same-version update and 65 unchanged live extension
files are recorded below and in the local proof. All local test/model/build handles
are terminal; only watcher 84347 remains. Earlier local smoke passes that used the
same remote launcher cannot prove isolated installation. Keep the failed trace and
restoration evidence; remote CI is separate evidence. Actual source workspace files
in the original dirty checkout were not modified.

After this gate, continue the full format/CRUD/provenance/Wiki goal: ODS remaining
sheet/grid lifecycle, PDF fields/body operations (field tree plus all Widgets),
ODT/ODP/HTML/EPUB/email/LaTeX and other stated gaps. The guide segment is not goal
completion. No subagents, PRs or version jumps. Retained owned npm dependencies:
/dev/shm/asset-aware-ods-guides-node-01; the workspace node_modules symlink is removed.

## ODS guidance and isolated VSIX smoke fix — ready for main

This goal turn is PROGRESS. The previous wait completed: watcher 9479 exited 0;
8d6c38b passed all 10 CI jobs, all 3 Pages jobs and 6 exact deployed file checks.
Fresh remote suites: 3,755 unit passes / 1 skip; 1,611 Python 3.10 passes / 4 skips;
212 integration passes in 557.74 seconds. CI installed Calc 24.2.7 and passed the
complete ODS rename/native-reference/typed-cell/full-page comparison. The actual
Agent run remains the separate recorded Calc 7.3.7.2 case. Old publication/local
proofs under /run/user/1000/asset-aware-ods-rename-* now record completion.

Current segment: 22 counted files + both MEM. Five canonical Agent guides and
bundled copies cover complete dependency inventory pagination, distinct inventory
hash guard, rename identity/revision, receipts/current refs and actual page/formula
correction. Typed formula input begins '=' (not stored XML 'of:='). Updated README,
changelog, human gap analysis, ODS spec, Wiki and generated website. ODS remaining
sheet insertion/deletion/reorder, row/column lifecycle and all other format gaps
remain explicit. PDF form research from official pypdf/PyMuPDF docs shows fields
and multi-page Widgets need one coherent model; current annotation edits reject
Widgets. This is pending implementation, not claimed PDF form CRUD.

Actual test discovery: the host remote code-insiders launcher ignores isolation
flags but reports success. Initial extension-install-01 is INVALID as isolation
proof. upgrade-01 caught empty isolated directories after installing the baseline
into the live extension. The current 1.4.0 package was restored immediately and
all five live guide hashes matched current source. We did not capture the live
package before the first legacy smoke; do not claim restoration to an unknown
pre-turn artifact. Keep cli-restoration.log, install-01 and failed upgrade-01 logs.

Fix: installSmokeIsolation.ts rejects remote-cli paths and resolved aliases before
invocation, requires both isolation flags in help, and checks the installed manifest
and current five guide bytes inside the isolated directory. installSmoke.ts uses
these checks before install and when verifying results; warnings about ignored flags
fail. Six behavioral regressions cover rejection before invocation, aliasing, missing
options, absent/wrong installed manifest and stale/missing installed guides. Full-check
workflow and its bundled copy explain the required evidence.

Fresh final extension CI: 205 passed, 64 package-content entries; actual VSIX has
66 entries and all 37 bundled assets equal sources. The corrected install smoke
passed through an explicit local code-server-insiders shim (not remote-cli), with
installed filesystem checks. No display: local activation skipped; legacy 0.2.10
baseline absent. Separate real same-version 1.4.0 baseline -> current replay passed:
all 37 installed assets match, test settings preserved, and all 65 live extension
files retain hash/size/mtime. The baseline is a constructed package restoring the
five prior-head guide files; this is not a previously published VSIX. Proofs/scripts/
logs under /run/user/1000/asset-aware-ods-guides-*; actual isolated tree under
/dev/shm/asset-aware-ods-guides-upgrade-03. Failed upgrade-01 remains retained.

29 docs/contract tests passed; both skill validators, docs sync, asset sync, release
harness, metadata/VSIX audit and diff hygiene passed. Python runtime's 342 source
hashes equal fully verified 8d6c38b: reuse that runtime/full-suite/wheel/Docker/Agent
evidence, not a new Python or Agent run. GitHub description/homepage/20 topics still
accurate. Public 1.4.0; next consolidated 1.4.1; no bump/tag/release. Node dependency
symlink removed; owned /dev/shm/asset-aware-ods-guides-node-01 and npm-cache-01
remain available for follow-up tests. Other projects and original dirty worktree
untouched. No local jobs remain active. Next: exact staging, user-author direct-main
commit/push, then verify every new-head CI/Pages job and deployed bytes before more
development. Goal remains ACTIVE and full scope unchanged; no subagents or PRs.

## ODS rename committed/pushed — exact-head publication gate pending

Commit8d6c38b014e2f9f90c3eb6f9d9e1ed7668a607d0 is on main/origin as
u9401066<u9401066@gap.kmu.edu.tw>, exactly30countedfiles+2MEM. No bump/tag/release:
public1.4.0,nextconsolidated1.4.1. Full4004pass/49skip599.67s; optional Calc
6passes plus unchanged-font-environment rerun1pass23.55s. Installedwheel/Docker,
SDK2, actual default Codex323successfulcalls/sixPNG and native/history/Wiki proofs
passed as detailed below. All4temporarily staged historic traces restored exactly.
All local tests/builds/model processes finished; onlypublicationwatcher remains.

Active watcher session9479 runs
/run/user/1000/asset-aware-ods-rename-verify-publication.py
CI35636438898 and Pages35636437551, exacthead8d6c38b. First API retry recovered
from transient connectivity; push succeeded. The watcher requires ALL10CI jobs,
ALL3Pages jobs and6deployed files byte-exact, plus remote main identity. Proof:
/run/user/1000/asset-aware-ods-rename-publication-proof.json. Read/wait existing
session; do not create a duplicate watcher. Do NOT begin new development until
this gate is verified. If a job fails, retain exact logs and resolve its cause.
Local proofstatus pushed_remote_verification_pending; update it afterallpass.
No new release/version is authorized by a per-feature milestone.

Goal ACTIVE, this turnPROGRESS. Oncegatespass, updateMEM and continue fullscope:
ODS table/row/column lifecycle, remainingformatCRUD/evidence/Wiki, actual Agent
review. Bundled assistant guide refresh needs next<=30countedfile segment.
OnlypostpushMEM files may be dirty. Original dirtydetachedcheckout remains untouched.

## ODS checked worksheet rename — locally verified, direct-main commit pending

Public/latest release1.4.0; next consolidated1.4.1. NO version/tag/release change.
Previous main/origin ddf4a9af03e95ca6b6d1fae4a42199abb655021d fullyverified.
This segment contains30countedfiles+2MEM; userauthor/committer
u9401066<u9401066@gap.kmu.edu.tw>, directmain, no PR/branch/subagents.
Work onlyagent-assets/main; original dirty detached checkout/servers untouched.
Goal ACTIVE. This is PROGRESS, not full all-format/table-row-column completion.
MCP checks native/source/version mechanics; Agent reviews and corrects meaning,
actual appearance and calculated formulas. No new permissions are needed.

New read_ods_dependencies inventory pins owners, XML paths/attributes, namespaces,
source contexts and whole-inventory SHA; rename_ods_table pins revision plus exact
table index/name and inventory. Supported cell/named/conditional/chart/settings
references map together, including Calc chart-cache provenance (svg:desc/legacyid),
while embedded-local references and ordinary literals/captions remain distinct.
Complete plans/snapshots checked before apply, native XML reopened before onecommit.
Unknown owners/aliases/sources, xmlbase, opaque/revision-aware/protected/signed data
retain guards. Typed formula caches invalidate; cache receipts label intermediate
post-rename identity. Styles, compressed ranges, unrelated members, sourcebytes/
mtime and historical references/Wikis remain fixed. No-op creates no history.
No sheet insertion/deletion/reordering or row/column lifecycle exposed yet.

Validation: full suite4004passed/49environment skips/599.67s, exit0.
/run/user/1000/asset-aware-ods-rename-full-02.log; session98900 CLOSED.
Owned completed full02temp781596303bytes removed afterproof. Earlier full01
hit PDF annotation timeout after owned bytecode cleanup under diskpressure; retained
log and byte-verified1793file fixture archive17,307,287bytes SHA
45a46770a7c9f554d9479d080565fd1c7a919ea71bb34ac52d583313340b157e.
Only that timed-out owned process tree stopped (session42183 exit143). Venv/src
bytecode rebuilt; isolated unchanged annotation2passed/276.16s then full02passed.
Do not weaken timeout/assertions or claim the initial run passed.

ODS focused131passed; SDK2 rename/restart2passed5.39s. Real Calc7.3 rename/reimport
compares supported cross-part references, typed cells and both full page images.
After fixing native named/conditional preview grammar (including calcext:value),
102focusedpassed3.78s and77render/audit tests passed. External-resource/unknown-
prefix/dynamic-INDIRECT guards retained. Optional final Calc batch6passed/1failed:
private CJK font environment clipped LAST PRINT to LAST PRIN in an existing
whole-sheet fixture; preserve outputs/logs. SAME unchanged test in normal fontenv
passed23.55s (session89488 closed). All7 optional tests therefore exercised; source
and assertions unchanged. Font-specific clipping remains a real reviewed limitation.
Current transaction actual24.2 notrerun; prior captured24.2owner observations are
not interchangeable with current kernel/render proof. All failure traces retained.

Default Codex run02 /dev/shm/asset-aware-codex-ods-rename-02:255.95s,
323successful MCP calls/3corrected invocation errors, six actual PNGs, three native
revisions, two native Wikis. Agent detects #REF afterrename, corrects INDIRECT's
literal to quoted new sheet, verifies rendered1 and chartA/B/C1/2/3; old refs and
sourcebytes/mtime remain intact. audit.json PASSED; source342hashes EXACTLY match
current runtime, wheel and Docker. Independent Calc reimport for BOTH edits matches
36reference/settings records/19typedcells/two full PDF pages each. Root additionally
viewed both delivered finalPNG; root-visual-review.json records CJK/header/data/
chart findings. First modelrun01 failed preview's old prefix check (no actualpages),
retained. Run02 first audit wrongly used PDF text order for cell identity; retained
audit-01-reading-order-failure.json. Corrected geometry audit +2regressions reject
chart-axis substitution. No modeloverride and no false general fidelity claim.

New CI/unit/realCalc/SDK2 tests, README/CHANGELOG/native-ods-spec, Wiki and generated
site updated. Bundled assistant guide refresh belongs to NEXT segment(30filelimit).
Ruff/format816files/mypy342/banditmedium/metadata/releaseharness/docs generation/
29docs-contract tests/asset sync/diff passed. Extension sources/assets unchanged;
reuse prior199tests/64entries as prior evidence, NOT a fresh local run. New exact-
head remote extension packaging/activation remains required before further work.
GitHub description/topics re-read stillaccurate; latest releasev1.4.0.

Wheel/sdist /dev/shm/asset-aware-ods-rename-dist-01 match342source hashes.
Temporary repo dist symlink REMOVED (it was not ignored as a symlink). Installed
Python3.13 wheel and actual Dockerfile Python3.12 image pass exact native output/
full receipt/dependency inventory/restart/history/Wiki, doctor,30tools andSDK2stdio.
/run/user/1000/asset-aware-ods-rename-local-proof.json records logs/hashes/scope.
Artifact smoke/golden/source manifest outside repo under sameprefix.
Owned Dockeraaf27162420e/builder54b7d511f54b and wheelenv removed. Four owned
historic traces temporarily staged with NEW rename-space manifest have ALL been
restored to exact bytes/size/mtime; other7untouched. Do not rerun old stage scripts.
Current7.3runtime and private CJKfont fixture stay for future checks. No24.2runtime.
No live local tests/builds/model jobs remain. Source/style checks did not alter
user caches or original checkout. No generated artifacts staged/committed.

Next: exactstage30+2MEM, commit/push directmain asuser; then verify ALL exact-head
10CI jobs,3Pages jobs and6deployed files byte-for-byte BEFORE new development.
Use a NEW publication proof/watcher, keep all failed logs and do not bump version.
After publication gate, update MEM with exacthead/results and continue broader goal.

## ODS reference publication verified; lifecycle observations retained

Head ddf4a9af03e95ca6b6d1fae4a42199abb655021d is fully verified on main/origin.
ALL 10 CI jobs 35625034811, ALL 3 Pages jobs 35625033365 and all 6 deployed
files passed exact-head/byte checks. Watcher 15248 completed with exit 0; do not
restart it. Publication proof is /run/user/1000/asset-aware-ods-reference-publication-proof.json.
The matching local-proof.json now records local_and_publication_verified. Remote
logs under the same prefix record 3673 unit passes/1 skip/408.11s, 1514 Python3.10
passes/4 skips/917.08s, 209 integration passes/536.39s (including actual Calc
reference test), and actual installed Linux VSIX activation. Their hashes are in
local proof. All 340 current runtime files still match the tested artifact source
manifest. Seven version declarations and public docs remain 1.4.0; latest GitHub
release re-read v1.4.0. Next consolidated release 1.4.1; no bump/tag/release.
User author/committer and direct-main instructions remain unchanged.

After the publication gate completed, independent generated Calc fixtures explored
three operations in each of Calc7.3.7.2 and24.2.7.2: sheet rename, sheet deletion,
and deletion of all three data rows. Six before/after ODS files per version (12
native files total) retain global/local named ranges, named expressions, conditional
formatting, validation, print ranges, chart dependencies and per-sheet settings.
These are observations, NOT production candidate/MCP/visual proof or a universal
correctness oracle. No repository runtime or tests changed in this turn.

Both versions in these fixtures: rename changes references in content.xml,
ChartEvidence/content.xml and settings.xml; named expressions/validation/style
conditions use expression forms without the cell formula's leading '='. Sheet
deletion leaves surviving named ranges as named-range elements with #REF! address,
but chart addresses become Observer ranges at the former Source coordinates.
Deleting the data rows makes absolute named ranges #REF! while the relative named
range retains Source.A2:.B4; chart addresses also retain original coordinates.
Do not blindly reproduce these chart bindings as correct semantic behavior.
The package transaction needs owner-specific dependency policies and Agent review.
Exact native packages are retained, including the data behind those observations.

Probe scripts/logs/directories:
/run/user/1000/asset-aware-ods-lifecycle-probe-02 (Calc7.3)
/run/user/1000/asset-aware-ods-lifecycle-probe-03 (Calc24.2, matching bundledPython)
The -01 failed attempt used nonexistent UNO ValidationType.CELLRANGE; its script
and traceback are retained. -02 uses the documented LIST enumeration and passes.
Combined observations: /run/user/1000/asset-aware-ods-lifecycle-observations-01.json.
Complete hashes/scope/cleanup: /run/user/1000/asset-aware-ods-lifecycle-local-observation-proof-01.json.
Probe02 dependency-attributes.json additionally indexes selected native reference
attributes with qualified XML paths; it is not a complete schema/semantic catalog.
Private24.2 install verified the pinned official archive plus42 packages, used no
system package install, and removed its owned698068071-byte runtime afterward.
All three owned Calc profiles removed; native fixtures/logs/proofs and preexisting
Calc7.3 remain. Install98524 and probe2695 both completed exit0. No live watcher or
experiment remains. Original dirty detached checkout and its servers untouched.

Read-only upstream planning checked LibreOffice sc/source/core/tool/refupdat.cxx,
Office/Calc.xcs ExpandReference (default false, application preference), OASIS named
range/base-address semantics, UNO XNamedRanges/XTableCharts and ValidationType.
Future axis transactions need an explicit compatible expansion policy, workbook
sheet identity/source resolution, relative named-range/base semantics, compressed
row/column/style/merge maps, and chart/drawing/conditional/settings dependencies.
Next implementation remains the ODS native structural package/transaction layer
and MCP integration with immutable receipts, history/Wiki and actual Agent review.
Do not advertise lifecycle support from this reference primitive or these probes.
All-format ODT/ODP/HTML/EPUB/email/LaTeX work remains in scope. MCP necessary checks;
Agent full semantic/visual/formula review and correction. No subagents.

Previous turn and this turn are PROGRESS; goal remains ACTIVE, not complete or
blocked. Work only agent-assets/main. Only two post-publication MEM files are dirty
for the next <=30-counted-file segment; retain all historical sections below.

## ODS structural references — ddf4a9a pushed; exact-head checks pending

Head ddf4a9af03e95ca6b6d1fae4a42199abb655021d is committed/pushed directmain as
u9401066<u9401066@gap.kmu.edu.tw>,10countedfiles+2MEM. No bump/tag/release:
public1.4.0,nextconsolidated1.4.1. Parent eeb7510 fullyverified.

LIVE publication watcher15248. Poll this samehandle; do not duplicate/restart just
because observation expires. CI35625034811 requires ALL10jobs; Pages35625033365
requires ALL3jobs plus6deployed files byte-exact. Current proof remains pending.
Script /run/user/1000/asset-aware-ods-reference-verify-publication.py
Log /run/user/1000/asset-aware-ods-reference-publication-watch.log
Proof /run/user/1000/asset-aware-ods-reference-publication-proof.json
No new development until exact-head verification completes.

Localfull3922passed/47environment-skips/604.03s; separately6actualWord/ODSrender
casespassed/41.10s. New77focusedpassed. Calc7.3/24.2 each16operations/304formulas,
with SAME-version native candidate/control reimport and exact complete-formula
comparison. Wheel3.13/Docker3.12 each340sourcehashes+608capturedCalc replays,
lockedSDK2.2doctor/30tools/actualstdio pass; no actualCalc-in-artifact claim.
Allprior339runtimefiles unchanged; new pure domain reference primitive not yet
MCP lifecycle CRUD. No new modelrun claimed. New CI requires OS pyuno actual
reference test and Python3.10 kernel tests. README/CHANGELOG/spec explicitly retain
native package/dependency/transaction/Agent lifecycle work as next scope.
Ruff/format809/mypy340/bandit/docs/sync/artifactmetadata/diff checks passed.
Extensionassets unchanged, parent199tests/64entries reused; currentremoteactivation
still required. GitHubdescription/homepage/20topics re-read accurate, unchanged.

All11historical modeltrace dirs restoredordinary with exacthash/size/mtime.
OwnedCalc24.2runtime, wheelvenv/data, Dockerimage/builder and completedtesttemps
removed; logs/proofs/dist/preexisting7.3/warmbytecode retained. Original dirty
checkout untouched. No subagents. Goal ACTIVE; this turn is PROGRESS, not completion.
Only post-push2MEM checkpoints remain dirty for the next segment.


## ODS structural references — locally verified, ready to commit

Current10countedfiles+2MEM implement an internal OpenFormula reference-mapping
foundation, independent Calc UNO oracle/reimport comparison and artifact replay;
CI+releaseharness now require OS pyuno/actual edits and Python3.10 kernel tests.
README/CHANGELOG/native-ods-spec describe the remaining MCP lifecycle gap. No
schema/dependency/version change; all7declarations1.4.0,nextconsolidated1.4.1.
No new model run: no MCP structural operation is exposed by this segment.
The broader native package/lifecycle/dependency/Agent evaluation work remains.

Local full3922passed/47skips/604.03s, plus6actualWord/ODSrender cases/41.10s that
were disabled in that full run; no merged/full-count claim. New77focusedpassed/
5.43s. Calc7.3 and24.2 each16actualstructuraloperations/304formulas. Candidate and
independent control BOTH reopen in the SAME Calc; complete formulas then match.
Rawspellingdifferences retained:0in7.3,2in24.2. Allfailedlogs remain. Proof dirs
/run/user/1000/asset-aware-ods-reference-calc{73,242}-proof contain original/control/
candidateODS and hashes. 24.2 uses its matching bundledPython; system7.3pyuno was
incompatible. Domain340-source manifest matches wheel/sdist and installed artifacts;
allprior339sourcefiles identical to published eeb7510. WheelPython3.13 and Docker
Python3.12 each608captured-Calc candidate replays, lockedSDK2.2doctor,30tools and
actualSDK2stdio pass. They do not claim actualCalc installation in artifacts.

Ruff/format809,mypy340,banditmedium,35docs/artifactchecks, releaseharness, generated
docs,sync-assets,allversionmetadata and diffhygiene pass. Extension/source/Agent
assets byte-identical to verified eeb7510: reuse199tests/64entries/install proof;
no new localextensionrun claimed. Exact-head remoteactivation still required.
GitHubdescription/homepage/20topics reread accurate, unchanged. Public1.4.0 only.
Localproof /run/user/1000/asset-aware-ods-reference-local-proof.json.

Fullrunner82635, build60790, Docker53691, render26053 and allartifact/cleanup
processes terminal0. OwnedCalc24.2extraction, wheelvenv/data, Docker9d737e5766f6/
builder42879215b15c and completedfull/supplementaltemps removed. All11historical
modeltrace dirs restoredordinary with exactfilehash/size/mtime via two current
space manifests. Warmbytecode and preexistingCalc7.3 retained. Logs/proofs/dist
retained; original dirtydetached checkout untouched. No subagents. Goal ACTIVE.

Next exactstage10+2MEM, userauthor/committer u9401066<u9401066@gap.kmu.edu.tw>,
directmaincommit/push; ALL10CI/3Pages/6deployedbytechecks before newdevelopment.
Then integrate nativeODS table/row/column operations and dependent native objects;
ODT/ODP/HTML/EPUB/email/LaTeX/allformats remain in scope. Do not mark complete.


## ODS structural references — implementation and verification in progress

Previous goal turn was PROGRESS: eeb7510 publication all10CI/3Pages/6deployed
files verified. This turn re-read live GitHub main and CI; exacthead unchanged.
Goal remains ACTIVE; all-format scope unchanged, no subagents. Work ONLY
agent-assets/main. Public1.4.0, nextconsolidated1.4.1; no per-feature version bump.

New pure domain primitive src/domain/native_ods_references.py parses OpenFormula
points/ranges/wholeaxes, quoted/Unicode names, external sources and errors; maps
row/column insert/delete and sheet rename/delete. Exact literals/namespace spelling/
dollar flags and original Unicode change spans retained. Explicit grid limits,
range contraction, sticky final-grid endpoints and #REF! behavior verified with
real Calc UNO edits. This is NOT yet an advertised MCP structural operation.
Package rows/columns/styles/merges/names/object dependencies, full transactions,
receipts/history/Wiki and Agent lifecycle evaluation are still required. Multi-
sheet/nested-table axis edits need explicit context; source fragments need resolver.

Current changes: domain module, unit tests, independent OS/bundled-Python UNO
oracle and integration/artifact replay scripts; CI+releaseharness guard, README/
CHANGELOG/native-ods-spec. <=30countedfiles. No public schema or runtime dependency
changes. No new model run claimed; model evaluation follows MCP lifecycle wiring.
Calc7.3 final77focusedpassed/5.43s (76unit+1integration); Calc24.2 independent
integrationpassed/9.77s. Each exercises16actualoperations/304formulas. Both sides
are reimported into the SAME Calc before exact complete-formula comparison;
raw spelling differences retained (7.3:0,24.2:2), not numerical-equivalence checks.
Proofs /run/user/1000/asset-aware-ods-reference-calc{73,242}-proof retain generated
ODS/control/candidate files+hashed inventory. System7.3pyuno could not drive24.2;
24.2 bundledPython works. Allfailedlogs retained under sameprefix; use -06 final
24.2 log. Python3.8-compatible oracle serialization fixed; no expectation weakening.

Full suite RUNNING session82635, log /run/user/1000/asset-aware-ods-reference-full-01.log,
owned basetemp /dev/shm/asset-aware-ods-reference-full-01. Poll samehandle; do not
restart on observation timeout. It enables actual7.3reference oracle. Warm bytecode
retained. Wheel/sdist build session60790; poll it. Sources340, mypy340passed; Ruff/
format809,35docs/artifacttests, releaseharness/versionmetadata/sync checks passed.
Private24.2 extraction removed after success; preexisting7.3 untouched. Artifacts/
oldmodeltraces preserved; no root/global cleanup. Before new artifacts/checks inspect
space. No commit/push yet. Remaining: fullresult, installedwheel/Docker608formula
captured-Calc replay+sourcehashes, relevant package checks, finalreview/MEM/exactstage,
userauthor directmaincommit/push, thenALLexact-head10CI/3Pages/6deployedbytes.


## ODS rendition guidance — publication COMPLETE, eeb7510 verified

Head eeb751055c122d26a799316f4203685b1142f7cb remains main/origin with user author
and committer u9401066<u9401066@gap.kmu.edu.tw>. ALL10CI jobs35617320856 and
ALL3Pages jobs35617319164 passed; all6deployed files match exactcommit bytes.
Watcher51323 completed; no duplicate watcher was started. Publicationproof and
localproof under /run/user/1000/asset-aware-ods-rendition-guides now record success.
No runtime changes in this checkpoint; guide commit13countedfiles+2MEM remains
the latest published segment. Local55focused/199extension tests and packaged5guide
checks remain recorded; unchanged runtime339files reuse parent full3847/41 and
actualdefaultCodex208calls/11PNGs evidence, not a new local full/model run.
Downloaded exacthead remote logs separately prove3597unitpassed/1skip/467.74s,
1438Python3.10passed/4skips/918.68s and installedLinuxextensionactivationpassed.
Logs retained at sameprefix-ci-{unit,python310,linux-vsix}.log; hashes in localproof.

Seven project version declarations rechecked: ALL1.4.0. GitHub latest release
re-read v1.4.0; next consolidated1.4.1. No per-feature bump/tag/release.
Version correction remains binding; MCP SDK dependency version is independent.
One git ls-remote attempt encountered transient DNS failure; authoritative GitHub
API confirmed main at this exacthead, and publication verifier completed normally.

Read-only preparation reviewed existing ODS compressed-grid/editor/service and
upstream odfdo table/cache plus OASIS1.4 OpenFormula reference grammar. Upstream
odfdo main observed c7d320fd5010898856913d6462ebea25139984d0. Structural insertion
alone does not establish dependency preservation; next segment must cover table/
row/column identity, formulas, ranges, object anchors and actual Calc comparisons.
No lifecycle implementation or new behavioral test is claimed in this checkpoint.
Broader ODS lifecycle/rich-runs and ODT/ODP/HTML/EPUB/email/LaTeX/all-format work
remain active. MCP mechanical checks; Agent semantic/visual/result correction.
Work ONLY agent-assets/main; original dirtydetached checkout untouched. No
subagents. Only two MEM checkpoint files dirty for the next <=30countedfile segment.
Goal ACTIVE, not complete/blocked. This turn makes publication-verification progress.


## ODS rendition guidance — eeb7510 pushed; exact-head checks pending

Head eeb751055c122d26a799316f4203685b1142f7cb is committed/pushed directmain as
u9401066<u9401066@gap.kmu.edu.tw>,13countedfiles+2MEM. CI35617320856 and
Pages35617319164 require ALL10/ALL3jobs and6deployed exactbyte checks.
LIVE watcher51323; poll samehandle, do not duplicate.
Script /run/user/1000/asset-aware-ods-rendition-guides-verify-publication.py
Log /run/user/1000/asset-aware-ods-rendition-guides-publication-watch.log
Proof /run/user/1000/asset-aware-ods-rendition-guides-publication-proof.json
No new development until exact-head verification completes.

FiveAgent sources+fivebundledcopies align ODS rendition/source_formats discovery,
complete receipts/actualpage review, cache/clipping and MCP/Agent responsibilities.
README/CHANGELOG/native-ods-spec updated. Currentfocused55passed, VSIX199tests/
64entries/install-update,5actualpackagedguides byte-equal. Allversiondeclarations
remain1.4.0; nextconsolidated1.4.1, no bump/tag/release. Parent e5950c1 fullyverified.
Runtime339/dependencies/tests/extensionimplementation unchanged; parentfull3847/41,
actualdefaultCodex208calls/11PNGs and wheel/Docker proof explicitly reused, no new
full/modelrun claimed. Localproof sameprefix-local-proof.json.
All11historicaltrace dirs restoredexactly; owned npmdeps/cache/out removed.
Original dirtydetached checkout untouched; goalACTIVE; no subagents.

## ODS rendition guidance — locally verified; ready to publish

Previous goal turn was PROGRESS: e5950c1 nativeODS renditions implemented, tested,
pushed and ALL10CI/3Pages/6deployedfiles verified. This turn re-read live GitHub
jobs and origin/main; still e5950c12a6bac881d6cbd58e1b0d2fd5ac4c1906 and allsuccess.
Goal remains ACTIVE; full all-format scope unchanged. No subagents.

Current13countedfiles+2MEM synchronize5Agent guidance sources and5bundled copies,
plus README/CHANGELOG/native-ods-spec. Discover source_formats separately from
ods_enabled, read complete creation receipts and everyactualpage, compare formula/
cache/results, report clipping, retain exact .xlsx/.ods and historical mappings.
MCP mechanical checks; Agent full semantic/visual/result review and corrections.
Onlydocumentation/assistantassets changed; runtime339files, tests, dependencies,
extensionimplementation and buildconfig unchanged. No new model/full-suite run is
claimed. Parent3847pass/41skips, defaultCodex208successfulcalls/11PNGs, actualCalc7.3/
24.2, installedwheel actualCalc and Docker capturedCalc replay remain evidence for
that identical runtime. Allruntimefiles match the captured source manifest.

Currentfocused55passed/0.80s; VSIX199tests/64entries/install-updatepass. All5actual
packagedguides are byte-identical to sources. Localactivation skipped; exact-head
remoteactivation required afterpush. Releaseharness/docs/sync/metadata/diffchecks
pass; GitHubdescription and20topics reread and stillaccurate, no mutation needed.
Localproof /run/user/1000/asset-aware-ods-rendition-guides-local-proof.json.
InternalVSIX /run/user/1000/asset-aware-ods-rendition-guides-local-1.4.0.vsix.

All11historicalmodeltrace dirs restoredordinary with exacthash/size/mtime. Owned
npmdeps/cache/out removed. Currentpublic1.4.0,nextconsolidated1.4.1; no bump/tag/
release. Work ONLY agent-assets main; original dirtydetached checkout untouched.
Next exact13+2MEMstage, userauthor u9401066<u9401066@gap.kmu.edu.tw>, directmain
commit/push, then ALLexact-head10CI/3Pages/6deployedbytechecks before newdevelopment.
Broader ODS table/row/column lifecycle and ODT/ODP/HTML/EPUB/email/LaTeX/etc remain.

## ODS renditions — publication COMPLETE, e5950c1 verified

Head e5950c12a6bac881d6cbd58e1b0d2fd5ac4c1906 is on main/origin with user author
u9401066<u9401066@gap.kmu.edu.tw>. ALL10CI jobs35614035534 and ALL3Pages jobs
35614034482 passed. Six deployedfiles match exactcommitbytes: index.html,site.js,
site-content.js,site-content/native-file-assets.md,native-ods-spec.md,
wiki/Native-File-Assets.md. Publicationrunner62547 terminal0; no livewatch remains.
Proof /run/user/1000/asset-aware-ods-render-publication-proof.json is published_verified.
Localproof /run/user/1000/asset-aware-ods-render-local-proof.json now records both.

Current segment24countedfiles+2MEM implements nativeODS PDF renditions, native
resource/OpenFormula/graphicchecks and source-preserving Wiki receipts. Drawing
namespace fixed with real-URI/no-ID guards; historical byte/full-receiptgoldens
remain exact. Runtime339files, all7versions1.4.0. Latestpublicrelease re-readv1.4.0;
next consolidated1.4.1, no per-feature bump/tag/release. Broader goal ACTIVE.

Localfull3847passed/41environment-skips/635.25s plus9audit focusedtests(4newafter
fullcollection). Calc7.3:39unit+5integrationpassed; Calc24.2:5integrationpassed.
Independent fullpagepixels, styled999/recalculated3, unstyledcachepolicy, hidden/
blank scopes, charts/raster, SDK2 restart and exactWiki/source retention verified.
DefaultCodexrun01:208successfulcalls,11actualPNGs,234.98s,1recoveredargumenterror.
Original auditor failure retained; exact authoredformula spelling corrected and
independent nativeXML/read tamper checks strengthened, final auditpassed. No runtime
change after capturedmodel manifest. Installedwheel339+actualCalc, Docker339+
capturedCalc replay; bothdoctor/30tools/SDK2stdio pass. Docker does not claim actual
Calc installation. VSIX199tests/64entries/install-updatepass, remoteactivationpass.

All11historical modeltrace dirs restored ordinary/hash-size-mtime exact. Owned
Dockerimage/builder,wheelenv/cache/data,npmdeps/cache/out, completedpytest-32temp and
thisturn'sprivateCalc24.2runtime cleaned. Logs, sourceorigin proof, actualCalc/model/
artifact artifacts and internalVSIX retained in/run. Preexisting7.3runtime and warm
workerbytecode retained. Original dirtydetached checkout untouched. No subagents.

NEXT coherent segment: update5Agent guidance sources and5bundledcopies for native
ODS renditions/source_formats, complete receipts/actualpage review, cache/clipping
boundaries; existing instructions still describe XLSX-only renditions. Stay<=30
countedfiles excluding2MEM, sync/package/verify; currentruntime/model/fullproof can
be reused only if exactruntime unchanged. Then continue ODS lifecycle and remaining
ODT/ODP/HTML/EPUB/email/LaTeX/all-format scope. Only post-publicationMEM status changes
remain dirty. Do not mark the broad goal complete or blocked.

## ODS renditions — e5950c1 pushed; exact-head publication checks pending

Head e5950c12a6bac881d6cbd58e1b0d2fd5ac4c1906 committed/pushed directmain as
u9401066<u9401066@gap.kmu.edu.tw>,24countedfiles+2MEM. No version/tag/release:
public1.4.0,next consolidated1.4.1. Baseline2d7cdfd remains fully verified.

LIVE publication runner62547; poll this handle, do not duplicate it.
CI35614035534 requires ALL10jobs; Pages35614034482 requires ALL3jobs plus6deployed
files byte-exact. Script /run/user/1000/asset-aware-ods-render-verify-publication.py;
log /run/user/1000/asset-aware-ods-render-publication-watch.log;
proof /run/user/1000/asset-aware-ods-render-publication-proof.json.
Do not start new development until exact-head verification completes.

Localproof /run/user/1000/asset-aware-ods-render-local-proof.json records
3847passed/41skips/635.25s +9focused auditcases (4added after fullcollection),
Calc7.3unit39+integration5/Calc24.2integration5, defaultCodex208successfulcalls/
11PNGs/1recoveredargumenterror, installedwheel339+actualCalc and Docker339+
capturedCalc replay, bothdoctor/30tools/SDK2stdio, VSIX199/64entries/install-update.
All11historical trace dirs restored exactly; ownedruntime/builddeps/cache/image/
builder cleaned; all logs/proofs retained. Localactivation skipped, remote required.
Original checkout untouched. Goal ACTIVE. After verification, update5Agent sources+
5bundled copies in a separate <=30file segment; then broader format/lifecycle work.

## ODS renditions — local gates complete; ready for direct-main publication

Current segment24countedfiles+2MEM adds native ODS PDF renditions, ODF resource/
formula/graphic checks, native-source Wiki receipts, real Calc/SDK2 restart and
model/artifact evidence. Official drawing namespace bug fixed with independent
no-ID repetition tests; historical original-input byte/full-receipt goldens retained.
Runtime339files unchanged since model/full-suite snapshot. Public/current1.4.0;
next consolidated1.4.1. No bump/tag/release. Goal ACTIVE, no subagents.

RealCalc7.3:39unit+5integration=44pass; Calc24.2:5integrationpass. Exact same-version
control pixels cover all4mode/policy combinations, native chart/raster, hidden/blank
sheets, cache999 vs result3 and the unstyled forced-recalc case. SDK2 processrestart
retains receipts, actualPNGs and byte-exactWiki/nativeODS. Agent owns semantics,
formula result review and visual clipping; MCP does not assert fidelity.

DefaultCodex actualrun /run/user/1000/asset-aware-codex-ods-rendition-01:
208successful calls,11actualPNGs,234.98s;1recovered text_limit12000 error retained.
Audit passes with exact source/formula/style/native read records, source mtime,
PDFpixels, oldrefs and Wikis. Initial auditor expected a namespace prefix that the
existing typed editor intentionally does not author; corrected to exact =2+3.
Original failedaudit retained, strengthened nativeXML comparisons and4negative
cases pass (9focused total). Model CLI0; wrapperinitial1 reflected auditonly.
Current339runtimefiles/uv.lock still match captured model fingerprints.

Full3847passed/41environment-skips/635.25s, runner72939 terminal0. The4newaudit
cases were added after collection and verified separately. Ruff/format804,
mypy339, banditmedium, releaseharness, docs generation, bundledsync, allartifact
metadata/contents and diffchecks pass. Sevenversiondeclarations all1.4.0.
VSIX199tests/64entries/install-updatepass; localactivation skipped, exact-head
remote activation required. InternalVSIX /run/user/1000/asset-aware-ods-render-local-1.4.0.vsix.

Python3.13installedwheel matches all339files; actualCalc chartPDF pixels and complete
receipt/source/Wiki/restart match. DockerPython3.12 matches all339files and replays
captured actualCalc output through resourcechecks/service/Wiki; it does NOT install
or claim realCalc inside Docker. Bothdoctor/30tools/SDK2stdio pass. Allproof:
/run/user/1000/asset-aware-ods-render-local-proof.json
All logs/artifacts retained with asset-aware-ods-render prefixes.

All11temporarily staged historicalmodeltrace directories restored ordinary with
exacthash/size/mtime. OwnedDockerimage56d4adec75af/buildera9039c5db278 removed;
wheelenv/cache/data and npmdeps/cache/out removed. Completedfulltest tmp pytest-32
removed after successful run; retained actualCalc/model/artifact proofs remain.
Newprivate24.2runtime removed after successfultests; official42deb/archivesource
proof remains. Keep preexisting7.3runtime and warmedworkerbytecode.

NEXT: exact24+2MEMstage, userauthor u9401066<u9401066@gap.kmu.edu.tw>, directmain
commit/push. Verify ALLexact-headCI10+Pages3 and6deployedbytes before any further
changes. Assistantguidance5sources+5bundles needs the next coherent follow-up
segment to stay within30files. Broader ODS lifecycle/ODT/ODP/HTML/EPUB/email/LaTeX/
allformat work remains. Original dirtydetached checkout untouched.

## ODS renditions — runtime implemented; validation in progress

Base2d7cdfd remains fully published/verified. Current runtime339files is frozen
for full suite72939 and completed actual default-model evaluation. No commit/push
or version change: public1.4.0,next consolidated1.4.1. Goal ACTIVE; no subagents.
Work only agent-assets checkout; original dirty detached checkout untouched.

Real Calc7.3:44passed(new39unit+5integration), 24.2:5integrationpassed.
SDK2 four policy/mode variants, restart/receipts/PNGs/Wiki/source preservation
and independent full-page chart/raster pixels pass. Explicit style is necessary
for cached999 vs recalculated3; unstyled formulas independently render3 even
with prefer_cache because Calc resolves number formats. Hidden overflow is clipped;
full pixel equality to direct Calc verifies it, Agent reports the limitation.
Logs /run/user/1000/asset-aware-ods-render-calc73-03.log and -calc242-01.log.
Namespace drawing fix and historical unchanged byte/receipt goldens remain.

Actual defaultCodex run /run/user/1000/asset-aware-codex-ods-rendition-01:
208successful calls,11actualPNGs,234.98s,1recovered text_limit12000 error. Initial
audit incorrectly expected of:=2+3 while the existing editor writes requested
=2+3 verbatim; initial failure retained as audit-initial-formula-spelling-failure.json.
Corrected exact spelling + strengthened independent XML/read checks pass on the
same retained run. New4negative audit tests+existing5pass. No new model run needed.
Runtime/lock fingerprint needs final verification. All model session83552 terminal1
was caused only by initial auditor; CLI itself0. Final audit proof is separate.

Full suite LIVE session72939, log /run/user/1000/asset-aware-ods-render-full-01.log;
uses localWriter and privateCalc7.3, normal warmed bytecode, TMPDIR=/dev/shm.
Focused prior231+101tests; mypy339 and changed lint pass. Full suite collected
before4newauditcases; run those separately (9passed) and do not claim otherwise.
New packaged rendition replay tests/native_ods_rendition_artifact_smoke.py passes
locally with captured actual chartPDF+receipt; first failure was test keywordpdf
instead ofpdfs and retained. Installedwheel actualCalc and Docker replay pending.
Source manifest /run/user/1000/asset-aware-ods-render-source-manifest.json.

Docs README/CHANGELOG/native-ods-spec/wiki/site regenerated; CI3.10unit gate wired.
Assistant sources/bundles still need separate coherent follow-up (count cap30).
Current count about24+2MEM; use actualgit before staging. Need wheel/Docker/VSIX,
full gates, localproof, exactstage user-author directmaincommit/push and ALLexact-head
CI10+Pages3+6deployed files before further development. Do not mark goal complete.

Private24.2runtime this turn /dev/shm/asset-aware-ods-render-calc242-runtime-01
verified official archive+42deb hashes, alltests complete; safe to remove only this
owned runtime to free space for packaging. Origin proof and all test artifacts in/run
must remain. Historical11traces currently restored; if staging use NEW script/manifest
asset-aware-ods-render-space, verify hash-size-mtime on stage/restore. No user cleanup.

## ODS renditions — implementation in progress, not committed

Base2d7cdfd47ea9831184cf7001ff397fa188f73fdf fully published/verified. Previous
goalturn was PROGRESS (harness commit+allCI/deployed checks). Current segment
adds ODS-specific resource/OpenFormula checks and LibreOfficeODSRenderer, extends
create_workbook_rendition to configured XLSX/ODS ports, advertises source_formats,
and retains .ods attachments in rendition Wikis. Source remains native/unchanged.
No version change:public1.4.0,next1.4.1. Broad all-format goal ACTIVE.

Important discovered/fixed bug: NS[draw] was incorrectly xmlns:draw:1.0 instead
of official xmlns:drawing:1.0. Fix native_odf_package; real namespace/no-ID drawing
regressions now protect repeated row/cell splits and render resource checks.
Historical performance fixture explicitly retains its old unused drawing declaration;
all old byte/full-receipt goldens still pass. No hash assertions were loosened.

Verified:231existingXLSX/schema tests; latest101ODS/kernel/performance/renderer/
rendition tests; Ruff and mypy339 pass. Logs /run/user/1000/asset-aware-ods-render-*.
No full suite, artifacts, actual Codex, docs/harness sync or commit/push yet.
Sources9 + tests3 currently (count actual git state before staging; <=30+2MEM).

Current actual Calc7.3 SDK2 test FAILED: prefer_cache requested but cached999
renders3; investigate rather than accept arbitrary values. Initial standalone
stdin renderer probe failed only because multiprocessing spawn needs a real
__main__ file. Later real-file probe tested constant and dependent formulas,
Calc/custom generator: both policies render3. Record:
/run/user/1000/asset-aware-ods-render-policy-probe-01.log and artifactdirectory.
Actual integrationfailure:/run/user/1000/asset-aware-ods-render-calc73-01.log.
First unitfailure was incorrect test protected-root path; corrected, latestpasses.
All completed test/probe sessions are terminal; no model run has started.

Old privateCalc24.2 runtime had been cleaned; missing-path probe failure retained.
Preparing a NEW private24.2.7.2 runtime from previously verified official archive:
/run/user/1000/asset-aware-ods-render-install-calc242.py (running; locate current
session from latest tool result); log sameprefix .log. Archive in/run, extracted
packages in/dev/shm/asset-aware-ods-render-calc242-runtime-01. Verifies whole archive
and all42package hashes against prior origin proof; no apt install/postinstall.
Read/resolve current live handle; do not duplicate on an observation timeout.

Need finish policy/control investigation, actual Calc cases incl images/charts,
SDK2 restart/receipts/Wiki, default-model Codex image review, doc/harness updates,
CI gate wiring/packaged replay/full checks. Existing new test is appended to
tests/integration/test_native_ods_calc.py so its configured CI path will collect it.
Original checkout untouched; no subagents. Rootrecent266MiB;/dev/shm~1GiBfree;
use atomicMEMwrites, retained runtimebytecode, TMPDIR=/dev/shm.

## ODS Agent guidance — publication COMPLETE, 2d7cdfd verified

Head2d7cdfd47ea9831184cf7001ff397fa188f73fdf is on main/origin with user author.
ALL10CI jobs35604988799 and ALL3Pages jobs35604987852 passed. Six deployedfiles
match exact commit bytes:index.html,site.js,site-content.js,
site-content/native-file-assets.md,native-ods-spec.md,wiki/Native-File-Assets.md.
Runner36701 terminalexit0; no live watch remains. One transient Pages connection
retry succeeded; no CI failures. Proof statuspublished_verified:
/run/user/1000/asset-aware-ods-harness-publication-proof.json

Current segment14countedfiles+2MEM synchronizes5Agent sources/5bundledcopies,
corrects stale ODS status, and scopes optionalNode skipping to the ODS CSL test.
Focused44passed; withoutNode14passed/1skip; VSIX199tests/64entries/install-update
and remote Linux activation pass. Actual5packaged guidance files equal sources.
Runtime337files and dependency/build definitions unchanged; parentfull3813/33,
Codex04(223successful calls), wheel/Docker evidence remains applicable to that
identical runtime. No new full-suite/model run is claimed for the docs segment.
Parentfce0b63 also fully published/verified. Current localproof:
/run/user/1000/asset-aware-ods-harness-local-proof.json

All11staged historicalmodeltrace dirs restored ordinary/hash-size-mtime exact.
Owned npm dependencies/cache/out removed; internalVSIX retained in/run.
Root~37MiB; retain runtimebytecode, avoid unrelated cleanup, use atomicMEMwrites.
Githubdescription names XLSX/ODS;20topics verified. Latestpublicreleasev1.4.0 and
all7version declarations remain1.4.0; nextconsolidated1.4.1. No bump/tag/release.
Original dirtydetached checkout untouched; no subagents. Only post-publication
MEM status updates remain dirty for the next coherent <=30file segment.

NEXT: native ODS recalculated renditions and table/row/column lifecycle; retain
all-format scope including ODT/ODP/HTML/EPUB/email/LaTeX/etc. Broad goal ACTIVE,
not complete/blocked. Read-only renderer preparation is saved outside the repo:
/run/user/1000/asset-aware-ods-rendition-research.md. Existing XLSX renderer/source
checks are OOXML-specific; ODFRecalcMode and native ODS resource/dependency checks
need separate handling. Upstream LibreOffice/OASIS references recorded; no ODS
renderer implementation or new render test is claimed.

## ODS Agent guidance — pushed 2d7cdfd; exact-head checks pending

Head2d7cdfd47ea9831184cf7001ff397fa188f73fdf is committed/pushed directmain as
u9401066<u9401066@gap.kmu.edu.tw>;14countedfiles+2MEM. Current CI35604988799 and
Pages35604987852 need all10/all3jobs plus6deployed exact-byte checks.
Verification runner36701 is LIVE; poll it, do not duplicate.
Script:/run/user/1000/asset-aware-ods-harness-verify-publication.py
Log:/run/user/1000/asset-aware-ods-harness-publication-watch.log
Proof:/run/user/1000/asset-aware-ods-harness-publication-proof.json
No further code until this exact head verifies; fix genuine failures first.

Parentfce0b63 is fully verified. Current runtime337sourcefiles unchanged; local
44focused +14pass/1skip withoutNode +199VSIXtests/64entries/install-update passed.
Five actual packaged guidance files are byte-exact. Full3813/33, Codex04, installed
wheel/Docker proof remains from identical parent runtime, not newly rerun.
All11historical modeltrace dirs are restored ordinary with hashes/sizes/mtimes
exact; task npm dependencies/out removed. Local VSIXproof in/run; root~34MiB.
Original dirty checkout untouched. Public/current1.4.0,next consolidated1.4.1;
no bump/tag/release. Broad goal ACTIVE; no subagents. After verification, ODS
lifecycle/renditions and remaining native formats still require implementation.

## ODS Agent guidance — verified locally; ready for direct-main commit

Add native ODS complete reads with both pagination layers, exact logical refs,
original-revision cell edits, inline no-op receipts and MCP/Agent review boundaries
to5assistant sources and5bundled copies. README/spec/Unreleased status corrected.
Only optional-Node ODS CSL test guard changes Python test code; runtime337files,
all src/dependency/build definitions and extension TypeScript are unchanged.

Focused44passed/3.29s; no-Node14passed/1skip/2.20s; VSIX199tests/64entries and
install/update passed. All5actual packaged guidance files match source bytes.
Local activation skipped; exact-head remote Linux activation remains required.
Ruff/format/releaseharness/docs/sync/diff checks pass. Parent fce0b63 full3813/33,
Codex04, wheel/Docker evidence remains valid for identical runtime hashes; no
new full-suite/model run is claimed for this documentation/test-guard segment.
Proof:/run/user/1000/asset-aware-ods-harness-local-proof.json; internal VSIX
/run/user/1000/asset-aware-ods-harness-local-1.4.0.vsix is not a release.

Initial npm logging hit ENOSPC before asset synchronization; failure log retained.
All11 temporarily staged prior modeltrace directories are now restored ordinary
with exact file hashes/sizes/mtimes; task-owned npm dependencies/cache/out removed.
Root~34MiB, use atomic MEMwrites. Github description now names XLSX/ODS;20topics
verified with spreadsheets replacing xlsx. Metadata proof retained.

14countedfiles+2MEM, user-author directmain commit/push next; require ALL exact-head
CI/Pages and deployed bytes before development. Public1.4.0,next consolidated1.4.1,
no bump/tag/release. Broad all-format goal ACTIVE; ODS lifecycle/recalculated
renditions and remaining formats still outstanding. Original checkout untouched.

## ODS MCP/evidence/Wiki — publication verified; Agent guidance follow-up

Head fce0b63b1f70204fbdf4a3cd14f4131b477a5672 is on main with user author.
Fresh REST API confirms all10CI jobs35602250351 and all3Pages jobs35602247118
success; six deployed files match exact commit bytes. Publication proof:
/run/user/1000/asset-aware-ods-mcp-publication-proof.json,published_verified.
The watch45026 terminated1 on network-unreachable, not a CI/test failure;
independent completed-run/job metadata was saved. No watcher remains live.

Next bounded segment: synchronize ODS complete-read/reference/review guidance in
AGENTS/Codex/Cline/Copilot + bundled VSIX copies; correct stale pending-MCP text;
make only the Node-dependent ODS-CSL test skip when optional Node is absent.
Runtime337source files remain frozen with full3813passed/33skipped, finalCodex04
223successful calls, installedwheel/Docker and cross-platformCI evidence intact.
No runtime behavior or version change. All seven declarations are1.4.0; next
consolidated1.4.1. No tags/releases. Broader all-format goal remains ACTIVE;
ODS lifecycle/recalculated renditions and ODT/ODP/other formats remain.
Original dirty detached checkout untouched; no subagents; exact staging <=30files
plus2MEM. Use atomic MEMwrites and temporary task-owned storage for dependencies.

## ODS MCP/evidence/Wiki — pushed fce0b63; exact-head CI pending

Head fce0b63b1f70204fbdf4a3cd14f4131b477a5672 is committed/pushed directmain
as u9401066<u9401066@gap.kmu.edu.tw>,30countedfiles+2MEM.
CI35602250351 watcher session45026 is RUNNING; do not restart a livewatch.
Pages35602247118 completed success; verify all3jobs and6deployedfiles with proof
/run/user/1000/asset-aware-ods-mcp-publication-proof.json. CI needs ALL10jobs.
No new development until exact-head checks are green; fix actual failures first.

Final local full3813passed/33skipped/764.61s; discovery233pass; cold-cache PDF
annotation follow-up2pass at same300slimit, and bothcases pass in finalfullsuite.
DefaultCodex final04:223calls/0errors/197.33s,27fullODSreads,9cellrecords,3source+
2independent revisions,3Wikis; no visual/calculation claim. Source337manifestSHA
b2b4d2b93ea634211f618fa54b02c0332d1a35ac06a26dfaa9a8c95b55385820.
Final wheel3.13/Docker3.12 exactsource/output/receipt/restart/doctor/30tools/SDK2
pass. VSIX199tests/64entries/install-update pass; remote Linux activation pendingCI.
All11prior modeltraces restored ordinary/hash+mtime exact; own install artifacts
removed. Runtimebytecode retained for worker startup. Root~37MiB; atomicMEMwrites.
Public1.4.0,next consolidated1.4.1; no bump/tag/release.

After publication: bundledODSAgent guidance in separate segment; also align new
ODS-CSL optional-node test guard with existing optionalCSLtests if needed.
Broader ODS lifecycle/renditions, ODT/ODP/etc goal stays ACTIVE. No subagents.
Original dirty detached checkout untouched.


## ODS MCP/evidence/Wiki — final local gates COMPLETE; ready for commit/push

Final source337files frozen at manifestSHA
b2b4d2b93ea634211f618fa54b02c0332d1a35ac06a26dfaa9a8c95b55385820.
Full final suite35989 terminalexit0:3813passed/33skipped/764.61s. BOTH PDFannotation
surfaces pass. Initial cold-cache full attempt81405 had1timeout/821passed/33skipped
and was interrupted after3discovery fixes; logs retained. Cache-primed annotation
follow-up11223 passed2cases/274.94s at unchanged300slimit;233discovery tests pass.
No verification assertions or timeout limits were loosened.

Final-source defaultCodex run04 passed:223successful calls,zeroerrors,197.33s,
27complete ODS reads,9cell records,3source revisions,2independent-book revisions,
3Wikis. Actual runtime/uv.lock hashes match. Visual/calculation review not_checked.
Prior successful03 and guarded failure02 plus wrapper failure01 are all retained.
Final wheel3.13/Docker3.12 exact337sourcefiles, exact independently rendered Calc
output/full receipts, source protection, restart/Wiki identity, doctor/30tools/SDK2
all pass. Final ownedimage5981977790f4/builder893fc0ceafda removed after checks;
wheel env/cache removed. VSIX199tests/64entries/install-update pass; activation
requires exact-headremoteCI. Ruff799/mypy337/security/harness/docs/sync-assets pass.

All11prior modeltrace dirs RESTORED ordinary with exact hashes/mtimes. Finalspace
manifest marks all restored; runtime bytecode is retained to avoid cold worker
timeouts. Root~37MiB; atomic MEMwrites only, TMPDIR=/dev/shm, no global cleanup.
Source originaldirtydetached checkout remains untouched. No subagents.

Machineproof:/run/user/1000/asset-aware-ods-mcp-local-proof.json. Exactstageplan
/run/user/1000/asset-aware-ods-mcp-commit-paths.json has30countedfiles+2MEM.
Next:user-author u9401066<u9401066@gap.kmu.edu.tw>,directmain commit/push,thenALL
exact-headCI/Pages and deployed bytes. No newcode before publication verification.
Public1.4.0,next consolidated1.4.1; no version/tag/release increment.
After publication: synchronize bundled ODS Agent guidance as a separate segment;
ODS lifecycle/renditions and ODT/ODP/remainingformats still part of ACTIVE goal.
Do not mark goal complete or blocked.


## ODS MCP/evidence/Wiki — implementation complete; full-suite verification pending

Current uncommitted segment wires create_ods/read_ods/read_ods_cell/update_ods with
full original logical cell refs and revision CAS, typed edits/blank clears, complete
hash-paged receipts, selections/derivations/CSL/custom locators and immutable ODS
Wikis. Compressed range refs identify anchors only; derivation endpoints retain
exact non-anchor/implicit cells. Complete receipts resolve external blob storage;
receipt hash participates in Wiki identity. No-op reports are complete inline.
Version remains public1.4.0,next consolidated1.4.1; no tag/release/bump.

Actual default-model Codex run03 passed independent audit:212successful MCP calls,
zero errors,25complete ODS reads,8cell records,3source revisions,2independent-book
revisions,3Wikis,186.77s. Visual review/recalculation are explicitly not_checked.
/run/user/1000/asset-aware-codex-ods-03. Retain run02 failure:repeated rows containing
formulas correctly blocked2edits; model reported unchanged source. Success fixture
uses repeated literal rows+separate formula row; no guard relaxation. Run01 wrapper
failed on absent optionaldefusedxml before model invocation; log retained.

Focusedkernel/service/performance60passed;241related/SDK2two-process tests passed.
Wheel3.13/Docker3.12 exact337source files, independently-rendered Calc output/full
receipt, restart/Wiki bytes, source mtime, oldrefs/create and doctor/30tools/SDK2 pass.
VSIX199tests/64entries/install-update pass; localactivation skipped, remoteCI required.
Ruff/mypy337/security/harness/docs checks pass. Source frozen at manifest SHA
2c5ebaba7256b8ecccb1c4b648997b47794b675f2683a4786f5111dfae9a65d1.

Full suite session81405 is STILL RUNNING; first PDF annotation case timed out300s
with bytecode caches removed/disabled. Runtime imports were primed within this
worktree; follow-up session11223 tests BOTH annotation tool surfaces under same
300slimit. Do not call it fixed until actual results. Logs/proof use prefix
/run/user/1000/asset-aware-ods-mcp-. Full source unchanged throughout gates.
All11temporarily staged prior model runs are RESTORED ordinary dirs with exact
hashes/mtimes; own Docker image/builder/wheel env/cache/node_modules/out removed.
Cache priming generated .pyc in this worktree only; check space before MEMwrites.
Use atomic MemoryBank writes; root~100MiB before priming. Originaldirtydetached
checkout untouched. No subagents. Count29files+2MEM currently; exactstaging/user
author/directmain only after verification, then ALL exact-headCI/Pages+deployedbytes.
Bundled ODS Agent guidance still needs a separate coherent follow-up segment.
Broader all-format goal remains ACTIVE; ODS lifecycle/renditions and ODT/ODP/etc
remain. Do not mark complete or blocked.


## ODS performance — publication COMPLETE; all exact-head checks green

Headfcd107bbbb88f69007c8c13e3e6987d54f7e01bb is published on main as user author.
CI35595051371 passed ALL10jobs; Pages35595050125 passed ALL3jobs. Six deployed
files equal exact commit bytes:index.html,site.js,site-content.js,
site-content/native-file-assets.md,native-ods-spec.md,native-operation-results-spec.md.
Final proof /run/user/1000/asset-aware-ods-performance-publication-proof.json
statuspublished_verified. CI watcher58722 terminalexit0; do not restart it.

Full3789passed/33skipped/749.77s; focused60; Calc7.3/odfdo3; wheel3.13/Docker3.12
source335files exact and large output/full-receipt goldens match published5093031.
Local5,000formula19.536s→0.336s; wheel0.382s,Docker0.407s. VSIX199tests/64entries,
install/update and now remote Linux activation all pass. Source manifest SHA
7c3704484d9befc0c43c839a9456a2a0c4d73ce5493c5606875feb422e23b2f8 unchanged.
Both storage5093031 and performancefcd107b segments are fully verified/published.

All12actual-model trace directories are ordinary/restored with hashes/mtimes exact.
Own Docker/wheel/node_modules/.pyc/dist/out/pytest-cache removed after checks.
Root~26MiB; avoid cache regeneration:PYTHONDONTWRITEBYTECODE=1 uv run --no-sync
python -B. Use atomic MemoryBank writes. The earlier374-character historical tail
truncation was fully repaired before commit; both MEM diffs had zero deletions.

NEXT: ODS MCP/reference/evidence/citation/Wiki integration. Cell locators must bind
part/tableindex+name/row/column; distinguish physical repeated-range listings from
logical cell refs. Canonical ODS citation formatting is still absent. Full reads
and Wiki must retain complete external operation results through the repository.
Stage coherent segments<=30countedfiles, update both MEM, user-author directmain
commits/push with exact-headCI/Pages. Actual default-model Codex ODS evaluation
remains required after public MCP wiring; no ODS model run has yet been claimed.
Broader all-format goal remains ACTIVE; do not mark complete or blocked.
Public/current1.4.0,next consolidated1.4.1; no per-feature bumps/tags/releases.
Original dirty detached checkout remains untouched. No subagents.

## ODS performance — pushed fcd107b; exact-head CI/Pages pending

Headfcd107bbbb88f69007c8c13e3e6987d54f7e01bb committed/pushed directmain as
u9401066<u9401066@gap.kmu.edu.tw>;13countedfiles plus2MEM. CI35595051371 and
Pages35595050125 started. Watch logs:
/run/user/1000/asset-aware-ods-performance-{ci,pages}-watch.log. Publication proof
/run/user/1000/asset-aware-ods-performance-publication-proof.json is pending.
Require all10CIjobs,3Pagesjobs and deployed index/site.js/site-content.js,
site-content/native-file-assets.md,native-ods-spec.md,native-operation-results-spec.md
exact commit bytes before further work. Fix any actual CI failure first.

Local full3789passed/33skipped/749.77s; focused60,actualCalc7.3/odfdo3; exact335
sourcefiles in wheel/Docker; 5,000formulas0.336s local/0.382s wheel/0.407s Docker
versus19.536s baseline. Complete output and12,387,293-byte canonical receipt match
published5093031 exactly. VSIX199tests/64entries/install-update pass. Source SHA
7c3704484d9befc0c43c839a9456a2a0c4d73ce5493c5606875feb422e23b2f8 frozen.
No ODS model evaluation yet; MCP/evidence/citations/Wiki still not exposed.

ALL12actual-model traces are RESTORED ordinary dirs with exact hashes/mtimes. Own
Docker/wheel/node_modules and generated .pyc/dist/out/pytest-cache removed after
validation. Root is tight(~26MiB): use PYTHONDONTWRITEBYTECODE=1 and uv run --no-sync
python -B. A MemoryBank write hit ENOSPC and truncated374characters from historical
activeContext tail; fully recovered from verified5093031 tail using atomic staging.
Both MEM diffs had ZERO deletions before commit. Preserve this history, avoid
unsafe in-place long writes. Source and complete proof files were unaffected.

Previous5093031publication is complete (all10CI/all3Pages/sixexactfiles). This new
head needs its own verification. Public1.4.0,next consolidated1.4.1,no tags/releases.
Overall all-format goal active. Original detached checkout untouched.

## ODS performance — local gates COMPLETE; ready for user-author commit/push

Full session4756 completed exit0:3789passed/33skipped/749.77s, with existing
Writer/CJK/Calc/odfdo/publicPDF fixtures enabled. Log
/run/user/1000/asset-aware-ods-performance-full.log. Focused60pass,Calc/odfdo3pass.
Source335files remain exact manifest7c3704484d9befc0c43c839a9456a2a0c4d73ce5493c5606875feb422e23b2f8.
Wheel3.13 and Docker3.12 pass exact5,000-formula source/output/full-receipt goldens,
exact Calc fixture receipts, doctor,30tools and SDK2stdio. Timing0.382s/0.407s
versus oldlocal19.536s; localoptimized0.336s. VSIX199tests/64contententries and
install/update pass. Ruff792/mypy335/security/harness/artifact/docs gates pass.

ALL12staged model evaluation directories restored as ordinary directories with
exact hashes/mtimes; manifests performance-build-space.json and performance-space.json
now mark allrestoredtrue. Generated .pyc caches in ONLY this worktree src/tests/
.venv were removed after tests to recover space; runtime sources untouched. Own
Docker/wheel/node_modules removed after checks. Do not remove source/packages or
actual traces. Use PYTHONDONTWRITEBYTECODE=1 while space is tight.

Machine proof /run/user/1000/asset-aware-ods-performance-local-proof.json. Exactly
13countedfiles plus2MEM in performance-commit-paths.json. Source frozen; do not
repeat full tests without new changes/failures. Next exact user-author main commit
and push, then ALL exact-headCI/Pages and deployed bytes. No version/tag/release
change: public1.4.0,next1.4.1. Previous5093031publication complete.

After publication, proceed with ODS MCP/evidence/citations/Wiki integration;
there has still been no actual Codex ODS evaluation because MCP is not exposed.
Broad all-format goal remains active. Original dirty detached checkout untouched.

## ODS performance — artifacts green; full suite4756 still running

Source335files frozen at manifest
/run/user/1000/asset-aware-ods-performance-source-manifest.json SHA
7c3704484d9befc0c43c839a9456a2a0c4d73ce5493c5606875feb422e23b2f8.
Focused60passed0.38s; actualCalc7.3/odfdo3passed5.48s. Ruff792files/mypy335,
Bandit medium gate/zizmor,harness and artifact audits pass. Wheel3.13 measured
0.381908s and Docker3.12 measured0.406752s for5,000formulas, matching published
5093031 output/full-result SHAs exactly and preserving source/history/restart.
Both also replay exact Calc fixture bytes/full receipts and pass doctor,30tools,
SDK2stdio. VSIX199tests,64contententries,install/update pass; remoteactivation
still required after push. Docs/readme/changelog/architecture updated and synced.

Full pytest4756 includes existing private CJK/Writer/Calc/odfdo/publicPDF fixtures;
log /run/user/1000/asset-aware-ods-performance-full.log. Do not stop/restart without
actual failure or source change. Local proof
/run/user/1000/asset-aware-ods-performance-local-proof.json is full_pending.
No new Codex model run claimed: ODS still has no public MCP operations. Previous
storage Codex proof belongs to published5093031, not this new source manifest.

All install/build sessions terminalexit0. Own Docker3484709c872d and builder
3fa3df12b6cd removed; own wheel env/cache/data and node_modules removed.
Current13countedfiles+2MEM; tests/unit/test_native_ods_performance.py untracked.
Root free~530MiB BEFORE trace restoration. ALL12trace dirs still staged: earlier
11 via /run/user/1000/asset-aware-ods-performance-build-space.json in
/dev/shm/asset-aware-ods-performance-build-staging, and newest storageCodex run via
/run/user/1000/asset-aware-ods-performance-space.json in
/run/user/1000/asset-aware-ods-performance-trace-staging. Originalpaths are symlinks;
all bytes/mtimes verified before staging. Need restore ALL as ordinary dirs.

Restoring needs~541MiB plus margin. Once full tests finish, remove ONLY generated
.pyc caches from this alternate worktree src/tests/.venv (source files/packages
stay): measured src6.4MB/tests9.5MB/ownvenv22MB. This is safe rebuildable test
cache, unlike source or actual-model traces. Verify .venv resolves inside this
worktree first. Avoid writing caches afterward with python -B/PYTHONDONTWRITEBYTECODE.
Then restore12directories with full hash/mtime checks, record proof, finalize
spec/MEM, exact user-author main commit/push and all exact-headCI/Pages.
Public1.4.0,next1.4.1; no tags/releases. Broad goal active, original checkout untouched.

## ODS cache traversal — implemented; focused proof passes, full gates pending

Published storage head50930318c4d1b7ead69e64ef957d839a60f16ce3 is fully verified:
CI35590907090 all10 and Pages35590906633 all3passed,6deployedfiles exact. Final
proof /run/user/1000/asset-aware-native-results-publication-proof.json. Watch35099
terminalexit0. No further waiting/rechecking necessary for that head.

Next ODS performance spec was written first in docs/native-ods-spec.md. New
tests/unit/test_native_ods_performance.py initially failed2cases:200formula rows
walked41,813records,400walked163,613 (log performance-regression-before). Published
5093031 output/complete-receipt golden SHAs were captured before editing runtime.
The reader now exposes a shared cell_record helper; cache invalidation records
visited physical nodes directly; checked output uses one full traversal matching
planned locators/ranges and rejects missing/mismatched targets. Complete receipts,
namespace context, compressed ranges and all existing guards are retained.

Focused60passed0.38s, including exact200/400output/receipt goldens and grouped,
repeated300columns*1000rows with Unicode formula prefixes/rich display.5,000formula
replay now0.335961s versus19.535553s (~58.15x this run), with byte-identical output
and full12,387,293-byte canonical receipt. Source unchanged. Baseline and proof:
/run/user/1000/asset-aware-ods-performance-{baseline,after,goldens}.json. Artifact
smoke now accepts --baseline to verify exact large result/output SHAs in installs.
Mypy335passes; Calc7.3/odfdo focused tests running session32964.

IMPORTANT space: root filled again. The NEW completed storage Codex run is now
staged with exact hashes/mtimes at /run/user/1000/asset-aware-ods-performance-trace-staging;
original /tmp/asset-aware-native-results-codex-delimited-01 is a symlink. Restore
as an ordinary directory before finishing this phase using
/run/user/1000/asset-aware-ods-performance-space.json. The earlier11historical
runs remain ordinary/restored. PrivateCalc7.3,odfdo325 and CJK fixtures retained;
privateCalc24.2 removed with origin proof saved. Node_modules absent.

Need finish docs/readme/changelog/MEMarchitecture, freeze335sourcefiles with new
manifest, full appropriate gates and exact installed artifact replay, then user-
author directmain commit/push and all CI/Pages. <=30countedfiles, both MEM excluded.
Product remains1.4.0,next consolidated1.4.1. ODS MCP/evidence/Wiki and broad formats
remain pending; overall goal active, no subagents, original checkout untouched.

## Native receipt archive — publication COMPLETE, all exact-head checks green

Head50930318c4d1b7ead69e64ef957d839a60f16ce3 is published on main. CI35590907090
passed ALL10jobs, including Python3.10, Linux/macOS/Windows, unit/integration.
Pages35590906633 passed ALL3jobs. Six deployed files equal exact commit bytes:
index.html,site.js,site-content.js,site-content/native-file-assets.md,
site-content/release-testing.md,native-operation-results-spec.md. Final proof:
/run/user/1000/asset-aware-native-results-publication-proof.json status
published_verified. CI watcher35099 is terminal exit0; do not restart it.

Local3775passed/44skipped plus15optionalpassed covering11extra skips; actualCodex
188successfulcalls/4regionPNGs/6CSVrevisions/3derivations audited.335sourcefiles
match wheel/Docker; VSIX199tests/install-update pass. All actual runs retained,
all11staged historical runs restored exactly. No version/tag/release change:
public1.4.0,next consolidated1.4.1. Root detached checkout still untouched.

Next phase: remove quadratic ODS formula-cache traversal while preserving exact
complete receipts, source bytes and compressed ranges. Then continue ODS MCP,
evidence/citations/Wiki and broad format support. Overall goal remains active.

## Native receipt archive — pushed5093031; exact-head remote verification pending

Committed/pushed50930318c4d1b7ead69e64ef957d839a60f16ce3 directmain as user
u9401066<u9401066@gap.kmu.edu.tw>,30countedfiles plus2MEM. Main/origin main equal;
no tag/release/version bump. Exact-head CI35590907090 and Pages35590906633 started.
Watch logs /run/user/1000/asset-aware-native-results-{ci,pages}-watch.log; proof
/run/user/1000/asset-aware-native-results-publication-proof.json currently pending.
Require ALL CI and Pages jobs, then compare deployed index/site.js/site-content.js,
site-content/native-file-assets.md and native-operation-results-spec.md exact bytes.
Fix genuine CI failures before further work. Do not overwrite failed run evidence.

Local complete:3775passed/44skipped plus15optionalpassed covering11extra skips;
actualCodex188calls/audit,source335wheel/Docker,VSIX199tests allpass. Full session
89412 and optional1650 both terminal exit0. Original source manifest unchanged.
All11old traces restored; new actual run retained; generated build environments
removed. Current remaining work after publication is ODS cache traversal speed,
then ODS public operations/evidence/citations/Wiki and broader format coverage.
Goal remains active. Public1.4.0,next consolidated1.4.1; no per-feature bump.

## Native complete result storage — local gates complete; committing/publishing

Full suite session89412 completed exit0:3775passed/44skipped/571.83s. The11extra
skips versus the prior baseline were optional Word/CJK/ODS/real-PDF fixtures;
rerun session1650 enabled them using existing private fixtures:15passed173.83s,
including all11missing cases. Remaining33skip scopes match the prior baseline.
Logs /run/user/1000/asset-aware-native-results-full.log and
/run/user/1000/asset-aware-native-results-optional-gaps.log. Do not repeat full
tests without source changes or new failures. Actual Codex188calls/audit, full
receipts/Wiki restarts, source-matched wheel/Docker and VSIX gates all pass.

Machine proof /run/user/1000/asset-aware-native-results-local-proof.json; source
manifest335files SHA d6df2ae2d7e7b92fac5f66e04092b8bc99a1592a79c5f854b8324ea95c48448c.
Thirty counted files plus2MEM staged exactly from commit-paths.json. All11prior
traces are ordinary restored directories; actual new Codex run retained. Owned
Docker/wheel/node_modules build products removed after validation. No source
changes since frozen manifest. Product1.4.0,next consolidated1.4.1,no tag/release.

Commit and push directmain as u9401066<u9401066@gap.kmu.edu.tw>, then require
ALL exact-head CI/Pages jobs and deployed bytes before continuing. ODS traversal
optimization is next, followed by public operations/evidence/citations/Wiki. Broad
all-format goal remains active; original detached checkout stays untouched.

## Native receipt archive — Agent/artifact gates passed; full suite pending

Read-only follow-up analysis locates the ODS quadratic work: `_invalidate_caches`
already traverses physical row/cell elements, yet calls `book.read_cell` from the
start for each cache; serialized readback repeats `checked.read_cell` per cache.
Next phase should construct identical records from each visited element and its
exact compressed repetition coordinates, then match a single checked physical
traversal to planned locators. Avoid a persistent index over mutable XML unless
invalidation is explicit. Keep same receipts byte-for-byte, namespace context,
repeated ranges and protection guards. No ODS runtime changes made in this segment.

Actual default-model Codex CSV/PDF evaluation completed187.52s,exit0,audit passed:
188successful native calls,4actual region PNGs,6CSV revisions,3derivations,zero
errors. Original run stays /tmp/asset-aware-native-results-codex-delimited-01.
Synthetic fixture scope only; no arbitrary-document review claim. Complete
three-process SDK2 receipt/Wiki migration equality passes. Source335files remain
exact manifest d6df2ae2d7e7b92fac5f66e04092b8bc99a1592a79c5f854b8324ea95c48448c.

Fresh5,000-formula capacity replay passes locally, Python3.13 wheel and Docker3.12:
source4,051bytes; old index18,829,912bytes locally; new index1,320bytes; complete
receipt12,387,603bytes. All5,000before/after caches and source bytes/mtime survive
restart. Docker source path changes metadata length only. ODS traversal still
~19.5s locally/~27.3s container, so performance work remains. Both artifacts pass
console doctor,30tools and SDK2stdio. VSIX199tests,64contententries and install/update
pass; local activation skipped, required remoteCI remains. Ruff791files,mypy335,
harness/artifact audit,docs sync and configured security gates pass. An earlier
unfiltered Bandit log retains23existing low findings; CI medium/high gate is clean.

Owned Docker imageaceba8a4d05b/builder7054b607b1c1 and wheel environments removed.
All11previous traces RESTORED as ordinary directories with exact hashes/mtimes;
manifest /run/user/1000/asset-aware-native-results-space.json marks every restored.
Owned node_modules removed after completed extension checks. A transient root
disk exhaustion affected only a git-status refresh; completed artifact commands
passed. Current space recovered; do not remove unrelated data or original traces.

Full suite session89412/log /run/user/1000/asset-aware-native-results-full.log still
running. Local machine proof /run/user/1000/asset-aware-native-results-local-proof.json.
Exactly30countedfiles plus2MEM; exact commit list in
/run/user/1000/asset-aware-native-results-commit-paths.json. Repository description
reviewed and still accurate. Next finish full suite, update proof/spec/MEM, commit
and push directmain using user author, then verify all exact-headCI/Pages before
further development. Public1.4.0,next consolidated1.4.1; no tag/release/bump.

## Native complete result archive — implemented; release validation underway

Complete receipts now persist outside asset.json with hash/size and exact history
bindings; v1 inline data remains read-only until a successful migration. All11
application consumers resolve full reports, including rendition and image Wiki.
Legacy archive preparation precedes external writeback. Selected corruption fails
without hiding intact history. New independent model auditor reads verified raw
blobs without the production resolver. No version bump: public1.4.0,next1.4.1.

Focused existing native tests:1925passed108.10s. Expanded storage+auditor44passed
1.52s; three-process SDK2 migration/read/Wiki equality1passed10.82s. Ruff/mypy335
source files pass. Frozen source manifest:
/run/user/1000/asset-aware-native-results-source-manifest.json
SHA d6df2ae2d7e7b92fac5f66e04092b8bc99a1592a79c5f854b8324ea95c48448c.
Actual default-model Codex CSV/PDF/derivation/Wiki evaluation is running at
/tmp/asset-aware-native-results-codex-delimited-01 (session23673), no override.
Capacity replay running15699; full/artifact checks and publication still pending.

Eleven previous terminal evaluation directories are temporarily staged with
verified hashes/mtimes in /dev/shm/asset-aware-native-results-build-staging. Original
paths retain symlinks. Restore ALL as ordinary directories using manifest
/run/user/1000/asset-aware-native-results-space.json before finishing. Staging
session87912 must complete. Private Calc24.2 fixture is removed after copying
origin to /run/user/1000/asset-aware-native-results-calc242-origin.json; private7.3
stays unchanged. This frees space for required build checks without losing traces.

ODS cache performance and MCP/evidence/Wiki integration are still pending; full
all-format goal remains active, not complete or blocked. Root checkout untouched.

## Native result storage — actual capacity failure reproduced; design recorded

On current d7b8905, a4,000-formula ODS edit commits successfully but needs15,623,786
metadata bytes. A5,000-formula ODS (3,091bytes compressed) edits successfully but
its13,087,436-byte compact receipt makes19,529,786 metadata bytes and actual commit
fails at16MiB with "Native asset output exceeds byte limit". Prior asset metadata,
managed revision and source bytes remain exact after failure. Logs/proofs:
/run/user/1000/asset-aware-ods-receipt-storage-before.{json,log} and
/run/user/1000/asset-aware-ods-receipt-storage-5000-before.{json,log}.
The earlier measured quadratic scan is also confirmed (5,000 takes18.49s).

Specification written first:docs/native-operation-results-spec.md. Plan immutable
full result blobs bound to asset/history/revision/parent/operation, small hash/size
references in versioned metadata, lazy checked repository access, read compatibility
for v1 inline results and migration on a successful write. Preserve complete data;
do not work around the problem by increasing limits or dropping audit fields.
Existing application result consumers and rendition/Wiki paths require adaptation.
The Calc oracle fix is now verified: all10 exact-head CI jobs passed. Begin the
result-archive implementation and regressions; retain private Calc24.2 temporarily
for focused validation, then remove it before heavier artifact builds.

Current remote head d7b89056f082c6e066958a961bfe801863cac406; CI35585741752/watch91058
completed successfully (watch91058 exit0). Pages35585741038 passed all3 jobs and six deployed files equal the
commit, including changed native-ods-spec.md. Publication proof remains
/run/user/1000/asset-aware-ods-adapter-publication-proof.json. Root checkout stays
untouched; alternate worktree main only. Public1.4.0,next consolidated1.4.1.

## ODS Calc export oracle — local compatibility fix verified, ready to push

Core commit e657fc3 CI35582830640 finished with eight passing jobs and one actual
integration failure (204passed/1failed); final summary consequently failed. This
was not a timeout. Retain both complete/failed CI logs and original run. Pages at
that exact head passed all3jobs and five deployed files matched exact commit bytes.

Original assertion B3.value is True failed because Calc24.2.7 exported the predicate
as numeric1 while Calc7.3 exported BooleanTrue. Official TDF24.2.7.2 was downloaded,
SHA256 be967ebc63cb15b831b4e8176492e83eb625dc00852eb96eda2b299b6e74bb74 verified,
and extracted privately without installing packages. Original test reproduced the
same1failed/1passed result. Independent expected workbooks authored with xlsxwriter
and converted by the same Calc establish exact value/data-type agreement. A second
old RGB-property assumption also failed; compare font metadata with the independent
control and verify actual red glyphs. Whole-page dimensions, text and pixels must
match the expected render; source bytes/mtime and unchanged-region checks remain.
Explicit authored Boolean cells retain strict Boolean read-back. Runtime unchanged.

Final Calc24.2 plus docs/hygiene:37passed6.40s; Calc7.3:2passed5.68s. Ruff and harness
checks pass. Root viewed Calc24.2 before/after PNGs: red title, blue numeric cells,
TRUE/high after recalculation, unchanged geometry and no clipping. Proof artifacts:
/run/user/1000/asset-aware-ods-calc242-oracle-02 and
/run/user/1000/asset-aware-ods-calc73-oracle-01. Failed local logs ending
calc242-before.log and calc242-oracle-01.log retained. Private24.2 fixture:
/dev/shm/asset-aware-calc242-fixture-01; retain until new CI passes, then remove only
that owned fixture. Existing private7.3 fixture stays.

Only test/spec/changelog plus both MEM change in this fix segment:3counted files.
All332 runtime files exactly match manifest330734bc482e2ad861174f42c5a989a238b144478349e0370406c51accb9e81c;
previous full3756passed/33skipped and wheel/Docker checks still cover identical
runtime. No need to rerun unrelated local packaging/tests for this oracle-only fix.
Next commit/push directmain with user author, then require all exact-head CI/Pages
jobs. Public1.4.0,next consolidated1.4.1; no version/tag/release change.

ODS MCP/reference/citation/Wiki work remains pending. Measured quadratic cache
receipt scans and metadata-history growth (details below) must be resolved before
broad exposure; do not drop provenance to satisfy budgets. No subagents or new
model invocation; broad goal remains active and unproven complete.

## ODS adapter — CI Calc24.2.7 predicate export failure under investigation

Retained-raster publication at9a117f2 is complete: CI35576413197 all10 and
Pages35576410855 all3 pass, five deployed files exact. Proof:
/tmp/asset-aware-image-retention-publication-proof.json. Owned Pillow12.2 removed.

ODS native package/reader/text/grid/editor and domain values/locators implement
creation, compressed reads, scoped edits/clears and deterministic cache/column
repairs. Real Calc caught stale6.86 after precedent5.75; typed cache invalidation
retains formulas/styles/paragraphs and produces11.50,TRUE,high on independent read/
render. Unchanged text geometry/pixels match. Root viewed before/after PNGs; final
proof03 PNG hashes equal those inspected proof02 images. odfdo3.25.0 independently
reads literal Unicode/Decimal/Boolean values and compressed ranges.

First full3753passed/33skipped722.35s preceded a final Unicode formula-prefix fix.
Added Chinese/combining-character namespace cases exposed wrong expression parsing;
use actual XML NCName validation. Final focused60 ODS plus32 docs/hygiene =92passed
4.14s. An old label-count18 assertion failed after area:opendocument was added; it
now follows the complete explicit label fixture. Premature second full was stopped
with SIGINT (28passed/9skipped) because its collection retained the stale assertion;
all logs retained. FINAL full session93089 exited0:3756passed/33skipped757.02s.
Log:/run/user/1000/asset-aware-ods-adapter-full-final-second.log. Source stayed frozen
through final full, wheel and Docker verification; manifest rechecked exact.

Final source-manifest SHA330734bc482e2ad861174f42c5a989a238b144478349e0370406c51accb9e81c
covers332 source files. Final wheel3.13/Docker3.12 exact-source, exact ODS bytes/full
receipt replay and import/doctor/30tools/SDK2 stdio pass. VSIX199tests,64contententries,
package/install/update/artifact gates pass; localactivation unavailable; required
remote Linux must pass. Ruff785files/mypy332/Bandit/zizmor/harness pass. Metadata
description remains accurate; new area:opendocument remote label and sync script
verified. Docs site remains synchronized; public capabilities do not claim ODS MCP.

Final proof:/run/user/1000/asset-aware-ods-adapter-final-local-proof.json. Final own
Dockere32fdb6784eb/builder999bea8023d4 and wheel env removed; previous own artifacts
also removed. All11 temporarily staged historical runs are restored as ordinary
directories at their original paths with exact hashes/mtimes independently checked.
Manifests:/tmp/asset-aware-ods-final-staging.json and
/run/user/1000/asset-aware-ods-adapter-final-space.json. Low root disk required
removing only this worktree's ignored, rebuildable vscode-extension/node_modules
after all extension checks; package-lock unchanged, restore with npm ci in that
directory when next needed. No actual/failed traces or unrelated files removed.
Isolated odfdo fixture /dev/shm/asset-aware-ods-odfdo-325 remains until CI completes.

26counted files plus2 MEM committed and pushed as e657fc378220ff06a5bafe3d51d341fc524da908
with user author u9401066 <u9401066@gap.kmu.edu.tw>, directmain. CI35582830640
at that exact head: eight jobs pass, integration and summary FAILED. Integration:
204passed/1failed499.88s. tests/integration/test_native_ods_calc.py expected
B3.value is True; Ubuntu24.04 Calc24.2.7 exports numeric1. Existing watcher2795
exited1; authoritative run is terminal, not an observation timeout. Keep failed
log:/run/user/1000/asset-aware-ods-adapter-ci-failed.log. Same-version control and
actual render must distinguish export representation from lost display/type.
Do not merely accept truthy values or restart the failed run. Pages35582828924
all3jobs pass and five deployed files match exact commit bytes. Publication proof:
/run/user/1000/asset-aware-ods-adapter-publication-proof.json. Both package versions
remain1.4.0; next consolidated1.4.1; latest GitHub release remainsv1.4.0; no newtag.

MCP/evidence/citations/Wiki wiring, ODS sheet/grid lifecycle/rich-run editing,
recalculated renditions and actual default-model Codex remain required. Next wiring
uses NativeDocumentRequest/native_schema/native_document_contract, operations,
process isolation, reference unions/evidence and Wiki; avoid treating compressed
physical ranges as one logical cell. Cache receipt read-back should be indexed for
large formula catalogs before broad exposure. Original dirty worktree untouched;
no subagents. Full all-format goal remains active, not complete.

Read-only integration inspection: NativeDelimitedOperations/ProcessNativeDelimited
provide the revision/CAS/process pattern. ODS references must enter NativeDocumentRequest,
NativeSelectionParent and NativeReference, then evidence, CSL/custom citations and
Wiki. citation_format_service currently has no ODS locator rendering, so default
source citation would have an empty required locator; add a canonical ODS branch.
Compressed catalog ranges must not imply each logical cell was separately read;
keep exact-cell identity distinct from physical repetition descriptions. A bounded
formula scale probe completed successfully in session82056, log:
/run/user/1000/asset-aware-ods-formula-scale-before.log. 1000/2000/4000 formulas
took0.806/3.093/12.136s, with every cache before/after checked: measured quadratic
rescan cost. Complete receipt sizes were2.62/5.23/10.47MB despite1.3/1.6/2.1KB
compressed outputs. Avoid quadratic scans before MCP exposure; also account for
NativeAssetRepository MAX_METADATA_BYTES16MiB across the entire history. Do not
solve receipt growth by silently dropping provenance or pretending all formulas
were checked. Full immutable source revisions and exact paged receipts must stay
accessible; storage budget/precommit behavior needs explicit integration tests.
Prioritize this actual CI failure before new runtime development. Current MEM update
records this follow-up state; commit together with the next coherent segment.

## Retained raster release gates — ready to push main and verify remote jobs

Core implementation committed fbdc592 with30counted files plus two MEM. Runtime
source remains031a7a209b69748cc5eda1ca47a9c5f4dc9a74e2ecf0d171806bd36515d1a54c;
actual default Codex source fingerprint matches. Full3682passed/33skipped and final
focused69passed include actual old/new Pillow SDK2 restart and strict audit fixes.

Built wheel (Python3.13) and Docker (Python3.12) replay the same175call Codex trace
with exact source fingerprints and full independent image/history/citation/Wiki
checks; console, doctor,30-tool listing and SDK2 stdio pass. VSIX199tests,64packaged
content entries,66-file250.17KB package,install/update and all-artifact1.4.0 audit
pass. Local activation remains unavailable without xvfb-run; required remote Linux
activation must pass. Docs/hygiene35tests pass; source/bundled guides synchronized.
Browser plugin unavailable; existing Playwright1.63.0/Chromium1234 with private libs
passes eight bilingual desktop/mobile states, no overflow/console errors. Root
visually inspected the Chinese retained-evidence section and English mobile page.

Bilingual native usage/evaluation, raster specification and five source/bundled
assistant guides now explain catalog/full-reference pins, exact preview recipes,
retained integrity vs reproduction and unchanged mutation checks. Corrected the
previous milestone's stale pending-publication wording using verified remote proof.
GitHub description still matches scope; latest release verified v1.4.0. No new tag.

19counted docs/assets/evaluation files plus two MEM comprise this second segment.
Owned Docker9e03817c918c and builder3b6ac4e7dec2 removed after verification; clean
wheel/replay envs removed. All11temporarily staged owned historical runs restored
with exact bytes/mtimes (/tmp/asset-aware-image-retention-staging.json). Keep actual
and failed traces, logs and isolated Pillow12.2 target until CI succeeds. Local
proof:/run/user/1000/asset-aware-image-retention-local-proof.json. Next commit/push
main, await every exact-head CI/Pages job, compare deployed files, then record final
publication proof. Public1.4.0,next consolidated1.4.1; broad all-format goal active.
Original dirty checkout remains untouched; no PR, branch, subagent or model override.

## Retained raster evidence — local runtime and actual Codex verification passed

Complete frame/catalog records and exact preview recipes now persist beside native
revisions. Historical full refs, regions, selections, derivations and pinned native/
cross-format Wikis survive restart and decoder drift. Source hash checks remain;
retained integrity is explicitly not fresh decoder reproduction. Missing historical
preview recipes require a matching decoder. Current edit guards stay unchanged.
Atomic files/markers/locks, bounded records/PNGs and symlink/hash/conflict checks
fail closed. New optional catalog pins/full frame reads are advertised by contract.

Actual Pillow12.2.0->12.3.0 SDK2 balanced/compact restart tests passed with isolated
old package /dev/shm/asset-aware-image-retention-pillow122; no global dependency
change. CI Python3.10 now installs that explicit test-only decoder and enforces the
same test. New retention/SDK2 scope34passed7.74s. Full suite3682passed,33optional
skips,706.74s. Final focused archive/retention/audit69passed2.59s; this includes14
new audit cases added after full-suite collection. Ruff772files, mypy325sources,
Bandit, zizmor and release-harness checks pass. No runtime changes after full-suite
or actual-model launch. Source031a7a209b69748cc5eda1ca47a9c5f4dc9a74e2ecf0d171806bd36515d1a54c.

Actual default Codex /run/user/1000/asset-aware-codex-image-retention-crud-01:
CLIexit0,292.81s,175successful calls,zero toolerrors;15framePNGs,one region,three
TIFF revisions,six literal cells,three Wikis. Independent audit attempt3 passes;
attempt1 rejected legitimate read_workbook and attempt2 rejected the fully read
global policy despite complete per-operation schemas. Corrected audit verifies
complete source-bound workbook records and complete global capability/policy pages;
per-mutation schemas, full receipts/pixels/lineage/required operations remain strict.
Both failed attempts and original wrapperexit1 retained. New audit tests first
omitted synthetic completed status, then treated operation inventory as a dict;
corrected fixtures pass, all failure logs retained. Root viewed the actual full-row
crop [254,422,796,454], confirming visible Aluminum,3.43 ± 0.13,% and method letters.

Thirty counted files plus two MEM form this local implementation segment. README,
Chinese README, changelog, specification and architecture updated. Next: detailed
bilingual usage/assistant guidance/site sync, package/runtime gates, segmented main
push and exact-head CI/Pages verification. No publication claim for this new code
until those finish. Public1.4.0,next consolidated1.4.1; no per-feature bump/tag.
Broader all-format goal stays active. Original dirty checkout remains untouched.

## Raster evidence retention — implementation in progress

Previous version-only turn made no implementation progress. Revalidated clean main
at 1920d39. Its publication is complete: CI35571014125 all10jobs, including required
Linux VSIX activation, and Pages35571013014 all3jobs succeeded. Seven live website
files matched commit bytes; latest release remains v1.4.0. Proof:
/tmp/asset-aware-native-image-publication-proof.json. Owned browser server and private
Python3.10 environment were stopped/removed after success; all traces remain.

Now preserving complete image frame/catalog records and generated previews across
decoder changes. Existing hashes include decoder version and must remain unchanged.
Archive integrity/source-byte checks are distinct from current reproduction and
Agent semantic review. Current-decoder mutation checks stay intact. Specification
updated before implementation. Runtime integration, corruption/drift regressions,
actual MCP/Agent verification and release gates remain pending. Public1.4.0, next
consolidated1.4.1; no per-feature bump. Work only in isolated agent-assets main;
original dirty checkout untouched. Broad all-format goal remains active.

## Native raster local release gates — ready for exact-head publication checks

Actual default-model Codex NIST derivative audit passes258calls/zeroerrors/304.08s,
15framePNGs/one region/three TIFF revisions/six literal XLSX cells/three Wikis.
Full suite:3648passed,33optional skips,726.48s. Python3.10 image/SDK2 scope:111passed,
41.10s; balanced17.56s/compact17.39s. Final docs/GitHub-hygiene35tests pass0.34s.
Ruff766files, mypy322sources, Bandit/zizmor/harness/diff checks pass. Installed wheel
and Docker exactsource replay plus console/doctor/30-tool SDK2 stdio pass. Source:
de71fed018b653557674cd0d50623ae92eba7de3e336626c7244b2097f917a00.

VSIX199tests,64package-content entries,all-artifact audit and install/update pass.
Local activation unavailable without xvfb-run; required CI activation must pass.
Eight bilingual desktop/mobile website states pass; feature desktopzh/mobileen
screenshots visually checked. Browser first lacked private libasound path, then
old copied assertion expected nonexistent native-image-v1; retained both failures.
Corrected harness uses existing private libs and actual raster contract terms.
No production/UI fix or global package/font/renderer change was needed.

README/ChineseREADME, changelog/roadmap/spec/capability analysis, Chinese/English
usage and evaluation pages and five source/bundled assistant guides now reflect
scoped raster workflows and remaining limits. GitHub metadata/label scripts now
include raster frames and retain PDF annotations; topic list stays unchanged.
27counted files plus two MEM comprise this final docs/assets/metadata segment.
All11temporarily staged owned terminal runs restored with exact hashes/mtimes.
Owned Docker image591f7dafd083/builderb045f1d29e3c and wheel/replay envs removed;
Python3.10 test env retained until CI passes. Actual/failed traces remain intact.

Proof:/run/user/1000/asset-aware-native-image-validation.json. Commit/push main,
then await all exact-head CI/Pages jobs, compare live files and verify release1.4.0.
Docs server8887 still running for checks; stop after publication. No new tag or
version bump: public1.4.0, next consolidated1.4.1. Broader all-format goal remains
active; original dirty checkout untouched. Author u9401066 <u9401066@gap.kmu.edu.tw>.

## Actual Codex raster workflow — independent audit passed; release gates in progress

Local integration committed as dc0b8d1 (30 counted files + two MEM). New evaluation
uses default Codex CLI only, no model override/subagents/shell tools. Hash-pinned
NIST SRM1648a original page index4 is explicitly rasterized into a benchmark PNG
with EXIF orientation6; it is not claimed as an originally published NIST image.
Source fingerprint remains de71fed018b653557674cd0d50623ae92eba7de3e336626c7244b2097f917a00.

Actual run /run/user/1000/asset-aware-codex-native-image-nist-01 completed with CLI
exit0 in304.08s:258 successful MCP calls, zero tool errors. Retained artifacts and
independent audit prove15 actual full-frame PNGs, one region crop, three exact TIFF
revisions (reorder/insert/delete), historical refs/selection, six literal XLSX cells,
region-to-cell derivation and three source-attached custom-citation Wiki snapshots.
The first wrapper failed AFTER the successful CLI turn with ModuleNotFoundError
because the audit module was being completed; retain its run log. Separate completed
audits pass. Import now precedes any model execution; prepared inputs/runtime are
rechecked and prior traces cannot be overwritten. Numbered audit attempts retained.

Independent positive/negative audit regression tests:23 passed0.28s; modified pixels,
orientation/alpha/order/count/crop or incomplete/hash-invalid reads fail closed.
Checkout replay verifies source fingerprint and passes. New audit test and all five
image integration modules are required by Python3.10 CI/release-harness audit. Ruff,
format and harness pass. Full suite is RUNNING: session51437, owned log
/run/user/1000/asset-aware-native-image-full-suite-first.log; do not claim it passed.

This evaluation/test/spec segment remains local. Next: bilingual docs and bundled
assistant assets, full suite result, wheel/container replay/runtime/VSIX checks,
browser/docs checks, exact staged commits/push and final all-job CI/Pages verification.
Keep original worktree untouched, <=30 counted files per commit excluding two MEM,
public1.4.0 and next consolidated1.4.1; no tag/per-feature bump. Broad goal active.

## Native image MCP integration — local verification passed, real Agent evaluation next

Version policy reconfirmed: Python/VSIX remain 1.4.0; next consolidated release
1.4.1. No per-feature bump/tag. Work remains on main in the isolated agent-assets
worktree; original dirty checkout untouched. Thirty counted integration files plus
the two MEM files comprise this segment, author u9401066 <u9401066@gap.kmu.edu.tw>.

Production ProcessNativeImage now provides full hash-paged catalogs/frame records,
actual PNG previews/regions, guarded PNG creation/cropping, ordered TIFF composition
and exact candidate revisions. Full references integrate historical verification,
selections, derivations, custom/CSL citations and immutable image/cross-format Wikis.
Wiki identity includes catalog/receipt/color policy; direct operation input files
are preserved, without claiming recursive semantic lineage. Repeated frame inputs
now decode each source version once. Invalid ICC requires explicit unmanaged preview.
MCP checks bytes/structure; Agent owns semantic and actual visual review/correction.

Focused suite: 332 passed in 39.28s. Final changed scope: eight passed in 35.04s,
including balanced/compact actual SDK2 stdio lifecycles (16.67s/16.76s). Full Ruff,
format (757 files), mypy (322 sources), Bandit, zizmor and release-harness audit pass.
Evidence: /run/user/1000/asset-aware-native-image-integration-proof.json;
source SHA de71fed018b653557674cd0d50623ae92eba7de3e336626c7244b2097f917a00.
Earlier failures are retained: nonexistent test path (zero collected), two wrong
Wiki test assumptions (authors field and two unique input versions), and SDK2 test
helper passed a partial instead of the client. Corrected tests retain all assertions.
Root disk exhaustion interrupted Ruff cache writing; only this checkout's mypy/Ruff
caches moved to owned /run/user/1000 paths, no unrelated data removed.

Next: add five new test paths to the persistent release-harness audit, actual
default-model Codex evaluation with a hash-pinned real-PDF-derived oriented image,
independent trace/artifact checks, bilingual docs/assistant asset sync, full release
gates and final exact-head CI/Pages before claiming publication. Existing PDF
publication proofs do not cover this new runtime. No new push yet; broad goal active.

## Product scope documentation — capability matrix and honest comparison criteria

Local kernel commit 46e0494 contains 25 counted files plus two MEM files, author
u9401066 <u9401066@gap.kmu.edu.tw>, on main. It is not pushed yet; production MCP
wiring remains unchanged. Image/PDF worker focused tests pass 76/76, mypy eleven
sources, Ruff, release-harness and workflow security audits pass. Full release and
actual-Agent validation must follow integration, not be borrowed from the older
PDF publication proof.

Rewrote docs/agent-asset-gap-analysis.md from current contracts/implementation:
removed unsupported 100%/94.5% fidelity and enterprise-share percentages; documented
per-format capabilities and explicit unknowns. Built-in model analysis may suffice
for summaries/Q&A; continued native editing, immutable evidence and reusable Wiki
are the value proposition to test, not an asserted benchmark victory. Comparison
must include a coding Agent with existing libraries, not only model file upload.
Official Docling, PyMuPDF, pikepdf, pypdf, pdfplumber, OCRmyPDF, Pillow and libvips
references are linked with distinct roles. No new dependencies installed.

README/Chinese README now describe current main separately from public1.4.0 and
remove stale pending-CSL claims. Chinese wiki and English native-file page explain
responsibilities and pending raster integration. Regenerated Pages payload; 28 docs
checks pass in 0.18s, node --check docs/site.js and diff hygiene pass. Nine counted
doc files plus two MEM files in this segment. Local only; do not claim new Pages
publication. Next remains image application/MCP/evidence/Wiki and SDK2/actual Codex,
then full local release gates and exact-head CI/Pages checks. Next release1.4.1.

## Standalone raster kernel — focused verification passed, integration pending

Previous PDF annotation milestone is fully published at main
1d4eb416e40b0e8301d5dec3ef58aca5bd053ca5: final CI 35562614780 all ten jobs,
Pages 35562614554 all three jobs and six exact deployed files; public v1.4.0.
Authoritative proof: /tmp/asset-aware-pdf-annotations-publication-proof.json.
The preceding pending-CI entry is historical; its owned Python 3.10 env was removed.

New standalone-image kernel supplies complete oriented/typed frame records, source
frame/region refs, previews, PNG/TIFF extraction, ordered TIFF composition and exact
candidate revisions with complete frame accounting. PNG/APNG/JPEG/TIFF/GIF/WebP/BMP/
AVIF reads have explicit decoder/precision limits. Palette/alpha changes are pixels;
LAB samples need no invented RGB conversion. GIF truncation and TIFF main-chain
corruption fail before pretending the sequence is complete. ProcessNativeImage
bounds execution and transports plain typed records. Existing PPTX embedding and
PDF worker behavior remain unchanged; no production wiring or advertised capability.

Initial 52 tests passed. Expanded first run exposed iTXt MessagePack incompatibility
and an incorrect test assumption about preserved palette transparency: retained
/run/user/1000/asset-aware-native-image-core-second.log (63 pass, 2 fail). Fix retains
international text/language/translated keyword as plain types; palette test checks
actual alpha preservation. Final focused run: 76 passed in 7.63s (68 image cases,
eight existing PDF worker cases), core-fifth.log. mypy-eighth.log: all eleven new
source files pass. No dependency/version change. Six image test modules are now
required in Python 3.10 CI and the release-harness audit before future publication.

This is a local kernel segment, not a complete image feature or all-format outcome.
Next: application/repository CAS, paged SDK2 records and actual PNGs, historical
verification/selections/derivations/CSL/Wiki, real default-model Codex image evaluation,
full release gates and final CI/Pages. Rewrite stale gap analysis (unmeasured 100% /
94.5% / enterprise-share claims) from current code. Keep <=30 counted files per
segment, original dirty checkout untouched, direct main author u9401066.
Public 1.4.0; next consolidated 1.4.1, no per-feature tag or version bump.

## PDF annotation Python 3.10 CI — measured timeout correction, final rerun pending

The coverage correction correctly exposed two 180-second timeouts on CI head
7400c7e, run 35561236292: 1,157 passed, four optional skips, two failed in 712.88s.
Both failures are pytest-timeout, not content assertion errors. All other CI jobs
except the dependent summary passed. Full logs and completed job states retained:
/run/user/1000/asset-aware-pdf-annotations-ci-py310-first.log and
/tmp/asset-aware-pdf-annotations-second-remote-proof.json. No failed run rerun.

Created isolated /dev/shm/asset-aware-pdf-annotations-py310 using frozen lock and
system Python 3.10.12; symlinked dependencies, no global Python/font/renderer change.
A diagnostic invokes the unmodified balanced test with every assertion and records
each MCP call: 408 calls, 142.512s, passed. It has an explicit 600s diagnostic bound.
Evidence: /run/user/1000/asset-aware-pdf-annotations-py310-diagnostic.
Only the two annotation case deadlines now use 300s; the enclosing Python 3.10 job
allows 20 minutes and reports ten slowest tests. Other test deadlines remain 120s;
no assertion, paging completeness, source/visual/Wiki checks or runtime code changed.
Formal Python 3.10 pytest then passed both cases in 266.20s (134.47s/130.83s).
Final source fingerprint remains 74e3abc39b06170c0bedc7fa777654abfdb0d9138e638012c1da8293a27b25f5;
prior complete 3,521-test suite, actual Codex and wheel/Docker proofs still apply.

Ruff/zizmor/harness guards, 28 docs tests and regenerated site pass. Chinese/English
release notes preserve both timeout failures and successful diagnostic. Eight
browser/language states passed after the failure documentation; later text adds
only the formal two-case result. Owned temporary docs server has stopped.
Validation JSON updated with the failed run and measured correction. This six-file
plus two-MEM segment needs commit/push and fresh all-ten CI/all-three Pages checks,
six live byte comparisons and latest-release confirmation before publication proof.
Keep private Python 3.10 environment until final CI passes, then remove only it.
Public 1.4.0; next consolidated 1.4.1. No new tags, PRs, subagents or model overrides.
Broad all-format goal remains active; original dirty checkout remains untouched.

## Native PDF annotation CI coverage — all gates passed, adding persistent SDK2 coverage

8b7e243 first publication checks passed: CI 35560131550 all ten jobs and Pages
35560130943 all three jobs, six deployed files byte-identical; release stays v1.4.0.
Proof: /tmp/asset-aware-pdf-annotations-first-remote-proof.json. Final review found
that the explicit CI test list omitted the new annotation SDK2 lifecycle cases,
although the full local suite already ran both. Added six focused annotation unit
modules and tests/integration/test_native_pdf_annotations_stdio.py to the existing
Python 3.10 job. This exercises balanced/compact on the minimum supported Python
without adding load to the Writer/Impress integration job. No job/test timeout or
runtime source change. Added seven required paths to the release-harness guard;
it first failed on all seven missing entries, then passed with the workflow fix.
Ruff and zizmor pass; collection confirms both existing SDK2 cases. Existing final
runtime fingerprint, full suite, wheel/Docker and actual Codex proofs remain valid.
Second exact-head CI/Pages verification is required after this two-file+two-MEM
commit. Keep both runs and proofs; this is a coverage correction, not a retry to
hide failures. Owned docs server stopped; all staged runs restored and own package
test environments removed. Public 1.4.0; next consolidated 1.4.1. Broad goal active.

## Native PDF annotations — local release gates complete, publication pending

Runtime commits fdf9ba9, 0b117a9 and b2cbbfc remain local until this docs segment.
Final source fingerprint: 74e3abc39b06170c0bedc7fa777654abfdb0d9138e638012c1da8293a27b25f5.
Full suite: 3,521 passed, 33 optional skips, 698.37s; final docs: 28 passed, 0.18s.
Ruff 728 files, mypy 306 modules, Bandit medium/high gate pass (185 low findings
retained). VSIX 199 tests, 64 package files and install/update pass. Local activation
unavailable: xvfb-run missing; required CI still must pass. Baseline 0.2.10 fixture
and optional runtime diagnostics are not part of the local smoke result.

Final NASA Apollo02 default Codex: 238 successful calls, one recovered contract
parameter error, 379.19s, 359 original pages, four revisions, five complete records,
eight actual PNGs and two Wikis. All body streams/pixels checked; Agent visually
reviewed page indices 17/18 only. Created/final target PNGs independently viewed.
NIST01 passed before final parser-copy correction; Apollo01 failed safely and its
original evidence is preserved. No model overrides or retries to hide failures.
Installed Python 3.13 wheel and Python 3.12 Docker replays both match final source
and the same four revisions, eight images, annotation evidence and Wikis. Console
and SDK2 stdio smoke pass for both installed distributions.

Chinese/English docs, README, changelog, roadmap, full spec and five source/bundled
assistant instructions updated. Eight desktop/mobile/language browser states pass;
feature desktop Chinese/mobile English screenshots inspected. GitHub description
and area:pdf label now include annotations; existing topics preserved.
All 11 temporary hash/mtime-verified staged runs restored. Owned Docker image/builder
and wheel environment removed; failed runs/probes retained. Docs HTTP port 8886
still needs shutdown after publication. Original dirty checkout untouched.
Validation proof: /run/user/1000/asset-aware-pdf-annotations-validation.json.
Next: commit this 20-counted-file docs segment plus two MEM files, push main, require
exact-head CI (10 jobs) and Pages (3), compare six live files and latest v1.4.0.
Public remains 1.4.0; next consolidated patch 1.4.1, no feature-by-feature tag/bump.
Broad all-format goal remains active. Author u9401066 <u9401066@gap.kmu.edu.tw>.

## Native PDF annotation real-Agent checks — rendering/parser copy corrections

Local commits:fdf9ba9(core),0b117a9(22counted integration files+2MEM). Not pushed.
Default-model Codex NIST01 passed:399successful MCP calls+1recovered contract
text_limit error,321.35s,17original pages,4revisions,37complete annotation records,
8actual PNGs,2Wikis. All body streams/pixels and8original Links preserved. Source
fingerprint is recorded in expected.json; NIST precedes the later NASA reader fix.
Actual created/final target images independently viewed. Evidence:
/run/user/1000/asset-aware-codex-pdf-annotations-nist-01.

New mixed Highlight/FreeText audit exposed MuPDF annots=False compositing differences
(max1level,mean<0.004). Native graphs/body streams unchanged. Production now compares
exact pixels from annotation-free disposable reader copies; audit independently
removes page Annots using MuPDF xrefs, retains all original full-annotation checks.
No tolerance relaxation or source/output mutation. FreeText can enter page text
extraction, documented explicitly. Probe retained at/run/user/1000/asset-aware-pdf-
annotation-transparency-probe. After first correction109focusedpass6.80s,mypy306pass.

Apollo01 actual Agent failed safely at first mutation:writer warning in the reader
copy because it bypassed verified duplicate-Length parser checks. No revision was
committed. Exact traceback retained inpdf-annotations-apollo-writer-probe.log.
Reader now uses NativePdfPackage, preserving strict known-equal proof and rejecting
conflicting/unknown warnings.58focusedpass3.27s. Apollo02 default-model run ACTIVE;
full-final pytest ACTIVE. Full-first was intentionally interrupted for this real
bug:55passed30optional skips468.35s,not a final full-suite result.

New opt-in runner/auditor/replay and negative audit tests retain real corpus identity,
complete reads/order, raw streams, all body pixels, delivered images, historical refs,
derivations and Wiki checks. Docker first build and wheel smoke passed before NASA
fix; they are rebuilt after the fix. First Docker replay found mount UID/path issues,
not document failure; preserve logs, use uid1000 and SAME absolute evidence bind path.
Latest Docker image:asset-aware-mcp:pdf-annotations-final-smoke. Wheel venv:
/dev/shm/asset-aware-wheel-smoke-6m300tps/venv. Source replay awaits Apollo02 result.

Docs/harness updates remain separate/uncommitted; generatedsite and source/bundled
instructions synced. VSIX199tests/package64 passed; install/update smoke running.
xvfb-run absent, required-activation attempt exits127; normal install smoke is next.
Seven old owned evaluation runs remain hash/mtime-verified RAM staging; four restored.
Restore ALL with/tmp/asset-aware-pdf-annotations-stage.py restore after own Docker
cleanup. Do not delete unrelated caches. No new version/tag:public1.4.0,next1.4.1.
Authoru9401066@gap.kmu.edu.tw;original dirty checkout untouched;no PR/subagent.
Broad all-format goal remains active. Full release/docs/CI/Pages/push outstanding.

## Native PDF annotation MCP integration — SDK2 and provenance validated

The22-file runtime/service/test segment exposes complete hash-pinned catalogs and
records, guarded create/update/delete, per-kind schemas, source/history checks and
isolated PDF worker operations. Annotation refs support verify, selections,
derivation source/target endpoints and CSL. Wiki pdf-annotations-v1 retains exact
PDFs, page previews, full annotation records and custom precise locators;
no-annotation PDFs remain byte-identical legacy pdf-pages-v1. Historical snapshots
and human notes survive edits/deletion. Comments are distinct from underlying text.

Focused core/service/provenance/schema/existing-PDF tests:111pass, then both SDK2
balanced/compact lifecycle cases pass248.32s. SDK covers complete policy/schema,
all records/receipts, create→metadata/appearance→delete, actual PNG pixel equality,
old refs/selections, derivation history and immutable Wikis. Ruff and mypy306pass.
New test-only defects retained:missing publish source_path, wrong verify_derivation
key, native /Text spelling and listing-versus-full-page evidence; fixed assertions
and reran only relevant checks. Logs:/run/user/1000/asset-aware-pdf-annotations-
service-{second,third}.log, sdk-{second,third}.log, service-mypy-final.log.

Corefdf9ba9 and this integration segment stay LOCAL pending complete feature proof.
Real originals inspected:NIST1648a17pages/8Link annotations;NASA Apollo11359pages/
no annotations with already-supported identical duplicate Length declarations.
Actual cached NISTpage4/NASApage17 images viewed. New default-model Codex annotation
runner/auditor is being prepared in uncommitted tests/codex_pdf_annotations; actual
Agent runs, full regression/release/docs/CI/Pages publication remain outstanding.
Public1.4.0;next consolidated1.4.1. User reiterated stay1.4.x;no per-feature bump/tag.
Broad goal remains active; no subagent/PR; authoru9401066@gap.kmu.edu.tw.

## Native PDF annotation kernel — validated, MCP integration next

Previous goal turn was substantive progress:96dd150 is fully published.
Exact-head CI35554037436 all10pass, Pages35554036827 all3pass, six live files
byte-identical; integration203pass445.69s, both SDK note cases pass.
Proof:/tmp/asset-aware-docx-notes-publication-proof.json passed/fully_published.
Private Writer24/py310 removed after CI; all11stagedruns restored; failures and
Agent evidence retained. Redundant final remote probes had transient DNS errors;
this turn a fresh GitHub REST main ref independently confirms96dd150.

Eight new files implement native annotation core, NOT yet exposed through MCP:
12 typed appearance kinds, complete catalog/record identity (including Popup,
Widget, Link and unknown native graphs), create/metadata/explicit appearance/delete
operations, exact inverse native preservation and bounded independent pixel checks.
Batch refs are validated before mutation. Native array indirection, cross-page
replies, IDs/content and original bytes are preserved. Owned-popup deletion is
explicit; incoming dependencies, external/shared arrays, locks, signatures, field
structures and unsupported rich/appearance edits retain guards. Annotation
Contents is distinct from underlying highlighted text. Complete service receipts,
reference verification, selection/derivation/Wiki integration remain next.

Focused core plus existing PDF tests:131pass4.57s; Ruff and mypy304modules pass.
Initial40pass/3Inkfail fixed with plain coordinate pairs. Indirect Annots regression
first19pass/1fail, corrected without weakening external dependency checks.
Coordinate suite first66pass/6fail exposed nonzero origins/UserUnit with rotation;
actual pixels independently proved clipping/offset. Corrected disposable unrotated
generation and scaled display transforms. Eight before/after PDFs, measurements
and actual reviewed PNGs retained:/run/user/1000/asset-aware-pdf-annotation-geometry-probe.
Post-fix maximum bounding error0.001389 (stroke/pixel boundary); no NumPy dependency.
Logs:/run/user/1000/asset-aware-pdf-annotations-{records-first,dependencies-before,
core-first,core-second,core-third,core-fourth,core-final,core-mypy*}.log.
Next: NativePdf/process methods, typed MCP operations/contracts, complete paged
reads/receipts, refs/selections/derivations and immutable Wiki; SDK2 and actual
default-model Codex on original real PDFs, full validation/docs/Pages before push.
This8-file core segment plus2MEM stays local until the complete feature is ready.
Public1.4.0,next consolidated1.4.1; no tag/bump/PR/subagent. Broadgoal stays active.
Original dirty detached checkout untouched; authoru9401066@gap.kmu.edu.tw.

## Native Word note ID correction documentation — ready for publication

Runtime a8e8333 and recovery auditc7b8d10 are committed underu9401066.
This20-file docs/harness segment updates bilingual operation/evaluation guides,
README/CHANGELOG/ROADMAP, generatedsite and five source/bundled instruction pairs.
The actual Writer24 failure and controlled probes are reported honestly; explicit
mapping is a managed document correction, not a hidden renderer workaround.
Final3403/33optional skips426.69s;actualCodex211success+2recovered errors282.24s;
wheel/Docker24notes/4catalogs/2Wikis atsource22b65;browser8states anddocs25pass.
All11stagedrunsrestored,ownedDockerimage/builderremoved,server8886stopped. Private
py310 andisolatedWriter24remainforCI followup. Originalfailures/oldtracesretained.
Pushmain next,then exact-head allCI/Pages jobs andsixlivebytecomparisons. Previous
CI failure isterminal andneeds thiscorrectivecommit, not an unchangedrerun.
Localproof:/run/user/1000/asset-aware-docx-notes-remap-validation.json.
Publicationproof:/tmp/asset-aware-docx-notes-publication-proof.json.
Public1.4.0,nextconsolidated1.4.1;notag/bump.Broadall-formatgoalactive.

## Native Word ID correction — actual Agent recovery harness

Runtime/spec/tests committed a8e8333 (7counted+2MEM). This2-file test segment adds
opt-in --repair-note-ids while keeping the original3-revision audit compatible.
The default-model Agent must read/render the misbound intermediate revision,
explicitly remap known IDs, reread full receipts/notes, review corrected pages,
verify mapped/deleted historical refs and retain both immutable Wikis. Independent
native/render audits enforce all4versions,9PNGs and the actual wrong contents
before correction. Final211successful calls+2recovered errors/282.24s is retained.
No model override or rerun to erase errors. Source22b65 unchanged; documentation/
harness segment follows. Public1.4.0,nextconsolidated1.4.1,broadgoal remainsactive.

## Native Word note ID correction — validated runtime/spec/tests

Prior notes main aff334e CI35457459127 failed honestly: npm503 maintenance and a
real Writer24.2.7 note-content binding error (202pass/1fail integration423.87s).
Pages35457458636 all3pass and6publicfilesexact; all other functional/platform jobs
passed. npm service recovered; both locked npm audits now0 findings. Do not rerun
old integration unchanged or weaken the original page assertions.
Official isolated24.2.7.2 independently reproduced the wrong footnote/endnote
contents. Eight controlled runs show body-ordered definitions plus body-aligned
IDs pass both7.3.7 and24.2.7. Probe files/first CI failure remain retained under
/run/user/1000/asset-aware-docx-notes-lo24-replay and matching CI-log prefixes.
Added explicit remap_ids inside update_docx_notes: bounded part/kind/old-new maps,
atomic swaps/collision checks, normal-role/main-body scope, exact inverse XML
preservation checks and full mapping/reference receipts. Ordinary edits keepIDs;
only explicit mapping changes them. Source and historical refs/Wikis remain intact.
No hidden preview transformation; actual exported DOCX is the reviewed source.
Final production22b65b0de604570966f520b6860bec439813d71fd0751c0bd5b2331fddfc6758.
Default Codex03 on24.2.7.2:211success+2recovered input errors/282.24s;24complete notes,
4catalogs,13contracts,4managed revisions,2Wikis,9actual PNGs independently replayed.
Agent saw wrong contents, applied explicit maps and reviewed all corrected pages;
old foot11/end5/deletedfoot8 refs still verify. Viewed before/after page1 and final
page3 locally. No model override, no Microsoft Word or universal-fidelity claim.
Full3403pass/33optional skips/426.69s on7.3 withCJK andNIST/NASA; focused74/18.06s;
SDK24 bothconfigs+16initialremaptests18pass27.25s; final19remaptests in full suite.
Python3.10 79pass/1optional skip28.60s. Wheel/Docker outsidecheckout both reproduce
24notes/4catalogs/2exactWikis at same source. Standardpip/doctor/tools/SDK2 pass.
Ruff707/mypy298/Bandit/harness/sync/allartifacts,uv214packages andnpm audits pass.
VSIX199tests/64files/install-update pass; GUI activation to exact-head CI.
Browser8desktop/mobile zh/en states pass,actualdesktopzh/mobileen reviewed; cached
CDN assets used. First throwaway browser expectation accidentally renamed product
projection token; fixed harness-only, original failed log retained. Docs25pass.
Dockerdebf32b86c2e andbuilderab576b5192d1 removed; all11owned stagedruns restored
with exacthashes/mtimes. OwnedHTTP8886 stopped. Privatepy310 retaineduntilCI.
IsolatedWriter24 fixture moved with fullhash/mtime/symlink verification into
/dev/shm/asset-aware-docx-notes-lo24; original/run path is a symlink. Official
archiveSHAbe967ebc63cb15b831b4e8176492e83eb625dc00852eb96eda2b299b6e74bb74;
downloadedarchive removed after verification, rendered evidence retained.
Proof /run/user/1000/asset-aware-docx-notes-remap-validation.json. Thisruntime7file
segment plus2MEM precedes separate2fileactualaudit and20filedocs/harness segments.
Then pushmain and verify all10CI jobs,3Pages jobs,sixlivefiles. Broadgoal active.
Public1.4.0,nextconsolidated1.4.1; no version/tag/modeloverride/subagents/PR.
Original dirty detached checkout untouched; authoru9401066@gap.kmu.edu.tw.

## Native Word notes documentation — ready for publication

Runtime c074858 and actual-agent audit37a513d are committed under u9401066.
This20-file documentation/harness segment updates bilingual README, CHANGELOG,
ROADMAP, native operation/evaluation guides, generated website and five original/
bundled assistant asset pairs. Final generated-docs25pass/0.15s, harness audit,
asset sync and diff checks pass. Browser8desktop/mobile zh/en states passed with
actual desktopzh/mobileen inspected; owned server8885 stopped. Docker/wheel replay
same16notes/3catalogs/2Wikis at final sourcee5294369; all11staged runs restored,
owned Docker image/builder removed. Public1.4.0,next consolidated1.4.1, no tag/bump.
Pushmain next, then exact-head all CI/Pages jobs and six live-file byte comparisons.
Publication proof will be /tmp/asset-aware-docx-notes-publication-proof.json.
Privatepy310 environment stays until CI completes. Original failures are retained.
Broader all-format goal active; original dirty detached checkout untouched.

## Native Word notes — actual Codex audit and installed replay

Runtime/spec/tests committed as c074858 under u9401066,27counted files plus2MEM.
This separate6-file segment adds the opt-in default-model Codex runner, complete
trace/record/native/render/Wiki auditor,18negative audit regressions and installed
runtime replay without test imports. Final153successful calls+1recovered contract
input error/204.28s, earlier149+1/223.72s are both retained; no model override.
Ordinary pytest never starts a model. All production/full-suite/wheel/Docker checks
remain as recorded below; final production e5294369 unchanged. Docs/harness segment
and exact-head remote verification remain. Public1.4.0,next consolidated1.4.1.

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

## Workbook renditions — verified locally, publication pending

Implemented create_workbook_rendition/read_rendition with explicit mode/calculation,
exact source revisions, immutable PDF receipts, native page images and portable
Wiki conversion source attachments. Source XLSX is never resaved or advanced.
Real private Calc7.3.7 SDK2 test passed10.83s across four policies, actual PNGs,
blank/hidden/print scopes and cached999/recalculated3. Official current Calc config
and importer still use OOXMLRecalcMode0/1; cache preference can still recalculate.

Actual default-model Codex232 successful MCP calls/0 errors/184.70s,11 PNGs,
three PDFs and two workbook revisions; independent audit passes after strengthening
complete receipts, unchanged parts and all PDF verifications. Evidence:
/dev/shm/asset-aware-codex-workbook-rendition-01. Agent identified top/right text
clipping in whole-sheet output; no claimed correction or Excel fidelity verdict.
Next functional gap is explicit column width/row height control and Agent rerender.

Source SHA81defa2d1206e24186100a03b57cb872c962316ba05cc313b6ef58c3d67830ef
matches actual Codex, wheel and Docker311ae04c4a863880308e4c924d31e10cb5b3d235eb3a0a4a17867a8a4285c709.
Ruff570/mypy250/Bandit/locked audit214zero/npmzero/zizmorhigh passed.
Extension199/package64/install-update, clean wheel and Docker import/doctor/list/
SDK2 smoke passed. No local activation without display. Browser plugin unavailable;
Playwright zh/en desktop/mobile terms, navigation, nooverflow/console gates passed.
Mobile-zh screenshot inspected. Fullpytest01:2890passed34skipped105.42s; final
fullpytest02 passed2896/34skipped103.89s, including Wiki provenance/audit regressions.
Metadata/labels synchronized. README/wiki/site/harness updated; public1.4.0 with
all development Unreleased/future1.4.x, no tag/bump. All11 staged owned completed
runs fully restored with exact hashes/mtimes; only own obsolete builder/runtime
removed, current Docker and real-Codex evidence retained. Original dirty detached
user worktree unchanged. Scoped source/docs commits and CI/Pages proof pending.
Overall cross-format CRUD/evidence/real-Codex goal stays active.

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

Core Table editing is committed as642e3b2 (23 counted files plus5 MEM). The second
scoped commit contains README/changelog, bilingual site/Wiki and synchronized
assistant assets. Final local proof: /tmp/asset-aware-table-edit-local-proof.json.
All local gates and final Codex03 passed; exact CI/Pages checks follow push.
Public remains1.4.0 / Unreleased1.4.x; the overall goal remains active.

## Native Table column editing — final local verification passed

Final source SHA07e8fcbe8627f93cded1a89af22dbd2423b203f210ba792bd3f3dd13e360edcc
matches actual Codex03, built wheel03 and Docker9175c4e212dd. Actual03 completed
66successfulcalls/zeroerrors/132.75sec; one real MCP scan PNG, ten exact strings,
rich header rename, calculated/totals edits, complete original/current references,
original before-formula receipts, historical Count/007 and two Wikis independently
verified. No Excel rendering or formula evaluation claim; supplied Table template.
Final pytest05:2716passed33skipped99.21sec. Ruff531files, mypy237sources, Bandit,
lock/security/workflow audits, extension199tests/VSIXinstall-update, artifact/wheel/
Dockerstdio, 18skills/assets, metadata/labels and zh/en desktop/mobile browser pass.
No local VSIX activation (no display/Xvfb). Final site statistics/navigation/version
terms and console checks passed after moving browser temp storage to private SHM;
the preceding run reported ERR_INSUFFICIENT_RESOURCES and is not counted as passing.

The full combined reference+receipt16MiB budget is checked before CAS. Receipt
before values come from original package cells, not renamed intermediate formulas.
Regression reproduced the old receipt defect; strengthened audit rejects actual02.
Earlier audit reports are retained as audit.before-receipt-check.json. Actual01 also
needed the schema allowlist correction. Only actual03 proves the final source.
pytest02exit120 came from temporary Docker disk pressure;03 caught a Wiki-link
suffix, both corrected. Removed only completed own builder/runtime/pytest artifacts.
Keep final Docker, actual evidence and original detached user worktree intact.

Next: source/docs scoped main commits and push, exact CI/Pages/public validation.
Public stays1.4.0 / Unreleased1.4.x. Native Table object creation, totals-row lifecycle,
surviving-axis moves and broader cross-format real-corpus/fidelity remain open.
The overall goal is active; this is a Table editing milestone.

## 2026-09-19 — native Table column editing

Previous turn only reconfirmed version policy (no feature progress). Revalidated
clean main/origin at 0d0e65b. Table expansion publication completed: CI35413821293
all10 jobs, Pages35413820003 all3, five public files byte-identical; proof retained
at /tmp/asset-aware-table-expansion-publication-proof.json. Older pending entries
below are historical. Original detached user worktree stays untouched.

Doing: specialized Table column/header, scalar calculated-column and existing
totals editing, with exact metadata/cell/reference correspondence and preserved
formatting. Spec precedes code. Add regressions, SDK2 and actual Codex evidence.
Public remains 1.4.0; all new work is Unreleased/future 1.4.x, no task-based bump.
The broad cross-format CRUD/fidelity/evidence/real-corpus goal remains active.

Core native Table expansion committed as b4e797e; the accompanying documentation,
bilingual site and synchronized assistant assets form the next scoped commit. All
local checks and actual Codex proof passed; push and exact CI/Pages checks follow.
Public remains 1.4.0 / Unreleased for 1.4.x; overall goal is active.

Final verification: pytest04 passed **2678 tests,33 skipped in96.90sec**;
Docker import/doctor/list/stdio and clean wheel02 installation/runtime/stdio passed.
GitHub metadata/managed labels and all artifact gates passed. Local proof:
/tmp/asset-aware-table-expansion-local-proof.json. Exact CI/Pages/public proof still
awaits the scoped commits/push; overall goal remains active.

## 2026-09-19 — native Table expansion verified by actual Codex, publication pending

Public remains 1.4.0 / Unreleased within 1.4.x; no new tag or version-file changes.
Base main/origin is 3e9d6ee. Original detached user worktree remains untouched.
Per-step expand_tables uses exact active table part and expected_ref, supports
first/last data and left/right column boundaries, extends before totals, retains
column IDs and generates unique headers/calculated cells. Table filters and sort
extents include inserted data; sort keys retain their original column identity.
Mapped/pivot schema guards remain. read_workbook.tables exposes complete parsed
XML, raw part hash and attributes/column identities, including non-UTF-8 definitions.
A2T native_generated null intent resolves only new generated native Table cells;
missing/blank still mean blank, existing-cell/independent-export misuse rejects.
Final generated coordinates survive sequential grid changes; receipts expose values.

Actual Codex /tmp/asset-aware-codex-table-expansion-01 completed82 successful calls,
zeroerrors,150.48sec and one actual scan PNG. It filled10 literal data cells into a
supplied six-column native Inventory template, then A2T changed007 to008 and added
one row/column with generated F4 formula and G1 Column7. Final A1:G4 membership,
20 literal strings/types, formulas, column IDs, complete original/baseline/current
reads, frozen/live A2T, historical007 proof, sourcePDF/XLSX bytes/mtimes and two
native Wikis pass independent audit. Template creation is not MCP table creation;
Excel rendering/recalculated results remain unverified. Runtime source hash
 dda6223ec8f8f23d82cf1fd7deccfabb44e73252a1f2f103c1bb1690180cb3c6
matches the current checkout and built wheel code. Lock hash unchanged.

Full pytest02 passed2667/33skipped;11 later audit regressions passed. Final full
pytest04 is running after disk pressure interrupted pytest03 (exit120). Docker
built4e7328a73a86; initial import also hit full disk. Removed only own completed
builder8ab950ae332c and old completed smoke288e73dc, retaining current runtime and
actual-Codex evidence. Docker import/doctor/list/stdio now pass. Wheel02 clean install
and runtime/stdio pass using private SHM with pip cache disabled; wheel01 exit120 is
not counted. Own completed pytest01/02/03 fixtures removed; logs retained.

Ruff518files, mypy232sources, Bandit, lock/Python/npm/workflow audits, docs/harness/
18skills/assets, extension tests/package/install-update and metadata checks pass.
No local VSIX activation (no display/Xvfb). Browser plugin unavailable; Playwright
fallback passed zh/en desktop/mobile terms, navigation, overflow and console gates;
/tmp/table-expansion-{desktop,mobile}-{zh,en}.png inspected desktop-en/mobile-zh.
README/zh, Wiki, spec, changelog, bilingual site and bundled harness updated.
Next: final suite result, artifact/metadata-label proof, scoped source/docs commits
with MEM, push main and exact CI/Pages/public-byte verification. Specialized Table
header/calculated/totals edits, native moves and broader cross-format real-corpus
coverage remain open. Whole goal stays active.

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
