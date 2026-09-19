# Native Word header/footer stories

Status: Unreleased / 1.4.x; public 1.4.0. Next consolidated patch 1.4.1.

The legacy DFM projection preserves header/footer parts but exposes only a short
preview and guesses their variant from filenames. Keep its historical evidence
stable; provide a separate complete native representation, selected by actual
content types and document relationships. No filename-based section inference.

`read_docx_stories` returns complete hash-paged section definitions, inherited
header/footer bindings, first/even-page settings and existing story keys.
`read_docx_story` returns one complete native part: XML, text-node paths, block
positions, relationships and every section/variant using that part, including
disabled definitions. These are definition bindings, not a rendered page map.

`update_docx_story` requires the exact revision, whole story reference and explicit
`shared_scope: all_sections_using_part`. A sequential batch sets existing text
nodes without replacing runs, inserts typed native paragraphs/tables, and deletes
selected complete direct blocks. It edits a shared definition once; it never
silently detaches a linked section. Paths/indices address each intermediate XML
tree. Source files and historical references remain unchanged.

MCP checks native locators, requested readback, source CAS, field/range/control
dependencies, unchanged XML outside the edit plan and exact unrelated part bytes.
No-op returns original bytes. Full before/after operation receipts are paged and
must fit the response budget before commit. Agents review all affected actual
pages, including inherited/latent definitions, field results and overflow.

The new story reference participates in verification, immutable JSON selections,
derivations and custom/CSL citations. Wiki snapshots containing stories use a
distinct projection identity and include every full story record and source part.
Legacy snapshots and references remain available without reinterpretation.

Creating/deleting whole header/footer definitions, changing section links and
editing footnote/endnote stories remain further work toward full Word CRUD.
This increment completes native content CRUD inside existing header/footer parts;
it does not establish arbitrary Word or Microsoft Word rendering fidelity.

References:
- https://python-docx.readthedocs.io/en/latest/dev/analysis/features/header.html
- https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.headerreference?view=openxml-3.0.1
