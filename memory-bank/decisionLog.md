# Decision Log

## 2026-09-18 — editable native tables and typed citation display

Create DrawingML tables from explicit grid/cell/merge input using scratch python-pptx;
apply the destination tableStyles default GUID, and compare readback to input plus
preserve package/XML outside additions. Covered cells must be empty/default so merge
operations cannot discard caller content. Existing native shape CRUD/evidence applies.
Actual Codex run 01 exposed citation_contract as an underspecified object. Advertise
preset/custom format models and keep source proof objects separate; valid JSON remains
accepted. Preserve first-run recovery evidence and rerun actual MCP with current schema.
No minor-version increase: public 1.4.0, work remains Unreleased for 1.4.x.


## 2026-09-18 — native picture assets preserve exact image bytes

Add four bounded PPTX picture operations and native-file-ref-v1. Use python-pptx
only for new scratch picture nodes; preserve original package parts and modify
only intended XML/relationships. Replacement adds new media rather than overwriting
shared media. Extracted images retain source shape/media lineage. PNG preview scope
is embedded raster only. Complete slide semantics/rendering remains Agent work.
Keep published version 1.4.0 and collect this work under Unreleased for 1.4.x.


## 2026-09-18 — Native PDF object-preserving page operations, bounded worker and version pacing

Keep public 1.4.0 and accumulate Unreleased for 1.4.x. Adopt pikepdf 10.13.0.post1
(public form-aware copy API) behind a domain port; PyMuPDF remains an independent
reader/renderer. Do not flatten PDF pages or promise arbitrary text editing. Preserve
page object identity when reordering; page assignment can break destinations.
Cross-document copies require complete supported dependencies and source references.
Known copied annotation backreferences can be repaired deterministically from source
identity; pixel equality alone did not catch that upstream graph duplication.
Use bounded canonical graphs, page/form/document checks and immutable revisions.
Agent performs semantic/full-resolution/viewer review. Reuse private atomic MessagePack
worker handoff to bound partial/large outputs rather than a blocking pipe receive.
Official references: https://pikepdf.readthedocs.io/en/latest/topics/pages.html and
https://pikepdf.readthedocs.io/en/latest/topics/interactive_forms.html.
Real Codex scan evaluation after final runtime changes passes seven independent
checks; preserve run 01 and 02 evidence and their exact runtime/lock hashes.

## 2026-09-18 — bounded native PPTX shape operations and truthful row results

Keep published version 1.4.0 and accumulate Unreleased on main for 1.4.x. Shape
creation reuses public python-pptx only to generate new nodes; existing packages
are edited through scoped lxml overlays. Preserve group transforms and reject
zero extents instead of silently recalculating old geometry. Shape deletion uses
full current-revision evidence, rejects known surviving dependencies and retains
relationships/media. Reversal-based XML comparison bounds what changed; neither
it nor package reopening proves full visual fidelity or opaque dependency safety.
MCP performs necessary mechanical checks; the agent completes semantic/visual
review and corrections. Existing shape-v1 evidence digest semantics remain stable.
A2T responses must report the resolved stable row identity; input row indices are
not reliable labels when an explicit row ID takes precedence.

## 2026-09-18 — canonical A2T citation readback without conflating verification

Live Codex PDF testing could inspect only citation counts/labels even though full
locators were persisted. Add table_cite read, preserving existing get summaries.
The canonical record binds table/row/column, current value and complete stored
CellCitation. It omits mutable row indices, allowing stable row-ID reads across
unrelated deletions. Hash-pinned continuation rejects content or scope mismatch.
Pages are transport fragments; full quotes and locators are never replaced by
previews. Cap encoded responses and complete UTF-8 representations (16 MiB).
Hash equality checks stored content, not authenticity, source validity or meaning.
Agent review and source verification remain separate. SDK2 and live Codex audits
must independently reconstruct actual delivered refs and compare final state;
historical evaluation runs retain their original check coverage. Keep this work
unreleased on main in the 1.4.x sequence, without another immediate version bump.

## 2026-09-18 — user-directed 1.4.x release sequence

The user explicitly said not to jump versions so quickly and requested 1.4.x.
Use **1.4.0** for this milestone, with 1.4.x for subsequent small fixes. This
supersedes the previous 2.0.0 proposal, which reached main only as preparation at
929e878; no 2.0.0 tag or package was published. Do not infer another major bump
from an internal contract version. Native-contract-v2 still changes the discovery
response, so preserve explicit schema_delivery/for_op/schema_request migration
instructions. Existing document inputs and evidence snapshots remain compatible.
The full release/artifact checks still apply; SDK 2.x is a separate dependency
version and remains unchanged.


## 2026-09-18 — PDF assembly should preserve document references deliberately

- Rechecked pikepdf's official page-assembly documentation:
  https://pikepdf.readthedocs.io/en/latest/topics/pages.html.
  Copying page data does not automatically transfer whole-document bookmarks or
  metadata. Replacing/copying page objects can break indirect references; documented
  emplace and remove/reinsert operations preserve different identity guarantees.
  Future native PDF contracts need explicit page mapping, link/bookmark/metadata
  handling and check coverage, not just a successfully saved output file.
- pypdf's official merge documentation describes importing relevant named
  destinations and controlled append/merge operations:
  https://pypdf.readthedocs.io/en/stable/user/merging-pdfs.html.
  Evaluate these with representative linked/bookmarked/form PDFs before selecting
  an adapter. No new PDF dependency was added for the presentation milestone.


## 2026-09-18 — precise native PPTX edits and evidence projection

- Reuse python-pptx for independent creation, then edit existing DrawingML a:t
  nodes through bounded OOXML packages. Whole shape/text-frame assignment clears
  runs per upstream documentation; do not use it for preserving existing formats.
- Resolve slide identity through relationships; locate slide/notes shapes by native
  IDs and retain group ancestry/local transforms. Regular run indices exclude
  fields and break nodes. Never infer inherited formatting or world-space bounds.
- Require both managed revision CAS and source-run hashes. Reopen updated bytes,
  restore requested text nodes in memory and compare canonical XML, while package
  replacement preserves all untouched member bytes. This proves the declared
  mechanical scope; the agent still reviews semantics, rendering and overflow.
- Use a new pptx-shapes-v1 wiki projection and attach every exact package member.
  Unknown features remain available in source/XML/relationships. Old opaque PPTX
  snapshots are separate; golden v1.2 XLSX and v1.3 DOCX output hashes remain stable.
  PPTX source references are revision-scoped and distinct from PDF/Word/cell refs.
- Official references: https://python-pptx.readthedocs.io/en/latest/user/text.html,
  https://python-pptx.readthedocs.io/en/latest/user/understanding-shapes.html,
  https://learn.microsoft.com/en-us/office/open-xml/presentation/structure-of-a-presentationml-document.


## 2026-09-18 — asset workflow value and scalable operation discovery

- User confirms MCP owns necessary checks and operation evidence; the agent owns
  full semantic/rendered review and correction. A parser wrapper or MCP transport
  alone is not sufficient differentiation: Docling already supplies both structured
  parsing and MCP integration (official repository rechecked). Reuse parser and PDF
  manipulation libraries rather than duplicating their engines.
- Product value must be demonstrated with repeatable workflows: exact source and
  revision references, bounded component access, preservation of untouched content,
  explicit writeback/divergence handling and reusable wiki evidence. Measure these
  outcomes against direct model workflows and existing parsers on the same fixtures;
  avoid claiming inherently better extraction or automatic semantic correctness.
- `native-contract-v2` explicitly migrates discovery to selected-operation schemas
  and hash-pinned JSON pages. Share runtime required/optional field rules; retain
  complete validation keywords and transitive definitions. Keep normal response
  caps, including JSON escaping, instead of raising limits with each new format.
  The complete SDK input schema and existing operation payloads remain available.


## 2026-09-18 — parsed DOCX evidence and distinct wiki projections

- Reuse complete DocxIR serialization; canonical block hashes never use truncated
  previews. A reference binds asset ID, immutable revision, native part and block
  ID. Successful integrity verification does not claim exhaustive extraction or
  semantic support. Old revision references survive updates and archive.
- Add docx-blocks-v1 to DOCX snapshot identity rather than replacing v1.2 opaque
  exports. Keep legacy XLSX/XLSM projection serialization byte-identical. Export
  every original package part with exact bytes and original-path/hash mapping;
  parser temporary media names cannot establish reliable chart/image associations.
- Upstream roles rechecked against official repositories:
  [Docling](https://github.com/docling-project/docling) provides structured parsing
  and a common document representation; [pdfplumber](https://github.com/jsvine/pdfplumber)
  exposes characters/geometry/table extraction; [pikepdf](https://github.com/pikepdf/pikepdf)
  provides QPDF-backed read/write; [pypdf](https://github.com/py-pdf/pypdf) provides
  page split/merge/crop/transformation. Reuse these capabilities where appropriate;
  asset identity, revisions, source checks and evidence publication remain project
  responsibilities. No new dependency is introduced in the DOCX evidence milestone.


## 2026-09-18 — reuse the DFM write path for native DOCX

- Avoid a second Word editing implementation. Native revisions supply immutable
  bytes to the existing DocxService session/checksum, pre/post-save and unedited
  block guards. The workspace adapter adds package inventory/byte preservation.
- Expose deterministic bounded DFM reads with full native identity/revision
  binding. Removing only the derived session creation timestamp permits stable
  chunk assembly across stateless reads. Native edits preserve every marker and
  its order; document-level style/structural changes remain unsupported explicitly.
- Native edits create managed versions before source writeback; existing CAS,
  backup and divergence semantics apply. The latest user clarification governs:
  MCP performs necessary mechanical checks, while agents own full semantic and
  rendered review and subsequent correction. No structural pass implies fidelity.


## 2026-09-18 — academic citation processor evaluation

- Keep canonical asset references independent of citation presentation. Standards
  need ordered document-level citation clusters, a bibliography, explicit CSL
  metadata/style/locale and repeatable engine/version hashes. Formatting each
  evidence record independently cannot implement context-dependent disambiguation.
- Primary sources checked: [CSL developer guide](https://citationstyles.org/developers/),
  [citeproc-py](https://github.com/citeproc-py/citeproc-py),
  [citeproc-js API](https://citeproc-js.readthedocs.io/en/latest/running.html),
  [citeproc-js license](https://github.com/Juris-M/citeproc-js/blob/master/LICENSE),
  and [jgm/citeproc](https://github.com/jgm/citeproc).
- citeproc-py's documented gaps include disambiguation/year-suffix, subsequent
  et-al, collapsing, punctuation-in-quote and display. It is not accepted as a
  complete APA/Chicago engine merely because it consumes CSL. citeproc-js has a
  CPAL/AGPL license and production use requires processCitationCluster rather than
  context-free makeCitationCluster. jgm/citeproc is a BSD Haskell implementation
  with a JSON executable option; it also documents conformance limitations.
- No dependency selected/installed in 1.2.0. Evaluate same-author/year suffixes,
  reordered/deleted citations, numeric order, note styles, locale and missing
  metadata before adding a backend. Keep external conversion separate from native
  format-preserving editing; Pandoc conversion is not a fidelity guarantee.


| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-09-18 | **PDF bundle refresh must prove unchanged generated content and retain replaced trees** | A matching manifest marker did not protect human edits. Publication now validates complete inventory/hashes, rechecks the observed version under an OS lock, reuses identical output and retains real replacement backups. Keeping old inodes also preserves late writes from already-open external editor handles. Publication IO is moved behind a domain port into infrastructure. |
| 2026-09-18 | **Native evidence notes are immutable revision snapshots** | Pin links to asset/revision/native locator so updates cannot silently change cited evidence. Repeat exports verify exact inventory and bytes; preserve manual edits and unknown files by rejecting replacement. New revision snapshots leave curated sibling notes untouched. A manifest-last completion marker and retained partial-output report avoid promising atomic directory visibility across platforms. Citation presentation changes use a separate wiki root in this first implementation. |
| 2026-09-18 | **Native edits preserve package members and expose review boundaries** | Use XlsxWriter for new package structure and scoped XML operations for typed values. Reopen and compare saved cells; leave unrelated members byte-identical. Semantic/rendered/formula review remains agent-owned. Regression coverage now supports separating native readers, edit guards, repair plans and file publication into focused modules before the first checkpoint. |
| 2026-08-13 | **A document timeout covers fallback work, not only the first extractor** | Killing a rich-text worker and then running unbounded `pdftotext` or PyMuPDF in the parent made the advertised timeout ineffective. Text extraction now owns one absolute deadline; timeout fails closed and only an early non-timeout error may spend the remaining budget in another isolated worker. |
| 2026-08-13 | **Global agent config never trusts workspace-local launch material** | A lookalike repository could satisfy the old source heuristic and persist its Python module or `.env` values into global Codex/Cline settings. Automatic external-consumer config now requires workspace trust, always pins the published extension version with globalStorage cwd/data/cache, and permits local source only in trusted Development/Test contexts or a future explicit opt-in. |
| 2026-08-13 | **Public evidence previews and persisted AssetRefs are separate contracts** | Canonical refs need the complete exact quote, hash and locator, but embedding multi-megabyte quotes in MCP responses defeats response caps. Persisted citation/agent-asset bundles keep canonical refs; public long-span surfaces emit bounded `asset-ref-preview-v1` objects without canonical locators, and verification rejects previews or incomplete canonical refs fail closed. |
| 2026-08-13 | **The product site is code-native, generated and browser-gated** | Raster diagrams had frozen v0.6 metrics and private development topology. The replacement landing uses HTML/CSS/SVG for the Evidence Rail, reads runtime stats from the docs generator, links every path back to GitHub, and shares canonical wiki content with the reader. Desktop/mobile visual QA plus real route/search/language/copy/menu tests prevent a syntactically valid but unusable release. |
| 2026-08-13 | **Codex config ownership is field-level; user policy survives managed lifecycle** | Treating every `mcp_servers.asset-aware-mcp.*` table as extension-owned silently deleted per-tool approval policy. The extension now owns only launch/env fields, byte-preserves primary policy/future assignments and nested tool tables, and keeps an `enabled=false` non-executable transport shell during opt-out only when Codex needs it to parse retained policy. |
| 2026-08-13 | **PDF worker results use bounded streaming MessagePack in private atomic files** | Large image/table payloads can deadlock multiprocessing pipes, while pickle is executable deserialization. A 0700/0600 no-follow file boundary with an aggregate cap, strict envelope validation and atomic publication supports multi-megabyte assets without pipe backpressure and fails closed on partial/crashed output. |
| 2026-08-13 | **Extension-managed Codex config is semantic, marker-owned and least-privilege** | Hand-written TOML regexes can delete commented unrelated tables or duplicate quoted keys. Only an exact managed marker grants ownership; valid custom TOML is preserved, invalid/ambiguous/symlinked config fails closed, secrets are not serialized, and the managed server uses an isolated cwd with implicit dotenv disabled. |
| 2026-08-13 | **MCP SDK 2 Context is for progress, not protocol logging** | SDK protocol logging is deprecated and can emit warnings during real stdio operation. Python logging on stderr keeps JSON-RPC stdout clean while runtime-injected Context continues to provide bounded progress notifications without leaking `ctx` into tool schemas. |
| 2026-08-13 | **Span AssetRefs preserve an exact self-verifying quote** | Truncating a 2,198-character quote while retaining the full-span SHA-256 and char/byte locator made the exported reference unverifiable. Presentation responses may be bounded separately, but a reusable citation AssetRef must keep quote, hash and locator scoped to the same evidence bytes. |
| 2026-08-13 | **Publish v1 only from a green annotated tag, then verify immutable bytes across registries** | `scripts/release.sh --push-tag` requires clean `main==origin/main`, complete local gates and no version/tag collision before pushing. The tag workflow independently tests and builds, publishes PyPI through OIDC, waits for public installability before Marketplace, and creates GitHub Release last. Public wheel/sdist hashes matched the tag-first build; Marketplace CDN, Marketplace metadata and GitHub Release VSIX hashes matched each other. |
| 2026-08-13 | **Protect `main` with the fail-closed aggregate gate and review/history rules** | Individual jobs can change as the matrix evolves, while `📋 Test Summary` owns the complete needs graph and exits nonzero when any required job fails. Making it strict and required, plus one approval, stale-review dismissal, resolved conversations, linear history, and force-push/deletion bans, turns the refreshed CI into an enforceable merge gate. |
| 2026-08-13 | **Preserve the v0.2.0 draft after exact inspection found unique history** | Initial inventory called it dangling, but the destructive-action precheck found an existing `v0.2.0` git tag and a unique historical VSIX asset. Deleting the draft would discard provenance for cosmetic cleanup, so it remains untouched; the v1 release is independently current/latest. |
| 2026-08-13 | **Convergence preserves semantics, not obsolete SHAs** | PR #3/#4/#5/#8 were empty, stale, conflicted or superseded by stricter code on v0.9.0, so hard-merging them would regress the repository. Twelve branches were already absorbed/superseded; the one backup branch was mined for still-valid behavior and regression tests before retirement. This leaves one coherent default branch without discarding unique useful work. |
| 2026-08-13 | **Rename the repository default branch atomically from `master` to `main` only after release gates** | The user explicitly requested convergence to `main`, while the repository still used `master`. Updating workflow triggers, badges, docs and scripts first, then pushing `main`, switching GitHub's default and deleting `master`, prevents a split-brain period or missed CI/Pages runs. |
| 2026-08-13 | **Fast-forward the stale local 0.6.3 checkout to the published 0.9.0 repository baseline before new development** | `origin/master`, tag `v0.9.0`, PyPI 0.9.0, and its hash-verified sdist all resolve to the newer production line. Developing from the stale checkout would duplicate and lose already-published citation, readiness, multi-engine, website, harness, and VSIX work. The pre-sync worktree remains recoverable in a named stash; only intentional Memory Bank state is replayed. |
| 2026-08-13 | **MCP Python SDK 2.0 is a hard runtime floor; SDK v1 compatibility is removed** | The user explicitly requested MCP 2.0+ without past compatibility, and official v2 is stable. The dependency becomes `mcp>=2,<3`; code uses `MCPServer`, snake_case protocol fields, and v2 client/testing APIs. Migration guidance replaces a dual SDK runtime path, making this a breaking release. |
| 2026-08-13 | **Use pdf-inspector's classification ideas behind an internal preflight boundary, but do not ship PyPI 1.14.1** | The pinned upstream main contains content-stream/CID/Form expansion limits that the published 1.14.1 artifact does not. The local preflight contract adopts page classification, OCR reasons and routing while adding process/file/page/layout/memory/source-change guards; it does not claim to sanitize or certify hostile PDFs. A future upstream version can replace the inspector behind the interface after contract and hardening verification. |
| 2026-08-13 | **Agent assets are immutable, deterministic evidence records with Foam as a portable view** | Agents need reusable units rather than another prose report. `document(op="export_assets")` therefore emits stable IDs, source and record hashes, exact locators/citations, JSONL/media and a Foam subtree using staged document-scoped replacement. The first repository adapter is PDF-backed; future DOCX/general implementations must preserve the same provenance contract instead of fabricating locator parity. |
| 2026-08-13 | **MinerU and Marker remain adapter-only security holds** | MinerU 3.4.4 caps `transformers<5` while applicable fixes require `>=5.5`; Marker caps Pillow below the project's patched floor. Empty extras keep public capability names stable without installing known-vulnerable chains. Production structured extraction uses PyMuPDF4LLM or Docling until upstream constraints are removed and re-audited. |
| 2026-05-15 | **`Install LightRAG Backend` is launch-mode-aware (source vs published)** | The extension launches the MCP server in two modes: `uv run --directory <repo> python -m src.server` when a local source checkout is detected, otherwise `uvx ...` against `uv tool` env. The original `installOptionalExtra` always emitted `uv tool install`, which is wrong for source-mode users — the install lands in the `uv tool` env while the running server uses the workspace `.venv`. Fix: import `findLocalAssetAwareSource` from `mcpConfigCommon` and branch — local source → `uv sync --extra <extra>` (cwd = source root); else → `uv tool install --upgrade --python 3.11 'asset-aware-mcp[<extra>]==<version>'`. Confirmation modal shows the detected mode so users see what env will be modified. |
| 2026-05-15 | **`lightrag-hku` moved to `[lightrag]` optional extra; `mistralai` removed** | Default install was ~1190 MB largely from past marker-pdf + torch + transformers + surya-ocr leftovers and lightrag transitive deps (pandas/numpy/tiktoken/google-genai). LightRAG is already opt-in (`enable_lightrag=false` default) and protected by try/except + `_HAS_LIGHTRAG` flag, so making it an extra is non-breaking. `mistralai` had zero usages in src/tests/scripts. Result: slim default install ~227 MB; KG users opt in via `uv tool install --upgrade 'asset-aware-mcp[lightrag]'` or the new VS Code command. |
| 2026-05-15 | **Optional extras get first-class VS Code install commands** | After moving LightRAG to an extra, users need a discoverable path to add it back. Two commands were added — `Install LightRAG Backend (optional)` opens a terminal and runs the pinned `uv tool install`; `Install Marker Backend (optional)` shows the security-hold modal with upstream tracker + Pillow CVE links rather than silently failing. Keeps install paths transparent and auditable. |
| 2026-05-07 | **Cline MCP managed entry merge is non-destructive and launch-shape gated** | Cline users may already have a same-name `asset-aware-mcp` server that is custom or belongs to another workspace. The installer and VS Code extension may update only entries that match the managed Asset-Aware launch shape; they must preserve `alwaysAllow`, `disabled`, custom env, and unrelated servers, and back up malformed Cline settings before writing. |
| 2026-04-29 | **Asset-Aware 對齊 MedPaper/Foam 時只擔任 decomposition / locator authority，不直接寫 Foam notes** | MedPaper 已擁有 LLM wiki/Foam materialization、wikilink、dashboard 與 graph-health 邏輯；若 Asset-Aware 也寫 Foam notes 會造成重複責任與路徑衝突。Asset-Aware 應輸出穩定 `doc_id`/`block_id`/`span_id`、`source_revision_id`、hash、char/byte/page/bbox locator、context、CRAAP scaffold 與 DFM revision sidecar，讓 MedPaper 可驗證 promotion。 |
| 2026-04-29 | **VSIX assistant harness 同步採 manifest-based non-destructive update** | Extension 啟動自動同步 harness assets 是好體驗，但直接覆蓋 `.cline/skills`、`.codex/skills`、`.clinerules` 或 Copilot/Codex instructions 會吃掉使用者客製化。新增 workspace manifest 後，只有目前內容仍符合上次 extension 寫入 hash 的檔案才會更新；同路徑被使用者改過就 preserve。 |
| 2026-04-29 | **外部 MCP config 讀取/解析失敗時 fail-closed，不用空白設定修復** | Copilot/Cline/Codex 設定可能含 custom server、comments 或手寫片段。若 malformed JSON/TOML 或 unreadable 時用空白基底寫回，等同把使用者設定移走。正確策略是備份/警告並跳過，待使用者修復後再 merge Asset-Aware entry。 |
| 2026-04-29 | **DFM→DOCX Track Changes 必須同時產生機器可驗證 sidecar** | Word 的 `w:del`/`w:ins` 讓人可審查，但 citation-ready / Foam promotion 需要穩定 `block_id`、old/new hash、char/byte range 與 context。`revisions.jsonl` 將人類可視修訂與 Asset-Aware locator contract 接起來，避免下游重新猜 diff。 |
| 2026-04-29 | **DFM→DOCX Track Changes emission 採 opt-in diff 寫入，不改變預設回寫語意** | 普通 `save_docx` 已是穩定的直接文字回寫路徑；若預設改成 `w:del`/`w:ins` 會影響既有驗證器、下游抽字與使用者預期。因此新增 `track_changes=True` 與 `revision_author`，只在使用者需要 Word 審查時比較原始 IR / edited IR 並產生原生 Track Changes，同時保留未啟用時的既有行為。 |
| 2026-04-29 | **Word Track Changes 在 DFM 中作為唯讀 `dfm:revision` review annotation，而不是正文 edit target** | 追蹤修訂是審查/ provenance 訊號，若讓 parser 把 `dfm:revision` 當正文回寫，會讓刪除文字、移動文字或格式修訂污染正常段落對位。將 revision block 設為 protected，並在 metadata 保存 `revision_id`、`source_tag`、`scope`、`source_block_id` 與 `visible_in_current_text`，可讓使用者與 agent 檢查修改來源，同時避免 DFM→DOCX round-trip 誤寫。 |
| 2026-04-24 | **已發布版本若揭露 CI-only defect，採下一個 patch 版本修正，不覆寫既有 PyPI/Marketplace artifact** | `v0.6.12` tagged release 已成功發布到 PyPI 與 VS Code Marketplace；同一版本 artifact 不應被重打或覆寫。Windows branch CI 揭露的是 package-content guard 的 subprocess portability defect，因此正確補救是發布 `v0.6.13` corrective release，保留不可變 artifact 歷史並讓最終新版指向全綠 commit。 |
| 2026-04-24 | **Release、CI、Cline harness 與 VSIX artifact 檢查必須共用可重跑的 audit scripts** | 發版風險主要來自各路徑 gate 不一致：local release 可過但 tag workflow 失敗，或 VSIX 內混入 compiled tests。將 Cline harness、Python artifacts、VSIX package contents、version sync 與 activation smoke 收斂到 script/CI/release workflow，可讓 MEM+GIT+PUSH+TAG 前後使用同一套 production-grade 檢查。 |
| 2026-04-14 | **Manifest title fallback 必須在 question-first PDF 時退回 filename，而不是吃正文第一行** | 真實麻醉科考題 PDF（例如 111 年）首頁可能直接以 `1.` 開始，下一行就是題幹。若 title fallback 只抓第一個「看起來有字」的行，會把題幹誤存成文件標題，進而污染 `list_documents` 與 downstream prompt。正確策略是先清理 heading markdown noise；若正文已開始，就退回檔名 stem。 |
| 2026-04-14 | **Manifest 必須顯式保存低文字品質診斷，讓 OCR 需求可被程式判斷** | 真實答案 PDF 可能只抽出極少且高度重複的文字，例如連續的 `本題送分`。若 manifest 沒有品質摘要，呼叫端只能誤以為文件正常 ingest。加入 `text_quality_status`、可視文字量、重複率與 `ocr_recommended`，才能在後續 workflow 中及早分流。 |

| Date | Decision | Rationale |
| 2026-03-23 | **LightRAG MCP 查詢預設改為 structured output，但保留 text/data 相容模式** | 這個 repo 的知識圖譜用途已從單純問答擴展到 citation-aware agent workflow。若繼續把 references 附加在純文字尾端，agent 需要再做 fragile parsing。改為預設回傳 `answer`、`references`、`metadata`、`retrieval`、`counts` 可直接支援引用與表格工作流；同時保留 `response_mode="text"` 和 `response_mode="data"`，降低對既有呼叫端的破壞性。 |
|------|----------|-----------|
| 2026-03-19 | **agent asset 能力擴展採分段發布，不做單一大版本合併** | gap 修補涉及不同風險面：格式入口擴展、表格原生化、agent 理解增強、非 flow-based 特殊格式。若一次合併發布，測試面與回歸面會互相干擾，難以判斷品質退化來源。按 Release A/B/C/D 分段，可讓每次發布只承擔單一能力面風險。 |
| 2026-03-18 | **section metadata 的最終真相必須在 manifest generator 收斂** | 如果 Marker ingest 先用 TOC + line index 算出 section，再由 `ManifestGenerator.generate()` 用另一套規則重建 sections，manifest、fetch、segmentation 會開始共享不同的 section 歸屬。改為讓 generator 接受預先計算好的 sections，並在 generator 階段統一回填 assets 的 `section_id` / `section_title`，可避免多重真相。 |
| 2026-03-18 | **line span 必須在 ETL 階段持久化，segmentation 只消費不回推** | 如果 line range 只存在於 segmentation export 的 runtime 回推邏輯，asset fetch、overlay、agent citation 都必須重複做猜測，且容易因重複句子而誤對位。將 block 與 asset 的 line span 在 ETL 當下寫進 `blocks.json` / manifest，才能讓 fetch、segmentation、resource 共用同一份定位真相。 |
| 2026-03-18 | **line span 對位採 page-aware + section-aware，並保留 legacy backfill** | 純全文順序比對對重複句子很脆弱。新版 line span index 先縮到 page，再縮到 section，可明顯降低誤對位；但現有舊資料沒有 metadata，所以在 `SegmentationService` 遇到舊 `blocks.json` 時允許自動 backfill 升級。 |
| 2026-03-18 | **layout asset 關聯要保留來源 block identity，不能只靠同頁順序猜測** | 同頁多 figure/table 時，單靠 page-based FIFO 很容易把 segmentation block 配到錯的 asset。將 `source_block_id` / `source_order` 存入 `FigureAsset` / `TableAsset`，再讓 segmentation 優先按 block 身分配對，才能穩定支援 overlay、caption 關聯與 citation。 |
| 2026-03-18 | **line number 內部維持 0-based / end-exclusive，但所有對外顯示改為 1-based** | `SectionAsset.start_line/end_line` 目前被 section extractor 與 slicing 邏輯用作 0-based / end-exclusive 索引。為避免打破內部語意，顯示層統一轉成 1-based，可同時修正第一段 `start_line=0` 被隱藏的問題。 |
| 2026-03-18 | **reading order 與 line-level citation 必須分離建模** | `reading_order` 回答的是閱讀流程與區塊排序，`line_start/end` 回答的是 markdown 引用定位。兩者不是同一個軸，若混在一起會導致 caption/table/footer 排序規則破壞精準行號引用，因此在 `DocumentSegment` 中同時保存兩套資訊。 |
| 2026-03-18 | **以 `segmentation.json` 作為統一 layout contract** | 現有 manifest 偏向資產摘要，`blocks.json` 偏向 Marker 原始結構。新增 `DocumentSegmentation` 將 manifest、blocks、assets、reading order 正規化，讓 MCP tool、resource 與 VS Code extension 都能用穩定結構消費，不必各自猜欄位。 |
| 2026-03-18 | **保存 `original.pdf` 並以 overlay 圖像做 layout debug** | 單看文字回傳仍然難知道 ETL 解析是否正確。將原始 PDF 與 segmentation 結合，產生 bbox/type/reading-order overlay，可直接檢查 Marker 或 PyMuPDF 的段落切分品質。 |
| 2026-03-18 | **OCR 採 on-demand 前處理而非全域預設啟用** | OCR 成本高、依賴額外系統工具，且不是所有 PDF 都需要。將 `ocr_enabled`、`ocr_language`、`rotate_pages`、`deskew` 暴露在 tool 參數層，保留預設快速路徑，同時支援掃描 PDF 的補救流程。 |
| 2026-03-18 | **`marker-pdf` 改為 optional extra，預設安裝不帶 torch** | `Marker` 是高精度但重量級的可選功能，會帶入 `torch` / `surya` 與平台相關 wheels，最容易造成安裝失敗。預設安裝改為只保留 PyMuPDF，可顯著降低 cross-platform 安裝摩擦；需要 `use_marker=True` 時再透過 `uv sync --extra marker` 或 extension 設定明確啟用。 |
| 2026-03-18 | **不收窄 package 的 Python 3.11+ 支援宣告，只固定 extension / installer runtime 為 Python 3.11** | 使用者要求保留 3.11+ 支援。真正的啟動問題不是專案邏輯不支援新版 Python，而是終端使用者機器在 `uvx` 自動選到 3.14 時，`marker-pdf -> regex` 依賴鏈可能觸發本機原生編譯。將 extension / installer 固定到 wheel 可用性最佳的 3.11，可同時保留專案相容性與跨平台穩定啟動。 |
| 2026-03-09 | **DOCX→PDF / DOCX→DOC 採保真模式，PDF→DOCX 採內容重建模式** | DOCX 來源具可逆結構，適合透過 LibreOffice 做 fidelity export；PDF ETL 不具版面可逆性，因此僅承諾可讀內容重建，不宣稱 layout fidelity。 |
| 2026-03-09 | **strict round-trip 採 fail-closed 策略** | 對生產級文件編輯流程，任何結構、文字、格式、表格、媒體、樣式差異都應明確視為失敗，避免只靠總分掩蓋回歸。 |
| 2026-03-09 | **save_docx 加入 unedited block mutation guard** | 真實 Proposal 文件測試證明 parser/render 流程若誤動未編輯區塊，必須立即中止寫回，避免 silent corruption。 |
| 2026-02-23 | **`.doc` 格式支援 — LibreOffice 自動轉換** | 使用者需要編輯舊版 `.doc` 檔案，DFM 僅支援 `.docx`。透過 `subprocess` 呼叫 LibreOffice headless 模式自動轉換，無需使用者手動操作。轉換後的 `.docx` 存於 tempdir 避免污染原始目錄。 |
| 2026-02-23 | **Markdown 跳脫機制 (`_escape_md` / `_unescape_md`)** | 文字內容含 `*`、`~`、`^` 字元時，Round-trip 會被 Markdown 格式標記干擾（如 `※**下列` 中的 `**`）。新增跳脫/反跳脫對稱方法，並合併相鄰同格式 runs 避免 `**A****B**` 問題。 |
| 2026-02-11 | DFM (Docx-Flavored Markdown) 格式設計 | Agent 無法直接看 docx，需要 Markdown 中間格式即時編輯。DFM 保留 block-level 與 run-level 格式資訊，支援完整往返 |
| 2026-02-11 | DocxIR 中間表示層 | docx → IR → DFM → edit → IR → docx 保證往返保真。IR 保留原始 preserved_parts、assets、styles、checksum |
| 2026-02-11 | DocxValidator 6 維度驗證 | Agent 看不到渲染結果，需程式化驗證。6 維度加權評分（text 0.35 最重）取代肉眼對比 |
| 2026-02-11 | DfmTableBridge 雙向橋接 | Docx 表格 → A2T 工作流（plan → draft → commit）→ Docx 表格，打通兩個子系統 |
| 2026-02-11 | Template-based rebuild (複製 original → 只改 document.xml) | 最大限度保留 media/styles/theme/fonts 等，非文字部分保真率極高 |
| 2026-02-10 | A2T 工具合併 19→7 (operation-based) | 減少工具總量 28%，降低 Agent 認知負擔，用 Literal type 統一入口 |
| 2026-02-10 | AssetRef 支援 7 種來源類型 | 做表 ≠ 拆解，表格應接受任意來源（PDF/KG/URL/口述） |
| 2026-02-10 | Citation 作為平行附加層 | 不改變 rows list[dict] 結構，用 dict[str, CellCitation] 側掛 |
| 2026-02-10 | ChangeEntry 自動審計 | 所有寫入操作自動記錄，支援 cell-level 歷史追溯 |
| 2026-02-10 | get_section_content 移至 section_tools | 語意上屬於 section 導航，不應在 table_tools |
| 2025-12-15 | 採用憲法-子法層級架構 | 類似 speckit 的規則層級，可擴展且清晰 |
| 2025-12-15 | DDD + DAL 獨立架構 | 業務邏輯與資料存取分離，提高可測試性 |
| 2025-12-15 | Skills 模組化拆分 | 單一職責，可組合使用，易於維護 |
| 2025-12-15 | Memory Bank 與操作綁定 | 確保專案記憶即時更新，不遺漏 |

---

## [2025-12-15] 採用憲法-子法層級架構

### 背景
需要一個清晰的規則層級系統，類似 speckit 但可擴展。

### 選項
1. 單一 copilot-instructions.md - 簡單但不夠靈活
2. 憲法 + 子法層級 - 清晰層級，可擴展
3. 全部放在 Skills 內 - 分散，難以管理

### 決定
採用選項 2：憲法-子法層級

### 理由
- 最高原則集中在 CONSTITUTION.md
- 細則可在 bylaws/ 擴展
- Skills 專注於操作程序
- 符合現實法律體系，易理解

### 影響
- 新增 CONSTITUTION.md
- 新增 .github/bylaws/ 目錄
- Skills 需引用相關法規
| 2025-12-26 | 使用 Ollama 作為預設 LLM 後端 | 1. 本地運行，無需 API Key 成本
2. 支援 qwen2.5:7b (LLM) 和 nomic-embed-text (Embedding)
3. 隱私保護，資料不離開本機
4. 仍保留 OpenAI 作為備選後端 |
| 2025-12-26 | Figure caption mapping 需要實作 - 目前 fig_{page}_{index} 命名未對應實際圖說 | 測試 Nobel Prize PDF 時發現 fig_2_1 實際對應 "Figure 1. Regulation of cell-type specific functions"，系統缺乏 caption 解析功能。未來版本應在 ETL 階段提取圖說文字，建立 asset_id 到 caption 的映射。 |
| 2025-12-26 | mcp-operator skill 必須明確警告：純文字 AI 無法分析 base64 圖片 | 測試時發現純文字 AI 會根據「標準知識」猜測圖片內容而非實際分析，導致錯誤答案。必須在 skill 中明確禁止這種行為，要求 agent 誠實告知使用者其視覺能力限制。 |
| 2026-01-05 | 升級 Node.js 環境至 v20 並完成 VS Code 擴充功能打包 | 原環境 Node.js v12 不支援現代 JavaScript 語法（如 ?? 運算子），導致 npm install 失敗。升級至 v20 後成功編譯並生成 .vsix 檔案，確保擴充功能可供安裝。 |
| 2026-01-05 | 全面對齊文件至 Docling-based Asset-Aware ETL 實作 | 專案已從初始的「Medical RAG」想法演進為具體的「Asset-Aware ETL」架構，使用 Docling 作為核心引擎。為了避免開發者與使用者混淆，必須將 README、Spec 與擴充功能說明全面更新，反映當前的 DDD 架構、非同步 Job 處理與 Manifest 優先的資料存取模式。 |
| 2026-01-05 | 捨棄 Docling 引擎，改以 PyMuPDF 作為核心 ETL 引擎 | Docling 雖然精度高但依賴過重（約 2GB，需 PyTorch/CUDA），不符合專案輕量化的需求。PyMuPDF (fitz) 速度快、體積小，且已實作表格與圖片提取功能，足以滿足當前 Asset-Aware ETL 的核心需求。 |
| 2026-01-12 | **🚨 架構重構：Asset-Centric Architecture** | 用戶反映三大功能存在耦合問題：(1) 做表被迫依賴 PDF 拆解、(2) 已存在的圖片需重新拆解、(3) 功能間互相影響。決定引入 AssetRegistry 作為資產索引中心，實現真正的功能獨立。詳見 `docs/ARCHITECTURE_REFACTOR_PROPOSAL.md`。 |
| 2026-02-03 | **Marker 整合到標準 ingest 流程** | 為支援精確來源追蹤（頁碼+bbox），將 Marker 整合到 `ingest_documents` tool 中。新增 `use_marker=True` 參數，可選擇：(1) PyMuPDF（預設、快速）或 (2) Marker（結構化、含 blocks.json）。Marker 採用 lazy-load 避免啟動延遲。研究 Unstructured.io (13.9k stars) 作為未來備選方案，但目前 Marker 已足夠。 |
| 2026-02-05 | **Section Navigation Tools (動態層級)** | 為支援任意深度的書籍章節結構，實作 SectionNode/SectionTree domain model 和 SectionService。新增 4 個 MCP tools: `list_section_tree`, `get_section_detail`, `get_section_blocks`, `search_sections`。不 hardcode 層級數，從 blocks.json 動態建構 section hierarchy。 |
| 2026-02-09 | **ETL Profile 設定模組化** | ETL 管線中大量硬編碼常數（字型閾值、heading noise patterns、caption patterns、section keywords 等），不同期刊格式需不同設定。決定採用「兩者並行」策略：Python dataclass 定義預設值 + JSON 檔案可覆蓋。`ETLProfile` 為 frozen dataclass（domain value object），`ETLProfileRegistry` 提供 5 個內建預設。DI 鏈：`dependencies.py` 建立共享 profile → `PyMuPDFExtractor(profile=)` + `ManifestGenerator(profile=)`。 |
| 2026-02-09 | **Marker ETL 規格書與缺陷修復** | 建立完整規格書 `docs/marker-etl-spec.md`，定義品質要求（QM/QF/QT/QI/QS/QB/QST/QMT/QE），修復 3 個實作缺陷：(1) Figure-Block 匹配 bug — 改為 index-based 1:1 匹配而非全部用第一個、(2) Table row/col 解析 — 從 markdown 表格文字解析實際行列數、(3) 圖片尺寸讀取 — 使用 PIL 取得實際 width/height。新增 89 個單元測試全部通過。 |
| 2026-07-08 | 採用可插拔多引擎 PDF→資產架構：ETL_ENGINE 環境變數選擇 pymupdf（預設）/pymupdf4llm/docling/mineru，並讓結構化引擎 Docling/MinerU 輸出 Marker-compatible MarkerParseResult | Marker 因 marker-pdf 1.10.2 pin Pillow<11 與安全基線 Pillow>=12.2.0 衝突而停用；三個替代引擎（pymupdf4llm/docling/mineru）皆以 uv pip compile 驗證解析 pillow==12.3.0 相容。讓結構化引擎輸出 MarkerParseResult 可零侵入復用既有 _ingest_single_with_marker 資產管線（最小改動）；保留 document_service 的 marker_extractor slot 名稱、僅將型別泛化為 StructuredPDFExtractor Protocol，維持既有測試與 API 相容（避免破壞性重命名）；所有結構化引擎全懶加載，未安裝時 import 不炸並自動降級為 PyMuPDF 快速引擎，確保基礎安裝零額外依賴。PyMuPDF4LLM 採 Tier 1 drop-in（繼承 PyMuPDFExtractor 只覆寫 extract_text）、Docling 為 Tier 2（MIT 授權）、MinerU 為 Tier 3 最高精度（CLI + subprocess 隔離避免 OOM）。 |

## 2026-09-18 — cross-format CRUD and evidence library

Authoritative baseline is origin/main e612d20, published 1.0.1. Original master
worktree remains at 0.9.0 with pre-existing user changes; do not reset it.
Worktree: /home/eric/workspace251226/asset-aware-mcp-agent-assets;
branch: feat/agent-asset-contracts.

The latest explicit user reply confirms: MCP provides necessary source/version,
format-preservation and operation-result checks; the agent owns complete semantic
and visual verification and coordinates corrections. This clarification overrides
the earlier complete-MCP-validation wording. Deterministic checks remain enforced
on every supported write; do not claim full fidelity from structural checks alone.
Full scope is tracked in docs/spec.md and ROADMAP.md; a milestone is not completion.

Next: implement versioned citation presentation contracts in existing evidence
and portable asset exports, then native capabilities/CRUD and inspectable operation results.
README/Pages/GitHub metadata/labels/MEM and staged commits/push/releases are
explicitly authorized. Full release gates remain required before tagging.

Domain owns pure contracts; application binds display to evidence; infrastructure
owns native format IO. Citation formatting never mutates source provenance.
# 2026-09-18 — real Codex PDF evidence and correction boundary

User goal item 7 requires Codex itself to exercise MCP. A direct SDK client is
still necessary for repeatable mechanics, but cannot establish image perception
or agent tool use. Add a separately opted-in CLI runner with synthetic inputs,
one current-checkout stdio server, existing authentication, no persistent config
writes, and independent trace/artifact checks. Retain recoverable tool failures
and first-pass transcription accuracy instead of reporting only final success.
One scan run dropped two leading zeros and corrected them after image reinspection;
this is agent correction, not deterministic MCP semantic validation.

Image integrity is a necessary MCP responsibility: real testing found rotated
page crops mixed unrotated locator and rotated rendering coordinates. Fix the
coordinate transform, with independent full-page/pixel crop regressions. Preserve
unrotated cropbox locator metadata. This is supported by official PyMuPDF Page
coordinate documentation: https://pymupdf.readthedocs.io/en/latest/page.html.
Codex launch follows https://learn.chatgpt.com/docs/non-interactive-mode and
https://learn.chatgpt.com/docs/extend/mcp?surface=cli. Synthetic workflow results
are not general OCR, handwriting, arbitrary table or PDF writeback benchmarks.
