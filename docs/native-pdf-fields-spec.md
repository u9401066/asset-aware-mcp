# Native PDF field CRUD — managed MCP integration

Release scope: **1.4.1**. Complete paged field reads and checked native CRUD
connect managed revisions, evidence and Wiki through MCP. The default Codex form
evaluation passed an independent audit; static previews do not prove interactive
viewer parity. Publication status is listed in GitHub Releases.

## Managed operations and evidence

Discover `read_pdf_fields`, `read_pdf_field` and `update_pdf_fields` through the
native contract and their complete operation schemas. Reads require `asset_id`
and `revision`; a single-field read also requires its exact `pdf_field_locator`.
Assemble every top-level `text_excerpt` using Unicode character offsets, verify
the complete UTF-8 `text_sha256`, and send `pdf_field_text_sha256` on continuation.
The catalog's `catalog_sha256` is a separate guard for mutation. Catalog reads
include the complete latest operation receipt for that exact file revision.

Updates require `expected_revision` and `pdf_fields_update`, which contains
`expected_catalog_sha256` and the typed edits described below. Every existing
field, create parent and create widget page must refer to the same asset and
original revision. After a successful change, read the complete `review_request`
and reacquire current references from the serialized PDF. Object numbers can
change during serialization; never transfer old object numbers to a new revision.
No-op receipts are returned inline, without appending history. External source
files are untouched; source writeback remains a separate explicit operation.

Full `native-pdf-field-ref-v1` references can be verified, selected with a JSON
Pointer/character range, cited through CSL, or used as derivation sources and
targets. Historical references remain bound to their original bytes after editing
or deletion. Custom citation text identifies the physical field path and object;
display names never replace these identities.

PDFs with an AcroForm or orphan page widgets use a `pdf-fields-v1:<receipt hash>`
Wiki projection. It retains exact PDF bytes, complete field and annotation
catalogs/records, operation receipts, distinct notes for duplicate names, hidden
values, child-field links and every actual widget-page preview. Empty AcroForms
retain the final deletion receipt. Returning to identical PDF bytes with a new
operation receipt produces a separate Wiki snapshot; old snapshots stay intact.
PDFs without AcroForm/widget evidence retain their existing projection.

## Implemented native operations

`edit_fields` consumes a full original catalog hash and 1–32 edits. Every update
or deletion uses a full original field reference; new widgets use full original
page references. Overlapping existing subtree targets fail. Each request produces
an independent candidate PDF and complete receipts; original file bytes are never
overwritten by this adapter.

- Create text, checkbox, radio and choice fields, including hidden text/choice
  values and up to 32 page widgets. New fields can be roots or children of an exact
  existing parent. Explicit `new_groups` creates new named ancestors atomically
  with the leaf; it never resolves an existing parent by a guessed name.
- Update text, checkbox/radio native state names, or exact choice-option indices.
  Multiselect preserves native `V` arrays and `I` indices, including duplicate
  export values with different labels. Field type, option definitions, other
  fields and source content remain intact.
- Delete the explicitly referenced subtree and all its widgets. Receipts retain
  every removed field record, not just the top-level group definition. Incoming
  native references and shared array ownership are checked. Historical copies are
  independent; deletion is not secure erasure.

Visible text/choice updates require `replace_all_widget_appearances` and a style
for every original widget path. This is explicit style replacement inside the
existing native rectangle, not a promise to reconstruct arbitrary original font
styling. Omitted style values use schema defaults. Embedded font resources and
normal appearances are generated in a separate document; stale rollover/down
appearances are removed. Widget rotation and page crop/rotation/UserUnit are
retained. Styles use displayed point sizes before page rotation. Multiline and
comb layout are explicit; single-line fields cannot silently wrap, and unsupported
glyphs or text that does not fit fail instead of being replaced or truncated.
The caller can deliberately revise the style/value and retry.

Checkbox/radio updates instead require `preserve_native_button_states`: existing
appearance streams stay byte-identical while `V` and every widget's `AS` change
together. Hidden fields require `no_widgets`. Identical value/style results return
the original bytes without serialization or a new history event. Repeated Unicode
updates reuse existing font objects/resources instead of embedding another full
font copy each time.

The journal tracks only requested dictionary keys and arrays. After serializing,
the adapter independently reopens and compares all native page/document graphs,
then restores its in-memory edits and checks the original graphs. Bounded base
page renders and untouched-page renders must agree. Final field records and the
full new catalog are read from serialized bytes. Fault-injection tests cover both
unplanned page-content changes and a writer returning a wrong field value.

Existing encryption/signature/XFA restrictions remain. Mutations also require
unambiguous ownership and editable flags. Tagged widget dependencies, requested
whole-form viewer regeneration (`NeedAppearances`), password/file-select/rich-text
value workflows, ambiguous radio states without `RadiosInUnison`, and clearing a
choice value inherited from an ancestor retain explicit guards. Readable native
data is not thereby advertised as editable. Existing actions/scripts are retained
without execution; their semantic/calculation dependencies and native viewer
editing/regeneration require Agent review. These limits do not redefine the wider
document collaboration goal as complete.

## Identity and representation

`PdfFieldLocator.field_path` starts with a zero-based index in `AcroForm.Fields`;
each following index addresses the original parent's `Kids` array. The locator
also contains the original PDF object number and generation. A full
`PdfFieldReference` adds the immutable file revision and complete record hash.
Partial and qualified names are labels: duplicate names never collapse records or
authorize editing a different object. Direct dictionaries retain physical paths
and explicit identity limitations.

The raw field tree distinguishes logical field nodes from pure Widget children.
A radio group is one field with multiple widgets. One field can have widgets on
several pages or no visual widget. Every actual page `Annots` occurrence retains
its page/object/array locator. Equal direct dictionaries are not assumed to be the
same object. Orphan widgets, missing or conflicting parent/page links, ambiguous
widget attributes and multiple occurrences are reported. Cycles, shared tree
ownership, malformed arrays and resource-limit violations fail explicitly.

Records retain native field properties, ancestor definitions, the origin of each
inherited entry, child-field locators, all owned widgets and their appearance
graphs/states. A group record describes its own definition and membership;
descendant values remain separate records. Catalog hashes cover every field
record, orphan widgets and form properties. Shared default appearance/resources
are included in the form-properties hash bound into each field record. Parent
links and physical tree paths remain distinct when they disagree; the reader
does not repair one to agree with the other.

The selected inherited entries are `FT`, `Ff`, `V`, `DV`, `DA`, `Q`, `MaxLen`,
`Opt`, `TI` and `I`. Missing field-level `DA`/`Q` can resolve to explicit AcroForm
defaults. `AA`, `T`, `TU`, `TM`, `DS` and `RV` are not inherited. Native graphs keep
string bytes, multiselect arrays/indices and unknown properties; no scalar-only
choice conversion occurs. Widget geometry uses the existing displayed CropBox
fractions after rotation, without clipping coordinates to the page.

Limits: 20,000 combined field-tree nodes/widgets, 20,000 page annotations,
64 tree levels, 16 MiB per field record and 128 MiB aggregate catalog
representation. Existing native PDF encryption, signature, XFA mutation and parser
checks remain in force. Reading does not invoke implicit AcroForm repair or set
`NeedAppearances`. XFA presence is retained; AcroForm values are not claimed to
represent the XFA interface.

## Upstream references and observed differences

- [pypdf form documentation](https://pypdf.readthedocs.io/en/latest/user/forms.html)
  explains the field-tree/page-widget distinction, repeated fields and radio
  groups. Its name-oriented examples are not sufficient as revision-bound
  mutation selectors.
- [pikepdf form documentation](https://pikepdf.readthedocs.io/en/latest/api/form.html)
  identifies appearance-generation and multiselect limitations. In the installed
  `10.13.0.post1` implementation, `MultipleFieldProxy` forwards value writes to the
  first duplicate; the high-level choice wrapper treats multiselect as single
  selection. Low-level `AcroForm.validate()` defaults to repair, so it must not be
  used implicitly in a source-preserving read path.
- [PyMuPDF Widget documentation](https://pymupdf.readthedocs.io/en/latest/widget.html)
  supplies widget/appearance operations to evaluate during mutation development.
  A native value update alone is not evidence that every appearance was updated.
- Adobe's [PDF 1.7 reference](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/pdfreference1.7old.pdf)
  and [PDF 1.4 choice-field entries](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/pdfreference1.4.pdf)
  document the inheritance and option-index distinctions retained here.

Read-only checks used pinned inputs from pikepdf tag `v10.13.0.post1`, with Git
blob identities and SHA-256 retained in the local research manifest:

| Upstream input | Observed result |
|---|---|
| `form.pdf` | 4 logical fields, 5 page widgets, no orphans, no XFA; the source object graph stayed unchanged. Low-level enumeration reports the radio widgets separately, which is why it is not used as the logical-field inventory. |
| `form_210966.pdf` | 64 field nodes, including 61 terminal fields, 69 page widgets, no orphans; XFA retained and source object graph unchanged. |
| `form_dd0293.pdf` | Existing native-package encryption guard rejected the input, although its empty user password permits low-level library opening. Also contains XFA. No native catalog success or mutation compatibility is claimed. |

Synthetic regression fixtures additionally cover duplicate names, hidden fields,
multiselect values/indices, direct dictionaries, orphan widgets, malformed trees,
resource changes, CJK values and crop/rotation geometry. Their pixel comparisons
prove read preservation; they do not establish value/appearance consistency.

The internal CRUD suite also exercises creation/update/deletion, complete widget
coverage, nested groups, immutable old references, multiline/comb behavior,
no-border output, font reuse/no-op behavior, crop/rotation/UserUnit and native
dependency guards. A local visual exercise retained original/created/changed/
deleted PDFs and eight actual page images; the Agent inspected all eight. It
showed `中文 007 µg α` changing to `更新 008 µg β` on both affected pages and the
original page content after deletion. This was a direct adapter exercise, **not**
the required default Codex/MCP evaluation.

The pinned upstream `form.pdf` was also updated and reopened: `Text1` received
`中文 007 µg`, `Check Box3` selected native `/Yes`, and `Group4` selected native
`/Choice2`; the text field was subsequently deleted. Source bytes stayed unchanged.
The first 12-point text request failed its fit check. An explicit 8-point retry
passed, but visual comparison found that its default style added a black border
to the originally borderless field. The Agent inspected the native `MK`/`BS`/
`Border`/`AP` entries and retried with explicit `border_width=0`. All three final
page images were then inspected; the extra border was gone, the text fitted and
the intended native button states remained. All three attempt logs and both
rendered output sets are retained. This is an actual Agent style correction, not
an MCP semantic verdict or default Codex/MCP evaluation.
This verifies that case, not arbitrary forms or native viewer behavior. A separate
no-border regression initially exposed a PyMuPDF drawing call emitting a stroke
even with no requested color; skipping the empty frame draw fixed it, and the
original pixel-equality assertion now passes.

## Verification and remaining delivery work

Focused tests cover managed source/version checks, complete reads/no-op receipts,
CSL/custom citations, selected substrings, derivation endpoints, all-field deletion
and receipt-sensitive Wiki identity. Real SDK2 stdio tests pass for both balanced
and compact tool surfaces, including contract discovery, hidden-value updates,
Unicode field creation across two pages, deletion, complete readback and actual
page-image comparisons against the committed revisions.

The actual default Codex CLI evaluation used the pinned upstream form above,
without a model override, with only the native MCP document tool. It updated text,
checkbox and radio values, copied the authored text into a new visible field,
deleted the original field, and retained its historical selection as a derivation
source. It read complete contracts, schemas, catalogs, fields and receipts before
continuing, viewed four actual page images, and exported original/final Wikis.

Independent audit passed: 426 successful MCP calls, two recovered tool errors,
four managed versions, 17 complete field records and four actual page images.
The first error was an unused contract parameter; the second rejected a new field
whose text did not fit. Codex explicitly reduced its font size from 5 to 4 points.
Native values/button states, untouched body bytes/pixels, pushbutton and button
appearances, exact receipts, source bytes/mtime, selections and derivation were
checked. The root Agent also inspected all four images: text was legible and
unclipped, deletion removed only the original text, and native button appearances
retained their geometry and intended states.

The model completed successfully; the initial audit failed because it incorrectly
rejected rereading an existing selection reference. The original report is retained.
Corrected audit verifies the complete selection against its already-read parent,
JSON Pointer, context, Unicode/UTF-8 ranges and hashes, with regression tests for
invalid values, parents, contexts and selector overrides. Reauditing the unchanged
trace passed; the model was not rerun to erase a failure. The standalone audit CLI
also returns a failure exit status when the trace is missing or invalid.

Reproduction commands and scope are recorded in the
[evaluation guide](site-content/release-testing.md#codex-native-pdf-field-evaluation-unreleased).
Static MuPDF previews do not verify interactive editing or regeneration in other
viewers. The copied text is an authored value, not evidence from the originally
blank form. Agent owns semantic/visual review; hashes do not certify it. Full
artifact and publication checks remain required.
