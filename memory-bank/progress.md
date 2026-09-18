# Progress (Updated: 2026-09-18)

## 2026-09-18 active goal — not complete

- [x] Native PDF page collaboration implemented and locally verified: create/read/
  render/copy/insert/delete/reorder/geometry, source lineage, immutable evidence,
  wiki and explicit source writeback. 1,739 Python tests pass / 30 optional skips.
  SDK2 and Codex scanned run 02 pass all seven independent checks (49 MCP calls,
  zero errors; exact final transcription). No new version: public 1.4.0 / Unreleased.
- [ ] Native PDF checkpoint commit/push and exact CI/Pages verification pending.

- [x] Unreleased checkpoint: native PPTX textbox addition / existing shape deletion
  with reference, dependency, version and XML preservation guards; truthful A2T
  row-ID results after earlier-row deletion. 1,647 Python tests / 199 extension
  tests pass. Real SDK2 CRUD/writeback and scanned Codex run (49 calls, nine checks)
  pass; first transcription errors were corrected and retained in evidence.
  Docs/README/harness/assets/Pages sources synchronized, public version stays 1.4.0.
  Exact commit ab49252 CI 35342913394 and Pages 35342912718 passed.
- [ ] Broader structural CRUD remains: slide manipulation, non-text creation,
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
