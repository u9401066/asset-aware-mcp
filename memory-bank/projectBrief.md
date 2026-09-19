# Asset-Aware MCP — current project brief

Updated 2026-09-19 from the user's active goal and clarified responsibility split.
Public release stays **1.4.0**; accumulate **Unreleased within 1.4.x** and increment
patch versions only for an intentional release. Do not bump/tag per milestone.

## Purpose and value

Help Agents work on human-delivered native documents and reusable evidence across
PDF, DOCX, spreadsheets, presentations, text/structured documents and media.
Model-native document understanding is useful, but the project must also preserve
source identity, precise locators, reversible managed edits, mechanical checks,
operation receipts and portable cross-document relationships. Reading/summary alone
is insufficient differentiation; broad native CRUD and format fidelity remain an
active goal, not a claim of universal support.

## What becomes an asset

A file becomes an operable asset when it has a stable identity, exact retained
revisions, known capabilities and source relationship. Pages, tables, cells, figures,
text selections and explicit visual regions can be addressable components. Parsed
text, DFM, PNG previews and PDF renditions are representations with declared scope,
not replacements for original bytes. Source-to-target derivations retain complete
references and caller review separately. Unknown files can be retained as opaque
assets without inventing parsed content or unsupported edit capabilities.

For example: retain a scanned PDF revision → view its page/region → Agent
transcribes a string cell → record the exact region-to-cell derivation → export
Wiki notes, JSON evidence and source attachments. Updating the workbook or PDF does
not silently move old claims. Hash validity alone does not establish meaning.

## Responsibility boundary

- MCP: deterministic source/version/locator checks, supported format preservation,
  bounded operations, atomic managed versions, complete inspectable receipts and
  well-defined repairs such as relocating modeled references or clearing stale caches.
- Agent: coverage/transcription, semantic support, actual rendered layout, calculated
  results, choosing corrections and repeating review. No fabricated review scores.
- Human-source publication/writeback remains explicit with source freshness checks;
  revisions, existing Wiki snapshots and curated notes remain protected.

## Current implementation and unfinished scope

Official MCP SDK2 runtime; native PDF page CRUD/regions, DOCX body/DFM operations,
PPTX text/pictures/tables/slide operations, XLSX cells/worksheets/grids/native Tables
and A2T round trips. Optional Writer/Impress/Calc previews support Agent review.
Custom citation templates and simple author-year/numeric presets remain display
contracts separate from evidence; they are not a full APA/Chicago/CSL processor.
Foam Wiki exports and optional LightRAG support cross-document use.

Consult installed contract, README, ROADMAP and tests for exact capability/format
limits. General text/web/structured/media CRUD, complete native feature coverage,
standards-aware citation rendering and broad real-file fidelity remain unfinished.

## Validation and delivery

Use real SDK2 transport and explicitly opted-in default-model Codex tests, including
actual PDF images and independent source/value/pixel audits. Distinguish synthetic
fixtures from real corpora. Update README, Pages, metadata/labels and Memory Bank;
review segmented commits directly on main under u9401066 <u9401066@gap.kmu.edu.tw>,
then verify exact-head CI/Pages and public artifacts. No self-PR or per-task tag.

## Historical context

The 2025-12-26 brief focused on a four-tool medical PDF/RAG MVP. That narrow scope,
its unchecked early milestones and blanket trust in OCR are superseded by the
current cross-format goal and the user's explicit MCP/Agent responsibility split.
Medical research remains a use case, not the product boundary. Local-first remains
a preference; optional services/engines and their dependencies are disclosed.
