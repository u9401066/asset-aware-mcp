# Immutable native operation results

Status: implemented and locally validated on the Unreleased development line. Public 1.4.0, next consolidated 1.4.1; no per-feature version bump.

## Problem and required outcome

Complete native operation results currently live inside `asset.json` beside the
revision index. A valid synthetic ODS with 5,000 formula cells is only 3,091 bytes;
invalidating its typed caches produces a 13,087,436-byte compact result and a
19,529,786-byte candidate metadata file. The current 16 MiB metadata guard rejects
the actual commit. A 4,000-cell control succeeds, but consumes 15,623,786 metadata
bytes. Both probes verify that a rejected commit preserves the prior metadata,
revision and source bytes. Growing histories have the same structural problem.

Keep every complete before/after record, change, check, repair and Agent review
requirement. Separate the revision index from immutable operation-result content;
do not reduce detail, silently truncate results, or merely raise the metadata
limit. This storage improvement applies to native formats generally, including
existing PDF, DOCX, presentation, spreadsheet, delimited and image workflows.

## Identity and persistence

- Each external result has a versioned reference with a SHA-256 digest and exact
  byte size. The blob contains the complete `NativeEditResult` and a versioned
  envelope binding asset ID, history index, revision, parent revision and operation.
  Its hash covers the canonical UTF-8 JSON envelope, not a preview or summary.
- Keep blobs inside the owning asset directory in a dedicated results directory.
  Backups must copy the entire asset directory, including revisions and results.
  Filenames derive only from validated hashes; symlink/path redirection must fail.
- New or mutated metadata uses an explicit storage schema revision. Existing v1
  metadata containing inline results remains readable. On a successful write,
  retain all legacy result content in verified blobs before replacing metadata.
  Reads alone do not rewrite metadata or source documents.
- Never publish a reference before its complete blob is durable and read-back
  checked. Preserve compare-and-swap and source-freshness guards. Missing,
  truncated, replaced, oversized or mismatched blobs fail explicitly on access.
  Existing immutable content must not be overwritten to hide corruption.
- A failed metadata publication leaves the previous index authoritative. Any new
  unreferenced blob is not a committed result. Preserve the current safeguards
  around interrupted source writeback and later reconciliation.
- Keep explicit per-result byte limits independently of the small metadata limit.
  Loading/listing an asset must not hydrate its entire result history into memory.
  Resolve only the selected result, with binding, size, hash and schema checks.
  Never interpret an unresolved reference as an absent or abbreviated result.

## Application behavior

Existing native reads, read-back requests, rendition provenance and Wiki snapshots
must still expose the complete result they currently promise. Resolve references
through the repository port before serializing or inspecting results. Keep legacy
inline results supported by the same access path. Native asset IDs, source hashes,
cell/block/page locators and existing citation references remain unchanged.

Selections and citations retain their existing scopes: stored content integrity
is not semantic truth, formula recalculation or visual equivalence. Agent review
remains responsible for those judgments. Storage changes must not mark review
requirements as passed or substitute a newer result for a selected historical one.

## Verification required before enabling

- Reproduce a real large ODS receipt commit and demonstrate that the complete
  result can be read after restart while metadata stays bounded.
- Exercise repeated large results and legacy inline-history migration. Preserve
  exact result content and historical reads across storage changes.
- Reject missing/corrupt/truncated blobs, altered size/hash, cross-asset or wrong
  revision/history bindings, and path/symlink redirection.
- Test stale CAS, failed publication, unchanged operations and source writeback;
  no failure may publish half a metadata transaction or lose the prior version.
- Check existing complete result responses and native/rendition/Wiki exports,
  including actual SDK2 process restarts. Hash-paged callers must receive all data.
- Run focused regressions, full required checks and an actual default-model Codex
  workflow before declaring the storage-backed Agent workflow complete.

The separate ODS quadratic cache-read scan also needs correction before broad
ODS MCP exposure; this storage change alone does not complete that workflow.

## Implementation and verification

`NativeAssetRepository.read_result` resolves selected entries; application callers
never treat an external reference as a null receipt. Metadata uses
`native-file-asset-v2`, with v1 read compatibility. This internal storage schema
number is independent of the product version. The metadata limit remains 16 MiB;
each complete canonical result envelope has a separate 128 MiB limit.

The focused storage suite covers large Unicode history, restarts, migration, CAS,
no-ops, repeated file hashes, metadata failure, immutable corruption, history
binding, missing/truncated/oversized results and symlink rejection. A three-process
SDK2 regression compares complete reads and every Wiki artifact before migration,
from v1 data, and after migration; selected corruption then fails explicitly. The
independent Codex auditor verifies raw blob size/hash/envelope without importing
the production resolver. Actual Agent runs, full checks and artifact validation
are recorded separately; none imply arbitrary-document visual correctness.

The reproducible 5,000-formula capacity replay is
`tests/native_operation_results_artifact_smoke.py`; it verifies every cache
before/after record, complete post-restart results and unchanged source bytes/mtime.
ODS cache traversal optimization is tracked in `native-ods-spec.md`; public
MCP/evidence/Wiki wiring remains pending.

Local verification: full suite 3,775 passed / 44 skipped (571.83s), followed by
15 passing optional cases (173.83s), covering the 11 additional environment skips
relative to the previous baseline. Actual default-model Codex: 188 successful MCP
calls, four region PNGs, six CSV revisions, three derivations, independent audit
passed. This was a synthetic scan/CSV workflow, not an ODS Agent evaluation.

Checkout, Python 3.13 wheel and Python 3.12 Docker replay the 5,000-formula case
with all 335 source files matched: full receipt 12,387,603 bytes; local index
1,320 bytes versus an 18,829,912-byte inline representation. Exact sources, every
cache record and post-restart results match. Both artifacts pass doctor, 30-tool
discovery and SDK2 stdio; VSIX 199 unit tests, 64 packaged entries and install/update
pass. Local activation is unavailable; remote CI remains required.
