# Native raster assets — implementation contract

Release scope: **1.4.1**. Kernel, application, evidence/Wiki, SDK2 and an actual
default Codex evaluation have been verified. The evaluation covers the exercised
samples, not universal image fidelity. Publication status is listed in GitHub Releases.

The `images_enabled` contract flag controls `create_image`, `extract_image`,
`compose_images`, `read_image`, `read_image_frame`, `render_image_frame`,
`read_image_region` and `update_image`. Creates use typed `image_create`,
`image_extract` or `image_compose`; updates pin `asset_id`, `expected_revision`
and `image_update`. Reads pin asset/revision, with `image_locator` for a frame.
Complete catalog/record/receipt JSON is hash-paged through `image`; previews take
a full frame/region `reference` and return actual MCP PNGs. Historical evidence
remains bound to its source. Adapter availability never implies a visual verdict.

A raster asset retains its exact source bytes and immutable revisions. Frame
records describe the decoder's main frame sequence, with zero-based locators,
stored/displayed dimensions, EXIF orientation, sample precision, pixel hashes and
typed metadata. PNG/APNG, JPEG, TIFF, GIF, WebP, BMP and AVIF are the initial
decoder formats. Optional decoder availability remains a runtime constraint.

The projection is not a claim to understand every TIFF sub-IFD, private field,
thumbnail or layer. Animated frames describe composited display frames. APNG's
optional default image is a separate frame. Palette colors and transparency are
part of displayed pixel identity. Unknown or reduced source precision must never
be presented as proven source-sample preservation.

Frame and region references bind asset ID, source SHA-256, complete locator and
canonical record hash. Regions use EXIF-oriented displayed-frame fractions with a
top-left origin; bounds round outward to whole pixels. Render size/color policy
does not change region identity. PNG previews are RGBA8, optionally transformed
from embedded ICC to sRGB, with no inferred HDR intensity scaling.

With `image_evidence_retention_enabled`, reads retain complete canonical frame
records/catalogs and generated preview recipes beside immutable native revisions.
`read_image` and `export_wiki` accept `image_catalog_sha256`; `read_image_frame`
accepts a full `reference` matching its asset/revision/locator. Unpinned reads use
the current decoder. Source bytes are always checked before archive resolution.
Retained hashes keep decoder identity unchanged. Verification reports retained
integrity separately from current-decoder reproduction; no semantic truth is added.

Exact cached PNGs bind full frame/region reference, render size and color policy.
Their original renderer metadata stays intact. Missing historical previews require
current decoding to reproduce the full referenced frame record; changed pixels,
metadata or decoder identity cannot be substituted. Atomic content-addressed files,
commit markers, operation locks, bounded reads and symlink/hash checks protect
capture integrity. Catalog capture is limited to 128 ordered frames/16 MiB of
records; each PNG is at most 3 MiB. Historical reads/Wikis reuse the archive;
mutation guards continue checking current-decoder representations. This does not
retroactively capture uncaptured old representations or certify decoding accuracy.

`export_wiki` retains exact source attachments, all frame records and PNGs, complete
catalogs and operation receipts, plus direct operation input attachments/references.
This is mechanical provenance, not recursively inferred semantic lineage. Explicit
frame/region/selection derivations attach their source evidence across formats.
Custom citation displays include frame/region geometry; CSL retains the full
reference and source file separately from caller-supplied printed locators.
`image_color_policy` also applies to exported previews; invalid ICC needs an explicit
`unmanaged` choice. Image snapshots bind catalog, receipt and color policy, keeping
legacy opaque snapshots and earlier same-file-SHA operation snapshots intact.

Creation offers explicit RGBA canvases. Extraction creates a new PNG/TIFF from a
complete source-frame reference and optional region. TIFF composition creates a
new ordered frame sequence from complete references, with explicit decoded-pixel
or RGBA8 projection and `pixels_only` metadata policy. These derivatives retain
the original asset and report omitted metadata. Each encoded output is reopened
and checked for exact requested frame count, geometry, sample bytes and decoded
colors. Reordering, insertion and deletion can be expressed through a new composed
candidate; no animation timing is invented for a TIFF sequence.

In-place image revisions accept an independently registered candidate with the
same detected format. A plan pins the source catalog and full candidate file
reference, maps or deletes every old frame, and maps or inserts every new frame
exactly once. Mapped frames explicitly preserve or replace decoded pixels and
decoder metadata. The committed bytes are exactly the checked candidate bytes;
the MCP must not silently re-encode an original to satisfy an edit.

Decoder workers have time, memory, input, pixel, metadata and result bounds.
Malformed/truncated TIFF main-directory chains cannot be accepted as shorter
documents. Oversized output or failed readback stops before repository mutation.
MCP handles identity, structural checks and inspectable receipts. The Agent checks
actual images, meaning, color, frame correspondence and metadata changes, then
coordinates corrections. This scoped workflow does not provide arbitrary photo
retouching, layer editing or universal animation/viewer fidelity.

The real Codex evaluation uses an explicitly derived EXIF-oriented PNG from the
hash-pinned NIST SRM1648a PDF page index4, not an originally published PNG. Its 258
successful MCP calls delivered 15 full-frame PNGs and a region preview, completed
three TIFF revisions, created six literal workbook cells and exported three Wiki
snapshots. Independent source/pixel/history/region/citation checks passed. The first
runner wrapper failed after the successful CLI turn because its audit module was
not yet present; that failure is retained, and separate completed audits passed.
See [the reproducible evaluation](../tests/codex_native_image/README.md).

References informing these choices:

- [Pillow file-format behavior](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html)
- [libvips multipage and animated images](https://github.com/libvips/libvips/blob/master/doc/multipage-and-animated-images.md)
