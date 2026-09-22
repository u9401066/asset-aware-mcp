# Native Word story definition lifecycle

Release scope: **1.4.1**. Use the installed runtime contract and the limits below.

Complete header/footer content CRUD needs definition lifecycle and explicit section
inheritance. `read_docx_story_structure` returns the full catalog, its independent
`catalog_sha256`, and the latest complete operation receipt at the selected file
revision. Its `story_structure` pages use one `text_sha256`; equal file revisions
can recur with different latest receipts. The older catalog/reference representations
remain unchanged, including historical Wiki projection identity.

`update_docx_story_structure` requires `asset_id`, `expected_revision` and a typed
`docx_story_structure`: `expected_catalog_sha256`, explicit
`scope: sections_and_following_inheritors`, and 1..32 sequential edits:

| Edit | Required intent |
| --- | --- |
| `create` | New `part`, `story_kind` header/footer, typed paragraph/table `blocks`. |
| `clone` | New `part`, existing `source_part` and complete `source_part_sha256`. |
| `bind` | Zero-based `section_index`, `story_kind`, `variant` default/first/even, `part` or null. |
| `delete` | Existing `part` and `expected_part_sha256`; no surviving bindings or incoming references. |
| `first_page` | Section index and explicit `enabled` boolean; affects header and footer. |
| `even_pages` | Document-level `enabled` boolean; affects all sections' headers and footers. |

Null binding removes only that direct reference, resuming inheritance. To make a
section blank, create/bind a blank paragraph definition. Subsequent inheriting
sections follow changes until the next direct declaration; explicitly rebind them
to their previous parts to preserve their content. Dormant first/even bindings are
still dependencies. Disabling an option retains its definitions.

New names are bounded ASCII XML part paths under `word/`, without `_rels`
directories. Existing names are read from native inventory. New parts cannot reuse
case-folded names or capture dangling relationships. Clones preserve native runs,
tables and field caches, relocate relationship targets to the new owner, retain
external targets/media bytes, and allocate distinct drawing/paragraph identities.
Known ranges, controls, revisions, notes and embedded objects require further
identity-aware clone support and are explicitly rejected. This is not arbitrary
Word clone fidelity.

Deletion checks every retained relationship part and historical section XML, removes
only the unbound definition and its own relationships/content-type override, and
retains referenced media. It is not secure erasure. All edits preserve unrelated
native XML and part bytes, check serialized readback, and commit atomically only
when complete receipts fit the delivery budget. Exact no-ops retain source bytes
and history. The Agent must read every receipt/story and inspect actual page PNGs.
Human source bytes/mtime and historical story evidence, selections and Wikis remain
intact. Microsoft Word parity and footnote/endnote CRUD remain further work.

Growing capability prose exposed a transport truncation regression. Native discovery
now advertises `contract_delivery`, `contract_sha256` and `contract_request`.
`contract_details` provides the entire contract at that hash with text pagination;
scope or capability changes reject stale reads. The compact index retains all
enabled flags, format/operation lists and schema continuation. `schema_request`
continues to deliver the separate request schema. Clients must follow both advertised
delivery mechanisms before relying on complete operation policies.

Primary references:

- [python-docx header inheritance](https://python-docx.readthedocs.io/en/latest/dev/analysis/features/header.html)
- [Open XML header references](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.headerreference?view=openxml-3.0.1)
- [Open XML footer references](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.footerreference?view=openxml-3.0.1)
